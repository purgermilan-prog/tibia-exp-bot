import requests
import json

url = "https://api.tibiadata.com/v4/highscores/Premia/experience/all"

r = requests.get(url)

print(r.status_code)
print(r.text[:2000])
