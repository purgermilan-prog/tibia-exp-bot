import requests


WORLD = "Premia"

for page in [1, 2, 3, 10, 12]:

    url = (
        f"https://api.tibiadata.com/v4/highscores/"
        f"{WORLD}/experience/all?page={page}"
    )

    r = requests.get(url)

    data = r.json()

    lista = data["highscores"]["highscore_list"]

    print("PAGE:", page)

    print(
        "FIRST:",
        lista[0]["rank"],
        lista[0]["name"]
    )

    print(
        "LAST:",
        lista[-1]["rank"],
        lista[-1]["name"]
    )

    print("----------------") 
