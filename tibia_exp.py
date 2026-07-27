import requests
import os


# === KONFIGURACJA ===

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

CHAR_NAME = "Mian Stone'arrow"

WORLD = "Premia"


# === POBIERANIE EXP Z TIBIADATA HIGHSCORES ===

def fetch_exp():

    url = (
        f"https://api.tibiadata.com/v4/highscores/"
        f"{WORLD}/experience/all"
    )

    print("Request:", url)

    r = requests.get(
        url,
        timeout=20
    )

    print("Status:", r.status_code)

    if r.status_code != 200:
        print(r.text)
        return None


    data = r.json()


    highscores = (
        data
        .get("highscores", {})
        .get("highscore_list", [])
    )


    for player in highscores:

        if player["name"].lower() == CHAR_NAME.lower():

            print("FOUND:")
            print(player)

            return player["value"]


    return None



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
            f"⚠️ Nie znaleziono {CHAR_NAME} w highscores."
        )

    else:

        send_to_discord(
            f"📊 EXP {CHAR_NAME}: **{exp:,}**"
        )


    print("BOT END")



if __name__ == "__main__":
    main()
