# LPP
This project transforms a smartphone into a precise, gyroscope-controlled mouse for a PC. Control is handled via a webpage on the phone, which sends sensor data (gyroscope &amp; accelerometer) to a Python server running on the PC. This server then translates the phone's movements into mouse actions.


Gyro Mouse

Turn your smartphone into a powerful, motion-controlled mouse for your PC. Using your phone's built-in gyroscope and a web-based interface, this project allows for precise cursor control over your local Wi-Fi network. No app installation required on your phone!

Features

Dual Control Modes:

Absolute Mode: Acts like a laser pointer. A 5-point calibration maps your phone's orientation directly to your entire screen area (multi-monitor aware).

Relative Mode: Works like a classic mouse, moving the cursor based on the phone's movement.

Advanced Smoothing:

Adjustable Smoothing: A slider lets you choose between ultra-smooth, slightly delayed movement and direct, responsive control.

Dynamic Anti-Jitter: An optional filter that uses the accelerometer to intelligently distinguish between intentional movement and natural hand tremors, providing an incredibly stable cursor.

Full Mouse Functionality:

Left-click (tap & hold).

Right-click (tap & hold).

Intuitive Scroll Mode: Activated by holding both left and right touch areas simultaneously.

Web-Based Client: Runs in any modern mobile browser. No need to install any app on your phone.

How It Works

The project uses a client-server architecture:

PC Server (pc_server.py): A Python script that serves the client webpage and runs a WebSocket server. It receives sensor data from the phone, processes it (applies smoothing, calculates position), and uses the pynput library to control the host system's mouse.

Phone Client (gyro_pointer_simulator.html): A single HTML file with JavaScript that accesses the phone's orientation and motion sensors. It sends this data via WebSocket to the PC server.

Setup Guide

Follow these steps to get your Gyro Mouse running.

1. Prerequisites

You need Python 3.x installed on your PC.

You need to install a few Python libraries. Open a terminal or command prompt and run:

pip install websockets pynput screeninfo


2. Download Files

Download pc_server.py and gyro_pointer_simulator.html.

Important: Place both files in the same folder on your PC.

3. Run the Server

Open a terminal or command prompt.

Navigate to the folder where you saved the files with "cd"

Run the server with the command:

python pc_server.py


The server will start and display your PC's local IP address, for example: [HTTP] Server started. Open http://192.168.1.42:8081 on your phone.. Note down this address.

4. Connect Your Phone

Make sure your smartphone is connected to the same Wi-Fi network as your PC.

Open a web browser on your phone (like Chrome, Safari, or Firefox).

Enter the address displayed by the server into the browser's address bar (e.g., http://192.168.1.42:8081).

The web interface should load, and it will attempt to connect automatically. If not, you can enter the IP manually and press "Connect".

5. Usage

Once connected, choose your preferred mode ("Absolute Mode" or "Relative Mode").

If you choose Absolute Mode, follow the on-screen instructions to complete the 5-point calibration.

You are now ready to control your PC!

Configuration

For advanced tuning, you can modify the constant values at the top of the pc_server.py file to adjust sensitivity, deadzone, and default smoothing parameters.
