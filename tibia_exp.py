import requests

for page in [1, 2, 12]:

    url = (
        f"https://api.tibiadata.com/v4/highscores/"
        f"Premia/experience/all/{page}"
    )

    r = requests.get(url)

    data = r.json()

    hs = data["highscores"]

    print("URL:", url)
    print(
        "API PAGE:",
        hs["highscore_page"]["current_page"]
    )

    print(
        "FIRST:",
        hs["highscore_list"][0]["rank"],
        hs["highscore_list"][0]["name"]
    )

    print(
        "LAST:",
        hs["highscore_list"][-1]["rank"],
        hs["highscore_list"][-1]["name"]
    )

    print("---")
