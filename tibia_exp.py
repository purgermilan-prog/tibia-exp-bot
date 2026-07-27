import requests

name = "Mian Stone'arrow"

url = "https://api.tibiadata.com/v4/character/" + requests.utils.quote(name)

print(url)

r = requests.get(url)

print(r.status_code)
print(r.text[:1000])
