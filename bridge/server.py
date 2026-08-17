import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Listen on ALL network interfaces.
# This allows both the PC and your Android phone to connect.
HOST = "0.0.0.0"
PORT = 8080

EA_DATA = {
    "connected": False,
    "ea": "GhostkillerPro",
    "last_heartbeat": None,
    "data": {}
}


class BridgeHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):

        body = json.dumps(data).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(body)


    def do_GET(self):

        path = self.path.split("?")[0]

        if path == "/":

            self.send_json({
                "name": "Sydney AI Master MT5 Bridge",
                "status": "online",
                "port": PORT,
                "mode": "read-only"
            })

            return


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

                "time":
                    EA_DATA["last_heartbeat"]
                    or datetime.now().isoformat()

            })

            return


        if path == "/api/account":

            data = EA_DATA["data"]

            self.send_json({

                "broker":
                    data.get(
                        "broker",
                        "MT5"
                    ),

                "platform":
                    "MetaTrader 5",

                "symbol":
                    data.get(
                        "symbol",
                        "XAUUSD"
                    ),

                "timeframe":
                    data.get(
                        "timeframe",
                        "M5"
                    ),

                "balance":
                    data.get(
                        "balance",
                        0
                    ),

                "equity":
                    data.get(
                        "equity",
                        0
                    ),

                "currency":
                    data.get(
                        "currency",
                        ""
                    )

            })

            return


        if path == "/api/ea":

            data = EA_DATA["data"]

            self.send_json({

                "name":
                    EA_DATA["ea"],

                "running":
                    EA_DATA["connected"],

                "symbol":
                    data.get(
                        "symbol",
                        "XAUUSD"
                    ),

                "timeframe":
                    data.get(
                        "timeframe",
                        "M5"
                    ),

                "lot_size":
                    data.get(
                        "lot_size",
                        0
                    ),

                "open_trades":
                    data.get(
                        "open_trades",
                        0
                    )

            })

            return


        if path == "/api/signal":

            data = EA_DATA["data"]

            self.send_json({

                "symbol":
                    data.get(
                        "symbol",
                        "XAUUSD"
                    ),

                "timeframe":
                    data.get(
                        "timeframe",
                        "M5"
                    ),

                "direction":
                    data.get(
                        "direction",
                        "NO TRADE"
                    ),

                "confidence":
                    data.get(
                        "confidence",
                        0
                    ),

                "decision":
                    data.get(
                        "decision",
                        "NO TRADE"
                    )

            })

            return


        if path == "/api/trades":

            data = EA_DATA["data"]

            trades = data.get(
                "trades",
                []
            )

            self.send_json({
                "trades": trades
            })

            return


        if path == "/api/health":

            self.send_json({

                "bridge": "online",

                "host": HOST,

                "port": PORT,

                "pc_ip":
                    "192.168.0.135",

                "ea_connected":
                    EA_DATA["connected"],

                "time":
                    datetime.now().isoformat()

            })

            return


        self.send_json({

            "error":
                "Endpoint not found",

            "path":
                path

        }, 404)


    def do_POST(self):

        path = self.path.split("?")[0]

        print(
            datetime.now().isoformat(),
            "POST:",
            path
        )

        if path != "/api/ea/heartbeat":

            self.send_json({

                "error":
                    "POST endpoint not found",

                "path":
                    path

            }, 404)

            return


        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
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

                        "raw":
                            raw_data.decode(
                                "utf-8",
                                errors="ignore"
                            )

                    }

            else:

                data = {}


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
                EA_DATA["ea"]
            )


            self.send_json({

                "ok": True,

                "connected": True,

                "mode":
                    "read-only",

                "mt5":
                    "connected",

                "ea":
                    EA_DATA["ea"],

                "time":
                    EA_DATA["last_heartbeat"]

            })


        except Exception as error:

            print(
                "Heartbeat error:",
                error
            )

            self.send_json({

                "ok": False,

                "error":
                    str(error)

            }, 400)


    def do_OPTIONS(self):

        self.send_response(200)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()


    def log_message(
        self,
        format,
        *args
    ):

        print(
            datetime.now().isoformat(),
            "-",
            format % args
        )


print("")
print("==============================")
print(" Sydney AI Master MT5 Bridge")
print("==============================")
print("")
print("Bridge: ONLINE")
print("")
print("PC:     http://127.0.0.1:8080")
print("LAN:    http://192.168.0.135:8080")
print("")
print("Mode: READ-ONLY")
print("")
print("Waiting for GhostkillerPro...")
print("")


server = ThreadingHTTPServer(
    (HOST, PORT),
    BridgeHandler
)


try:

    server.serve_forever()

except KeyboardInterrupt:

    print("")
    print("Bridge stopped.")

finally:

    server.server_close()