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
import sqlite3
from mega import Mega
from dotenv import load_dotenv
import json
from pathlib import Path
from random import randint
from datetime import datetime


# Global constants and config method

load_dotenv()

MEGA_EMAIL = os.getenv("MEGA_EMAIL")
MEGA_PASSWORD = os.getenv("MEGA_PASSWORD")

mega = Mega()
m = mega.login(MEGA_EMAIL, MEGA_PASSWORD)

GETIMG_API_KEY = os.getenv("GETIMG_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

BOT_USERNAME = "@kitten_in_armour_bot"

BOT_COMMANDS = [('/start', 'Starts a conversation with the bot.'),
                ('/magic', 'Secret incantations.'),
                ('/companion', 'Get yourself a worthy companion.')]

SYSTEM_PROMPT = "Kitten in armour with a medieval weapon"

URL = "https://api.getimg.ai/v1/flux-schnell/text-to-image"

SEED = randint(1, 2147483647)

IMAGE_NAME = 'kitten-{SEED}.png'
FILE_PATH = './tmp/' + IMAGE_NAME


PAYLOAD = {
    "prompt": SYSTEM_PROMPT,
    "width": 256,
    "height": 256,
    "seed": SEED,
    "output_format": "png",
    "response_format": "url"
}

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {GETIMG_API_KEY}"
}


# Methods

def get_image(cur, url=URL, payload=PAYLOAD, headers=HEADERS, file_path=FILE_PATH):
    response = requests.post(url, json=payload, headers=headers).json()

    if response.get("error") is None:
        image_url = response["url"]
        cur.execute('INSERT INTO PRICE (IMAGE_NAME, URL, COST, TIMESTAMP) VALUES (?, ?, ?, ?)',
                    (IMAGE_NAME, image_url, response.get("cost"), datetime.now()))
    else:
        return response, 'ERROR', f'Error: {response.get("error")}'

    img_data = requests.get(image_url).content
    with open(FILE_PATH, 'wb') as handler:
        handler.write(img_data)

    return response, 'INFO', f"Created image {IMAGE_NAME} using seed {SEED}"

def upload_image(file_path=FILE_PATH):
    try:
        folder = m.find('kitten-in-armour')
        m.upload(file_path, folder[0])
    except FileNotFoundError:
        return 'ERROR', f"FileNotFoundError: file {IMAGE_NAME} could not be found on the system"
    return 'INFO', f"Uploaded image {IMAGE_NAME} to Mega"

def remove_local_image(file_path=FILE_PATH):
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except FileExistsError:
            return 'ERROR', f"FileExistsError: file {IMAGE_NAME} could not be removed from the system"
        return 'INFO', f"Removed image {IMAGE_NAME} from folder tmp successfully"

def full_api_call():
    db_conn = sqlite3.connect('./db/database.db')
    cur = db_conn.cursor()

    response, level, message = get_image(cur)
    cur.execute('INSERT INTO LOGS VALUES (?, ?, ?, ?)',
                (datetime.now(), level, message, str(response)))
    
    image_url = response.get("url")

    level, message = upload_image()
    cur.execute('INSERT INTO LOGS VALUES (?, ?, ?, NULL)',
                (datetime.now(), level, message))
    remove_local_image()
    cur.execute('INSERT INTO LOGS VALUES (?, ?, ?, NULL)',
                (datetime.now(), level, message))
    
    db_conn.commit()
    db_conn.close()

    return image_url


# Commands

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if update.message is not None else update.edited_message
    keyboard = [[InlineKeyboardButton("Get started", callback_data="/magic")]]

    await update.message.reply_text("Aye, Warrior! Here, take a companion for your travels.\n/magic for the secret incantations",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def magic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if update.message is not None else update.edited_message
    commands_explained = [f"{command} {description}" for command, description in zip(commands, command_descriptions)]
    await update.message.reply_text(f"{"\n".join(commands_explained)}")

async def companion_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if update.message is not None else update.edited_message
    image_url = full_api_call()
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