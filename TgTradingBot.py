import requests
import pandas as pd
import json
import numpy as np
import time
import matplotlib.pyplot as plt 
from datetime import datetime, timedelta, date
import math
import uuid
from pybit.unified_trading import HTTP
import random


from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import traceback
import threading
import logging

from SpredLib import Spread
from BotLib import TradingBot

from keys import TOKEN, CHAT_ID, api_key, api_secret, pair_symbols


global pair_symbols


# Initialize the Updater
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

global session
session = HTTP(
        testnet=False,
        api_key=api_key,
        api_secret=api_secret,
    )



global trading_bot
trading_bot = False


############################## команды и их действие в тг боте ################################################################################

# Command handler
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hello! I am your Telegram bot. Use /info")

# Message handler
def echo(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    update.message.reply_text(f"Я вас не понимаю, используйте /info для доступных комманд")

# Command handler for /start_bybit
def info(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("""
        \n /start_trading_bot - для запуска бота 
        \n /bank - сколько у нас всего $    
        \n /got_spread_history - получить исторические спреды для входа и выхода за сутки      
        \n /stop_trading_bot - для остановки бота   
        \n ----------------------------------------------------  
        \n /soft_enter_1k - войти в позицию на 1к $ (ждать удачного момента для входа, потери <= 0.3%)
        \n /close_all - закрыть все, вывести деньги в USDT (Использовать только когда остались копейки, тк закрывает всю позицию сразу!)
        """
        )
    
# Command handler for /start_bybit
def start_trading_bot(update: Update, context: CallbackContext) -> None:
    global trading_bot
    global session
    global pair_symbols
    symbol = pair_symbols
    if trading_bot:
        if trading_bot.is_running == True:
            update.message.reply_text("Бот уже запущен")
        else:
            trading_bot.is_running = True
            update.message.reply_text("Ранее бот был остановлен, перезапустил")
    else:
        trading_bot = TradingBot(symbol, session, 1000, update, context, CHAT_ID )
        update.message.reply_text("Запустил бота, режим сканирования ставки и пинга")
        bot_thread = threading.Thread(target=trading_bot.run)
        bot_thread.start()
        # создаем файл для отчетности если его еще не было
        trading_bot.create_file_first_time()
    
    
# Command handler for /stop_trading_bot
def stop_trading_bot(update: Update, context: CallbackContext) -> None:
    global trading_bot
    if trading_bot:
        trading_bot.stop()
        update.message.reply_text("Остановил бота.")
    else:
        update.message.reply_text("Бот не запущен")



def got_spread_history(update: Update, context: CallbackContext) -> None:
    global trading_bot
    if trading_bot:
        trading_bot.report_to_chat()
    else:
        update.message.reply_text("Бот не запущен")



def parse_answer_get_wallet_balance(answer):
    '''Возвращает список с информацией по каждому коину, в идеале список из 1 элемента для инверсных из 2х для спота'''
    result = []
    try:
        if answer['retMsg'] == 'OK':
            res0 = answer['result']['list']
            if len(res0) != 1:
                return 'error_3' # вернул информацию не по одному счету
            else:
                res1 = res0[0]['coin']
            # собираем информацию по всем коинам на инверсном/споттовом счете 
            for i in range(len(res1)):
                result.append({'coin': res1[i]['coin'], 'walletBalance': res1[i]['walletBalance']})
            return result
        else:
            return 'error_2' # вернулась ошибка на запрос
    except:
        return 'error_1' # ошибка в парсинге

def get_token_balace(info, symbol):
    for i in range(len(info)):
        if info[i]['coin'] == symbol:
            return info[i]['walletBalance']
    return "0.0"

# def soft_enter_1k(update: Update, context: CallbackContext) -> None:
#     global session
#     global pair_symbol
#     global trading_bot
#     if trading_bot:
#         trading_bot.is_running = False
#         trading_bot.soft_enter_position_1k(1.003)
#         trading_bot.is_running = True
#     else:
#         update.message.reply_text(f"Запустите бот для выполнения")



# Command handler for /bank
def bank(update: Update, context: CallbackContext) -> None:
    global trading_bot
    if trading_bot:
        trading_bot.bank_call()
    else:
        update.message.reply_text("Бот не запущен")
    


# def close_all(update: Update, context: CallbackContext) -> None:
#     """Close all Positions in coin  to USDT on spot wallet. If success -> True
#     symols is for trading pair like btcusd, session is for bybit session"""
#     global session
#     global pair_symbol
#     global trading_bot
#     symbol = pair_symbol

#     try:
#         ## 1. Sell Inverse Perps to base Coin

#         # get the size of short position in perps
#         pos_info = session.get_positions(category="inverse", symbol=symbol)
#         pos_size = float(pos_info['result']['list'][0]['size'])
#         if pos_size != 0.0:
#             # place an opposite order to close the position
#             r = session.place_order(
#                 category="inverse",
#                 symbol=symbol,
#                 side="Buy",
#                 orderType="Market",
#                 qty=pos_size,
#                 # timeInForce="FOK",
#             )
#             # wait till the sell is complete
#             # time.sleep(1)
#             if r['retMsg'] != 'OK':
#                 update.message.reply_text(f"Ошибка при закрытии фьючерсной позиции")
#         else: 
#             update.message.reply_text(f"Ошибка, позиция во фьючерсах не найдена")

#             ## 2. Transfer base Coins to Spot trading
#         # get balance
#         total_not_hedged, total_not_hedged_usd = trading_bot.calc_not_hedged()

#         amount_coin = str(np.floor(float(total_not_hedged) * (10 ** 6)) / (10 ** 6))
#         amount_coin = str(np.floor(float(amount_coin) * (10 ** 2)) / (10 ** 2))

#         session.place_order(
#             category="spot",
#             symbol=symbol + "T",
#             side="Sell",
#             orderType="Market",
#             qty=amount_coin,
#             timeInForce="FOK",
#         )
#         update.message.reply_text(f"Успешно перевел средства в usdt")

#     except:
#         update.message.reply_text(f"Ошибка, позиция не закрыта")
        


# Error handler
def error(update: Update, context: CallbackContext) -> None:
    # Log the error
    logger = logging.getLogger(__name__)
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # Send an error message to the chat
    traceback_str = traceback.format_exception(type(context.error), context.error, context.error.__traceback__)
    error_message = f"An error occurred:\n```\n{''.join(traceback_str)}\n```"
    context.bot.send_message(chat_id=CHAT_ID, text=error_message, parse_mode='MarkdownV2')

#################################################################################################################################

# Register command and message handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
dispatcher.add_handler(CommandHandler("start_trading_bot", start_trading_bot))  # Add the /start_trading_bot command handler
dispatcher.add_handler(CommandHandler("stop_trading_bot", stop_trading_bot))  # Add the /stop_trading_bot command handler
dispatcher.add_handler(CommandHandler("info", info))  # Add the /info command handler
dispatcher.add_handler(CommandHandler("got_spread_history", got_spread_history))


# dispatcher.add_handler(CommandHandler("bank", bank))  # Add the /bank command handler

# dispatcher.add_handler(CommandHandler("enter_1k", enter_1k))  
# dispatcher.add_handler(CommandHandler("close_all", close_all))  # Add the /close_all command handler

# dispatcher.add_handler(CommandHandler("soft_enter_1k", soft_enter_1k))




# Register error handler
dispatcher.add_error_handler(error)

# Start the bot
def main() -> None:

    while True:
        try:
            updater.start_polling(timeout=90)
            updater.idle()
        except Exception as e:
            print(datetime.now(), e)
            time.sleep(5)
            continue
    
if __name__ == '__main__':
    main()



