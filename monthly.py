import json
import os
import calendar
from datetime import date, datetime

import requests


# ======================
# KONFIGURACJA
# ======================

HISTORY_FILE = "exp_history.json"

DISCORD_WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK_MONTHLY"
)

# Opcjonalnie:
# REPORT_MONTH=2026-08
#
# Jeżeli brak, bot automatycznie
# wybierze poprzedni miesiąc.
REPORT_MONTH = os.getenv("REPORT_MONTH")


# ======================
# HISTORIA
# ======================

def load_history():

    if not os.path.exists(HISTORY_FILE):

        print(
            "ERROR: History file not found."
        )

        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            history = json.load(file)

        print(
            "History type:",
            type(history).__name__
        )

        # ======================
        # FORMAT:
        # {"history": [...]}
        # ======================

        if isinstance(history, dict):

            if "history" in history:

                history = history["history"]

                print(
                    "Found 'history' list."
                )

            else:

                print(
                    "History keys:",
                    len(history)
                )

                normalized = []

                for entry_date, data in history.items():

                    print(
                        "Processing:",
                        entry_date,
                        "type:",
                        type(data).__name__
                    )

                    if not isinstance(
                        data,
                        dict
                    ):

                        continue

                    entry = dict(data)

                    entry.setdefault(
                        "date",
                        entry_date
                    )

                    normalized.append(
                        entry
                    )

                print(
                    "Normalized entries:",
                    len(normalized)
                )

                return normalized

        # ======================
        # FORMAT:
        # [...]
        # ======================

        if isinstance(history, list):

            print(
                "History entries:",
                len(history)
            )

            normalized = [
                entry
                for entry in history
                if isinstance(
                    entry,
                    dict
                )
            ]

            print(
                "Valid history entries:",
                len(normalized)
            )

            if normalized:

                print(
                    "First entry:",
                    normalized[0]
                )

            return normalized

        print(
            "ERROR: Unsupported history format."
        )

        return []

    except Exception as e:

        print(
            f"ERROR loading history: {e}"
        )

        return []


# ======================
# MIESIĄC
# ======================

def get_report_month():

    if REPORT_MONTH:

        try:

            year, month = map(
                int,
                REPORT_MONTH.split("-")
            )

            if month < 1 or month > 12:

                raise ValueError

            return year, month

        except Exception:

            print(
                "ERROR: REPORT_MONTH "
                "must be YYYY-MM"
            )

            return None

    today = date.today()

    if today.month == 1:

        return today.year - 1, 12

    return today.year, today.month - 1


def previous_month(
    year,
    month
):

    if month == 1:

        return year - 1, 12

    return year, month - 1


def month_name(
    year,
    month
):

    names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December"
    ]

    return names[month - 1]


def expected_dates(
    year,
    month
):

    days = calendar.monthrange(
        year,
        month
    )[1]

    return {
        date(
            year,
            month,
            day
        ).isoformat()
        for day in range(
            1,
            days + 1
        )
    }
# ======================
# DANE MIESIĄCA
# ======================

def get_month_entries(
    history,
    year,
    month
):

    prefix = f"{year:04d}-{month:02d}-"

    entries = [
        entry
        for entry in history
        if entry.get(
            "date",
            ""
        ).startswith(prefix)
    ]

    return sorted(
        entries,
        key=lambda x: x.get(
            "date",
            ""
        )
    )


def is_complete_month(
    history,
    year,
    month
):

    entries = get_month_entries(
        history,
        year,
        month
    )

    dates = {
        entry.get("date")
        for entry in entries
    }

    expected = expected_dates(
        year,
        month
    )

    return expected.issubset(
        dates
    )


# ======================
# FORMATOWANIE EXP
# ======================

def format_exp(value):

    sign = ""

    if value > 0:

        sign = "+"

    elif value < 0:

        sign = "-"

    value = abs(value)

    if value >= 1_000_000_000:

        return (
            f"{sign}"
            f"{value / 1_000_000_000:.3f}B"
        )

    if value >= 1_000_000:

        return (
            f"{sign}"
            f"{value / 1_000_000:.3f}M"
        )

    if value >= 1_000:

        return (
            f"{sign}"
            f"{value / 1_000:.1f}k"
        )

    return f"{sign}{value:,}"


# ======================
# ZMIANA DZIENNA
# ======================

def calculate_daily_gains(
    history
):

    entries = sorted(
        history,
        key=lambda x: x.get(
            "date",
            ""
        )
    )

    gains = {}

    previous = None

    for entry in entries:

        current_date = entry.get(
            "date"
        )

        current_exp = entry.get(
            "exp"
        )

        if (
            previous is not None
            and current_exp is not None
        ):

            previous_exp = previous.get(
                "exp"
            )

            if previous_exp is not None:

                gains[current_date] = (
                    current_exp
                    - previous_exp
                )

        previous = entry

    return gains


# ======================
# STATYSTYKI MIESIĄCA
# ======================

def calculate_stats(
    history,
    entries
):

    daily_gains = calculate_daily_gains(
        history
    )

    month_gains = []

    for entry in entries:

        day = entry.get(
            "date"
        )

        if day in daily_gains:

            month_gains.append(
                (
                    day,
                    daily_gains[day]
                )
            )

    if entries:

        first_exp = entries[0].get(
            "exp",
            0
        )

        last_exp = entries[-1].get(
            "exp",
            0
        )

        net_exp = (
            last_exp
            - first_exp
        )

    else:

        net_exp = 0

    positive_days = [
        item
        for item in month_gains
        if item[1] > 0
    ]

    best_day = (
        max(
            month_gains,
            key=lambda x: x[1]
        )
        if month_gains
        else None
    )

    worst_day = (
        min(
            month_gains,
            key=lambda x: x[1]
        )
        if month_gains
        else None
    )

    if positive_days:

        average = (
            sum(
                gain
                for _, gain in positive_days
            )
            / len(positive_days)
        )

    else:

        average = 0

    start_level = entries[0].get(
        "level",
        0
    )

    end_level = entries[-1].get(
        "level",
        0
    )

    levels_gained = (
        end_level
        - start_level
    )

    start_rank = entries[0].get(
        "rank",
        0
    )

    end_rank = entries[-1].get(
        "rank",
        0
    )

    start_achievements = entries[0].get(
        "achievement_points",
        "?"
    )

    end_achievements = entries[-1].get(
        "achievement_points",
        "?"
    )

    if (
        isinstance(
            start_achievements,
            int
        )
        and isinstance(
            end_achievements,
            int
        )
    ):

        achievement_gain = (
            end_achievements
            - start_achievements
        )

    else:

        achievement_gain = "?"

    return {
        "daily_gains": daily_gains,
        "month_gains": month_gains,
        "net_exp": net_exp,
        "positive_days": len(
            positive_days
        ),
        "total_days": len(
            entries
        ),
        "average": average,
        "best_day": best_day,
        "worst_day": worst_day,
        "start_level": start_level,
        "end_level": end_level,
        "levels_gained": levels_gained,
        "start_rank": start_rank,
        "end_rank": end_rank,
        "start_achievements":
            start_achievements,
        "end_achievements":
            end_achievements,
        "achievement_gain":
            achievement_gain
    }


# ======================
# ŚMIERCI
# ======================

def get_deaths(
    entries
):

    deaths = []

    for entry in entries:

        for death in entry.get(
            "deaths",
            []
        ):

            if not isinstance(
                death,
                dict
            ):

                continue

            death_copy = dict(
                death
            )

            death_copy["date"] = (
                entry.get("date")
            )

            deaths.append(
                death_copy
            )

    return sorted(
        deaths,
        key=lambda x: x.get(
            "time",
            ""
        )
    )


def death_line(
    death
):

    time = death.get(
        "time",
        ""
    )

    level = death.get(
        "level",
        "?"
    )

    killers = death.get(
        "killers",
        []
    )

    killer_names = []

    for killer in killers:

        if isinstance(
            killer,
            dict
        ):

            name = killer.get(
                "name",
                "unknown"
            )

            killer_names.append(
                name
            )

        else:

            killer_names.append(
                str(killer)
            )

    if killer_names:

        killer_text = ", ".join(
            killer_names
        )

    else:

        killer_text = "unknown"

    try:

        dt = datetime.fromisoformat(
            time.replace(
                "Z",
                "+00:00"
            )
        )

        time_text = dt.strftime(
            "%d.%m %H:%M"
        )

    except Exception:

        time_text = time

    return (
        f"☠️ {time_text} — "
        f"Level {level} — "
        f"{killer_text}"
    )
# ======================
# PORÓWNANIE
# ======================

def percent_change(
    current,
    previous
):

    if previous == 0:

        return None

    return (
        (current - previous)
        / abs(previous)
    ) * 100


def comparison_line(
    label,
    current,
    previous,
    formatter=None
):

    change = percent_change(
        current,
        previous
    )

    if formatter:

        current_text = formatter(
            current
        )

        previous_text = formatter(
            previous
        )

    else:

        current_text = str(current)
        previous_text = str(previous)

    if change is None:

        percent_text = "N/A"

    else:

        if change > 0:

            arrow = "▲"

        elif change < 0:

            arrow = "▼"

        else:

            arrow = "＝"

        percent_text = (
            f"{arrow} "
            f"{abs(change):.1f}%"
        )

    return (
        f"**{label}:** "
        f"{current_text} vs "
        f"{previous_text} "
        f"({percent_text})"
    )


# ======================
# PB
# ======================

def previous_best_before_month(
    history,
    year,
    month
):

    daily_gains = calculate_daily_gains(
        history
    )

    month_start = date(
        year,
        month,
        1
    )

    previous = []

    for day, gain in daily_gains.items():

        try:

            day_date = date.fromisoformat(
                day
            )

        except Exception:

            continue

        if day_date < month_start:

            previous.append(
                (
                    day,
                    gain
                )
            )

    if not previous:

        return None

    return max(
        previous,
        key=lambda x: x[1]
    )


# ======================
# DISCORD
# ======================

def send_discord(
    message
):

    if not DISCORD_WEBHOOK_URL:

        print(
            "ERROR: "
            "DISCORD_WEBHOOK_MONTHLY not set."
        )

        return False

    try:

        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={
                "content": message
            },
            timeout=30
        )

    except requests.RequestException as e:

        print(
            "Discord request error:",
            e
        )

        return False

    if response.status_code not in (
        200,
        204
    ):

        print(
            "Discord error:",
            response.status_code,
            response.text
        )

        return False

    print(
        "Monthly report sent."
    )

    return True
# ======================
# MAIN
# ======================

def main():

    print("MONTHLY BOT START")

    history = load_history()

    if not history:

        print(
            "ERROR: No history data loaded."
        )

        return

    report_month = get_report_month()

    if not report_month:

        return

    year, month = report_month

    print(
        f"Report month: {year}-{month:02d}"
    )

    entries = get_month_entries(
        history,
        year,
        month
    )

    print(
        "Month entries:",
        len(entries)
    )

    # Miesiąc musi być kompletny.
    if not is_complete_month(
        history,
        year,
        month
    ):

        print(
            "Month is not complete. "
            "Report cancelled."
        )

        return

    stats = calculate_stats(
        history,
        entries
    )

    deaths = get_deaths(
        entries
    )

    # ======================
    # PB
    # ======================

    previous_pb = previous_best_before_month(
        history,
        year,
        month
    )

    new_pb = False

    if (
        stats["best_day"]
        and previous_pb
    ):

        if (
            stats["best_day"][1]
            >
            previous_pb[1]
        ):

            new_pb = True

    # ======================
    # TOP DAYS
    # ======================

    top_days = sorted(
        stats["month_gains"],
        key=lambda x: x[1],
        reverse=True
    )[:3]

    top_lines = []

    for day, gain in top_days:

        top_lines.append(
            f"• {day}: "
            f"**{format_exp(gain)}**"
        )

    if not top_lines:

        top_lines.append(
            "No EXP data."
        )

    # ======================
    # DEATHS
    # ======================

    death_lines = []

    for death in deaths:

        death_lines.append(
            death_line(death)
        )

    if not death_lines:

        death_lines.append(
            "🕊️ No deaths."
        )

    death_text = "\n".join(
        death_lines
    )

    if len(death_text) > 1000:

        death_text = (
            death_text[:950]
            + "\n..."
        )

    # ======================
    # PORÓWNANIE
    # ======================

    comparison_text = None

    previous_year, previous_month_number = previous_month(
        year,
        month
    )

    if is_complete_month(
        history,
        previous_year,
        previous_month_number
    ):

        previous_entries = get_month_entries(
            history,
            previous_year,
            previous_month_number
        )

        previous_stats = calculate_stats(
            history,
            previous_entries
        )

        comparison_lines = [
            comparison_line(
                "EXP",
                stats["net_exp"],
                previous_stats["net_exp"],
                format_exp
            ),
            comparison_line(
                "Average",
                stats["average"],
                previous_stats["average"],
                format_exp
            ),
            (
                f"**Levels:** "
                f"{stats['levels_gained']} vs "
                f"{previous_stats['levels_gained']}"
            ),
            (
                f"**Deaths:** "
                f"{len(deaths)} vs "
                f"{len(get_deaths(previous_entries))}"
            )
        ]

        comparison_text = "\n".join(
            comparison_lines
        )

    # ======================
    # WIADOMOŚĆ
    # ======================

    message_lines = [
        (
            f"🗓️ **Monthly Report — "
            f"{month_name(year, month)} {year}**"
        ),
        "",
        (
            f"**Level:** "
            f"{stats['start_level']} → "
            f"{stats['end_level']}"
        ),
        (
            f"**EXP:** "
            f"{format_exp(stats['net_exp'])}"
        ),
        (
            f"**Active days:** "
            f"{stats['positive_days']} / "
            f"{stats['total_days']}"
        ),
        "",
        "📈 **EXP**",
        (
            f"**Net:** "
            f"{format_exp(stats['net_exp'])}"
        ),
        (
            f"**Average:** "
            f"{format_exp(stats['average'])}"
        )
    ]

    if stats["best_day"]:

        message_lines.append(
            f"**Best day:** "
            f"{format_exp(stats['best_day'][1])} "
            f"({stats['best_day'][0]})"
        )

    else:

        message_lines.append(
            "**Best day:** No data."
        )

    message_lines.extend(
        [
            "",
            "🏆 **Progress**",
            (
                f"**Levels:** "
                f"+{stats['levels_gained']}"
            ),
            (
                f"**Rank:** "
                f"{stats['start_rank']} → "
                f"{stats['end_rank']}"
            ),
            (
                f"**Achievements:** "
                f"{stats['start_achievements']} → "
                f"{stats['end_achievements']}"
            ),
            "",
            "🔥 **Records**"
        ]
    )

    message_lines.extend(
        top_lines
    )

    message_lines.extend(
        [
            "",
            f"💀 **Deaths ({len(deaths)})**",
            death_text
        ]
    )

    # ======================
    # PB
    # ======================

    if stats["best_day"]:

        pb_text = (
            f"🏆 **Best day:** "
            f"{format_exp(stats['best_day'][1])}"
        )

        if new_pb:

            pb_text += (
                " 🎉 **NEW PB!**"
            )

        message_lines.extend(
            [
                "",
                "🎯 **PB**",
                pb_text
            ]
        )

    # ======================
    # PORÓWNANIE
    # ======================

    if comparison_text:

        message_lines.extend(
            [
                "",
                (
                    f"📊 **vs "
                    f"{month_name(previous_year, previous_month_number)} "
                    f"{previous_year}**"
                ),
                comparison_text
            ]
        )

    message_lines.extend(
        [
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "Arrow Accountant • Monthly Report"
        ]
    )

    message = "\n".join(
        message_lines
    )

    print(
        "Message length:",
        len(message)
    )

    send_discord(
        message
    )

    print(
        "MONTHLY BOT END"
    )


# ======================
# START
# ======================

if __name__ == "__main__":

    main()