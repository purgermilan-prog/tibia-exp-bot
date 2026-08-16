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
# CZAS TIBII
# ======================

def tibia_datetime():

    now = datetime.now()

    # Tibia resetuje dobę o 10:00
    if now.hour < 10:

        now -= timedelta(days=1)

    return now



def tibia_date():

    return tibia_datetime().date().isoformat()



def tibia_day_start():

    now = tibia_datetime()

    return now.replace(
        hour=10,
        minute=0,
        second=0,
        microsecond=0
    )


# ======================
# FORMAT EXP
# ======================

def format_exp(value):

    # 1 000 EXP = 1k
    # 1 000 000 EXP = 1000k

    if value >= 1000:

        return f"{value/1000:,.0f}k"

    return str(value)



# ======================
# EXP TIBIA
# ======================

def exp_for_level(level):

    x = level

    return int(
        (50 / 3) *
        (
            x**3
            -
            6*x**2
            +
            17*x
            -
            12
        )
    )


# ======================
# API
# ======================

def api_get(url):

    for attempt in range(1, API_RETRIES + 1):

        try:

            response = requests.get(
                url,
                timeout=API_TIMEOUT,
                headers={
                    "User-Agent":
                    "TibiaEXPBot/1.0"
                }
            )


            if response.status_code == 200:

                return response.json()


            print(
                f"API error {response.status_code}"
            )


        except Exception as e:

            print(
                f"API exception: {e}"
            )


        time.sleep(3)


    return None



# ======================
# CHARACTER
# ======================

def fetch_character_data():

    url = (
        "https://api.tibiadata.com/v4/character/"
        +
        CHAR_NAME.replace(" ", "%20")
    )


    data = api_get(url)


    if not data:

        return None


    try:

        return data["character"]["character"]


    except Exception:

        return None



# ======================
# HIGHSCORE (ZOPTYMALIZOWANE)
# ======================

def fetch_highscore(last_rank=None):

    print("Searching highscores (smart search)...")

    # Pobieramy pierwszą stronę, aby poznać liczbę stron
    first = api_get(
        f"https://api.tibiadata.com/v4/highscores/"
        f"{WORLD}/experience/all/1"
    )

    if not first:
        return None

    try:
        pages = (
            first["highscores"]
            ["highscore_page"]
            ["total_pages"]
        )

    except Exception:
        pages = 50

    target_pages = []

    if last_rank:

        # Poprawne wyliczenie strony
        estimated_page = max(
            1,
            min((last_rank - 1) // 50 + 1, pages)
        )

        neighbors = [
            estimated_page - 2,
            estimated_page - 1,
            estimated_page,
            estimated_page + 1,
            estimated_page + 2
        ]

        target_pages = []

        for page in neighbors:
            if 1 <= page <= pages and page not in target_pages:
                target_pages.append(page)

    remaining_pages = [
        p
        for p in range(1, pages + 1)
        if p not in target_pages
    ]

    search_order = target_pages + remaining_pages

    for page in search_order:

        data = api_get(
            f"https://api.tibiadata.com/v4/highscores/"
            f"{WORLD}/experience/all/{page}"
        )

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
                    f"Found {CHAR_NAME} on page {page}"
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
        ) as file:

            data = json.load(file)


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
    ) as file:

        json.dump(
            {
                "history": history
            },
            file,
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


    current_day = datetime.fromisoformat(
        tibia_date()
    )


    limit = (
        current_day -
        timedelta(days=days)
    ).date()


    old = None


    for item in history:

        item_date = datetime.fromisoformat(
            item["date"]
        ).date()


        if item_date >= limit:

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

    month = tibia_date()[:7]


    data = [
        item for item in history
        if item["date"].startswith(month)
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


    days = (
        last - first
    ).days


    if days <= 0:

        return 0


    return (
        history[-1]["exp"]
        -
        history[0]["exp"]
    ) / days



def average_month(history):

    month = tibia_date()[:7]


    data = [
        item for item in history
        if item["date"].startswith(month)
    ]


    if len(data) < 2:

        return 0


    first = datetime.fromisoformat(
        data[0]["date"]
    )

    last = datetime.fromisoformat(
        data[-1]["date"]
    )


    days = (
        last - first
    ).days


    if days <= 0:

        return 0


    return (
        data[-1]["exp"]
        -
        data[0]["exp"]
    ) / days



def biggest_daily(history):

    best = 0

    best_date = None


    for index in range(1, len(history)):

        gain = (
            history[index]["exp"]
            -
            history[index - 1]["exp"]
        )


        if gain > best:

            best = gain

            best_date = history[index]["date"]


    return best, best_date



def exp_since_start(history):

    if len(history) < 2:

        return 0


    return (
        history[-1]["exp"]
        -
        history[0]["exp"]
    )



def levels_since_start(history):

    if len(history) < 2:

        return 0


    return (
        history[-1]["level"]
        -
        history[0]["level"]
    )



def bot_days(history):

    if not history:

        return 0


    start = datetime.fromisoformat(
        history[0]["date"]
    )


    today = datetime.fromisoformat(
        tibia_date()
    )


    return (
        today - start
    ).days + 1
# ======================
# DISCORD
# ======================

def send_discord(message):

    if not DISCORD_WEBHOOK_URL:

        print(message)

        return


    for attempt in range(3):

        try:

            response = requests.post(
                DISCORD_WEBHOOK_URL,
                json={
                    "content": message
                },
                timeout=15
            )


            if response.status_code in [200, 204]:

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

    # Wczytujemy historię, aby znać ostatni ranking
    history = load_history()

    last_rank = (
        history[-1].get("rank")
        if history
        else None
    )

    # Inteligentne wyszukiwanie highscores
    highscore = fetch_highscore(last_rank)

    if not highscore:

        send_discord(
            f"⚠️ Nie znaleziono {CHAR_NAME}"
        )

        return

    character = fetch_character_data()

    level = highscore["level"]

    exp = highscore["value"]

    rank = highscore["rank"]

    achievements = "?"

    if character:

        achievements = character.get(
            "achievement_points",
            "?"
        )

    # data wg doby Tibii

    today = tibia_date()

    # Historia została już wczytana wyżej

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
# ======================
# ZMIANY LVL / RANK
# ======================

if len(history) >= 2:

    previous = history[-2]

    previous_level = previous["level"]
    previous_rank = previous["rank"]
    previous_exp = previous["exp"]

else:

    previous_level = level
    previous_rank = rank
    previous_exp = exp


# Zmiana levela
level_change = level - previous_level


# Zmiana rankingu
# + = awans w rankingu
# - = spadek
rank_change = previous_rank - rank


# ======================
# PROCENTY EXP
# ======================

# EXP potrzebny na cały aktualny level
current_level_start = exp_for_level(level)
next_level_start = exp_for_level(level + 1)

level_range = (
    next


    avg = average_daily(history)

    avg_month = average_month(history)



    best, best_date = biggest_daily(
        history
    )



    message = f"""
🌙 **Daily EXP Report: {CHAR_NAME} 🏹**

⭐ LVL **{level} ({level_change:+d})** | 🏆 Rank **#{rank} ({rank_change:+d})**
✨ Current EXP: **{exp:,}**

📈 Today: **+{format_exp(gain_today)} ({today_percent}%)**
📅 7 days: **+{format_exp(gain_week)}**
📆 Month: **+{format_exp(gain_month)}**
📉 Next LVL {level + 1}: **{format_exp(exp_for_level(level + 1) - exp)} ({next_level_percent}% remaining)**

⚡ Avg/day: **{format_exp(int(avg))}**
⚡ Avg month: **{format_exp(int(avg_month))}**

🚀 Total gain: **+{format_exp(exp_since_start(history))} EXP**
🆙 Levels: **+{levels_since_start(history)}**
🔥 Best: **+{format_exp(best)} ({best_date})**

🤖 Bot: **{bot_days(history)} days**
📅 Since: **{history[0]["date"]}**
🕙 Tibia reset: **{tibia_day_start().strftime("%d.%m %H:%M")}**
"""


    send_discord(message)


    print("BOT END")



if __name__ == "__main__":

    main()
