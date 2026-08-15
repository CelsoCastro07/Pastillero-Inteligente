#include <Arduino.h>
#include <Wire.h>
#include <RTClib.h>
#include <WiFi.h>
#include "time.h"
#include "apwifieeprommode.h"
#include "PaginaWeb.h"
#include "DHT.h"
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <Preferences.h>
Preferences prefsCorreos;
// Variables para los correos
String correo1 = "";
String correo2 = "";

int horaDosisGlobal = 0;
int minDosisGlobal = 0;
int hora, minuto,segundo, diaSemana;
bool hayDosisConfigurada = false;
bool dosisEntregada = false;
bool horaObtenida = false;
const char* nombresDias[] = {"Domingo", "Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sábado"};
static int ultimoMinutoEjecutado = -1;
struct tm timeinfo;
const long  intervalo = 1000; // Leer cada 1 segundos
unsigned long ultimaLectura = 0;
unsigned long tiempoActual = 0;
unsigned long tiempoInicioAlarma = 0;
static unsigned long ultimoCambioBuzzer = 0;
static bool estadoBuzzer = false;
volatile bool alarmaActiva = false;
TaskHandle_t TaskMotorHandle = NULL;
const float TEMPERATURA_LIMITE = 30.0;
bool estadoAnteriorIR = HIGH;
const char* urlGoogleScript = "https://script.google.com/macros/s/AKfycbyJ7UKISfV_IVe873zMZNKTfHduIAcSGTf4mdsC5wp9DdEC1GV9au2JnLe6dq9m0tGZ/exec";
bool pastillaTomadaRealmente = false;

// Definición de pines (ajusta estos números según tu ESP32)
#define PIN_1 13
#define PIN_2 12
#define PIN_3 14
#define PIN_4 27
#define DHTPIN 4     // Pin donde conectaste el sensor
#define DHTTYPE DHT11 // O DHT22 si es el blanco/más preciso
#define SDA_PIN 21
#define SCL_PIN 22
#define IR_PIN 5
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64 // O 32, dependiendo de tu modelo
#define PIN_BUZZER 33
#define PIN_BOTON 26
#define PIN_VENTILADOR 18
//Display
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
// Humedad
DHT dht(DHTPIN, DHTTYPE);
// Real time clock
RTC_DS3231 rtc;
// Secuencia de pasos (invertida para lógica de transistores)
// 1 = Apagado (Transistor abierto), 0 = Encendido (Transistor saturado/llevado a GND)
int secuencia[8][4] = {
    {0, 1, 1, 1}, 
    {0, 0, 1, 1}, 
    {1, 0, 1, 1}, 
    {1, 0, 0, 1}, 
    {1, 1, 0, 1}, 
    {1, 1, 0, 0}, 
    {1, 1, 1, 0}, 
    {0, 1, 1, 0}
};

void registrarRutasCorreos() {
  // Ruta para guardar los correos enviados desde la web
  server.on("/guardar_correos", HTTP_GET, []() {
    String c1 = server.arg("c1");
    String c2 = server.arg("c2");
    
    prefsCorreos.begin("medigo-mail", false);
    prefsCorreos.putString("correo1", c1);
    prefsCorreos.putString("correo2", c2);
    prefsCorreos.end();

    server.send(200, "text/plain", "OK");
  });

  // Ruta para que la web lea los correos actuales en formato JSON
  server.on("/obtener_correos", HTTP_GET, []() {
    prefsCorreos.begin("medigo-mail", true);
    String c1 = prefsCorreos.getString("correo1", "");
    String c2 = prefsCorreos.getString("correo2", "");
    prefsCorreos.end();

    String json = "{\"c1\":\"" + c1 + "\",\"c2\":\"" + c2 + "\"}";
    server.send(200, "application/json", json);
  });
}

void enviarCorreoAlerta() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    Serial.println("Enviando correo de alerta...");
    http.begin(urlGoogleScript);
    http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS); // Necesario para los scripts de Google
    
    int codigoRespuesta = http.GET();
    
    if (codigoRespuesta > 0) {
      Serial.println("¡Correo enviado con éxito por Gmail!");
      String payload = http.getString();
      Serial.println(payload);
    } else {
      Serial.print("Error al enviar el correo: ");
      Serial.println(codigoRespuesta);
    }
    
    http.end();
  } else {
    Serial.println("WiFi desconectado, no se pudo enviar el correo.");
  }
}

// Hora de dosis configurada DE EJEMPLO

void handleVerHorarios() {
    String respuesta = "<html><head><meta name='viewport' content='width=device-width, initial-scale=1'><style>";
    respuesta += "body{font-family:sans-serif; background:#f4f4f9; padding:20px;}";
    respuesta += ".card{background:white; padding:15px; margin:10px 0; border-radius:10px; box-shadow:0 2px 5px rgba(0,0,0,0.1); display:flex; justify-content:space-between;}";
    respuesta += ".btn-del{background:#ff4d4d; color:white; padding:5px 10px; text-decoration:none; border-radius:5px;}";
    respuesta += "</style></head><body><h1>Mis Horarios</h1>";
    
    const char* nombresDias[] = {"Domingo", "Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "SAbado"};
    
    for(int i = 0; i < 7; i++) {
        String horarios = leerStringDeEEPROM(200 + (i * 20));
        if (horarios.length() > 0) {
            respuesta += "<h3>" + String(nombresDias[i]) + "</h3>";
            // Aquí separamos los horarios guardados para ponerles un botón a cada uno
            // (Logica simplificada para mostrar cada horario)
            respuesta += "<div class='card'><span>" + horarios + "</span><a href='/borrar?dia=" + String(i) + "' class='btn-del'>Borrar Todo</a></div>";
        }
    }
    respuesta += "<br><a href='/horarios'>Volver</a></body></html>";
    server.send(200, "text/html", respuesta);
}

void handleBorrar() {
    int dia = server.arg("dia").toInt();
    int direccion = 200 + (dia * 20);
    
    // Sobreescribimos con nada (vacío)
    escribirStringEnEEPROM(direccion, ""); 
    
    // Redirigimos al usuario a la lista actualizada
    server.sendHeader("Location", "/verHorarios", true);
    server.send(303, "text/plain", "");
}

void handleGuardarHorario() {
    Serial.println("Guardando horario...");
    String dia = server.arg("dia");   // Ejemplo: "1"
    String hora = server.arg("hora");  // Ejemplo: "14:30"
    
    if (dia != "" && hora != "") {
        int direccion = 200 + (dia.toInt() * 20);
        String horariosGuardados = leerStringDeEEPROM(direccion);
        if (horariosGuardados.length() > 40) {
            server.send(400, "text/plain", "Error: Limite de horarios alcanzado");
            return;
        }
        if (horariosGuardados.length() > 0) {
            horariosGuardados += "," + hora;
        } else {
            horariosGuardados = hora;
        }
        
        escribirStringEnEEPROM(direccion, horariosGuardados);
        
        int dosPuntos = hora.indexOf(':');
        horaDosisGlobal = hora.substring(0, dosPuntos).toInt();
        minDosisGlobal = hora.substring(dosPuntos + 1).toInt();
        hayDosisConfigurada = true;
        
        // Respuesta limpia para JavaScript
        server.send(200, "text/plain", "¡Horario guardado con éxito!");
    } else {
        server.send(400, "text/plain", "Error: Datos incompletos");
    }
    Serial.println("Horario guardado");
}

// Esta función corre en segundo plano de manera totalmente independiente
void tareaMotor(void * pvParameters) {

    while(1) {
        // La tarea se queda "dormida" y no consume CPU hasta que le digamos que se mueva
        vTaskSuspend(NULL); 

        // Cuando la despiertan, ejecuta los 2048 pasos con su propio delay sin afectar el loop
        for (int i = 0; i < 512; i++) {
            int paso_actual = i % 8;
            digitalWrite(PIN_1, secuencia[paso_actual][0]);
            digitalWrite(PIN_2, secuencia[paso_actual][1]);
            digitalWrite(PIN_3, secuencia[paso_actual][2]);
            digitalWrite(PIN_4, secuencia[paso_actual][3]);
            vTaskDelay(pdMS_TO_TICKS(2)); // Aquí usamos vTaskDelay de FreeRTOS de forma segura
        }

        // Apagamos bobinas al terminar
        digitalWrite(PIN_1, LOW);
        digitalWrite(PIN_2, LOW);
        digitalWrite(PIN_3, LOW);
        digitalWrite(PIN_4, LOW);
    }
}

void IRAM_ATTR botonPresionado() {
    // Añadimos una pequeña pausa y comprobación para filtrar falsos flancos por ruido
    static unsigned long ultimoDebounce = 0;
    unsigned long tiempoMilis = millis();
    
    if (tiempoMilis - ultimoDebounce > 200) { // Ventana de 200ms para ignorar rebotes/ruido
        // Verificamos que el pin realmente siga en LOW (presionado)
        if (digitalRead(PIN_BOTON) == LOW) {
            Serial.println("¡Pastilla retirada 2 (Botón real)!");
            digitalWrite(PIN_BUZZER, LOW);
            alarmaActiva = false;
            tiempoInicioAlarma = 0; 
        }
        ultimoDebounce = tiempoMilis;
    }
}

void sonarAlarma() {
    
    if (tiempoInicioAlarma == 0) {
        tiempoInicioAlarma = millis();
        ultimoCambioBuzzer = millis();
        estadoBuzzer = true;
        digitalWrite(PIN_BUZZER, HIGH);
    }
    unsigned long tiempoActual = millis();
    // Si ya pasaron los 5 segundos, apagamos todo y reseteamos
    if (tiempoActual - tiempoInicioAlarma >= 15000) {
        digitalWrite(PIN_BUZZER, LOW);
        alarmaActiva = false;
        tiempoInicioAlarma = 0; // Reseteamos para la próxima vez
        Serial.println("Alarma apagada automáticamente.");
        enviarCorreoAlerta();
        return;
    }
    
    // Si aún no pasan los 5 segundos, hacemos el "bip" intermitente cada 300ms sin bloquear
    if (tiempoActual - ultimoCambioBuzzer >= 300) {
        ultimoCambioBuzzer = tiempoActual;
        estadoBuzzer = !estadoBuzzer;
        digitalWrite(PIN_BUZZER, estadoBuzzer ? HIGH : LOW);
    }
   
}

void gestionar_monitoreo_tiempo() {

    // 1. Intentar obtener la hora (Prioridad RTC)
    // NOTA: rtc.begin() debe ir SOLO en el setup(). Aquí usamos rtc.now().
    if (getLocalTime(&timeinfo)) {
        hora = timeinfo.tm_hour;
        minuto = timeinfo.tm_min;
        segundo = timeinfo.tm_sec;
        diaSemana = timeinfo.tm_wday; // 0=Domingo, 6=Sábado
        horaObtenida = true;
        //Serial.println("Hora obtenida por NTP");
    } 
    // 2. Respaldo: Si NTP falla, intentar usar RTC
    else {
        DateTime now = rtc.now();
        // Validación: Solo usamos RTC si el año es mayor a 2020 (módulo sano)
        if (now.year() > 2020) {
            hora = now.hour();
            minuto = now.minute();
            segundo = now.second();
            diaSemana = now.dayOfTheWeek();
            horaObtenida = true;
            // Serial.println("NTP falló, usando RTC como respaldo");
        }
    }
    // 3. Ejecutar lógica si obtuvimos hora
    if (horaObtenida) {
        //Serial.printf("Hora: %02d:%02d:%02d\n", hora, minuto, segundo);
        String horarios = leerStringDeEEPROM(200 + (diaSemana * 20));
        char bufferActual[6];
        sprintf(bufferActual, "%02d:%02d", hora, minuto);
        String horaActualStr = String(bufferActual);

        // Si la hora actual está en la lista y no hemos disparado este minuto
        if (horarios.indexOf(horaActualStr) != -1) {
            if (minuto != ultimoMinutoEjecutado) {
                Serial.println("¡HORA DEL MEDICAMENTO!");
                vTaskResume(TaskMotorHandle);
                // Aquí es donde activas el buzzer
                alarmaActiva = true;
                ultimoMinutoEjecutado = minuto; // Guardamos el minuto ejecutado
            }
        } else {
            //Serial.print("Hora actual: "); Serial.println(horaActualStr);
            //Serial.print("Horarios en memoria: "); Serial.println(horarios);
            // Resetear cuando la hora actual ya no coincide (para preparar la siguiente dosis)
            ultimoMinutoEjecutado = -1;
        }
    }
}

void setup_pantalla() {
    // Inicializamos la pantalla con la dirección I2C común 0x3C
 // Intentar con 0x3C
    if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        Serial.println("OLED no encontrado en 0x3C, intentando 0x3D...");
    
    // Si falla, intentar con 0x3D
    if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3D)) {
      Serial.println("¡Error crítico! OLED no detectado en ninguna dirección.");
      return; // Aquí el código se detiene si no encuentra la pantalla
    }
}
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);
  String mensaje = "¡Iniciando MediGo!";
  int16_t x = (128 - (mensaje.length() * 6)) / 2;
  int16_t y = (64 - 8) / 2;
  display.setCursor(x, y);
  display.println(mensaje);
  display.display();
}

void actualizar_oled_pro(float t, float h, String estado) {
  display.clearDisplay();
  
  // 1. Cabecera con línea divisoria
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.print("HORA: "); 
  display.print(hora); display.print(":");
  if (minuto < 10) {
  display.print("0"); // Imprimimos el cero manualmente
    }
  display.print(minuto);
  display.print(":");
  if (segundo < 10) {
  display.print("0"); // Imprimimos el cero manualmente
    }
  display.print(segundo);

  display.drawLine(0, 10, 128, 10, SSD1306_WHITE); // Línea divisoria

  // 2. Zona Central: Temperatura y Humedad con letra más grande
  display.setTextSize(2);
  display.setCursor(0, 15);
  display.print(t, 0); display.print("C");
  
  display.setCursor(70, 15);
  display.print(h, 0); display.println("%");

  // Etiquetas pequeñas debajo de los valores
  display.setTextSize(1);
  display.setCursor(0, 35); display.print("Temp");
  display.setCursor(70, 35); display.print("Hum");

  // 3. Pie de página para estado
  display.drawLine(0, 48, 128, 48, SSD1306_WHITE);
  display.setCursor(0, 54);
  display.print("IP: "); display.print(WiFi.localIP());

  display.display();
}

void leer_ambiente() {

    // Si quieres evitar que falle al desconectarlo, puedes validar o usar un intervalo más amplio
    float h = dht.readHumidity();
    float t = dht.readTemperature();

    // Si la lectura es válida, actualizamos la OLED
    if (!isnan(h) && !isnan(t)) {
        actualizar_oled_pro(t, h, "Activo");
        // --- AQUÍ LLAMAS AL VENTILADOR USANDO TU VARIABLE 't' EXISTENTE ---
        // --- EVALUACIÓN DIRECTA AQUÍ ---
        if (t > 30.0) {
            digitalWrite(PIN_VENTILADOR, HIGH); // Prende si pasa de 30°C
        } 
        else if (t <= 29.0) {
            digitalWrite(PIN_VENTILADOR, LOW);  // Apaga si baja de 29°C
        }
    } else {
        // Si el sensor está desconectado, mostramos la hora igual pero sin congelar
        actualizar_oled_pro(0, 0, "Error DHT"); 
        // Si hay error en el sensor, por seguridad podemos apagar el ventilador
        digitalWrite(PIN_VENTILADOR, LOW);
    }
}
  
//Serial.print("Humedad: ");
//Serial.print(h);
//Serial.print("%  Temperatura: ");
//Serial.print(t);
//Serial.println("°C");

void monitorear_ir() {
  int estadoIR = digitalRead(IR_PIN); 

  if (estadoIR == LOW && estadoAnteriorIR == HIGH) {
    Serial.println("¡Pastilla retirada 1!");
    // Apagamos la alarma y el buzzer inmediatamente
    digitalWrite(PIN_BUZZER, LOW);
    alarmaActiva = false;
    tiempoInicioAlarma = 0;
    pastillaTomadaRealmente = true; 
    delay(200); 
  }

  estadoAnteriorIR = estadoIR;
}

void sincronizar_ntp() {
   
    // Configurar servidor NTP
    configTime(-5 * 3600, 0, "pool.ntp.org"); // -5 es tu zona horaria (Ecuador)
    Serial.println(" ¡Conectado y sincronizado!");
    Serial.print("Mi dirección IP es: ");
    Serial.println(WiFi.localIP());
}

void carga_horario_EPROM(int dia){
    String horarioRecuperado = leerStringDeEEPROM(200 + (dia * 20)); // Ejemplo: recupera día 0 (Domingo)
    if (horarioRecuperado.length() >= 5) {
        int dosPuntos = horarioRecuperado.indexOf(':');
        horaDosisGlobal = horarioRecuperado.substring(0, dosPuntos).toInt();
        minDosisGlobal = horarioRecuperado.substring(dosPuntos + 1).toInt();
        hayDosisConfigurada = true;
        Serial.printf("Horario cargado desde EEPROM: %02d:%02d\n", horaDosisGlobal, minDosisGlobal);
    }

}

void setup() {
    
    Serial.begin(115200);
    //EEPROM.begin(512); // O el tamaño que uses
    // Borrado masivo
    //for (int i = 0 ; i < 512 ; i++) {
        //EEPROM.write(i, 0);
    //}
    //EEPROM.commit();
    //Serial.println("Memoria EEPROM limpia completamente.");
    Wire.begin(SDA_PIN, SCL_PIN);
    rtc.begin();
    display.begin();
    dht.begin();
    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);

    registrarRutasCorreos();
    setup_pantalla();
    intentoconexion("MediGo_Setup", "12345678");
    sincronizar_ntp();

    server.on("/", HTTP_GET, []() {
    server.send_P(200, "text/html", paginaHorarios);});

    if (!rtc.begin()) {
        Serial.println("Error: No se encontró el RTC, iniciando con NTP");
    }
    //Pagina web
    server.begin();
    server.on("/horarios", HTTP_GET, [](){
        server.send_P(200, "text/html", paginaHorarios);
    });
    server.on("/guardarHorario", HTTP_GET, handleGuardarHorario);
    server.on("/verHorarios", HTTP_GET, handleVerHorarios);
    server.on("/borrar", HTTP_GET, handleBorrar);

    // Configurar pines como salida
    pinMode(PIN_1, OUTPUT);
    pinMode(PIN_2, OUTPUT);
    pinMode(PIN_3, OUTPUT);
    pinMode(PIN_4, OUTPUT);

    if (rtc.lostPower()) {
        Serial.println("RTC perdió energía, ajustando hora...");
        rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    }

    pinMode(IR_PIN, INPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
    pinMode(PIN_BOTON, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_BOTON), botonPresionado, FALLING);
    pinMode(PIN_VENTILADOR, OUTPUT);
    
    // Creamos la tarea en el Núcleo 0 (el ESP32 tiene Core 0 y Core 1)
    xTaskCreatePinnedToCore(
        tareaMotor,           // Función de la tarea
        "MotorTask",          // Nombre de la tarea (para depuración)
        2048,                 // Tamaño de la pila (Stack size)
        NULL,                 // Parámetros
        1,                    // Prioridad de la tarea
        &TaskMotorHandle,     // Referencia de la tarea
        0                     // Núcleo donde va a correr (Núcleo 0)
    );
    delay(1000);
}
void loop() {
    // Si el usuario intentó conectarse pero aún no hay conexión, 
    // seguimos atendiendo el servidor web.
    server.handleClient();

    if (WiFi.status() != WL_CONNECTED) {
        loopAP();
    }

    gestionar_monitoreo_tiempo();

    if (alarmaActiva) {
        sonarAlarma(); // Tu alarma existente sonando de fondo sin congelar nada
    }

    tiempoActual = millis();
    if (tiempoActual - ultimaLectura >= intervalo) {
        ultimaLectura = tiempoActual;
        leer_ambiente();
    }
    monitorear_ir();
    
    delay(1000);

}
