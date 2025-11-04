# ia.py
# ------------------------------------------------------------
# Capa de IA (Hugging Face Inference Router)
# - Seguridad: guard para temas sensibles.
# - Conexión: router nuevo (v1/chat/completions).
# - Logs: activables con DEBUG_IA=1.
# - Reintento: 1 retry si el modelo está en warming-up (503).
# - Función pública:
#     responder_ia(texto) -> str | None
# ------------------------------------------------------------

import os
import re
import time
import json
import requests

# ============ Configuración ============

HF_TOKEN = os.getenv("HF_TOKEN")  # ej: hf_xxxxxxxxxxxxxxxxx
HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai")
HF_TIMEOUT = int(os.getenv("HF_TIMEOUT", "12"))
DEBUG_IA = os.getenv("DEBUG_IA", "0") == "1"

HF_API_URL = "https://router.huggingface.co/v1/chat/completions"

# Mensaje de sistema para orientar tono/alcance
SYSTEM_PROMPT = (
    "Eres Duki Bot, asistente del Duoc UC. Responde en español de Chile, breve, claro y amable. "
    "Si no tienes un dato exacto, dilo y sugiere ir a Financiamiento, Centro Académico o Servicios Digitales. "
    "No inventes horarios ni información interna; no entregues datos personales. "
    "Respuesta de 1 a 2 frases, sin markdown."
)

# Patrones de contenido sensible (bloqueo simple)
SENSITIVE_PATTERNS = [
    r"horari[oa]s? exact[oa]s?",
    r"contraseñ[a|o]s?|claves?",
    r"\bRUT\b|\brut\b",
    r"\bafp\b|\bisapre\b|\bcolmena\b|\bfonasa\b",
    r"direcci[oó]n exacta|coordenadas",
]

# ============ Utilidades ============

def log_debug(msg: str):
    if DEBUG_IA:
        print(msg)

def _looks_sensitive(user_text: str) -> bool:
    t = (user_text or "").lower()
    return any(re.search(p, t, flags=re.IGNORECASE) for p in SENSITIVE_PATTERNS)

def _safety_guard(user_text: str) -> str | None:
    """Regresa un mensaje seguro si detecta contenido sensible."""
    if _looks_sensitive(user_text):
        return ("Prefiero no entregar datos sensibles o exactitudes que podrían ser inexactas. "
                "Consulta la intranet o acércate a la oficina correspondiente.")
    return None

def _build_payload(user_text: str) -> dict:
    """
    Construye el payload compatible con /v1/chat/completions (estilo OpenAI).
    Usa roles 'system' y 'user' por separado (mejor que incrustar el system dentro del user).
    """
    return {
        "model": HF_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        # Puedes ajustar estos parámetros si quieres:
        "temperature": 0.2,
        "max_tokens": 256,
    }

def _extract_text_from_response(resp_json: dict) -> str:
    """
    Extrae el texto del formato tipo OpenAI:
    { choices: [ { message: { content: "..." } } ] }
    """
    try:
        return (
            resp_json.get("choices", [{}])[0]
                     .get("message", {})
                     .get("content", "")
        ).strip()
    except Exception:
        return ""

# ============ API pública ============

def responder_ia(user_text: str) -> str | None:
    """
    Flujo:
    1) Guard de seguridad (bloquea consultas sensibles).
    2) Llamada al router de Hugging Face (con 1 reintento si 503).
    3) Retorna texto (1–2 frases) o None si no hubo respuesta.
    """
    # 1) Guard
    guard_msg = _safety_guard(user_text)
    if guard_msg:
        log_debug("[IA-DEBUG] Guard activado → contenido sensible.")
        return guard_msg

    if not HF_TOKEN:
        log_debug("[IA-DEBUG] HF_TOKEN ausente → no se llama IA.")
        return None

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = _build_payload(user_text)

    # 2) Intento + 1 reintento si 503
    for attempt in (1, 2):
        t0 = time.perf_counter()
        try:
            log_debug(json.dumps({
                "ia_call": "start",
                "attempt": attempt,
                "url": HF_API_URL,
                "model": HF_MODEL,
                "timeout": HF_TIMEOUT
            }, ensure_ascii=False))

            resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=HF_TIMEOUT)
            elapsed_ms = int((time.perf_counter() - t0) * 1000)

            # Log resumen de respuesta (sin saturar consola)
            preview = resp.text[:300].replace("\n", " ")
            log_debug(json.dumps({
                "ia_call": "end",
                "attempt": attempt,
                "status": resp.status_code,
                "elapsed_ms": elapsed_ms,
                "body_preview": preview
            }, ensure_ascii=False))

            if resp.status_code == 200:
                data = resp.json()
                text = _extract_text_from_response(data)

                if text:
                    # Limpieza básica y acotar longitud
                    text = re.sub(r"\s+", " ", text)
                    if len(text) > 400:
                        text = text[:400].rstrip() + "..."
                    return text

                log_debug("[IA-DEBUG] 200 OK pero sin texto generado.")
                return None

            # Si el modelo está "warming up", intentar una vez más
            if resp.status_code == 503 and attempt == 1:
                time.sleep(2.5)
                continue

            # Otros códigos → no reintentar
            return None

        except Exception as e:
            log_debug(json.dumps({
                "ia_call": "exception",
                "attempt": attempt,
                "error": repr(e)
            }, ensure_ascii=False))
            if attempt == 1:
                time.sleep(1.5)
                continue
            return None

    return None