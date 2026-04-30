from datetime import datetime
import pytz

def get_lisbon_greeting():
    lisbon_tz = pytz.timezone('Europe/Lisbon')
    now = datetime.now(lisbon_tz)
    if now.hour < 12:
        return "Bom dia"
    elif now.hour < 20:
        return "Boa tarde"
    else:
        return "Boa noite"
