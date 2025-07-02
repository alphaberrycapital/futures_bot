import string
from SpredLib import Spread
import pandas as pd
import numpy as np
import time 
import math
import uuid
import requests
from pybit.unified_trading import HTTP
import datetime
import time
import random
from datetime import datetime, timedelta
from os import path

class TradingBot:
    
    def __init__(self, symbols, session, bank, update, context, chat_id):
        self.symbols = symbols
        self.session = session
        self.in_position = False
        self.bank = bank
        self.spr = None
        self.is_running = True
        self.update = update
        self.context = context
        self.CHAT_ID = chat_id
        self.checkpoints = []
        self.balances_history = []
        self.aprs = []
        self.spr_enter = []
        self.spr_exit = []
        self.open_positions_symbols = []
        self.last_checkpoint = datetime.now()
        
        self.res_dict = {symbol:(None, None) for symbol in symbols}
        

    def stop(self):
        self.is_running = False

    # для покупки/продажи спота
    def force_spot_order(self, symbol, amount, buy=True):
            response = self.session.place_order(
                category="spot",
                symbol=f"{symbol}",
                side="Buy" if buy else 'Sell',
                orderType="Market",
                marketUnit = "quoteCoin" if buy else 'baseCoin',
                qty=f"{amount}",
                timeInForce="FOK"
            )
            return response

    # для покупки/продажи фьючерса
    def force_futures_order(self, symbol, amount, short=True):
        response = self.session.place_order(
            category="linear",
            symbol=f"{symbol}",
            side="Sell" if short else "Buy",
            orderType="Market",
            qty=f"{amount}",
            isLeverage=0
        )
        return response


    def string_to_float(self, str1):
        if str1 == '':
            return 0.0
        else:
            return float(str1)


    # def bank_info(self):
    #     # тут собираем инфу по свободным средствам + токенам на балансе + открытым позициям в срочных фьючерсах
    #     # собираем информацию по позиции

    #     dict_positions = {}
    #     dict_tokens_unifyed = {}

    #     self.open_positions_symbols - открытые позиции

    #     self.symbols - поддерживаемые токены в которых хотим торговать

    #     #Spot UNIFIED USDT
    #     amount_unified = self.session.get_wallet_balance(accountType="UNIFIED")
    #     unified_info = self.parse_answer_get_wallet_balance(amount_unified)
    #     try:
    #         amount_unified_usdt = self.string_to_float(self.get_token_balace(unified_info, "USDT"))
    #     except:
    #         amount_unified_usdt = 0.0

    #     # проверяем вообще все инструменты из доступных, не сидит ли у нас там где-то позиция
    #     for symbol in self.symbols:
    #         futures_symbols = self.get_all_futures_names(symbol)
    #         for future_symbol in futures_symbols:
    #             pos_info = self.session.get_positions(
    #                 category="linear",
    #                 symbol=future_symbol,
    #             )
    #             pos_size = self.string_to_float(pos_info['result']['list'][0]['size'])
    #             pos_coin = self.string_to_float(pos_info['result']['list'][0]['positionValue'])
    #             mark_price = self.string_to_float(pos_info['result']['list'][0]['markPrice'])
    #             if pos_size > 0:
    #                 dict_positions[symbol] = {future_symbol:(pos_size, pos_coin, mark_price)}


    #     # проверяем баланс на наличие различных токенов
    #     for symbol in self.symbols:
    #         # собираем всю полученную информацию
    #         try:
    #             amount_coin_on_unified = self.string_to_float(self.get_token_balace(unified_info, self.symbol.replace('USD','')))
    #         except:
    #             amount_coin_on_unified = 0.0
    #         if amount_coin_on_unified > 0:
    #             dict_tokens_unifyed[symbol] = amount_coin_on_unified


    #     # аггрегируем
    #     coin_cash = 0
    #     for symbol in self.symbols:


    #     (amount_coin_on_unified - pos_coin)*mark_price

 

    #     total_balance = amount_unified_usdt+pos_size+coin_cash

    #     return total_balance, unified_info, pos_size, pos_info, amount_unified_usdt, coin_cash


    # def bank_call(self):
    #     total_balance, unified_info, pos_size, pos_info, amount_unified_usdt, coin_cash = self.bank_info()
    #     self.update.message.reply_text(f"общая сумма: {total_balance}")
    #     self.update.message.reply_text(f"UNIFIED: {unified_info}")
    #     self.update.message.reply_text(f"Размер позиции во фьючах в долларах?: {pos_size}")
    #     self.update.message.reply_text(f"Общая информация о позиции: {pos_info}")
    #     self.update.message.reply_text(f"Сумма остатка в долларах на изначальном счету?: {amount_unified_usdt}")
    #     self.update.message.reply_text(f"Токены в долларах?: {coin_cash}")




    @staticmethod
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

    @staticmethod       
    def get_token_balace(info, symbol):
        for i in range(len(info)):
            if info[i]['coin'] == symbol:
                return info[i]['walletBalance']
        return "0.0"


    def calc_enter_spread(self, symbol, future_name, amount_enter):
        """принимаем количество долларов на вход 
        и выдает размер потенциальной позиции"""
        
        self.spr = Spread(symbol+"USDT", future_name, self.session, amount_enter)
        
        tokens_bought, spread, futures_usdt_position = self.spr.calculate_spread_entry(bank = amount_enter)
        amount_usd_short = np.floor(futures_usdt_position)
        return amount_usd_short, spread



    # def soft_enter_position_1k(self, acceptable_coeff=1):
    #     '''Покупаем на 1к токенов, затем продаем все незахеджированные токены'''
    #     try:
    #         amount_enter = 1000
    #         # флаг того, что мы готовы войти в позицию
    #         ready_to_enter = 0
    #         n_max = 100
    #         while ready_to_enter == 0:
    #             n_max -= 1
    #             if n_max < 0:
    #                 print('Количество попыток превышено')
    #                 self.update.message.reply_text("Не удалось войти, попробуйте в другой раз")
    #                 return
    #             # считаем сколько мы потеряем от вхождения в позицию
    #             # spread = avg_price_spot/avg_price_futures , чем больше тем хуже
    #             amount_usd_short, spread = self.calc_enter_spread(amount_enter)

    #             if acceptable_coeff >= spread:
    #                 # выходим из цикла, условия нам подходят
    #                 ready_to_enter = 1
    #                 print('Готовы войти в позицию')
    #                 print('Спред для входа = ', spread)
    #             else:
    #                 print('Текущий спред для входа = ', spread)
    #                 print('Спред нам не подходит, сканирую дальше')
    #                 time.sleep(0.1)

    #         # Покупаем спот
    #         r = self.force_spot_order(amount_enter, buy=True)
    #         if r['retMsg'] != 'OK':
    #             self.update.message.reply_text("Возникла проблема при покупке спота, отмена")
    #             return

    #         print(r)
    #         print(f"Купил спот")

    #         # short futures
    #         try:
    #             r_fut = self.force_perp_order(amount_usd_short, short=True)
    #             print(r_fut)
    #             print(f"Продал фьючерсы")
    #             self.update.message.reply_text("Вошел в позицию, все успешно")
    #         except:
    #             # есть шанс, что цена изменилась пробуем шортить на 1% меньше
    #             self.update.message.reply_text("Не удалось войти по желаемой цене, пробую уменьшить позицию")
    #             r_fut = self.force_perp_order(np.floor(amount_usd_short*0.99), short=True)
    #             if r_fut['retMsg'] != 'OK':
    #                 # если и тут не получилось, то выходим, бот сам разберется что делать со средствами
    #                 self.update.message.reply_text("Возникла проблема при short токена, отмена!")
    #                 return
    #             self.update.message.reply_text("Вошел в позицию, все успешно")
    #     except Exception as e:
    #         self.update.message.reply_text(f"Возникла ошибка при попытке войти в позицию!!!: {e}")
    #         print(e)
    #         self.error(e)


    def create_file_first_time(self):
        current_dt = datetime.now()
        if path.exists("data/file_to_send.csv") == False:
            data_dict = { 
            'datetime':[],
            'symbol':[],
            'symbol_best':[],
            'APY, %':[],
            }
            file_to_send = pd.DataFrame(data_dict)
            file_to_send.to_csv('data/file_to_send.csv', index=False)



    def report_to_chat(self, current_dt):
        # отправляем файл в чатик
        with open('data/file_to_send.csv', 'rb') as f:
            self.context.bot.send_document(self.CHAT_ID, f)



    def get_all_futures_names(self, token):
        """Возвращает список доступных фьючерсов для определенного токена"""
        res = self.session.get_tickers(
            category="linear"
        )
        data = res['result']['list']
        all_tickers = []
        for x in data:
            if token+"USDT-" in x['symbol']:
                all_tickers.append(x['symbol'])
        return all_tickers

    
    @staticmethod         
    def spread_to_apy(spread, future_name):

        # Указываем дату в формате день, месяц, год
        target_date = datetime.strptime(future_name.split('-')[1], '%d%b%y')
        # Получаем текущую дату
        current_date = datetime.now()
        
        # Вычисляем разницу между датами
        difference = target_date - current_date

        res = (spread-1)*100/(difference.days/365)

        # делим на 2 тк ноги 2 на самом деле
        return res/2


    def check_profitable_symbol(self, symbol): #OK
        '''Проверяет все инструменты по конретному тикеру, возвращает данные о самом доходном в APY с учетом комиссий
        По сути проверяем спорт/срочный фьюч на разные сроки'''
        status = False
        symbol_best = None
        apy_best = 0.0
        #собрали все фьючерсы
        list_futures = self.get_all_futures_names(symbol)


        for future_name in list_futures:
            amount_usd_short, spread = self.calc_enter_spread(symbol, future_name, 1000)
            apy = self.spread_to_apy(spread, future_name)
            print(status, future_name, apy_best, apy)
            if apy > apy_best:
                apy_best = apy
                symbol_best = future_name
                status = True
        
        return status, symbol_best, apy_best


    def check_profitable_all_symbols(self): #OK
        """Возвращает словарь в формате: ключ - токен, значение - самый доходный тикер(с учетом срока) и его доходность в APR """
        # инициализируем наш словарик
        res_dict = {}
        for symbol in self.symbols:
            res_dict[symbol] = (None, None)
            try:
                # проверяем доходности на все сроки по конкретному инструменту, возвращаем самый доходный (или никакой)
                status, symbol_best, apr_best = self.check_profitable_symbol(symbol)
                if status == True:
                    res_dict[symbol] = (symbol_best, apr_best)
            except:
                continue
        return res_dict

    def save_info_in_self(self, res_dict_new): #OK
        """Обновляем данные внутри обьекта если новые данные пришли более выгодные"""
        for symbol in self.res_dict:
            if self.res_dict[symbol] == (None, None) or ((res_dict_new[symbol][1] != None) and res_dict_new[symbol][1] > self.res_dict[symbol][1]):
                self.res_dict[symbol] = res_dict_new[symbol]


    def save_info_in_file(self, current_dt): #OK
        # сохраняем данные из self в файл
        # читаем существующий файл
        df = pd.read_csv('data/file_to_send.csv')
        data_dict = df.to_dict(orient='list')
        current_dt_str = current_dt.strftime("%Y-%m-%d %H:%M:%S")
        for symbol in self.res_dict:
            data_dict['datetime'].append(current_dt_str)
            data_dict['symbol'].append(symbol)
            data_dict['symbol_best'].append(self.res_dict[symbol][0])
            data_dict['APY, %'].append(self.res_dict[symbol][1])
        # обновляем на сервере
        df_to_send = pd.DataFrame().from_dict(data_dict)
        df_to_send.to_csv('data/file_to_send.csv', index=False)

        # очищаем переменные, тк уже сохранили информацию
        for symbol in self.res_dict:
            self.res_dict[symbol] = (None, None)
            
    @staticmethod  
    def return_max_profitable(cut_off, res_dict):
        """Возвращает лучший вариант для входа в позицию если удовлетворяет граничным условиям"""
        max_apy = 0
        symb_res = None
        symb_base = None
        for symbol in res_dict:
            if res_dict[symbol][1] > cut_off and res_dict[symbol][1] > max_apy:
                max_apy = res_dict[symbol][1]
                symb_res = res_dict[symbol][0]
                symb_base = symbol
        return symb_base, symb_res, max_apy
                

 
    
    def run(self):

        while self.is_running:
            try:
                # проверяем доходности по всем желаемым фьючерсам на все сроки
                res_dict = self.check_profitable_all_symbols()



                # если какой-либо из инструментов превышает 7% APY, тогда если есть баланс в виде 1к $, то мы должны открыть позицию (проверка)
                # symb_base, symb_res, max_apy = self.return_max_profitable(0.07, res_dict)


                # # по сути значит что условие выполнилось и нашелся вариант, открываем позицию на 1к $
                # if max_apy != 0:
                #     print('HEHEHEHHEEE', max_apy)
                    # self.soft_enter_position_1k(symb_base, symb_res):



                # записываем информацию в обьект в любом случае
                self.save_info_in_self(res_dict) 

                # тут же внутри будем записывать в файл раз в час и очищать внутренние обьекты
                current_dt = datetime.now()
                if (current_dt-self.last_checkpoint).seconds > 3600:
                    self.save_info_in_file(current_dt)


                time.sleep(10)
            except Exception as e:
                self.update.message.reply_text(f"Возникла ошибка!!!: {e}")
                print(e)
                time.sleep(3)


         

