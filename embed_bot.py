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

SAVE_FILE = "embed_history.json"

API_RETRIES = 3
API_TIMEOUT = 20

# Stały kolor embeda: #F1E0C6
EMBED_COLOR = 0xF1E0C6


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

        return {}

    try:

        with open(
            SAVE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, dict):

                return data

    except Exception as e:

        print(
            f"History load error: {e}"
        )

    return {}


def save_history(history):

    try:

        with open(
            SAVE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                history,
                f,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"History saved to {SAVE_FILE}"
        )

    except Exception as e:

        print(
            f"History save error: {e}"
        )


# ======================
# AKTUALIZACJA HISTORII
# ======================

def update_history(
    history,
    date,
    exp,
    level,
    rank
):

    history[date] = {
        "exp": exp,
        "level": level,
        "rank": rank
    }

    return history


# ======================
# POPRZEDNI DZIEŃ TIBII
# ======================

def get_previous_day(history):

    today = tibia_date()

    dates = sorted(
        [
            date
            for date in history.keys()
            if date < today
        ],
        reverse=True
    )

    if not dates:

        return None

    return dates[0]


# ======================
# PRZYROST EXP
# ======================

def get_exp_gain(
    history,
    date
):

    if date not in history:

        return 0

    dates = sorted(
        [
            d
            for d in history.keys()
            if d < date
        ],
        reverse=True
    )

    if not dates:

        return 0

    previous_date = dates[0]

    current_exp = history[date]["exp"]
    previous_exp = history[previous_date]["exp"]

    return current_exp - previous_exp


# ======================
# STATYSTYKI
# ======================

def calculate_stats(
    history,
    current_exp,
    current_level
):

    today = tibia_date()

    dates = sorted(history.keys())

    today_gain = 0
    week_gain = 0
    month_gain = 0

    # ----------------------
    # DZISIAJ
    # ----------------------

    if today in history:

        previous_dates = [
            d
            for d in dates
            if d < today
        ]

        if previous_dates:

            previous_date = previous_dates[-1]

            today_gain = (
                current_exp
                -
                history[previous_date]["exp"]
            )

    # ----------------------
    # 7 DNI
    # ----------------------

    cutoff_7 = (
        tibia_datetime().date()
        -
        timedelta(days=7)
    )

    old_week_dates = [
        d
        for d in dates
        if datetime.fromisoformat(d).date()
        <= cutoff_7
    ]

    if old_week_dates:

        old_date = old_week_dates[-1]

        week_gain = (
            current_exp
            -
            history[old_date]["exp"]
        )

    # ----------------------
    # MIESIĄC
    # ----------------------

    current_month = (
        tibia_datetime().year,
        tibia_datetime().month
    )

    month_dates = [
        d
        for d in dates
        if (
            datetime.fromisoformat(d).year,
            datetime.fromisoformat(d).month
        )
        == current_month
    ]

    if month_dates:

        first_month_date = month_dates[0]

        month_gain = (
            current_exp
            -
            history[first_month_date]["exp"]
        )

    # ----------------------
    # ŚREDNIA / DZIEŃ
    # ----------------------

    if len(dates) > 1:

        first_date = datetime.fromisoformat(
            dates[0]
        ).date()

        last_date = datetime.fromisoformat(
            dates[-1]
        ).date()

        days = (
            last_date - first_date
        ).days

        if days > 0:

            total_gain = (
                current_exp
                -
                history[dates[0]]["exp"]
            )

            avg_day = (
                total_gain / days
            )

        else:

            avg_day = 0

    else:

        avg_day = 0

    # ----------------------
    # ŚREDNIA / MIESIĄC
    # ----------------------

    avg_month = (
        month_gain / max(1, len(month_dates))
    )

    # ----------------------
    # NEXT LEVEL
    # ----------------------

    next_level_exp = exp_for_level(
        current_level + 1
    )

    current_level_exp = exp_for_level(
        current_level
    )

    exp_into_level = (
        current_exp
        -
        current_level_exp
    )

    exp_needed = (
        next_level_exp
        -
        current_exp
    )

    level_total = (
        next_level_exp
        -
        current_level_exp
    )

    if level_total > 0:

        progress = (
            exp_into_level
            /
            level_total
        )

    else:

        progress = 0

    progress = max(
        0,
        min(1, progress)
    )

    return {
        "today_gain": today_gain,
        "week_gain": week_gain,
        "month_gain": month_gain,
        "avg_day": avg_day,
        "avg_month": avg_month,
        "next_level_exp": next_level_exp,
        "exp_needed": max(0, exp_needed),
        "progress": progress
    }


# ======================
# PROGRESS BAR
# ======================

def build_progress_bar(
    current_exp,
    current_level,
    gain,
    blocks=10
):

    current_level_exp = exp_for_level(
        current_level
    )

    next_level_exp = exp_for_level(
        current_level + 1
    )

    level_total = (
        next_level_exp
        -
        current_level_exp
    )

    if level_total <= 0:

        return "░" * blocks

    current_progress = (
        current_exp
        -
        current_level_exp
    )

    current_progress = max(
        0,
        min(
            current_progress,
            level_total
        )
    )

    filled = int(
        round(
            (
                current_progress
                /
                level_total
            )
            * blocks
        )
    )

    filled = max(
        0,
        min(blocks, filled)
    )

    return (
        "█" * filled
        +
        "░" * (blocks - filled)
    )


# ======================
# FORMAT ZMIANY
# ======================

def format_change(value):

    if value > 0:

        return f"+{format_exp(value)}"

    if value < 0:

        return f"-{format_exp(abs(value))}"

    return "0"


# ======================
# DISCORD EMBED
# ======================

def build_embed(
    character,
    highscore,
    stats,
    previous_data
):

    level = character.get(
        "level",
        "?"
    )

    current_exp = character.get(
        "experience",
        0
    )

    rank = highscore.get(
        "rank",
        "?"
    )

    today_gain = stats[
        "today_gain"
    ]

    week_gain = stats[
        "week_gain"
    ]

    month_gain = stats[
        "month_gain"
    ]

    avg_day = stats[
        "avg_day"
    ]

    avg_month = stats[
        "avg_month"
    ]

    exp_needed = stats[
        "exp_needed"
    ]

    progress = stats[
        "progress"
    ]

    progress_bar = build_progress_bar(
        current_exp,
        level,
        today_gain
    )

    progress_percent = (
        progress * 100
    )

    embed = {
        "title": (
            f"{CHAR_NAME} — {WORLD}"
        ),

        "color": EMBED_COLOR,

        "fields": [

            {
                "name": "Level",
                "value": str(level),
                "inline": True
            },

            {
                "name": "Rank",
                "value": f"#{rank}",
                "inline": True
            },

            {
                "name": "Current EXP",
                "value": (
                    f"{current_exp:,}"
                ),
                "inline": True
            },

            {
                "name": "Today",
                "value": format_change(
                    today_gain
                ),
                "inline": True
            },

            {
                "name": "7 days",
                "value": format_change(
                    week_gain
                ),
                "inline": True
            },

            {
                "name": "Month",
                "value": format_change(
                    month_gain
                ),
                "inline": True
            },

            {
                "name": "Next Level",
                "value": format_exp(
                    exp_needed
                ),
                "inline": True
            },

            {
                "name": "Avg/day",
                "value": format_exp(
                    int(avg_day)
                ),
                "inline": True
            },

            {
                "name": "Avg/month",
                "value": format_exp(
                    int(avg_month)
                ),
                "inline": True
            },

            {
                "name": "Progress",
                "value": (
                    f"{progress_bar} "
                    f"{progress_percent:.1f}%"
                ),
                "inline": False
            }

        ],

        "footer": {
            "text": (
                f"Tibia day: {tibia_date()} "
                f"| Reset: 10:00"
            )
        },

        "timestamp": (
            datetime.utcnow()
            .isoformat()
            +
            "Z"
        )
    }

    return embed


# ======================
# DISCORD
# ======================

def send_discord(embed):

    if not DISCORD_WEBHOOK_URL:

        print(
            "DISCORD_WEBHOOK_URL not configured"
        )

        return False

    payload = {
        "embeds": [
            embed
        ]
    }

    for attempt in range(
        1,
        API_RETRIES + 1
    ):

        try:

            response = requests.post(
                DISCORD_WEBHOOK_URL,
                json=payload,
                timeout=API_TIMEOUT
            )

            if response.status_code in (
                200,
                204
            ):

                print(
                    "Discord message sent."
                )

                return True

            print(
                "Discord error:",
                response.status_code,
                response.text
            )

        except Exception as e:

            print(
                f"Discord exception: {e}"
            )

        time.sleep(3)

    return False
# ======================
# MAIN
# ======================

def main():

    print("=" * 60)
    print("Tibia EXP Bot")
    print("=" * 60)

    # ----------------------
    # POBIERANIE POSTACI
    # ----------------------

    print(
        f"Fetching character: {CHAR_NAME}"
    )

    character = fetch_character_data()

    if not character:

        print(
            "ERROR: Could not fetch character data."
        )

        return

    current_exp = character.get(
        "experience"
    )

    current_level = character.get(
        "level"
    )

    if current_exp is None:
        print(
            "ERROR: Character EXP not found."
        )
        return

    if current_level is None:
        print(
            "ERROR: Character level not found."
        )
        return

    print(
        f"Level: {current_level}"
    )

    print(
        f"EXP: {current_exp:,}"
    )

    # ----------------------
    # HISTORIA
    # ----------------------

    history = load_history()

    print(
        f"History entries: {len(history)}"
    )

    # ----------------------
    # OSTATNI ZAPISANY RANK
    # ----------------------

    last_rank = None

    if history:

        dates = sorted(history.keys())

        last_date = dates[-1]

        try:

            last_rank = history[
                last_date
            ].get("rank")

        except Exception:

            last_rank = None

    # ----------------------
    # HIGHSCORE
    # ----------------------

    highscore = fetch_highscore(
        last_rank
    )

    if not highscore:

        print(
            "WARNING: Could not find character "
            "in highscores."
        )

        # Nie przerywamy całkowicie.
        # Rank ustawiamy na poprzedni,
        # jeżeli taki istnieje.

        highscore = {
            "rank": last_rank or "?"
        }

    rank = highscore.get(
        "rank",
        "?"
    )

    print(
        f"Rank: #{rank}"
    )

    # ----------------------
    # DATA TIBII
    # ----------------------

    today = tibia_date()

    print(
        f"Tibia day: {today}"
    )

    # ----------------------
    # POPRZEDNI STAN
    # ----------------------

    previous_data = None

    if today in history:

        previous_data = history[today]

    # ----------------------
    # AKTUALIZACJA HISTORII
    # ----------------------

    history = update_history(
        history,
        today,
        current_exp,
        current_level,
        rank
    )

    # ----------------------
    # STATYSTYKI
    # ----------------------

    stats = calculate_stats(
        history,
        current_exp,
        current_level
    )

    print("-" * 60)

    print(
        f"Today: "
        f"{format_change(stats['today_gain'])}"
    )

    print(
        f"7 days: "
        f"{format_change(stats['week_gain'])}"
    )

    print(
        f"Month: "
        f"{format_change(stats['month_gain'])}"
    )

    print(
        f"Avg/day: "
        f"{format_exp(int(stats['avg_day']))}"
    )

    print(
        f"Avg/month: "
        f"{format_exp(int(stats['avg_month']))}"
    )

    print(
        f"Next level: "
        f"{format_exp(stats['exp_needed'])}"
    )

    print(
        f"Progress: "
        f"{stats['progress'] * 100:.1f}%"
    )

    # ----------------------
    # ZAPIS HISTORII
    # ----------------------

    save_history(history)

    # ----------------------
    # EMBED
    # ----------------------

    embed = build_embed(
        character,
        highscore,
        stats,
        previous_data
    )

    # ----------------------
    # DISCORD
    # ----------------------

    success = send_discord(
        embed
    )

    if success:

        print(
            "Bot finished successfully."
        )

    else:

        print(
            "Bot finished with Discord error."
        )

    print("=" * 60)


# ======================
# START
# ======================


    main()
  # ======================
# DEBUG / DIAGNOSTYKA
# ======================

def print_history(history):

    print()
    print("=" * 60)
    print("HISTORY")
    print("=" * 60)

    if not history:

        print("History is empty.")

        return

    for date in sorted(history.keys()):

        entry = history[date]

        exp = entry.get(
            "exp",
            "?"
        )

        level = entry.get(
            "level",
            "?"
        )

        rank = entry.get(
            "rank",
            "?"
        )

        print(
            f"{date} | "
            f"Level {level} | "
            f"Rank #{rank} | "
            f"EXP {exp:,}"
        )

    print("=" * 60)


def print_current_status(
    character,
    highscore
):

    print()
    print("=" * 60)
    print("CURRENT STATUS")
    print("=" * 60)

    print(
        f"Character: {CHAR_NAME}"
    )

    print(
        f"World: {WORLD}"
    )

    print(
        f"Level: "
        f"{character.get('level', '?')}"
    )

    print(
        f"EXP: "
        f"{character.get('experience', 0):,}"
    )

    print(
        f"Rank: "
        f"#{highscore.get('rank', '?')}"
    )

    print(
        f"Tibia day: "
        f"{tibia_date()}"
    )

    print(
        f"Day starts: "
        f"{tibia_day_start()}"
    )

    print("=" * 60)


# ======================
# TEST API
# ======================

def test_api():

    print()
    print("=" * 60)
    print("API TEST")
    print("=" * 60)

    character = fetch_character_data()

    if not character:

        print(
            "Character API: FAILED"
        )

        return False

    print(
        "Character API: OK"
    )

    print(
        f"Level: "
        f"{character.get('level', '?')}"
    )

    print(
        f"EXP: "
        f"{character.get('experience', 0):,}"
    )

    highscore = fetch_highscore()

    if not highscore:

        print(
            "Highscore API: FAILED"
        )

        return False

    print(
        "Highscore API: OK"
    )

    print(
        f"Rank: "
        f"#{highscore.get('rank', '?')}"
    )

    print("=" * 60)

    return True


# ======================
# PEŁNA DIAGNOSTYKA
# ======================

def diagnostic():

    print()
    print("=" * 60)
    print("FULL DIAGNOSTIC")
    print("=" * 60)

    print(
        f"Current system time: "
        f"{datetime.now()}"
    )

    print(
        f"Tibia datetime: "
        f"{tibia_datetime()}"
    )

    print(
        f"Tibia date: "
        f"{tibia_date()}"
    )

    print(
        f"Tibia day start: "
        f"{tibia_day_start()}"
    )

    print()

    history = load_history()

    print_history(
        history
    )

    character = fetch_character_data()

    if not character:

        print(
            "Character data unavailable."
        )

        return

    highscore = fetch_highscore()

    if not highscore:

        highscore = {
            "rank": "?"
        }

    print_current_status(
        character,
        highscore
    )

    print(
        "Diagnostic finished."
    )

    print("=" * 60)


# ======================
# START
# ======================

if __name__ == "__main__":

    main()
