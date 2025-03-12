import serial
import json
import threading
import socket
import time

# import serial.tools.list_ports

# # List all available serial ports

# def detect_esp32_port():
#     # List all available serial ports
#     ports = serial.tools.list_ports.comports()
#     print("Available serial ports:")
#     for port in ports:
#         print(f"Port: {port.device}, Description: {port.description}")
    
#     # Look for ESP32 or related devices
#     for port in ports:
#         if "ESP32" in port.description or "CP210x" in port.description or "CH340" in port.description:
#             print(f"Found ESP32 on {port.device}")
#             return port.device  # Return the device name (e.g., COM3)
    
#     raise Exception("ESP32 not found. Please check the device connection.")

# # Run and detect ESP32
# SERIAL_PORT = detect_esp32_port()
# print(f"Using serial port: {SERIAL_PORT}")

# Automatically detect and set the serial port
SERIAL_PORT = 'COM9'
SERIAL_BAUDRATE = 115200
TCP_SERVER_PORT = 9000


# Data template
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

# Lock for thread-safe data access
data_lock = threading.Lock()

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

# ========== TCP Server for Open MCT ==========
def tcp_server():
    print(f"[INFO] Starting TCP server on port {TCP_SERVER_PORT} for Open MCT")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', TCP_SERVER_PORT))
    server_socket.listen(5)

    while True:
        client_socket, addr = server_socket.accept()
        print(f"[INFO] Open MCT connected from {addr}")

        try:
            with client_socket:
                while True:
                    # Wait for client to request data (optional: check for specific keyword)
                    request = client_socket.recv(1024).decode('utf-8').strip()
                    if not request:
                        break  # Client disconnected

                    print(f"[DEBUG] Received request: {request}")

                    # Prepare and send latest data as JSON
                    with data_lock:
                        response = json.dumps(latest_data)
                    client_socket.sendall(response.encode('utf-8'))
                    print(f"[INFO] Sent data to Open MCT: {response}")

        except Exception as e:
            print(f"[ERROR] TCP connection error: {e}")

# ========== Main ==========
if __name__ == '__main__':
    # Start serial reader in background
    serial_thread = threading.Thread(target=serial_reader, daemon=True)
    serial_thread.start()

    # Start TCP server to serve Open MCT
    tcp_server()
