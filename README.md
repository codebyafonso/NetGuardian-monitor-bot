# telegram-monitor-bot

Sistema de monitoramento de servidores e banco de dados com notificações via Telegram. Um ESP32 verifica periodicamente se os servidores estão online e envia os dados para uma API FastAPI, que também monitora o storage do MongoDB Atlas e dispara alertas no Telegram.

## Como funciona

```
ESP32
  └─ a cada 10s faz GET nos servidores
  └─ envia resultado via POST para a API
        └─ API verifica o status
              ├─ offline → notifica imediatamente no Telegram
              └─ online  → notifica 1x por hora no Telegram

API (background, a cada 1h)
  └─ conecta no MongoDB Atlas
  └─ verifica storage total do cluster
        ├─ >= 80% → alerta 🟡 no Telegram
        └─ >= 95% → alerta 🔴 no Telegram
```

## Estrutura

```
telegram-monitor-bot/
├── main.py          ← API FastAPI (sobe no Render)
├── requirements.txt
├── .env.example
└── esp32/
    └── monitor.ino  ← Código do ESP32 (Arduino IDE)
```

---

## API (Render)

### Setup local

1. Clone o repositório e crie o `.env`:
```bash
cp .env.example .env
```

2. Preencha o `.env`:
```
TELEGRAM_TOKEN=token_do_botfather
CHAT_ID=seu_chat_id

MONGO_URI=mongodb+srv://usuario:senha@cluster.mongodb.net/
MONGO_LIMIT_MB=512
MONGO_ALERT_PERCENT=80
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Rode localmente:
```bash
python -m uvicorn main:app --reload
```

### Deploy no Render

1. Suba o repositório no GitHub
2. Crie um **Web Service** no [Render](https://render.com) apontando pro repositório
3. Configure as variáveis de ambiente no painel do Render:

| Variável | Descrição |
|---|---|
| `TELEGRAM_TOKEN` | Token do bot (BotFather) |
| `CHAT_ID` | ID do chat/grupo no Telegram |
| `MONGO_URI` | Connection string do Atlas (`mongodb+srv://...`) |
| `MONGO_LIMIT_MB` | Limite total do cluster em MB (padrão: `512`) |
| `MONGO_ALERT_PERCENT` | % de uso para disparar alerta (padrão: `80`) |

4. Start command:
```
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Endpoints

### `POST /monitor`
Recebe status de servidor enviado pelo ESP32.

```json
{
  "server": "nome-do-servidor",
  "status": "online",
  "response_time": 1043
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `server` | string | Nome do servidor |
| `status` | string | `"online"` ou `"offline"` |
| `response_time` | int | Tempo de resposta em ms (use `0` se offline) |

### `GET /mongo-status`
Retorna o uso atual de storage do cluster MongoDB Atlas.

```json
{
  "usado_mb": 210.5,
  "livre_mb": 301.5,
  "total_mb": 512.0,
  "percent": 41.1,
  "bancos": [
    { "banco": "supportflow", "tamanho_mb": 130.2 },
    { "banco": "pppoeye", "tamanho_mb": 80.3 }
  ]
}
```

---

## Notificações no Telegram

**Servidor offline** (imediato):
```
🚨 SERVIDOR OFFLINE

Servidor: supportflow
Tempo resposta: 0 ms
```

**Servidor online** (1x por hora):
```
✅ SERVIDOR ONLINE

Servidor: supportflow
Tempo resposta: 1023 ms
```

**Storage MongoDB** (quando >= 80%):
```
🟡 ALERTA: MongoDB Atlas

Uso total: 82.3%
Usado: 421.4 MB
Livre: 90.6 MB
Limite: 512 MB

Por banco:
  • supportflow: 310.2 MB
  • pppoeye: 111.2 MB
```

---

## ESP32 (Arduino IDE)

### Configuração

Abra `esp32/monitor.ino` e edite as variáveis no topo:

```cpp
const char* ssid     = "SEU_WIFI";
const char* password = "SUA_SENHA";
const char* apiUrl   = "https://SUA_API.onrender.com/monitor";

String urls[] = {
  "https://servidor1.com",
  "https://servidor2.com"
};
String serverNames[] = {
  "servidor1",
  "servidor2"
};
```

### Bibliotecas necessárias (Arduino IDE)

- `WiFi.h` — nativa do ESP32
- `HTTPClient.h` — nativa do ESP32

### Comportamento

- Verifica todos os servidores **a cada 10 segundos**
- Reconecta automaticamente ao WiFi se a conexão cair
- Reinicia automaticamente após **10 minutos** sem atividade (watchdog)

---

## Como obter o CHAT_ID

1. Abra o Telegram e procure `@userinfobot`
2. Mande `/start` — ele responde com seu ID

Para grupos: adicione o bot ao grupo, envie uma mensagem e acesse:
```
https://api.telegram.org/bot<TOKEN>/getUpdates
```
O ID do grupo começa com `-100`.
