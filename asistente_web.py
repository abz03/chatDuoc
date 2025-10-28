from flask import Flask, request, jsonify, render_template
from datetime import datetime
import pytz
import os
import re
import requests

app = Flask(__name__)

# =========================
#   CONFIGURACIÓN IA HF
# =========================
# Serverless Inference API (gratis con límites). Requiere token como VAR de entorno.
HF_TOKEN = os.getenv("HF_TOKEN")  # <-- pon esto en Render (Environment Variable)
HF_MODEL = os.getenv("HF_MODEL", "google/gemma-2-2b-it")  # modelos livianos y capaces
HF_TIMEOUT = int(os.getenv("HF_TIMEOUT", "12"))
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

# Instrucciones base para orientar respuestas (breve, útil, Chile/DUOC)
SYSTEM_PROMPT = (
    "Eres Duki Bot, asistente del Duoc UC. Responde en español de Chile, breve, claro y amable. "
    "Si no tienes un dato exacto, dilo y sugiere ir a Financiamiento, Centro Académico o Servicios Digitales. "
    "No inventes horarios ni información interna; no entregues datos personales. "
    "Respuesta de 1 a 2 frases, sin markdown."
)

# Temas sensibles para evitar palabras dañinas
SENSITIVE_PATTERNS = [
    r"horari[oa]s? exact[oa]s?",
    r"contraseñ[a|o]s?|claves?",
    r"\bRUT\b|\brut\b",
    r"\bafp\b|\bisapre\b|\bcolmena\b|\bfonasa\b",
    r"direcci[oó]n exacta|coordenadas",
]

def _looks_sensitive(user_text: str) -> bool:
    t = (user_text or "").lower()
    return any(re.search(p, t, flags=re.IGNORECASE) for p in SENSITIVE_PATTERNS)

def _safety_guard(user_text: str) -> str | None:
    if _looks_sensitive(user_text):
        return ("Prefiero no entregar datos sensibles o exactitudes que podrían ser inexactas. "
                "Consulta la intranet o acércate a la oficina correspondiente.")
    return None

def ask_hf_inference(user_text: str) -> str | None:
    """
    Llama a Hugging Face Serverless Inference API si HF_TOKEN está definido.
    Devuelve una respuesta breve o None si falla.
    """
    if not HF_TOKEN:
        return None
    try:
        # Prompt estilo chat simple (instrucciones + usuario)
        prompt = f"{SYSTEM_PROMPT}\nUsuario: {user_text}\nAsistente:"
        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 120,
                "temperature": 0.25,
                "top_p": 0.9,
                "repetition_penalty": 1.1,
                "return_full_text": False
            }
        }
        resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=HF_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            # La forma de la respuesta varía por backend; cubrimos casos comunes:
            # 1) lista con dicts {"generated_text": "..."} (text-generation)
            if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
                text = (data[0].get("generated_text") or "").strip()
            # 2) dict con "generated_text"
            elif isinstance(data, dict) and "generated_text" in data:
                text = (data.get("generated_text") or "").strip()
            # 3) otros contratos (algunos devuelven "choices" estilo OpenAI-like)
            else:
                text = ""
                if isinstance(data, dict):
                    # intenta rutas alternas
                    choices = data.get("choices")
                    if isinstance(choices, list) and choices:
                        msg = choices[0].get("message", {}).get("content", "")
                        text = (msg or "").strip()

            if text:
                # limpieza y cortafuegos de longitud
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) > 400:
                    text = text[:400].rstrip() + "..."
                return text
            return None
        # 5xx cuando el modelo se está calentando o no disponible
        return None
    except Exception:
        return None

# ==========================================
#   RESPUESTAS PREDEFINIDAS (tu flujo base)
# ==========================================
def procesar_comando(comando):
    comando = (comando or "").lower()
    salas_600 = ["601", "602", "603", "604", "605"]
    salas_500 = ["501", "502", "503", "504", "505"]
    salas_300 = ["301", "302", "303", "304", "305"]

    for sala in salas_600:
        if sala in comando:
            return f"La sala {sala} está en la sede principal en el sexto piso. Si usas el ascensor llegarás directamente."

    for sala in salas_500:
        if sala in comando:
            return f"La sala {sala} está en la sede principal en el quinto piso. Si usas el ascensor llegarás directamente."
        
    for sala in salas_300:
        if sala in comando:
            return f"La sala {sala} está en la sede Boulevard en el tercer piso. Si usas el ascensor llegarás directamente, recuerda que son preferenciales."

    if "sala 603" in comando and ("11:30" in comando or "once treinta" in comando or "a las once" in comando):
        return "En la sala 603 el día lunes tienes Habilidades de la Comunicación, desde las 11:30 hasta las 12:50 horas del medio día."

    elif "hola" in comando or "cómo estás" in comando:
        return "Hola, ¿cómo estás?"

    elif "hora" in comando:
        from_zone = pytz.timezone("America/Santiago")
        hora_chile = datetime.now(from_zone).strftime("%H:%M")
        return "La hora es " + hora_chile

    elif "nombre" in comando or "salas" in comando:
        return "Soy un asistente de voz. Puedes preguntarme por salas, ubicación o la hora."

    elif ("pagar" in comando or "matricula" in comando or "matrícula" in comando or "matriculas" in comando):
        return "Para pagos o matrículas, debes dirigirte a Financiamiento, ubicada en la sede principal de Plaza Vespucio en el quinto piso."

    elif ("modificaciones horarias" in comando or "beneficios" in comando or "becas" in comando or "gratuidad" in comando or "justificaciones" in comando):
        return "Para modificaciones horarias, beneficios estudiantiles, becas, gratuidad o presentar justificaciones, dirígete al Centro Académico en la sede principal de Plaza Vespucio, quinto piso."
    
    elif (
        ("cuenta" in comando and "duoc" in comando) or
        ("problema" in comando and "cuenta" in comando) or
        ("correo" in comando and "institucional" in comando) or
        ("correo" in comando) or
        ("cuenta" in comando and "institucional" in comando)
    ):
        return "Para problema con tu cuenta Duoc o correo, dirígete a Servicios digitales en la sede Boulevard de Plaza Vespucio, tercer piso; también puedes ir a la sede principal de Plaza Vespucio, en el quinto piso."
    
    elif ("bicicleta" in comando):
        return "Para dejar tu bicicleta en Duoc, tienes dos opciones: dirígete al bicicletero en la sede Boulevard de Plaza Vespucio en el primer piso o ve a la sede principal en el quinto piso. No olvides llevar tu candado."
   
    elif ("nombre" in comando or 
        "cómo te llamas" in comando or 
        "quién eres" in comando or 
        "qué cosas puedo preguntarte" in comando or 
        "qué sabes sobre las salas" in comando):
        return "Soy Duki Bot, tu asistente de voz. Puedes preguntarme por salas, ubicación, la hora o temas relacionados con servicios estudiantiles."
    else:
        # 1) Guardas de seguridad
        guard_msg = _safety_guard(comando)
        if guard_msg:
            return guard_msg

        # 2) Intentar IA de Hugging Face (si hay token)
        ai_answer = ask_hf_inference(comando)
        if ai_answer:
            return ai_answer

        # 3) Fallback final
        return ("No entendí el comando con precisión. Si es sobre salas, ubicación, la hora o trámites "
                "(Financiamiento, Centro Académico, Servicios Digitales), cuéntame un poco más.")

# =========================
#         RUTAS
# =========================
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/api/comando", methods=["POST"])
def comando():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"respuesta": "No se recibió ningún dato válido."}), 400

        texto_usuario = data.get("texto", "")
        respuesta = procesar_comando(texto_usuario)

        meta = {
            "engine": "rules_or_hf",
            "model": HF_MODEL,
            "hf_enabled": bool(HF_TOKEN),
        }

        return jsonify({"respuesta": respuesta, "meta": meta})
    except Exception as e:
        print(f"Error en comando: {e}")
        return jsonify({"respuesta": "Ocurrió un error en el servidor."}), 500

if __name__ == "__main__":
    print("HF_TOKEN presente:", bool(os.getenv("HF_TOKEN")))
    print("Modelo:", os.getenv("HF_MODEL"))
    print("Timeout:", os.getenv("HF_TIMEOUT"))
    print("Puerto Flask:", 5000)
    app.run(host="0.0.0.0", port=5000)
#Remiau
