# app.py
# ------------------------------------------------------------
# Backend principal de Duki Bot (Flask)
# - Orquesta el flujo:
#     1) Reglas predefinidas (reglas.procesar_reglas)
#     2) IA (ia.responder_ia) si no hay match
#     3) Fallback seguro si nada responde
# - Endpoints:
#     GET  /             -> index.html
#     POST /api/comando  -> procesa texto del usuario
#     GET  /health       -> healthcheck simple (sin llamar a IA)
# ------------------------------------------------------------

from flask import Flask, request, jsonify, render_template
import os
import time

# Módulos locales
import reglas
import ia  # usa responder_ia(user_text) y helpers de logs

app = Flask(__name__)

# Mensaje de fallback si reglas e IA no responden
FALLBACK_MSG = (
    "No entendí el comando con precisión. Si es sobre salas, ubicación, la hora "
    "o trámites (Financiamiento, Centro Académico, Servicios Digitales), "
    "cuéntame un poco más."
)

# Limitar tamaño de entrada para evitar abusos/ruidos
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "600"))


@app.route("/", methods=["GET"])
def index():
    """Entrega el frontend básico."""
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    """
    Healthcheck liviano (no llama a la IA).
    Útil para saber si el contenedor y variables mínimas están OK.
    """
    return jsonify({
        "ok": True,
        "hf_enabled": bool(ia.HF_TOKEN),
        "model": ia.HF_MODEL,   # ← ahora por defecto: meta-llama/Llama-3.1-8B-Instruct:novita
        "timeout": ia.HF_TIMEOUT
    }), 200


@app.route("/api/comando", methods=["POST"])
def comando():
    """
    Flujo:
    - Intenta responder con reglas predefinidas (rápido, determinista).
    - Si no hay coincidencia, intenta IA (ia.responder_ia).
    - Si la IA falla o no responde, retorna fallback seguro.
    """
    try:
        # Validación del cuerpo JSON
        if not request.is_json:
            return jsonify({"respuesta": "El contenido debe ser JSON."}), 400

        data = request.get_json(silent=True)
        if not data or "texto" not in data:
            return jsonify({"respuesta": "Falta el campo 'texto' en el JSON."}), 400

        # Normalización del texto
        texto_usuario = (data.get("texto") or "").strip()

        if not texto_usuario:
            return jsonify({"respuesta": "El texto está vacío."}), 400

        # Cap de longitud (para no sobrecargar ni enviar ruido)
        if len(texto_usuario) > MAX_INPUT_CHARS:
            texto_usuario = texto_usuario[:MAX_INPUT_CHARS].rstrip()
            ia.log_debug(f"[API] Texto recortado a {MAX_INPUT_CHARS} caracteres.")

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
        # Log al stdout para visibilidad en contenedores
        print(f"[SERVER] Error en /api/comando: {e}")
        return jsonify({"respuesta": "Ocurrió un error en el servidor."}), 500


if __name__ == "__main__":
    # Logs útiles al iniciar
    print("HF_TOKEN presente:", bool(os.getenv("HF_TOKEN")))
    print("Modelo HF:", os.getenv("HF_MODEL", ia.HF_MODEL))
    print("Timeout HF:", os.getenv("HF_TIMEOUT", ia.HF_TIMEOUT))
    print("DEBUG_IA:", os.getenv("DEBUG_IA", "0"))
    print("MAX_INPUT_CHARS:", MAX_INPUT_CHARS)
    print("Puerto Flask:", 5000)

    # Inicia servidor
    app.run(host="0.0.0.0", port=5000)