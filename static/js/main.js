
document.addEventListener("DOMContentLoaded", function () {
  const formulario = document.getElementById("formularioTexto");
  const entradaTexto = document.getElementById("textoEntrada");
  const respuestaBox = document.getElementById("respuestaBox");
  const respuestaTexto = document.getElementById("respuesta");

  const botonEnviar = document.getElementById("botonEnviar");
  const spinnerEnviar = document.getElementById("spinnerEnviar");

  const botonHablar = document.getElementById("botonHablar");
  const spinnerHablar = document.getElementById("spinnerHablar");

  formulario.addEventListener("submit", function (e) {
    e.preventDefault();
    const texto = entradaTexto.value.trim();
    if (texto !== "") {
      limpiarRespuesta();
      mostrarCargaTexto();
      enviarComando(texto, ocultarCargaTexto);
      entradaTexto.value = "";
    }
  });

  function iniciarReconocimiento() {
    limpiarRespuesta();
    mostrarCargaHablar();

    try {
      const reconocimiento = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
      reconocimiento.lang = 'es-ES';
      reconocimiento.start();

      reconocimiento.onresult = function (event) {
        const texto = event.results[0][0].transcript;
        enviarComando(texto, ocultarCargaHablar);
      };

      reconocimiento.onerror = function (event) {
        alert('Error al reconocer voz: ' + event.error);
        ocultarCargaHablar();
      };

      reconocimiento.onend = function () {
        ocultarCargaHablar();
      };
    } catch (error) {
      alert("No se puede iniciar reconocimiento de voz. Verifica si el navegador tiene acceso al micrófono.");
      ocultarCargaHablar();
    }
  }

  window.iniciarReconocimiento = iniciarReconocimiento;

  function enviarComando(texto, callbackFinCarga) {
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
      if (typeof callbackFinCarga === 'function') {
        callbackFinCarga();
      }
    });
  }

  function limpiarRespuesta() {
    respuestaTexto.textContent = "";
    respuestaBox.classList.add("d-none");
  }

  function mostrarCargaTexto() {
    botonEnviar.classList.add("d-none");
    spinnerEnviar.classList.remove("d-none");
  }

  function ocultarCargaTexto() {
    spinnerEnviar.classList.add("d-none");
    botonEnviar.classList.remove("d-none");
  }

  function mostrarCargaHablar() {
    botonHablar.classList.add("d-none");
    spinnerHablar.classList.remove("d-none");
  }

  function ocultarCargaHablar() {
    spinnerHablar.classList.add("d-none");
    botonHablar.classList.remove("d-none");
  }

  function hablar(texto) {
    if (!texto) return;
    const voz = new SpeechSynthesisUtterance(texto);
    voz.lang = 'es-ES';
    speechSynthesis.speak(voz);
  }
});
