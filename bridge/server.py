import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8080"))
EA_DATA = {"connected": False, "ea": "GhostkillerPro", "last_heartbeat": None, "data": {}}


def build_scan(data):
    """Build a transparent 105-point scan from live EA telemetry.

    The current EA heartbeat exposes regime/EMA/ADX/ATR. SMC fields are
    accepted when supplied by a future EA build but are not invented.
    """
    regime = int(data.get("regime_direction", 0) or 0)
    adx = float(data.get("regime_adx", 0) or 0)
    atr = float(data.get("regime_atr", 0) or 0)
    ema_bull = bool(data.get("ema_bullish", False))
    ema_bear = bool(data.get("ema_bearish", False))

    trend = "Bullish" if regime > 0 else "Bearish" if regime < 0 else "Neutral"
    direction = "BUY" if regime > 0 and ema_bull else "SELL" if regime < 0 and ema_bear else "NO TRADE"

    components = {
        "h1_trend": 20 if regime != 0 else 0,
        "adx": 10 if adx >= 30 else 0,
        "liquidity_sweep": 15 if bool(data.get("liquidity_sweep", False)) else 0,
        "bos": 10 if bool(data.get("bos", False)) else 0,
        "choch": 10 if bool(data.get("choch", False)) else 0,
        "order_block": 10 if bool(data.get("order_block", False)) else 0,
        "fvg": 10 if bool(data.get("fvg", False)) else 0,
        "ote": 5 if bool(data.get("ote", False)) else 0,
        "atr": 5 if atr > 0 else 0,
        "volume": 5 if bool(data.get("volume_expansion", False)) else 0,
        "session": 5 if bool(data.get("kill_zone", False)) else 0,
    }
    confidence = sum(components.values())

    critical = ["liquidity_sweep", "bos", "choch", "order_block", "fvg"]
    missing = [key for key in critical if not bool(data.get(key, False))]
    ready = confidence >= 95 and not missing and direction != "NO TRADE"

    if ready:
        decision = direction
    else:
        decision = "NO TRADE"

    return {
        "symbol": data.get("symbol", "XAUUSD"),
        "timeframe": data.get("timeframe", "M5"),
        "direction": decision,
        "confidence": confidence,
        "max_confidence": 105,
        "decision": decision,
        "trend": trend,
        "adx": adx,
        "atr": atr,
        "liquidity_sweep": bool(data.get("liquidity_sweep", False)),
        "bos": bool(data.get("bos", False)),
        "choch": bool(data.get("choch", False)),
        "order_block": bool(data.get("order_block", False)),
        "fvg": bool(data.get("fvg", False)),
        "ote": bool(data.get("ote", False)),
        "volume_expansion": bool(data.get("volume_expansion", False)),
        "kill_zone": bool(data.get("kill_zone", False)),
        "components": components,
        "missing_confirmation": missing,
        "scan_ready": ready,
        "source": "live MT5 EA heartbeat telemetry",
        "message": "Full 95+ SMC confirmation is unavailable until the EA sends the missing SMC fields." if missing else "Scanner evaluated live EA telemetry.",
        "scanned_at": datetime.now().isoformat(),
    }


class BridgeHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        data = EA_DATA["data"]
        if path == "/":
            self.send_json({"service": "Sydney AI Master MT5 Bridge", "status": "online", "mode": "read-only", "ea": EA_DATA["ea"], "time": datetime.now().isoformat()})
            return
        if path == "/api/status":
            self.send_json({"connected": EA_DATA["connected"], "mode": "read-only", "mt5": "connected" if EA_DATA["connected"] else "waiting_for_ea", "ea": EA_DATA["ea"], "time": EA_DATA["last_heartbeat"]})
            return
        if path == "/api/account":
            self.send_json({"broker": data.get("broker", "MT5"), "platform": "MetaTrader 5", "symbol": data.get("symbol", "XAUUSD"), "timeframe": data.get("timeframe", "M5"), "balance": data.get("balance", 0), "equity": data.get("equity", 0), "currency": data.get("currency", "")})
            return
        if path == "/api/ea":
            self.send_json({"name": EA_DATA["ea"], "running": EA_DATA["connected"], "symbol": data.get("symbol", "XAUUSD"), "timeframe": data.get("timeframe", "M5"), "lot_size": data.get("lot_size", 0), "open_trades": data.get("open_trades", 0)})
            return
        if path == "/api/signal":
            self.send_json({"symbol": data.get("symbol", "XAUUSD"), "timeframe": data.get("timeframe", "M5"), "direction": data.get("direction", "NO TRADE"), "confidence": data.get("confidence", 0), "decision": data.get("decision", "NO TRADE"), "trend": data.get("trend", "Unknown"), "liquidity_sweep": data.get("liquidity_sweep", False), "bos": data.get("bos", False), "choch": data.get("choch", False), "order_block": data.get("order_block", False), "fvg": data.get("fvg", False)})
            return
        if path == "/api/scan":
            self.send_json(build_scan(data))
            return
        if path == "/api/trades":
            self.send_json({"trades": data.get("trades", [])})
            return
        self.send_json({"error": "Endpoint not found", "path": path}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        if path != "/api/ea/heartbeat":
            self.send_json({"error": "POST endpoint not found", "path": path}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8")) if raw else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                data = {}
            EA_DATA["connected"] = True
            EA_DATA["last_heartbeat"] = datetime.now().isoformat()
            if isinstance(data, dict):
                EA_DATA["data"] = data
                if data.get("ea"):
                    EA_DATA["ea"] = data["ea"]
            print("EA HEARTBEAT RECEIVED:", EA_DATA["ea"])
            self.send_json({"ok": True, "connected": True, "mode": "read-only", "mt5": "connected", "ea": EA_DATA["ea"], "time": EA_DATA["last_heartbeat"]})
        except Exception as error:
            print("Heartbeat error:", error)
            self.send_json({"ok": False, "error": str(error)}, 400)

    def log_message(self, format_string, *args):
        print(datetime.now().isoformat(), "-", format_string % args)

def main():
    print("==============================")
    print(" Sydney AI Master MT5 Bridge")
    print("==============================")
    print("Bridge: ONLINE")
    print("Host:", HOST)
    print("Port:", PORT)
    print("Mode: READ-ONLY")
    print("Waiting for GhostkillerPro...")
    print()
    server = ThreadingHTTPServer((HOST, PORT), BridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Bridge stopped.")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
