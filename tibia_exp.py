import os
import re
import requests
from bs4 import BeautifulSoup

WORLD = "Premia"
CHAR_NAME = "Mian Stone'arrow"

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def fetch_exp_highscores():

    target = CHAR_NAME.lower()

    for page in range(1, 51):

        print("Checking page:", page)

        url = (
            "https://www.tibia.com/community/"
            "?subtopic=highscores"
            f"&world={WORLD}"
            "&beprotection=-1"
            "&category=6"
            "&profession=0"
            f"&currentpage={page}"
        )

        r = requests.get(url, headers=HEADERS, timeout=15)

        print("Status:", r.status_code)

        soup = BeautifulSoup(r.text, "html.parser")

        rows = soup.select("table.TableContent tr")

        print("Rows found:", len(rows))

        for row in rows:

            cols = row.find_all("td")

            if len(cols) < 2:
                continue

            values = [
                c.get_text(" ", strip=True)
                for c in cols
            ]

            print(values)

            name = cols[1].get_text(strip=True).lower()

            if name == target:

                exp_text = cols[-1].get_text(strip=True)

                exp = re.sub(r"\D", "", exp_text)

                print("FOUND EXP:", exp)

                return int(exp)

    return None


def send_discord(text):

    print("Sending Discord:", text)

    if WEBHOOK_URL:
        requests.post(
            WEBHOOK_URL,
            json={"content": text}
        )
    else:
        print("NO WEBHOOK")


def main():

    print("BOT START")

    exp = fetch_exp_highscores()

    if exp is None:
        text = "❌ Nie znaleziono postaci w highscores."
    else:
        text = (
            f"📊 {CHAR_NAME}\n"
            f"EXP: **{exp:,}**"
        )

    send_discord(text)


if __name__ == "__main__":
    main()
