
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

  // para llamarlo desde el HTML
  window.iniciarReconocimiento = iniciarReconocimiento;

  // TIMEOUT DE 40 segundos
  function enviarComando(texto, callbackFinCarga) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort(); // cancela la petición si se pasa el tiempo
    }, 40000); // 40.000 ms

    fetch('/api/comando', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto }),
      signal: controller.signal
    })
    .then(response => response.json())
    .then(data => {
      const respuesta = data.respuesta || "No se obtuvo respuesta.";
      respuestaTexto.textContent = respuesta;
      // aseguramos estilo informativo
      respuestaBox.classList.remove("d-none");
      respuestaBox.classList.remove("alert-danger");
      respuestaBox.classList.add("alert-info");
      hablar(respuesta);
    })
    .catch((error) => {
      if (error.name === "AbortError") {
        // Timeout alcanzado
        mostrarError("El sistema está tardando demasiado en responder (timeout de 1 minuto). Por favor intenta nuevamente.");
      } else {
        mostrarError("Error al procesar el comando. Intenta otra vez más tarde.");
        console.error(error);
      }
    })
    .finally(() => {
      clearTimeout(timeoutId); // limpiamos el timeout siempre
      if (typeof callbackFinCarga === 'function') {
        callbackFinCarga();
      }
    });
  }

  function limpiarRespuesta() {
    respuestaTexto.textContent = "";
    respuestaBox.classList.add("d-none");
    // Reseteamos el estilo a "info" por si antes hubo error, para borrar texto escrito
    respuestaBox.classList.remove("alert-danger");
    respuestaBox.classList.add("alert-info");
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

  // Muestra errores en el mismo recuadro de respuesta
  function mostrarError(mensaje) {
    respuestaTexto.textContent = mensaje;
    respuestaBox.classList.remove("d-none");
    respuestaBox.classList.remove("alert-info");
    respuestaBox.classList.add("alert-danger");
  }
});
