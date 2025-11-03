import os, sys, time, requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Load environment variables (for local testing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# === Schedule Configuration (IST-based) ===
IST_DAY  = os.getenv("IST_DAY",  "03")       # Day of the month (e.g., "03")
IST_TIME = os.getenv("IST_TIME", "13:39")    # Target time in IST (24h)
TZ_NAME  = os.getenv("TIMEZONE", "Asia/Kolkata")

# === Whapi Configuration ===
WHAPI_TOKEN  = os.getenv("WHAPI_TOKEN", "").strip()
GROUP_ID     = os.getenv("GROUP_ID", "").strip()
MENTION_WAID = os.getenv("MENTION_WAID", "").strip()
DISPLAY_NAME = os.getenv("DISPLAY_NAME", "Sanket").strip()

API_BASE = "https://gate.whapi.cloud"


# === Utility Functions ===
def fail(msg: str):
    print(f"[error] {msg}")
    sys.exit(1)


def validate():
    """Ensure required environment variables are provided."""
    missing = [k for k, v in {
        "WHAPI_TOKEN": WHAPI_TOKEN,
        "GROUP_ID": GROUP_ID,
        "MENTION_WAID": MENTION_WAID,
    }.items() if not v]

    if missing:
        fail(f"Missing env vars: {', '.join(missing)}")

    if not GROUP_ID.endswith("@g.us"):
        fail("GROUP_ID must end with @g.us (WhatsApp group ID).")

    if not MENTION_WAID.isdigit():
        fail("MENTION_WAID must contain only digits (no '+').")


def ist_gate():
    """Allow sending within ±5 minutes of target IST time."""
    try:
        tz = ZoneInfo(TZ_NAME)
    except Exception:
        fail(f"Invalid TIMEZONE: {TZ_NAME}")

    now = datetime.now(tz)
    target_time = datetime.strptime(IST_TIME, "%H:%M").time()
    diff_minutes = abs((now.hour * 60 + now.minute) - (target_time.hour * 60 + target_time.minute))

    if now.strftime("%d") != str(IST_DAY).zfill(2) or diff_minutes > 5:
        print(f"[skip] Not in window. Now IST={now.strftime('%d %H:%M')} target={IST_DAY} {IST_TIME}")
        sys.exit(0)


# === Main Message Sender ===
def send_text():
    """Send the WhatsApp message through Whapi with one mention."""
    url = f"{API_BASE}/messages/text"
    headers = {
        "Authorization": f"Bearer {WHAPI_TOKEN}",
        "Content-Type": "application/json"
    }

    # ✅ Proper mention format
    body_text = "please confirm if rent for Raintree flat has been received this month? @user"

    payload = {
        "to": GROUP_ID,
        "body": body_text,
        "mentions": [MENTION_WAID]
    }

    print(f"[send] Sending to {GROUP_ID}...")
    print(f"[debug] Payload: {payload}")  # Optional: For debugging logs

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"[http] {r.status_code} {r.text}")

    if r.status_code != 200:
        fail("Whapi rejected the request. Check token, group ID, or mention format.")

    try:
        resp = r.json()
    except Exception:
        fail("Non-JSON response from API.")

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
