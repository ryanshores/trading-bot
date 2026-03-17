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
