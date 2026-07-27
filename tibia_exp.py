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
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }


    for page in range(10, 16):

        url = (
            "https://www.tibia.com/community/"
            f"?subtopic=highscores"
            "&world=Premia"
            "&beprotection=-1"
            "&category=6"
            "&profession=0"
            f"&currentpage={page}"
        )

        print("Checking:", url)


        try:
            r = requests.get(
                url,
                headers=headers,
                timeout=20
            )

        except Exception as e:
            print("REQUEST ERROR:", e)
            continue


        print("STATUS:", r.status_code)
        print("HTML START:")
        print(r.text[:300])


        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )


        rows = soup.select(
            "table.TableContent tr"
        )


        print("ROWS FOUND:", len(rows))


        for row in rows:

            cols = row.find_all("td")


            if len(cols) < 2:
                continue


            name = cols[1].get_text(strip=True)


            print("FOUND NAME:", name)


            if name == CHAR_NAME:

                exp_text = (
                    cols[-1]
                    .get_text(strip=True)
                    .replace(",", "")
                )


                print(
                    "FOUND CHARACTER EXP:",
                    exp_text
                )


                return int(exp_text)


    return None



# === DISCORD ===

def send_to_discord(message):

    print("DISCORD MESSAGE:")
    print(message)


    if not DISCORD_WEBHOOK_URL:
        print("NO WEBHOOK SET")
        return


    try:
        requests.post(
            DISCORD_WEBHOOK_URL,
            json={
                "content": message
            },
            timeout=15
        )

    except Exception as e:
        print("DISCORD ERROR:", e)



# === MAIN ===

def main():

    print("BOT START")


    exp = fetch_exp()


    if exp is None:

        send_to_discord(
            "⚠️ Nie znaleziono postaci w highscores."
        )

    else:

        send_to_discord(
            f"📊 EXP {CHAR_NAME}: **{exp:,}**"
        )


    print("BOT END")



if __name__ == "__main__":
    main()
