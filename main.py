import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Monitor Bot Telegram")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


class StatusPayload(BaseModel):
    server: str
    status: str
    response_time: int


def enviar_telegram(msg: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise HTTPException(status_code=500, detail="TELEGRAM_TOKEN ou CHAT_ID não configurados.")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
    }
    response = requests.post(url, json=payload, timeout=10)

    if not response.ok:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao enviar mensagem no Telegram: {response.text}",
        )


@app.post("/monitor")
def receber_status(data: StatusPayload):
    servidor = data.server
    status = data.status
    tempo = data.response_time

    if status == "offline":
        mensagem = (
            f"🚨 <b>SERVIDOR OFFLINE</b>\n\n"
            f"Servidor: <code>{servidor}</code>\n"
            f"Tempo resposta: <b>{tempo} ms</b>"
        )
    elif status == "online":
        mensagem = (
            f"✅ <b>SERVIDOR ONLINE</b>\n\n"
            f"Servidor: <code>{servidor}</code>\n"
            f"Tempo resposta: <b>{tempo} ms</b>"
        )
    else:
        raise HTTPException(status_code=400, detail=f"Status desconhecido: '{status}'")

    enviar_telegram(mensagem)
    return {"status": "ok", "servidor": servidor, "enviado": True}


@app.get("/")
def health():
    return {"status": "online", "bot": "Monitor Telegram"}
