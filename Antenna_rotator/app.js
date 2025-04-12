const SERVER_IP = 'http://10.24.220.47:5053';
const socket = io(SERVER_IP, { transports: ['websocket'], reconnection: true });

function updateUI(data) {
  const serialConnected = data['serial connected'];
  const manualControl = data['manual_control'];

  document.getElementById('azimuth').textContent = data.azimuth ?? '--';
  document.getElementById('elevation').textContent = data.elevation ?? '--';
  document.getElementById('lat').textContent = data.lat ?? '--';
  document.getElementById('lon').textContent = data.lon ?? '--';
  document.getElementById('alt').textContent = data.alt ?? '--';
  document.getElementById('speed').textContent = data.GPS_Speed ?? '--';
  document.getElementById('pressure').textContent = data.pressure ?? '--';
  document.getElementById('temp').textContent = data.temperature ?? '--';
  document.getElementById('humidity').textContent = data.humidity ?? '--';
  document.getElementById('volt').textContent = data.volt ?? '--';

  if (serialConnected) {
    document.getElementById('rotatorStatus').textContent = "Rotator Status: Connected";
    document.getElementById('rotatorStatus').className = "connected";
  } else {
    document.getElementById('rotatorStatus').textContent = "Rotator Status: Not connected";
    document.getElementById('rotatorStatus').className = "not-found";
  }

  updateManualUI(manualControl);
}

function sendRotation() {
  const azimuth = parseFloat(document.getElementById('azimuthInput').value);
  const elevation = parseFloat(document.getElementById('elevationInput').value);

  if (isNaN(azimuth) || isNaN(elevation) || azimuth < 0 || azimuth > 360 || elevation < 0 || elevation > 180) {
    alert("Enter valid azimuth (0-360) and elevation (0-180).");
    return;
  }

  fetch(`${SERVER_IP}/rotate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ azimuth, elevation })
  })
  .then(response => response.json())
  .then(data => {
    if (data.status === "command sent") showCommandSentMessage();
    else alert("Rotation failed");
  })
  .catch(error => alert("Failed to send rotation. Check connection."));
}

function showCommandSentMessage() {
  const box = document.getElementById('commandSentBox');
  box.style.display = 'block';
  setTimeout(() => box.style.display = 'none', 3000);
}

function toggleMode() {
  document.body.classList.toggle('dark');
}

function toggleManualControl() {
  fetch(`${SERVER_IP}/toggle_manual`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      updateManualUI(data.manual_control);
    });
}

function updateManualUI(manualControlEnabled) {
  const statusText = document.getElementById('manualStatus');
  if (manualControlEnabled) {
    statusText.textContent = "Manual control enabled";
    statusText.style.color = "orange";
  } else {
    statusText.textContent = "Auto mode active";
    statusText.style.color = "green";
  }
}

socket.on('connect', () => {
  document.getElementById('connectionStatus').textContent = 'Connected to WebSocket';
  document.getElementById('connectionStatus').className = 'connected';
});

socket.on('disconnect', () => {
  document.getElementById('connectionStatus').textContent = 'Disconnected from WebSocket';
  document.getElementById('connectionStatus').className = 'disconnected';
});

let map;
let balloonPath = [];

// Initialize the map
function initMap(lat, lon) {
  map = L.map('map').setView([lat, lon], 13);  // Initial position based on lat/lon

  // Set the map tiles (OpenStreetMap)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  // Create a marker for the initial position
  let marker = L.marker([lat, lon]).addTo(map);
  marker.bindPopup("Balloon Position").openPopup();

  // Store the path of the balloon
  balloonPath.push([lat, lon]);
  L.polyline(balloonPath, { color: 'blue' }).addTo(map);
}

// Update the map with new position from WebSocket data
function updateMapPosition(data) {
  const lat = parseFloat(data.lat);
  const lon = parseFloat(data.lon);

  if (!isNaN(lat) && !isNaN(lon)) {
    // If map is not initialized, initialize it
    if (!map) {
      initMap(lat, lon);
    } else {
      // Update the map view and marker position
      map.setView([lat, lon], 13);
      const marker = L.marker([lat, lon]).addTo(map);
      marker.bindPopup("Balloon Position").openPopup();

      // Store and display the balloon's path
      balloonPath.push([lat, lon]);
      L.polyline(balloonPath, { color: 'blue' }).addTo(map);
    }
  }
}

// WebSocket handling for position updates
socket.on('status_update', (data) => {
  updateUI(data);
  updateMapPosition(data);  // Update map with the latest position
});


function createGraph() {
  const xKey = document.getElementById('xSelect').value;
  const yKey = document.getElementById('ySelect').value;

  const container = document.createElement('div');
  container.classList.add('chart-container');
  const canvas = document.createElement('canvas');
  container.appendChild(canvas);
  document.getElementById('customGraphs').appendChild(container);

  const ctx = canvas.getContext('2d');
  const newChart = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [{
        label: `${yKey} vs ${xKey}`,
        data: [],
        borderColor: getRandomColor(),
        borderWidth: 2,
        showLine: true
      }]
    },
    options: {
      animation: false,
      responsive: true,
      parsing: false,
      scales: {
        x: {
          type: 'linear',
          title: { display: true, text: xKey },
          position: 'bottom'
        },
        y: {
          type: 'linear',
          title: { display: true, text: yKey }
        }
      }
    }
  });

  customGraphs.push({ chart: newChart, xKey, yKey });
}

function updateCustomGraphs(data) {
  customGraphs.forEach(({ chart, xKey, yKey }) => {
    const xVal = parseFloat(data[xKey]);
    const yVal = parseFloat(data[yKey]);

    if (!isNaN(xVal) && !isNaN(yVal)) {
      chart.data.datasets[0].data.push({ x: xVal, y: yVal });
      if (chart.data.datasets[0].data.length > 30) chart.data.datasets[0].data.shift();
      chart.update();
    }
  });
}

function getRandomColor() {
  return '#' + Array.from({ length: 6 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
}