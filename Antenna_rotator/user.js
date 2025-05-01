// WebSocket connection
const socket = io('http://10.24.220.47:5053');

// Gauge variables
let gauges = {};

// Initialize all gauges
function initGauges() {
  // Common gauge configuration
  const gaugeConfig = {
    relativeGaugeSize: true,
    donut: true,
    donutStartAngle: 90,
    startAnimationTime: 1000,
    refreshAnimationTime: 1000,
    levelColors: ["#00ffcc", "#ff9933"],
    counter: true,
    decimals: 2,
    gaugeWidthScale: 0.6,
    shadowOpacity: 0.2,
    shadowSize: 5,
    shadowVerticalOffset: 3,
    textRenderer: function(value) {
      return value.toFixed(2);
    }
  };

  // Initialize each gauge
  gauges.latitude = new JustGage({
    ...gaugeConfig,
    id: "latitude-gauge",
    value: 0,
    min: -90,
    max: 90,
    title: " ",
    label: "°",
    levelColors: ["#00ccff", "#0066ff"]
  });

  gauges.longitude = new JustGage({
    ...gaugeConfig,
    id: "longitude-gauge",
    value: 0,
    min: -180,
    max: 180,
    title: " ",
    label: "°",
    levelColors: ["#00ccff", "#0066ff"]
  });

  gauges.altitude = new JustGage({
    ...gaugeConfig,
    id: "altitude-gauge",
    value: 0,
    min: 0,
    max: 10000,
    title: " ",
    label: "m",
    levelColors: ["#ffcc00", "#ff9900"]
  });

  gauges.speed = new JustGage({
    ...gaugeConfig,
    id: "speed-gauge",
    value: 0,
    min: 0,
    max: 100,
    title: " ",
    label: "km/h",
    levelColors: ["#00ff00", "#009900"]
  });

  gauges.temperature = new JustGage({
    ...gaugeConfig,
    id: "temperature-gauge",
    value: 0,
    min: -40,
    max: 100,
    title: " ",
    label: "°C",
    levelColors: ["#ff6666", "#cc0000"]
  });

  gauges.humidity = new JustGage({
    ...gaugeConfig,
    id: "humidity-gauge",
    value: 0,
    min: 0,
    max: 100,
    title: " ",
    label: "%",
    levelColors: ["#66ccff", "#0066cc"]
  });

  gauges.pressure = new JustGage({
    ...gaugeConfig,
    id: "pressure-gauge",
    value: 0,
    min: 800,
    max: 1100,
    title: " ",
    label: "hPa",
    levelColors: ["#ffaa33", "#ff6600"]
  });

  gauges.voltage = new JustGage({
    ...gaugeConfig,
    id: "voltage-gauge",
    value: 0,
    min: 0,
    max: 15,
    title: " ",
    label: "V",
    levelColors: ["#cc66ff", "#9900cc"]
  });

  console.log("All circular gauges initialized successfully");
}

// Update all gauges with new data
function updateGauges(data) {
  try {
    // Update numeric displays
    document.getElementById('lat-value').textContent = data.lat ? parseFloat(data.lat).toFixed(6) : '--';
    document.getElementById('lon-value').textContent = data.lon ? parseFloat(data.lon).toFixed(6) : '--';
    document.getElementById('alt-value').textContent = data.alt ? parseFloat(data.alt).toFixed(2) : '--';
    document.getElementById('speed-value').textContent = data.GPS_Speed ? (parseFloat(data.GPS_Speed) ).toFixed(2) : '--';
    document.getElementById('temp-value').textContent = data.temperature ? parseFloat(data.temperature).toFixed(2) : '--';
    document.getElementById('humidity-value').textContent = data.humidity ? parseFloat(data.humidity).toFixed(2) : '--';
    document.getElementById('pressure-value').textContent = data.pressure ? parseFloat(data.pressure).toFixed(2) : '--';
    document.getElementById('volt-value').textContent = data.volt ? parseFloat(data.volt).toFixed(2) : '--';

    // Update gauge visuals
    if (data.lat) gauges.latitude.refresh(parseFloat(data.lat));
    if (data.lon) gauges.longitude.refresh(parseFloat(data.lon));
    if (data.alt) gauges.altitude.refresh(parseFloat(data.alt));
    if (data.GPS_Speed) gauges.speed.refresh(parseFloat(data.GPS_Speed)); // Convert m/s to km/h
    if (data.temperature) gauges.temperature.refresh(parseFloat(data.temperature));
    if (data.humidity) gauges.humidity.refresh(parseFloat(data.humidity));
    if (data.pressure) gauges.pressure.refresh(parseFloat(data.pressure));
    if (data.volt) gauges.voltage.refresh(parseFloat(data.volt));
  } catch (error) {
    console.error("Error updating gauges:", error);
  }
}

// WebSocket event handlers
socket.on('connect', () => {
  const statusEl = document.getElementById('connectionStatus');
  statusEl.textContent = "✅ Connected to WebSocket";
  statusEl.className = "connected";
  console.log("WebSocket connected");
});

socket.on('disconnect', () => {
  const statusEl = document.getElementById('connectionStatus');
  statusEl.textContent = "🔌 Disconnected from WebSocket";
  statusEl.className = "disconnected";
  console.log("WebSocket disconnected");
});

socket.on('status_update', (data) => {
  console.log("Received telemetry data:", data);
  updateGauges(data);
});

// Initialize everything when the page loads
document.addEventListener('DOMContentLoaded', () => {
  initGauges();
});