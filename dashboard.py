"""
Web Dashboard for Trading Bot
Real-time performance visualization
"""

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import json
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import threading

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY", "dev-secret-change-in-production"
)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state with thread-safe access
dashboard_data = {
    "balance": 10000.0,
    "open_positions": [],
    "trades": [],
    "pnl": 0.0,
    "win_rate": 0.0,
    "last_update": None,
}
data_lock = threading.Lock()


class DashboardServer:
    """Dashboard server that runs alongside the trading bot"""

    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.thread = None

    def start(self):
        """Start dashboard in background thread"""

        def run():
            socketio.run(
                app, host=self.host, port=self.port, debug=False, use_reloader=False
            )

        self.thread = threading.Thread(target=run)
        self.thread.daemon = True
        self.thread.start()
        print(f"📊 Dashboard running at http://{self.host}:{self.port}")

    def update_data(self, data: Dict):
        """Update dashboard data"""
        global dashboard_data
        with data_lock:
            dashboard_data.update(data)
            dashboard_data["last_update"] = datetime.now().isoformat()
            socketio.emit("update", dashboard_data)


# Flask Routes
@app.route("/")
def index():
    """Main dashboard page"""
    return render_template("dashboard.html")


@app.route("/api/status")
def api_status():
    """API endpoint for current status"""
    return jsonify(dashboard_data)


@app.route("/api/trades")
def api_trades():
    """API endpoint for trade history"""
    return jsonify(dashboard_data.get("trades", []))


@app.route("/api/positions")
def api_positions():
    """API endpoint for open positions"""
    return jsonify(dashboard_data.get("open_positions", []))


@socketio.on("connect")
def handle_connect():
    """Handle client connection"""
    emit("update", dashboard_data)


# HTML Template (normally would be in templates/dashboard.html)
@app.route("/static/dashboard.html")
def serve_dashboard_html():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Bot Dashboard</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #fff;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #1a1f3a;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #2a2f4a;
        }
        .stat-card h3 {
            color: #8892b0;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
        }
        .positive { color: #00d084; }
        .negative { color: #ff4757; }
        .neutral { color: #ffd700; }
        .chart-container {
            background: #1a1f3a;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            height: 400px;
        }
        .trades-table {
            background: #1a1f3a;
            border-radius: 10px;
            overflow: hidden;
        }
        .trades-table table {
            width: 100%;
            border-collapse: collapse;
        }
        .trades-table th,
        .trades-table td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #2a2f4a;
        }
        .trades-table th {
            background: #2a2f4a;
            color: #8892b0;
            text-transform: uppercase;
            font-size: 0.8em;
        }
        .trades-table tr:hover {
            background: #2a2f4a;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 10px;
        }
        .status-online { background: #00d084; }
        .status-offline { background: #ff4757; }
        .last-update {
            text-align: center;
            color: #8892b0;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Trading Bot Dashboard</h1>
        <p><span class="status-indicator status-online"></span>Bot Online</p>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <h3>Current Balance</h3>
            <div class="stat-value" id="balance">$10,000.00</div>
        </div>
        <div class="stat-card">
            <h3>Total PnL</h3>
            <div class="stat-value" id="pnl">$0.00</div>
        </div>
        <div class="stat-card">
            <h3>Win Rate</h3>
            <div class="stat-value neutral" id="win-rate">0%</div>
        </div>
        <div class="stat-card">
            <h3>Open Positions</h3>
            <div class="stat-value" id="open-positions">0</div>
        </div>
    </div>
    
    <div class="chart-container">
        <canvas id="pnlChart"></canvas>
    </div>
    
    <div class="trades-table">
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Action</th>
                    <th>Price</th>
                    <th>PnL</th>
                </tr>
            </thead>
            <tbody id="trades-body">
            </tbody>
        </table>
    </div>
    
    <div class="last-update">
        Last update: <span id="last-update">Never</span>
    </div>
    
    <script>
        const socket = io();
        let pnlChart;
        
        // Initialize chart
        function initChart() {
            const ctx = document.getElementById('pnlChart').getContext('2d');
            pnlChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Balance',
                        data: [],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: '#fff' }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#8892b0' },
                            grid: { color: '#2a2f4a' }
                        },
                        y: {
                            ticks: { color: '#8892b0' },
                            grid: { color: '#2a2f4a' }
                        }
                    }
                }
            });
        }
        
        // Update dashboard
        function updateDashboard(data) {
            // Update stats
            document.getElementById('balance').textContent = 
                '$' + (data.balance || 0).toFixed(2);
            
            const pnl = data.pnl || 0;
            const pnlEl = document.getElementById('pnl');
            pnlEl.textContent = (pnl >= 0 ? '+' : '') + '$' + pnl.toFixed(2);
            pnlEl.className = 'stat-value ' + (pnl >= 0 ? 'positive' : 'negative');
            
            document.getElementById('win-rate').textContent = 
                (data.win_rate || 0).toFixed(1) + '%';
            document.getElementById('open-positions').textContent = 
                (data.open_positions || []).length;
            
            // Update trades table
            const tbody = document.getElementById('trades-body');
            tbody.innerHTML = '';
            (data.trades || []).slice(-10).reverse().forEach(trade => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>${new Date(trade.timestamp).toLocaleTimeString()}</td>
                    <td>${trade.action || 'CLOSE'}</td>
                    <td>$${(trade.price || 0).toFixed(2)}</td>
                    <td class="${(trade.pnl || 0) >= 0 ? 'positive' : 'negative'}">
                        ${(trade.pnl || 0) >= 0 ? '+' : ''}$${(trade.pnl || 0).toFixed(2)}
                    </td>
                `;
            });
            
            // Update chart
            if (pnlChart && data.balance_history) {
                pnlChart.data.labels = data.balance_history.map((_, i) => i);
                pnlChart.data.datasets[0].data = data.balance_history;
                pnlChart.update();
            }
            
            // Update timestamp
            document.getElementById('last-update').textContent = 
                data.last_update ? new Date(data.last_update).toLocaleString() : 'Never';
        }
        
        // Socket events
        socket.on('connect', () => {
            console.log('Connected to dashboard');
        });
        
        socket.on('update', (data) => {
            updateDashboard(data);
        });
        
        // Initialize
        initChart();
        
        // Fetch initial data
        fetch('/api/status')
            .then(r => r.json())
            .then(data => updateDashboard(data));
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    server = DashboardServer()
    server.start()

    # Keep running
    try:
        while True:
            import time

            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
