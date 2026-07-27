import requests
from bs4 import BeautifulSoup
import os

# === KONFIGURACJA ===

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

CHAR_NAME = "Mian Stone'arrow"


# === POBIERANIE EXP Z HIGHSCORES ===

def fetch_exp():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    for page in range(10, 16):

        url = (
            "https://www.tibia.com/community/"
            f"?subtopic=highscores"
            f"&world=Premia"
            "&beprotection=-1"
            "&category=6"
            "&profession=0"
            f"&currentpage={page}"
        )

        r = requests.get(url, headers=headers)

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        rows = soup.select(
            "table.TableContent tr"
        )

        for row in rows:

            cols = row.find_all("td")

            if len(cols) < 2:
                continue

            name = cols[1].get_text(strip=True)

            if name == CHAR_NAME:

                exp = (
                    cols[-1]
                    .get_text(strip=True)
                    .replace(",", "")
                )

                return int(exp)

    return None



# === DISCORD ===

def send_to_discord(message):

    if not DISCORD_WEBHOOK_URL:
        print("Brak webhooka Discord")
        print(message)
        return

    requests.post(
        DISCORD_WEBHOOK_URL,
        json={
            "content": message
        }
    )


# === START ===

def main():

    print("Start")

    exp = fetch_exp()

    if exp is None:

        send_to_discord(
            "⚠️ Nie znaleziono postaci w highscores."
        )

    else:

        send_to_discord(
            f"📊 EXP {CHAR_NAME}: **{exp:,}**"
        )


if __name__ == "__main__":
    main()
