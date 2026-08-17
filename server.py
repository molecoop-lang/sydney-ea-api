import os
import time
import uuid
from datetime import datetime, time as dt_time
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

# ============================================================
# SYDNEY EA PYTHON API
# STEP 25
#
# Architecture:
#
# Flutter App
#      ↓
# Python FastAPI
#      ↓
# MT5 EA
#      ↓
# Broker
#
# IMPORTANT:
# This API is the control layer.
# Real MT5 execution should only happen after the EA
# confirms receipt and execution.
# ============================================================


app = FastAPI(
    title="Sydney EA Python API",
    version="25.0.0",
    description="Python bridge for Sydney EA Platform"
)


# ============================================================
# CONFIGURATION
# ============================================================

API_KEY = os.getenv(
    "SYDNEY_API_KEY",
    "CHANGE_THIS_API_KEY"
)

REMOTE_TRADING_ENABLED = False

TRADING_SYMBOL = "XAUUSD"

START_HOUR = 9
END_HOUR = 17

MIN_AI_SCORE = 95

MAX_TRADES = 5

COOLDOWN_SECONDS = 60


# ============================================================
# EA STATE
# ============================================================

ea_state = {
    "connected": False,
    "running": False,
    "heartbeat": 0,
    "last_heartbeat": None,
    "last_command": "NONE",
    "last_signal_id": None,
    "last_signal": "WAIT",
    "last_score": 0,
    "last_update": None,
}


# ============================================================
# MARKET STATE
# ============================================================

market_state = {
    "symbol": TRADING_SYMBOL,
    "bid": 0.0,
    "ask": 0.0,
    "spread": 0.0,
    "updated": None,
}


# ============================================================
# TRADE STATE
# ============================================================

trades = []

last_trade_time: Optional[float] = None


# ============================================================
# MODELS
# ============================================================

class HeartbeatRequest(BaseModel):
    ea_name: str = "Sydney EA"
    symbol: str = TRADING_SYMBOL
    broker: str = "MT5"


class MarketUpdate(BaseModel):
    symbol: str
    bid: float = Field(..., gt=0)
    ask: float = Field(..., gt=0)


class SignalRequest(BaseModel):
    symbol: str = TRADING_SYMBOL

    direction: str

    confidence: float = Field(
        ...,
        ge=0,
        le=100
    )

    signal_id: Optional[str] = None

    reason: Optional[str] = None


class TradeRequest(BaseModel):
    symbol: str = TRADING_SYMBOL

    direction: str

    volume: float = Field(
        ...,
        gt=0
    )

    confidence: float = Field(
        ...,
        ge=0,
        le=100
    )

    signal_id: Optional[str] = None

    comment: str = "Sydney AI"


class CloseTradeRequest(BaseModel):
    ticket: int


# ============================================================
# SECURITY
# ============================================================

def verify_api_key(
    authorization: Optional[str]
):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )

    if not authorization.startswith(
        "Bearer "
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization format"
        )

    supplied_key = authorization[
        len("Bearer "):
    ]

    if supplied_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )


# ============================================================
# TIME / SESSION
# ============================================================

def is_trading_session() -> bool:
    now = datetime.now().time()

    start = dt_time(
        START_HOUR,
        0,
        0
    )

    end = dt_time(
        END_HOUR,
        0,
        0
    )

    return start <= now < end


# ============================================================
# COOLDOWN
# ============================================================

def cooldown_active() -> bool:

    global last_trade_time

    if last_trade_time is None:
        return False

    elapsed = (
        time.time() - last_trade_time
    )

    return elapsed < COOLDOWN_SECONDS


def cooldown_remaining() -> int:

    global last_trade_time

    if last_trade_time is None:
        return 0

    remaining = (
        COOLDOWN_SECONDS
        - (time.time() - last_trade_time)
    )

    return max(
        0,
        int(remaining)
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "name": "Sydney EA Python API",
        "step": 25,
        "version": "25.0.0",
        "status": "online",
        "remote_trading": REMOTE_TRADING_ENABLED,
        "symbol": TRADING_SYMBOL,
        "session": "09:00-17:00",
        "minimum_ai_score": MIN_AI_SCORE,
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "api": "online",
        "time": datetime.now().isoformat(),
    }


# ============================================================
# MT5 STATUS
# ============================================================

@app.get("/mt5/status")
def mt5_status(
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    return {
        "connected": ea_state["connected"],
        "running": ea_state["running"],
        "heartbeat": ea_state["heartbeat"],
        "last_heartbeat":
            ea_state["last_heartbeat"],
        "last_command":
            ea_state["last_command"],
        "remote_trading":
            REMOTE_TRADING_ENABLED,
        "symbol": TRADING_SYMBOL,
        "session_open":
            is_trading_session(),
    }


# ============================================================
# MT5 HEARTBEAT
# ============================================================

@app.post("/mt5/heartbeat")
def mt5_heartbeat(
    request: HeartbeatRequest,
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    now = datetime.now().isoformat()

    ea_state["connected"] = True
    ea_state["heartbeat"] += 1
    ea_state["last_heartbeat"] = now
    ea_state["last_update"] = now

    return {
        "success": True,
        "message": "Heartbeat received",
        "ea_name": request.ea_name,
        "symbol": request.symbol,
        "broker": request.broker,
        "heartbeat":
            ea_state["heartbeat"],
        "server_time": now,
    }


# ============================================================
# MARKET UPDATE
# ============================================================

@app.post("/mt5/market")
def update_market(
    request: MarketUpdate,
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    if request.ask < request.bid:
        raise HTTPException(
            status_code=400,
            detail="ASK cannot be below BID"
        )

    market_state["symbol"] = request.symbol
    market_state["bid"] = request.bid
    market_state["ask"] = request.ask
    market_state["spread"] = (
        request.ask - request.bid
    )
    market_state["updated"] = (
        datetime.now().isoformat()
    )

    return {
        "success": True,
        "market": market_state
    }


# ============================================================
# MARKET DATA
# ============================================================

@app.get("/market")
def get_market(
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    return market_state


# ============================================================
# EA START
# ============================================================

@app.post("/ea/start")
def start_ea(
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    if not ea_state["connected"]:
        raise HTTPException(
            status_code=503,
            detail="EA is not connected"
        )

    ea_state["running"] = True
    ea_state["last_command"] = "START"

    return {
        "success": True,
        "running": True,
        "command": "START",
    }


# ============================================================
# EA STOP
# ============================================================

@app.post("/ea/stop")
def stop_ea(
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    ea_state["running"] = False
    ea_state["last_command"] = "STOP"

    return {
        "success": True,
        "running": False,
        "command": "STOP",
    }


# ============================================================
# EA STATE
# ============================================================

@app.get("/ea/state")
def ea_state_endpoint(
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    return {
        "running":
            ea_state["running"],
        "connected":
            ea_state["connected"],
        "last_command":
            ea_state["last_command"],
    }


# ============================================================
# SIGNAL VALIDATION
# ============================================================

def validate_signal(
    request: SignalRequest
):

    if request.symbol != TRADING_SYMBOL:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Only {TRADING_SYMBOL} "
                "is allowed"
            )
        )

    direction = request.direction.upper()

    if direction not in [
        "BUY",
        "SELL"
    ]:

        raise HTTPException(
            status_code=400,
            detail=(
                "Direction must be BUY "
                "or SELL"
            )
        )

    if request.confidence < MIN_AI_SCORE:

        raise HTTPException(
            status_code=403,
            detail=(
                f"AI confidence must be "
                f"{MIN_AI_SCORE}+"
            )
        )


# ============================================================
# RECEIVE SIGNAL
# ============================================================

@app.post("/signal")
def receive_signal(
    request: SignalRequest,
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    validate_signal(request)

    signal_id = (
        request.signal_id
        or f"SIG-{uuid.uuid4().hex[:8]}"
    )

    ea_state["last_signal_id"] = signal_id
    ea_state["last_signal"] = (
        request.direction.upper()
    )
    ea_state["last_score"] = (
        request.confidence
    )

    return {
        "success": True,
        "accepted": True,
        "signal_id": signal_id,
        "symbol": request.symbol,
        "direction":
            request.direction.upper(),
        "confidence":
            request.confidence,
        "session_open":
            is_trading_session(),
    }


# ============================================================
# LAST SIGNAL
# ============================================================

@app.get("/signal")
def get_signal(
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    return {
        "signal_id":
            ea_state["last_signal_id"],
        "signal":
            ea_state["last_signal"],
        "confidence":
            ea_state["last_score"],
    }


# ============================================================
# OPEN TRADE
# ============================================================

@app.post("/trade/open")
def open_trade(
    request: TradeRequest,
    authorization: Optional[str] = Header(
        default=None
    )
):

    global last_trade_time

    verify_api_key(
        authorization
    )

    # --------------------------------------------------------
    # HARD SAFETY CHECKS
    # --------------------------------------------------------

    if not REMOTE_TRADING_ENABLED:

        raise HTTPException(
            status_code=403,
            detail=(
                "Remote trading is disabled. "
                "Set SYDNEY_REMOTE_TRADING_ENABLED=true "
                "only when the EA/API connection has "
                "been tested."
            )
        )

    if not ea_state["connected"]:

        raise HTTPException(
            status_code=503,
            detail="EA is offline"
        )

    if not ea_state["running"]:

        raise HTTPException(
            status_code=403,
            detail="EA is stopped"
        )

    if not is_trading_session():

        raise HTTPException(
            status_code=403,
            detail=(
                "Trading is outside "
                "09:00-17:00"
            )
        )

    if request.symbol != TRADING_SYMBOL:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Only {TRADING_SYMBOL} "
                "is allowed"
            )
        )

    direction = request.direction.upper()

    if direction not in [
        "BUY",
        "SELL"
    ]:

        raise HTTPException(
            status_code=400,
            detail="Invalid direction"
        )

    if request.confidence < MIN_AI_SCORE:

        raise HTTPException(
            status_code=403,
            detail=(
                f"Confidence must be "
                f"{MIN_AI_SCORE}+"
            )
        )

    if len(trades) >= MAX_TRADES:

        raise HTTPException(
            status_code=403,
            detail=(
                "Maximum open trades "
                "reached"
            )
        )

    if cooldown_active():

        raise HTTPException(
            status_code=403,
            detail=(
                "Cooldown active: "
                f"{cooldown_remaining()} seconds"
            )
        )

    # --------------------------------------------------------
    # CREATE TRADE COMMAND
    # --------------------------------------------------------

    trade_id = str(
        uuid.uuid4()
    )

    trade = {
        "id": trade_id,
        "symbol": request.symbol,
        "direction": direction,
        "volume": request.volume,
        "confidence":
            request.confidence,
        "signal_id":
            request.signal_id,
        "comment":
            request.comment,
        "status":
            "PENDING_EA_EXECUTION",
        "created":
            datetime.now().isoformat(),
    }

    trades.append(trade)

    last_trade_time = time.time()

    ea_state["last_command"] = (
        f"{direction} {request.symbol}"
    )

    return {
        "success": True,
        "accepted": True,
        "execution": (
            "PENDING_EA_EXECUTION"
        ),
        "trade": trade,
        "tp_sl": (
            "CONTROLLED_BY_EA"
        ),
    }


# ============================================================
# GET TRADES
# ============================================================

@app.get("/mt5/trades")
def get_trades(
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    return {
        "count": len(trades),
        "max_trades": MAX_TRADES,
        "trades": trades,
    }


# ============================================================
# CLOSE ONE TRADE
# ============================================================

@app.post("/trade/close")
def close_trade(
    request: CloseTradeRequest,
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    target = None

    for trade in trades:

        if trade.get("ticket") == request.ticket:
            target = trade
            break

    if target is None:

        return {
            "success": True,
            "message": (
                "Close command sent to EA"
            ),
            "ticket": request.ticket,
            "status":
                "PENDING_EA_CONFIRMATION",
        }

    target["status"] = (
        "PENDING_CLOSE"
    )

    ea_state["last_command"] = (
        f"CLOSE {request.ticket}"
    )

    return {
        "success": True,
        "ticket": request.ticket,
        "status":
            "PENDING_CLOSE",
    }


# ============================================================
# CLOSE ALL
# ============================================================

@app.post("/trade/close-all")
def close_all(
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    ea_state["last_command"] = (
        "CLOSE_ALL"
    )

    for trade in trades:
        trade["status"] = (
            "PENDING_CLOSE"
        )

    return {
        "success": True,
        "command": "CLOSE_ALL",
        "status":
            "PENDING_EA_CONFIRMATION",
        "trade_count":
            len(trades),
    }


# ============================================================
# COOLDOWN
# ============================================================

@app.get("/risk")
def risk_status(
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    return {
        "symbol":
            TRADING_SYMBOL,
        "minimum_ai_score":
            MIN_AI_SCORE,
        "max_trades":
            MAX_TRADES,
        "open_trades":
            len(trades),
        "cooldown_seconds":
            COOLDOWN_SECONDS,
        "cooldown_remaining":
            cooldown_remaining(),
        "session":
            "09:00-17:00",
        "session_open":
            is_trading_session(),
        "remote_trading":
            REMOTE_TRADING_ENABLED,
    }


# ============================================================
# CONFIGURATION
# ============================================================

@app.get("/config")
def config(
    authorization: Optional[str] = Header(
        default=None
    )
):

    verify_api_key(
        authorization
    )

    return {
        "symbol":
            TRADING_SYMBOL,

        "start_time":
            "09:00",

        "end_time":
            "17:00",

        "minimum_ai_score":
            MIN_AI_SCORE,

        "max_trades":
            MAX_TRADES,

        "cooldown_seconds":
            COOLDOWN_SECONDS,

        "tp_sl":
            "EA_CONTROLLED",

        "remote_trading":
            REMOTE_TRADING_ENABLED,
    }


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
  )
