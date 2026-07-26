import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

CHAR_NAME = "Mian Stone'arrow"
WORLD = "Premia"
HISTORY_FILE = "exp_history.json"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def fetch_exp():
    for page in range(10, 16):
        url = (
            "https://www.tibia.com/community/"
            f"?subtopic=highscores&world={WORLD}&beprotection=-1&category=6&profession=0&currentpage={page}"
        )
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")

        rows = soup.select("table.TableContent tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            name = cols[1].get_text(strip=True)
            if name == CHAR_NAME:
                exp = cols[-1].get_text(strip=True).replace(",", "")
                return int(exp)
    return None


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)


def send_text(exp, gain):
    if WEBHOOK_URL is None:
        print("No DISCORD_WEBHOOK_URL set.")
        return

    text = (
        f"📊 **Daily EXP report — {CHAR_NAME}**\n"
        f"🌍 World: {WORLD}\n\n"
        f"🔹 Current EXP: **{exp:,}**\n"
        f"🔹 Daily gain: **{gain:+,}**\n"
        f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )

    r = requests.post(WEBHOOK_URL, json={"content": text})
    print("Discord status:", r.status_code, r.text)


def main():
    exp = fetch_exp()
    if exp is None:
        print("Character not found.")
