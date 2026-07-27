import requests

url = "https://api.tibiadata.com/v4/highscores/Premia/experience/all"

for page in [1, 2, 12]:

    r = requests.get(
        url,
        params={"page": page}
    )

    data = r.json()

    hs = data["highscores"]

    print("PAGE REQUEST:", page)
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
