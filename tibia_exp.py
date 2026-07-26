import os
import requests

CHAR_NAME = "Mian Stone'arrow"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def fetch_exp():
    url = f"https://api.tibiadata.com/v4/character/{CHAR_NAME.replace(' ', '%20')}"
    r = requests.get(url)
    data = r.json()

    if "character" not in data or "experience" not in data["character"]:
        return None

    return data["character"]["experience"]

def main():
    exp = fetch_exp()

    if exp is None:
        text = f"❌ Character **{CHAR_NAME}** not found."
    else:
        text = f"📊 EXP for **{CHAR_NAME}**: **{exp:,}**"

    requests.post(WEBHOOK_URL, json={"content": text})

if __name__ == "__main__":
    main()
