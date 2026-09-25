#!/usr/bin/env python3
"""
Saleor Telegram Order Notifier (Python Version)
Supports single/multiple Telegram accounts, group chats, test mode, and 24/7 background polling.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load .env file manually or via dotenv if available
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

def load_env(path):
    config = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip().strip("\"'")
    return config

ENV = load_env(ENV_PATH)

API_URL = os.getenv("API_URL", ENV.get("API_URL", "https://api.easytopick.in/graphql/"))
BASE_URL = os.getenv("BASE_URL", ENV.get("BASE_URL", "http://localhost:9000/")).rstrip("/")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", ENV.get("TELEGRAM_BOT_TOKEN", ""))
RAW_CHAT_IDS = os.getenv("TELEGRAM_CHAT_ID", ENV.get("TELEGRAM_CHAT_ID", ""))
CHAT_IDS = [c.strip() for c in RAW_CHAT_IDS.replace(";", ",").split(",") if c.strip()]
STAFF_EMAIL = os.getenv("SALEOR_STAFF_EMAIL", ENV.get("SALEOR_STAFF_EMAIL", ""))
STAFF_PASSWORD = os.getenv("SALEOR_STAFF_PASSWORD", ENV.get("SALEOR_STAFF_PASSWORD", ""))
APP_TOKEN = os.getenv("SALEOR_APP_TOKEN", ENV.get("SALEOR_APP_TOKEN", ""))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", ENV.get("POLL_INTERVAL_SECONDS", "20")))
STATE_FILE = Path(__file__).resolve().parent / ".telegram_notifier_state.json"

AUTH_TOKEN = APP_TOKEN
REFRESH_TOKEN = ""

TOKEN_CREATE_MUTATION = """
mutation CreateToken($email: String!, $password: String!) {
  tokenCreate(email: $email, password: $password) {
    token
    refreshToken
    csrfToken
    errors {
      field
      message
      code
    }
  }
}
"""

ORDERS_QUERY = """
query GetRecentOrders {
  orders(first: 10, sortBy: { field: CREATION_DATE, direction: DESC }) {
    edges {
      node {
        id
        number
        created
        status
        paymentStatus
        userEmail
        billingAddress {
          firstName
          lastName
          phone
          city
          countryArea
          postalCode
        }
        shippingAddress {
          firstName
          lastName
          phone
          streetAddress1
          city
          countryArea
          postalCode
        }
        total {
          gross {
            amount
            currency
          }
        }
        lines {
          id
          productName
          variantName
          quantity
          unitPrice {
            gross {
              amount
              currency
            }
          }
        }
      }
    }
  }
}
"""

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"lastSeenOrderId": None, "lastSeenOrderNumber": None, "processedOrderIds": []}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"❌ Failed to save state file: {e}")

def format_currency(amount, currency="INR"):
    amt = float(amount or 0)
    symbol = "₹" if currency == "INR" else "$" if currency == "USD" else f"{currency} "
    return f"{symbol}{amt:,.2f}"

def format_ist(date_str):
    try:
        # Parse ISO date string
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        ist_offset = timedelta(hours=5, minutes=30)
        dt_ist = dt.astimezone(timezone(ist_offset))
        return dt_ist.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return date_str

def escape_html(text):
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_IDS:
        raise ValueError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing in .env file.")

    results = []
    for chat_id in CHAT_IDS:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                if res_data.get("ok"):
                    results.append(res_data)
                else:
                    print(f"❌ Telegram API Error for Chat ID [{chat_id}]: {res_data}")
        except Exception as e:
            print(f"❌ Error sending to Chat ID [{chat_id}]: {e}")

    if not results and CHAT_IDS:
        raise RuntimeError("Failed to deliver message to any configured Telegram chat IDs.")
    return results

def format_order_message(order):
    order_number = order.get("number") or "N/A"
    status = order.get("status") or "UNCONFIRMED"
    payment_status = order.get("paymentStatus") or "NOT_CHARGED"
    total_val = order.get("total", {}).get("gross", {}).get("amount", 0)
    currency = order.get("total", {}).get("gross", {}).get("currency", "INR")
    total_amount = format_currency(total_val, currency)
    order_time = format_ist(order.get("created", ""))

    addr = order.get("shippingAddress") or order.get("billingAddress") or {}
    first_name = addr.get("firstName") or ""
    last_name = addr.get("lastName") or ""
    customer_name = f"{first_name} {last_name}".strip() or "Guest Customer"
    phone = addr.get("phone") or "Not provided"
    email = order.get("userEmail") or "Not provided"
    city = ", ".join(filter(None, [addr.get("city"), addr.get("countryArea")])) or "N/A"

    lines = order.get("lines", [])
    if lines:
        items_lines = []
        for idx, item in enumerate(lines, 1):
            title = item.get("productName") or "Item"
            variant = f" ({item.get('variantName')})" if item.get("variantName") else ""
            qty = item.get("quantity") or 1
            u_amt = item.get("unitPrice", {}).get("gross", {}).get("amount", 0)
            u_curr = item.get("unitPrice", {}).get("gross", {}).get("currency", "INR")
            price = format_currency(u_amt, u_curr)
            items_lines.append(f"   <b>{idx}.</b> {escape_html(title)}{escape_html(variant)} × <b>{qty}</b> — {price}")
        items_list = "\n".join(items_lines)
    else:
        items_list = "   <i>No items information available</i>"

    order_id_encoded = urllib.parse.quote(order.get("id", ""))
    dashboard_link = f"{BASE_URL}/orders/{order_id_encoded}"

    msg = f"""
🛍️ <b>NEW ORDER RECEIVED!</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 <b>Order:</b> <code>#{order_number}</code>
💰 <b>Total Amount:</b> <b>{total_amount}</b>
💳 <b>Payment:</b> <code>{payment_status}</code>
⚡ <b>Status:</b> <code>{status}</code>
📅 <b>Date:</b> {order_time}

👤 <b>Customer Details:</b>
• <b>Name:</b> {escape_html(customer_name)}
• <b>Phone:</b> <code>{escape_html(phone)}</code>
• <b>Email:</b> {escape_html(email)}
• <b>Location:</b> {escape_html(city)}

🛒 <b>Ordered Items ({len(lines)}):</b>
{items_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 <a href="{dashboard_link}"><b>👉 View Order in Dashboard</b></a>
"""
    return msg.strip()

def authenticate_saleor():
    global AUTH_TOKEN, REFRESH_TOKEN
    if APP_TOKEN:
        AUTH_TOKEN = APP_TOKEN
        return AUTH_TOKEN

    if not STAFF_EMAIL or not STAFF_PASSWORD:
        raise ValueError("Saleor credentials missing. Set SALEOR_STAFF_EMAIL & SALEOR_STAFF_PASSWORD in .env")

    print(f"🔐 Logging into Saleor as: {STAFF_EMAIL}...")
    payload = {
        "query": TOKEN_CREATE_MUTATION,
        "variables": {"email": STAFF_EMAIL, "password": STAFF_PASSWORD},
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Forwarded-Proto": "https"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))

    if res_data.get("errors"):
        raise RuntimeError(f"Auth GraphQL Error: {res_data['errors'][0]['message']}")

    token_data = res_data.get("data", {}).get("tokenCreate", {})
    if token_data.get("errors"):
        raise RuntimeError(f"Login Failed: {token_data['errors'][0]['message']}")

    AUTH_TOKEN = token_data.get("token")
    REFRESH_TOKEN = token_data.get("refreshToken")
    print("✅ Successfully authenticated with Saleor API!")
    return AUTH_TOKEN

def execute_graphql(query, variables=None):
    global AUTH_TOKEN
    if not AUTH_TOKEN:
        authenticate_saleor()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "X-Forwarded-Proto": "https"
    }
    payload = {"query": query, "variables": variables or {}}

    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode("utf-8"))

    # Check for expired token
    is_auth_error = any(
        "expired" in str(err.get("message", "")).lower() or
        "signature" in str(err.get("message", "")).lower()
        for err in data.get("errors", [])
    )

    if is_auth_error:
        print("🔄 Token expired or unauthorized. Refreshing authentication...")
        authenticate_saleor()
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
        req = urllib.request.Request(API_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

    if data.get("errors"):
        raise RuntimeError(f"GraphQL Query Error: {data['errors'][0]['message']}")

    return data.get("data", {})

def check_new_orders(state, is_first_run=False):
    try:
        data = execute_graphql(ORDERS_QUERY)
        edges = data.get("orders", {}).get("edges", [])
        if not edges:
            return

        orders = [e["node"] for e in edges]

        if is_first_run and not state.get("lastSeenOrderId"):
            latest = orders[0]
            state["lastSeenOrderId"] = latest["id"]
            state["lastSeenOrderNumber"] = latest["number"]
            state["processedOrderIds"] = [o["id"] for o in orders]
            save_state(state)
            print(f"📌 Initialized tracker. Latest order in store is #{latest['number']}. Watching for NEW orders now...")
            return

        processed_set = set(state.get("processedOrderIds", []))
        new_orders = [o for o in orders if o["id"] not in processed_set]

        if new_orders:
            print(f"🔔 Found {len(new_orders)} new order(s)! Sending notifications...")
            new_orders.reverse()

            for order in new_orders:
                print(f"📤 Sending Telegram notification for Order #{order.get('number')}...")
                msg = format_order_message(order)
                send_telegram_message(msg)

                processed_set.add(order["id"])
                state["lastSeenOrderId"] = order["id"]
                state["lastSeenOrderNumber"] = order.get("number")

            state["processedOrderIds"] = list(processed_set)[-200:]
            save_state(state)
            print("✅ All new order notifications sent successfully!")
    except Exception as e:
        print(f"❌ Error checking orders: {e}")

def run_test():
    print("\n🧪 Running Telegram Notification Test (Python)...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"• Telegram Chat IDs ({len(CHAT_IDS)}): {', '.join(CHAT_IDS) or 'NOT SET'}")
    print(f"• Telegram Bot Token: {'****** (Configured)' if BOT_TOKEN else 'NOT SET'}")
    print(f"• Saleor API URL: {API_URL}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    if not BOT_TOKEN or not CHAT_IDS:
        print("❌ Configuration Error: Please provide TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file.")
        sys.exit(1)

    sample_order = {
        "id": "T3JkZXI6OTk5",
        "number": "999",
        "created": datetime.now(timezone.utc).isoformat(),
        "status": "UNFULFILLED",
        "paymentStatus": "FULLY_CHARGED",
        "userEmail": "customer@example.com",
        "shippingAddress": {
            "firstName": "Rahul",
            "lastName": "Sharma",
            "phone": "+91 98765 43210",
            "city": "New Delhi",
            "countryArea": "Delhi",
        },
        "total": {"gross": {"amount": 1499.0, "currency": "INR"}},
        "lines": [
            {
                "productName": "Premium Cotton T-Shirt",
                "variantName": "Black / L",
                "quantity": 2,
                "unitPrice": {"gross": {"amount": 499.0, "currency": "INR"}},
            },
            {
                "productName": "Sport Sneaker Shoes",
                "variantName": "Size 9",
                "quantity": 1,
                "unitPrice": {"gross": {"amount": 501.0, "currency": "INR"}},
            },
        ],
    }

    test_msg = f"""
🧪 <b>TEST NOTIFICATION (Python)</b>
<i>Your Telegram Order Alert System is working perfectly!</i>

{format_order_message(sample_order)}
"""
    try:
        print(f"📤 Sending sample order notification to {len(CHAT_IDS)} Telegram chat(s)...")
        send_telegram_message(test_msg)
        print("\n🎉 SUCCESS! Test message delivered to your Telegram app(s)!")
    except Exception as e:
        print(f"\n❌ Failed to send Telegram message: {e}")

def start_watcher():
    print("\n🚀 Starting Saleor Telegram Order Notifier (Python)...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"• Saleor API: {API_URL}")
    print(f"• Dashboard URL: {BASE_URL}")
    print(f"• Check Interval: {POLL_INTERVAL} seconds")
    print(f"• Telegram Bot: {'Configured' if BOT_TOKEN else 'Missing'}")
    print(f"• Telegram Chat IDs ({len(CHAT_IDS)}): {', '.join(CHAT_IDS) or 'Missing'}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    if not BOT_TOKEN or not CHAT_IDS:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing in .env!")
        sys.exit(1)

    state = load_state()

    try:
        authenticate_saleor()
        check_new_orders(state, is_first_run=True)
    except Exception as e:
        print(f"❌ Initialization error: {e}")

    print(f"\n👀 Actively watching for new orders in background (every {POLL_INTERVAL}s)...")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            time.sleep(POLL_INTERVAL)
            check_new_orders(state, is_first_run=False)
        except KeyboardInterrupt:
            print("\n🛑 Stopping notifier...")
            break
        except Exception as e:
            print(f"❌ Loop error: {e}")
            time.sleep(POLL_INTERVAL)

def find_group_ids():
    print("\n🔍 Searching for Telegram Groups & Chats...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN is missing in .env file.")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Saleor-Notifier"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if not data.get("ok"):
            print(f"❌ Telegram API Error: {data}")
            return

        results = data.get("result", [])
        if not results:
            print("⚠️ Koi updates nahi mile!")
            print("👉 Kripya Telegram Group me jaakar bot (@easytopick_order_bot) ko add karein,")
            print("   aur group me ek message (jaise 'hello' ya 'test') send karein.")
            print("   Fir ye command dubara run karein.\n")
            return

        found_chats = {}
        for item in results:
            msg = item.get("message") or item.get("my_chat_member") or item.get("channel_post") or {}
            chat = msg.get("chat", {})
            if chat and "id" in chat:
                c_id = str(chat["id"])
                c_type = chat.get("type", "unknown")
                c_title = chat.get("title") or f"{chat.get('first_name', '')} {chat.get('last_name', '')}".strip() or "Unnamed"
                found_chats[c_id] = {"title": c_title, "type": c_type}

        print(f"✅ Found {len(found_chats)} Chat(s)/Group(s):\n")
        for c_id, info in found_chats.items():
            print(f"• Name: {info['title']} ({info['type']})")
            print(f"  👉 Exact Chat ID: {c_id}\n")

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("💡 In IDs ko copy karke apni .env file me TELEGRAM_CHAT_ID me paste kar sakte hain!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    except Exception as e:
        print(f"❌ Error fetching updates: {e}")

if __name__ == "__main__":
    if "--test" in sys.argv:
        run_test()
    elif "--get-group-id" in sys.argv or "--find-id" in sys.argv or "--groups" in sys.argv:
        find_group_ids()
    else:
        start_watcher()
