
from flask import Flask, request, jsonify, render_template
from datetime import datetime
import pytz

app = Flask(__name__)

def procesar_comando(comando):
    comando = comando.lower()
    salas_600 = ["601", "602", "603", "604", "605"]
    salas_500 = ["501", "502", "503", "504", "505"]

    for sala in salas_600:
        if sala in comando:
            return f"La sala {sala} está en la sede principal en el sexto piso. Si usas el ascensor llegarás directamente."

    for sala in salas_500:
        if sala in comando:
            return f"La sala {sala} está en la sede principal en el quinto piso. Si usas el ascensor llegarás directamente."

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

    else:
        return "No entendí el comando. ¿Puedes repetirlo?"

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
        return jsonify({"respuesta": respuesta})
    except Exception as e:
        print(f"Error en comando: {e}")
        return jsonify({"respuesta": "Ocurrió un error en el servidor."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
