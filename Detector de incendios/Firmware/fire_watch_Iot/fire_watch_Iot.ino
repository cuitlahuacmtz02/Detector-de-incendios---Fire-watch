#include <WiFi.h>  
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Fonts/FreeSerif9pt7b.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <DHT_U.h>
#include <MQUnifiedsensor.h>
//Display oled
#define BUILTIN_LED 2
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define buzzer_PIN 13
//Sensor utilizados: IR y DH11
#define IR_SENSOR_PIN 32    // Pin para el fototransistor IR *
#define TEMP_SENSOR_PIN 33  // Pin para el DHT11     *
#define DHTTYPE DHT11
//Definiciones: MQ7
#define placa "ESP 32"
#define Voltage_Resolution 5
#define pin 36       // GPIO36 (VP) en ESP32
#define type "MQ-7" //MQ7
#define ADC_Bit_Resolution 12 // For arduino UNO/MEGA/NANO
#define RatioMQ7CleanAir 27.5 //RS / R0 = 27.5 ppm 
#define PWMPin 5 // Pin connected to mosfet
//Delaraciones DH11
DHT dht(TEMP_SENSOR_PIN, DHTTYPE);
float tempValue = 0;
float temp = 0; 
float hum = 0;   
//Declaraciones MQ7
MQUnifiedsensor MQ7(placa, Voltage_Resolution, ADC_Bit_Resolution, pin, type);
unsigned long oldTime = 0;
float ppm = 0;
float ppmValue = 0;
//Declaraciones IR
int irADC = 0;
float irVolt = 0;
float irValue = 0;
float LOmin = 700;
float LOmax = 950;
float voltMin = 0.09; 
float voltMax = 2.15; 
// Configuración WiFi y MQTT
const char* ssid = "";
const char* password = "";
const char* mqtt_server = "broker.emqx.io";
WiFiClient espClient;
PubSubClient client(espClient);
unsigned long lastMsg = 0;
#define MSG_BUFFER_SIZE (50)
char msgGas[MSG_BUFFER_SIZE];
char msgTemp[MSG_BUFFER_SIZE];
char msgIR[MSG_BUFFER_SIZE];
char msgAL1[MSG_BUFFER_SIZE];
char msgAcesso1[MSG_BUFFER_SIZE];
char msgAcesso2[MSG_BUFFER_SIZE];
char buffer[100];            //mensaje con los datos de los sensores
//codigos de acceso
const int valid_codes[] = {1234, 5678, 9012, 3456};
int input_code = 0;
//Declaraciones Display Oled
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

//Funcion para la conexion a wifi
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  display.begin(SSD1306_SWITCHCAPVCC, 0x3C); // Inicializa el OLED
  delay(2000);
  display.setFont(&FreeSerif9pt7b);
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(0, 20);
  display.println("Connecting to");
  display.display();
  delay(2000);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  randomSeed(micros());
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}


void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  String incomingMessage = "";

  for (int i = 0; i < length; i++) {
    incomingMessage += (char)payload[i];
  }
  Serial.println(incomingMessage);

  if (String(topic) == "accessCodeTopic") {
    input_code = incomingMessage.toInt();
    if (validateCode(input_code)) {
      snprintf(msgAcesso1, MSG_BUFFER_SIZE, "Access Granted");
      Serial.println(msgAcesso1);
      client.publish("connectionStatus", msgAcesso1);
    } else {
      snprintf(msgAcesso2, MSG_BUFFER_SIZE, "Access Denied");
      Serial.println(msgAcesso2);
      client.publish("connectionStatus", msgAcesso2);
    }
  }
}
//validar codigo de acesso 
bool validateCode(int code) {
  for (int i = 0; i < sizeof(valid_codes) / sizeof(valid_codes[0]); i++) {
    if (valid_codes[i] == code) return true;
  }
  return false;
}
//funcion para reconectar a wifi
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      client.subscribe("accessCodeTopic");
      display.begin(SSD1306_SWITCHCAPVCC, 0x3C); // Inicializa el OLED
      delay(2000);
      display.setFont(&FreeSerif9pt7b);
      display.clearDisplay();
      display.setTextSize(1);
      display.setTextColor(WHITE);
      display.setCursor(0, 20);
      display.println("Connected");
      display.display();
      delay(2000);
    } 
    else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      display.begin(SSD1306_SWITCHCAPVCC, 0x3C); // Inicializa el OLED
      delay(2000);
      display.setFont(&FreeSerif9pt7b);
      display.clearDisplay();
      display.setTextSize(1);
      display.setTextColor(WHITE);
      display.setCursor(0, 20);
      display.println("ERROR: 1");
      display.println("rc, try 5seg");
      display.display();
      delay(5000);
    }
  }
}

void setup() {
  pinMode(BUILTIN_LED, OUTPUT);
  pinMode(TEMP_SENSOR_PIN, INPUT);
  pinMode(IR_SENSOR_PIN, INPUT);
  pinMode(buzzer_PIN, OUTPUT);

  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  dht.begin(); // Inicializa el DHT11
  
  //Set math model to calculate the PPM concentration and the value of constants
  MQ7.setRegressionMethod(1); //_PPM =  a*ratio^b
  MQ7.setA(99.042); 
  MQ7.setB(-1.518); 
  /*
    Exponential regression:
  GAS     | a      | b
  H2      | 69.014  | -1.374
  LPG     | 700000000 | -7.703
  CH4     | 60000000000000 | -10.54
  CO      | 99.042 | -1.518
  Alcohol | 40000000000000000 | -12.35
  */
  MQ7.init(); 
  Serial.print("Calibrating please wait.");
  MQ7.setR0(10.0); // Asigna manualmente un valor de R0
  Serial.println("  done!.");
  
  //MQ CAlibration  
  MQ7.serialDebug(true);

  display.begin(SSD1306_SWITCHCAPVCC, 0x3C); // Inicializa el OLED
  delay(2000);
  display.setFont(&FreeSerif9pt7b);
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(0, 20);
  display.println("Fire Watch IOT");
  display.display();
  delay(2000);
}

void sensor (){
  // Actualiza el valor del sensor MQ7
  MQ7.update(); 
  ppm = MQ7.readSensor(); // Lee el valor en PPM
  ppmValue = ppm + 0.01;

  // Leer temperatura y humedad del DHT11
  temp = dht.readTemperature(); // Temperatura en °C
  hum = dht.readHumidity();     // Humedad relativa en %
  if (!isnan(temp) && !isnan(hum)) {
    tempValue = temp; // Guarda la temperatura válida
    delay(500);
  } 
  else {
    Serial.println("Error reading DHT11");
    delay(500);
  }

  // Leer sensor IR
  irADC = analogRead(IR_SENSOR_PIN);
  irVolt = (irADC * 3.3) / 4095.0;
  irValue = LOmin + ((LOmax - LOmin) / (voltMax - voltMin)) * (irVolt - voltMin);

  //publicar los datos en el monitor serial
  publicar();
  sprintf(buffer, "Longitud de onda: %.3f, Temperatura: %.3f, PPM: %.3f", irValue, tempValue, ppmValue);
  Serial.println(buffer);
}

void publicar(){
  snprintf(msgGas, MSG_BUFFER_SIZE, "PPM: %.2f", ppmValue);
  Serial.print("Publish message: ");
  Serial.println(msgGas);
  client.publish("outTopic1", msgGas);

  snprintf(msgTemp, MSG_BUFFER_SIZE, "Temp: %.2f", tempValue);
  Serial.print("Publish message: ");
  Serial.println(msgTemp);
  client.publish("outTopic2", msgTemp);

  snprintf(msgIR, MSG_BUFFER_SIZE, "IR: %.2f", irValue);
  Serial.print("Publish message: ");
  Serial.println(msgIR);
  client.publish("outTopic3", msgIR);

  // Actualiza pantalla OLED
  display.clearDisplay();
  display.setFont(&FreeSerif9pt7b);
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(0, 20);
  display.println(msgGas);
  display.println(msgTemp);
  display.println(msgIR);
  display.display();

  if(irValue >= 850 && tempValue >= 40 && ppmValue >= 400){
      digitalWrite(buzzer_PIN, HIGH);
      snprintf(msgAL1, MSG_BUFFER_SIZE, "AL1");
      Serial.print("Publish message: ");
      Serial.println(msgAL1);
      client.publish("alertTopic", msgAL1);
    }
}

void loop() {
  digitalWrite(buzzer_PIN, LOW);
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // Publicar datos cada 2 segundos
  unsigned long now = millis();
  if (now - lastMsg > 2000) {
    lastMsg = now;
    sensor();
  }
}
