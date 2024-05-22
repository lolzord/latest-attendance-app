#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// WiFi credentials
const char* ssid = "mozaia@unifi";  // Change this to your WiFi network name
const char* password = "0193814565abc";  // Change this to your WiFi password

// RFID reader pins
#define SS_PIN D4
#define RST_PIN D2

// LCD display setup
LiquidCrystal_I2C lcd(0x27, 16, 2);  // Set the LCD I2C address

// Create MFRC522 instance
MFRC522 mfrc522(SS_PIN, RST_PIN);

// Server details
const char* host = "delightful-flower-278edaa2951844d6b87045ea391d2607.azurewebsites.net";  // Your Azure URL
const int httpsPort = 443;  // HTTPS port

void setup() {
  Serial.begin(115200);  // Match this with the Serial Monitor baud rate
  SPI.begin();
  mfrc522.PCD_Init();
  
  // Initialize the LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.print("Connecting to");
  lcd.setCursor(0, 1);
  lcd.print("WiFi...");

  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  // Show IP address
  lcd.clear();
  lcd.print("Connected!");
  lcd.setCursor(0, 1);
  lcd.print(WiFi.localIP().toString());
  delay(2000);  // Show the IP address for a short time
}

void loop() {
  // Check for new cards
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }

  // Extract the card ID
  String cardID = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    char buff[3];
    sprintf(buff, "%02X", mfrc522.uid.uidByte[i]);
    cardID += String(buff);
  }

  // Connect to the server and send the card ID
  WiFiClientSecure client;
  client.setInsecure(); // Use this for testing purposes only, it skips the certificate verification
  if (client.connect(host, httpsPort)) {
    // Request to /record_attendance
    String url = "/record_attendance?id=" + cardID;
    client.print(String("GET ") + url + " HTTP/1.1\r\n" +
                 "Host: " + host + "\r\n" +
                 "Connection: close\r\n\r\n");

    // Check the server response
    int timeout = 5000; // 5 seconds timeout
    unsigned long startTime = millis();
    while (!client.available() && millis() - startTime < timeout) {
      delay(100);
    }

    if (client.available()) {
      String response = client.readStringUntil('\r');
      Serial.print("Server Response: ");
      Serial.println(response);
      lcd.clear();
      lcd.print("ID Sent");
      lcd.setCursor(0, 1);
      lcd.print(cardID); // Show card ID on LCD
    } else {
      lcd.clear();
      lcd.print("No Response");
      Serial.println("No response from server");
    }

    client.stop();
  } else {
    lcd.clear();
    lcd.print("Server Error");
    Serial.println("Connection to server failed");
  }

  delay(1000);  // Delay before next read
}

void waitForResponse(WiFiClient& client) {
  while(client.connected() || client.available()) {
    if(client.available()) {
      String line = client.readStringUntil('\n');
      if (line == "\r") {
        break; // headers are finished, and the body is about to start
      }
    }
  }
  delay(100); // Short delay to allow any remaining data to arrive
  client.stop(); // Close the connection
}
