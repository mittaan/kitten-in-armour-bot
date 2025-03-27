#!user/bin/env python3

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext,
    CallbackQueryHandler
)
import os
import sqlite3
from mega import Mega
from dotenv import load_dotenv
from random import randint
from datetime import datetime


# Global constants and config method

load_dotenv("../.env", override=True)

MEGA_EMAIL = os.getenv("MEGA_EMAIL")
MEGA_PASSWORD = os.getenv("MEGA_PASSWORD")

mega = Mega()
m = mega.login(MEGA_EMAIL, MEGA_PASSWORD)

GETIMG_API_KEY = os.getenv("GETIMG_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

BOT_USERNAME = "@kitteninarmour_bot"

BOT_COMMANDS = [('/start', 'Starts a conversation with the bot.'),
                ('/magic', 'Secret incantations.'),
                ('/companion', 'Get yourself a worthy companion.')]

SYSTEM_PROMPT = "kitten in armour with a medieval weapon"

URL = "https://api.getimg.ai/v1/flux-schnell/text-to-image"

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {GETIMG_API_KEY}"
}

AVAILABLE_PARAMS = {"1": 'brown', "2": 'grey', "3": 'orange', "4": 'black', "5": 'white', "6": 'bicolor', "7": 'mackarel'}


# Methods

def set_seed(mod):
    seed = randint(1, 2147483647)

    image_name = f'kitten-{seed}.png'
    file_path = './tmp/' + image_name

    payload = {
        "prompt": f"{mod} {SYSTEM_PROMPT}",
        "width": 256,
        "height": 256,
        "seed": seed,
        "output_format": "png",
        "response_format": "url"
    }

    return seed, image_name, file_path, payload    


def fetch_image_from_database(image_name):
    db_conn = sqlite3.connect('./db/database.db')
    cur = db_conn.cursor()

    cur.execute('SELECT image_name, URL FROM IMAGES_INFO')

    query_result = cur.fetchall()
    
    db_conn.commit()
    db_conn.close()

    stored_images = {img: url for img, url in query_result}

    if image_name in stored_images.keys():
        return stored_images.get(image_name)
    return None


def get_image(cur, payload, file_path, image_name, seed, headers=HEADERS, url=URL):
    response = requests.post(url, json=payload, headers=headers).json()

    if response.get("error") is None:
        image_url = response["url"]
        cur.execute('INSERT INTO IMAGES_INFO (image_name, URL, COST, TIMESTAMP) VALUES (?, ?, ?, ?)',
                    (image_name, image_url, response.get("cost"), datetime.now()))
    else:
        return response, 'ERROR', f'Error: {response.get("error")}'

    img_data = requests.get(image_url).content
    with open(file_path, 'wb') as handler:
        handler.write(img_data)

    return response, 'INFO', f"Created image {image_name} using seed {seed}"


def upload_image(file_path, image_name):
    try:
        folder = m.find('kitten-in-armour')
        m.upload(file_path, folder[0])
    except FileNotFoundError:
        return 'ERROR', f"FileNotFoundError: file {image_name} could not be found on the system"
    return 'INFO', f"Uploaded image {image_name} to Mega"


def remove_local_image(file_path, image_name):
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except FileExistsError:
            return 'ERROR', f"FileExistsError: file {image_name} could not be removed from the system"
        return 'INFO', f"Removed image {image_name} from folder tmp successfully"


def full_api_call(payload, file_path, image_name, seed):
    db_conn = sqlite3.connect('./db/database.db')
    cur = db_conn.cursor()

    response, level, message = get_image(cur, payload, file_path, image_name, seed)
    cur.execute('INSERT INTO LOGS VALUES (?, ?, ?, ?)',
                (datetime.now(), level, message, str(response)))
    
    image_url = response.get("url")

    level, message = upload_image(file_path, image_name)
    cur.execute('INSERT INTO LOGS VALUES (?, ?, ?, NULL)',
                (datetime.now(), level, message))
    remove_local_image(file_path, image_name)
    cur.execute('INSERT INTO LOGS VALUES (?, ?, ?, NULL)',
                (datetime.now(), level, message))
    
    db_conn.commit()
    db_conn.close()

    return image_url


# Commands

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if update.message is not None else update.edited_message
    keyboard = [[InlineKeyboardButton("Get started", callback_data="/magic")]]

    await message.reply_text("Aye, Warrior! Here, take a companion for your travels.\n/magic for the secret incantations",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def magic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if update.message is not None else update.edited_message
    commands_explained = [f"{command} {description}" for command, description in zip(commands, command_descriptions)]
    await message.reply_text('\n'.join(commands_explained))

async def companion_command(update: Update, context: CallbackContext):
    message = update.message if update.message is not None else update.edited_message
    param = "".join(context.args).strip()
    mod = ""

    if param in AVAILABLE_PARAMS:
        mod = param
    
    seed, image_name, file_path, payload = set_seed(mod)
    image_url = fetch_image_from_database(image_name)
    if image_url is None:
        image_url = full_api_call(payload, file_path, image_name, seed)
    await message.reply_photo(image_url)

async def debug_command(update: Update, context: CallbackContext):
    message = update.message if update.message is not None else update.edited_message
    param = "".join(context.args).strip()
    mod = ""

    if param in AVAILABLE_PARAMS:
        mod = param
    
    seed, image_name, file_path, payload = set_seed(mod)

    await message.reply_text('DEBUG: - ' + payload)

# Responses

def handle_response(text: str) -> str:
    if text in commands:
        return f"Executing command {text}"
    elif text == BOT_USERNAME:
        return "Oi, you! It's dangerous to go alone,\nbring a /companion"
    return "Never heard of this incantation,\ncheck the available /magic"


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
                keyboard.append([InlineKeyboardButton("Call a buddy", callback_data="/companion")])
                
        else:
            return
    else:
        if BOT_USERNAME in text.split():
            new_text: str = text.replace(BOT_USERNAME, "").strip()
            if new_text != "":
                response: str = handle_response(new_text)
            else:
                response: str = handle_response(BOT_USERNAME)
                keyboard.append([InlineKeyboardButton("Call a buddy", callback_data="/companion")])
                
        else:
            response: str = handle_response(text)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard != [] else None

    await update.message.reply_text(response, reply_markup=reply_markup)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    callback = update.callback_query
    callback_data = update.callback_query.data

    match callback_data:
        case "/magic":
            await magic_command(callback, context)
        case "/companion":
            await companion_command(callback, context)


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):    
    db_conn = sqlite3.connect('./db/database.db')
    cur = db_conn.cursor()
    
    error_message = update.message if update.message is not None else update.edited_message

    message = f"Update {error_message} from user caused error {context.error}"

    cur.execute('INSERT INTO LOGS VALUES (?, ?, ?, NULL)',
                (datetime.now(), 'ERROR', message))
    db_conn.commit()
    db_conn.close()



if __name__ == "__main__":

    print("Starting bot...")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot = app.bot
    commands, command_descriptions = zip(*BOT_COMMANDS)
    commands_with_bot_name = [command + BOT_USERNAME for command in commands]
    valid_commands = list(commands) + commands_with_bot_name
    valid_commands.append(BOT_USERNAME)

    headers = { 'x-api-key' : GETIMG_API_KEY }
    
    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("magic", magic_command))
    app.add_handler(CommandHandler("companion", companion_command))
    app.add_handler(CommandHandler("debug", debug_command))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Errors
    app.add_error_handler(error)

    print("Polling...")
    app.run_polling(poll_interval=1)