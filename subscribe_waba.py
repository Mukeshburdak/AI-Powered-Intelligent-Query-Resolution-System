
import os
import json
import urllib.request
import urllib.error

from dotenv import load_dotenv

load_dotenv()

WABA_ID = "1132881789485314"
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
VERSION = os.getenv("WHATSAPP_API_VERSION", "v27.0")

url = f"https://graph.facebook.com/{VERSION}/{WABA_ID}/subscribed_apps"

payload = json.dumps({}).encode("utf-8")

request = urllib.request.Request(
    url,
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        print("HTTP Status:", response.status)
        print(response.read().decode())

except urllib.error.HTTPError as error:
    print("HTTP Error:", error.code)
    print(error.read().decode())
