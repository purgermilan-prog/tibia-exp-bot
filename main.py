import requests
import os
import time
from bs4 import BeautifulSoup
from urllib.parse import quote_plus


# ======================
# CONFIG
# ======================

DISCORD_WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK_URL"
)

GUILD_NAME = "General Levy of Sarmats"
WORLD = "Antica"

REQUEST_TIMEOUT = 20



# ======================
# HTTP REQUESTS
# ======================

def get_page(url):

    try:

        r = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if r.status_code == 200:

            return r.text


        print(
            f"HTTP ERROR {r.status_code}: {url}"
        )


    except Exception as e:

        print(
            "REQUEST ERROR:",
            e
        )


    return None



def api_get(url):

    for attempt in range(3):

        try:

            r = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": "TibiaGuildEXPBot/1.0"
                }
            )

            if r.status_code == 200:

                return r.json()


        except Exception as e:

            print(
                f"API error {attempt + 1}/3:",
                e
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



    try:

        members = data["guild"]["members"]


        return [
            member["name"]
            for member in members
        ]


    except Exception as e:

        print(
            "Guild parsing error:",
            e
        )


        return []
# ======================
# GUILDSTATS EXPERIENCE
# ======================

def fetch_character_exp(nick):

    encoded_nick = quote_plus(nick)


    url = (
        "https://guildstats.eu/include/character/tab.php?"
        f"nick={encoded_nick}&tab=experience"
    )


    html = get_page(url)
    print(nick, url)
    print(html[:1000])


    if not html:

        return None



    try:

        soup = BeautifulSoup(
            html,
            "html.parser"
        )


        rows = soup.find_all("tr")


        for row in rows:

            cells = row.find_all("td")


            if len(cells) < 2:

                continue


            exp_change = cells[1].get_text(
                strip=True
            )


            # Szukamy wartości EXP
            # przykłady:
            # +10,898,273
            # 0

            if (
                exp_change.startswith("+")
                or exp_change == "0"
            ):


                exp_value = (
                    exp_change
                    .replace("+", "")
                    .replace(",", "")
                    .strip()
                )


                return int(exp_value)



    except Exception as e:

        print(
            f"GuildStats parse error ({nick}):",
            e
        )


    return None



# ======================
# FETCH ALL MEMBERS EXP
# ======================

def fetch_members_exp(members):

    exp_data = {}

    detected = 0


    for nick in members:


        exp = fetch_character_exp(nick)


        if exp is not None:


            exp_data[nick] = exp

            detected += 1


            print(
                f"{nick}: +{exp:,}"
            )


        else:


            print(
                f"{nick}: NO DATA"
            )


        # mała przerwa
        time.sleep(1)



    print(
        f"EXP detected: {detected}/{len(members)}"
    )


    return exp_data, detected
# ======================
# TOP 3
# ======================

def get_top3(players):

    return sorted(
        players.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]



def format_top3(players):

    if not players:

        return "Brak danych"


    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]


    text = ""


    for i, player in enumerate(players):

        text += (
            f"{medals[i]} "
            f"{player[0]} "
            f"+{player[1]:,}\n"
        )


    return text



# ======================
# DISCORD
# ======================

def send_discord(message):

    if not DISCORD_WEBHOOK_URL:

        print(
            "Brak DISCORD_WEBHOOK_URL"
        )

        print(message)

        return



    try:

        r = requests.post(
            DISCORD_WEBHOOK_URL,
            json={
                "content": message
            },
            timeout=15
        )


        if r.status_code not in [200, 204]:

            print(
                "Discord error:",
                r.status_code
            )


    except Exception as e:

        print(
            "Discord exception:",
            e
        )



# ======================
# MAIN
# ======================

def main():

    print(
        "GENERAL LEVY GUILDSTATS BOT START"
    )


    members = fetch_guild_members()


    if not members:

        send_discord(
            "⚠️ Nie udało się pobrać członków gildii."
        )

        return



    print(
        f"Members found: {len(members)}"
    )



    exp_data, detected = fetch_members_exp(
        members
    )



    if not exp_data:

        send_discord(
            "⚠️ Nie znaleziono żadnych danych EXP."
        )

        return



    total_exp = sum(
        exp_data.values()
    )


    top3 = get_top3(
        exp_data
    )



    missing = [
        nick
        for nick in members
        if nick not in exp_data
    ]



    message = f"""
🌙 **Daily Exp Report — {GUILD_NAME} ({WORLD})**

👥 Members:
**{len(members)}**

🔎 EXP detected:
**{detected}/{len(members)}**

📦 Guild EXP today:
**+{total_exp:,}**

🏆 Today TOP 3:

{format_top3(top3)}
"""



    if missing:


        message += (
            "\n⚠️ Missing EXP data:\n"
        )


        for nick in missing:

            message += (
                f"- {nick}\n"
            )



    send_discord(
        message
    )


    print(
        "BOT END"
    )



if __name__ == "__main__":

    main()