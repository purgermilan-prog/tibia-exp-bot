import json
import os
from datetime import date, timedelta

import requests


# ======================
# KONFIGURACJA
# ======================

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

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
        with open(SAVE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        history = data.get("history", [])

        # Sortujemy na wszelki wypadek.
        history.sort(key=lambda item: item["date"])

        return history

    except Exception as e:
        print(f"History error: {e}")
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
                json={"content": message},
                timeout=15
            )

            if response.status_code in [200, 204]:
                print("Discord message sent.")
                return

            print(
                f"Discord error {response.status_code}: "
                f"{response.text[:200]}"
            )

        except Exception as e:
            print("Discord error:", e)

        if attempt < 2:
            import time
            time.sleep(3)

    print("Failed to send Discord message.")


# ======================
# TYGODNIOWE DANE
# ======================

def get_week_data(history):
    """
    Weekly report is generated on Monday after the Tibia reset.

    The current history entry represents the EXP gained during the
    previous Tibia day. Therefore, on Monday we use the current Monday
    entry plus the six preceding entries = 7 completed Tibia days.

    Example:
        Monday 24.08 report
        period: 17.08 10:00 -> 24.08 10:00
        daily gains: entries dated 18.08 ... 24.08
    """

    if len(history) < 8:
        return None

    latest = history[-1]
    latest_date = date.fromisoformat(latest["date"])

    # We expect the latest saved entry to be today's Tibia date.
    expected_dates = [
        latest_date - timedelta(days=days)
        for days in range(7, -1, -1)
    ]

    by_date = {
        date.fromisoformat(item["date"]): item
        for item in history
    }

    # Need the starting snapshot + 7 daily snapshots.
    if any(day not in by_date for day in expected_dates):
        print("Missing one or more history days for weekly report.")
        print(
            "Expected:",
            ", ".join(day.isoformat() for day in expected_dates)
        )
        return None

    start = by_date[expected_dates[0]]
    daily_entries = [
        by_date[day]
        for day in expected_dates[1:]
    ]

    daily_gains = []

    previous = start

    for item in daily_entries:
        gain = item["exp"] - previous["exp"]

        daily_gains.append({
            "date": item["date"],
            "gain": gain,
            "level": item.get("level", previous.get("level")),
            "rank": item.get("rank", previous.get("rank")),
        })

        previous = item

    total_gain = latest["exp"] - start["exp"]

    # Levels gained during the period.
    levels = latest.get("level", 0) - start.get("level", 0)

    # Average over exactly 7 completed Tibia days.
    avg_day = total_gain / 7

    best_day = max(daily_gains, key=lambda item: item["gain"])
    worst_day = min(daily_gains, key=lambda item: item["gain"])

    return {
        "start": start,
        "latest": latest,
        "start_date": expected_dates[0],
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
    Previous week's total is calculated from the 8 snapshots immediately
    preceding the current week's starting snapshot.
    """

    previous_end_date = start_date
    previous_start_date = start_date - timedelta(days=7)

    by_date = {
        date.fromisoformat(item["date"]): item
        for item in history
    }

    if (
        previous_start_date not in by_date
        or previous_end_date not in by_date
    ):
        return None

    start = by_date[previous_start_date]
    end = by_date[previous_end_date]

    total_gain = end["exp"] - start["exp"]
    avg_day = total_gain / 7

    return {
        "total_gain": total_gain,
        "avg_day": avg_day,
        "start": start,
        "end": end,
    }


# ======================
# PB
# ======================

def find_global_pb(history, current_week):
    """
    Finds the biggest completed daily EXP gain before the current week's
    final snapshot. The current week's gains can then be marked as PB.
    """

    current_dates = {
        item["date"]
        for item in current_week["daily"]
    }

    best = 0
    best_date = None

    for index in range(1, len(history)):
        current = history[index]
        previous = history[index - 1]

        # Current week is checked separately.
        if current["date"] in current_dates:
            continue

        gain = current["exp"] - previous["exp"]

        if gain > best:
            best = gain
            best_date = current["date"]

    return best, best_date


# ======================
# WIADOMOŚĆ
# ======================

def build_message(week, previous_week, global_pb, global_pb_date):
    start_date = week["start_date"]
    end_date = week["end_date"]

    start_text = start_date.strftime("%d.%m")
    end_text = end_date.strftime("%d.%m.%Y")

    message = f"""
📊 **Weekly Exp Report: {CHAR_NAME} 🏹**

📅 **{start_text} → {end_text}**

📈 EXP: **{format_exp(week["total_gain"])}**
🆙 Levels: **+{week["levels"]}**
⚡ Avg/day: **{format_exp(int(week["avg_day"]))}**

🏆 Best: **{format_exp(week["best_day"]["gain"])}** ({week["best_day"]["date"]})
📉 Worst: **{format_exp(week["worst_day"]["gain"])}** ({week["worst_day"]["date"]})
"""

    # Daily breakdown
    message += "\n📋 **Daily:**\n"

    for item in week["daily"]:
        marker = ""

        if item["gain"] > global_pb and global_pb > 0:
            marker = " 🏆 **PB**"

        message += (
            f"{item['date'][8:10]}.{item['date'][5:7]}  "
            f"**{format_exp(item['gain'])}**{marker}\n"
        )

    # Comparison with previous week
    if previous_week:
        total_change = (
            (week["total_gain"] - previous_week["total_gain"])
            / previous_week["total_gain"] * 100
            if previous_week["total_gain"] != 0
            else 0
        )

        avg_change = (
            (week["avg_day"] - previous_week["avg_day"])
            / previous_week["avg_day"] * 100
            if previous_week["avg_day"] != 0
            else 0
        )

        message += f"""
📈 **vs previous week**
EXP: **{format_percent(total_change)}**
Avg/day: **{format_percent(avg_change)}**
"""

    # Rank change
    start_rank = week["start"].get("rank")
    end_rank = week["latest"].get("rank")

    if start_rank is not None and end_rank is not None:
        rank_change = start_rank - end_rank

        if rank_change > 0:
            rank_text = f"#{start_rank} → #{end_rank} (+{rank_change})"
        elif rank_change < 0:
            rank_text = f"#{start_rank} → #{end_rank} ({rank_change})"
        else:
            rank_text = f"#{start_rank} → #{end_rank}"

        message += f"\n🏆 Rank: **{rank_text}**\n"

    # Global PB
    current_week_pb = max(
        (item["gain"] for item in week["daily"]),
        default=0
    )

    if current_week_pb > global_pb and global_pb > 0:
        pb_date = max(
            week["daily"],
            key=lambda item: item["gain"]
        )["date"]

        message += (
            f"\n🏆 **NEW PB: {format_exp(current_week_pb)} "
            f"({pb_date})**\n"
        )

    return message.strip()


# ======================
# MAIN
# ======================

def main():
    print("=" * 60)
    print("Tibia Weekly EXP Report")
    print("=" * 60)

    history = load_history()

    print(f"History entries: {len(history)}")

    if not history:
        print("ERROR: No history found.")
        return

    week = get_week_data(history)

    if not week:
        print("ERROR: Not enough consecutive history for weekly report.")
        return

    previous_week = get_previous_week(
        history,
        week["start_date"]
    )

    global_pb, global_pb_date = find_global_pb(
        history,
        week
    )

    print(
        f"Week: {week['start_date']} -> {week['end_date']}"
    )
    print(
        f"EXP: {week['total_gain']:,}"
    )
    print(
        f"Avg/day: {week['avg_day']:,.0f}"
    )
    print(
        f"Best: {week['best_day']['gain']:,} "
        f"({week['best_day']['date']})"
    )
    print(
        f"Worst: {week['worst_day']['gain']:,} "
        f"({week['worst_day']['date']})"
    )

    message = build_message(
        week,
        previous_week,
        global_pb,
        global_pb_date
    )

    print("\n" + message + "\n")

    send_discord(message)

    print("WEEKLY REPORT END")


if __name__ == "__main__":
    main()
