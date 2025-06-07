
document.addEventListener("DOMContentLoaded", function () {
  document.getElementById("formularioTexto").addEventListener("submit", function(e) {
    e.preventDefault();
    const texto = document.getElementById("textoEntrada").value;
    enviarComando(texto);
    document.getElementById("textoEntrada").value = "";
  });

  function iniciarReconocimiento() {
    document.getElementById("botonCarga").classList.remove("d-none");
    document.querySelector('button[type="submit"]').classList.add("d-none");

    const reconocimiento = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    reconocimiento.lang = 'es-ES';
    reconocimiento.start();

    reconocimiento.onresult = function(event) {
      const texto = event.results[0][0].transcript;
      enviarComando(texto);
    };

    reconocimiento.onerror = function(event) {
      alert('Error al reconocer voz: ' + event.error);
      document.getElementById("botonCarga").classList.add("d-none");
      document.querySelector('button[type="submit"]').classList.remove("d-none");
    };

    reconocimiento.onend = function() {
      // Si no se reconoce nada, ocultar spinner
      document.getElementById("botonCarga").classList.add("d-none");
      document.querySelector('button[type="submit"]').classList.remove("d-none");
    };
  }

  window.iniciarReconocimiento = iniciarReconocimiento;

  function enviarComando(texto) {
    document.getElementById("botonCarga").classList.remove("d-none");
    document.querySelector('button[type="submit"]').classList.add("d-none");

    fetch('/api/comando', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto })
    })
    .then(response => response.json())
    .then(data => {
      const respuesta = data.respuesta;
      document.getElementById("respuesta").textContent = respuesta;
      document.getElementById("respuestaBox").classList.remove("d-none");
      hablar(respuesta);
    })
    .catch((error) => {
      alert("Error al procesar el comando.");
      console.error(error);
    })
    .finally(() => {
      document.getElementById("botonCarga").classList.add("d-none");
      document.querySelector('button[type="submit"]').classList.remove("d-none");
    });
  }

  function hablar(texto) {
    const voz = new SpeechSynthesisUtterance(texto);
    voz.lang = 'es-ES';
    speechSynthesis.speak(voz);
  }
});
