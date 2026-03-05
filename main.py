import os
import asyncio
import logging
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)
load_dotenv()

app = FastAPI(title="Monitor Bot Telegram")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_LIMIT_MB = float(os.getenv("MONGO_LIMIT_MB", "512"))
MONGO_ALERT_PERCENT = float(os.getenv("MONGO_ALERT_PERCENT", "80"))

ONLINE_INTERVAL = timedelta(hours=1)
MONGO_CHECK_INTERVAL = 3600  # 1 hora em segundos

ultimo_online: dict[str, datetime] = {}


# ---------------- TELEGRAM ----------------

def enviar_telegram(msg: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logging.error("TELEGRAM_TOKEN ou CHAT_ID não configurados.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=20)
        if not response.ok:
            logging.error(f"Telegram recusou a mensagem: {response.text}")
    except requests.exceptions.Timeout:
        logging.warning("Timeout ao conectar no Telegram. Mensagem não enviada.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao enviar para o Telegram: {e}")


# ---------------- MONGODB ----------------

def checar_mongo() -> dict:
    if not MONGO_URI:
        logging.error("MONGO_URI não configurado.")
        return {}

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
        admin = client["admin"]
        result = admin.command("listDatabases", nameOnly=False)
        client.close()

        total_bytes = result.get("totalSize", 0)
        usado_mb = round(total_bytes / (1024 * 1024), 2)
        total_mb = MONGO_LIMIT_MB
        percent = round((usado_mb / total_mb) * 100, 1)
        livre_mb = round(total_mb - usado_mb, 2)

        bancos = [
            {
                "banco": db["name"],
                "tamanho_mb": round(db["sizeOnDisk"] / (1024 * 1024), 2),
            }
            for db in result.get("databases", [])
            if db["name"] not in ("admin", "local", "config")
        ]

        return {
            "usado_mb": usado_mb,
            "livre_mb": livre_mb,
            "total_mb": total_mb,
            "percent": percent,
            "bancos": bancos,
        }
    except Exception as e:
        logging.error(f"Erro ao conectar no MongoDB: {e}")
        return {}


async def loop_mongo():
    await asyncio.sleep(10)  # aguarda a API subir antes da primeira checagem
    while True:
        logging.info("Verificando storage do MongoDB...")
        info = checar_mongo()

        if info:
            percent = info["percent"]
            if percent >= MONGO_ALERT_PERCENT:
                emoji = "🔴" if percent >= 95 else "🟡"
                detalhe = "\n".join(
                    f"  • {b['banco']}: {b['tamanho_mb']} MB"
                    for b in info.get("bancos", [])
                )
                mensagem = (
                    f"{emoji} <b>ALERTA: MongoDB Atlas</b>\n\n"
                    f"Uso total: <b>{percent}%</b>\n"
                    f"Usado: <b>{info['usado_mb']} MB</b>\n"
                    f"Livre: <b>{info['livre_mb']} MB</b>\n"
                    f"Limite: <b>{info['total_mb']} MB</b>"
                )
                if detalhe:
                    mensagem += f"\n\n<b>Por banco:</b>\n{detalhe}"
                enviar_telegram(mensagem)
                logging.warning(f"MongoDB em {percent}% — alerta enviado.")
            else:
                logging.info(f"MongoDB OK: {percent}% usado ({info['usado_mb']} MB de {info['total_mb']} MB)")

        await asyncio.sleep(MONGO_CHECK_INTERVAL)


@app.on_event("startup")
async def startup():
    asyncio.create_task(loop_mongo())


# ---------------- ENDPOINTS ----------------

class StatusPayload(BaseModel):
    server: str
    status: str
    response_time: int


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


@app.get("/mongo-status")
def mongo_status():
    info = checar_mongo()
    if not info:
        raise HTTPException(status_code=503, detail="Não foi possível conectar ao MongoDB.")
    return info


@app.api_route("/", methods=["GET", "HEAD"])
def health():
    return {"status": "online", "bot": "Monitor Telegram"}
