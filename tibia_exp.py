import os
import requests
from bs4 import BeautifulSoup

CHAR_NAME = "Mian Stone'arrow"
WORLD = "Premia"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_exp():
    for page in range(10, 16):
        url = (
            "https://www.tibia.com/community/"
            f"?subtopic=highscores&world={WORLD}&beprotection=-1&category=6&profession=0&currentpage={page}"
        )
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")

        rows = soup.select("table.TableContent tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue

            name = cols[1].get_text(strip=True)
            if name == CHAR_NAME:
                exp = cols[-1].get_text(strip=True).replace(",", "")
                return int(exp)
    return None


def main():
    exp = fetch_exp()

    if exp is None:
        text = f"❌ Character **{CHAR_NAME}** not found on highscores."
    else:
        text = f"📊 EXP for **{CHAR_NAME}** on **{WORLD}**: **{exp:,}**"

    r = requests.post(WEBHOOK_URL, json={"content": text})
    print("Discord status:", r.status_code, r.text)


if __name__ == "__main__":
    main()
