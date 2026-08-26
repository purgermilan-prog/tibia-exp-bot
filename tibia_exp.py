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


def tibia_date_from_timestamp(timestamp):

    dt = datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )

    # TibiaData zwraca czas w UTC.
    # Usuwamy timezone, aby zachować tę samą
    # logikę 10:00 -> 10:00 co w tibia_datetime().
    dt = dt.replace(tzinfo=None)

    # Wszystko przed 10:00 należy do poprzedniego
    # dnia Tibii.
    if dt.hour < 10:

        dt -= timedelta(days=1)

    return dt.date().isoformat()


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


def biggest_daily(history, exclude_date=None):

    best = 0
    best_date = None

    for index in range(1, len(history)):

        # Nie uwzględniamy dzisiejszego wyniku
        # przy sprawdzaniu dotychczasowego PB
        if exclude_date is not None:
            if history[index]["date"] == exclude_date:
                continue

        gain = (
            history[index]["exp"]
            -
            history[index - 1]["exp"]
        )

        if gain > best:

            best = gain
            best_date = history[index]["date"]

    return best, best_date


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
# AKTUALIZACJA ŚMIERCI
# ======================

def update_deaths(history, deaths):
    """
    Dodaje nowe śmierci do odpowiednich dni Tibii.

    Śmierci są pobierane z TibiaData, który pokazuje
    historię śmierci z ostatniego miesiąca.

    Funkcja:
    - przypisuje śmierć do właściwego dnia Tibii,
    - nie tworzy wpisów bez danych EXP,
    - nie duplikuje istniejących śmierci.
    """

    for death in deaths:

        time = death.get("time")
        level = death.get("level")
        reason = death.get("reason", "")

        if not time:
            continue

        # Ustalamy dzień Tibii, do którego należy śmierć.
        death_date = tibia_date_from_timestamp(time)

        # Szukamy odpowiedniego wpisu w historii EXP.
        day_entry = None

        for entry in history:

            if entry.get("date") == death_date:

                day_entry = entry
                break

        # Jeżeli danego dnia nie ma w historii,
        # nie tworzymy sztucznego wpisu bez EXP.
        if day_entry is None:
            continue

        # Starsze wpisy historii mogą jeszcze nie posiadać
        # pola deaths.
        if "deaths" not in day_entry:

            day_entry["deaths"] = []

        # Sprawdzamy, czy ta śmierć została już zapisana.
        already_exists = any(
            existing.get("time") == time
            for existing in day_entry["deaths"]
        )

        if already_exists:
            continue

        # Zapisujemy wszystkich killerów.
        killers = []

        for killer in death.get("killers", []):

            name = killer.get("name")

            if name:
                killers.append(name)

        # Zapisujemy śmierć.
        day_entry["deaths"].append({
            "time": time,
            "level": level,
            "killers": killers,
            "reason": reason
        })

    return history
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


    # ======================
    # WCZYTANIE HISTORII
    # ======================

    history = load_history()

    last_rank = (
        history[-1].get("rank")
        if history
        else None
    )


    # ======================
    # HIGH SCORES
    # ======================

    highscore = fetch_highscore(last_rank)

    if not highscore:

        send_discord(
            f"⚠️ Nie znaleziono {CHAR_NAME}"
        )

        return


    # ======================
    # CHARACTER
    # ======================

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

    # ======================
    # ŚMIERCI
    # ======================

    deaths = character.get("deaths", [])

    # ======================
    # POPRZEDNI STAN
    # ======================

    if history:

        previous = history[-1]

        previous_level = previous.get(
            "level",
            level
        )

        previous_rank = previous.get(
            "rank",
            rank
        )

        previous_exp = previous.get(
            "exp",
            exp
        )

    else:

        previous_level = level
        previous_rank = rank
        previous_exp = exp


    # ======================
    # DATA TIBIA
    # ======================

    today = tibia_date()

    # ======================
    # DOTYCHCZASOWY PB
    # ======================

    previous_best, previous_best_date = biggest_daily(
        history,
        exclude_date=today
    )

    # ======================
    # AKTUALIZACJA HISTORII
    # ======================

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

history = update_deaths(
    history,
    deaths
)

save_history(history)


    # ======================
    # STATYSTYKI
    # ======================

    gain_today = daily_gain(history)

    gain_week = gain_from_days(
        history,
        7
    )

    gain_month = gain_current_month(
        history
    )

    best, best_date = biggest_daily(
        history
    )

    # ======================
    # PB EXP
    # ======================

    is_pb = (
        gain_today > 0
        and previous_best > 0
        and gain_today > previous_best
    )

    # ======================
    # ZMIANY LVL / RANK
    # ======================

    level_change = (
        level -
        previous_level
    )

    # + = awans w rankingu
    # - = spadek w rankingu

    rank_change = (
        previous_rank -
        rank
    )


    # ======================
    # PROCENTY EXP
    # ======================

    # EXP wymagany od początku
    # aktualnego levela

    current_level_start = exp_for_level(
        level
    )

    # EXP wymagany do następnego levela

    next_level_start = exp_for_level(
        level + 1
    )

    # Cały zakres aktualnego levela

    level_range = (
        next_level_start -
        current_level_start
    )


    # ======================
    # % POZOSTAŁEGO LEVELA
    # ======================

    if level_range > 0:

        remaining_exp = (
            next_level_start -
            exp
        )

        next_level_percent = (
            remaining_exp /
            level_range
        ) * 100

        next_level_percent = round(
            max(
                0,
                min(
                    100,
                    next_level_percent
                )
            )
        )

    else:

        next_level_percent = 0


    # ======================
    # % EXP WBITEGO DZISIAJ
    # ======================

    # Jeżeli nie mamy poprzedniego
    # zapisu, nie próbujemy zgadywać.

    if not history or len(history) < 2:

        today_percent = 0


    # ======================
    # NORMALNY DZIEŃ
    # ======================

    elif level == previous_level:

        if level_range > 0:

            today_percent = (
                gain_today /
                level_range
            ) * 100

            today_percent = round(
                max(
                    0,
                    today_percent
                )
            )

        else:

            today_percent = 0


    # ======================
    # LEVEL UP
    # ======================

    else:

        # ----------------------
        # STARY LEVEL
        # ----------------------

        old_level_start = exp_for_level(
            previous_level
        )

        old_level_end = exp_for_level(
            previous_level + 1
        )

        old_level_range = (
            old_level_end -
            old_level_start
        )


        if old_level_range > 0:

            # Ile EXP brakowało
            # do starego levela

            old_remaining = (
                old_level_end -
                previous_exp
            )

            old_percent = (
                old_remaining /
                old_level_range
            ) * 100

            old_percent = round(
                max(
                    0,
                    min(
                        100,
                        old_percent
                    )
                )
            )

        else:

            old_percent = 0


        # ----------------------
        # NOWY LEVEL
        # ----------------------

        new_level_start = exp_for_level(
            level
        )

        new_level_end = exp_for_level(
            level + 1
        )

        new_level_range = (
            new_level_end -
            new_level_start
        )


        if new_level_range > 0:

            new_exp = (
                exp -
                new_level_start
            )

            new_percent = (
                new_exp /
                new_level_range
            ) * 100

            new_percent = round(
                max(
                    0,
                    min(
                        100,
                        new_percent
                    )
                )
            )

        else:

            new_percent = 0


        # Wynik np.
        # 25% → LVL UP → 10%

        today_percent = (
            f"{old_percent}% "
            f"→ LVL UP → "
            f"{new_percent}%"
        )


    # ======================
    # TEKST ZMIAN
    # ======================

    if level_change > 0:

        level_text = (
            f"**{level} (+{level_change})**"
        )

    elif level_change < 0:

        level_text = (
            f"**{level} ({level_change})**"
        )

    else:

        level_text = (
            f"**{level}**"
        )


    if rank_change > 0:

        rank_text = (
            f"**#{rank} (+{rank_change})**"
        )

    elif rank_change < 0:

        rank_text = (
            f"**#{rank} ({rank_change})**"
        )

    else:

        rank_text = (
            f"**#{rank}**"
        )


    # ======================
    # DISCORD MESSAGE
    # ======================

    message = f"""
🌙 **Daily Exp Report: {CHAR_NAME} 🏹**

⭐ Level {level_text} | 🏆 Rank {rank_text}
✨ Current Exp: **{exp:,}**

📈 Today: **+{format_exp(gain_today)} ({today_percent}%)**
{"🎉 New 🏆 **PB!** 🎊" if is_pb else ""}
📅 7 days: **+{format_exp(gain_week)}**
📆 Month: **+{format_exp(gain_month)}**
📉 Next LVL {level + 1}: **{format_exp(next_level_start - exp)} ({next_level_percent}% remaining)**

🔥 Best: **+{format_exp(best)} ({best_date})**

🤖 Bot: **{bot_days(history)} days** 📅 Since: **{history[0]["date"]}**
🕙 Tibia reset: **{tibia_day_start().strftime("%d.%m %H:%M")}**
🗣️📢 <@338762987261132811>
"""


    # ======================
    # WYSŁANIE
    # ======================

    send_discord(
        message
    )


    print("BOT END")


# ======================
# START
# ======================

if __name__ == "__main__":

    main() 
