from decouple import config
import requests


def send_message():
    msg = (
        "<b>{datetime.datetime.today().strftime('%a, %d %b %Y %H:%M:%S')}</b>\n"
        "<b>{state}</b> по {price}\n"
        " <b>Баланс:</b>\n    <i>ETH: ,\n    BTC: </i>"
    )
    r = requests.post(
        f"https://api.telegram.org/bot{config('TELEGRAM_BOT_API_KEY', cast=str)}/sendMessage",
        json={
            "chat_id": config("TELEGRAM_BOT_CHAT_ID", cast=str),
            "parse_mode": "HTML",
            "disable_notification": True,
            "text": msg,
        },
    )
