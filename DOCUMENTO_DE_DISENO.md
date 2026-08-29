# Documento de Diseño

**Título del Proyecto:** MediGo: Estación Dispensadora Inteligente Portátil de Medicamentos.

---

## 1. Introducción
La falta de adherencia a los tratamientos médicos es un problema grave, especialmente en adultos mayores o personas con rutinas exigentes, olvidos cognitivos o falta de supervisión directa, representando riesgos severos para la salud. Además, el almacenamiento convencional a menudo ignora la sensibilidad de los fármacos a factores ambientales como la humedad, degradando rápidamente algunos compuestos farmacológicos.  

**MediGo** es una estación de dispensación de medicamentos portátil, inteligente e interconectada, diseñada para mitigar la falta de adherencia a tratamientos médicos. El sistema automatiza la entrega de dosis programadas, verifica la ingesta mediante sensores ópticos, monitorea y reacciona ante atascos mecánicos, controla las condiciones ambientales del almacenamiento y reporta la telemetría a la nube para un seguimiento efectivo por parte de terceros.

---

## 2. Alcance y Limitaciones
* **Alcance:** Creación de un dispositivo autónomo capaz de gestionar horarios, alertar al usuario, verificar caídas y atascos en la dispensación, notificar vía correo electrónico en caso de omisiones o fallos, e integrar una arquitectura de control concurrente basada en ESP32.  
* **Limitaciones:** El sistema no sustituye el juicio médico ni la gestión presencial en casos de emergencia crítica. No resolverá fallos mecánicos derivados de condiciones externas extremas (ej. inmersión total en agua o daños físicos por impacto) que excedan la protección IP54 proyectada.

---
## 3 El diagrama de contexto define los límites del sistema **MediGo** y sus interacciones con los actores y sistemas externos.

![Diagrama de Contexto](images/diagrama_contexto.png)

## 4. Diagrama de Bloques del Diseño

![Diagrama de Bloques](Diagrama_Bloques.png)

### Descripción de Bloques
* **Bloque de Control:** ESP32 ejecutando FreeRTOS en C Nativo (ESP-IDF) para la gestión asíncrona de tareas (sensores, pantalla, conexión a nube y temporización).
* **Bloque Actuador:** Motor paso a paso 28BYJ-48 comandado directamente mediante el driver ULN2003 desde los GPIO del ESP32 (los niveles lógicos de 3.3V activan directamente la red Darlington del ULN2003).
* **Bloque de Sensores:** Sensores infrarrojos para la verificación de caída de pastilla y detección de atascos por tiempo de tránsito; sensor DHT (11/22) para monitoreo de humedad y temperatura interna.
* **Bloque de Energía:** Batería Li-ion 18650 acoplada a un módulo de carga TP4056 con protección BMS (1S). Para la línea de alimentación de actuadores y periferia se integra un convertidor elevador DC-DC (*Boost MT3608*) que eleva el voltaje de la batería a 5V/12V.
* **Bloque de Interfaz:** Pantalla OLED 0.96" (I2C), pulsador físico de confirmación y zumbador piezoeléctrico mediante control PWM.

---

## 5. Lógica de Estados del Software

![Diagrama de Estados](Diagrama_de_Estados.png)

1. **Inicialización:** Carga de parámetros desde la memoria NVS y verificación de conexión Wi-Fi (si falla, pasa a *Modo Portal Cautivo*).
2. **Modo Espera:** Monitoreo continuo de temperatura/humedad ambiental, actualización de reloj e inspección de alarmas programadas.
3. **Modo Dispensación:** Activación del motor paso a paso (vía ULN2003) para posicionar la dosis.
4. **Modo Verificación y Detección de Atascos:**
   * El sistema evalúa el sensor IR de caída dentro de una ventana de tiempo predefinida.
   * **Rutina de Desatasco:** Si se detecta una obstrucción mediante el sensor IR, el sistema ejecuta automáticamente un ciclo de desatasco (inversión corta de giro del motor) antes de reintentar.
   * **Criterio de Éxito / Alerta:** Si el paso es exitoso y se presiona el botón de confirmación, avanza a *Modo Éxito*. Si la obstrucción persiste o se agota el tiempo límite (*Timeout* de 10 min), conmuta a *Modo Alerta*.
5. **Modo Alerta:** Envío de notificación por correo electrónico / ThingSpeak y habilitación de la opción de liberación manual de emergencia.
6. **Modo Éxito:** Registro del evento en memoria NVS y transmisión de telemetría a la nube.

---

## 6. Alternativas de Diseño
* Para la arquitectura de cómputo se descartó una Raspberry Pi a fin de minimizar el consumo energético y maximizar la autonomía portátil, centralizando las tareas en el ESP32 con manejo concurrente en FreeRTOS.
* Se simplificó la etapa de potencia eliminando acoplamientos MOSFET intermedios, ya que las salidas GPIO de 3.3V del ESP32 saturan directamente las entradas de control del driver ULN2003.
* En el esquema eléctrico se separó la etapa de carga (TP4056 + BMS) de la etapa de regulación de potencia, añadiendo un convertidor DC-DC *Boost* dedicado para garantizar el voltaje y corriente de torque que exige el motor 28BYJ-48.

---

## 7. Plan de Test y Validación
* **Validación de Firmware:** Pruebas de concurrencia en FreeRTOS para asegurar que las llamadas Wi-Fi/Nube no bloqueen la respuesta de los sensores IR ni el control de fases del motor.
* **Validación Mecánica y Detección de Atascos:** Pruebas de par cinemático con el motor 28BYJ-48 simulando píldoras de diferentes tamaños e introduciendo obstrucciones deliberadas para validar la rutina automática de reversa y la activación de alarmas.
* **Test de Seguridad y Alimentación:** Verificación de la curva de descarga de la batería 18650 con el convertidor elevador DC-DC bajo carga activa, y simulación de fallos electrónicos para comprobar el acceso manual mecánico de emergencia.

---

## 8. Consideraciones Éticas y Gestión de Riesgos
El proyecto aplica el principio de *seguridad por diseño*. Al depender el paciente de la correcta entrega de su medicación, se aplican los siguientes mecanismos de mitigación:
* **Mitigación Doble de Atascos:** Detección electrónica activa mediante el sensor IR y secuencia de reintento automático por firmware en caso de bloqueo mecánico. Como respaldo de última instancia, se incluye un botón de anulación mecánica para extracción manual.
* **Privacidad de Datos:** La información transmitida a ThingSpeak empleará identificadores anónimos y códigos de evento cifrados, evitando vincular datos de identidad directamente en el tráfico de red.
