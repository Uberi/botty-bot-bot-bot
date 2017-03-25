#include <Servo.h>


int pos = 0;    // variable to store the servo position
Servo leftServo, rightServo;  // create servo object to control a servo
char data = 0;            //Variable for storing received data
char buffer[256];

void setup() {
  // put your setup code here, to run once:

  leftServo.attach(9);
  rightServo.attach(10);
  pinMode(4, OUTPUT);
  pinMode(5, OUTPUT);
  pinMode(6, OUTPUT);
  pinMode(7, OUTPUT);
  // Bluetooth
  Serial.begin(9600);   //Sets the baud for serial data transmission                               
  pinMode(0, OUTPUT);   //Sets digital pin 13 as output pin
  pinMode(1, INPUT);

}

void loop() {

  int i = 0;
  if(Serial.available() > 0)                           // Do actions on recieving data
  {
    digitalWrite(13, HIGH);
    while (Serial.available() > 0) {
      buffer[i] = Serial.read();
      i++;
    }
    digitalWrite(13, LOW);

    // Drive forwards
    digitalWrite(4, HIGH);
    digitalWrite(5, LOW);
    digitalWrite(6, HIGH);
    digitalWrite(7, LOW);
    delay(1000);
    // Drive backwards
    digitalWrite(4, LOW);
    digitalWrite(5, HIGH);
    digitalWrite(6, LOW);
    digitalWrite(7, HIGH);
    delay(1000);
    
    // Spin Around
    digitalWrite(4, HIGH);                             // Make the wheels spin
    digitalWrite(5, LOW);
    
    digitalWrite(6, LOW);
    digitalWrite(7, HIGH);

    int min = random(60, 80);
    int max = random(min + 20, 120);
    int offset = random(-20, 20);
    int iterations = random(3,6);
    for(int q = 0; q <= iterations; q++) {
      // FLAIL 3~~(0.0)~~~E
      for (pos = min; pos <= max; pos += 1) {            // goes from min degrees to max degrees
        // in steps of 1 degree
        leftServo.write(180-pos + offset);               // tell servo to go to position in variable 'pos'
        rightServo.write(pos + offset);  
        delay(5);                                        // waits 5ms for the servo to reach the position
      }
      
      for (pos = max; pos >= min; pos -= 1) {            // goes from max degrees to min degrees
        rightServo.write(180-pos + offset);              // tell servo to go to position in variable 'pos'
        leftServo.write(pos + offset);  
        delay(5);                                        // waits 5ms for the servo to reach the position
      }
      delay(200);
    }
  }
  digitalWrite(4, LOW);                             // Make the wheels spin
  digitalWrite(5, LOW);
    
  digitalWrite(6, LOW);
  digitalWrite(7, LOW);
}
