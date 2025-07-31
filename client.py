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
MQTT_TOPIC_LOCATION_UPDATES = 'ppd/projeto/location_updates'

COLOR_ERROR = "#C21807"
COLOR_ONLINE = "#1F6AA5"
COLOR_OFFLINE = "#C21807"
COLOR_SELECTED_TEXT = "#1F6AA5"
COLOR_SELECTED_BG = ("gray70", "gray30")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.username = None
        self.lat = 0.0
        self.lon = 0.0
        self.raio = 0.0
        self.selected_recipient = None
        self.selected_contact_frame = None
        self.is_online = True
        self.default_switch_progress_color = None
        self.default_switch_fg_color = None
        self.message_buffer = []

        self.title("Comunicador Geográfico - Login")
        self.geometry("400x450")

        self.rpc_proxy = xmlrpc.client.ServerProxy(RPC_URL, allow_none=True)
        self.mqtt_client = None
        self.is_running = True
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.create_login_widgets()

    def create_login_widgets(self):
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
        self.mqtt_client = MQTTHandler(MQTT_BROKER, MQTT_PORT, client_id=self.username, on_message_callback=self.on_mqtt_message)
        self.login_frame.destroy()
        self.title(f"Comunicador Geográfico - {self.username}")
        self.geometry("800x600")
        self.initialize_connections()

    def setup_main_ui(self):
        self.grid_columnconfigure(0, weight=1, minsize=250)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        left_frame = ctk.CTkFrame(self, width=250)
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        left_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left_frame, text="Contatos", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        self.contacts_frame = ctk.CTkScrollableFrame(left_frame)
        self.contacts_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        profile_frame = ctk.CTkFrame(left_frame)
        profile_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(profile_frame, text="Meu Perfil", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(5,10))
        
        ctk.CTkLabel(profile_frame, text="Latitude:").pack(anchor="w", padx=10)
        self.lat_entry_edit = ctk.CTkEntry(profile_frame)
        self.lat_entry_edit.pack(fill="x", padx=10, pady=(0,5))
        self.lat_entry_edit.insert(0, str(self.lat))

        ctk.CTkLabel(profile_frame, text="Longitude:").pack(anchor="w", padx=10)
        self.lon_entry_edit = ctk.CTkEntry(profile_frame)
        self.lon_entry_edit.pack(fill="x", padx=10, pady=(0,5))
        self.lon_entry_edit.insert(0, str(self.lon))

        ctk.CTkLabel(profile_frame, text="Raio (km):").pack(anchor="w", padx=10)
        self.raio_entry_edit = ctk.CTkEntry(profile_frame)
        self.raio_entry_edit.pack(fill="x", padx=10, pady=(0,10))
        self.raio_entry_edit.insert(0, str(self.raio))

        ctk.CTkButton(profile_frame, text="Atualizar Perfil", command=self._update_profile).pack(fill="x", padx=10, pady=(0,10))

        self.status_switch = ctk.CTkSwitch(profile_frame, text="Status Online", command=self._toggle_status)
        self.status_switch.pack(fill="x", padx=10, pady=10)
        self.status_switch.select()
        self.default_switch_progress_color = self.status_switch.cget("progress_color")
        self.default_switch_fg_color = self.status_switch.cget("fg_color")

        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        self.log_textbox = ctk.CTkTextbox(right_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.recipient_label = ctk.CTkLabel(right_frame, text="Selecione um contato para enviar mensagem")
        self.recipient_label.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,5))
        self.message_entry = ctk.CTkEntry(right_frame, placeholder_text="Digite sua mensagem...")
        self.message_entry.grid(row=2, column=0, padx=(10, 5), pady=10, sticky="ew")
        self.message_entry.bind("<Return>", self.send_message_callback)
        self.send_button = ctk.CTkButton(right_frame, text="Enviar", width=100, command=self.send_message)
        self.send_button.grid(row=2, column=1, padx=(5, 10), pady=10, sticky="e")
        self._update_contacts_list()

    def _create_contact_item(self, parent_frame, username, status, distance=None):
        color = COLOR_ONLINE if status == 'ONLINE' else COLOR_OFFLINE
        item_frame = ctk.CTkFrame(parent_frame, fg_color="transparent", corner_radius=5)
        item_frame.pack(fill="x", padx=5, pady=3)
        item_frame.grid_columnconfigure(1, weight=1)
        dot_label = ctk.CTkLabel(item_frame, text="●", text_color=color, font=ctk.CTkFont(size=18), fg_color="transparent")
        dot_label.grid(row=0, column=0, sticky="w")
        name_label = ctk.CTkLabel(item_frame, text=username, anchor="w", fg_color="transparent")
        name_label.grid(row=0, column=1, sticky="w", padx=5)
        if distance is not None:
            dist_label = ctk.CTkLabel(item_frame, text=f"({distance:.2f} km)", anchor="e", font=ctk.CTkFont(size=10), text_color="gray", fg_color="transparent")
            dist_label.grid(row=0, column=2, sticky="e", padx=5)
            dist_label.bind("<Button-1>", lambda event, u=username, f=item_frame: self._select_recipient(u, f))
        item_frame.bind("<Button-1>", lambda event, u=username, f=item_frame: self._select_recipient(u, f))
        dot_label.bind("<Button-1>", lambda event, u=username, f=item_frame: self._select_recipient(u, f))
        name_label.bind("<Button-1>", lambda event, u=username, f=item_frame: self._select_recipient(u, f))

    def _select_recipient(self, username, frame):
        if self.selected_contact_frame is not None:
            try:
                self.selected_contact_frame.configure(fg_color="transparent")
            except ctk.TclError:
                pass
        frame.configure(fg_color=COLOR_SELECTED_BG)
        self.selected_contact_frame = frame
        self.selected_recipient = username
        self.recipient_label.configure(text=f"Enviando para: {self.selected_recipient}", text_color=COLOR_SELECTED_TEXT)

    def _toggle_status(self):
        self.is_online = not self.is_online
        new_status = 'ONLINE' if self.is_online else 'OFFLINE'

        if self.is_online:
            self.status_switch.configure(text="Status Online", progress_color=self.default_switch_progress_color, fg_color=self.default_switch_fg_color)
        else:
            self.status_switch.configure(text="Status Offline", fg_color=COLOR_OFFLINE)

        try:
            self.rpc_proxy.atualizar_status(self.username, new_status)
            self.mqtt_client.publish(MQTT_TOPIC_PRESENCE, f"{self.username}:{new_status}", retain=True)

            if self.is_online:
                self.add_log("[SISTEMA] Seu status foi alterado para ONLINE.")
                self.add_log(f"[SISTEMA] Exibindo {len(self.message_buffer)} mensagens recebidas...")
                for msg in self.message_buffer:
                    self.add_log(f"[MSG ASSÍNCRONA] {msg}")
                self.message_buffer.clear()
            else:
                self.add_log("[SISTEMA] Seu status foi alterado para OFFLINE (Invisível).")
                self.add_log("[SISTEMA] Você não receberá novas mensagens até ficar online.")
            
        except Exception as e:
            self.add_log(f"[ERRO] Falha ao atualizar status: {e}")
            self.is_online = not self.is_online
            if self.is_online:
                self.status_switch.select()
                self.status_switch.configure(text="Status Online", progress_color=self.default_switch_progress_color, fg_color=self.default_switch_fg_color)
            else:
                self.status_switch.deselect()
                self.status_switch.configure(text="Status Offline", fg_color=COLOR_OFFLINE)

    def _update_profile(self):
        new_lat_str = self.lat_entry_edit.get()
        new_lon_str = self.lon_entry_edit.get()
        new_raio_str = self.raio_entry_edit.get()
        try:
            new_lat = float(new_lat_str)
            new_lon = float(new_lon_str)
            new_raio = float(new_raio_str)
        except ValueError:
            self.add_log("[ERRO] Falha ao atualizar perfil: valores devem ser numéricos.")
            return
        self.lat, self.lon, self.raio = new_lat, new_lon, new_raio
        try:
            self.rpc_proxy.atualizar_localizacao(self.username, self.lat, self.lon)
            self.rpc_proxy.atualizar_raio(self.username, self.raio)
            self.add_log("[SISTEMA] Perfil atualizado com sucesso no servidor.")
            update_payload = f"{self.username}"
            self.mqtt_client.publish(MQTT_TOPIC_LOCATION_UPDATES, update_payload)
            self._update_contacts_list()
        except Exception as e:
            self.add_log(f"[ERRO] Falha ao comunicar atualização ao servidor: {e}")

    def add_log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def on_mqtt_message(self, client, userdata, message):
        topic = message.topic
        payload = message.payload.decode()
        
        if topic == MQTT_TOPIC_PRESENCE:
            self.after(100, self._update_contacts_list)
        
        elif topic == MQTT_TOPIC_LOCATION_UPDATES:
            updated_user = payload
            if updated_user != self.username:
                self.add_log(f"[SISTEMA] {updated_user} atualizou a localização. Atualizando lista...")
                self.after(100, self._update_contacts_list)
        
        elif topic == f"{MQTT_TOPIC_MSG_BASE}/{self.username}":
            if self.is_online:
                self.add_log(f"[MSG ASSÍNCRONA] {payload}")
            else:
                self.message_buffer.append(payload)

    def _update_contacts_list(self):
        if not hasattr(self, 'contacts_frame'): return
        
        self.selected_recipient = None
        self.selected_contact_frame = None
        self.recipient_label.configure(text="Selecione um contato para enviar mensagem", text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"])

        try:
            all_users_data = self.rpc_proxy.get_todos_usuarios()
        except Exception as e:
            self.add_log(f"[ERRO] Falha ao buscar lista de usuários: {e}")
            return

        list_of_widgets = list(self.contacts_frame.winfo_children())
        for widget in list_of_widgets:
            widget.destroy()

        online_in_radius, online_out_of_radius, offline_users = {}, {}, {}
        for user, data in all_users_data.items():
            if user == self.username: continue
            if data['status'] == 'ONLINE':
                dist = calcular_distancia(self.lat, self.lon, data['lat'], data['lon'])
                if dist <= self.raio:
                    online_in_radius[user] = {'data': data, 'dist': dist}
                else:
                    online_out_of_radius[user] = {'data': data, 'dist': dist}
            else:
                offline_users[user] = {'data': data}
        
        if online_in_radius:
            ctk.CTkLabel(self.contacts_frame, text=f"Online (Dentro do Raio - {len(online_in_radius)})", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=(5,2))
            for user, info in sorted(online_in_radius.items()):
                self._create_contact_item(self.contacts_frame, user, 'ONLINE', info['dist'])

        if online_out_of_radius:
            ctk.CTkLabel(self.contacts_frame, text=f"Online (Fora do Raio - {len(online_out_of_radius)})", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=(15,2))
            for user, info in sorted(online_out_of_radius.items()):
                self._create_contact_item(self.contacts_frame, user, 'ONLINE', info['dist'])
        
        if offline_users:
            ctk.CTkLabel(self.contacts_frame, text=f"Offline ({len(offline_users)})", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=(15,2))
            for user, info in sorted(offline_users.items()):
                self._create_contact_item(self.contacts_frame, user, 'OFFLINE')

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
                self.add_log("Bem-vindo! Conexões estabelecidas.")
                self.mqtt_client.publish(MQTT_TOPIC_PRESENCE, f"{self.username}:ONLINE", retain=True)
                self.mqtt_client.subscribe(MQTT_TOPIC_PRESENCE)
                self.mqtt_client.subscribe(self.personal_topic)
                self.mqtt_client.subscribe(MQTT_TOPIC_LOCATION_UPDATES)
                self.add_log("[MQTT] Conectado e status 'ONLINE' anunciado.")
            else:
                self.create_login_widgets()
                self.status_label_login.configure(text="Falha ao conectar ao Broker MQTT.", text_color=COLOR_ERROR)
                return
            self.rpc_polling_thread = threading.Thread(target=self.poll_rpc_messages, daemon=True)
            self.rpc_polling_thread.start()
        except Exception as e:
            self.create_login_widgets()
            self.status_label_login.configure(text="Erro de conexão RPC.", text_color=COLOR_ERROR)
            print(f"Erro detalhado: {e}")
            self.login_button.configure(state="normal", text="Tentar Novamente")

    def poll_rpc_messages(self):
        while self.is_running:
            if not self.is_online: 
                time.sleep(2)
                continue
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
        recipient = self.selected_recipient
        message = self.message_entry.get()
        if not recipient:
            self.add_log("[SISTEMA] Selecione um destinatário na lista de contatos.")
            return
        if not message:
            self.add_log("[SISTEMA] Digite uma mensagem para enviar.")
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
            def cleanup_thread():
                try:
                    if self.mqtt_client:
                        self.mqtt_client.publish(MQTT_TOPIC_PRESENCE, f"{self.username}:OFFLINE", retain=True)
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