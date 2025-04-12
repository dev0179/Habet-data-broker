import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import subprocess
import logging
import time
import threading
import serial
import serial.tools.list_ports
import math
import os

# ========== CONFIGURATION ==========
SERIAL_PORT = '/dev/ttyUSB1'
SERIAL_BAUDRATE = 115200

ROTATOR_MODEL = '603'
ROTATOR_PORT = '/dev/ttyUSB0'

WEB_SOCKET_PORT = 5053

LAT_S = 42.02698670969771
LON_S = -93.6535530849385
ALT_S = 0.279  # in km

A = 6378.137
B = 6356.752
E2 = 1 - (B**2 / A**2)

# ========== FLASK & SOCKETIO SETUP ==========
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

logging.basicConfig(filename='rotator.log', level=logging.INFO, format='%(asctime)s - %(message)s')

serial_connected = False
manual_control = False
data_sent = {
    "lon": 0,
    "lat": 0,
    "alt": 0,
    "azimuth": 0,
    "elevation": 0,
    "serial connected": serial_connected,
    "manual_control": manual_control,
    "GPS_Speed": 0,
    "pressure": 0,
    "temperature": 0,
    "humidity": 0,
    "counter": 0,
    "volt": 0
}

data_lock = threading.Lock()

# ========== UTILITY FUNCTIONS ==========
def execute_rotctl_command(command):
    full_cmd = f"rotctl -m {ROTATOR_MODEL} -r {ROTATOR_PORT} {command}"
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)

    if result.stdout.strip() == "":
        print("No output from rotctl. Device may be disconnected.")
        return None

    return result.stdout.strip()

def update_rotator(azimuth, elevation):
    if azimuth is not None and elevation is not None:
        result = execute_rotctl_command(f'P {azimuth} {elevation}')
        if result:
            print("Rotator successfully updated.")
        else:
            print("Rotator update failed.")

def lla_to_ecef(lat, lon, alt):
    lat, lon = math.radians(lat), math.radians(lon)
    N = A / math.sqrt(1 - E2 * math.sin(lat)**2)
    X = (N + alt) * math.cos(lat) * math.cos(lon)
    Y = (N + alt) * math.cos(lat) * math.sin(lon)
    Z = ((B**2 / A**2) * N + alt) * math.sin(lat)
    return X, Y, Z

def ecef_to_enu(V, lat_s, lon_s):
    lat_s, lon_s = math.radians(lat_s), math.radians(lon_s)
    R = [
        [-math.sin(lon_s), math.cos(lon_s), 0],
        [-math.sin(lat_s) * math.cos(lon_s), -math.sin(lat_s) * math.sin(lon_s), math.cos(lat_s)],
        [math.cos(lat_s) * math.cos(lon_s), math.cos(lat_s) * math.sin(lon_s), math.sin(lat_s)]
    ]
    return [sum(R[i][j] * V[j] for j in range(3)) for i in range(3)]

def compute_az_el(lat_t, lon_t, alt_t):
    alt_t /= 1000
    Xs, Ys, Zs = lla_to_ecef(LAT_S, LON_S, ALT_S)
    Xt, Yt, Zt = lla_to_ecef(lat_t, lon_t, alt_t)
    V = [Xt - Xs, Yt - Ys, Zt - Zs]
    ENU = ecef_to_enu(V, LAT_S, LON_S)
    az = math.degrees(math.atan2(ENU[0], ENU[1]))
    if az < 0:
        az += 360
    el = math.degrees(math.atan2(ENU[2], math.sqrt(ENU[0]**2 + ENU[1]**2)))
    return az, el

# ========== ROTATOR STATUS EMITTER ==========
def rotator_status_thread():
    while True:
        try:
            status = execute_rotctl_command('p')
            if status:
                lines = status.splitlines()
                if len(lines) >= 2:
                    az = float(lines[0])
                    el = float(lines[1])
                    data_sent.update({"azimuth": az, "elevation": el, "serial connected": serial_connected})
                    socketio.emit('status_update', data_sent)
        except Exception as e:
            logging.error(f"Status thread error: {e}")
        time.sleep(1)


@app.route('/toggle_manual', methods=['POST'])
def toggle_manual():
     global manual_control
     manual_control = not manual_control
     data_sent["manual_control"] = manual_control  
     return jsonify({"manual_control": manual_control})

# ================ CSV logger ====================
def log_to_csv(data):
    from datetime import datetime
    import csv

    # Define the log file path
    file_path = 'LX-179B.csv'

    # Get current timestamp
    timestamp = datetime.now().isoformat()

    # Prepare the row to write
    row = [
        timestamp,
        data.get("lat"),
        data.get("lon"),
        data.get("alt"),
        data.get("azimuth"),
        data.get("elevation"),
        data.get("GPS_Speed"),
        data.get("pressure"),
        data.get("temperature"),
        data.get("humidity"),
        data.get("volt")
    ]

    # Append to CSV
    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(row)


# ========== SERIAL READER THREAD ==========
def serial_reader():
    global serial_connected
    global manual_control
    ser = None
    while True:
        if ser is None or not ser.is_open:
            try:
                ser = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=1)
                print(f"[INFO] Serial connected on {SERIAL_PORT}")
                serial_connected = True
                print(f"status connected: {serial_connected}")
            except Exception as e:
                if serial_connected:
                    print(f"[WARN] Lost serial connection: {e}")
                else:
                    print(f"[INFO] Waiting for serial device: {e}")
                serial_connected = False
                data_sent.update({"azimuth": 0, "elevation":0,  "serial connected": serial_connected})
                time.sleep(2)
                continue  # Try again

        try:
            line = ser.readline().decode('utf-8').strip()
            print('Data received:', line)
            if line.startswith('$$HAR'): 
                parts = line.split(',')
                print(parts)
                if len(parts) >=10:
                    lat = float(parts[1]) / 10000000
                    lon = float(parts[2]) / 10000000
                    alt = float(parts[3]) / 1000
                    gps_heading = float(parts[4]) / 100000
                    gps_speed = float(parts[5]) / 10
                    gps_pdop = float(parts[6]) / 10
                    pressure = float(parts[7]) / 100
                    temperature = float(parts[8]) / 100
                    humidity = float(parts[9]) / 1000
                    counter = float(parts[10])
                    volt = float(parts[11])
                    other_info = parts[11] if len(parts) > 11 else None
            
                    data_sent.update({
                        "lat": lat,
                        "lon": lon,
                        "alt": alt,
                        "GPS_Heading": gps_heading,
                        "GPS_Speed": gps_speed,
                        "GPS_PDOP": gps_pdop,
                        "pressure": pressure,
                        "temperature": temperature,
                        "humidity": humidity,
                        "counter": counter,
                        "volt": volt,
                        "other": other_info               
                    })
                    log_to_csv(data_sent)

                    az, el = int(round(compute_az_el(lat, lon, alt)))

                    if not manual_control:
                        if el>=0:
                            update_rotator(az, el)
                            socketio.emit('status_update', data_sent)
                        else:
                            update_rotator(az,0)
                            socketio.emit('status_update', data_sent)
                    else:
                        print("manual control is activated")
        except Exception as e:
            print(f"Serial read error: {e}")
        time.sleep(0.5)

# ========== MANUAL ROTATE ==========
@app.route('/rotate', methods=['POST'])
def rotate():
    if not manual_control:
        return jsonify({"error": "Manual control is disabled. Toggle it on to send commands."}), 403
    else:
        data = request.get_json()
        try:
            azimuth = int(round(float(data.get('azimuth', -1))))
            elevation = int(round(float(data.get('elevation', -1))))

            if not (0 <= azimuth <= 360):
                return jsonify({"error": "Azimuth must be 0-360"}), 400
            if not (0 <= elevation <= 180):
                return jsonify({"error": "Elevation must be 0-180"}), 400

            threading.Thread(target=update_rotator, args=(azimuth, elevation)).start()
            socketio.emit('status_update', {
                "azimuth": azimuth,
                "elevation": elevation,
                "serial connected": serial_connected,
                "manual_control": manual_control
            })
            return jsonify({"status": "command sent"})
        except ValueError:
            return jsonify({"error": "Invalid numbers"}), 400

@socketio.on('connect')
def on_connect():
    emit('connection', {'status': 'connected'})
    emit('status_update', data_sent)

# ========== MAIN ==========
if __name__ == '__main__':
    # Only start serial reader if port exists
    if os.path.exists(SERIAL_PORT):
        threading.Thread(target=serial_reader, daemon=True).start()
    else:
        print(f"[INFO] Skipping serial: {SERIAL_PORT} not found")

    socketio.start_background_task(rotator_status_thread)
    socketio.run(app, host='0.0.0.0', port=WEB_SOCKET_PORT)
