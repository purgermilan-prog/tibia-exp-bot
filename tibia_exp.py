import os
import re
import requests
from bs4 import BeautifulSoup

# === KONFIGURACJA ===
WORLD = "Premia"
CHAR_NAME = "Mian Stone'arrow"

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

TIBIADATA_URL = "https://api.tibiadata.com/v4/character/{}"

HIGHSCORES_URL = (
    "https://www.tibia.com/community/?subtopic=highscores"
    "&world={world}&beprotection=-1&category=6&profession=0&currentpage={page}"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# =====================================================
# TIBIADATA
# =====================================================

def fetch_exp_tibiadata():
    url = TIBIADATA_URL.format(CHAR_NAME.replace(" ", "%20"))

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)

        print("TibiaData status:", r.status_code)
        print(r.text[:500])

        data = r.json()

    except Exception as e:
        print("TibiaData error:", e)
        return None

    def find_exp(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "experience" and isinstance(v, int):
                    return v
                found = find_exp(v)
                if found:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = find_exp(item)
                if found:
                    return found
        return None

    return find_exp(data)


# =====================================================
# HIGHSCORES
# =====================================================

def fetch_exp_highscores():

    target = CHAR_NAME.lower()

    for page in range(1, 51):

        url = HIGHSCORES_URL.format(
            world=WORLD,
            page=page
        )

        print(f"Checking page {page}")

        try:
            r = requests.get(
                url,
                headers=HEADERS,
                timeout=15
            )

        except Exception as e:
            print(e)
            continue

        print("Status:", r.status_code)

        soup = BeautifulSoup(r.text, "html.parser")

        rows = soup.select("table.TableContent tr")

        for row in rows:

            cols = row.find_all("td")

            if len(cols) < 2:
                continue

            name = cols[1].get_text(strip=True).lower()

            if target == name:

                exp_text = cols[-1].get_text(strip=True)

                digits = re.sub(r"\D", "", exp_text)

                if digits.isdigit():
                    print("Found on page", page)
                    return int(digits)

    return None


# =====================================================
