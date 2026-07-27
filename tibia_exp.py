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

    # Wariant 1 — najczęstszy
    try:
        return data["character"]["character"]["experience"]
    except Exception:
        pass

    # Wariant 2 — uproszczony
    try:
        return data["character"]["experience"]
    except Exception:
        pass

    # Wariant 3 — niektóre odpowiedzi TibiaData mają EXP w "data"
    try:
        return data["character"]["data"]["experience"]
    except Exception:
        pass

    # Wariant 4 — fallback: szukamy EXP w całym JSON
    try:
        # przechodzimy po wszystkich polach i szukamy klucza "experience"
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


def main():
    exp = fetch_exp()

    if exp is None:
        text = f"❌ Could not fetch EXP for **{CHAR_NAME}**."
    else:
        text = f"📊 EXP for **{CHAR_NAME}**: **{exp:,}**"

    requests.post(WEBHOOK_URL, json={"content": text})


if __name__ == "__main__":
    main()
