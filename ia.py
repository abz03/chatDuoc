# ia.py
# ------------------------------------------------------------
# Capa de IA (Hugging Face Inference Providers Router)
# - Seguridad: guard para temas sensibles.
# - Conexión: router nuevo (no el endpoint deprecado).
# - Logs: activables con DEBUG_IA=1.
# - Reintento: 1 retry si el modelo está en warming-up (503).
# - Telemetría: dict LAST con info de la última llamada IA.
# - API pública:
#     responder_ia(texto) -> str | None
#     ping_ia() -> dict (para /api/ia-status)
# ------------------------------------------------------------

import os
import re
import time
import json
import requests

# Flags y configuración desde entorno
HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "google/gemma-2-2b-it")
HF_TIMEOUT = int(os.getenv("HF_TIMEOUT", "12"))
DEBUG_IA = os.getenv("DEBUG_IA", "0") == "1"

# NUEVO router (reemplaza al endpoint deprecado)
HF_API_URL = f"https://router.huggingface.co/hf-inference/{HF_MODEL}"

# Prompt de sistema para orientar el tono y límites
SYSTEM_PROMPT = (
    "Eres Duki Bot, asistente del Duoc UC. Responde en español de Chile, breve, claro y amable. "
    "Si no tienes un dato exacto, dilo y sugiere ir a Financiamiento, Centro Académico o Servicios Digitales. "
    "No inventes horarios ni información interna; no entregues datos personales. "
    "Respuesta de 1 a 2 frases, sin markdown."
)

# Patrones sensibles (bloquear invenciones peligrosas)
SENSITIVE_PATTERNS = [
    r"horari[oa]s? exact[oa]s?",
    r"contraseñ[a|o]s?|claves?",
    r"\bRUT\b|\brut\b",
    r"\bafp\b|\bisapre\b|\bcolmena\b|\bfonasa\b",
    r"direcci[oó]n exacta|coordenadas",
]

# Telemetría de la última llamada IA
LAST = {
    "called": False,
    "attempt": 0,
    "status": None,
    "elapsed_ms": None,
    "url": None,
    "error": None,
    "body_preview": None,
    "used_model": None,
}

def log_debug(msg: str):
    if DEBUG_IA:
        print(msg)

def _looks_sensitive(user_text: str) -> bool:
    t = (user_text or "").lower()
    return any(re.search(p, t, flags=re.IGNORECASE) for p in SENSITIVE_PATTERNS)

def _safety_guard(user_text: str) -> str | None:
    if _looks_sensitive(user_text):
        return ("Prefiero no entregar datos sensibles o exactitudes que podrían ser inexactas. "
                "Consulta la intranet o acércate a la oficina correspondiente.")
    return None

def responder_ia(user_text: str) -> str | None:
    """
    1) Guard de seguridad (devuelve msg seguro si corresponde).
    2) Llama al router de Hugging Face (con 1 reintento si 503).
    3) Devuelve texto breve o None si no hubo respuesta.
    """
    guard_msg = _safety_guard(user_text)
    if guard_msg:
        LAST.update({
            "called": False, "attempt": 0, "status": None, "elapsed_ms": None,
            "url": HF_API_URL, "error": "guard_blocked",
            "body_preview": None, "used_model": HF_MODEL
        })
        log_debug("[IA-DEBUG] Guard activado → contenido sensible.")
        return guard_msg

    if not HF_TOKEN:
        LAST.update({
            "called": False, "attempt": 0, "status": None, "elapsed_ms": None,
            "url": HF_API_URL, "error": "no_token",
            "body_preview": None, "used_model": HF_MODEL
        })
        log_debug("[IA-DEBUG] HF_TOKEN ausente → no se llama IA.")
        return None

    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    prompt = f"{SYSTEM_PROMPT}\nUsuario: {user_text}\nAsistente:"
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

    for attempt in (1, 2):  # 1 intento + 1 retry si 503
        t0 = time.perf_counter()
        try:
            resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=HF_TIMEOUT)
            elapsed = int((time.perf_counter() - t0) * 1000)
            preview = resp.text[:300].replace("\n", " ")

            LAST.update({
                "called": True, "attempt": attempt, "status": resp.status_code,
                "elapsed_ms": elapsed, "url": HF_API_URL, "error": None,
                "body_preview": preview, "used_model": HF_MODEL
            })

            if resp.status_code == 200:
                data = resp.json()
                text = ""
                if isinstance(data, list) and data and "generated_text" in data[0]:
                    text = (data[0]["generated_text"] or "").strip()
                elif isinstance(data, dict) and "generated_text" in data:
                    text = (data["generated_text"] or "").strip()
                elif isinstance(data, dict):
                    text = (data.get("choices", [{}])[0]
                                .get("message", {})
                                .get("content", "") or "").strip()

                if text:
                    text = re.sub(r"\s+", " ", text)
                    if len(text) > 400:
                        text = text[:400].rstrip() + "..."
                    return text

                # 200 sin texto generado
                return None

            if resp.status_code == 503 and attempt == 1:
                time.sleep(2.5)
                continue  # reintenta una vez

            # otros códigos → sin reintento extra
            return None

        except Exception as e:
            LAST.update({
                "called": True, "attempt": attempt, "status": None,
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                "url": HF_API_URL, "error": repr(e),
                "body_preview": None, "used_model": HF_MODEL
            })
            if attempt == 1:
                time.sleep(1.5)
                continue
            return None

    return None


def ping_ia() -> dict:
    """
    Healthcheck: ping rápido al router.
    Devuelve ok/status/elapsed/model/url/preview.
    """
    try:
        if not HF_TOKEN:
            return {"ok": False, "reason": "HF_TOKEN missing", "hf_enabled": False}

        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        payload = {"inputs": "ping", "parameters": {"max_new_tokens": 5, "temperature": 0.01, "return_full_text": False}}

        t0 = time.perf_counter()
        r = requests.post(HF_API_URL, headers=headers, json=payload, timeout=HF_TIMEOUT)
        elapsed = int((time.perf_counter() - t0) * 1000)

        return {
            "ok": r.status_code == 200,
            "status": r.status_code,
            "elapsed_ms": elapsed,
            "model": HF_MODEL,
            "hf_enabled": True,
            "url": HF_API_URL,
            "preview": r.text[:150]
        }
    except Exception as e:
        return {"ok": False, "error": repr(e), "model": HF_MODEL, "hf_enabled": True, "url": HF_API_URL}