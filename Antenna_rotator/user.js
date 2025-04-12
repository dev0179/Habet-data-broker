const socket = io('http://10.24.220.47:5053'); // Your WebSocket endpoint

// Declare the gauges
let latitudeGauge, longitudeGauge, altitudeGauge, speedGauge;
let temperatureGauge, humidityGauge, pressureGauge, voltageGauge;

function gaugeInitLog(id, label) {
  const el = document.getElementById(id);
  if (!el) {
    console.error(`❌ Gauge div for ${label} (id="${id}") not found in DOM.`);
  } else {
    console.log(`✅ Gauge container ready: #${id}`);
  }
  return el;
}

// Create Gauges
function createGauges() {
    try {
      console.log("🛠️ Initializing gauges...");
  
      const gaugeConfigs = [
        {
          varRef: 'latitudeGauge',
          id: "latitude-gauge",
          label: "Latitude",
          config: { value: 0, min: -90, max: 90, title: "°", levelColors: ["#00ccff"] }
        },
        {
          varRef: 'longitudeGauge',
          id: "longitude-gauge",
          label: "Longitude",
          config: { value: 0, min: -180, max: 180, title: "°", levelColors: ["#00ccff"] }
        },
        {
          varRef: 'altitudeGauge',
          id: "altitude-gauge",
          label: "Altitude",
          config: { value: 0, min: 0, max: 10000, title: "m", levelColors: ["#ffcc00"] }
        },
        {
          varRef: 'speedGauge',
          id: "speed-gauge",
          label: "Speed",
          config: { value: 0, min: 0, max: 500, title: "km/h", levelColors: ["#00ff00"] }
        },
        {
          varRef: 'temperatureGauge',
          id: "temperature-gauge",
          label: "Temperature",
          config: { value: 0, min: -40, max: 100, title: "°C", levelColors: ["#ff6666"] }
        },
        {
          varRef: 'humidityGauge',
          id: "humidity-gauge",
          label: "Humidity",
          config: { value: 0, min: 0, max: 100, title: "%", levelColors: ["#66ccff"] }
        },
        {
          varRef: 'pressureGauge',
          id: "pressure-gauge",
          label: "Pressure",
          config: { value: 0, min: 800, max: 1100, title: "hPa", levelColors: ["#ffaa33"] }
        },
        {
          varRef: 'voltageGauge',
          id: "voltage-gauge",
          label: "Voltage",
          config: { value: 0, min: 0, max: 15, title: "V", levelColors: ["#cc66ff"] }
        }
      ];
  
      gaugeConfigs.forEach(gauge => {
        const { id, label, config, varRef } = gauge;
        const el = document.getElementById(id);
  
        if (!el) {
          console.error(`❌ [${label}] Gauge DOM element not found: #${id}`);
          return;
        }
  
        try {
          window[varRef] = new JustGage({
            id,
            ...config
          });
          console.log(`✅ [${label}] Gauge initialized: #${id}`, config);
        } catch (gaugeErr) {
          console.error(`❌ [${label}] Failed to create gauge #${id}:`, gaugeErr);
        }
      });
  
      console.log("✅ All gauges processed.");
  
    } catch (err) {
      console.error("❌ Fatal error during gauge initialization:", err);
    }
  }
  
// Safely parse float values
function getSafeValue(data, key, fallback = 0) {
  const raw = data[key];
  const parsed = parseFloat(raw);
  if (isNaN(parsed)) {
    console.warn(`⚠️ Invalid value for "${key}":`, raw);
    return fallback;
  }
  return parsed;
}

// Update data
function updateData(data) {
  console.log("📡 Received data:", data);

  try {
    latitudeGauge?.refresh(getSafeValue(data, "lat"));
    longitudeGauge?.refresh(getSafeValue(data, "lon"));
    altitudeGauge?.refresh(getSafeValue(data, "alt"));
    speedGauge?.refresh(getSafeValue(data, "speed"));
    temperatureGauge?.refresh(getSafeValue(data, "temperature"));
    humidityGauge?.refresh(getSafeValue(data, "humidity"));
    pressureGauge?.refresh(getSafeValue(data, "pressure"));
    voltageGauge?.refresh(getSafeValue(data, "volt"));
  } catch (err) {
    console.error("❌ Error refreshing gauges:", err);
  }
}

// WebSocket Events
socket.on('connect', () => {
  const el = document.getElementById('connectionStatus');
  if (el) el.textContent = "✅ Connected to WebSocket";
  console.log("🟢 WebSocket connected.");
});

socket.on('disconnect', () => {
  const el = document.getElementById('connectionStatus');
  if (el) el.textContent = "🔌 Disconnected from WebSocket";
  console.log("🔴 WebSocket disconnected.");
});

socket.on('status_update', (data) => {
  console.log("📬 status_update event received.");
  updateData(data);
});

// On load
window.onload = () => {
  console.log("🚀 Page loaded. Starting gauge setup...");
  createGauges();
};
