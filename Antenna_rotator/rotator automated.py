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
SERIAL_PORT = 'COM9'
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
latest_rotation = {"azimuth": 0, "elevation": 0,  "serial connected": serial_connected}
latest_data = {}
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
        print(f"Updating rotator to Az: {azimuth}, El: {elevation}")
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
                    latest_rotation.update({"azimuth": az, "elevation": el, "serial connected": serial_connected})
                    socketio.emit('status_update', latest_rotation)
        except Exception as e:
            logging.error(f"Status thread error: {e}")
        time.sleep(1)

# ========== SERIAL READER THREAD ==========
def serial_reader():
    global serial_connected
    ser = None
    while True:
        if ser is None or not ser.is_open:
            try:
                ser = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=1)
                print(f"[INFO] Serial connected on {SERIAL_PORT}")
                serial_connected = True
                latest_rotation["serial connected"] = serial_connected
            except Exception as e:
                if serial_connected:
                    print(f"[WARN] Lost serial connection: {e}")
                else:
                    print(f"[INFO] Waiting for serial device: {e}")
                serial_connected = False
                latest_rotation["serial connected"] = serial_connected
                socketio.emit('status_update', latest_rotation)
                time.sleep(2)
                continue

        try:
            line = ser.readline().decode('utf-8').strip()
            if line.startswith('$$HAR'):
                parts = line.split(',')
                if len(parts) >= 10:
                    lat = float(parts[2]) / 10000000
                    lon = float(parts[3]) / 10000000
                    alt = float(parts[4]) / 1000

                    latest_data.update({
                        "time": parts[1],
                        "lat": lat,
                        "lon": lon,
                        "alt": alt,
                        "GPS_Heading": float(parts[5]) / 100000,
                        "GPS_Speed": float(parts[6]) / 10,
                        "GPS_PDOP": float(parts[7]) / 10,
                        "pressure": float(parts[8]) / 100,
                        "temperature": float(parts[9]) / 100,
                        "humidity": float(parts[10]) / 1000,
                        "other": parts[11] if len(parts) > 11 else None
                    })

                    az, el = compute_az_el(lat, lon, alt)
                    latest_rotation.update({"azimuth": az, "elevation": el, "serial connected": serial_connected, "lat": lat, "lon": lon})
                    update_rotator(az, el)
                    socketio.emit('status_update', latest_rotation)
        except Exception as e:
            print(f"Serial read error: {e}")
        time.sleep(0.5)

# ========== MANUAL ROTATE ==========
@app.route('/rotate', methods=['POST'])
def rotate():
    data = request.get_json()
    try:
        azimuth = float(data.get('azimuth', -1))
        elevation = float(data.get('elevation', -1))

        if not (0 <= azimuth <= 360):
            return jsonify({"error": "Azimuth must be 0-360"}), 400
        if not (0 <= elevation <= 90):
            return jsonify({"error": "Elevation must be 0-90"}), 400

        threading.Thread(target=update_rotator, args=(azimuth, elevation)).start()
        latest_rotation.update({"azimuth": azimuth, "elevation": elevation})
        socketio.emit('status_update', latest_rotation)
        return jsonify({"status": "command sent"})
    except ValueError:
        return jsonify({"error": "Invalid numbers"}), 400

@socketio.on('connect')
def on_connect():
    emit('connection', {'status': 'connected'})
    emit('status_update', latest_rotation)

# ========== MAIN ==========
if __name__ == '__main__':
    threading.Thread(target=serial_reader, daemon=True).start()
    socketio.start_background_task(rotator_status_thread)
    socketio.run(app, host='0.0.0.0', port=WEB_SOCKET_PORT)
