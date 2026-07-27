import os
import requests

CHAR_NAME = "Mian Stone'arrow"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def fetch_exp():
    url = f"https://api.tibiadata.com/v4/character/{CHAR_NAME.replace(' ', '%20')}"
    r = requests.get(url)

    # Próba sparsowania JSON
    try:
        data = r.json()
    except Exception:
        return None

    # Wariant 1 — najczęściej spotykany
    try:
        return data["character"]["character"]["experience"]
    except KeyError:
        pass

    # Wariant 2 — czasem TibiaData zwraca uproszczoną strukturę
    try:
        return data["character"]["experience"]
    except KeyError:
        pass

    # Jeśli nie znaleziono EXP w żadnym wariancie
    return None


def main():
    exp = fetch_exp()

    if exp is None:
        text = f"❌ Could not fetch EXP for **{CHAR_NAME}**."
    else:
        text = f"📊 EXP for **{CHAR_NAME}**: **{exp:,}**"

    requests.post(WEBHOOK_URL, json={"content": text})


if __name__ == "__main__":
    main()
