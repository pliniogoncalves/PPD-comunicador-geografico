import xmlrpc.client
import time

proxy = xmlrpc.client.ServerProxy('http://127.0.0.1:8000/RPC2', allow_none=True)

try:
    print("--- Cenário de Teste da Etapa 1 (Revisada) ---")

    print("\n1. Alice se registra e fica online.")
    proxy.registrar_usuario("Alice", -3.71, -38.54, 5.0)
    proxy.atualizar_status("Alice", "ONLINE")

    print("2. Beto se registra e fica online.")
    proxy.registrar_usuario("Beto", -3.72, -38.55, 5.0)
    proxy.atualizar_status("Beto", "ONLINE")

    print("\n3. Verificando estado do servidor:")
    print(proxy.get_todos_usuarios())

    print("\n4. Alice envia uma mensagem RPC para Beto.")
    proxy.enviar_mensagem_sincrona("Alice", "Beto", "Oi Beto, tudo bem? (via RPC)")

    print("5. Beto faz polling e verifica suas mensagens.")
    mensagens_beto = proxy.receber_mensagens_sincronas("Beto")
    print(f"Beto recebeu: {mensagens_beto}")

    print("\n6. Beto verifica de novo, a caixa de entrada deve estar vazia.")
    mensagens_beto = proxy.receber_mensagens_sincronas("Beto")
    print(f"Beto recebeu: {mensagens_beto}")

except Exception as e:
    print(f"Ocorreu um erro: {e}")