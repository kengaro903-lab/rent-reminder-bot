import os, sys, time, requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# === Schedule (IST-based) ===
IST_DAY  = os.getenv("IST_DAY",  "03")       # Day of the month (e.g., "03")
IST_TIME = os.getenv("IST_TIME", "13:50")    # Target time in IST (24h)
TZ_NAME  = os.getenv("TIMEZONE", "Asia/Kolkata")

# === Whapi Config ===
WHAPI_TOKEN  = os.getenv("WHAPI_TOKEN", "").strip()
GROUP_ID     = os.getenv("GROUP_ID", "").strip()
MESSAGE      = os.getenv("MESSAGE", "📩 Rent check: Hello Alberto Del Rio group — please confirm if rent for *Raintree* flat has been received this month.").strip()

API_BASE = "https://gate.whapi.cloud"


def fail(msg: str):
    print(f"[error] {msg}")
    sys.exit(1)


def validate():
    """Ensure required env vars are set."""
    missing = [k for k, v in {
        "WHAPI_TOKEN": WHAPI_TOKEN,
        "GROUP_ID": GROUP_ID,
    }.items() if not v]

    if missing:
        fail(f"Missing env vars: {', '.join(missing)}")

    if not GROUP_ID.endswith("@g.us"):
        fail("GROUP_ID must end with @g.us (WhatsApp group ID).")


def ist_gate():
    """Allow sending within ±5 minutes of the target IST time."""
    try:
        tz = ZoneInfo(TZ_NAME)
    except Exception:
        fail(f"Invalid TIMEZONE: {TZ_NAME}")

    now = datetime.now(tz)
    target = datetime.strptime(IST_TIME, "%H:%M").time()
    diff_minutes = abs((now.hour * 60 + now.minute) - (target.hour * 60 + target.minute))

    if now.strftime("%d") != str(IST_DAY).zfill(2) or diff_minutes > 5:
        print(f"[skip] Not in window. Now IST={now.strftime('%d %H:%M')} target={IST_DAY} {IST_TIME}")
        sys.exit(0)


def send_text():
    """Send plain text WhatsApp message via Whapi."""
    url = f"{API_BASE}/messages/text"
    headers = {
        "Authorization": f"Bearer {WHAPI_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": GROUP_ID,
        "body": MESSAGE
    }

    print(f"[send] Sending to {GROUP_ID}...")
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"[http] {r.status_code} {r.text}")

    if r.status_code != 200:
        fail("Whapi rejected the request. Check token, group ID, or permissions.")

    try:
        resp = r.json()
    except Exception:
        fail("Non-JSON response from Whapi API.")

    return (((resp or {}).get("message")) or {}).get("id")


def get_status(msg_id: str):
    """Check message delivery status."""
    if not msg_id:
        return
    url = f"{API_BASE}/messages/{msg_id}"
    headers = {"Authorization": f"Bearer {WHAPI_TOKEN}"}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        print(f"[warn] Status check failed: {r.status_code}")
        return
    try:
        data = r.json()
    except Exception:
        return
    status = data.get("status")
    print(f"[status] message_id={msg_id} status={status}")
    return status


def main():
    validate()
    ist_gate()
    msg_id = send_text()
    for _ in range(5):
        st = get_status(msg_id)
        if st in ("sent", "delivered", "read"):
            break
        time.sleep(2)


if __name__ == "__main__":
    main()
