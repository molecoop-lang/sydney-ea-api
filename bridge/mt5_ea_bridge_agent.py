import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

CLOUD_URL = os.environ.get("SYDNEY_CLOUD_URL", "https://sydney-ea-api-1.onrender.com").rstrip("/")
TOKEN = os.environ.get("BRIDGE_TOKEN", "sydney-ea-transfer-2026")
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "5"))
ACCOUNT_POLL_SECONDS = int(os.environ.get("ACCOUNT_POLL_SECONDS", "5"))

def headers():
    return {"X-Bridge-Token": TOKEN}

def get_json(path):
    req = Request(CLOUD_URL + path, headers=headers())
    with urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def post_json(path, payload):
    body = json.dumps(payload).encode("utf-8")
    req = Request(CLOUD_URL + path, data=body, headers={**headers(), "Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def download_file(name):
    req = Request(CLOUD_URL + "/api/ea/download", headers=headers())
    with urlopen(req, timeout=30) as r:
        return r.read()

def find_experts_dirs():
    override = os.environ.get("MT5_EXPERTS_DIR", "").strip()
    if override:
        return [Path(override)]
    root = Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
    if not root.exists():
        return []
    return sorted([p / "MQL5" / "Experts" for p in root.glob("*") if (p / "MQL5" / "Experts").is_dir()])

def read_mt5_account():
    """Read the account from the locally running MT5 terminal.

    This is read-only. No password, trading command, or order request is sent.
    """
    if mt5 is None:
        return {"connected": False, "error": "MetaTrader5 Python package is not installed"}

    try:
        if not mt5.initialize():
            return {
                "connected": False,
                "error": f"MT5 initialize failed: {mt5.last_error()}"
            }

        info = mt5.account_info()
        terminal = mt5.terminal_info()
        if info is None:
            return {
                "connected": False,
                "error": f"MT5 account_info failed: {mt5.last_error()}"
            }

        result = {
            "connected": True,
            "terminal_connected": bool(getattr(terminal, "connected", True)) if terminal else True,
            "broker": str(getattr(info, "company", "") or ""),
            "server": str(getattr(info, "server", "") or ""),
            "login": int(getattr(info, "login", 0) or 0),
            "currency": str(getattr(info, "currency", "") or ""),
            "balance": float(getattr(info, "balance", 0.0) or 0.0),
            "equity": float(getattr(info, "equity", 0.0) or 0.0),
            "margin": float(getattr(info, "margin", 0.0) or 0.0),
            "free_margin": float(getattr(info, "margin_free", 0.0) or 0.0),
            "leverage": int(getattr(info, "leverage", 0) or 0),
        }
        return result
    except Exception as error:
        return {"connected": False, "error": str(error)}


def install_to_mt5(name, data):
    dirs = find_experts_dirs()
    if not dirs:
        raise RuntimeError("No MT5 MQL5\\Experts folder found. Set MT5_EXPERTS_DIR to the correct folder.")
    installed = []
    for folder in dirs:
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / name
        target.write_bytes(data)
        installed.append(str(target))
    return installed

def main():
    print("Sydney AI Master MT5 EA installer agent")
    print("Cloud:", CLOUD_URL)
    print("Polling every", POLL_SECONDS, "seconds")
    last_seen = None
    last_account_poll = 0.0
    while True:
        try:
            # Read-only MT5 account telemetry.
            now = time.time()
            if now - last_account_poll >= ACCOUNT_POLL_SECONDS:
                account = read_mt5_account()
                try:
                    post_json("/api/mt5/account", account)
                    if account.get("connected"):
                        print(
                            "MT5 account connected:",
                            account.get("broker", ""),
                            "| login:", account.get("login", ""),
                            "| balance:", account.get("balance", 0),
                            "| equity:", account.get("equity", 0),
                        )
                    else:
                        print("MT5 account offline:", account.get("error", "unknown"))
                except Exception as account_error:
                    print("Could not report MT5 account:", account_error)
                last_account_poll = now

            manifest = get_json("/api/ea/manifest")
            if manifest.get("uploaded") and manifest.get("file_name"):
                key = (manifest["file_name"], manifest.get("uploaded_at"), manifest.get("size"))
                if key != last_seen:
                    print("New EA available:", manifest["file_name"])
                    data = download_file(manifest["file_name"])
                    installed = install_to_mt5(manifest["file_name"], data)
                    print("Installed:")
                    for path in installed:
                        print("  ", path)
                    print("IMPORTANT: MT5 must refresh/reload the Experts list before attaching the EA.")
                    try:
                        post_json("/api/ea/install-status", {
                            "status": "installed",
                            "installed_paths": installed,
                            "message": "EA copied to MT5 Experts folder(s). Refresh Navigator and attach the EA to a chart."
                        })
                    except Exception as status_error:
                        print("Could not report install status:", status_error)
                    last_seen = key
        except Exception as e:
            print("Agent error:", e)
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
