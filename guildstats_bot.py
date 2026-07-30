import cloudscraper
import requests
from datetime import datetime
import os

URL = "https://guildstats.eu/character/Mian%20Stone%27arrow"

HTML_FILE = "guildstats_page.html"


import cloudscraper

def download_page():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    }

    scraper = cloudscraper.create_scraper()

    response = scraper.get(
        URL,
        headers=headers,
        timeout=30
    )

    print("STATUS:", response.status_code)

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
