# utils/crash_reporter.py
import urllib.request
import urllib.parse
import traceback
from config import BOT_TOKEN, ADMIN_ID


def send_crash_alert(exception):
    """
    Synchronous, fail-safe HTTP POST to Telegram.
    Used when the main event loop dies.
    """
    try:
        error_msg = "".join(
            traceback.format_exception(None, exception, exception.__traceback__)
        )
        # Truncate if too long for Telegram (4096 chars limit)
        if len(error_msg) > 3500:
            error_msg = error_msg[-3500:]

        text = f"🚨 <b>CRITICAL SYSTEM FAILURE</b> 🚨\n\n<pre>{error_msg}</pre>"

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": ADMIN_ID, "text": text, "parse_mode": "HTML"}

        encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded_data)
        urllib.request.urlopen(req, timeout=5)
        print("Crash alert sent to Telegram.")

    except Exception as e:
        print(f"Failed to send crash alert: {e}")
