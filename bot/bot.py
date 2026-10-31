import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
OLLAMA_URL = "http://ollama-service.aibot.svc.cluster.local:11434/api/chat"
MODEL_NAME = "llama3.2:3b"

# Dictionary to hold message history per chat: { chat_id: [ {"role": "user/assistant", "content": "..."}, ... ] }
user_histories = {}
MAX_HISTORY_LENGTH = 10  # Keeps the last 10 turns (5 user messages + 5 assistant replies) to save context window

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_histories[chat_id] = []
    await context.bot.send_message(
        chat_id=chat_id,
        text="Hello! I am your AI assistant powered by Ollama. Memory is enabled for our conversation. Use /clear to reset context."
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_histories[chat_id] = []
    await context.bot.send_message(chat_id=chat_id, text="Conversation context cleared!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if chat_id not in user_histories:
        user_histories[chat_id] = []

    # Append new user message to history
    user_histories[chat_id].append({"role": "user", "content": user_text})

    # Limit history size to prevent running out of context memory
    if len(user_histories[chat_id]) > MAX_HISTORY_LENGTH:
        user_histories[chat_id] = user_histories[chat_id][-MAX_HISTORY_LENGTH:]

    # Send status action
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    payload = {
        "model": MODEL_NAME,
        "messages": user_histories[chat_id],
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response_json = response.json()
        bot_reply = response_json.get("message", {}).get("content", "Sorry, I couldn't generate a response.")

        # Append assistant reply to history
        user_histories[chat_id].append({"role": "assistant", "content": bot_reply})

        await context.bot.send_message(chat_id=chat_id, text=bot_reply)
    except Exception as e:
        logging.error(f"Error querying Ollama: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Error reaching the AI backend.")

if __name__ == '__main__':
    if not TOKEN:
        raise ValueError("TELEGRAM_TOKEN environment variable not set.")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling()
