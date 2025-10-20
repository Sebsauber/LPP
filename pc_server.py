import asyncio
import json
import websockets
import socket
import threading
import http.server
import socketserver
import math

# --- Configuration ---
HTTP_PORT = 8081
WS_PORT = 8080
SCROLL_SENSITIVITY = 0.07 
RELATIVE_SENSITIVITY = 3.5
DEADZONE = 2.0
SMOOTHING_FACTOR_JITTER = 0.1
JITTER_THRESHOLD = 1.5 

# --- Mouse & Screen Controller ---
try:
    from pynput.mouse import Controller, Button
    MOUSE_AVAILABLE = True
    mouse = Controller()
    print("[INIT] pynput mouse controller loaded.")
except ImportError:
    print("[WARN] pynput not installed. Mouse control will be disabled.")
    MOUSE_AVAILABLE = False, None
try:
    import screeninfo
    SCREENINFO_AVAILABLE = True
    print("[INIT] screeninfo loaded for multi-monitor support.")
except ImportError:
    print("[WARN] screeninfo not installed. Falling back to 1920x1080 resolution.")
    SCREENINFO_AVAILABLE = False

# --- Global State ---
state = {
    'mode': 'absolute',
    'calibration_points': {},
    'screen_origin': {'x': 0, 'y': 0},
    'screen_size': {'width': 1920, 'height': 1080},
    'last_smoothed_position': None,
    'use_jitter_reduction': True,
    'smoothing_factor': 0.25 # Default value, can be changed by the client
}

# ------------------------------------------------------
# Helper Functions
# ------------------------------------------------------
def get_virtual_screen_size():
    """Calculates the total bounding box of all connected monitors."""
    if not SCREENINFO_AVAILABLE: return {'x': 0, 'y': 0}, {'width': 1920, 'height': 1080}
    monitors = screeninfo.get_monitors()
    min_x, min_y = min(m.x for m in monitors), min(m.y for m in monitors)
    max_x, max_y = max(m.x + m.width for m in monitors), max(m.y + m.height for m in monitors)
    origin = {'x': min_x, 'y': min_y}
    size = {'width': max_x - min_x, 'height': max_y - min_y}
    print(f"[INFO] Virtual screen detected: {size['width']}x{size['height']} at ({origin['x']}, {origin['y']})")
    return origin, size

def start_http_server():
    """Starts a simple HTTP server in a separate thread to serve the HTML file."""
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=".", **kwargs)
        def do_GET(self):
            if self.path == '/': self.path = '/gyro_pointer_simulator.html'
            return super().do_GET()
    with socketserver.TCPServer(("", HTTP_PORT), CustomHandler) as httpd:
        ip = get_local_ip()
        print(f"[HTTP] Server started. Open http://{ip}:{HTTP_PORT} on your phone.")
        httpd.serve_forever()

def get_local_ip():
    """Finds the local IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        return ip
    except Exception: return "127.0.0.1"

# ------------------------------------------------------
# Mouse Logic
# ------------------------------------------------------
def map_value(value, from_min, from_max, to_min, to_max):
    """Maps a value from one range to another."""
    if from_max == from_min: return (to_min + to_max) / 2
    value_scaled = (value - from_min) / (from_max - from_min)
    return to_min + (value_scaled * (to_max - to_min))

def calculate_absolute_position(beta, alpha):
    """Calculates the target screen position based on 5-point calibration."""
    cp = state['calibration_points']
    if len(cp) < 5: return None
    min_beta = (cp['tl']['b'] + cp['tr']['b']) / 2
    max_beta = (cp['bl']['b'] + cp['br']['b']) / 2
    alpha_left = (cp['tl']['a'] + cp['bl']['a']) / 2
    alpha_right = (cp['tr']['a'] + cp['br']['a']) / 2
    alpha_span = alpha_right - alpha_left
    if abs(alpha_span) > 180: # Handle 360-degree wrap-around
        if alpha_span > 0: alpha_right -= 360
        else: alpha_left -= 360
        if alpha < (alpha_left + alpha_right) / 2: alpha += 360
    ss, so = state['screen_size'], state['screen_origin']
    target_x = map_value(alpha, alpha_left, alpha_right, so['x'], so['x'] + ss['width'])
    target_y = map_value(beta, min_beta, max_beta, so['y'], so['y'] + ss['height'])
    target_x = max(so['x'], min(so['x'] + ss['width'] - 1, target_x))
    target_y = max(so['y'], min(so['y'] + ss['height'] - 1, target_y))
    return int(target_x), int(target_y)

# ------------------------------------------------------
# WebSocket Server
# ------------------------------------------------------
async def handle_client(websocket):
    """Handles incoming WebSocket connections and processes sensor data."""
    print(f"[WS] New device connected: {websocket.remote_address}")
    state['calibration_points'] = {}
    state['last_smoothed_position'] = mouse.position if MOUSE_AVAILABLE else (0, 0)
    state['use_jitter_reduction'] = True 
    state['smoothing_factor'] = 0.25

    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")

            if action == "set_jitter_reduction":
                state['use_jitter_reduction'] = data.get('enabled', True)
                status = "enabled" if state['use_jitter_reduction'] else "disabled"
                print(f"[INFO] Dynamic anti-jitter {status}.")
            elif action == "set_smoothing":
                state['smoothing_factor'] = float(data.get('value', 0.25))
                print(f"[INFO] Smoothing factor set to {state['smoothing_factor']:.2f}.")
            elif action == "mode_change":
                state['mode'] = data.get('mode', 'absolute')
                print(f"[INFO] Mode changed to '{state['mode']}'.")
            elif action == "calibrate_point":
                point = data.get("point")
                state['calibration_points'][point] = {'b': data.get('b'), 'a': data.get('a')}
                if len(state['calibration_points']) == 5:
                    print("[INFO] Calibration complete!")
                    state['last_smoothed_position'] = mouse.position if MOUSE_AVAILABLE else (0, 0)
            elif action == "reset_calibration":
                state['calibration_points'] = {}
                print("[INFO] Calibration reset.")
            elif MOUSE_AVAILABLE:
                if action == "mouse_press":
                    button = Button.left if data.get("button") == "left" else Button.right
                    mouse.press(button)
                elif action == "mouse_release":
                    button = Button.left if data.get("button") == "left" else Button.right
                    mouse.release(button)
                elif action == "scroll_gesture":
                    delta_gamma = float(data.get("delta", 0))
                    mouse.scroll(0, -delta_gamma * SCROLL_SENSITIVITY)
                elif action == "gyro_move":
                    last_pos = state['last_smoothed_position']
                    current_smoothing = state['smoothing_factor']
                    if state['use_jitter_reduction']:
                        ax, ay, az = data.get('accel_x'), data.get('accel_y'), data.get('accel_z')
                        if ax is not None and ay is not None and az is not None:
                            magnitude = math.sqrt(ax**2 + ay**2 + az**2)
                            jitter_level = abs(magnitude - 9.8)
                            if jitter_level > JITTER_THRESHOLD:
                                current_smoothing = SMOOTHING_FACTOR_JITTER
                    
                    if state['mode'] == 'absolute':
                        target_pos = calculate_absolute_position(data.get('b'), data.get('a'))
                        if target_pos:
                            smooth_x = (target_pos[0] * current_smoothing) + (last_pos[0] * (1 - current_smoothing))
                            smooth_y = (target_pos[1] * current_smoothing) + (last_pos[1] * (1 - current_smoothing))
                            mouse.position = (int(smooth_x), int(smooth_y))
                            state['last_smoothed_position'] = (smooth_x, smooth_y)
                    else:
                        beta, gamma = data.get('b'), data.get('g')
                        dx = dy = 0
                        if abs(gamma) > DEADZONE: dx = (abs(gamma) - DEADZONE) * RELATIVE_SENSITIVITY * (1 if gamma > 0 else -1)
                        if abs(beta) > DEADZONE: dy = (abs(beta) - DEADZONE) * RELATIVE_SENSITIVITY * (-1 if beta > 0 else 1)
                        if dx != 0 or dy != 0:
                            target_x, target_y = last_pos[0] + dx, last_pos[1] + dy
                            smooth_x = (target_x * current_smoothing) + (last_pos[0] * (1 - current_smoothing))
                            smooth_y = (target_y * current_smoothing) + (last_pos[1] * (1 - current_smoothing))
                            mouse.position = (int(smooth_x), int(smooth_y))
                            state['last_smoothed_position'] = (smooth_x, smooth_y)
    except websockets.ConnectionClosed:
        print(f"[WS] Device disconnected: {websocket.remote_address}")

async def start_websocket_server():
    async with websockets.serve(handle_client, "0.0.0.0", WS_PORT):
        print(f"[WS] Server listening on ws://{get_local_ip()}:{WS_PORT}")
        await asyncio.Future()

# ------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------
if __name__ == "__main__":
    print("--- Starting Gyro Mouse Server ---")
    state['screen_origin'], state['screen_size'] = get_virtual_screen_size()
    threading.Thread(target=start_http_server, daemon=True).start()
    try:
        asyncio.run(start_websocket_server())
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user.")
    except OSError:
        print(f"\n[ERROR] A port ({WS_PORT} or {HTTP_PORT}) is already in use.")

