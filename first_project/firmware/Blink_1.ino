
String v = "v1.0.2";
int dl = 100;
void setup() {
Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
}


void loop() {
  Serial.println(v);
  digitalWrite(LED_BUILTIN, HIGH);   
  delay(dl);                       
  digitalWrite(LED_BUILTIN, LOW);    
  delay(dl);                   
}
