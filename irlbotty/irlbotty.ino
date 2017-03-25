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
  //pinMode(13, OUTPUT);  //Sets digital pin 13 as output pin

}

void loop() {
 
  if(Serial.available() > 0)                           // Do actions on recieving data
  {
    data = Serial.read();                              //Read the incoming data & store into datavar
    int min = random(60, 80);
    int max = random(min + 20, 120);
    int offset = random(-20, 20);
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
    
    digitalWrite(4, HIGH);                             // Make the wheels spin
    digitalWrite(5, LOW);
    
    digitalWrite(6, LOW);
    digitalWrite(7, HIGH);
  }
}
