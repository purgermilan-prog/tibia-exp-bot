import requests
import os
import json


# === KONFIGURACJA ===

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

CHAR_NAME = "Mian Stone'arrow"
WORLD = "Premia"

SAVE_FILE = "exp_history.json"


# === POBIERANIE EXP Z TIBIADATA ===

def fetch_exp():

    # pobieramy pierwszą stronę, żeby wiedzieć ile ich jest
    url = (
        f"https://api.tibiadata.com/v4/highscores/"
        f"{WORLD}/experience/all/1"
    )

    r = requests.get(url, timeout=20)

    if r.status_code != 200:
        print("API ERROR:", r.text)
        return None


    data = r.json()

    hs = data["highscores"]

    total_pages = hs["highscore_page"]["total_pages"]

    print("Total pages:", total_pages)


    # szukamy po wszystkich stronach

    for page in range(1, total_pages + 1):

        print("Checking page:", page)

        url = (
            f"https://api.tibiadata.com/v4/highscores/"
            f"{WORLD}/experience/all/{page}"
        )

        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            continue


        players = (
            r.json()
            ["highscores"]
            ["highscore_list"]
        )


        for player in players:

            if player["name"].lower() == CHAR_NAME.lower():

                print("FOUND:", player)

                return player["value"]


    return None



# === HISTORIA EXP ===

def load_previous_exp():

    if not os.path.exists(SAVE_FILE):
        return None

    with open(SAVE_FILE, "r") as f:
        return json.load(f).get("exp")



def save_exp(exp):

    with open(SAVE_FILE, "w") as f:
        json.dump(
            {
                "exp": exp
            },
            f
        )



# === DISCORD ===

def send_to_discord(message):

    print(message)

    if not DISCORD_WEBHOOK_URL:
        print("Missing webhook")
        return


    requests.post(
        DISCORD_WEBHOOK_URL,
        json={
            "content": message
        },
        timeout=15
    )



# === MAIN ===

def main():

    print("BOT START")

    exp = fetch_exp()


    if exp is None:

        send_to_discord(
            f"⚠️ Nie znaleziono {CHAR_NAME}"
        )

        return


    previous = load_previous_exp()


    if previous is None:

        message = (
            f"📊 EXP {CHAR_NAME}: **{exp:,}**\n"
            f"📝 Pierwszy zapis"
        )

    else:

        gain = exp - previous

        message = (
            f"📊 EXP {CHAR_NAME}: **{exp:,}**\n"
            f"📈 Przyrost: **{gain:,}**"
        )


    send_to_discord(message)

    save_exp(exp)


    print("BOT END")



if __name__ == "__main__":
    main()
