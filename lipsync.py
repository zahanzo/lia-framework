"""
lipsync.py -- VTube Studio Lip Sync

Connects to the VTube Studio WebSocket API and animates the model's
mouth parameter in sync with the AI's speech output.

No screen capture. No overlay. The avatar stays in VTube Studio / OBS
exactly as you configured it. This script only drives the mouth.

Requirements:
    pip install websockets

VTube Studio setup:
    1. Open VTube Studio
    2. Settings -> General -> Enable API (port 8001)
    3. Run this script (or it starts automatically with main.py)
    4. Click ALLOW when the popup appears in VTube Studio

Usage:
    Standalone test:
        python lipsync.py

    With the assistant (main.py imports mouth.py which calls set_speaking):
        The assistant automatically drives the mouth when it speaks.
        No need to run this separately — mouth.py imports it.
"""

import asyncio
import json
import math
import os
import time
import threading

# ============================================================
# CONFIGURATION
# ============================================================
VTUBE_WS_URL    = "ws://localhost:8001"
TOKEN_FILE      = "vtube_token.txt"
PLUGIN_NAME     = "AI Assistant Lip Sync"
PLUGIN_DEV      = "AI Framework"

# VTube Studio mouth parameter name.
# Check yours in VTube Studio: Expression Editor -> Parameters
MOUTH_PARAM     = "MouthOpen"

UPDATE_HZ       = 30   # mouth updates per second
MAX_RETRIES     = 3

# ============================================================
# STATE
# ============================================================
_is_speaking  = False
_mouth_smooth = 0.0
_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None        = None


# ============================================================
# PUBLIC API  (called by mouth.py)
# ============================================================
def set_speaking(speaking: bool):
    """
    Call this when the AI starts or stops speaking.
    mouth.py calls this automatically — no manual wiring needed.
    """
    global _is_speaking
    _is_speaking = speaking


def start():
    """Start the lip sync engine in a background thread. Call once at boot."""
    global _loop, _thread
    if _thread and _thread.is_alive():
        return
    _loop   = asyncio.new_event_loop()
    _thread = threading.Thread(
        target=_loop.run_until_complete,
        args=(_run(),),
        daemon=True
    )
    _thread.start()


def stop():
    global _is_speaking
    _is_speaking = False


# ============================================================
# MOUTH ANIMATION
# ============================================================
def _calc_mouth() -> float:
    """Smooth, natural-looking mouth animation based on speaking state."""
    global _mouth_smooth
    if _is_speaking:
        t   = time.time()
        # Two overlapping sines give a realistic talking rhythm
        raw = (
            0.5 * math.sin(t * 8.0) +
            0.3 * math.sin(t * 13.7) +
            0.2 * math.sin(t * 5.3) +
            0.6
        ) / 1.1
        target = max(0.0, min(1.0, raw))
    else:
        target = 0.0

    # Exponential smoothing — avoids jitter, gives natural decay
    _mouth_smooth = _mouth_smooth * 0.6 + target * 0.4
    return round(_mouth_smooth, 4)


# ============================================================
# VTUBE STUDIO API
# ============================================================
def _load_token() -> str | None:
    if os.path.exists(TOKEN_FILE):
        t = open(TOKEN_FILE).read().strip()
        return t or None
    return None


def _save_token(token: str):
    open(TOKEN_FILE, "w").write(token)


async def _send(ws, msg_type: str, data: dict) -> dict:
    await ws.send(json.dumps({
        "apiName":    "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID":  "lipsync",
        "messageType": msg_type,
        "data":       data
    }))
    return json.loads(await ws.recv())


async def _authenticate(ws) -> bool:
    token = _load_token()

    # Try saved token first
    if token:
        r = await _send(ws, "AuthenticationRequest", {
            "pluginName":          PLUGIN_NAME,
            "pluginDeveloper":     PLUGIN_DEV,
            "authenticationToken": token
        })
        if r.get("data", {}).get("authenticated"):
            print("[LipSync] Authenticated.")
            return True

    # Request new token — shows Allow popup in VTube Studio
    r = await _send(ws, "AuthenticationTokenRequest", {
        "pluginName":      PLUGIN_NAME,
        "pluginDeveloper": PLUGIN_DEV,
    })
    new_token = r.get("data", {}).get("authenticationToken", "")
    if not new_token:
        print("[LipSync] Could not get token. Enable the API in VTube Studio settings.")
        return False

    print("[LipSync] Click ALLOW in VTube Studio...")
    r = await _send(ws, "AuthenticationRequest", {
        "pluginName":          PLUGIN_NAME,
        "pluginDeveloper":     PLUGIN_DEV,
        "authenticationToken": new_token
    })
    if r.get("data", {}).get("authenticated"):
        _save_token(new_token)
        print("[LipSync] Authenticated! Token saved.")
        return True

    print("[LipSync] Authentication failed.")
    return False


async def _inject_mouth(ws, value: float):
    """Send mouth parameter to VTube Studio — fire and forget."""
    await ws.send(json.dumps({
        "apiName":    "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID":  "mouth",
        "messageType": "InjectParameterDataRequest",
        "data": {
            "faceFound":       True,
            "mode":            "set",
            "parameterValues": [
                {"id": MOUTH_PARAM, "value": value, "weight": 1.0}
            ]
        }
    }))
    # Drain response without blocking
    try:
        await asyncio.wait_for(ws.recv(), timeout=0.01)
    except Exception:
        pass


async def _mouth_loop(ws):
    interval = 1.0 / UPDATE_HZ
    print("[LipSync] Mouth animation running.")
    while True:
        await _inject_mouth(ws, _calc_mouth())
        await asyncio.sleep(interval)


# ============================================================
# CONNECTION MANAGER
# ============================================================
async def _run():
    try:
        import websockets
    except ImportError:
        print("[LipSync] websockets not installed. Run: pip install websockets")
        return

    retries = 0
    while retries < MAX_RETRIES:
        try:
            print(f"[LipSync] Connecting to {VTUBE_WS_URL}...")
            async with websockets.connect(VTUBE_WS_URL) as ws:
                retries = 0
                if not await _authenticate(ws):
                    await asyncio.sleep(10)
                    continue
                await _mouth_loop(ws)

        except Exception as e:
            retries += 1
            if retries >= MAX_RETRIES:
                print("[LipSync] Could not connect. Make sure VTube Studio is open")
                print("          with API enabled (Settings -> General -> Start API).")
                return
            print(f"[LipSync] Connection lost ({retries}/{MAX_RETRIES}), retrying in 5s...")
            await asyncio.sleep(5)


# ============================================================
# STANDALONE TEST
# ============================================================
if __name__ == "__main__":
    print("LipSync test — simulates 5 seconds of speaking.")
    print("Watch the MouthOpen parameter in VTube Studio.")
    start()
    time.sleep(2)   # wait for connection

    print("Speaking...")
    set_speaking(True)
    time.sleep(5)

    print("Stopped.")
    set_speaking(False)
    time.sleep(1)