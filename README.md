# Comunicador Geográfico

## Descrição
Sistema de comunicação baseado em localização que utiliza RPC para comunicação síncrona e um Middleware Orientado a Mensagens (MQTT) para comunicação assíncrona, de acordo com o status (online/offline) e a proximidade geográfica dos usuários.

## Arquitetura
- **Servidor RPC (`server_rpc.py`):** Atua como um serviço de diretório central, gerenciando o estado dos usuários (localização, status, raio) e servindo como relay para as mensagens síncronas.
- **Broker MOM (MQTT):** Um broker público (`broker.hivemq.com`) é utilizado para o sistema de presença (status online/offline), sincronização de estado e para a fila de mensagens assíncronas de cada usuário.
- **Cliente (`client.py`):** Aplicação com interface gráfica (`CustomTkinter`) que gerencia as conexões RPC e MQTT, a lógica de decisão de comunicação e a interação com o usuário.

## Pré-requisitos
Antes de começar, certifique-se de ter o **Python 3** instalado em seu sistema. É recomendado o uso de um ambiente virtual (`venv`) para gerenciar as dependências do projeto.

## Instalação e Execução

1.  **Clonar o repositório:**
    ```bash
    git clone https://github.com/pliniogoncalves/PPD-comunicador-geografico.git
    cd ppd-comunicador-geografico
    ```

2.  **Instalar as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Iniciar o Servidor:**
    Em um terminal, execute:
    ```bash
    python server_rpc.py
    ```

4.  **Iniciar os Clientes:**
    Abra um novo terminal para cada cliente que desejar iniciar e execute o comando abaixo.
    ```bash
    python client.py
    ```
    - Uma janela de login aparecerá.
    - Preencha os campos com os dados do usuário (Nome, Latitude, Longitude, Raio) e clique em "Conectar".

    **Exemplos de dados para teste:**

    -   **Usuário 1:**
        -   Nome: `Alice`
        -   Latitude: `-3.74`
        -   Longitude: `-38.52`
        -   Raio: `20`
    -   **Usuário 2:**
        -   Nome: `Beto`
        -   Latitude: `-3.85`
        -   Longitude: `-38.62`
        -   Raio: `10`
    -   **Usuário 3:**
        -   Nome: `Carlos`
        -   Latitude: `-23.55`
        -   Longitude: `-46.63`
        -   Raio: `100`