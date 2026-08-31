import json
import os
from datetime import date, timedelta

import requests


# ======================
# KONFIGURACJA
# ======================

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEEKLY")

SAVE_FILE = "exp_history.json"

CHAR_NAME = "Mian Stone'arrow"


# ======================
# FORMAT
# ======================

def format_exp(value):
    """Format EXP like 7,955k."""
    sign = "+" if value > 0 else ""
    value = abs(value)

    if value >= 1000:
        return f"{sign}{value / 1000:,.0f}k"

    return f"{sign}{value}"


def format_percent(value):
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


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

        history = data.get(
            "history",
            []
        )

        # Sortujemy na wszelki wypadek.
        history.sort(
            key=lambda item: item["date"]
        )

        return history

    except Exception as e:

        print(
            f"History error: {e}"
        )

        return []


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

                print(
                    "Discord message sent."
                )

                return

            print(
                f"Discord error {response.status_code}: "
                f"{response.text[:200]}"
            )

        except Exception as e:

            print(
                "Discord error:",
                e
            )

        if attempt < 2:

            import time

            time.sleep(3)

    print(
        "Failed to send Discord message."
    )


# ======================
# TYGODNIOWE DANE
# ======================

def get_week_data(history):
    """
    Current Tibia week-to-date report.

    Week starts on Monday and ends on the current Tibia date.

    Example:
        Saturday -> Monday through Saturday.
    """

    if len(history) < 2:

        return None

    latest = history[-1]

    latest_date = date.fromisoformat(
        latest["date"]
    )

    # Monday of the current week
    week_start_date = (
        latest_date -
        timedelta(
            days=latest_date.weekday()
        )
    )

    # Snapshot immediately before Monday
    start_snapshot_date = (
        week_start_date -
        timedelta(days=1)
    )

    by_date = {
        date.fromisoformat(item["date"]): item
        for item in history
    }

    if start_snapshot_date not in by_date:

        print(
            f"Missing history snapshot for "
            f"{start_snapshot_date.isoformat()}."
        )

        return None

    # Monday -> today
    current_dates = [
        week_start_date +
        timedelta(days=i)
        for i in range(
            (latest_date - week_start_date).days + 1
        )
    ]

    if any(
        day not in by_date
        for day in current_dates
    ):

        print(
            "Missing one or more history days "
            "for current week."
        )

        return None

    start = by_date[
        start_snapshot_date
    ]

    daily_entries = [
        by_date[day]
        for day in current_dates
    ]

    daily_gains = []

    previous = start

    for item in daily_entries:

        gain = (
            item["exp"]
            -
            previous["exp"]
        )

        daily_gains.append(
            {
                "date": item["date"],
                "gain": gain,
                "level": item.get(
                    "level",
                    previous.get("level")
                ),
                "rank": item.get(
                    "rank",
                    previous.get("rank")
                ),
            }
        )

        previous = item

    total_gain = (
        latest["exp"]
        -
        start["exp"]
    )

    levels = (
        latest.get("level", 0)
        -
        start.get("level", 0)
    )

    number_of_days = len(
        daily_gains
    )

    avg_day = (
        total_gain /
        number_of_days
    )

    best_day = max(
        daily_gains,
        key=lambda item: item["gain"]
    )

    worst_day = min(
        daily_gains,
        key=lambda item: item["gain"]
    )

    return {
        "start": start,
        "latest": latest,
        "start_date": week_start_date,
        "end_date": latest_date,
        "daily": daily_gains,
        "total_gain": total_gain,
        "levels": levels,
        "avg_day": avg_day,
        "best_day": best_day,
        "worst_day": worst_day,
    }


# ======================
# POPRZEDNI TYDZIEŃ
# ======================

def get_previous_week(history, start_date):
    """
    Returns the complete previous Tibia week:
    Monday -> Sunday.
    """

    previous_start_date = (
        start_date -
        timedelta(days=7)
    )

    previous_end_date = (
        start_date -
        timedelta(days=1)
    )

    # Snapshot immediately before previous Monday
    previous_start_snapshot_date = (
        previous_start_date -
        timedelta(days=1)
    )

    by_date = {
        date.fromisoformat(item["date"]): item
        for item in history
    }

    if (
        previous_start_snapshot_date
        not in by_date
        or
        previous_end_date
        not in by_date
    ):

        return None

    start = by_date[
        previous_start_snapshot_date
    ]

    end = by_date[
        previous_end_date
    ]

    total_gain = (
        end["exp"]
        -
        start["exp"]
    )

    avg_day = (
        total_gain /
        7
    )

    return {
        "total_gain": total_gain,
        "avg_day": avg_day,
        "start": start,
        "end": end,
        "start_date": previous_start_date,
        "end_date": previous_end_date,
    }


# ======================
# PB
# ======================

def find_global_pb(history, current_week):
    """
    Finds the previous all-time PB and all new PBs
    created during the current week.

    Every day that beats the PB known before that day
    is marked as a PB.

    Example:

        Previous PB: 27,722k

        Monday:  30,130k -> PB
        Tuesday: 12,000k
        Wednesday: 30,991k -> PB

    Both Monday and Wednesday are returned in pb_dates.
    """

    current_dates = {
        item["date"]
        for item in current_week["daily"]
    }

    # ======================
    # POPRZEDNI ALL-TIME PB
    # ======================

    previous_pb = 0

    for index in range(1, len(history)):

        current = history[index]
        previous = history[index - 1]

        # Bieżący tydzień sprawdzamy osobno.
        if current["date"] in current_dates:
            continue

        gain = (
            current["exp"]
            -
            previous["exp"]
        )

        if gain > previous_pb:

            previous_pb = gain

    # ======================
    # NOWE PB W BIEŻĄCYM TYGODNIU
    # ======================

    pb_dates = []

    current_pb = previous_pb

    # Przechodzimy chronologicznie.
    for item in current_week["daily"]:

        gain = item["gain"]

        if gain > current_pb:

            pb_dates.append(
                item["date"]
            )

            current_pb = gain

    # ======================
    # FINALNY PB
    # ======================

    global_pb = current_pb

    global_pb_date = None

    if pb_dates:

        # Ostatni rekord z listy PB
        # jest aktualnym all-time PB.
        global_pb_date = pb_dates[-1]

    else:

        # Nie było nowego PB w tym tygodniu.
        # Szukamy daty istniejącego rekordu.

        for index in range(1, len(history)):

            current = history[index]
            previous = history[index - 1]

            if current["date"] in current_dates:
                continue

            gain = (
                current["exp"]
                -
                previous["exp"]
            )

            if gain == global_pb:

                global_pb_date = (
                    current["date"]
                )

    return (
        pb_dates,
        global_pb,
        global_pb_date
    )
# ======================
# WIADOMOŚĆ
# ======================

def build_message(
    week,
    previous_week,
    pb_dates,
    global_pb,
    global_pb_date
):

    start_date = week["start_date"]
    end_date = week["end_date"]

    start_text = start_date.strftime(
        "%d.%m"
    )

    end_text = end_date.strftime(
        "%d.%m.%Y"
    )

    message = f"""
📊 **Weekly Report: {CHAR_NAME} 🏹**

📅 **{start_text} → {end_text}**

📈 Exp: **{format_exp(week["total_gain"])}**
🆙 Levels: **+{week["levels"]}**
⚡ Avg/day: **{format_exp(int(week["avg_day"]))}**

🏆 Best: **{format_exp(week["best_day"]["gain"])}** ({week["best_day"]["date"]})
📉 Worst: **{format_exp(week["worst_day"]["gain"])}** ({week["worst_day"]["date"]})
"""

    # ======================
    # DAILY BREAKDOWN
    # ======================

    message += "\n📋 **Daily:**\n"

    for item in week["daily"]:

        marker = ""

        if item["date"] in pb_dates:

            marker = " 🏆 **PB**"

        message += (
            f"{item['date'][8:10]}."
            f"{item['date'][5:7]}  "
            f"**{format_exp(item['gain'])}**"
            f"{marker}\n"
        )

    # ======================
    # PORÓWNANIE Z POPRZEDNIM TYGODNIEM
    # ======================

    if previous_week:

        total_change = (
            (
                week["total_gain"]
                -
                previous_week["total_gain"]
            )
            /
            previous_week["total_gain"]
            *
            100
            if previous_week["total_gain"] != 0
            else 0
        )

        avg_change = (
            (
                week["avg_day"]
                -
                previous_week["avg_day"]
            )
            /
            previous_week["avg_day"]
            *
            100
            if previous_week["avg_day"] != 0
            else 0
        )

        message += f"""
📈 **vs previous week**
EXP: **{format_percent(total_change)}**
Avg/day: **{format_percent(avg_change)}**
"""

    # ======================
    # RANK CHANGE
    # ======================

    start_rank = week["start"].get(
        "rank"
    )

    end_rank = week["latest"].get(
        "rank"
    )

    if (
        start_rank is not None
        and
        end_rank is not None
    ):

        rank_change = (
            start_rank -
            end_rank
        )

        if rank_change > 0:

            rank_text = (
                f"#{start_rank} → "
                f"#{end_rank} "
                f"(+{rank_change})"
            )

        elif rank_change < 0:

            rank_text = (
                f"#{start_rank} → "
                f"#{end_rank} "
                f"({rank_change})"
            )

        else:

            rank_text = (
                f"#{start_rank} → "
                f"#{end_rank}"
            )

        message += (
            f"\n🏆 Rank: **{rank_text}**\n"
        )

    # ======================
    # GLOBAL PB
    # ======================

    if pb_dates:

        message += (
            f"\n🏆 **NEW PB: "
            f"{format_exp(global_pb)} "
            f"({global_pb_date})**\n"
        )

    return message.strip()


# ======================
# MAIN
# ======================

def main():

    print("=" * 60)

    print(
        "Tibia Weekly EXP Report"
    )

    print("=" * 60)

    history = load_history()

    print(
        f"History entries: "
        f"{len(history)}"
    )

    if not history:

        print(
            "ERROR: No history found."
        )

        return

    week = get_week_data(
        history
    )

    if not week:

        print(
            "ERROR: Not enough consecutive "
            "history for weekly report."
        )

        return

    previous_week = get_previous_week(
        history,
        week["start_date"]
    )

    pb_dates, global_pb, global_pb_date = (
        find_global_pb(
            history,
            week
        )
    )

    print(
        f"Week: "
        f"{week['start_date']} "
        f"-> "
        f"{week['end_date']}"
    )

    print(
        f"EXP: "
        f"{week['total_gain']:,}"
    )

    print(
        f"Avg/day: "
        f"{week['avg_day']:,.0f}"
    )

    print(
        f"Best: "
        f"{week['best_day']['gain']:,} "
        f"({week['best_day']['date']})"
    )

    print(
        f"Worst: "
        f"{week['worst_day']['gain']:,} "
        f"({week['worst_day']['date']})"
    )

    print(
        f"PB dates: "
        f"{pb_dates}"
    )

    print(
        f"Global PB: "
        f"{global_pb:,} "
        f"({global_pb_date})"
    )

    message = build_message(
        week,
        previous_week,
        pb_dates,
        global_pb,
        global_pb_date
    )

    print(
        "\n" +
        message +
        "\n"
    )

    send_discord(
        message
    )

    print(
        "WEEKLY REPORT END"
    )


# ======================
# START
# ======================

if __name__ == "__main__":

    main()