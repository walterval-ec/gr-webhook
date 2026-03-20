"""
webhook.py
==========
Webhook para GR Asesoría Contable — Nivel 1
Recibe mensajes entrantes de clientes al +593 98 691 2956
y los reenvía al número personal de Laura (+593 99 607 8461)
usando template aprobado (sin restricción de ventana 24h).

Autor: GR Asesoría Contable
"""

import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ─── CREDENCIALES ───────────────────────────────────────────
ACCESS_TOKEN        = os.getenv("META_ACCESS_TOKEN")
PHONE_NUMBER_ID     = os.getenv("META_PHONE_NUMBER_ID")
VERIFY_TOKEN        = os.getenv("WEBHOOK_VERIFY_TOKEN", "gr_asesoria_webhook_2026")
NUMERO_LAURA        = os.getenv("NUMERO_REENVIO", "593996078461")
API_VERSION         = os.getenv("META_API_VERSION", "v19.0")
TEMPLATE_REENVIO    = os.getenv("TEMPLATE_REENVIO", "gr_asesoria_reenvio")
TEMPLATE_LANGUAGE   = os.getenv("TEMPLATE_LANGUAGE", "es")

API_URL = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


# ─── VERIFICACIÓN DEL WEBHOOK (GET) ─────────────────────────
@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verificado correctamente")
        return challenge, 200
    else:
        print(f"❌ Token inválido: {token}")
        return "Token inválido", 403


# ─── RECEPCIÓN DE MENSAJES (POST) ───────────────────────────
@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    data = request.get_json()

    try:
        entry   = data["entry"][0]
        changes = entry["changes"][0]
        value   = changes["value"]

        # Solo procesar mensajes entrantes
        if "messages" not in value:
            return jsonify({"status": "ok"}), 200

        mensaje  = value["messages"][0]
        contacto = value["contacts"][0]

        numero_cliente = mensaje["from"]
        nombre_cliente = contacto["profile"]["name"]
        tipo_mensaje   = mensaje["type"]

        # Extraer contenido según tipo
        if tipo_mensaje == "text":
            contenido = mensaje["text"]["body"]
        elif tipo_mensaje == "image":
            contenido = "📷 El cliente envió una imagen"
        elif tipo_mensaje == "audio":
            contenido = "🎵 El cliente envió un audio"
        elif tipo_mensaje == "document":
            contenido = "📄 El cliente envió un documento"
        elif tipo_mensaje == "location":
            loc = mensaje["location"]
            contenido = f"📍 Ubicación: {loc.get('latitude')}, {loc.get('longitude')}"
        else:
            contenido = f"Mensaje tipo: {tipo_mensaje}"

        numero_formato = f"+{numero_cliente}"

        # Reenviar a Laura via template
        exito = reenviar_a_laura(nombre_cliente, numero_formato, contenido)

        if exito:
            print(f"📩 Reenviado: {nombre_cliente} ({numero_formato})")
        else:
            print(f"❌ Fallo reenvío: {nombre_cliente} ({numero_formato})")

        return jsonify({"status": "ok"}), 200

    except (KeyError, IndexError) as e:
        print(f"ℹ️ Evento no procesado: {e}")
        return jsonify({"status": "ok"}), 200


# ─── FUNCIÓN DE REENVÍO VIA TEMPLATE ────────────────────────
def reenviar_a_laura(nombre: str, numero: str, contenido: str) -> bool:
    """
    Reenvía usando template aprobado — sin restricción de ventana 24h.
    Template: gr_asesoria_reenvio
    Variables: {{1}}=nombre, {{2}}=numero, {{3}}=contenido
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": NUMERO_LAURA,
        "type": "template",
        "template": {
            "name": TEMPLATE_REENVIO,
            "language": {"code": TEMPLATE_LANGUAGE},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": nombre},
                        {"type": "text", "text": numero},
                        {"type": "text", "text": contenido},
                    ]
                }
            ]
        }
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)
        data = resp.json()

        if resp.status_code == 200 and "messages" in data:
            print(f"✅ Reenvío exitoso a Laura")
            return True
        else:
            print(f"❌ Error reenvío: {data}")
            return False

    except Exception as e:
        print(f"❌ Excepción: {e}")
        return False


# ─── HEALTH CHECK ────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "running",
        "servicio": "GR Asesoría Contable — Webhook Nivel 1",
        "version": "1.1"
    }), 200


# ─── PUNTO DE ENTRADA ────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"🚀 Webhook iniciando en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
