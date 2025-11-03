# app.py
# ------------------------------------------------------------
# Backend principal de Duki Bot (Flask)
# - Orquesta el flujo:
#     1) Reglas predefinidas (reglas.procesar_reglas)
#     2) IA (ia.responder_ia) si no hay match
#     3) Fallback seguro si nada responde
# - Expone endpoints:
#     GET  /              -> index.html
#     POST /api/comando   -> procesa texto del usuario
#     GET  /api/ia-status -> estado/latencia del proveedor IA
# ------------------------------------------------------------

from flask import Flask, request, jsonify, render_template
from datetime import datetime
import pytz
import os
import time

# Módulos locales
import reglas
import ia

app = Flask(__name__)

# Mensaje de fallback si reglas e IA no responden
FALLBACK_MSG = ("No entendí el comando con precisión. Si es sobre salas, ubicación, la hora "
                "o trámites (Financiamiento, Centro Académico, Servicios Digitales), "
                "cuéntame un poco más.")

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/api/comando", methods=["POST"])
def comando():
    """
    Flujo:
    - Intenta responder con reglas predefinidas (rápido, determinista).
    - Si no hay coincidencia, intenta IA.
    - Si la IA falla o no responde, vuelve a fallback seguro.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"respuesta": "No se recibió ningún dato válido."}), 400

        texto_usuario = (data.get("texto") or "").strip()
        started = time.perf_counter()

        # 1) Reglas
        respuesta = reglas.procesar_reglas(texto_usuario)
        engine = "rules" if respuesta else None

        # 2) IA (solo si no hubo match de reglas)
        if not respuesta:
            ia.log_debug("[IA-DEBUG] Sin match de reglas → intento IA")
            respuesta = ia.responder_ia(texto_usuario)
            engine = "ia" if respuesta else "fallback"

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        return jsonify({
            "respuesta": respuesta or FALLBACK_MSG,
            "meta": {
                "engine": engine,
                "model": ia.HF_MODEL,
                "hf_enabled": bool(ia.HF_TOKEN),
                "elapsed_ms": elapsed_ms
            }
        }), 200

    except Exception as e:
        print(f"[SERVER] Error en /api/comando: {e}")
        return jsonify({"respuesta": "Ocurrió un error en el servidor."}), 500


@app.route("/api/ia-status", methods=["GET"])
def ia_status():
    """
    Endpoint de salud para validar conectividad y latencia de la IA.
    No afecta el flujo normal.
    """
    try:
        status = ia.ping_ia()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({"ok": False, "error": repr(e)}), 200


if __name__ == "__main__":
    # Logs útiles al iniciar
    print("HF_TOKEN presente:", bool(os.getenv("HF_TOKEN")))
    print("Modelo HF:", os.getenv("HF_MODEL"))
    print("Timeout HF:", os.getenv("HF_TIMEOUT"))
    print("DEBUG_IA:", os.getenv("DEBUG_IA"))
    print("Puerto Flask:", 5000)
    app.run(host="0.0.0.0", port=5000)