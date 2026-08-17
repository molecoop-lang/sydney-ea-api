```python
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ============================================================
# SERVER CONFIGURATION
# ============================================================

# Render provides PORT automatically.
# When running locally, it falls back to 8080.
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8080"))

# ============================================================
# EA DATA
# ============================================================

EA_DATA = {
    "connected": False,
    "ea": "GhostkillerPro",
    "last_heartbeat": None,
    "data": {},
}


# ============================================================
# HTTP HANDLER
# ============================================================

class BridgeHandler(BaseHTTPRequestHandler):

    # --------------------------------------------------------
    # JSON RESPONSE
    # --------------------------------------------------------

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json",
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*",
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.end_headers()

        self.wfile.write(body)

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def do_GET(self):

        path = self.path.split("?")[0]

        # ----------------------------------------------------
        # HEALTH CHECK
        # ----------------------------------------------------

        if path == "/":

            self.send_json({
                "service": "Sydney AI Master MT5 Bridge",
                "status": "online",
                "mode": "read-only",
                "ea": EA_DATA["ea"],
                "time": datetime.now().isoformat(),
            })

            return

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if path == "/api/status":

            self.send_json({
                "connected": EA_DATA["connected"],
                "mode": "read-only",
                "mt5": (
                    "connected"
                    if EA_DATA["connected"]
                    else "waiting_for_ea"
                ),
                "ea": EA_DATA["ea"],
                "time": (
                    EA_DATA["last_heartbeat"]
                    or datetime.now().isoformat()
                ),
            })

            return

        # ----------------------------------------------------
        # ACCOUNT
        # ----------------------------------------------------

        if path == "/api/account":

            data = EA_DATA["data"]

            self.send_json({
                "broker": data.get(
                    "broker",
                    "MT5",
                ),
                "platform": "MetaTrader 5",
                "symbol": data.get(
                    "symbol",
                    "XAUUSD",
                ),
                "timeframe": data.get(
                    "timeframe",
                    "M5",
                ),
                "balance": data.get(
                    "balance",
                    0,
                ),
                "equity": data.get(
                    "equity",
                    0,
                ),
                "currency": data.get(
                    "currency",
                    "",
                ),
            })

            return

        # ----------------------------------------------------
        # EA
        # ----------------------------------------------------

        if path == "/api/ea":

            data = EA_DATA["data"]

            self.send_json({
                "name": EA_DATA["ea"],
                "running": EA_DATA["connected"],
                "symbol": data.get(
                    "symbol",
                    "XAUUSD",
                ),
                "timeframe": data.get(
                    "timeframe",
                    "M5",
                ),
                "lot_size": data.get(
                    "lot_size",
                    0,
                ),
                "open_trades": data.get(
                    "open_trades",
                    0,
                ),
            })

            return

        # ----------------------------------------------------
        # AI SIGNAL
        # ----------------------------------------------------

        if path == "/api/signal":

            data = EA_DATA["data"]

            self.send_json({
                "symbol": data.get(
                    "symbol",
                    "XAUUSD",
                ),
                "timeframe": data.get(
                    "timeframe",
                    "M5",
                ),
                "direction": data.get(
                    "direction",
                    "NO TRADE",
                ),
                "confidence": data.get(
                    "confidence",
                    0,
                ),
                "decision": data.get(
                    "decision",
                    "NO TRADE",
                ),
                "trend": data.get(
                    "trend",
                    "Unknown",
                ),
                "liquidity_sweep": data.get(
                    "liquidity_sweep",
                    False,
                ),
                "bos": data.get(
                    "bos",
                    False,
                ),
                "choch": data.get(
                    "choch",
                    False,
                ),
                "order_block": data.get(
                    "order_block",
                    False,
                ),
                "fvg": data.get(
                    "fvg",
                    False,
                ),
            })

            return

        # ----------------------------------------------------
        # TRADES
        # ----------------------------------------------------

        if path == "/api/trades":

            data = EA_DATA["data"]

            trades = data.get(
                "trades",
                [],
            )

            self.send_json({
                "trades": trades,
            })

            return

        # ----------------------------------------------------
        # NOT FOUND
        # ----------------------------------------------------

        self.send_json({
            "error": "Endpoint not found",
            "path": path,
        }, 404)

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    def do_POST(self):

        path = self.path.split("?")[0]

        print(
            datetime.now().isoformat(),
            "POST:",
            path,
        )

        # ----------------------------------------------------
        # EA HEARTBEAT
        # ----------------------------------------------------

        if path != "/api/ea/heartbeat":

            self.send_json({
                "error": "POST endpoint not found",
                "path": path,
            }, 404)

            return

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            raw_data = self.rfile.read(
                content_length
            )

            if raw_data:

                try:

                    data = json.loads(
                        raw_data.decode(
                            "utf-8"
                        )
                    )

                except Exception:

                    data = {
                        "raw": raw_data.decode(
                            "utf-8",
                            errors="ignore",
                        )
                    }

            else:

                data = {}

            # ------------------------------------------------
            # UPDATE EA STATUS
            # ------------------------------------------------

            EA_DATA["connected"] = True

            EA_DATA["last_heartbeat"] = (
                datetime.now().isoformat()
            )

            if isinstance(data, dict):

                EA_DATA["data"] = data

                if data.get("ea"):

                    EA_DATA["ea"] = data["ea"]

            print(
                "EA HEARTBEAT RECEIVED:",
                EA_DATA["ea"],
            )

            self.send_json({

                "ok": True,

                "connected": True,

                "mode": "read-only",

                "mt5": "connected",

                "ea": EA_DATA["ea"],

                "time":
                    EA_DATA["last_heartbeat"],

            }, 200)

        except Exception as error:

            print(
                "Heartbeat error:",
                error,
            )

            self.send_json({

                "ok": False,

                "error": str(error),

            }, 400)

    # --------------------------------------------------------
    # OPTIONS / CORS
    # --------------------------------------------------------

    def do_OPTIONS(self):

        self.send_response(200)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*",
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )

        self.end_headers()

    # --------------------------------------------------------
    # LOGGING
    # --------------------------------------------------------

    def log_message(
        self,
        format,
        *args,
    ):

        print(
            datetime.now().isoformat(),
            "-",
            format % args,
        )


# ============================================================
# START SERVER
# ============================================================

print("")
print("==============================")
print(" Sydney AI Master MT5 Bridge")
print("==============================")
print("")
print("Bridge: ONLINE")
print("Host:", HOST)
print("Port:", PORT)
print("Mode: READ-ONLY")
print("")
print("Waiting for GhostkillerPro...")
print("")

server = ThreadingHTTPServer(
    (HOST, PORT),
    BridgeHandler,
)

try:

    server.serve_forever()

except KeyboardInterrupt:

    print("")
    print("Bridge stopped.")

finally:

    server.server_close()
```