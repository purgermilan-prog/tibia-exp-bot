import requests
import os
import json
import time
from datetime import datetime, timedelta

# ======================
# KONFIGURACJA
# ======================

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

CHAR_NAME = "Mian Stone'arrow"
WORLD = "Premia"

SAVE_FILE = "exp_history.json"

API_RETRIES = 3
API_TIMEOUT = 20

# ======================
# CZAS TIBII
# ======================

def tibia_datetime():

now = datetime.now()  

\# Tibia resetuje dobę o 10:00  
if now\.hour < 10:  

    now -= timedelta(days=1)  

return now

def tibia_date():

return tibia\_datetime().date().isoformat()

def tibia_day_start():

now = tibia\_datetime()  

return now\.replace(  
    hour=10,  
    minute=0,  
    second=0,  
    microsecond=0  
)

# ======================
# FORMAT EXP
# ======================

def format_exp(value):

\# 1 000 EXP = 1k  
\# 1 000 000 EXP = 1000k  

if value >= 1000:  

    return f"{value/1000:,.0f}k"  

return str(value)

# ======================
# EXP TIBIA
# ======================

def exp_for_level(level):

x = level  

return int(  
    (50 / 3) \*  
    (  
        x\*\*3  
        \-  
        6\*x\*\*2  
        \+  
        17\*x  
        \-  
        12  
    )  
)

# ======================
# API
# ======================

def api_get(url):

for attempt in range(1, API\_RETRIES + 1):  

    try:  

        response = requests.get(  
            url,  
            timeout=API\_TIMEOUT,  
            headers={  
                "User-Agent":  
                "TibiaEXPBot/1.0"  
            }  
        )  


        if response.status\_code == 200:  

            return response.json()  


        print(  
            f"API error {response.status\_code}"  
        )  


    except Exception as e:  

        print(  
            f"API exception: {e}"  
        )  


    time.sleep(3)  


return None

# ======================
# CHARACTER
# ======================

def fetch_character_data():

url = (  
    "[https://api.tibiadata.com/v4/character/](https://api.tibiadata.com/v4/character/)"  
    \+  
    CHAR\_NAME.replace(" ", "%20")  
)  


data = api\_get(url)  


if not data:  

    return None  


try:  

    return data["character"]["character"]  


except Exception:  

    return None

# ======================
# HIGHSCORE (ZOPTYMALIZOWANE)
# ======================

def fetch_highscore(last_rank=None):

print("Searching highscores (smart search)...")  

\# Pobieramy pierwszą stronę, aby poznać liczbę stron  
first = api\_get(  
    f"[https://api.tibiadata.com/v4/highscores/](https://api.tibiadata.com/v4/highscores/)"  
    f"{WORLD}/experience/all/1"  
)  

if not first:  
    return None  

try:  
    pages = (  
        first["highscores"]  
        ["highscore\_page"]  
        ["total\_pages"]  
    )  

except Exception:  
    pages = 50  

target\_pages = []  

if last\_rank:  

    \# Poprawne wyliczenie strony  
    estimated\_page = max(  
        1,  
        min((last\_rank - 1) // 50 + 1, pages)  
    )  

    neighbors = [  
        estimated\_page - 2,  
        estimated\_page - 1,  
        estimated\_page,  
        estimated\_page + 1,  
        estimated\_page + 2  
    ]  

    target\_pages = []  

    for page in neighbors:  
        if 1 <= page <= pages and page not in target\_pages:  
            target\_pages.append(page)  

remaining\_pages = [  
    p  
    for p in range(1, pages + 1)  
    if p not in target\_pages  
]  

search\_order = target\_pages + remaining\_pages  

for page in search\_order:  

    data = api\_get(  
        f"[https://api.tibiadata.com/v4/highscores/](https://api.tibiadata.com/v4/highscores/)"  
        f"{WORLD}/experience/all/{page}"  
    )  

    if not data:  
        continue  

    try:  

        players = (  
            data["highscores"]  
            ["highscore\_list"]  
        )  

    except Exception:  
        continue  

    for player in players:  

        if (  
            player["name"].lower()  
            \==  
            CHAR\_NAME.lower()  
        ):  

            print(  
                f"Found {CHAR\_NAME} on page {page}"  
            )  

            return player  

return None

# ======================
# HISTORIA
# ======================

def load_history():

if not os.path.exists(SAVE\_FILE):  

    return []  


try:  

    with open(  
        SAVE\_FILE,  
        "r",  
        encoding="utf-8"  
    ) as file:  

        data = json.load(file)  


    return data.get(  
        "history",  
        []  
    )  


except Exception:  

    return []

def save_history(history):

with open(  
    SAVE\_FILE,  
    "w",  
    encoding="utf-8"  
) as file:  

    json.dump(  
        {  
            "history": history  
        },  
        file,  
        indent=2,  
        ensure\_ascii=False  
    )

def update_today(history, record):

today = record["date"]  


for item in history:  

    if item["date"] == today:  

        item.update(record)  

        return history  



history.append(record)  

return history

# ======================
# STATYSTYKI
# ======================

def daily_gain(history):

if len(history) < 2:  

    return 0  


return (  
    history[-1]["exp"]  
    \-  
    history[-2]["exp"]  
)

def gain_from_days(history, days):

if len(history) < 2:  

    return 0  


current\_day = datetime.fromisoformat(  
    tibia\_date()  
)  


limit = (  
    current\_day -  
    timedelta(days=days)  
).date()  


old = None  


for item in history:  

    item\_date = datetime.fromisoformat(  
        item["date"]  
    ).date()  


    if item\_date >= limit:  

        old = item  

        break  


if old is None:  

    return 0  


return (  
    history[-1]["exp"]  
    \-  
    old["exp"]  
)

def gain_current_month(history):

month = tibia\_date()[:7]  


data = [  
    item for item in history  
    if item["date"].startswith(month)  
]  


if len(data) < 2:  

    return 0  


return (  
    data[-1]["exp"]  
    \-  
    data[0]["exp"]  
)

def average_daily(history):

if len(history) < 2:  

    return 0  


first = datetime.fromisoformat(  
    history[0]["date"]  
)  

last = datetime.fromisoformat(  
    history[-1]["date"]  
)  


days = (  
    last - first  
).days  


if days <= 0:  

    return 0  


return (  
    history[-1]["exp"]  
    \-  
    history[0]["exp"]  
) / days

def average_month(history):

month = tibia\_date()[:7]  


data = [  
    item for item in history  
    if item["date"].startswith(month)  
]  


if len(data) < 2:  

    return 0  


first = datetime.fromisoformat(  
    data[0]["date"]  
)  

last = datetime.fromisoformat(  
    data[-1]["date"]  
)  


days = (  
    last - first  
).days  


if days <= 0:  

    return 0  


return (  
    data[-1]["exp"]  
    \-  
    data[0]["exp"]  
) / days

def biggest_daily(history):

best = 0  

best\_date = None  


for index in range(1, len(history)):  

    gain = (  
        history[index]["exp"]  
        \-  
        history[index - 1]["exp"]  
    )  


    if gain > best:  

        best = gain  

        best\_date = history[index]["date"]  


return best, best\_date

def exp_since_start(history):

if len(history) < 2:  

    return 0  


return (  
    history[-1]["exp"]  
    \-  
    history[0]["exp"]  
)

def levels_since_start(history):

if len(history) < 2:  

    return 0  


return (  
    history[-1]["level"]  
    \-  
    history[0]["level"]  
)

def bot_days(history):

if not history:  

    return 0  


start = datetime.fromisoformat(  
    history[0]["date"]  
)  


today = datetime.fromisoformat(  
    tibia\_date()  
)  


return (  
    today - start  
).days + 1

# ======================
# DISCORD
# ======================

def send_discord(message):

if not DISCORD\_WEBHOOK\_URL:  

    print(message)  

    return  


for attempt in range(3):  

    try:  

        response = requests.post(  
            DISCORD\_WEBHOOK\_URL,  
            json={  
                "content": message  
            },  
            timeout=15  
        )  


        if response.status\_code in [200, 204]:  

            return  


    except Exception as e:  

        print(  
            "Discord error:",  
            e  
        )  


    time.sleep(3)

# ======================
# MAIN
# ======================

def main():

print("BOT START")  


\# ======================  
\# WCZYTANIE HISTORII  
\# ======================  

history = load\_history()  

last\_rank = (  
    history[-1].get("rank")  
    if history  
    else None  
)  


\# ======================  
\# HIGH SCORES  
\# ======================  

highscore = fetch\_highscore(last\_rank)  

if not highscore:  

    send\_discord(  
        f"⚠️ Nie znaleziono {CHAR\_NAME}"  
    )  

    return  


\# ======================  
\# CHARACTER  
\# ======================  

character = fetch\_character\_data()  

level = highscore["level"]  
exp = highscore["value"]  
rank = highscore["rank"]  


achievements = "?"  

if character:  

    achievements = character.get(  
        "achievement\_points",  
        "?"  
    )  


\# ======================  
\# POPRZEDNI STAN  
\# ======================  

if history:  

    previous = history[-1]  

    previous\_level = previous.get(  
        "level",  
        level  
    )  

    previous\_rank = previous.get(  
        "rank",  
        rank  
    )  

    previous\_exp = previous.get(  
        "exp",  
        exp  
    )  

else:  

    previous\_level = level  
    previous\_rank = rank  
    previous\_exp = exp  


\# ======================  
\# DATA TIBIA  
\# ======================  

today = tibia\_date()  


\# ======================  
\# AKTUALIZACJA HISTORII  
\# ======================  

history = update\_today(  
    history,  
    {  
        "date": today,  
        "exp": exp,  
        "level": level,  
        "rank": rank,  
        "achievement\_points": achievements  
    }  
)  

save\_history(history)  


\# ======================  
\# STATYSTYKI  
\# ======================  

gain\_today = daily\_gain(history)  

gain\_week = gain\_from\_days(  
    history,  
    7  
)  

gain\_month = gain\_current\_month(  
    history  
)  

avg = average\_daily(  
    history  
)  

avg\_month = average\_month(  
    history  
)  

best, best\_date = biggest\_daily(  
    history  
)  


\# ======================  
\# ZMIANY LVL / RANK  
\# ======================  

level\_change = (  
    level -  
    previous\_level  
)  

\# + = awans w rankingu  
\# - = spadek w rankingu  

rank\_change = (  
    previous\_rank -  
    rank  
)  


\# ======================  
\# PROCENTY EXP  
\# ======================  

\# EXP wymagany od początku  
\# aktualnego levela  

current\_level\_start = exp\_for\_level(  
    level  
)  

\# EXP wymagany do następnego levela  

next\_level\_start = exp\_for\_level(  
    level + 1  
)  

\# Cały zakres aktualnego levela  

level\_range = (  
    next\_level\_start -  
    current\_level\_start  
)  


\# ======================  
\# % POZOSTAŁEGO LEVELA  
\# ======================  

if level\_range > 0:  

    remaining\_exp = (  
        next\_level\_start -  
        exp  
    )  

    next\_level\_percent = (  
        remaining\_exp /  
        level\_range  
    ) \* 100  

    next\_level\_percent = round(  
        max(  
            0,  
            min(  
                100,  
                next\_level\_percent  
            )  
        )  
    )  

else:  

    next\_level\_percent = 0  


\# ======================  
\# % EXP WBITEGO DZISIAJ  
\# ======================  

\# Jeżeli nie mamy poprzedniego  
\# zapisu, nie próbujemy zgadywać.  

if not history or len(history) < 2:  

    today\_percent = 0  


\# ======================  
\# NORMALNY DZIEŃ  
\# ======================  

elif level == previous\_level:  

    if level\_range > 0:  

        today\_percent = (  
            gain\_today /  
            level\_range  
        ) \* 100  

        today\_percent = round(  
            max(  
                0,  
                today\_percent  
            )  
        )  

    else:  

        today\_percent = 0  


\# ======================  
\# LEVEL UP  
\# ======================  

else:  

    \# ----------------------  
    \# STARY LEVEL  
    \# ----------------------  

    old\_level\_start = exp\_for\_level(  
        previous\_level  
    )  

    old\_level\_end = exp\_for\_level(  
        previous\_level + 1  
    )  

    old\_level\_range = (  
        old\_level\_end -  
        old\_level\_start  
    )  


    if old\_level\_range > 0:  

        \# Ile EXP brakowało  
        \# do starego levela  

        old\_remaining = (  
            old\_level\_end -  
            previous\_exp  
        )  

        old\_percent = (  
            old\_remaining /  
            old\_level\_range  
        ) \* 100  

        old\_percent = round(  
            max(  
                0,  
                min(  
                    100,  
                    old\_percent  
                )  
            )  
        )  

    else:  

        old\_percent = 0  


    \# ----------------------  
    \# NOWY LEVEL  
    \# ----------------------  

    new\_level\_start = exp\_for\_level(  
        level  
    )  

    new\_level\_end = exp\_for\_level(  
        level + 1  
    )  

    new\_level\_range = (  
        new\_level\_end -  
        new\_level\_start  
    )  


    if new\_level\_range > 0:  

        new\_exp = (  
            exp -  
            new\_level\_start  
        )  

        new\_percent = (  
            new\_exp /  
            new\_level\_range  
        ) \* 100  

        new\_percent = round(  
            max(  
                0,  
                min(  
                    100,  
                    new\_percent  
                )  
            )  
        )  

    else:  

        new\_percent = 0  


    \# Wynik np.  
    \# 25% → LVL UP → 10%  

    today\_percent = (  
        f"{old\_percent}% "  
        f"→ LVL UP → "  
        f"{new\_percent}%"  
    )  


\# ======================  
\# TEKST ZMIAN  
\# ======================  

if level\_change > 0:  

    level\_text = (  
        f"\*\*{level} (+{level\_change})\*\*"  
    )  

elif level\_change < 0:  

    level\_text = (  
        f"\*\*{level} ({level\_change})\*\*"  
    )  

else:  

    level\_text = (  
        f"\*\*{level}\*\*"  
    )  


if rank\_change > 0:  

    rank\_text = (  
        f"\*\*#{rank} (+{rank\_change})\*\*"  
    )  

elif rank\_change < 0:  

    rank\_text = (  
        f"\*\*#{rank} ({rank\_change})\*\*"  
    )  

else:  

    rank\_text = (  
        f"\*\*#{rank}\*\*"  
    )  


\# ======================  
\# DISCORD MESSAGE  
\# ======================  

message = f"""

🌙 **Daily Exp Report: {CHAR_NAME} 🏹**

⭐ Level {level_text} | 🏆 Rank {rank_text}
✨ Current Exp: **{exp:,}**

📈 Today: **+{format_exp(gain_today)} ({today_percent}%)**
📅 7 days: **+{format_exp(gain_week)}**
📆 Month: **+{format_exp(gain_month)}**
📉 Next LVL {level + 1}: **{format_exp(next_level_start - exp)} ({next_level_percent}% remaining)**

⚡ Avg day: **{format_exp(int(avg))}**
⚡ Avg month: **{format_exp(int(avg_month))}**

🚀 Total gain: **+{format_exp(exp_since_start(history))} EXP**
🆙 Levels: **+{levels_since_start(history)}**
🔥 Best: **+{format_exp(best)} ({best_date})**

🤖 Bot: **{bot_days(history)} days** 📅 Since: **{history[0]["date"]}**
🕙 Tibia reset: **{tibia_day_start().strftime("%d.%m %H:%M")}**
"""

\# ======================  
\# WYSŁANIE  
\# ======================  

send\_discord(  
    message  
)  


print("BOT END")

# ======================
# START
# ======================

if __name__ == "__main__":

main()