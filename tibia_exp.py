import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import matplotlib.pyplot as plt

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


def make_chart(history):
    if len(history) < 2:
        return None

    dates = [h["date"] for h in history]
    exps = [h["exp"] for h in history]

    plt.figure(figsize=(6, 3))
    plt.plot(dates, exps, marker="o")
    plt.title(f"EXP history — {CHAR_NAME}")
    plt.xlabel("Date")
    plt.ylabel("EXP")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    chart_path = "exp_chart.png"
    plt.savefig(chart_path)
    plt.close()
    return chart_path


def send_embed(exp, gain, chart_path):
    if WEBHOOK_URL is None:
        print("No DISCORD_WEBHOOK_URL set.")
        return

    color = 0x2ecc71 if gain >= 0 else 0xe74c3c

    embed = {
        "title": f"Daily EXP report — {CHAR_NAME}",
        "description": f"World: {WORLD}",
        "color": color,
        "fields": [
            {"name": "Current EXP", "value": f"{exp:,}", "inline": True},
            {"name": "Daily gain", "value": f"{gain:+,}", "inline": True},
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    files = {}
    if chart_path and os.path.exists(chart_path):
        files["file"] = ("exp_chart.png", open(chart_path, "rb"), "image/png")
        embed["image"] = {"url": "attachment://exp_chart.png"}

    payload = {"embeds": [embed]}

    data = {"payload_json": json.dumps(payload)}
    r = requests.post(WEBHOOK_URL, data=data, files=files)
    print("Discord status:", r.status_code, r.text)


def main():
    exp = fetch_exp()
    if exp is None:
        print("Character not found.")
        return

    history = load_history()
    today = datetime.utcnow().strftime("%Y-%m-%d")

    prev_exp = history[-1]["exp"] if history else exp
    gain = exp - prev_exp

    history.append({"date": today, "exp": exp})
    save_history(history)

    chart_path = make_chart(history[-7:])  # ostatnie 7 dni
    send_embed(exp, gain, chart_path)


if __name__ == "__main__":
    main()
