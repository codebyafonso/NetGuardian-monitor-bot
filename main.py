import os
import logging
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException

logging.basicConfig(level=logging.INFO)
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Monitor Bot Telegram")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ONLINE_INTERVAL = timedelta(hours=1)

# Armazena o último envio de "online" por servidor
ultimo_online: dict[str, datetime] = {}


class StatusPayload(BaseModel):
    server: str
    status: str
    response_time: int


def enviar_telegram(msg: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logging.error("TELEGRAM_TOKEN ou CHAT_ID não configurados.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
    }
    try:
        response = requests.post(url, json=payload, timeout=20)
        if not response.ok:
            logging.error(f"Telegram recusou a mensagem: {response.text}")
    except requests.exceptions.Timeout:
        logging.warning("Timeout ao conectar no Telegram. Mensagem não enviada.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao enviar para o Telegram: {e}")


@app.post("/monitor")
def receber_status(data: StatusPayload):
    servidor = data.server
    status = data.status
    tempo = data.response_time
    enviado = False

    if status == "offline":
        mensagem = (
            f"🚨 <b>SERVIDOR OFFLINE</b>\n\n"
            f"Servidor: <code>{servidor}</code>\n"
            f"Tempo resposta: <b>{tempo} ms</b>"
        )
        enviar_telegram(mensagem)
        enviado = True

    elif status == "online":
        agora = datetime.now()
        ultimo = ultimo_online.get(servidor)

        if ultimo is None or agora - ultimo >= ONLINE_INTERVAL:
            mensagem = (
                f"✅ <b>SERVIDOR ONLINE</b>\n\n"
                f"Servidor: <code>{servidor}</code>\n"
                f"Tempo resposta: <b>{tempo} ms</b>"
            )
            enviar_telegram(mensagem)
            ultimo_online[servidor] = agora
            enviado = True

    else:
        raise HTTPException(status_code=400, detail=f"Status desconhecido: '{status}'")

    return {"status": "ok", "servidor": servidor, "enviado": enviado}


@app.api_route("/", methods=["GET", "HEAD"])
def health():
    return {"status": "online", "bot": "Monitor Telegram"}
