#!user/bin/env python3

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)
import os
from dotenv import load_dotenv
import json
from pathlib import Path


# Global constants and config method

load_dotenv()

GETIMG_API_KEY = os.getenv("GETIMG_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

BOT_USERNAME = "@kitten_in_armour_bot"

BOT_COMMANDS = [('/start', 'Starts a conversation with the bot.'),
                ('/magic', 'Secret incantations.'),
                ('/call', 'Get yourself a worthy companion.')]

SYSTEM_PROMPT = "Kitten in armour with a medieval weapon"

URL = "https://api.getimg.ai/v1/flux-schnell/text-to-image"

PAYLOAD = {
    "prompt": SYSTEM_PROMPT,
    "width": 256,
    "height": 256,
    "seed": 42,
    "output_format": "png",
    "response_format": "url"
}

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {GETIMG_API_KEY}"
}

response = requests.post(URL, json=PAYLOAD, headers=HEADERS)


# Methods

def parse_response(response):
    if response.get("error") is None:
        image_url = response["url"]
        cost = response["cost"]



# Commands

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if update.message is not None else update.edited_message
    keyboard = [[InlineKeyboardButton("Get started", callback_data="/help")]]

    await update.message.reply_text("Aye, Warrior! Here, take a companion for your travels.\n/magic for the secret incantations",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if update.message is not None else update.edited_message
    commands_explained = [f"{command} {description}" for command, description in zip(commands, command_descriptions)]
    await update.message.reply_text(f"{"\n".join(commands_explained)}")

async def spacio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if update.message is not None else update.edited_message
    await update.message.reply_photo(image_url)


# Responses

def handle_response(text: str) -> str:
    if text in commands:
        return f"Executing command {text}"
    elif text == BOT_USERNAME:
        return "Hello! Need a cat?\nTry /spacio"
    return "Not a valid command,\nplease seek /help"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if update.message is not None else update.edited_message
    chat_type: str = message.chat.type
    text: str = message.text
    command = [word for word in text.split() if word in valid_commands or BOT_USERNAME in word]

    if command == []:
        return

    keyboard = []

    if "group" in chat_type:
        if BOT_USERNAME in text.split():
            new_text: str = text.replace(BOT_USERNAME, "").strip()
            if new_text != "":
                response: str = handle_response(new_text)
            else:
                response: str = handle_response(BOT_USERNAME)
                keyboard.append([InlineKeyboardButton("Free kitty", callback_data="/spacio")])
                
        else:
            return
    else:
        if BOT_USERNAME in text.split():
            new_text: str = text.replace(BOT_USERNAME, "").strip()
            if new_text != "":
                response: str = handle_response(new_text)
            else:
                response: str = handle_response(BOT_USERNAME)
                keyboard.append([InlineKeyboardButton("Free kitty", callback_data="/spacio")])
                
        else:
            response: str = handle_response(text)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard != [] else None

    await update.message.reply_text(response, reply_markup=reply_markup)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    callback = update.callback_query
    callback_data = update.callback_query.data

    match callback_data:
        case "/help":
            await help_command(callback, context)
        case "/spacio":
            await spacio_command(callback, context)


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error_message = update.message if update.message is not None else update.edited_message
    logger.error(f"Update {error_message} from {update.message.from_user.id} caused error {context.error}")



if __name__ == "__main__":

    logger.info("Starting bot...")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot = app.bot
    commands, command_descriptions = zip(*BOT_COMMANDS)
    commands_with_bot_name = [command + BOT_USERNAME for command in commands]
    valid_commands = list(commands) + commands_with_bot_name
    valid_commands.append(BOT_USERNAME)

    headers = { 'x-api-key' : API_KEY }
    
    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("spacio", spacio_command))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Errors
    app.add_error_handler(error)

    logger.info("Polling...")
    app.run_polling(poll_interval=1)