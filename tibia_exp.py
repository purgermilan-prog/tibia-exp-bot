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

def tibia_date():

    now = datetime.now()

    # Doba Tibii zaczyna się o 10:00
    # przed 10:00 nadal jest poprzedni dzień
    if now.hour < 10:

        now -= timedelta(days=1)


    return now.date().isoformat()



def tibia_day_start():

    now = datetime.now()


    if now.hour < 10:

        now -= timedelta(days=1)


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

    """
    Format dla przyrostów i celów.
    1 000 000 EXP = 1000k
    """

    if value >= 1000:

        return f"{value/1000:,.0f}k"


    return str(value)



# ======================
# FORMUŁA EXP TIBIA
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

    month = tibia_date()[:7]


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

    month = tibia_date()[:7]


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
# MILESTONE
# ======================

def next_milestones(level):

    milestones = []


    # kolejne pełne setki
    next_hundred = (
        (level // 100) + 1
    ) * 100


    milestones.append(next_hundred)



    # poziomy z powtarzającymi cyframi

    special = [
        111,
        222,
        333,
        444,
        555,
        666,
        777,
        888,
        999,
        1111
    ]


    for lvl in special:

        if lvl > level:

            milestones.append(lvl)



    return sorted(
        set(milestones)
    )[:2]



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


            if r.status_code in [200, 204]:

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
            f"{CHAR_NAME}"
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



    today = tibia_date()



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


    avg = average_daily(history)

    avg_month = average_month(history)



    next_level = level + 1


    missing_level = (
        exp_for_level(next_level)
        -
        exp
    )



    milestones = next_milestones(level)



    milestone_text = ""


    for milestone in milestones:

        missing = (
            exp_for_level(milestone)
            -
            exp
        )


        milestone_text += (
            f"\n💯 {milestone} → "
            f"**{format_exp(missing)}**"
        )



    eta = None


    if milestones:

        first_missing = (
            exp_for_level(milestones[0])
            -
            exp
        )


        eta = eta_days(
            first_missing,
            avg
        )



    best, best_date = biggest_daily(
        history
    )



    message = f"""
🌙 **Daily EXP Report: {CHAR_NAME} 🏹**

⭐ LVL **{level}** | 🏆 Rank **#{rank}**
✨ Current EXP: **{exp:,}**

📈 Today: **+{format_exp(gain_today)}**
📅 7 days: **+{format_exp(gain_week)}**
📆 Month: **+{format_exp(gain_month)}**

⚡ Avg/day: **{format_exp(int(avg))}**
⚡ Avg month: **{format_exp(int(avg_month))}**

📉 Next LVL {next_level}:
**{format_exp(missing_level)} EXP**

🎯 Milestones:
{milestone_text}

⏳ ETA: **{eta_text(eta)}**

🕙 Tibia reset:
**{tibia_day_start().strftime("%d.%m %H:%M")}**

🤖 Bot: **{bot_days(history)} days**
📅 Since: **{history[0]["date"]}**

🚀 Total gain:
**+{format_exp(exp_since_start(history))} EXP**

🆙 Levels:
**+{levels_since_start(history)}**

🔥 Best:
**+{format_exp(best)} ({best_date})**
"""


    send_discord(message)


    print("BOT END")



if __name__ == "__main__":

    main()