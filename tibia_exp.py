import requests
import os
import json
from datetime import datetime, timedelta


# ======================
# KONFIGURACJA
# ======================

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

CHAR_NAME = "Mian Stone'arrow"
WORLD = "Premia"

SAVE_FILE = "exp_history.json"


# ======================
# FORMUŁA EXP TIBIA
# ======================

def exp_for_level(level):
    x = level
    return int((50 / 3) * (x**3 - 6*x**2 + 17*x - 12))


# ======================
# TIBIADATA
# ======================

def fetch_character_data():

    url = (
        "https://api.tibiadata.com/v4/character/"
        + CHAR_NAME.replace(" ", "%20")
    )

    r = requests.get(url, timeout=20)

    if r.status_code != 200:
        print("Character API error")
        return None

    return r.json()



def fetch_highscore():

    first_url = (
        f"https://api.tibiadata.com/v4/highscores/"
        f"{WORLD}/experience/all/1"
    )

    r = requests.get(first_url, timeout=20)

    if r.status_code != 200:
        return None


    total_pages = (
        r.json()
        ["highscores"]
        ["highscore_page"]
        ["total_pages"]
    )


    for page in range(1, total_pages + 1):

        print("Checking page:", page)

        url = (
            f"https://api.tibiadata.com/v4/highscores/"
            f"{WORLD}/experience/all/{page}"
        )

        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            continue


        players = (
            r.json()
            ["highscores"]
            ["highscore_list"]
        )


        for player in players:

            if player["name"].lower() == CHAR_NAME.lower():

                return player


    return None



# ======================
# HISTORIA
# ======================

def load_history():

    if not os.path.exists(SAVE_FILE):
        return []

    with open(SAVE_FILE, "r") as f:
        data = json.load(f)

    return data.get("history", [])



def save_history(history):

    with open(SAVE_FILE, "w") as f:

        json.dump(
            {
                "history": history
            },
            f,
            indent=2
        )



def add_today(history, record):

    today = record["date"]

    for old in history:

        if old["date"] == today:

            old.update(record)
            return history


    history.append(record)

    return history



# ======================
# STATYSTYKI
# ======================

def daily_gain(history):

    if len(history) < 2:
        return 0

    return (
        history[-1]["exp"]
        -
        history[-2]["exp"]
    )



def period_gain(history, days):

    if len(history) < 2:
        return 0

    cutoff = (
        datetime.now()
        -
        timedelta(days=days)
    ).date().isoformat()


    old = None

    for h in history:

        if h["date"] >= cutoff:

            old = h
            break


    if old is None:
        return 0


    return history[-1]["exp"] - old["exp"]



def average_daily(history):

    if len(history) < 2:
        return 0

    first = history[0]
    last = history[-1]

    days = (
        datetime.fromisoformat(last["date"])
        -
        datetime.fromisoformat(first["date"])
    ).days


    if days == 0:
        return 0


    return (
        last["exp"] - first["exp"]
    ) / days



def month_average(history):

    month = datetime.now().strftime("%Y-%m")

    data = [
        h for h in history
        if h["date"].startswith(month)
    ]


    if len(data) < 2:
        return 0


    days = (
        datetime.fromisoformat(data[-1]["date"])
        -
        datetime.fromisoformat(data[0]["date"])
    ).days


    if days == 0:
        return 0


    return (
        data[-1]["exp"]
        -
        data[0]["exp"]
    ) / days



def biggest_day(history):

    best = 0
    best_date = None


    for i in range(1, len(history)):

        gain = (
            history[i]["exp"]
            -
            history[i-1]["exp"]
        )


        if gain > best:

            best = gain
            best_date = history[i]["date"]


    return best, best_date



def eta_days(exp_needed, avg):

    if avg <= 0:
        return None

    return int(exp_needed / avg)



# ======================
# DISCORD
# ======================

def send_discord(message):

    requests.post(
        DISCORD_WEBHOOK_URL,
        json={
            "content": message
        },
        timeout=15
    )



# ======================
# MAIN
# ======================

def main():

    print("BOT START")


    highscore = fetch_highscore()

    if not highscore:

        send_discord(
            "⚠️ Nie znaleziono postaci w highscores"
        )

        return


    char = fetch_character_data()


    level = highscore["level"]
    exp = highscore["value"]


    achievements = (
        char["character"]["achievement_points"]
        if char else "?"
    )


    rank = highscore["rank"]


    today = datetime.now().date().isoformat()


    history = load_history()


    history = add_today(
        history,
        {
            "date": today,
            "exp": exp,
            "level": level,
            "rank": rank,
            "achievement_points": achievements
        }
    )


    save_history(history)


    gain_today = daily_gain(history)

    avg = average_daily(history)

    avg_month = month_average(history)


    next_level_exp = exp_for_level(level + 1)

    missing = next_level_exp - exp


    lvl_targets = []

    for target in [650,700,750]:

        if target > level:

            missing_target = (
                exp_for_level(target)
                -
                exp
            )

            days = eta_days(
                missing_target,
                avg
            )

            lvl_targets.append(
                f"{target}: {days} dni"
                if days else
                f"{target}: brak danych"
            )



    best, best_date = biggest_day(history)



    message = f"""
🌙 **Daily Tibia Report**

🧙 **{CHAR_NAME}**
🏹 Royal Paladin | Level **{level}**
🏆 Rank: **#{rank}**
⭐ Achievement points: **{achievements}**

✨ EXP:
**{exp:,}**

📈 Dzisiaj:
**+{gain_today:,}**

📅 7 dni:
**+{period_gain(history,7):,}**

📆 Miesiąc:
**+{period_gain(history,30):,}**

⏱️ Średnia ogólna:
**{int(avg):,}/dzień**

⏱️ Średnia miesiąca:
**{int(avg_month):,}/dzień**

📉 Do levela {level+1}:
**{missing:,} EXP**

🎯 ETA:
{chr(10).join(lvl_targets)}

🔥 Rekord dzienny:
**{best:,}**
({best_date})
"""


    send_discord(message)


    print("BOT END")



if __name__ == "__main__":
    main()
