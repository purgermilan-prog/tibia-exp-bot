import requests
import os
import json
import time
from datetime import datetime, timedelta

DISCORD_WEBHOOK_URL = os.getenv("GLOS")

GUILD_NAME = "General Levy of Sarmats"
WORLD = "Antica"

SAVE_FILE = "guild_exp_history.json"

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
# API REQUEST
# ======================

def api_get(url):

    for attempt in range(1, API_RETRIES + 1):

        try:

            r = requests.get(
                url,
                timeout=API_TIMEOUT,
                headers={
                    "User-Agent": "TibiaGuildEXPBot/1.0"
                }
            )

            if r.status_code == 200:
                return r.json()

            print(
                f"API error {r.status_code}, attempt {attempt}/{API_RETRIES}"
            )

        except Exception as e:

            print(
                f"API exception: {e}, attempt {attempt}/{API_RETRIES}"
            )

        time.sleep(3)

    return None


# ======================
# GUILD MEMBERS
# ======================

def fetch_guild_members():

    url = (
        "https://api.tibiadata.com/v4/guild/"
        f"{GUILD_NAME.replace(' ', '%20')}"
    )

    data = api_get(url)

    if not data:
        return []

    try:

        members = data["guild"]["members"]

        return [
            m["name"]
            for m in members
        ]

    except Exception:

        return []


# ======================
# HIGHSCORES (OPTYMALIZACJA)
# ======================

def fetch_all_highscores():

    players = {}

    url = (
        f"https://api.tibiadata.com/v4/highscores/"
        f"{WORLD}/experience/all/1"
    )

    first = api_get(url)

    if not first:
        return {}

    try:

        total_pages = (
            first["highscores"]
            ["highscore_page"]
            ["total_pages"]
        )

    except Exception:

        total_pages = 50

    print(f"Loading {total_pages} highscores pages...")

    for page in range(1, total_pages + 1):

        url = (
            f"https://api.tibiadata.com/v4/highscores/"
            f"{WORLD}/experience/all/{page}"
        )

        data = api_get(url)

        if not data:
            continue

        try:

            players_list = (
                data["highscores"]
                ["highscore_list"]
            )

        except Exception:

            continue

        for p in players_list:

            players[p["name"].lower()] = p["value"]

        print(f"Page {page}/{total_pages}")

    print(f"Loaded {len(players)} players")

    return players


# ======================
# HISTORY
# ======================

def load_history():

    if not os.path.exists(SAVE_FILE):

        return {
            "members": {},
            "guild_daily": []
        }

    try:

        with open(
            SAVE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {
            "members": {},
            "guild_daily": []
        }


def save_history(data):

    try:

        with open(
            SAVE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False
            )

        print(
            f"Saved history to {SAVE_FILE}"
        )

    except Exception as e:

        print(
            "SAVE ERROR:",
            e
        )


# ======================
# TOP 3 FORMAT
# ======================

def get_top3(data):

    if not data:

        return []

    return sorted(
        data.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]


def format_top3(title, players):

    text = f"\n{title}\n"

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for i, player in enumerate(players):

        text += (
            f"{medals[i]} "
            f"{player[0]} "
            f"(+{player[1]:,})\n"
        )

    if not players:

        text += "Brak danych\n"

    return text


# ======================
# MAIN
# ======================
def main():

    print("GUILD BOT START")

    members = fetch_guild_members()

    if not members:

        send_discord(
            f"⚠️ Nie znaleziono gildii **{GUILD_NAME}**."
        )

        return

    # ======================
    # POBIERZ HIGHSCORES TYLKO RAZ
    # ======================

    all_players = fetch_all_highscores()

    if not all_players:

        send_discord(
            "⚠️ Nie udało się pobrać highscores."
        )

        return

    history = load_history()

    # DOBA TIBII: 10:00 -> 10:00
    today = tibia_date()

    member_gain_today = {}
    member_gain_week = {}
    member_gain_month = {}

    total_exp_today = 0

    # ======================
    # FETCH EXP MEMBERS
    # ======================

    for name in members:

        exp = all_players.get(name.lower())

        if exp is None:
            print(f"{name} not found on highscores")
            continue

        total_exp_today += exp

        # NOWY GRACZ

        if name not in history["members"]:

            history["members"][name] = [
                {
                    "date": today,
                    "exp": exp
                }
            ]

        member_history = history["members"][name]

        # Aktualizacja dzisiejszego wpisu

        if (
            member_history
            and member_history[-1]["date"] == today
        ):

            member_history[-1]["exp"] = exp

        else:

            member_history.append(
                {
                    "date": today,
                    "exp": exp
                }
            )

        # ======================
        # DZISIAJ
        # ======================

        if len(member_history) >= 2:

            member_gain_today[name] = (
                exp -
                member_history[-2]["exp"]
            )

        else:

            member_gain_today[name] = 0

        # ======================
        # TYDZIEŃ
        # ======================

        week_limit = (
            tibia_datetime()
            -
            timedelta(days=7)
        ).date().isoformat()

        old_week = next(
            (
                x for x in member_history
                if x["date"] >= week_limit
            ),
            None
        )

        member_gain_week[name] = (
            exp - old_week["exp"]
            if old_week
            else 0
        )

        # ======================
        # MIESIĄC
        # ======================

        month_prefix = (
            tibia_datetime()
            .strftime("%Y-%m")
        )

        month_data = [
            x for x in member_history
            if x["date"].startswith(month_prefix)
        ]

        if len(month_data) >= 2:

            member_gain_month[name] = (
                exp -
                month_data[0]["exp"]
            )

        else:

            member_gain_month[name] = 0

    # ======================
    # GUILD DAILY HISTORY
    # ======================

    guild_daily = history["guild_daily"]

    if (
        guild_daily
        and guild_daily[-1]["date"] == today
    ):

        guild_daily[-1]["exp_total"] = total_exp_today

    else:

        guild_daily.append(
            {
                "date": today,
                "exp_total": total_exp_today
            }
        )

    if len(guild_daily) >= 2:

        gain_today_total = (
            total_exp_today -
            guild_daily[-2]["exp_total"]
        )

    else:

        gain_today_total = 0

    week_limit = (
        tibia_datetime()
        -
        timedelta(days=7)
    ).date().isoformat()

    old_week = next(
        (
            x for x in guild_daily
            if x["date"] >= week_limit
        ),
        None
    )

    gain_week_total = (
        total_exp_today -
        old_week["exp_total"]
        if old_week
        else 0
    )

    month_prefix = (
        tibia_datetime()
        .strftime("%Y-%m")
    )

    month_data = [
        x for x in guild_daily
        if x["date"].startswith(month_prefix)
    ]

    if len(month_data) >= 2:

        gain_month_total = (
            total_exp_today -
            month_data[0]["exp_total"]
        )

    else:

        gain_month_total = 0

    # ======================
    # TOP 3 PLAYERS
    # ======================

    top_today = get_top3(member_gain_today)
    top_week = get_top3(member_gain_week)
    top_month = get_top3(member_gain_month)

    # ======================
    # ACTIVE MEMBERS
    # ======================

    active_yesterday = sum(
        1 for gain in member_gain_today.values()
        if gain > 0
    )

    active_last_7_days = sum(
        1 for gain in member_gain_week.values()
        if gain > 0
    )
    # ======================
    # GUILD RECORDS TOP 3
    # ======================

    guild_records = []

    for i in range(1, len(guild_daily)):

        gain = (
            guild_daily[i]["exp_total"]
            -
            guild_daily[i-1]["exp_total"]
        )

        guild_records.append(
            (
                guild_daily[i]["date"],
                gain
            )
        )

    guild_records_top3 = sorted(
        guild_records,
        key=lambda x: x[1],
        reverse=True
    )[:3]


    # ======================
    # INDIVIDUAL RECORDS TOP 3
    # ======================

    individual_records = []

    for name, hist in history["members"].items():

        for i in range(1, len(hist)):

            gain = (
                hist[i]["exp"]
                -
                hist[i-1]["exp"]
            )

            individual_records.append(
                (
                    name,
                    hist[i]["date"],
                    gain
                )
            )


    individual_records_top3 = sorted(
        individual_records,
        key=lambda x: x[2],
        reverse=True
    )[:3]


    save_history(history)


    # ======================
    # FORMAT RECORDS
    # ======================

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]


    guild_record_text = "\n🔥 Guild daily records:\n"


    if guild_records_top3:

        for i, record in enumerate(guild_records_top3):

            guild_record_text += (
                f"{medals[i]} "
                f"+{record[1]:,} "
                f"({record[0]})\n"
            )

    else:

        guild_record_text += "Brak danych\n"



    individual_record_text = "\n🔥 Individual records:\n"


    if individual_records_top3:

        for i, record in enumerate(individual_records_top3):

            individual_record_text += (
                f"{medals[i]} "
                f"{record[0]} "
                f"+{record[2]:,} "
                f"({record[1]})\n"
            )

    else:

        individual_record_text += "Brak danych\n"



    # ======================
    # MESSAGE
    # ======================

    message = f"""
🌙 **Daily Exp Report — {GUILD_NAME} ({WORLD})**

👥 Members: **{len(members)}**
🟢 Active yesterday:
**{active_yesterday}/{len(members)} ({active_yesterday / len(members) * 100:.1f}%)**
🟢 Active last 7 days:
**{active_last_7_days}/{len(members)} ({active_last_7_days / len(members) * 100:.1f}%)**

📦 Total exp:
**{total_exp_today:,}**
📈 Today:
**+{gain_today_total:,}**
📅 Last 7 days:
**+{gain_week_total:,}**
📆 Current month:
**+{gain_month_total:,}**


{format_top3("🏆 Today TOP 3:", top_today)}
{format_top3("🏆 Week TOP 3:", top_week)}
{format_top3("🏆 Month TOP 3:", top_month)}

{guild_record_text}
{individual_record_text}
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



if __name__ == "__main__":

    main()