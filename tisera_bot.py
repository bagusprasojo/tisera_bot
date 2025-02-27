import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Load .env file
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Halo! Saya Tisera Bot. Apa yang bisa saya bantu?")

async def echo(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    await update.message.reply_text(f"Kamu bilang: {text}")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Bot sedang berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
