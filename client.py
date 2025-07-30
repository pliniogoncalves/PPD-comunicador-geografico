import customtkinter as ctk
import xmlrpc.client
import threading
import time
from mqtt_handler import MQTTHandler

RPC_URL = 'http://127.0.0.1:8000/RPC2'
MQTT_BROKER = 'broker.hivemq.com'
MQTT_PORT = 1883
MQTT_TOPIC_PRESENCE = 'ppd/projeto/presenca'

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
        self.mqtt_client = MQTTHandler(MQTT_BROKER, MQTT_PORT, on_message_callback=self.on_mqtt_message)

        self.is_running = True
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.create_widgets()
        self.initialize_connections()

    def create_widgets(self):
        """Cria os componentes da interface gráfica."""
        self.log_textbox = ctk.CTkTextbox(self, state="disabled", wrap="word", width=680, height=400)
        self.log_textbox.pack(padx=10, pady=10)

        self.message_entry = ctk.CTkEntry(self, placeholder_text="Digite sua mensagem...", width=680)
        self.message_entry.pack(padx=10, pady=(0, 10))

    def add_log(self, message):
        """Adiciona uma mensagem à caixa de texto de log de forma segura para threads."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def on_mqtt_message(self, client, userdata, message):
        """Callback para mensagens MQTT recebidas."""
        topic = message.topic
        payload = message.payload.decode()
        self.add_log(f"[MQTT] Mensagem recebida no tópico '{topic}': {payload}")
        if topic == MQTT_TOPIC_PRESENCE:
             self.add_log(f"[PRESENÇA] {payload}")


    def initialize_connections(self):
        """Inicia as conexões RPC e MQTT e as threads de background."""
        try:
            self.rpc_proxy.registrar_usuario(self.username, self.lat, self.lon, self.raio)
            self.add_log(f"[RPC] Usuário '{self.username}' registrado no servidor.")

            will_payload = f"{self.username}:OFFLINE"
            connected = self.mqtt_client.connect(will_topic=MQTT_TOPIC_PRESENCE, will_payload=will_payload)

            if connected:
                self.mqtt_client.publish(MQTT_TOPIC_PRESENCE, f"{self.username}:ONLINE", retain=True)
                self.mqtt_client.subscribe(MQTT_TOPIC_PRESENCE)
                self.rpc_proxy.atualizar_status(self.username, 'ONLINE')
                self.add_log("[MQTT] Conectado e status 'ONLINE' publicado.")
            else:
                self.add_log("[ERRO] Não foi possível conectar ao broker MQTT. As funções de chat não funcionarão.")
                return

            self.rpc_polling_thread = threading.Thread(target=self.poll_rpc_messages, daemon=True)
            self.rpc_polling_thread.start()

        except Exception as e:
            self.add_log(f"[ERRO GERAL] Falha na inicialização: {e}")

    def poll_rpc_messages(self):
        """Função executada em uma thread para buscar mensagens RPC periodicamente."""
        while self.is_running:
            try:
                messages = self.rpc_proxy.receber_mensagens_sincronas(self.username)
                if messages:
                    for msg in messages:
                        self.after(0, self.add_log, f"[MSG SÍNCRONA] {msg}")
            except Exception as e:
                self.after(0, self.add_log, f"[ERRO RPC POLLING] {e}")
                time.sleep(5)

            time.sleep(2)

    def on_closing(self):
        """Função chamada ao fechar a janela."""
        self.is_running = False

        self.mqtt_client.publish(MQTT_TOPIC_PRESENCE, f"{self.username}:OFFLINE", retain=True)
        self.mqtt_client.disconnect()

        self.rpc_proxy.atualizar_status(self.username, 'OFFLINE')

        print("Encerrando a aplicação...")
        self.destroy()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        username = sys.argv[1]
        if username == "Alice":
            lat, lon, raio = -3.71, -38.54, 5.0
        else:
            lat, lon, raio = -3.72, -38.55, 5.0

        app = App(username, lat, lon, raio)
        app.mainloop()
    else:
        print("Uso: python client.py <nome_de_usuario>")