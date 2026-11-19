
import os
import json
import urllib.request
import urllib.error

from dotenv import load_dotenv

load_dotenv()

WABA_ID = "1132881789485314"
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
VERSION = os.getenv("WHATSAPP_API_VERSION", "v27.0")

if not TOKEN:
    print("ERROR: WHATSAPP_ACCESS_TOKEN missing from .env")
    raise SystemExit(1)

url = f"https://graph.facebook.com/{VERSION}/{WABA_ID}/subscribed_apps"

request = urllib.request.Request(
    url,
    headers={"Authorization": f"Bearer {TOKEN}"},
    method="GET"
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        print("HTTP Status:", response.status)
        print(json.dumps(
            json.loads(response.read().decode()),
            indent=2
        ))

except urllib.error.HTTPError as error:
    print("HTTP Error:", error.code)
    print(error.read().decode())

except Exception as error:
    print("Error:", str(error))
