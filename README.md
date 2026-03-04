# Monitor Bot Telegram

API FastAPI que recebe status de servidores (ESP32 ou qualquer cliente HTTP) e envia notificações no Telegram.

## Setup

### 1. Instalar dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente
```bash
cp .env.example .env
```
Edite o `.env` com seus dados:
- `TELEGRAM_TOKEN` → Token do bot (obtido pelo @BotFather)
- `CHAT_ID` → ID do chat/grupo onde as mensagens serão enviadas

> Para descobrir o CHAT_ID, envie uma mensagem pro bot e acesse:
> `https://api.telegram.org/bot<TOKEN>/getUpdates`

### 3. Rodar localmente
```bash
uvicorn main:app --reload
```

### 4. Payload esperado (POST /monitor)
```json
{
  "server": "supportflow",
  "status": "online",
  "response_time": 1043
}
```
- `status`: `"online"` ou `"offline"`
- `response_time`: tempo em ms (use `0` quando offline)

### 5. Exemplo de mensagem recebida no Telegram
```
🚨 SERVIDOR OFFLINE

Servidor: supportflow
Tempo resposta: 0 ms
```

## Deploy no Render
1. Faça push do projeto no GitHub
2. Crie um novo Web Service no Render apontando pro repositório
3. Configure as variáveis de ambiente (`TELEGRAM_TOKEN` e `CHAT_ID`) no painel do Render
4. Start command: `uvicorn main:app --host 0.0.0.0 --port 10000`
