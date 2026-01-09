$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-8.0.472.8-hotspot"
$env:PATH = "C:\Program Files\Eclipse Adoptium\jdk-8.0.472.8-hotspot\bin;$env:PATH"
./gradlew clean build
Read-Host "Press Enter to exit"