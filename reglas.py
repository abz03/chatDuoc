# reglas.py
# ------------------------------------------------------------
# Respuestas predefinidas y flujo determinista original.
# Devuelve string si hay match; si no, devuelve None.
# ------------------------------------------------------------

from datetime import datetime
import pytz

def procesar_reglas(comando: str) -> str | None:
    if not comando:
        return None

    c = comando.lower()

    salas_600 = ["601", "602", "603", "604", "605"]
    salas_500 = ["501", "502", "503", "504", "505"]
    salas_300 = ["301", "302", "303", "304", "305"]

    for sala in salas_600:
        if sala in c:
            return f"La sala {sala} está en la sede principal en el sexto piso. Si usas el ascensor llegarás directamente."

    for sala in salas_500:
        if sala in c:
            return f"La sala {sala} está en la sede principal en el quinto piso. Si usas el ascensor llegarás directamente."
        
    for sala in salas_300:
        if sala in c:
            return f"La sala {sala} está en la sede Boulevard en el tercer piso. Si usas el ascensor llegarás directamente, recuerda que son preferenciales."

    if "sala 603" in c and ("11:30" in c or "once treinta" in c or "a las once" in c):
        return "En la sala 603 el día lunes tienes Habilidades de la Comunicación, desde las 11:30 hasta las 12:50 horas del medio día."

    if "hola" in c or "cómo estás" in c:
        return "Hola, ¿cómo estás?"

    if "hora" in c:
        from_zone = pytz.timezone("America/Santiago")
        hora_chile = datetime.now(from_zone).strftime("%H:%M")
        return "La hora es " + hora_chile

    if "nombre" in c or "salas" in c:
        return "Soy un asistente de voz. Puedes preguntarme por salas, ubicación o la hora."

    if ("pagar" in c or "matricula" in c or "matrícula" in c or "matriculas" in c):
        return "Para pagos o matrículas, debes dirigirte a Financiamiento, ubicada en la sede principal de Plaza Vespucio en el quinto piso."

    if ("modificaciones horarias" in c or "beneficios" in c or "becas" in c or "gratuidad" in c or "justificaciones" in c):
        return "Para modificaciones horarias, beneficios estudiantiles, becas, gratuidad o presentar justificaciones, dirígete al Centro Académico en la sede principal de Plaza Vespucio, quinto piso."
    
    if (
        ("cuenta" in c and "duoc" in c) or
        ("problema" in c and "cuenta" in c) or
        ("correo" in c and "institucional" in c) or
        ("correo" in c) or
        ("cuenta" in c and "institucional" in c)
    ):
        return "Para problema con tu cuenta Duoc o correo, dirígete a Servicios digitales en la sede Boulevard de Plaza Vespucio, tercer piso; también puedes ir a la sede principal de Plaza Vespucio, en el quinto piso."
    
    if "bicicleta" in c:
        return "Para dejar tu bicicleta en Duoc, tienes dos opciones: dirígete al bicicletero en la sede Boulevard de Plaza Vespucio en el primer piso o ve a la sede principal en el quinto piso. No olvides llevar tu candado."
   
    if ("cómo te llamas" in c or 
        "quién eres" in c or 
        "qué cosas puedo preguntarte" in c or 
        "qué sabes sobre las salas" in c):
        return "Soy Duki Bot, tu asistente de voz. Puedes preguntarme por salas, ubicación, la hora o temas relacionados con servicios estudiantiles."

    # Sin match → que app.py intente IA
    return None