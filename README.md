ARDUINO ETS2 SPEEDOMETER

This is a arduino-based custom speedometer and tachometer for Euro Truck Simulator and American Truck Simulator.

It uses data from Funbit's telemetry server, which you can download here: https://github.com/Funbit/ets2-telemetry-server

MAIN FEATURES

- Showing current speed and rpms
- Sending it to any com port as serial commands
- Starting the telemetry server with the app
- Runs in the background
- Start with your computer

SERIAL COMMANDS

It sends the data in 115200 baud rate

Speed Commands: s-(any number between 0-180)

- Eg. s90
- Eg. s116

RPMs Commands: r-(any number between 0-8000)

- Eg. r5000
- Eg. r2549

To replicate this project, you should have these:
- Arduino Uno (Most of them should work, its just the one I used.)
- 2 Servo motors (Or any number depending on how much gauges you are making)

I made mine using 3D printed parts and I printed the background on my inkjet printer. I also used a 8 screws and nuts, but I encourage you to modify the design for your own screws. 

In the 3D_Print folder, you will find:
- The STLs I used
- The .STEP to make your own
- The background sticker, already at the right size for A4 paper
