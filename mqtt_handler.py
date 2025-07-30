import paho.mqtt.client as mqtt
import uuid

class MQTTHandler:
    def __init__(self, broker, port, on_message_callback=None):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(client_id=f"user-client-{uuid.uuid4()}", 
                                  callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        if on_message_callback:
            self.client.on_message = on_message_callback

    def connect(self, will_topic=None, will_payload=None):
        """Conecta ao broker e configura o Last Will and Testament."""
        if will_topic and will_payload:
            print(f"Configurando Last Will: Tópico='{will_topic}', Mensagem='{will_payload}'")
            self.client.will_set(will_topic, payload=will_payload, qos=1, retain=True)

        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            print("Conectado ao Broker MQTT com sucesso.")
            return True
        except Exception as e:
            print(f"Falha ao conectar ao Broker MQTT: {e}")
            return False

    def publish(self, topic, payload, qos=1, retain=False):
        self.client.publish(topic, payload, qos=qos, retain=retain)

    def subscribe(self, topic, qos=1):
        self.client.subscribe(topic, qos=qos)
        print(f"Inscrito no tópico: {topic}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("Desconectado do Broker MQTT.")