#include <Servo.h>

// Pin definitions
const int SERVO_PIN = 9;  // Servo motor pin
const int LED_RED = 7;    // Red LED for unregistered plates
const int LED_GREEN = 6;  // Green LED for registered plates

// Servo configuration
Servo barrierServo;
const int BARRIER_CLOSED = 0;    // Angle for closed position
const int BARRIER_OPEN = 90;     // Angle for open position
const int OPEN_TIME = 7000;      // Time to keep barrier open (7 seconds)

// Serial communication
const int BAUD_RATE = 9600;
String inputString = "";
boolean stringComplete = false;

void setup() {
  // Initialize serial communication
  Serial.begin(BAUD_RATE);
  inputString.reserve(200);
  
  // Initialize servo
  barrierServo.attach(SERVO_PIN);
  barrierServo.write(BARRIER_CLOSED);
  
  // Initialize LEDs
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  
  // Set initial state
  digitalWrite(LED_RED, HIGH);
  digitalWrite(LED_GREEN, LOW);
}

void loop() {
  // Process incoming serial data
  if (stringComplete) {
    inputString.trim();
    
    // Handle status-based commands
    if (inputString.startsWith("STATUS:")) {
      String status = inputString.substring(7);
      status.trim();
      
      if (status == "REGISTERED") {
        openBarrier();
      } else {
        keepBarrierClosed();
      }
    }
    // Handle direct control commands
    else if (inputString == "ENTRANCE_OPEN" || inputString == "EXIT_OPEN") {
      openBarrier();
    }
    else if (inputString == "ENTRANCE_CLOSE" || inputString == "EXIT_CLOSE") {
      keepBarrierClosed();
    }
    
    // Clear the string for next input
    inputString = "";
    stringComplete = false;
  }
}

// Serial event handler
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    inputString += inChar;
    
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}

void openBarrier() {
  // Turn on green LED, turn off red LED
  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_RED, LOW);
  
  // Open the barrier
  barrierServo.write(BARRIER_OPEN);
  
  // Wait for specified time
  delay(OPEN_TIME);
  
  // Close the barrier
  barrierServo.write(BARRIER_CLOSED);
  
  // Reset LEDs
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_RED, HIGH);
}

void keepBarrierClosed() {
  // Ensure barrier is closed
  barrierServo.write(BARRIER_CLOSED);
  
  // Visual feedback - blink red LED
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_RED, LOW);
    delay(200);
    digitalWrite(LED_RED, HIGH);
    delay(200);
  }
}