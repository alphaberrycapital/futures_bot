
import numpy as np
import pandas as pd
import time 
import math

class Spread:
    def __init__(self, spot_symbol, futures_symbol, session, bank):
        self.spot_symbol = spot_symbol
        self.futures_symbol = futures_symbol
        self.session = session
        self.bank = bank
        self.spot_fee = 0.001
        self.futures_fee = 0.00055
        self.precision_spot = 1e6 if "BTC" in spot_symbol else (1e5 if "ETH" in spot_symbol else 1e3)
        self.precision_futures = 1e3 if "BTC" in futures_symbol else (1e2 if "ETH" in futures_symbol else 10)


    def calculate_spread_entry(self, bank):
        # считаем сколько токенов купим на bank
        # print("СЧИТАЮ СПЕРД ДЛЯ ", self.spot_symbol, self.futures_symbol)
        tokens_bought, avg_price_spot = self.calculate_ntokens_and_price_spot(bank)
        # print('1!!!', tokens_bought, avg_price_spot )
        
        futures_usdt_position, avg_price_futures = self.calculate_pos_and_price_futures(tokens_bought)
        # print('2!!!', futures_usdt_position, avg_price_spot/avg_price_futures)
        return tokens_bought, avg_price_spot/avg_price_futures, futures_usdt_position
        
    def calculate_pos_and_price_futures(self, n_of_tokens):
        """Считаем сколько $ нам будет стоить выставление позиции на n_of_tokens"""
         
        futures_orderbook = self.get_futures_orderbook()
        futures_usdt_position = 0
        coin_left = n_of_tokens
         
        coin_position = n_of_tokens

        # идём по стакану
        for i in range(len(futures_orderbook)):    
            # если можем продать остатки
            if coin_left <= futures_orderbook['bid_quantity'][i]:
                futures_usdt_position += coin_left * futures_orderbook['bid_price'][i]

                # добавляем комиссию 
                futures_usdt_position = futures_usdt_position/(1-self.futures_fee)
                
                avg_price_futures = futures_usdt_position/n_of_tokens

                return futures_usdt_position, avg_price_futures

            # если надо докупать по другим заявкам
            else:
                # выкупаем уровень
                futures_usdt_position += futures_orderbook['bid_quantity'][i] * futures_orderbook['bid_price'][i]
                coin_left = coin_left - futures_orderbook['bid_quantity'][i]

        return None, None



    def calculate_ntokens_and_price_spot(self, bank):
        """Считаем сколько лотов купим на споте и среднюю цену потреченную на эти лоты"""
        spot_orderbook = self.get_spot_orderbook()
        tokens_bought = 0
        avg_price_spot = None
        # считаем сколько можем потратить отняв сразу комиссию (небольшая неточность тут, это ок, второй порядок)
        bank_left = bank 
        bank_spent = 0

        # Считаем среднюю цену на споте
        for i in range(len(spot_orderbook)):
            # Cчитаем сколько потенциально могли бы купить на данном уровне
            n_of_tokens = bank_left/spot_orderbook['ask_price'][i]

            # если токенов на уровне больше то можем останавливаться
            if n_of_tokens <= spot_orderbook['ask_quantity'][i]:
                # надо добавить количество лотов которые можем взять тут 
                n_of_tokens = math.floor(n_of_tokens*self.precision_spot)/self.precision_spot
                tokens_bought += n_of_tokens
                bank_spent += n_of_tokens * spot_orderbook['ask_price'][i]
                if tokens_bought != 0:
                    avg_price_spot = bank_spent / (tokens_bought * (1 - self.spot_fee))
                    return tokens_bought, avg_price_spot
                else:
                    # если лоты слишком дорогие (не должно случаться если не ставить bank слишком мелким!)
                    return None, None
            else:
                # если надо докупать с другой заявки то выкупаем уровень
                tokens_bought += spot_orderbook['ask_quantity'][i]
                bank_spent += spot_orderbook['ask_quantity'][i] * spot_orderbook['ask_price'][i]
                bank_left -= spot_orderbook['ask_quantity'][i] * spot_orderbook['ask_price'][i]
        return None, None
    

    def get_futures_orderbook(self):
        return self.get_orderbook(self.session, self.futures_symbol, "linear", 200)
    
    def get_spot_orderbook(self):

        return self.get_orderbook(self.session, self.spot_symbol, "spot", 50)


    @staticmethod
    def get_orderbook(session, symbol, category, limit):

        tickers = session.get_orderbook(category=category, symbol=symbol, limit=limit)

        bids = pd.Series(tickers['result']['b'])
        asks = pd.Series(tickers['result']['a'])

        bids = bids.iloc[:min(len(bids),len(asks))]
        asks = asks.iloc[:min(len(bids),len(asks))]

        tickers = pd.DataFrame({'b':bids,'a':asks})
        tickers['bid_price'],tickers['bid_quantity'] = zip(*tickers['b'])
        tickers['ask_price'],tickers['ask_quantity'] = zip(*tickers['a'])

        tickers['bid_price'] = tickers['bid_price'].astype('float64')
        tickers['ask_price'] = tickers['ask_price'].astype('float64')
        tickers['bid_quantity'] = tickers['bid_quantity'].astype('float64')
        tickers['ask_quantity'] = tickers['ask_quantity'].astype('float64')
        tickers = tickers.drop(['b','a'],axis=1)
        return tickers
    
