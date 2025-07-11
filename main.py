import time
from telegram.ext import Updater, CommandHandler
from screener import run_screener
from keep_alive import keep_alive

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

def start(update, context):
    update.message.reply_text("🚀 Forex Screener Bot is Live. Use /scan to manually scan.")

def scan(update, context):
    update.message.reply_text("🔍 Running manual scan now...\n📌 Sans D Fx Trader")
    run_screener()


def main():
    keep_alive()
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("scan", scan))
    updater.start_polling()
    
    # Auto scan every 15 mins
    while True:
        run_screener()
        time.sleep(900)

if __name__ == "__main__":
    main()
