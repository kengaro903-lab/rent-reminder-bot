import os, sys, time, requests
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs): pass

load_dotenv()

# === User-friendly IST schedule (set in workflow or .env) ===
IST_DAY  = os.getenv("IST_DAY",  "03")     # e.g., "12"
IST_TIME = os.getenv("IST_TIME", "13:10")  # e.g., "10:00" (24h)
TZ_NAME  = os.getenv("TIMEZONE", "Asia/Kolkata")

# Whapi auth + target
WHAPI_TOKEN  = os.getenv("WHAPI_TOKEN", "").strip()
GROUP_ID     = os.getenv("GROUP_ID", "").strip()
MENTION_WAID = os.getenv("MENTION_WAID", "").strip()

# Message pieces
DISPLAY_NAME = os.getenv("DISPLAY_NAME", "Sanket").strip()
MESSAGE      = os.getenv("MESSAGE", "📩 Rent check: Have you received the *Raintree* flat rent this month?").strip()

API_BASE = "https://gate.whapi.cloud"

def fail(msg: str):
    print(f"[error] {msg}")
    sys.exit(1)

def validate():
    missing = [k for k,v in {
        "WHAPI_TOKEN": WHAPI_TOKEN,
        "GROUP_ID": GROUP_ID,
        "MENTION_WAID": MENTION_WAID,
    }.items() if not v]
    if missing:
        fail(f"Missing env vars: {', '.join(missing)}")
    if not GROUP_ID.endswith("@g.us"):
        fail("GROUP_ID must end with @g.us (e.g., 1203…@g.us).")
    if not MENTION_WAID.isdigit():
        fail("MENTION_WAID must be digits only (international format, no '+').")

def ist_gate():
    """Exit unless current IST day+time match IST_DAY/IST_TIME exactly."""
    try:
        tz = ZoneInfo(TZ_NAME)
    except Exception:
        fail(f"Invalid TIMEZONE: {TZ_NAME}")
    now = datetime.now(tz)
    if now.strftime("%d") != str(IST_DAY).zfill(2) or now.strftime("%H:%M") != IST_TIME:
        print(f"[skip] Not scheduled time. Now IST={now.strftime('%d %H:%M')} target={str(IST_DAY).zfill(2)} {IST_TIME}")
        sys.exit(0)

def send_text():
    url = f"{API_BASE}/messages/text"
    headers = {"Authorization": f"Bearer {WHAPI_TOKEN}", "Content-Type": "application/json"}
    body_text = f"{MESSAGE} @{DISPLAY_NAME}"
    payload = {"to": GROUP_ID, "body": body_text, "mentions": [MENTION_WAID]}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"[http] {r.status_code} {r.text}")
    if r.status_code != 200:
        fail("Whapi rejected the request. Check token, group id, or body format.")
    try:
        resp = r.json()
    except Exception:
        fail("Non-JSON response from API.")
    return (((resp or {}).get("message")) or {}).get("id")

def get_status(msg_id: str):
    if not msg_id:
        return
    url = f"{API_BASE}/messages/{msg_id}"
    r = requests.get(url, headers={"Authorization": f"Bearer {WHAPI_TOKEN}"}, timeout=15)
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
    ist_gate()           # Only send at the exact IST day+time
    msg_id = send_text()
    # quick poll for a few seconds
    for _ in range(6):
        st = get_status(msg_id)
        if st in ("sent", "delivered", "read"):
            break
        time.sleep(2)

if __name__ == "__main__":
    main()
