import requests
import os
import json
import time
from datetime import datetime, timedelta


# ======================
# KONFIGURACJA
# ======================

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

CHAR_NAME = "Mian Stone'arrow"
WORLD = "Premia"

SAVE_FILE = "exp_history.json"

API_RETRIES = 3
API_TIMEOUT = 20


# ======================
# FORMUŁA EXP TIBIA
# ======================

def exp_for_level(level):
    """
    Zwraca całkowity EXP wymagany na dany level.
    """
    x = level
    return int((50 / 3) * (x**3 - 6*x**2 + 17*x - 12))


# ======================
# REQUEST Z RETRY
# ======================

def api_get(url):

    for attempt in range(1, API_RETRIES + 1):

        try:

            r = requests.get(
                url,
                timeout=API_TIMEOUT,
                headers={
                    "User-Agent":
                    "TibiaEXPBot/1.0"
                }
            )


            if r.status_code == 200:
                return r.json()


            print(
                f"API error {r.status_code}, "
                f"attempt {attempt}/{API_RETRIES}"
            )


        except Exception as e:

            print(
                f"API exception: {e}, "
                f"attempt {attempt}/{API_RETRIES}"
            )


        time.sleep(3)


    return None



# ======================
# TIBIADATA CHARACTER
# ======================

def fetch_character_data():

    url = (
        "https://api.tibiadata.com/v4/character/"
        +
        CHAR_NAME.replace(" ", "%20")
    )


    print(url)


    data = api_get(url)


    if not data:
        return None


    try:

        return data["character"]["character"]


    except Exception:

        return None



# ======================
# TIBIADATA HIGHSCORES
# ======================

def fetch_highscore():

    print("Searching highscores...")


    # najpierw pobieramy pierwszą stronę
    first_url = (
        f"https://api.tibiadata.com/v4/highscores/"
        f"{WORLD}/experience/all/1"
    )


    first = api_get(first_url)


    if not first:
        return None



    try:

        total_pages = (
            first["highscores"]
            ["highscore_page"]
            ["total_pages"]
        )

    except Exception:

        total_pages = 50



    for page in range(1, total_pages + 1):

        print(
            f"Checking page {page}/{total_pages}"
        )


        url = (
            f"https://api.tibiadata.com/v4/highscores/"
            f"{WORLD}/experience/all/{page}"
        )


        data = api_get(url)


        if not data:
            continue



        try:

            players = (
                data["highscores"]
                ["highscore_list"]
            )


        except Exception:

            continue



        for player in players:

            if (
                player["name"].lower()
                ==
                CHAR_NAME.lower()
            ):

                print(
                    "FOUND:",
                    player
                )

                return player



    return None



# ======================
# HISTORIA
# ======================

def load_history():

    if not os.path.exists(SAVE_FILE):

        return []


    try:

        with open(
            SAVE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)


        return data.get(
            "history",
            []
        )


    except Exception:

        return []



def save_history(history):

    with open(
        SAVE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "history": history
            },
            f,
            indent=2,
            ensure_ascii=False
        )



def update_today(history, record):

    today = record["date"]


    for item in history:

        if item["date"] == today:

            item.update(record)

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



def gain_from_days(history, days):

    if len(history) < 2:
        return 0


    limit = (
        datetime.now()
        -
        timedelta(days=days)
    ).date().isoformat()


    old = None


    for item in history:

        if item["date"] >= limit:

            old = item
            break



    if old is None:
        return 0


    return (
        history[-1]["exp"]
        -
        old["exp"]
    )



def gain_current_month(history):

    month = datetime.now().strftime("%Y-%m")


    data = [
        x for x in history
        if x["date"].startswith(month)
    ]


    if len(data) < 2:
        return 0


    return (
        data[-1]["exp"]
        -
        data[0]["exp"]
    )



def average_daily(history):

    if len(history) < 2:
        return 0


    first = datetime.fromisoformat(
        history[0]["date"]
    )

    last = datetime.fromisoformat(
        history[-1]["date"]
    )


    days = (last - first).days


    if days <= 0:
        return 0


    return (
        history[-1]["exp"]
        -
        history[0]["exp"]
    ) / days



def average_month(history):

    month = datetime.now().strftime("%Y-%m")


    data = [
        x for x in history
        if x["date"].startswith(month)
    ]


    if len(data) < 2:
        return 0


    first = datetime.fromisoformat(
        data[0]["date"]
    )

    last = datetime.fromisoformat(
        data[-1]["date"]
    )


    days = (last - first).days


    if days <= 0:
        return 0


    return (
        data[-1]["exp"]
        -
        data[0]["exp"]
    ) / days



def biggest_daily(history):

    best = 0
    date = None


    for i in range(1, len(history)):

        gain = (
            history[i]["exp"]
            -
            history[i-1]["exp"]
        )


        if gain > best:

            best = gain
            date = history[i]["date"]


    return best, date



def exp_since_start(history):

    if len(history) < 2:
        return 0


    return (
        history[-1]["exp"]
        -
        history[0]["exp"]
    )



def bot_days(history):

    if not history:
        return 0


    start = datetime.fromisoformat(
        history[0]["date"]
    )


    return (
        datetime.now() - start
    ).days + 1



def levels_since_start(history):

    if len(history) < 2:
        return 0


    return (
        history[-1]["level"]
        -
        history[0]["level"]
    )



def eta_days(exp_needed, avg):

    if avg <= 0:
        return None


    return int(
        exp_needed / avg
    )



def eta_text(days):

    if days is None:
        return "brak danych"


    if days == 0:
        return "dzisiaj"


    if days == 1:
        return "jutro"


    return f"{days} dni"



# ======================
# DISCORD
# ======================

def send_discord(message):

    if not DISCORD_WEBHOOK_URL:

        print(
            "Brak webhooka"
        )

        print(message)

        return



    for attempt in range(3):

        try:

            r = requests.post(
                DISCORD_WEBHOOK_URL,
                json={
                    "content": message
                },
                timeout=15
            )


            if r.status_code in [200,204]:

                return


        except Exception as e:

            print(
                "Discord error:",
                e
            )


        time.sleep(3)



# ======================
# MAIN
# ======================

def main():

    print("BOT START")


    highscore = fetch_highscore()


    if not highscore:

        send_discord(
            "⚠️ Nie znaleziono "
            f"{CHAR_NAME}."
        )

        return



    character = fetch_character_data()



    level = highscore["level"]

    exp = highscore["value"]

    rank = highscore["rank"]



    vocation = (
        highscore.get(
            "vocation",
            "?"
        )
    )



    achievements = "?"


    if character:

        achievements = (
            character.get(
                "achievement_points",
                "?"
            )
        )



    today = datetime.now().date().isoformat()



    history = load_history()



    history = update_today(
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

    gain_week = gain_from_days(
        history,
        7
    )

    gain_month = gain_current_month(
        history
    )


    avg = average_daily(
        history
    )

    avg_m = average_month(
        history
    )



    next_level = level + 1


    missing = (
        exp_for_level(next_level)
        -
        exp
    )


     # najbliższy milestone co 50 leveli

    milestone = ((level // 50) + 1) * 50

    missing_milestone = (
        exp_for_level(milestone)
        -
        exp
    )

    milestone_days = eta_days(
        missing_milestone,
        avg
    )


    best, best_date = biggest_daily(
        history
    )



    message = f"""
🌙 **Daily Tibia EXP Report**

🧙 **{CHAR_NAME}**
🏹 {vocation}
🌎 {WORLD}

⭐ Level: **{level}**
🏆 Rank: **#{rank}**
🏅 Achievement points: **{achievements}**

✨ Current EXP:
**{exp:,}**

📈 Today:
**+{gain_today:,}**

📅 Last 7 days:
**+{gain_week:,}**

📆 Current month:
**+{gain_month:,}**

⏱️ Average EXP/day:
**{int(avg):,}**

⏱️ Average this month:
**{int(avg_m):,}**

📉 To level {next_level}:
**{missing:,} EXP**

🎯 Najbliższy milestone:
Level **{milestone}**

📉 Brakuje:
**{missing_milestone:,} EXP**

⏳ ETA:
**{eta_text(milestone_days)}**

🤖 Bot running:
**{bot_days(history)} day**

📅 Tracking since:
**{history[0]["date"]}**

🚀 EXP since start:
**+{exp_since_start(history):,}**

🆙 Levels since start:
**+{levels_since_start(history)}**

🔥 Biggest daily gain:
**+{best:,}**
({best_date})
"""


    send_discord(message)


    print("BOT END")



if __name__ == "__main__":
    main()
