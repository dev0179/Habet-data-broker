import serial
import json
import threading
import asyncio
import websockets
import time

# Serial Port Configuration
SERIAL_PORT = 'COM9'
SERIAL_BAUDRATE = 115200

# WebSocket Server Configuration
WEBSOCKET_PORT = 9000

# Shared Data Dictionary
latest_data = {
    "time": None,
    "lat": None,
    "lon": None,
    "alt": None,
    "vx": None,
    "vy": None,
    "vz": None,
    "temperature": None,
    "pressure": None,
    "humidity": None,
    "other": None
}

# Lock for thread-safe access
data_lock = threading.Lock()

# List of connected WebSocket clients
connected_clients = set()

# ========== Serial Reading Thread ==========
def serial_reader():
    global latest_data
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=1)
        print(f"[INFO] Connected to serial port {SERIAL_PORT}")
    except Exception as e:
        print(f"[ERROR] Cannot open serial port {SERIAL_PORT}: {e}")
        return

    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if line.startswith('$$HAR'):
                print(f"[DEBUG] Raw line: {line}")
                parts = line.split(',')
                
                if len(parts) >= 11:  # Ensure proper length
                    with data_lock:
                        latest_data = {
                            "time": parts[1].strip(),
                            "lat": parts[2].strip(),
                            "lon": parts[3].strip(),
                            "alt": parts[4].strip(),
                            "vx": parts[5].strip(),
                            "vy": parts[6].strip(),
                            "vz": parts[7].strip(),
                            "temperature": parts[8].strip(),
                            "pressure": parts[9].strip(),
                            "humidity": parts[10].strip(),
                            "other": parts[11].strip() if len(parts) > 11 else None
                        }
                        print(f"[INFO] Parsed data: {latest_data}")

            time.sleep(0.1)  # Slight delay to reduce CPU usage

        except Exception as e:
            print(f"[ERROR] Error reading/parsing serial: {e}")

# ========== WebSocket Server ==========
async def websocket_handler(websocket, path):
    global connected_clients
    print(f"[INFO] New WebSocket client connected: {websocket.remote_address}")
    
    # Add client to the set
    connected_clients.add(websocket)
    
    try:
        while True:
            with data_lock:
                response = json.dumps(latest_data)
            
            # Send latest telemetry data to the client
            await websocket.send(response)
            print(f"[INFO] Sent data to client {websocket.remote_address}: {response}")

            # Send data every 1 second (adjust as needed)
            await asyncio.sleep(1)

    except websockets.exceptions.ConnectionClosed:
        print(f"[INFO] Client {websocket.remote_address} disconnected")

    finally:
        connected_clients.remove(websocket)

# ========== Start WebSocket Server ==========
async def start_websocket_server():
    server = await websockets.serve(websocket_handler, "0.0.0.0", WEBSOCKET_PORT)
    print(f"[INFO] WebSocket server started on port {WEBSOCKET_PORT}")
    await server.wait_closed()

# ========== Main ==========
if __name__ == '__main__':
    # Start Serial Reader in a Background Thread
    serial_thread = threading.Thread(target=serial_reader, daemon=True)
    serial_thread.start()

    # Start WebSocket Server
    asyncio.run(start_websocket_server())
