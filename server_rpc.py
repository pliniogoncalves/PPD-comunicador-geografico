from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
import threading
from collections import defaultdict

class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

class LocationServer:
    def __init__(self):
        self.lock = threading.Lock()
        self.usuarios = {}
        self.caixas_de_entrada_rpc = defaultdict(list)
        print("Servidor RPC (Gerenciamento e Chat Síncrono) inicializado.")

    def registrar_usuario(self, nome, lat, lon, raio):
        with self.lock:
            self.usuarios[nome] = {
                'lat': float(lat),
                'lon': float(lon),
                'raio': float(raio),
                'status': 'OFFLINE'
            }
            print(f"Usuário '{nome}' registrado/atualizado. Dados: {self.usuarios[nome]}")
            return True

    def atualizar_localizacao(self, nome, lat, lon):
        with self.lock:
            if nome not in self.usuarios: return False
            self.usuarios[nome]['lat'] = float(lat)
            print(f"Localização de '{nome}' atualizada.")
            return True

    def atualizar_raio(self, nome, raio):
        with self.lock:
            if nome not in self.usuarios: return False
            self.usuarios[nome]['raio'] = float(raio)
            print(f"Raio de '{nome}' atualizado.")
            return True

    def atualizar_status(self, nome, status):
        with self.lock:
            if nome not in self.usuarios: return False
            if status not in ['ONLINE', 'OFFLINE']: return False
            self.usuarios[nome]['status'] = status
            print(f"Status de '{nome}' atualizado para {status}")
            return True

    def get_todos_usuarios(self):
        with self.lock:
            return self.usuarios.copy()

    def enviar_mensagem_sincrona(self, remetente, destinatario, mensagem):
        with self.lock:
            if destinatario not in self.usuarios or self.usuarios[destinatario]['status'] != 'ONLINE':
                return False

            msg_formatada = f"(RPC) {remetente}: {mensagem}"
            self.caixas_de_entrada_rpc[destinatario].append(msg_formatada)
            print(f"Mensagem RPC de '{remetente}' para '{destinatario}' recebida e armazenada.")
            return True

    def receber_mensagens_sincronas(self, nome_usuario):
        with self.lock:
            if nome_usuario in self.caixas_de_entrada_rpc:
                mensagens = self.caixas_de_entrada_rpc[nome_usuario]
                self.caixas_de_entrada_rpc[nome_usuario] = []
                return mensagens
            return []

def run_server():
    host = '127.0.0.1'
    port = 8000
    server = SimpleXMLRPCServer((host, port), requestHandler=RequestHandler, allow_none=True)
    server.register_introspection_functions()
    server.register_instance(LocationServer())
    print(f"📡 Servidor RPC iniciado em http://{host}:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()