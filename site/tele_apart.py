import telebot
from telebot import types
from back_site import search_bazos_sk, search_nehnutelnosti_sk, reset_apartmens
import json
import time

token = '7957640753:AAFZFRpeQxloxofvPPILe-8JLXa5iu6blOA'
bot = telebot.TeleBot(token)

commands = [
    telebot.types.BotCommand("start", "Start search"),
    telebot.types.BotCommand("help", "List of commands"),
    telebot.types.BotCommand("stop", "Stop search"),
    telebot.types.BotCommand("reset", "Reset search")
    ]

bot.set_my_commands(commands)

user_states = {}

user_data = {'processing': False}

WAITING_MIN_PRICE = "waiting_min_price"
WAITING_MAX_PRICE = "waiting_max_price"
WAITING_ROOMS = "waiting_rooms"
WAITING_LOCATION = "waiting_location"
CHOOSE_APARTMENT = "choose_apartment"


@bot.message_handler(commands=['start'])
def start(message):

    if message.chat.id not in user_data:
        user_data[message.chat.id] = {'processing': False}

    if user_data[message.chat.id].get("processing") is True:
        bot.send_message(message.chat.id, "Processing is going on")
        return
    
    
    user_states[message.chat.id] = CHOOSE_APARTMENT

    apartments = ["BAZOS", "NEHNUTELNOSTI"]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*apartments)
    bot.send_message(message.chat.id, "Choose site", reply_markup=keyboard)


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == CHOOSE_APARTMENT and not message.text.startswith("/"))
def choose_apartment(message):

    appartments = message.text.upper()
    if appartments not in ["BAZOS", "NEHNUTELNOSTI"]:
        bot.send_message(message.chat.id, "Choose BAZOS or NEHNUTELNOSTI")
        return

    user_data[message.chat.id] = {"apartment": appartments}
    user_states[message.chat.id] = WAITING_MIN_PRICE

    bot.send_message(message.chat.id, "Select the min price", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == WAITING_MIN_PRICE and not message.text.startswith("/"))
def waiting_price(message):

    if message.text.startswith("/"):
        user_states.pop(message.chat.id, None)
        user_data.pop(message.chat.id, None)
        return

    try:
        price = int(message.text)
        user_data[message.chat.id]["min_price"] = price
        user_states[message.chat.id] = WAITING_MAX_PRICE   
        bot.send_message(message.chat.id, "Select the max price")
    except ValueError:
        bot.send_message(message.chat.id, "Enter a number")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == WAITING_MAX_PRICE and not message.text.startswith("/"))
def waiting_max_price(message):

    try:
        price = int(message.text)
        user_data[message.chat.id]["max_price"] = price
        user_states[message.chat.id] = WAITING_ROOMS

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add("1", "2", "3", "4")

        bot.send_message(message.chat.id, "Select the number of rooms", reply_markup=keyboard)
    except ValueError:
        bot.send_message(message.chat.id, "Enter a number")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == WAITING_ROOMS and not message.text.startswith("/"))
def waiting_rooms(message):
    try:
        rooms = int(message.text)

        if rooms < 1 or rooms > 4:
            bot.send_message(message.chat.id, "Enter a number from 1 to 4")
            return

        user_data[message.chat.id]["rooms"] = rooms
        user_states[message.chat.id] = WAITING_LOCATION
        if user_data[message.chat.id]["apartment"] == "BAZOS":
            bot.send_message(message.chat.id, "Select the ZIP code", reply_markup=types.ReplyKeyboardRemove())
        else:
            bot.send_message(message.chat.id, "Select the city")
            
    except ValueError:
        bot.send_message(message.chat.id, "Enter a number")




@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == WAITING_LOCATION and not message.text.startswith("/"))
def waiting_location(message):

    location = message.text
    user_data[message.chat.id]["location"] = location.replace(" ", "")
    user_data[message.chat.id]["processing"] = True
    get_apart(message)


@bot.message_handler(func=lambda message: False)
def get_apart(message):
    wait_msg = bot.send_message(message.chat.id, "Please wait a few seconds...")

    room = user_data[message.chat.id]["rooms"]
    min_price = user_data[message.chat.id]["min_price"]
    max_price = user_data[message.chat.id]["max_price"]
    appartment = user_data[message.chat.id]["apartment"]
    location = user_data[message.chat.id]["location"]

    if appartment == "BAZOS":
        search_bazos_sk(size=room, min_price=min_price, max_price=max_price, location=location)
        with open("bazos_sk.json", encoding="utf-8") as file:
            data = json.load(file)
    
    elif appartment == "NEHNUTELNOSTI":
        search_nehnutelnosti_sk(size=room, min_price=min_price, max_price=max_price, location=location)
        with open("nehnutelnosti_sk.json", encoding="utf-8") as file:
            data = json.load(file)

    for index, item in enumerate(data):

        if message.chat.id not in user_data:
            return

        if item.get("accept") is False:
            continue

        card = f'<b>Price:</b> {item.get("price")}\n' \
            f'<b>Location:</b> {item.get("adress")}\n' \
            f'<a href="{item.get("link")}">{item.get("link")}</a>'
                
        if index%20 == 0:
            time.sleep(5)

        markup = types.InlineKeyboardMarkup()
        apt = types.InlineKeyboardButton(
            text="✅", 
            callback_data=f'{user_data[message.chat.id]["apartment"]}:{index}:accept'
        )
        rej = types.InlineKeyboardButton(
            text="❌", 
            callback_data=f'{user_data[message.chat.id]["apartment"]}:{index}:reject'
        )
        markup.row(apt, rej)

        bot.send_message(message.chat.id, card, parse_mode="HTML", reply_markup=markup)

    if len(data) == 0:
        bot.send_message(message.chat.id, "No listings found")
    else:
        bot.send_message(
            message.chat.id,
            "All listings have been sent!\nIf you want a new search, enter /start or /reset",
            reply_markup=types.ReplyKeyboardRemove()
        )

    user_data[message.chat.id]["processing"] = False
    user_states.pop(message.chat.id, None)

    bot.delete_message(message.chat.id, wait_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    data_part = call.data.split(":")

    apartment = data_part[0].lower()
    index = int(data_part[1])
    action = data_part[2]

    with open(f"{apartment}_sk.json", encoding="utf-8") as file:
        data = json.load(file)

    if action == "accept":
        data[index]["accept"] = True
        bot.answer_callback_query(
            call.id, "You accepted"
        )

    elif action == "reject":
        data[index]["accept"] = False
        bot.send_message(
            call.message.chat.id, f"You rejected {data[index].get('link')}"
        )
        bot.delete_message(call.message.chat.id, call.message.message_id)

    with open(f"{apartment}_sk.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


@bot.message_handler(commands=['stop'])
def stop(message):

    if message.chat.id not in user_data:
        user_data[message.chat.id] = {'processing': False}

    if user_data[message.chat.id].get("processing") is False:
        bot.send_message(message.chat.id, "Processing not started")
        return
    
    user_data[message.chat.id]['processing'] = False

    user_states.pop(message.chat.id, None)
    bot.send_message(message.chat.id, "Search stopped\nWrite /start to start a new search")


        
@bot.message_handler(commands=['help'])
def help(message):

    if user_data[message.chat.id].get("processing") is True:
        bot.send_message(message.chat.id, "Processing is going on")
        return
    
    bot.send_message(message.chat.id, "Write /start to start a new search\nWrite /stop to stop the search\nWrite /reset to reset the search")

@bot.message_handler(commands=['reset'])
def reset(message):

    user_states.pop(message.chat.id, None) 

    if message.chat.id not in user_data:
        user_data[message.chat.id] = {'processing': False}
    if user_data[message.chat.id].get("processing") is True:
        bot.send_message(message.chat.id, "Processing is going on")
        return
    
    reset_apartmens = ["BAZOS_RESET", "NEHNUTELNOSTI_RESET"]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(*reset_apartmens)
    bot.send_message(message.chat.id, "Choose what you want to reset", reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text.upper() in ["BAZOS_RESET", "NEHNUTELNOSTI_RESET"])
def reset_apart(message):

    user_data[message.chat.id]['processing'] = True

    reset_msg = bot.send_message(message.chat.id, "Resetting...")
    
    if reset_apartmens(message.text) is False:
        bot.send_message(message.chat.id, "Nothing to reset")
        return

    
    bot.delete_message(message.chat.id, reset_msg.message_id)
    bot.send_message(message.chat.id, "Reset done. Please use /start to begin a new search.")

    user_data[message.chat.id]['processing'] = False

    user_states.pop(message.chat.id, None)
    user_data.pop(message.chat.id, None)











        





def main():
    bot.polling()

if __name__ == '__main__':
    main()