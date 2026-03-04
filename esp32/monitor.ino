#include <WiFi.h>
#include <HTTPClient.h>

// ---------------- CONFIGURAÇÕES ----------------
const char* ssid = "SEU_WIFI";
const char* password = "SUA_SENHA";
const char* apiUrl = "https://SUA_API.onrender.com/monitor";

String urls[] = {
  "https://servidor1.com",
  "https://servidor2.com"
};
String serverNames[] = {
  "servidor1",
  "servidor2"
};

// ------------------------------------------------

int totalUrls = sizeof(urls) / sizeof(urls[0]);
unsigned long interval = 10000;
unsigned long lastTime = 0;
unsigned long watchdogTimer = 0;
const unsigned long watchdogLimit = 600000;

// ---------------- WIFI ----------------
void reconnectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.println("WiFi caiu. Reconectando...");
  WiFi.disconnect(true);
  WiFi.begin(ssid, password);
  int tentativas = 0;
  while (WiFi.status() != WL_CONNECTED && tentativas < 20) {
    delay(500);
    Serial.print(".");
    tentativas++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi reconectado!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFalha ao reconectar. Reiniciando ESP...");
    delay(2000);
    ESP.restart();
  }
}

// ---------------- API ----------------
void sendToAPI(String server, String status, int tempo) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(apiUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);

  String json = "{";
  json += "\"server\":\"" + server + "\",";
  json += "\"status\":\"" + status + "\",";
  json += "\"response_time\":" + String(tempo);
  json += "}";

  int response = http.POST(json);
  Serial.print("API Response: ");
  Serial.println(response);
  http.end();
}

// ---------------- PING SERVER ----------------
void pingURL(String url, String serverName) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  unsigned long start = millis();
  http.begin(url);
  http.setTimeout(8000);
  int httpCode = http.GET();
  unsigned long tempo = millis() - start;

  if (httpCode > 0) {
    Serial.print("OK -> ");
    Serial.print(serverName);
    Serial.print(" | HTTP: ");
    Serial.print(httpCode);
    Serial.print(" | Tempo: ");
    Serial.print(tempo);
    Serial.println(" ms");
    sendToAPI(serverName, "online", tempo);
  } else {
    Serial.print("ERRO -> ");
    Serial.print(serverName);
    Serial.print(" | ");
    Serial.println(http.errorToString(httpCode));
    sendToAPI(serverName, "offline", 0);
  }

  http.end();
  delay(500);
}

// ---------------- SETUP ----------------
void setup() {
  Serial.begin(115200);
  Serial.println("\nInicializando ESP32 Monitor");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Conectando WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
  watchdogTimer = millis();
}

// ---------------- LOOP ----------------
void loop() {
  reconnectWiFi();

  if ((millis() - lastTime) > interval) {
    Serial.println("\n------ VERIFICANDO SERVIDORES ------");
    Serial.print("Uptime: ");
    Serial.print(millis() / 1000);
    Serial.println(" segundos");

    for (int i = 0; i < totalUrls; i++) {
      pingURL(urls[i], serverNames[i]);
    }

    Serial.println("-----------------------------------");
    lastTime = millis();
    watchdogTimer = millis();
  }

  // Watchdog simples
  if (millis() - watchdogTimer > watchdogLimit) {
    Serial.println("Watchdog ativado. Reiniciando ESP...");
    delay(2000);
    ESP.restart();
  }
}
