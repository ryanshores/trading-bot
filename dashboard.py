"""
Web Dashboard for Trading Bot
Real-time performance visualization

Run with:
    Development: python dashboard.py
    Production: gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 --bind 0.0.0.0:5000 dashboard:app
"""

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY", "dev-secret-change-in-production"
)

# Initialize SocketIO with gevent (recommended for production)
try:
    from gevent import monkey

    monkey.patch_all()  # Required for gevent
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")
    ASYNC_MODE = "gevent"
except ImportError:
    # Fallback to threading for development
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
    ASYNC_MODE = "threading"

# Global state for dashboard
dashboard_data = {
    "balance": 10000.0,
    "open_positions": [],
    "trades": [],
    "pnl": 0.0,
    "win_rate": 0.0,
    "last_update": None,
}


def update_data(data: Dict):
    """Update dashboard data and broadcast to connected clients"""
    global dashboard_data
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


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


# Socket.IO Events
@socketio.on("connect")
def handle_connect():
    """Handle client connection"""
    emit("update", dashboard_data)


@socketio.on("request_update")
def handle_request_update():
    """Handle client requesting data update"""
    emit("update", dashboard_data)


# Development entry point
# For production, use: gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 --bind 0.0.0.0:5000 dashboard:app
if __name__ == "__main__":
    print("📊 Starting Dashboard Server")
    print("=" * 70)
    if ASYNC_MODE == "gevent":
        print("✓ Using gevent (production mode)")
    else:
        print("⚠ gevent not installed, using threading (development mode)")
        print("  For production, install: pip install gevent gevent-websocket")
    print()
    print("For production deployment, use:")
    print("  gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \\")
    print("           -w 1 --bind 0.0.0.0:5000 dashboard:app")
    print("=" * 70)

    # Development server
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
