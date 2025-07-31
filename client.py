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
COLOR_ERROR = "#C21807"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.username = None
        self.lat = 0.0
        self.lon = 0.0
        self.raio = 0.0

        self.title("Comunicador Geográfico - Login")
        self.geometry("400x450")

        self.rpc_proxy = xmlrpc.client.ServerProxy(RPC_URL, allow_none=True)
        self.mqtt_client = None
        self.is_running = True
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.create_login_widgets()

    def create_login_widgets(self):
        """Cria a interface gráfica para a tela de login."""
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(self.login_frame, text="Conectar ao Sistema", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 20))

        ctk.CTkLabel(self.login_frame, text="Nome de Usuário").pack(anchor="w", padx=10)
        self.username_entry_login = ctk.CTkEntry(self.login_frame, placeholder_text="Ex: Alice")
        self.username_entry_login.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(self.login_frame, text="Latitude").pack(anchor="w", padx=10)
        self.lat_entry_login = ctk.CTkEntry(self.login_frame, placeholder_text="Ex: -3.74")
        self.lat_entry_login.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(self.login_frame, text="Longitude").pack(anchor="w", padx=10)
        self.lon_entry_login = ctk.CTkEntry(self.login_frame, placeholder_text="Ex: -38.52")
        self.lon_entry_login.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(self.login_frame, text="Raio de Comunicação (km)").pack(anchor="w", padx=10)
        self.raio_entry_login = ctk.CTkEntry(self.login_frame, placeholder_text="Ex: 20")
        self.raio_entry_login.pack(fill="x", padx=10, pady=(0, 10))

        self.login_button = ctk.CTkButton(self.login_frame, text="Conectar", command=self.login)
        self.login_button.pack(fill="x", padx=10, pady=20)
        
        self.status_label_login = ctk.CTkLabel(self.login_frame, text="")
        self.status_label_login.pack()

    def login(self):
        """Processa os dados de login, conecta e transita para a tela principal."""
        self.username = self.username_entry_login.get().strip()
        lat_str = self.lat_entry_login.get().strip()
        lon_str = self.lon_entry_login.get().strip()
        raio_str = self.raio_entry_login.get().strip()

        if not all([self.username, lat_str, lon_str, raio_str]):
            self.status_label_login.configure(text="Todos os campos são obrigatórios.", text_color=COLOR_ERROR)
            return

        try:
            self.lat = float(lat_str)
            self.lon = float(lon_str)
            self.raio = float(raio_str)
        except ValueError:
            self.status_label_login.configure(text="Latitude, Longitude e Raio devem ser números.", text_color=COLOR_ERROR)
            return

        self.login_button.configure(state="disabled", text="Conectando...")
        self.status_label_login.configure(text="")
        
        self.mqtt_client = MQTTHandler(MQTT_BROKER,
                                       MQTT_PORT,
                                       client_id=self.username,
                                       on_message_callback=self.on_mqtt_message)
        
        self.login_frame.destroy()
        self.title(f"Comunicador Geográfico - {self.username}")
        self.geometry("700x500")
        
        self.initialize_connections()

    def setup_main_ui(self):
        """Cria os widgets da tela principal de chat."""
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
        self.update_online_users()

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
            
            self.rpc_proxy.atualizar_status(self.username, 'ONLINE')
            
            self.personal_topic = f"{MQTT_TOPIC_MSG_BASE}/{self.username}"
            will_payload = f"{self.username}:OFFLINE"
            connected = self.mqtt_client.connect(will_topic=MQTT_TOPIC_PRESENCE, will_payload=will_payload)
            
            if connected:
                self.setup_main_ui()
                self.add_log(f"[RPC] Usuário '{self.username}' registrado.")
                self.add_log("[RPC] Status atualizado para ONLINE no servidor.")
                self.add_log("Bem-vindo! Conexões estabelecidas.")

                self.mqtt_client.publish(MQTT_TOPIC_PRESENCE, f"{self.username}:ONLINE", retain=True)
                self.mqtt_client.subscribe(MQTT_TOPIC_PRESENCE)
                self.mqtt_client.subscribe(self.personal_topic)
                self.add_log("[MQTT] Conectado e status 'ONLINE' anunciado.")
            else:
                self.status_label_login.configure(text="Falha ao conectar ao Broker MQTT.", text_color=COLOR_ERROR)
                self.login_button.configure(state="normal", text="Conectar")
                return

            self.rpc_polling_thread = threading.Thread(target=self.poll_rpc_messages, daemon=True)
            self.rpc_polling_thread.start()
        except Exception as e:
            self.create_login_widgets()
            self.status_label_login.configure(text=f"Erro de conexão RPC.", text_color=COLOR_ERROR)
            print(f"Erro detalhado: {e}")
            self.login_button.configure(state="normal", text="Tentar Novamente")
            

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
        if self.username:
            self.is_running = False
            self.add_log("[SISTEMA] Encerrando...")

            def cleanup_thread():
                try:
                    if self.mqtt_client:
                        self.mqtt_client.disconnect()
                    self.rpc_proxy.atualizar_status(self.username, 'OFFLINE')
                    print(f"Limpeza em background para '{self.username}' concluída.")
                except Exception as e:
                    print(f"Erro durante a limpeza em background: {e}")

            threading.Thread(target=cleanup_thread, daemon=True).start()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()