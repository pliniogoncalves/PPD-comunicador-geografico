import customtkinter as ctk
import xmlrpc.client
import threading
import time
from mqtt_handler import MQTTHandler
from utils import calcular_distancia
import xml.parsers.expat

RPC_URL = 'http://127.0.0.1:8000/RPC2'
MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883
MQTT_TOPIC_PRESENCE = 'ppd/projeto/presenca'
MQTT_TOPIC_MSG_BASE = 'ppd/projeto/mensagens'

class App(ctk.CTk):
    def __init__(self, username, lat, lon, raio):
        super().__init__()
        self.username = username
        self.lat = lat
        self.lon = lon
        self.raio = raio
        self.title(f"Comunicador Geográfico - {self.username}")
        self.geometry("700x500")
        self.rpc_proxy = xmlrpc.client.ServerProxy(RPC_URL, allow_none=True)
        self.mqtt_client = MQTTHandler(MQTT_BROKER, 
                                       MQTT_PORT, 
                                       client_id=self.username,
                                       on_message_callback=self.on_mqtt_message)
        self.is_running = True
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.online_users = []
        self.create_widgets()
        self.initialize_connections()

    def create_widgets(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(padx=10, pady=10, fill="x")
        self.user_combobox = ctk.CTkComboBox(top_frame, values=["Ninguém online"], state="readonly")
        self.user_combobox.pack(side="left", padx=(0, 10))
        self.message_entry = ctk.CTkEntry(top_frame, placeholder_text="Digite sua mensagem...", width=350)
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0,10))
        self.message_entry.bind("<Return>", self.send_message_callback)
        self.send_button = ctk.CTkButton(top_frame, text="Enviar", command=self.send_message)
        self.send_button.pack(side="left")
        self.log_textbox = ctk.CTkTextbox(self, state="disabled", wrap="word")
        self.log_textbox.pack(padx=10, pady=(0, 10), fill="both", expand=True)

    def add_log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def on_mqtt_message(self, client, userdata, message):
        topic = message.topic
        payload = message.payload.decode()
        
        if topic == MQTT_TOPIC_PRESENCE:
            self.add_log(f"[PRESENÇA] {payload}")
            try:
                user, status = payload.split(':')
                
                if user != self.username:
                    self.rpc_proxy.atualizar_status(user, status)
                    self.add_log(f"[RPC SYNC] Status de '{user}' atualizado para '{status}' no servidor.")

            except Exception as e:
                self.add_log(f"[AVISO] Não foi possível processar a mensagem de presença: {e}")
                
            self.update_online_users()
            
        elif topic == f"{MQTT_TOPIC_MSG_BASE}/{self.username}":
            self.add_log(f"[MSG ASSÍNCRONA] {payload}")

    def update_online_users(self):
        try:
            all_users = self.rpc_proxy.get_todos_usuarios()
            all_other_users_list = sorted([user for user in all_users if user != self.username])
            
            self.after(0, self._update_combobox_ui, all_other_users_list)

        except Exception as e:
            self.add_log(f"[ERRO] Não foi possível buscar a lista de usuários: {e}")

    def _update_combobox_ui(self, all_users):
        try:
            current_selection = self.user_combobox.get()

            if all_users:
                self.user_combobox.configure(values=all_users)
                if current_selection in all_users:
                    self.user_combobox.set(current_selection)
                else:
                    self.user_combobox.set(all_users[0])
            else:
                self.user_combobox.configure(values=["Nenhum outro usuário"])
                self.user_combobox.set("Nenhum outro usuário")
        except Exception as e:
            self.add_log(f"[ERRO UI] Falha ao atualizar a lista de contatos: {e}")

    def initialize_connections(self):
        try:
            self.rpc_proxy.registrar_usuario(self.username, self.lat, self.lon, self.raio)
            self.add_log(f"[RPC] Usuário '{self.username}' registrado.")
            
            self.rpc_proxy.atualizar_status(self.username, 'ONLINE')
            self.add_log("[RPC] Status atualizado para ONLINE no servidor.")
            
            self.personal_topic = f"{MQTT_TOPIC_MSG_BASE}/{self.username}"
            will_payload = f"{self.username}:OFFLINE"
            connected = self.mqtt_client.connect(will_topic=MQTT_TOPIC_PRESENCE, will_payload=will_payload)
            
            if connected:
                self.mqtt_client.publish(MQTT_TOPIC_PRESENCE, f"{self.username}:ONLINE", retain=True)
                self.mqtt_client.subscribe(MQTT_TOPIC_PRESENCE)
                self.mqtt_client.subscribe(self.personal_topic)
                self.add_log("[MQTT] Conectado e status 'ONLINE' anunciado.")
                self.update_online_users()
            else:
                self.add_log("[ERRO] Falha na conexão MQTT.")
                return

            self.rpc_polling_thread = threading.Thread(target=self.poll_rpc_messages, daemon=True)
            self.rpc_polling_thread.start()
        except Exception as e:
            self.add_log(f"[ERRO GERAL] {e}")


    def poll_rpc_messages(self):
        while self.is_running:
            try:
                messages = self.rpc_proxy.receber_mensagens_sincronas(self.username)
                if messages:
                    for msg in messages:
                        self.after(0, self.add_log, f"[MSG SÍNCRONA] {msg}")
            except xml.parsers.expat.ExpatError:
                pass
            except Exception as e:
                self.after(0, self.add_log, f"[ERRO RPC POLLING] {e}")
                time.sleep(5)
            time.sleep(2)

    def send_message_callback(self, event):
        self.send_message()

    def send_message(self):
        recipient = self.user_combobox.get()
        message = self.message_entry.get()
        if not message or recipient in ["Nenhum outro usuário", "Ninguém online"]:
            self.add_log("[SISTEMA] Selecione um destinatário e digite uma mensagem.")
            return
        
        try:
            all_users = self.rpc_proxy.get_todos_usuarios()
            recipient_data = all_users.get(recipient)

            if not recipient_data:
                self.add_log(f"[ERRO] Usuário '{recipient}' não encontrado no servidor.")
                return
            
            dist = calcular_distancia(self.lat, self.lon, recipient_data['lat'], recipient_data['lon'])
            
            log_message = f"Você para {recipient}: {message}"
            
            if recipient_data['status'] == 'ONLINE' and dist <= self.raio:
                self.add_log(f"{log_message} (via RPC)")
                self.rpc_proxy.enviar_mensagem_sincrona(self.username, recipient, message)
            else:
                self.add_log(f"{log_message} (via MQTT)")
                recipient_topic = f"{MQTT_TOPIC_MSG_BASE}/{recipient}"
                self.mqtt_client.publish(recipient_topic, f"(MQTT) {self.username}: {message}")

            self.message_entry.delete(0, 'end')
        except Exception as e:
            self.add_log(f"[ERRO AO ENVIAR] {e}")
    
    def on_closing(self):
        self.is_running = False
        self.add_log("[SISTEMA] Encerrando...")

        def cleanup_thread():
            try:
                self.mqtt_client.disconnect()
                self.rpc_proxy.atualizar_status(self.username, 'OFFLINE')
                print(f"Limpeza em background para '{self.username}' concluída.")
            except Exception as e:
                print(f"Erro durante a limpeza em background: {e}")

        threading.Thread(target=cleanup_thread, daemon=True).start()
        self.destroy()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        username = sys.argv[1]
        if username == "Alice":
            lat, lon, raio = -3.74, -38.52, 20.0
        elif username == "Beto":
            lat, lon, raio = -3.85, -38.62, 10.0
        else:
            username = "Carlos"
            lat, lon, raio = -23.55, -46.63, 10.0
        app = App(username, lat, lon, raio)
        app.mainloop()
    else:
        print("Uso: python client.py <nome_de_usuario>")
        print("Exemplos: python client.py Alice | python client.py Beto | python client.py Carlos")