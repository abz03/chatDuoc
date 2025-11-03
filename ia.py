# ia.py (versión simple y didáctica)
# ------------------------------------------------------------
# Qué hace este archivo:
# 1) Lee variables desde Environment:
#       - HF_TOKEN   : tu token de Hugging Face
#       - HF_MODEL   : uno o varios modelos separados por coma
#                      ej: "mistralai/Mistral-7B-Instruct-v0.2, HuggingFaceTB/SmolLM2-1.7B-Instruct"
#       - HF_TIMEOUT : segundos de espera (recomendado 20)
#       - DEBUG_IA   : 1 para ver logs en consola, 0 para silenciar
# 2) Intenta responder usando el primer modelo que funcione.
# 3) Si un modelo no está disponible (404) o se demora (503), pasa al siguiente.
# 4) Si el modelo es Mistral, usa el formato de prompt [INST] ... [/INST].
# ------------------------------------------------------------

import os
import time
import re
import requests

# ========= 1) CONFIGURACIÓN BÁSICA (desde Environment) =========
HF_TOKEN   = os.getenv("HF_TOKEN")
HF_TIMEOUT = int(os.getenv("HF_TIMEOUT", "20"))
DEBUG_IA   = os.getenv("DEBUG_IA", "0") == "1"

# HF_MODEL puede ser "modeloA" o "modeloA, modeloB, modeloC"
_models_raw = (os.getenv("HF_MODEL") or "").strip()
if not _models_raw:
    raise RuntimeError("HF_MODEL no está definido en Environment.")

# Convertimos la lista de modelos a un arreglo limpio (sin espacios)
MODEL_LIST = [m.strip() for m in _models_raw.split(",") if m.strip()]

def _router_url(model_name: str) -> str:
    """URL del router nuevo de HuggingFace para un modelo dado."""
    return f"https://router.huggingface.co/hf-inference/{model_name}"

if DEBUG_IA:
    print("[IA] MODELOS CANDIDATOS:", MODEL_LIST)
    print("[IA] TIMEOUT (seg):", HF_TIMEOUT)

# ========= 2) REGLAS DE SEGURIDAD SENCILLAS (evitar respuestas peligrosas) =========
_SENSITIVE_PATTERNS = [
    r"contraseñ[a|o]s?|claves?",
    r"\bRUT\b|\brut\b",
    r"direcci[oó]n exacta|coordenadas",
    r"horari[oa]s? exact[oa]s?",
    r"\bafp\b|\bisapre\b|\bfonasa\b|\bcolmena\b",
]

def _is_sensitive(text: str) -> bool:
    t = (text or "").lower()
    return any(re.search(p, t, flags=re.IGNORECASE) for p in _SENSITIVE_PATTERNS)

# ========= 3) PROMPT Y PARÁMETROS =========
SYSTEM_PROMPT = (
    "Eres Duki Bot, asistente del Duoc UC. Responde en español de Chile, breve, claro y amable. "
    "Si no tienes un dato exacto, dilo y sugiere ir a Financiamiento, Centro Académico o Servicios Digitales. "
    "No inventes horarios ni información interna; no entregues datos personales. "
    "Respuesta de 1 a 2 frases, sin markdown."
)

def _is_mistral(model_name: str) -> bool:
    return "mistral" in (model_name or "").lower()

def _build_prompt(model_name: str, user_text: str) -> str:
    """
    Si el modelo es Mistral, usamos el formato recomendado:
        <s>[INST] ... [/INST]
    Para el resto, un formato simple.
    """
    user_text = (user_text or "").strip()
    if _is_mistral(model_name):
        return f"<s>[INST] {SYSTEM_PROMPT}\nUsuario: {user_text} [/INST]"
    return f"{SYSTEM_PROMPT}\nUsuario: {user_text}\nAsistente:"

# Parámetros de generación (puedes afinarlos si quieres)
GEN_PARAMS = {
    "max_new_tokens": 120,
    "temperature": 0.25,
    "top_p": 0.9,
    "repetition_penalty": 1.1,
    "return_full_text": False
}

# ========= 4) TELEMETRÍA SIMPLE (útil para ver qué pasó) =========
LAST = {
    "model": None,          # modelo que intentamos usar
    "url": None,            # URL del router
    "status": None,         # código HTTP (200, 404, 503, etc.)
    "elapsed_ms": None,     # tiempo de la llamada
    "error": None,          # texto de error si hubo excepción
    "preview": None         # un pedacito del cuerpo de respuesta
}

def _debug_print(msg: str):
    if DEBUG_IA:
        print("[IA]", msg)

# ========= 5) FUNCIÓN PRINCIPAL QUE RESPONDE CON IA =========
def responder_ia(user_text: str) -> str | None:
    """
    Flujo sencillo:
      a) Si el texto es sensible → devolvemos un aviso seguro.
      b) Si falta el token → no llamamos a la IA.
      c) Probamos cada modelo de MODEL_LIST hasta que uno responda 200 y devuelva texto.
      d) Si ninguno sirve → devolvemos None (tu app mostrará el fallback).
    """
    if _is_sensitive(user_text):
        return ("Prefiero no entregar datos sensibles o exactitudes que podrían ser inexactas. "
                "Consulta la intranet o acércate a la oficina correspondiente.")

    if not HF_TOKEN:
        _debug_print("No hay HF_TOKEN → no llamo a IA.")
        return None

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    for model in MODEL_LIST:
        url = _router_url(model)
        prompt = _build_prompt(model, user_text)
        payload = {"inputs": prompt, "parameters": GEN_PARAMS}

        # Hacemos 1 intento + 1 reintento si el modelo está "despertando" (503)
        for attempt in (1, 2):
            start = time.perf_counter()
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=HF_TIMEOUT)
                elapsed = int((time.perf_counter() - start) * 1000)

                # Guardamos telemetría para depurar
                LAST.update({
                    "model": model,
                    "url": url,
                    "status": resp.status_code,
                    "elapsed_ms": elapsed,
                    "error": None,
                    "preview": resp.text[:200]  # primeros 200 caracteres
                })

                # Caso exitoso
                if resp.status_code == 200:
                    data = resp.json()
                    # La API puede responder en distintos formatos; cubrimos los comunes.
                    text = ""
                    if isinstance(data, list) and data and "generated_text" in data[0]:
                        text = (data[0]["generated_text"] or "").strip()
                    elif isinstance(data, dict) and "generated_text" in data:
                        text = (data["generated_text"] or "").strip()
                    elif isinstance(data, dict):
                        # Algunos backends imitan "choices/message/content"
                        text = (data.get("choices", [{}])[0]
                                    .get("message", {})
                                    .get("content", "") or "").strip()

                    if text:
                        # Limpieza mínima
                        text = re.sub(r"\s+", " ", text)
                        if len(text) > 400:
                            text = text[:400].rstrip() + "..."
                        _debug_print(f"OK con modelo: {model} ({elapsed} ms)")
                        return text

                    # 200 pero sin texto → intentamos con otro modelo
                    _debug_print(f"200 OK pero sin texto con modelo {model}")
                    break

                # 503 = calentando; solo reintentamos una vez
                if resp.status_code == 503 and attempt == 1:
                    _debug_print(f"{model} en warming-up, reintento en 2.5s…")
                    time.sleep(2.5)
                    continue

                # Otros códigos → probamos el siguiente modelo
                _debug_print(f"{model} respondió {resp.status_code}; probamos otro.")
                break

            except Exception as e:
                # Error de red/timeout/etc.
                LAST.update({
                    "model": model,
                    "url": url,
                    "status": None,
                    "elapsed_ms": int((time.perf_counter() - start) * 1000),
                    "error": repr(e),
                    "preview": None
                })
                _debug_print(f"Excepción con {model}: {e}")
                # Reintentamos solo una vez si fue la 1ª
                if attempt == 1:
                    time.sleep(1.5)
                    continue
                break

    # Si llegamos acá, ningún modelo funcionó
    _debug_print("Ningún modelo respondió correctamente.")
    return None

# ========= 6) HEALTHCHECK SENCILLO =========
def ping_ia() -> dict:
    """
    Llama al primer modelo de la lista con un 'ping' muy corto,
    para saber si está disponible. Devuelve un resumen simple.
    """
    try:
        if not HF_TOKEN:
            return {"ok": False, "reason": "HF_TOKEN missing", "hf_enabled": False}

        model = MODEL_LIST[0]
        url = _router_url(model)
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        payload = {"inputs": "ping", "parameters": {"max_new_tokens": 5, "temperature": 0.01, "return_full_text": False}}

        t0 = time.perf_counter()
        r = requests.post(url, headers=headers, json=payload, timeout=HF_TIMEOUT)
        elapsed = int((time.perf_counter() - t0) * 1000)

        return {
            "ok": r.status_code == 200,
            "status": r.status_code,
            "model": model,
            "url": url,
            "elapsed_ms": elapsed,
            "preview": r.text[:150]
        }
    except Exception as e:
        return {"ok": False, "error": repr(e)}
