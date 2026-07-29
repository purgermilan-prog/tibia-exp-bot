import requests
import os
import json
import time
from datetime import datetime, timedelta

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

GUILD_NAME = "General Levy of Sarmats"
WORLD = "Antica"

SAVE_FILE = "guild_history.json"

API_RETRIES = 3
API_TIMEOUT = 20


# ======================
# API REQUEST
# ======================

def api_get(url):
    for attempt in range(1, API_RETRIES + 1):
        try:
            r = requests.get(url, timeout=API_TIMEOUT, headers={"User-Agent": "TibiaGuildEXPBot/1.0"})
            if r.status_code == 200:
                return r.json()
            print(f"API error {r.status_code}, attempt {attempt}/{API_RETRIES}")
        except Exception as e:
            print(f"API exception: {e}, attempt {attempt}/{API_RETRIES}")
        time.sleep(3)
    return None


# ======================
# GUILD MEMBERS
# ======================

def fetch_guild_members():
    url = f"https://api.tibiadata.com/v4/guild/{GUILD_NAME.replace(' ', '%20')}"
    data = api_get(url)
    if not data:
        return []

    try:
        members = data["guild"]["members"]
        return [m["name"] for m in members]
    except Exception:
        return []


# ======================
# CHARACTER EXP
# ======================

def fetch_highscore(name):
    url = f"https://api.tibiadata.com/v4/highscores/{WORLD}/experience/all/1"
    first = api_get(url)
    if not first:
        return None

    try:
        total_pages = first["highscores"]["highscore_page"]["total_pages"]
    except Exception:
        total_pages = 50

    for page in range(1, total_pages + 1):
        url = f"https://api.tibiadata.com/v4/highscores/{WORLD}/experience/all/{page}"
        data = api_get(url)
        if not data:
            continue

        try:
            players = data["highscores"]["highscore_list"]
        except Exception:
            continue

        for p in players:
            if p["name"].lower() == name.lower():
                return p

    return None


# ======================
# HISTORY
# ======================

def load_history():
    if not os.path.exists(SAVE_FILE):
        return {"members": {}, "guild_daily": []}

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"members": {}, "guild_daily": []}


def save_history(data):
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ======================
# MAIN
# ======================

def main():
    print("GUILD BOT START")

    members = fetch_guild_members()
    if not members:
        send_discord(f"⚠️ Nie znaleziono gildii **{GUILD_NAME}**.")
        return

    history = load_history()
    today = datetime.now().date().isoformat()

    member_exp_today = {}
    member_gain_today = {}
    member_gain_week = {}
    member_gain_month = {}

    total_exp_today = 0

    # ======================
    # FETCH EXP FOR EACH MEMBER
    # ======================

    for name in members:
        hs = fetch_highscore(name)
        if not hs:
            continue

        exp = hs["value"]
        total_exp_today += exp

        # historia indywidualna
        if name not in history["members"]:
            history["members"][name] = []

        # update today
        member_history = history["members"][name]
        if member_history and member_history[-1]["date"] == today:
            member_history[-1]["exp"] = exp
        else:
            member_history.append({"date": today, "exp": exp})

        # liczenie przyrostów
        if len(member_history) >= 2:
            member_gain_today[name] = exp - member_history[-2]["exp"]
        else:
            member_gain_today[name] = 0

        # tydzień
        week_limit = (datetime.now() - timedelta(days=7)).date().isoformat()
        old_week = next((x for x in member_history if x["date"] >= week_limit), None)
        member_gain_week[name] = exp - old_week["exp"] if old_week else 0

        # miesiąc
        month_prefix = datetime.now().strftime("%Y-%m")
        month_data = [x for x in member_history if x["date"].startswith(month_prefix)]
        if len(month_data) >= 2:
            member_gain_month[name] = exp - month_data[0]["exp"]
        else:
            member_gain_month[name] = 0

    # ======================
    # GUILD DAILY HISTORY
    # ======================

    guild_daily = history["guild_daily"]

    if guild_daily and guild_daily[-1]["date"] == today:
        guild_daily[-1]["exp_total"] = total_exp_today
    else:
        guild_daily.append({"date": today, "exp_total": total_exp_today})

    # przyrosty gildii
    if len(guild_daily) >= 2:
        gain_today_total = total_exp_today - guild_daily[-2]["exp_total"]
    else:
        gain_today_total = 0

    # tydzień
    week_limit = (datetime.now() - timedelta(days=7)).date().isoformat()
    old_week = next((x for x in guild_daily if x["date"] >= week_limit), None)
    gain_week_total = total_exp_today - old_week["exp_total"] if old_week else 0

    # miesiąc
    month_prefix = datetime.now().strftime("%Y-%m")
    month_data = [x for x in guild_daily if x["date"].startswith(month_prefix)]
    if len(month_data) >= 2:
        gain_month_total = total_exp_today - month_data[0]["exp_total"]
    else:
        gain_month_total = 0

    # ======================
    # BEST PLAYERS
    # ======================

    best_today = max(member_gain_today.items(), key=lambda x: x[1])
    best_week = max(member_gain_week.items(), key=lambda x: x[1])
    best_month = max(member_gain_month.items(), key=lambda x: x[1])

    # ======================
    # RECORDS
    # ======================

    # rekord gildii
    guild_records = []
    for i in range(1, len(guild_daily)):
        gain = guild_daily[i]["exp_total"] - guild_daily[i-1]["exp_total"]
        guild_records.append((guild_daily[i]["date"], gain))

    guild_record = max(guild_records, key=lambda x: x[1]) if guild_records else ("brak", 0)

    # rekord indywidualny
    individual_records = []
    for name, hist in history["members"].items():
        for i in range(1, len(hist)):
            gain = hist[i]["exp"] - hist[i-1]["exp"]
            individual_records.append((name, hist[i]["date"], gain))

    individual_record = max(individual_records, key=lambda x: x[2]) if individual_records else ("brak", "brak", 0)

    save_history(history)

    # ======================
    # MESSAGE
    # ======================

    message = f"""
🌙 **Daily EXP Report — {GUILD_NAME} ({WORLD})**

👥 Members: **{len(members)}**

📦 Total EXP:
**{total_exp_today:,}**

📈 Today:
**+{gain_today_total:,}**

📅 Last 7 days:
**+{gain_week_total:,}**

📆 Current month:
**+{gain_month_total:,}**

🏆 Best today:
**{best_today[0]}** (+{best_today[1]:,})

🏆 Best week:
**{best_week[0]}** (+{best_week[1]:,})

🏆 Best month:
**{best_month[0]}** (+{best_month[1]:,})

🔥 Guild record (daily):
**+{guild_record[1]:,}** ({guild_record[0]})

🔥 Individual record:
**{individual_record[0]}** — +{individual_record[2]:,} ({individual_record[1]})
"""

    send_discord(message)
    print("GUILD BOT END")


# ======================
# DISCORD
# ======================

def send_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("Brak webhooka")
        print(message)
        return

    for attempt in range(3):
        try:
            r = requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=15)
            if r.status_code in [200, 204]:
                return
        except Exception as e:
            print("Discord error:", e)
        time.sleep(3)


if __name__ == "__main__":
    main()
