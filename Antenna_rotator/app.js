const ctx = document.getElementById('liveChart').getContext('2d');
const liveChart = new Chart(ctx, {
  type: 'line',
  data: {
    datasets: [{
      label: 'Temperature (°C) vs Altitude (km)',
      data: [],
      borderColor: 'red',
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
        position: 'bottom',
        title: { display: true, text: 'Altitude (km)' }
      },
      y: {
        type: 'linear',
        title: { display: true, text: 'Temperature (°C)' }
      }
    }
  }
});

const SERVER_IP = 'http://10.24.220.47:5053';
const socket = io(SERVER_IP, { transports: ['websocket'], reconnection: true });

function updateUI(data) {
  const serialConnected = data['serial connected'];
  const manualControl = data['manual_control'];

  const now = new Date().toLocaleTimeString();
  const temperature = parseFloat(data.temperature);
  const altitude = parseFloat(data.alt);

  liveChart.data.datasets[0].data.push({ x: altitude, y: temperature });

  if (liveChart.data.datasets[0].data.length > 30) {
    liveChart.data.datasets[0].data.shift();
  }

  liveChart.update();
  customGraphs.forEach(({ chart, xKey, yKey }) => {
    const xVal = parseFloat(data[xKey]);
    const yVal = parseFloat(data[yKey]);

    if (!isNaN(xVal) && !isNaN(yVal)) {
      chart.data.datasets[0].data.push({ x: xVal, y: yVal });

      if (chart.data.datasets[0].data.length > 30) {
        chart.data.datasets[0].data.shift();
      }

      chart.update();
    }
  });
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
  .catch(() => alert("Failed to send rotation. Check connection."));
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

socket.on('status_update', updateUI);

const customGraphs = [];

function createGraph() {
  const xKey = document.getElementById('xSelect').value;
  const yKey = document.getElementById('ySelect').value;

  // Create container and canvas
  const container = document.createElement('div');
  container.style.width = '500px';
  container.style.height = '300px';

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
          position: 'bottom',
          title: { display: true, text: xKey }
        },
        y: {
          type: 'linear',
          title: { display: true, text: yKey }
        }
      }
    }
  });

  // Save chart config
  customGraphs.push({ chart: newChart, xKey, yKey });
}

function getRandomColor() {
  const letters = '0123456789ABCDEF';
  return '#' + Array.from({ length: 6 }, () => letters[Math.floor(Math.random() * 16)]).join('');
}

