#ifndef PAGINA_WEB_H
#define PAGINA_WEB_H

#include <Arduino.h>

const char paginaHorarios[] PROGMEM = R"rawliteral(
<!DOCTYPE HTML>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MediGo - Programacion</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
           background-color: #f4f4f9; display: flex; justify-content: center; padding: 20px; }
    .card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
            width: 100%; max-width: 400px; text-align: center; }
    h2 { color: #333; margin-bottom: 10px; }
    
    /* Estilo para el Reloj y Correos */
    #reloj { font-size: 22px; font-weight: bold; color: #007bff; margin-bottom: 15px; }
    .info-correos { background: #f8f9fa; padding: 10px; border-radius: 8px; margin-bottom: 20px; text-align: left; font-size: 14px; color: #444; border: 1px solid #eee; }
    .info-correos p { margin: 5px 0; }

    label { display: block; text-align: left; margin: 10px 0 5px; font-weight: bold; color: #555; }
    select, input[type="time"], input[type="email"] { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ddd; 
                                   border-radius: 8px; box-sizing: border-box; font-size: 16px; }
    input[type="submit"], .btn-action { width: 100%; padding: 12px; background-color: #007bff; color: white; border: none; 
                                border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }
    input[type="submit"]:hover, .btn-action:hover { background-color: #0056b3; }
    .btn-link { display: block; margin-top: 20px; color: #007bff; text-decoration: none; font-size: 14px; }
    
    /* Estilo para el mensaje flotante (Toast) */
    #toastMensaje {
        display: none;
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #28a745;
        color: #fff;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
        z-index: 1000;
        font-weight: bold;
        font-size: 14px;
        transition: opacity 0.3s ease;
    }
    hr { border: 0; border-top: 1px solid #eee; margin: 20px 0; }
  </style>
</head>
<body>
  <div class="card">
    <h2>MediGo - Panel Principal</h2>

    <!-- Sección de Correos Actuales (Debajo de la hora) -->
    <div class="info-correos">
      <p><b>Correo 1:</b> <span id="lblCorreo1">Cargando...</span></p>
      <p><b>Correo 2:</b> <span id="lblCorreo2">Cargando...</span></p>
    </div>

    <hr>

    <!-- Formulario para Programar Horarios -->
    <form id="formHorario">
      <label>Día de la semana:</label>
      <select name="dia">
        <option value="0">Domingo</option>
        <option value="1">Lunes</option>
        <option value="2">Martes</option>
        <option value="3">Miércoles</option>
        <option value="4">Jueves</option>
        <option value="5">Viernes</option>
        <option value="6">Sábado</option>
      </select>
      <label>Hora:</label>
      <input type="time" name="hora" required>
      <input type="submit" value="Guardar Horario">
    </form>

    <hr>

    <div id="seccionRegistroCorreos">
      <h3>Configurar Correos</h3>
      <form id="formCorreos">
        <label>Correo Destinatario 1:</label>
        <input type="email" id="inputC1" placeholder="ejemplo1@gmail.com" required>
        <label>Correo Destinatario 2:</label>
        <input type="email" id="inputC2" placeholder="ejemplo2@gmail.com" required>
        <button type="button" class="btn-action" onclick="guardarCorreos()">Guardar Correos</button>
      </form>
    </div>

    <!-- Mensaje que aparecerá cuando los 2 correos ya estén guardados -->
    <div id="mensajeCorreosListos" style="display: none; background: #e2f0d9; color: #385723; padding: 10px; border-radius: 8px; margin-top: 15px; font-size: 14px;">
      <b>✓ Correos configurados correctamente.</b><br>Los 2 destinatarios de alerta ya están guardados.
    </div>

  <!-- Contenedor del mensaje flotante -->
  <div id="toastMensaje">¡Acción realizada con éxito!</div>

  <script>
    // Enviar formulario de horarios
    document.getElementById('formHorario').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new URLSearchParams(new FormData(this));

        fetch('/guardarHorario?' + formData.toString())
        .then(response => response.text().then(text => ({ status: response.status, body: text })))
        .then(res => {
            mostrarToast(res.body, res.status === 200 ? '#28a745' : '#dc3545');
        })
        .catch(error => {
            mostrarToast('Error de conexión con el ESP32', '#dc3545');
        });
    });

    // Enviar correos actualizados al ESP32
    function guardarCorreos() {
        const c1 = document.getElementById('inputC1').value;
        const c2 = document.getElementById('inputC2').value;

        fetch(`/guardar_correos?c1=${encodeURIComponent(c1)}&c2=${encodeURIComponent(c2)}`)
        .then(response => response.text().then(text => ({ status: response.status, body: text })))
        .then(res => {
            mostrarToast(res.status === 200 ? "Correos guardados con éxito" : "Error al guardar", res.status === 200 ? '#28a745' : '#dc3545');
            cargarCorreos(); // Refrescar los textos mostrados
        })
        .catch(error => {
            mostrarToast('Error de conexión con el ESP32', '#dc3545');
        });
    }

    /// Cargar los correos actuales desde el ESP32 al abrir la página
    function cargarCorreos() {
        fetch('/obtener_correos')
        .then(res => res.json())
        .then(data => {
            const c1 = data.c1 ? data.c1.trim() : "";
            const c2 = data.c2 ? data.c2.trim() : "";

            document.getElementById('lblCorreo1').innerText = c1 || "No configurado";
            document.getElementById('lblCorreo2').innerText = c2 || "No configurado";

            // Si ya están ambos correos registrados, ocultamos el formulario y mostramos el mensaje
            if (c1 !== "" && c2 !== "") {
                if(document.getElementById('seccionRegistroCorreos')) {
                    document.getElementById('seccionRegistroCorreos').style.display = 'none';
                    document.getElementById('mensajeCorreosListos').style.display = 'block';
                }
            } else {
                if(document.getElementById('seccionRegistroCorreos')) {
                    document.getElementById('seccionRegistroCorreos').style.display = 'block';
                    document.getElementById('mensajeCorreosListos').style.display = 'none';
                }
                if(c1) document.getElementById('inputC1').value = c1;
                if(c2) document.getElementById('inputC2').value = c2;
            }
        })
        .catch(err => console.log("No se pudieron cargar los correos"));
    }
    window.onload = function() {
      cargarCorreos();
};

    function mostrarToast(mensaje, colorFondo) {
        const toast = document.getElementById('toastMensaje');
        toast.innerText = mensaje;
        toast.style.background = colorFondo;
        toast.style.display = 'block';

        setTimeout(() => {
            toast.style.display = 'none';
        }, 3500);
    }
  </script>
</body>
</html>
)rawliteral";

#endif
