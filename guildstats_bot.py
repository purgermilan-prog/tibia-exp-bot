import requests
from datetime import datetime
import os

URL = "https://guildstats.eu/character/Mian%20Stone%27arrow"

HTML_FILE = "guildstats_page.html"


def download_page():

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.text


if __name__ == "__main__":

    print("GUILDSTATS HTML TEST START")

    html = download_page()

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(
        f"Saved {HTML_FILE} "
        f"({len(html)} characters)"
    )

    print("END")
