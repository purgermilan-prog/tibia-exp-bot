import os
import re
import requests
from bs4 import BeautifulSoup

# === KONFIGURACJA ===
WORLD = "Premia"
CHAR_NAME = "Mian Stone'arrow"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# TibiaData API
TIBIADATA_URL = "https://api.tibiadata.com/v4/character/{}"

# Tibia.com highscores
HIGHSCORES_URL = (
    "https://www.tibia.com/community/?subtopic=highscores"
    "&world={world}&beprotection=-1&category=6&profession=0&currentpage={page}"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StonedBot/1.0; +https://github.com/Milan)"
}


# === 1. Próba pobrania EXP z TibiaData API ===
def fetch_exp_tibiadata():
    url = TIBIADATA_URL.format(CHAR_NAME.replace(" ", "%20"))
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
    except Exception:
        return None

    # Wariant 1
    try:
        return data["character"]["character"]["experience"]
    except Exception:
        pass

    # Wariant 2
    try:
        return data["character"]["experience"]
    except Exception:
        pass

    # Wariant 3
    try:
        return data["character"]["data"]["experience"]
    except Exception:
        pass

    # Wariant 4 — fallback: szukamy w całym JSON
    try:
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
    except Exception:
        pass

    return None


# === 2. Scraper Tibia.com highscores ===
def fetch_exp_highscores(max_pages=50):
    target = CHAR_NAME.lower()

    for page in range(1, max_pages + 1):
        url = HIGHSCORES_URL.format(world=WORLD, page=page)
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
        except Exception:
            continue

        if r.status_code != 200:
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                name = cells[1].get_text(strip=True).lower()
                if name == target:
                    exp_text = cells[-1].get_text(strip=True)
                    digits = re.sub(r"[^\d]", "", exp_text)
                    if digits.isdigit():
                        return int(digits)

    return None


# === 3. Logika hybrydowa ===
def fetch_exp():
    # 1. Spróbuj TibiaData
    exp = fetch_exp_tibiadata()
    if exp is not None:
        return exp, "TibiaData API"

    # 2. Jeśli TibiaData nie działa → scraper Tibia.com
    exp = fetch_exp_highscores()
    if exp is not None:
        return exp, "Tibia.com highscores"

    # 3. Nic nie działa
    return None, None


# === 4. Main ===
def main():
    exp, source = fetch_exp()

    if exp is None:
        text = f"❌ Could not fetch EXP for **{CHAR_NAME}** from TibiaData or Tibia.com."
    else:
        text = f"📊 EXP for **{CHAR_NAME}**: **{exp:,}**\n🔍 Source: **{source}**"

    if WEBHOOK_URL:
        requests.post(WEBHOOK_URL, json={"content": text})
    else:
        print("WEBHOOK_URL not set. Message would be:")
        print(text)


if __name__ == "__main__":
    main()
