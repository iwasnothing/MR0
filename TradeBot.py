import alpaca_trade_api as tradeapi
import requests
import ssl
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import os
import time
import joblib
import statistics

class TradeBot:
    def __init__(self,ticker1='ZM',ticker2='LBTYK',lookback=21,beta=1,res=0,API_KEY=None,API_SECRET=None):
        requests.packages.urllib3.disable_warnings()
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            # Legacy Python that doesn't verify HTTPS certificates by default
            pass
        else:
            # Handle target environment that doesn't support HTTPS verification
            ssl._create_default_https_context = _create_unverified_https_context
        self.ticker1 = ticker1
        self.ticker2 = ticker2
        self.lookback = lookback
        self.beta = beta
        self.res = res
        self.API_KEY = API_KEY
        self.API_SECRET = API_SECRET
        self.APCA_API_BASE_URL = "https://paper-api.alpaca.markets"
        self.api = tradeapi.REST(self.API_KEY, self.API_SECRET, self.APCA_API_BASE_URL, 'v2')

    def momentum(self,df):
        n = len(df)
        ma_short = df.iloc[int(n/2):n].values
        ma_long = df.iloc[1:n].values
        return sum(ma_short/len(ma_short)) - sum(ma_long/len(ma_long))


    def trading_signal(self):
        hist1 = self.load_data(self.ticker1, self.lookback)
        hist2 = self.load_data(self.ticker2, self.lookback)
        hist1['PctChg'] = hist1['Close'].pct_change()
        hist2['PctChg'] = hist2['Close'].pct_change()
        print(hist1)
        print(hist2)
        df = hist1.merge(hist2,on='Time',suffixes=['_'+self.ticker1, '_'+self.ticker2]).dropna()
        print(df)
        if len(hist1) < 2 or len(hist2) < 2 or len(df) < 2:
            return (0,0)
        cols = ['PctChg_'+self.ticker1,'PctChg_'+self.ticker2]
        print(cols)
        df['Diff'] = df[cols].apply(lambda x: x[cols[0]] - self.beta * x[cols[1]], axis=1)

        mm1 = self.momentum(df[cols[0]])
        mm2 = self.momentum(df[cols[1]])
        print(mm1,mm2)
        currentprice = [0,0]
        lasttrade = self.api.get_last_trade(self.ticker1)
        currentprice[0] = lasttrade.price

        lasttrade = self.api.get_last_trade(self.ticker2)
        currentprice[1] = lasttrade.price
        lastp1 = df.iloc[-1]['Close_'+self.ticker1]
        lastp2 = df.iloc[-1]['Close_'+self.ticker2]
        print(currentprice)
        print(lastp1,lastp2)
        return1 = (currentprice[0] - lastp1)/lastp1
        return2 = (currentprice[1] - lastp2)/lastp2
        print(return1,return2)
        current_diff = return1 - self.beta * return2
        print(current_diff)
        sig = statistics.stdev(df['Diff'])
        trade1 = 0
        trade2 = 0
        if current_diff >= self.res + sig:
            if mm1 <= 0 or mm2 >= 0:
                trade1 = -1
                trade2 = 1
        elif current_diff <= self.res - sig:
            if mm1 >= 0 or mm2 <= 0:
                trade1 = 1
                trade2 = -1
        print(trade1,trade2)
        return (trade1,trade2)

    def load_data(self,ticker,period):
        

        barset = self.api.get_barset(ticker, "day", limit=period)
        bars = barset[ticker]
        df = pd.DataFrame( [ (b.c,b.t) for b in bars], columns=['Close', 'Time'] )
        return df

    def buy(self,symbol,lot=1):
        APCA_API_BASE_URL = "https://paper-api.alpaca.markets"
        api = tradeapi.REST(self.API_KEY, self.API_SECRET, APCA_API_BASE_URL, 'v2')
        last_quote = api.get_last_quote(symbol)
        symbol_price = last_quote.askprice
        print(symbol_price)
        if symbol_price == 0:
            lasttrade = self.api.get_last_trade(symbol)
            symbol_price = lasttrade.price
        print(symbol_price)
        toBuy = True
        portfolio = api.list_positions()

        # Print the quantity of shares for each position.
        for position in portfolio:
            if position.symbol == symbol:
                toBuy = False
                print("current position is {}".format(position.qty))
        if toBuy == True:
            spread = 0.3
            print(symbol_price * (1 - spread),symbol_price * (1 - spread) * 0.95,symbol_price * (1 + spread))
            api.submit_order(
                symbol=symbol,
                qty=lot,
                side='buy',
                type='market',
                time_in_force='gtc',
                order_class='bracket',
                stop_loss={'stop_price': symbol_price * (1 - spread),
                           'limit_price': symbol_price * (1 - spread) * 0.95},
                take_profit={'limit_price': symbol_price * (1 + spread)}
            )
    
    def sell(self,symbol,lot=1):
        APCA_API_BASE_URL = "https://paper-api.alpaca.markets"
        api = tradeapi.REST(self.API_KEY, self.API_SECRET, APCA_API_BASE_URL, 'v2')
        last_quote = api.get_last_quote(symbol)
        symbol_price = last_quote.askprice
        
        toSell = False
        portfolio = api.list_positions()

        # Print the quantity of shares for each position.
        for position in portfolio:
            current_lot = int(position.qty)
            if position.symbol == symbol and  current_lot > 0 and current_lot >= lot:
                toSell = True
                print("current position is {}".format(position.qty))
                print("current position is {}".format(current_lot))
                print("selling position is {}".format(lot))
                api.submit_order(
                    symbol=symbol,
                    qty=lot,
                    side='sell',
                    type='market',
                    time_in_force='gtc'
                )

