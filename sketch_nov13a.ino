#include <Servo.h>

// Pin definitions
const int SPEED_SERVO_PIN = 9;
const int RPM_SERVO_PIN = 10;

// Servo objects
Servo speedServo;
Servo rpmServo;

// Current positions
int currentSpeedAngle = 175;
int currentRPMAngle = 0;

// Buffer for incoming data
const int BUFFER_SIZE = 32;
char buffer[BUFFER_SIZE];
int bufferIndex = 0;

// Timing variables
unsigned long lastUpdateTime = 0;
const unsigned long MIN_UPDATE_INTERVAL = 20; // Minimum time between updates in ms

void setup() {
  // Initialize servos
  speedServo.attach(SPEED_SERVO_PIN);
  rpmServo.attach(RPM_SERVO_PIN);
  
  // Set initial positions
  speedServo.write(currentSpeedAngle);
  rpmServo.write(currentRPMAngle);
  
  // Start serial with high baud rate
  Serial.begin(115200);
  Serial.setTimeout(1); // Minimize timeout for faster processing
}

void loop() {
  if (millis() - lastUpdateTime >= MIN_UPDATE_INTERVAL) {
    while (Serial.available() > 0) {
      char c = Serial.read();
      
      if (c == '\n') {
        buffer[bufferIndex] = '\0';
        processCommand(buffer);
        bufferIndex = 0;
      } else if (bufferIndex < BUFFER_SIZE - 1) {
        buffer[bufferIndex++] = c;
      }
    }
    lastUpdateTime = millis();
  }
}

void processCommand(char* cmd) {
  // Find the separator between speed and RPM
  char* rpmPart = strchr(cmd, 'r');
  
  if (cmd[0] == 's' && rpmPart != NULL) {
    // Extract speed value
    int speed = atoi(cmd + 1);
    // Extract RPM value
    int rpm = atoi(rpmPart + 1);
    
    // Update speed servo
    if (speed >= 0 && speed <= 180) {
      int speedAngle = map(speed, 0, 180, 175, 0);
      if (abs(currentSpeedAngle - speedAngle) > 1) {
        currentSpeedAngle = speedAngle;
        speedServo.write(currentSpeedAngle);
      }
    }
    
    // Update RPM servo
    if (rpm >= 0 && rpm <= 8000) {
      int rpmAngle = map(rpm, 0, 8000, 180, 0);
      if (abs(currentRPMAngle - rpmAngle) > 1) {
        currentRPMAngle = rpmAngle;
        rpmServo.write(currentRPMAngle);
      }
    }
  }
}