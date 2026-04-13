/**
 * F1 Lap Visualizer Component - Enhanced Edition
 * With visual track representation and F1 car animations
 */

class LapVisualizer {
  constructor(options = {}) {
    this.containerId = options.containerId || 'lap-visualizer-container';
    this.data = options.data || null;
    this.theme = options.theme || 'dark';
    this.onLapSelect = options.onLapSelect || (() => {});
    this.allStrategies = options.allStrategies || [];

    this.currentLap = 0;
    this.selectedStrategy = 0;
    this.animationSpeed = 1;
    this.isAnimating = false;
    this.charts = {};

    this.init();
  }

  init() {
    this.validateContainer();
  }

  validateContainer() {
    const container = document.getElementById(this.containerId);
    if (!container) {
      throw new Error(`Container with ID "${this.containerId}" not found`);
    }
  }

  render() {
    if (!this.data) {
      console.warn('No data provided to LapVisualizer');
      return;
    }

    const container = document.getElementById(this.containerId);
    container.innerHTML = this.getHTMLTemplate();
    this.attachEventListeners();
    this.initializeCharts();
    this.updateDisplay();
  }

  getHTMLTemplate() {
    return `
      <div class="lv-container">
        <!-- Header with Driver Info -->
        <div class="lv-header">
          <div class="lv-header-content">
            <div class="lv-header-left">
              <div class="lv-car-icon">🏎️</div>
              <div class="lv-title-section">
                <h2 class="lv-title">${this.data.driver_name || 'Driver'}</h2>
                <p class="lv-subtitle">${this.data.race_name || 'Race'} • ${this.data.strategy_name || 'Optimal'}</p>
              </div>
            </div>
            <div class="lv-header-right">
              <div class="lv-stat-badge">
                <span class="lv-badge-label">LAPS</span>
                <span class="lv-badge-value">${this.data.lap_times?.length || 0}</span>
              </div>
              <div class="lv-stat-badge">
                <span class="lv-badge-label">TIME</span>
                <span class="lv-badge-value">${this.formatTime(this.data.total_time || 0)}</span>
              </div>
              ${this.getComparisonBadges()}
            </div>
          </div>
        </div>

        <!-- Control Panel -->
        <div class="lv-controls-panel">
          <div class="lv-controls-row">
            <div class="lv-control-group">
              <label>Lap:</label>
              <input type="range" id="lv-lap-slider" class="lv-slider" min="0" max="100" value="0">
              <span id="lv-lap-display" class="lv-lap-badge">Lap 1</span>
            </div>

            <div class="lv-control-group">
              <label>Speed:</label>
              <select id="lv-speed-select" class="lv-select">
                <option value="0.5">0.5x</option>
                <option value="1" selected>1x</option>
                <option value="2">2x</option>
                <option value="4">4x</option>
              </select>
            </div>

            <div class="lv-button-group">
              <button id="lv-play-btn" class="lv-btn lv-btn-play" title="Play">▶ PLAY</button>
              <button id="lv-pause-btn" class="lv-btn lv-btn-pause" title="Pause" disabled>⏸ PAUSE</button>
              <button id="lv-reset-btn" class="lv-btn lv-btn-reset" title="Reset">↺ RESET</button>
            </div>
          </div>
        </div>

        <!-- Live Lap Counter & Track Visualization -->
        <div class="lv-main-content">
          <div class="lv-left-panel">
            <!-- Live Lap Counter -->
            <div class="lv-lap-counter">
              <div class="lv-counter-display">
                <div class="lv-counter-label">Current Lap</div>
                <div class="lv-counter-number" id="lv-current-lap">1</div>
              </div>
              <div class="lv-counter-progress">
                <div class="lv-progress-bar" id="lv-progress" style="width: 0%"></div>
              </div>
            </div>

            <!-- Lap Info Card -->
            <div class="lv-info-card">
              <h3 class="lv-card-title">⏱ LAP DATA</h3>
              <div class="lv-info-grid">
                <div class="lv-info-item">
                  <span class="lv-info-label">Time</span>
                  <span class="lv-info-value" id="lv-info-time">-</span>
                </div>
                <div class="lv-info-item">
                  <span class="lv-info-label">Position</span>
                  <span class="lv-info-value" id="lv-info-position">-</span>
                </div>
                <div class="lv-info-item">
                  <span class="lv-info-label">Fuel</span>
                  <span class="lv-info-value" id="lv-info-fuel">-</span>
                </div>
                <div class="lv-info-item">
                  <span class="lv-info-label">Tyre Age</span>
                  <span class="lv-info-value" id="lv-info-tyre">-</span>
                </div>
              </div>
            </div>

            <!-- Pit Stop Timeline -->
            <div class="lv-pit-timeline">
              <h3 class="lv-card-title">🛑 PIT STOPS</h3>
              <div id="lv-pit-stops" class="lv-pit-list"></div>
            </div>
          </div>

          <!-- Charts Section -->
          <div class="lv-right-panel">
            <!-- Lap Times Chart -->
            <div class="lv-chart-card">
              <h3 class="lv-chart-title">🏁 Lap Performance</h3>
              <canvas id="lv-chart-laptime" class="lv-chart"></canvas>
            </div>

            <!-- Fuel & Tyre Chart -->
            <div class="lv-chart-card">
              <h3 class="lv-chart-title">⛽ Fuel & Tyre Management</h3>
              <canvas id="lv-chart-fueltyre" class="lv-chart"></canvas>
            </div>

            <!-- Position Chart -->
            <div class="lv-chart-card">
              <h3 class="lv-chart-title">📍 Position Evolution</h3>
              <canvas id="lv-chart-position" class="lv-chart"></canvas>
            </div>
          </div>
        </div>

        <!-- Footer Stats -->
        <div class="lv-footer">
          <div class="lv-footer-stat">
            <span class="lv-footer-label">Total Race Time</span>
            <span class="lv-footer-value" id="lv-total-time">-</span>
          </div>
          <div class="lv-footer-stat">
            <span class="lv-footer-label">Total Pit Stops</span>
            <span class="lv-footer-value" id="lv-pit-count">-</span>
          </div>
          <div class="lv-footer-stat">
            <span class="lv-footer-label">Final Position</span>
            <span class="lv-footer-value" id="lv-final-pos">-</span>
          </div>
          <div class="lv-footer-stat">
            <span class="lv-footer-label">Avg Lap Time</span>
            <span class="lv-footer-value" id="lv-avg-time">-</span>
          </div>
        </div>
      </div>
    `;
  }

  attachEventListeners() {
    document.getElementById('lv-lap-slider').addEventListener('input', (e) => {
      this.currentLap = parseInt(e.target.value);
      this.stopAnimation();
      this.updateDisplay();
    });

    document.getElementById('lv-speed-select').addEventListener('change', (e) => {
      this.animationSpeed = parseFloat(e.target.value);
    });

    document.getElementById('lv-play-btn').addEventListener('click', () => this.startAnimation());
    document.getElementById('lv-pause-btn').addEventListener('click', () => this.stopAnimation());
    document.getElementById('lv-reset-btn').addEventListener('click', () => this.reset());
  }

  initializeCharts() {
    this.createLaptimeChart();
    this.createFuelTyreChart();
    this.createPositionChart();
  }

  createLaptimeChart() {
    const ctx = document.getElementById('lv-chart-laptime').getContext('2d');
    const lapTimes = this.data.lap_times || [];
    const labels = lapTimes.map((_, i) => `L${i + 1}`);

    this.charts.laptime = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Lap Time (s)',
          data: lapTimes,
          borderColor: '#ff006e',
          backgroundColor: 'rgba(255, 0, 110, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointRadius: 2,
          pointBackgroundColor: '#ff006e',
          pointHoverRadius: 6,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: { legend: { labels: { color: '#cbd5e1' } } },
        scales: {
          y: { grid: { color: 'rgba(100, 116, 139, 0.1)' }, ticks: { color: '#cbd5e1' } },
          x: { grid: { display: false }, ticks: { color: '#cbd5e1', maxTicksLimit: 10 } }
        }
      }
    });
  }

  createFuelTyreChart() {
    const ctx = document.getElementById('lv-chart-fueltyre').getContext('2d');
    const fuel = this.data.fuel_levels || [];
    const tyreAge = this.data.tyre_ages || [];
    const labels = fuel.map((_, i) => `L${i + 1}`);

    this.charts.fueltyre = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Fuel (L)',
            data: fuel,
            borderColor: '#00d9ff',
            backgroundColor: 'rgba(0, 217, 255, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 2,
            yAxisID: 'y'
          },
          {
            label: 'Tyre Age (laps)',
            data: tyreAge,
            borderColor: '#ffbe0b',
            backgroundColor: 'rgba(255, 190, 11, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 2,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { labels: { color: '#cbd5e1' } } },
        scales: {
          y: { display: true, grid: { color: 'rgba(100, 116, 139, 0.1)' }, ticks: { color: '#cbd5e1' } },
          y1: { display: true, position: 'right', grid: { drawOnChartArea: false }, ticks: { color: '#cbd5e1' } },
          x: { grid: { display: false }, ticks: { color: '#cbd5e1', maxTicksLimit: 10 } }
        }
      }
    });
  }

  createPositionChart() {
    const ctx = document.getElementById('lv-chart-position').getContext('2d');
    const positions = this.data.positions || [];
    const labels = positions.map((_, i) => `L${i + 1}`);

    this.charts.position = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Position',
          data: positions,
          borderColor: '#a100f2',
          backgroundColor: 'rgba(161, 0, 242, 0.1)',
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointRadius: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: { legend: { labels: { color: '#cbd5e1' } } },
        scales: {
          y: { reverse: true, grid: { color: 'rgba(100, 116, 139, 0.1)' }, ticks: { color: '#cbd5e1' } },
          x: { grid: { display: false }, ticks: { color: '#cbd5e1', maxTicksLimit: 10 } }
        }
      }
    });
  }

  updateDisplay() {
    const lapData = this.getLapData(this.currentLap);
    if (!lapData) return;

    const maxLap = (this.data.lap_times || []).length - 1;
    document.getElementById('lv-lap-slider').max = maxLap;
    document.getElementById('lv-lap-slider').value = this.currentLap;
    document.getElementById('lv-lap-display').textContent = `Lap ${this.currentLap + 1}`;
    document.getElementById('lv-current-lap').textContent = this.currentLap + 1;

    const progress = ((this.currentLap) / maxLap) * 100;
    document.getElementById('lv-progress').style.width = progress + '%';

    // Update info
    document.getElementById('lv-info-time').textContent =
      typeof lapData.lapTime === 'number' ? lapData.lapTime.toFixed(3) + 's' : '-';
    document.getElementById('lv-info-position').textContent = lapData.position;
    document.getElementById('lv-info-fuel').textContent =
      typeof lapData.fuel === 'number' ? lapData.fuel.toFixed(1) + 'L' : '-';
    document.getElementById('lv-info-tyre').textContent =
      typeof lapData.tyreAge === 'number' ? lapData.tyreAge + ' laps' : '-';

    // Update footer
    document.getElementById('lv-total-time').textContent = this.formatTime(this.data.total_time || 0);
    document.getElementById('lv-pit-count').textContent = this.data.pit_stops?.length || 0;
    document.getElementById('lv-final-pos').textContent = this.data.final_position || '-';

    const avgTime = (this.data.lap_times || []).length > 0
      ? (this.data.lap_times.reduce((a, b) => a + b, 0) / this.data.lap_times.length).toFixed(3)
      : '-';
    document.getElementById('lv-avg-time').textContent = typeof avgTime === 'string' ? avgTime + 's' : avgTime;

    // Update pit stops
    this.updatePitStops();

    this.onLapSelect({ lap: this.currentLap, data: lapData });
  }

  updatePitStops() {
    const container = document.getElementById('lv-pit-stops');
    container.innerHTML = '';

    const pitStops = this.data.pit_stops || [];
    if (pitStops.length === 0) {
      container.innerHTML = '<div class="lv-no-data">No pit stops</div>';
      return;
    }

    pitStops.forEach((stop, idx) => {
      const lapNum = stop.lap ?? '-';
      const active = this.currentLap >= lapNum;
      const div = document.createElement('div');
      div.className = `lv-pit-item ${active ? 'active' : ''}`;
      div.innerHTML = `
        <span class="lv-pit-number">${idx + 1}</span>
        <span class="lv-pit-lap">L${lapNum}</span>
        <span class="lv-pit-duration">${stop.duration?.toFixed(2) || '2.5'}s</span>
      `;
      container.appendChild(div);
    });
  }

  getLapData(lapIndex) {
    if (!this.data) return null;
    return {
      lap: lapIndex + 1,
      fuel: this.data.fuel_levels?.[lapIndex] ?? '-',
      tyreAge: this.data.tyre_ages?.[lapIndex] ?? '-',
      position: this.data.positions?.[lapIndex] ?? '-',
      lapTime: this.data.lap_times?.[lapIndex] ?? '-'
    };
  }

  startAnimation() {
    if (this.isAnimating) return;
    this.isAnimating = true;
    document.getElementById('lv-play-btn').disabled = true;
    document.getElementById('lv-pause-btn').disabled = false;

    const maxLap = (this.data.lap_times || []).length - 1;
    const interval = Math.max(100 / this.animationSpeed, 50);

    this.animationInterval = setInterval(() => {
      if (this.currentLap < maxLap) {
        this.currentLap++;
        document.getElementById('lv-lap-slider').value = this.currentLap;
        this.updateDisplay();
      } else {
        this.stopAnimation();
      }
    }, interval);
  }

  stopAnimation() {
    this.isAnimating = false;
    if (this.animationInterval) clearInterval(this.animationInterval);
    document.getElementById('lv-play-btn').disabled = false;
    document.getElementById('lv-pause-btn').disabled = true;
  }

  reset() {
    this.stopAnimation();
    this.currentLap = 0;
    document.getElementById('lv-lap-slider').value = 0;
    this.updateDisplay();
  }

  updateData(newData) {
    this.data = newData;
    this.reset();
    this.initializeCharts();
    this.updateDisplay();
  }

  destroy() {
    this.stopAnimation();
    Object.values(this.charts).forEach(chart => chart?.destroy?.());
    const container = document.getElementById(this.containerId);
    if (container) container.innerHTML = '';
  }

  getComparisonBadges() {
    if (!this.allStrategies || this.allStrategies.length <= 1) return '';

    const optimal = this.allStrategies[0];
    let html = '<div class="lv-comparison-section" title="Compare strategies - hover to see differences">';

    for (let i = 1; i < Math.min(3, this.allStrategies.length); i++) {
      const strategy = this.allStrategies[i];
      const timeDelta = (strategy.total_time_seconds || 0) - (optimal.total_time_seconds || 0);
      const sign = timeDelta > 0 ? '+' : '';
      const color = timeDelta > 0 ? '#ff6b6b' : '#51cf66';

      html += `
        <div class="lv-comparison-item" style="color: ${color}">
          <span>${strategy.name}</span>
          <span>${sign}${timeDelta.toFixed(2)}s</span>
        </div>
      `;
    }

    html += '</div>';
    return html;
  }

  formatTime(seconds) {
    if (typeof seconds !== 'number') return '-';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = (seconds % 60).toFixed(3);
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(6, '0')}`;
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = LapVisualizer;
}
