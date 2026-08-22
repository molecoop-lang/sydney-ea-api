import base64
import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8080"))
BRIDGE_TOKEN = os.environ.get("BRIDGE_TOKEN", "sydney-ea-transfer-2026")
UPLOAD_DIR = Path(os.environ.get("EA_UPLOAD_DIR", "/tmp/sydney_ea_uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_EA_BYTES = 8 * 1024 * 1024

EA_DATA = {"connected": False, "ea": "GhostkillerPro", "last_heartbeat": None, "data": {}}
MT5_ACCOUNT = {"connected": False, "last_update": None, "data": {}}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def safe_name(name):
    name = os.path.basename(str(name or "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.(ex5|mq5)", name, re.IGNORECASE):
        raise ValueError("Only simple .ex5 or .mq5 filenames are allowed")
    return name

def current_upload():
    manifest = UPLOAD_DIR / "manifest.json"
    if not manifest.exists():
        return None
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return None

class BridgeHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Bridge-Token")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        return self.headers.get("X-Bridge-Token", "") == BRIDGE_TOKEN

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Bridge-Token")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        data = EA_DATA["data"]
        if path == "/":
            self.send_json({"service": "Sydney AI Master MT5 Bridge", "status": "online", "mode": "cloud-bridge", "ea": EA_DATA["ea"], "time": utc_now()})
            return
        if path == "/api/status":
            mt5_connected = MT5_ACCOUNT["connected"]
            self.send_json({
                "connected": mt5_connected or EA_DATA["connected"],
                "mt5_connected": mt5_connected,
                "ea_connected": EA_DATA["connected"],
                "mode": "cloud-bridge",
                "mt5": "connected" if mt5_connected else ("waiting_for_mt5"),
                "ea": EA_DATA["ea"],
                "time": MT5_ACCOUNT["last_update"] or EA_DATA["last_heartbeat"]
            })
            return
        if path == "/api/account":
            account = MT5_ACCOUNT["data"]
            self.send_json({
                "connected": MT5_ACCOUNT["connected"],
                "broker": account.get("broker", data.get("broker", "MT5")),
                "server": account.get("server", ""),
                "login": account.get("login", ""),
                "account": account.get("login", ""),
                "platform": "MetaTrader 5",
                "symbol": data.get("symbol", account.get("symbol", "XAUUSD")),
                "timeframe": data.get("timeframe", account.get("timeframe", "M5")),
                "balance": account.get("balance", data.get("balance", 0)),
                "equity": account.get("equity", data.get("equity", 0)),
                "currency": account.get("currency", data.get("currency", "")),
                "margin": account.get("margin", 0),
                "free_margin": account.get("free_margin", 0),
                "leverage": account.get("leverage", 0),
                "terminal_connected": account.get("terminal_connected", False),
                "last_update": MT5_ACCOUNT["last_update"]
            })
            return
        if path == "/api/ea":
            self.send_json({"name": EA_DATA["ea"], "running": EA_DATA["connected"], "symbol": data.get("symbol", "XAUUSD"), "timeframe": data.get("timeframe", "M5"), "lot_size": data.get("lot_size", 0), "open_trades": data.get("open_trades", 0)})
            return
        if path == "/api/signal":
            self.send_json({"symbol": data.get("symbol", "XAUUSD"), "timeframe": data.get("timeframe", "M5"), "direction": data.get("direction", "NO TRADE"), "confidence": data.get("confidence", 0), "decision": data.get("decision", "NO TRADE"), "trend": data.get("trend", "Unknown"), "liquidity_sweep": data.get("liquidity_sweep", False), "bos": data.get("bos", False), "choch": data.get("choch", False), "order_block": data.get("order_block", False), "fvg": data.get("fvg", False)})
            return
        if path == "/api/trades":
            self.send_json({"trades": data.get("trades", [])})
            return
        if path == "/api/scan":
            fields = data
            checks = [
                ("liquidity_sweep", 15), ("bos", 10), ("choch", 10),
                ("order_block", 10), ("fvg", 10), ("ote", 5),
                ("atr", 5), ("volume_expansion", 5), ("kill_zone", 5),
            ]
            components = {
                "h1_trend": 20 if fields.get("trend") in ("Bullish", "Bearish") else 0,
                "adx": 10 if float(fields.get("adx", 0) or 0) > 25 else 0,
            }
            for key, points in checks:
                components[key] = points if bool(fields.get(key, False)) else 0
            components["session"] = components.pop("kill_zone")
            score = sum(components.values())
            missing = [key for key in ("liquidity_sweep", "bos", "choch", "order_block", "fvg") if not fields.get(key, False)]
            ready = score >= 95 and not missing
            direction = fields.get("direction", "NO TRADE") if ready else "NO TRADE"
            self.send_json({
                "symbol": fields.get("symbol", "XAUUSD"), "timeframe": fields.get("timeframe", "M5"),
                "direction": direction, "confidence": score, "max_confidence": 105,
                "decision": direction, "trend": fields.get("trend", "Neutral"),
                "adx": float(fields.get("adx", 0) or 0), "atr": float(fields.get("atr", 0) or 0),
                "liquidity_sweep": bool(fields.get("liquidity_sweep", False)),
                "bos": bool(fields.get("bos", False)), "choch": bool(fields.get("choch", False)),
                "order_block": bool(fields.get("order_block", False)), "fvg": bool(fields.get("fvg", False)),
                "ote": bool(fields.get("ote", False)), "volume_expansion": bool(fields.get("volume_expansion", False)),
                "kill_zone": bool(fields.get("kill_zone", False)), "components": components,
                "missing_confirmation": missing, "scan_ready": ready,
                "source": "live MT5 EA heartbeat telemetry",
                "message": "95+ confirmation available." if ready else "Full 95+ SMC confirmation is unavailable until the EA sends the missing SMC fields.",
                "scanned_at": utc_now(),
            })
            return
        if path == "/api/ea/install-status":
            if not self.authorized():
                self.send_json({"error": "Unauthorized"}, 401); return
            upload = current_upload()
            self.send_json(upload or {"uploaded": False, "message": "No EA uploaded"})
            return
        if path == "/api/ea/file-status":
            if not self.authorized():
                self.send_json({"error": "Unauthorized"}, 401); return
            upload = current_upload()
            self.send_json(upload or {"uploaded": False, "message": "No EA uploaded"})
            return
        if path == "/api/ea/manifest":
            if not self.authorized():
                self.send_json({"error": "Unauthorized"}, 401); return
            upload = current_upload()
            self.send_json(upload or {"uploaded": False, "message": "No EA uploaded"})
            return
        if path == "/api/ea/download":
            if not self.authorized():
                self.send_json({"error": "Unauthorized"}, 401); return
            upload = current_upload()
            if not upload:
                self.send_json({"error": "No EA uploaded"}, 404); return
            file_path = UPLOAD_DIR / upload["file_name"]
            if not file_path.exists():
                self.send_json({"error": "EA file missing"}, 404); return
            body = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{upload["file_name"]}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_json({"error": "Endpoint not found", "path": path}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/ea/upload":
            if not self.authorized():
                self.send_json({"error": "Unauthorized"}, 401); return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 12 * 1024 * 1024:
                    self.send_json({"error": "Invalid upload size"}, 413); return
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                name = safe_name(payload.get("file_name"))
                raw = base64.b64decode(payload.get("content_base64", ""), validate=True)
                if len(raw) > MAX_EA_BYTES:
                    self.send_json({"error": "EA file exceeds 8 MB limit"}, 413); return
                if not raw:
                    self.send_json({"error": "Empty EA file"}, 400); return
                (UPLOAD_DIR / name).write_bytes(raw)
                manifest = {
                    "uploaded": True, "file_name": name, "size": len(raw),
                    "uploaded_at": utc_now(), "install_status": "waiting_for_mt5_bridge",
                    "message": "EA uploaded. Waiting for the PC MT5 bridge agent."
                }
                (UPLOAD_DIR / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                self.send_json(manifest)
            except Exception as error:
                self.send_json({"error": str(error)}, 400)
            return
        if path == "/api/ea/install-status":
            if not self.authorized():
                self.send_json({"error": "Unauthorized"}, 401); return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                upload = current_upload() or {}
                upload.update({
                    "install_status": payload.get("status", "unknown"),
                    "installed_paths": payload.get("installed_paths", []),
                    "install_message": payload.get("message", ""),
                    "installed_at": utc_now(),
                })
                (UPLOAD_DIR / "manifest.json").write_text(json.dumps(upload), encoding="utf-8")
                self.send_json(upload)
            except Exception as error:
                self.send_json({"error": str(error)}, 400)
            return
        if path == "/api/mt5/account":
            if not self.authorized():
                self.send_json({"error": "Unauthorized"}, 401); return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                payload = json.loads(raw.decode("utf-8")) if raw else {}
                if not isinstance(payload, dict):
                    raise ValueError("Account telemetry must be a JSON object")
                MT5_ACCOUNT["connected"] = bool(payload.get("connected", True))
                MT5_ACCOUNT["last_update"] = utc_now()
                MT5_ACCOUNT["data"] = payload
                self.send_json({"ok": True, "connected": MT5_ACCOUNT["connected"], "time": MT5_ACCOUNT["last_update"]})
            except Exception as error:
                self.send_json({"ok": False, "error": str(error)}, 400)
            return
        if path != "/api/ea/heartbeat":
            self.send_json({"error": "POST endpoint not found", "path": path}, 404); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8")) if raw else {}
            EA_DATA["connected"] = True
            EA_DATA["last_heartbeat"] = utc_now()
            if isinstance(data, dict):
                EA_DATA["data"] = data
                if data.get("ea"):
                    EA_DATA["ea"] = data["ea"]
            self.send_json({"ok": True, "connected": True, "mode": "cloud-bridge", "mt5": "connected", "ea": EA_DATA["ea"], "time": EA_DATA["last_heartbeat"]})
        except Exception as error:
            self.send_json({"ok": False, "error": str(error)}, 400)

    def log_message(self, format_string, *args):
        print(utc_now(), "-", format_string % args)

def main():
    print("Sydney AI Master cloud bridge online on", PORT)
    ThreadingHTTPServer((HOST, PORT), BridgeHandler).serve_forever()

if __name__ == "__main__":
    main()
