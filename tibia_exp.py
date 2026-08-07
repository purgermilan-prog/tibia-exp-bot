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

def send_discord(embed=None, message=None):

    if not DISCORD_WEBHOOK_URL:

        if message:
            print(message)

        elif embed:
            print(embed)

        return


    if embed:

        payload = {
            "embeds": [embed]
        }

    elif message:

        payload = {
            "content": message
        }

    else:

        return


    for attempt in range(3):

        try:

            response = requests.post(
                DISCORD_WEBHOOK_URL,
                json=payload,
                timeout=15
            )


            if response.status_code in [200, 204]:

                return


            print(
                "Discord HTTP error:",
                response.status_code,
                response.text
            )


        except Exception as e:

            print(
                "Discord error:",
                e
            )


        time.sleep(3)


# ======================
# DISCORD EMBED HELPERS
# ======================

def progress_blocks(percent):

    """
    10 pól.
    0-5%   = 0
    6-15%  = 1
    16-25% = 2
    itd.
    """

    percent = max(
        0,
        min(100, percent)
    )

    blocks = int(
        (percent + 5) // 10
    )

    return max(
        0,
        min(10, blocks)
    )


def build_progress_bars(
    exp,
    level,
    previous_exp,
    previous_level
):

    """
    Tworzy pasek pokazujący:

    🟦 = progress z poprzedniej doby
    🟩 = EXP zdobyty podczas obecnej doby
    ⬜ = pozostały EXP

    Przy level-upie tworzone są dwa paski:
    poprzedni level + nowy level.
    """


    # ======================
    # PRZYPADEK: LEVEL UP
    # ======================

    if previous_level < level:

        # ----------------------
        # Poprzedni level
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

            old_previous_percent = (
                (
                    previous_exp -
                    old_level_start
                )
                /
                old_level_range
            ) * 100

        else:

            old_previous_percent = 0


        old_previous_percent = max(
            0,
            min(100, old_previous_percent)
        )


        old_previous_blocks = progress_blocks(
            old_previous_percent
        )


        # ----------------------
        # Ile EXP weszło dzisiaj
        # do starego levela
        # ----------------------

        old_current_percent = 100

        old_current_blocks = 10


        old_blue = min(
            old_previous_blocks,
            10
        )

        old_green = max(
            0,
            10 - old_blue
        )

        old_empty = 0


        old_bar = (
            "🟦" * old_blue
            +
            "🟩" * old_green
            +
            "⬜" * old_empty
        )


        old_line = (
            f"{previous_level} "
            f"{old_bar} "
            f"{level}"
        )


        # ----------------------
        # Nowy level
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

            new_current_percent = (
                (
                    exp -
                    new_level_start
                )
                /
                new_level_range
            ) * 100

        else:

            new_current_percent = 0


        new_current_percent = max(
            0,
            min(100, new_current_percent)
        )


        new_blocks = progress_blocks(
            new_current_percent
        )


        new_bar = (
            "🟩" * new_blocks
            +
            "⬜" * (10 - new_blocks)
        )


        new_line = (
            f"{level} "
            f"{new_bar} "
            f"{level + 1}"
        )


        return (
            f"{old_line}\n"
            f"{new_line}"
        )


    # ======================
    # NORMALNY DZIEŃ
    # ======================

    current_level_start = exp_for_level(
        level
    )

    next_level_start = exp_for_level(
        level + 1
    )

    level_range = (
        next_level_start -
        current_level_start
    )


    if level_range <= 0:

        return (
            f"{level} "
            f"⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ "
            f"{level + 1}"
        )


    current_percent = (
        (
            exp -
            current_level_start
        )
        /
        level_range
    ) * 100


    previous_percent = (
        (
            previous_exp -
            current_level_start
        )
        /
        level_range
    ) * 100


    current_percent = max(
        0,
        min(100, current_percent)
    )

    previous_percent = max(
        0,
        min(100, previous_percent)
    )


    current_blocks = progress_blocks(
        current_percent
    )

    previous_blocks = progress_blocks(
        previous_percent
    )


    # Jeżeli EXP spadł, nie pokazujemy
    # zielonych pól.
    if current_blocks < previous_blocks:

        blue = current_blocks
        green = 0
        empty = 10 - blue

    else:

        blue = previous_blocks
        green = current_blocks - previous_blocks
        empty = 10 - current_blocks


    bar = (
        "🟦" * blue
        +
        "🟩" * green
        +
        "⬜" * empty
    )


    return (
        f"{level} "
        f"{bar} "
        f"{level + 1}"
    )


def get_embed_color(
    gain_today,
    level_up
):

    # Złoty = level up
    if level_up:

        return 0xF1C40F


    # Czerwony = strata EXP
    if gain_today < 0:

        return 0xE74C3C


    # Niebieski = 0 EXP
    if gain_today == 0:

        return 0x3498DB


    # Zielony = dodatni EXP
    return 0x2ECC71


def format_change(value):

    if value > 0:

        return f"(+{value})"


    if value < 0:

        return f"({value})"


    return ""


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

    highscore = fetch_highscore(
        last_rank
    )


    if not highscore:

        send_discord(
            message=f"⚠️ Nie znaleziono {CHAR_NAME}"
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
    # POPRZEDNI STAN
    # ======================

    if history:

        previous_record = history[-1]

        previous_exp = previous_record.get(
            "exp",
            exp
        )

        previous_level = previous_record.get(
            "level",
            level
        )

        previous_rank = previous_record.get(
            "rank",
            rank
        )

    else:

        previous_exp = exp
        previous_level = level
        previous_rank = rank


    # ======================
    # DATA TIBIA
    # ======================

    today = tibia_date()


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


    save_history(history)


    # ======================
    # STATYSTYKI
    # ======================

    gain_today = daily_gain(
        history
    )


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


    avg_month = average_month(
        history
    )


    best, best_date = biggest_daily(
        history
    )


    # ======================
    # ZMIANY
    # ======================

    level_change = (
        level -
        previous_level
    )


    rank_change = (
        previous_rank -
        rank
    )


    level_up = (
        level_change > 0
    )


    # ======================
    # PROGRESS BAR
    # ======================

    progress_bar = build_progress_bars(
        exp,
        level,
        previous_exp,
        previous_level
    )


    # ======================
    # KOLOR
    # ======================

    embed_color = get_embed_color(
        gain_today,
        level_up
    )


    # ======================
    # LEVEL / RANK
    # ======================

    level_change_text = format_change(
        level_change
    )

    rank_change_text = format_change(
        rank_change
    )


    level_text = (
        f"**{level}** "
        f"{level_change_text}"
        if level_change_text
        else
        f"**{level}**"
    )


    rank_text = (
        f"**#{rank}** "
        f"{rank_change_text}"
        if rank_change_text
        else
        f"**#{rank}**"
    )


    # ======================
    # NEXT LEVEL
    # ======================

    next_level_exp = (
        exp_for_level(level + 1)
        -
        exp
    )


   # ======================
# EMBED
# ======================

embed = {
    "title": f"🌙 Daily EXP Report: {CHAR_NAME} 🏹",
    "color": embed_color,

    "fields": [

        {
            "name": "⭐ Level",
            "value": level_text,
            "inline": True
        },

        {
            "name": "🏆 Rank",
            "value": rank_text,
            "inline": True
        },

        {
            "name": "✨ Current EXP",
            "value": f"**{exp:,}**",
            "inline": False
        },

        {
            "name": "📈 Today",
            "value": f"**{format_exp(gain_today)}**",
            "inline": True
        },

        {
            "name": "📅 7 days",
            "value": f"**{format_exp(gain_week)}**",
            "inline": True
        },

        {
            "name": "📆 Month",
            "value": f"**{format_exp(gain_month)}**",
            "inline": True
        },

        {
            "name": f"📉 Next LVL {level + 1}",
            "value": f"**{format_exp(next_level_exp)}**",
            "inline": True
        },

        {
            "name": "⚡ Avg/day",
            "value": f"**{format_exp(int(avg))}**",
            "inline": True
        },

        {
            "name": "⚡ Avg/month",
            "value": f"**{format_exp(int(avg_month))}**",
            "inline": True
        },

        {
            "name": "📊 Progress",
            "value": progress_bar,
            "inline": False
        },

        {
            "name": "🚀 Total gain",
            "value": f"**+{format_exp(exp_since_start(history))} EXP**",
            "inline": True
        },

        {
            "name": "🆙 Levels",
            "value": f"**+{levels_since_start(history)}**",
            "inline": True
        },

        {
            "name": "🔥 Best",
            "value": f"**+{format_exp(best)}** ({best_date})",
            "inline": True
        }
    ],

    "footer": {
        "text": (
            f"🤖 Bot: {bot_days(history)} days"
            f" • Since: {history[0]['date']}"
            f" • Tibia reset: "
            f"{tibia_day_start().strftime('%d.%m %H:%M')}"
        )
    }
}


# ======================
# WYSŁANIE
# ======================

send_discord(
    embed=embed
)


    print("BOT END")


# ======================
# START
# ======================

if __name__ == "__main__":

    main()
