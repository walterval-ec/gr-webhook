"""
webhook.py
==========
Webhook para GR Asesoría Contable — Nivel 1
Recibe mensajes entrantes de clientes al +593 98 691 2956
y los reenvía al número personal de Laura (+593 99 607 8461)

Autor: GR Asesoría Contable
"""

import os
import json
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ─── CREDENCIALES ───────────────────────────────────────────
ACCESS_TOKEN     = os.getenv("META_ACCESS_TOKEN")
PHONE_NUMBER_ID  = os.getenv("META_PHONE_NUMBER_ID")
VERIFY_TOKEN     = os.getenv("WEBHOOK_VERIFY_TOKEN", "gr_asesoria_webhook_2026")
NUMERO_LAURA     = os.getenv("NUMERO_REENVIO", "593996078461")  # número de Laura sin +
APP_SECRET       = os.getenv("META_APP_SECRET", "")
API_VERSION      = os.getenv("META_API_VERSION", "v19.0")

API_URL = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

# ─── VERIFICACIÓN DEL WEBHOOK (GET) ─────────────────────────
@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    """Meta llama a este endpoint para verificar el webhook."""
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print(f"✅ Webhook verificado correctamente")
        return challenge, 200
    else:
        print(f"❌ Token inválido: {token}")
        return "Token inválido", 403


# ─── RECEPCIÓN DE MENSAJES (POST) ───────────────────────────
@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    """Recibe mensajes entrantes de clientes y los reenvía a Laura."""
    data = request.get_json()

    try:
        entry    = data["entry"][0]
        changes  = entry["changes"][0]
        value    = changes["value"]

        # Solo procesar si hay mensajes
        if "messages" not in value:
            return jsonify({"status": "ok"}), 200

        mensaje  = value["messages"][0]
        contacto = value["contacts"][0]

        # Extraer datos del cliente
        numero_cliente = mensaje["from"]
        nombre_cliente = contacto["profile"]["name"]
        tipo_mensaje   = mensaje["type"]

        # Extraer contenido según tipo
        if tipo_mensaje == "text":
            contenido = mensaje["text"]["body"]
        elif tipo_mensaje == "image":
            contenido = "📷 [El cliente envió una imagen]"
        elif tipo_mensaje == "audio":
            contenido = "🎵 [El cliente envió un audio]"
        elif tipo_mensaje == "document":
            contenido = "📄 [El cliente envió un documento]"
        elif tipo_mensaje == "location":
            loc = mensaje["location"]
            contenido = f"📍 [El cliente envió su ubicación: {loc.get('latitude')}, {loc.get('longitude')}]"
        else:
            contenido = f"[Mensaje de tipo: {tipo_mensaje}]"

        # Formatear número para mostrar
        numero_formato = f"+{numero_cliente}"

        # Construir mensaje de reenvío para Laura
        texto_reenvio = (
            f"📨 *Mensaje entrante — GR Asesoría Contable*\n\n"
            f"👤 *Cliente:* {nombre_cliente}\n"
            f"📱 *Número:* {numero_formato}\n"
            f"💬 *Mensaje:*\n{contenido}\n\n"
            f"_Para responder, escribe directamente a {numero_formato}_"
        )

        # Reenviar a Laura
        reenviar_a_laura(texto_reenvio)

        print(f"📩 Mensaje de {nombre_cliente} ({numero_formato}) reenviado a Laura")
        return jsonify({"status": "ok"}), 200

    except (KeyError, IndexError) as e:
        # No es un mensaje de texto — puede ser status update, etc.
        print(f"ℹ️ Evento no procesado: {e}")
        return jsonify({"status": "ok"}), 200


# ─── FUNCIÓN DE REENVÍO ──────────────────────────────────────
def reenviar_a_laura(texto: str) -> bool:
    """Envía el mensaje de reenvío al número de Laura."""
    payload = {
        "messaging_product": "whatsapp",
        "to": NUMERO_LAURA,
        "type": "text",
        "text": {"body": texto}
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)
        data = resp.json()

        if resp.status_code == 200 and "messages" in data:
            print(f"✅ Reenvío exitoso a Laura ({NUMERO_LAURA})")
            return True
        else:
            print(f"❌ Error en reenvío: {data}")
            return False

    except Exception as e:
        print(f"❌ Excepción en reenvío: {e}")
        return False


# ─── HEALTH CHECK ────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "running",
        "servicio": "GR Asesoría Contable — Webhook Nivel 1",
        "version": "1.0"
    }), 200


# ─── PUNTO DE ENTRADA ────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"🚀 Webhook iniciando en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
