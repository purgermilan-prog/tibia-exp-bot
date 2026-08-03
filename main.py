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
# HTTP
# ======================

def api_get(url):

    for attempt in range(1, 4):

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


            print(
                f"API error {r.status_code}, attempt {attempt}/3"
            )


        except Exception as e:

            print(
                f"API exception: {e}, attempt {attempt}/3"
            )


        time.sleep(3)


    return None



def get_page(url):

    try:

        r = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "Chrome/138 Safari/537.36"
                )
            }
        )


        print(
            f"PAGE STATUS {r.status_code}: {url}"
        )


        if r.status_code == 200:

            return r.text


        print(
            r.text[:300]
        )


    except Exception as e:

        print(
            "PAGE ERROR:",
            e
        )


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

    except Exception as e:

        print(
            "GUILD PARSE ERROR:",
            e
        )

        return []
# ======================
# GUILDSTATS EXP
# ======================

def fetch_character_exp(nick):

    encoded_nick = quote_plus(nick)


    url = (
        "https://guildstats.eu/include/character/tab.php?"
        f"nick={encoded_nick}&tab=experience"
    )


    html = get_page(url)


    print(
        "CHECK:",
        nick
    )


    if not html:

        print(
            "NO HTML:",
            nick
        )

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


            if (
                exp_change.startswith("+")
                or exp_change == "0"
            ):


                value = (
                    exp_change
                    .replace("+", "")
                    .replace(",", "")
                    .strip()
                )


                print(
                    nick,
                    "EXP:",
                    value
                )


                return int(value)



    except Exception as e:

        print(
            "GUILDSTATS PARSE ERROR:",
            nick,
            e
        )



    print(
        "EXP NOT FOUND:",
        nick
    )


    return None




# ======================
# ALL MEMBERS
# ======================

def fetch_members_exp(members):

    exp_data = {}

    detected = 0



    for nick in members:


        exp = fetch_character_exp(nick)



        if exp is not None:

            exp_data[nick] = exp

            detected += 1



        time.sleep(1)



    print(
        f"EXP DETECTED: {detected}/{len(members)}"
    )


    return exp_data, detected
# ======================
# FORMAT TOP 3
# ======================

def get_top3(data):

    return sorted(
        data.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]



def format_top3(data):

    if not data:

        return "Brak danych"


    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]


    text = ""


    for i, player in enumerate(data):

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
            "BRAK WEBHOOKA"
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


        print(
            "DISCORD STATUS:",
            r.status_code
        )


    except Exception as e:

        print(
            "DISCORD ERROR:",
            e
        )



# ======================
# MAIN
# ======================

def main():

    print(
        "=== GENERAL LEVY BOT START ==="
    )


    members = fetch_guild_members()



    if not members:

        send_discord(
            "⚠️ Nie udało się pobrać członków gildii."
        )

        return



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
        "=== BOT END ==="
    )



if __name__ == "__main__":

    main()
