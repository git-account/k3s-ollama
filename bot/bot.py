import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Internal Kubernetes DNS service URL for Ollama inside the 'aibot' namespace
OLLAMA_URL = "http://ollama-service.aibot.svc.cluster.local:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

# Read the Telegram token from environment variables (injected via K8s Secret)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text

    # Payload expected by Ollama's generate API endpoint
    payload = {
        "model": MODEL_NAME,
        "prompt": user_prompt,
        "stream": False
    }

    try:
        # Send prompt to the local K3s LLM service
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        res_json = response.json()
        reply_text = res_json.get("response", "Sorry, I couldn't generate a response.")
    except Exception as e:
        reply_text = f"Error communicating with local LLM backend: {e}"

    # Send the response back to the user on Telegram
    await update.message.reply_text(reply_text)

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN environment variable is missing!")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Telegram bot wrapper started, polling for messages...")
    app.run_polling()
