
document.addEventListener("DOMContentLoaded", function () {
  const formulario = document.getElementById("formularioTexto");
  const entradaTexto = document.getElementById("textoEntrada");
  const respuestaBox = document.getElementById("respuestaBox");
  const respuestaTexto = document.getElementById("respuesta");
  const botonCarga = document.getElementById("botonCarga");
  const botonEnviar = document.querySelector('button[type="submit"]');

  formulario.addEventListener("submit", function (e) {
    e.preventDefault();
    const texto = entradaTexto.value.trim();
    if (texto !== "") {
      limpiarRespuesta();
      enviarComando(texto);
      entradaTexto.value = "";
    }
  });

  function iniciarReconocimiento() {
    limpiarRespuesta();
    mostrarCarga();
    const reconocimiento = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    reconocimiento.lang = 'es-ES';
    reconocimiento.start();

    reconocimiento.onresult = function (event) {
      const texto = event.results[0][0].transcript;
      enviarComando(texto);
    };

    reconocimiento.onerror = function (event) {
      alert('Error al reconocer voz: ' + event.error);
      ocultarCarga();
    };

    reconocimiento.onend = function () {
      ocultarCarga();
    };
  }

  window.iniciarReconocimiento = iniciarReconocimiento;

  function enviarComando(texto) {
    mostrarCarga();

    fetch('/api/comando', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto })
    })
    .then(response => response.json())
    .then(data => {
      const respuesta = data.respuesta || "No se obtuvo respuesta.";
      respuestaTexto.textContent = respuesta;
      respuestaBox.classList.remove("d-none");
      hablar(respuesta);
    })
    .catch((error) => {
      alert("Error al procesar el comando.");
      console.error(error);
    })
    .finally(() => {
      ocultarCarga();
    });
  }

  function limpiarRespuesta() {
    respuestaTexto.textContent = "";
    respuestaBox.classList.add("d-none");
  }

  function mostrarCarga() {
    botonCarga.classList.remove("d-none");
    botonEnviar.classList.add("d-none");
  }

  function ocultarCarga() {
    botonCarga.classList.add("d-none");
    botonEnviar.classList.remove("d-none");
  }

  function hablar(texto) {
    if (!texto) return;
    const voz = new SpeechSynthesisUtterance(texto);
    voz.lang = 'es-ES';
    speechSynthesis.speak(voz);
  }
});
