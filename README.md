# Projeto Final - Comunicador Geográfico

**Disciplina:** Programação Paralela e Distribuída - 2025.1

## Descrição
Sistema de comunicação baseado em localização que utiliza RPC para comunicação síncrona e um Middleware Orientado a Mensagens (MQTT) para comunicação assíncrona, de acordo com o status (online/offline) e a proximidade geográfica dos usuários.

## Arquitetura
- **Servidor RPC (`server_rpc.py`):** Atua como um serviço de diretório central, gerenciando o estado dos usuários (localização, status, raio) e servindo como relay para as mensagens síncronas.
- **Broker MOM (MQTT):** Um broker público (`broker.hivemq.com`) é utilizado para o sistema de presença (status online/offline) e para a fila de mensagens assíncronas de cada usuário.
- **Cliente (`client.py`):** Aplicação com interface gráfica (`CustomTkinter`) que gerencia as conexões RPC e MQTT, a lógica de decisão de comunicação e a interação com o usuário.

## Como Executar

1.  **Instalar as dependências:**
    ```bash
    py -m pip install -r requirements.txt
    ```

2.  **Iniciar o Servidor:**
    Em um terminal, execute:
    ```bash
    py server_rpc.py
    ```

3.  **Iniciar os Clientes:**
    Abra um novo terminal para cada cliente que desejar iniciar. Passe o nome do usuário como argumento.
    ```bash
    # Exemplo para iniciar 3 clientes
    py client.py Alice
    py client.py Beto
    py client.py Carlos
    ```