import os, sys, time, json, requests
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
except ImportError:
    print("[setup] Installing python-dotenv is recommended: pip install python-dotenv")
    def load_dotenv(*args, **kwargs): pass

load_dotenv()

TOKEN        = os.getenv("WHAPI_TOKEN", "").strip()
GROUP_ID     = os.getenv("GROUP_ID", "").strip()
WA_ID        = os.getenv("MENTION_WAID", "").strip()
DISPLAY_NAME = os.getenv("DISPLAY_NAME", "Resident").strip()
MESSAGE      = os.getenv("MESSAGE", "📩 Rent check").strip()
SEND_AT      = os.getenv("SEND_AT", "").strip()
TZ_NAME      = os.getenv("TIMEZONE", "Asia/Kolkata").strip()

API_BASE = "https://gate.whapi.cloud"

def fail(msg: str):
    print(f"[error] {msg}")
    sys.exit(1)

def validate():
    missing = [k for k,v in {
        "WHAPI_TOKEN": TOKEN,
        "GROUP_ID": GROUP_ID,
        "MENTION_WAID": WA_ID,
    }.items() if not v]
    if missing:
        fail(f"Missing env vars: {', '.join(missing)}. Edit your .env.")

    if not GROUP_ID.endswith("@g.us"):
        fail("GROUP_ID must end with @g.us (e.g., 1203…@g.us).")

    if not WA_ID.isdigit():
        fail("MENTION_WAID must be digits only (international format, no '+').")

def wait_until_if_needed():
    if not SEND_AT:
        return
    try:
        tz = ZoneInfo(TZ_NAME)
    except Exception:
        fail(f"Invalid TIMEZONE: {TZ_NAME}")
    try:
        target = datetime.strptime(SEND_AT, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    except ValueError:
        fail("SEND_AT must be in 'YYYY-MM-DD HH:MM' 24h format (IST). Example: 2025-11-01 10:00")

    now = datetime.now(tz)
    delta = (target - now).total_seconds()
    if delta <= 0:
        print(f"[info] SEND_AT {target} is in the past; sending now.")
        return
    # Sleep in short chunks so Ctrl+C remains responsive
    print(f"[info] Waiting until {target} ({TZ_NAME}) to send…")
    while delta > 0:
        to_wait = min(60, delta)  # up to 60s chunks
        time.sleep(to_wait)
        now = datetime.now(tz)
        delta = (target - now).total_seconds()
        # Optional: show countdown every minute
        if int(delta) % 300 < 2:  # roughly every ~5 minutes
            print(f"[info] ~{int(delta)//60} min remaining…")

def send_text():
    url = f"{API_BASE}/messages/text"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    body_text = f"{MESSAGE} @{DISPLAY_NAME}"
    payload = {"to": GROUP_ID, "body": body_text, "mentions": [WA_ID]}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"[http] {r.status_code} {r.text}")
    if r.status_code != 200:
        fail("Whapi rejected the request. Check token, group id, or body format.")
    try:
        resp = r.json()
    except Exception:
        fail("Non-JSON response from API.")
    msg_id = ((((resp or {}).get("message")) or {}).get("id")) or None
    return msg_id

def get_status(msg_id: str):
    if not msg_id:
        return
    url = f"{API_BASE}/messages/{msg_id}"
    r = requests.get(url, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=15)
    if r.status_code != 200:
        print(f"[warn] Status check failed: {r.status_code} {r.text}")
        return
    try:
        data = r.json()
    except Exception:
        print("[warn] Could not parse status JSON")
        return
    status = data.get("status")
    print(f"[status] message_id={msg_id} status={status}")
    return status

def main():
    validate()
    wait_until_if_needed()
    msg_id = send_text()
    # Optional quick poll (few seconds) to show delivery state
    for _ in range(6):
        st = get_status(msg_id)
        if st in ("sent", "delivered", "read"):
            break
        time.sleep(2)

if __name__ == "__main__":
    main()
