from curses.ascii import RS
import os, csv, json
import yfinance as yf
import pandas as pd
import talib, numpy as np
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, SMAIndicator

from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def index():
    stocks = {}
    with open('datasets/symbols.csv') as f:
        for row in csv.reader(f):
            stocks[row[0]] = {'company': row[1]}
            symbol = row[0]
            for filename in os.listdir('datasets/daily'):
                if symbol == filename.split('.')[0]:
                    df = pd.read_csv('datasets/daily/{}'.format(filename))
                    stocks[symbol]['data'] = json.loads(df.to_json(orient='records'))
                   

    return render_template("index.html", stocks=stocks)

@app.route("/snapshot", methods=['POST'])
def snapshot():
    rsi_length = request.form['rsi_length']
    rsi_oversold = request.form['rsi_oversold']
    rsi_overbought = request.form['rsi_overbought']
    
    stoch_k = request.form['K_val']
    stoch_d = request.form['D_val']
    stoch_length = request.form['stoch_length']
    stoch_buy_level = request.form['stoch_buy_level']
    stoch_sell_level = request.form['stoch_sell_level']

    macd_slp = request.form['Slow_p']
    macd_fp = request.form['Fast_p']
    macd_sp = request.form['Signal_p']

    ema_fast = request.form['Fast_ep']
    ema_medium = request.form['Medium_ep']
    ema_slow = request.form['Slow_ep']
    
    cip_n1 = request.form['n1']
    cip_n2 = request.form['n2']
    cip_obl1 = request.form['obl1']
    cip_obl2 = request.form['obl2']
    cip_osl1 = request.form['osl1']
    cip_osl2 = request.form['osl2']
    cip_wts = request.form['wts']

    with open ('datasets/symbols.csv') as f:
        symbols = f.read().splitlines()
        for symbol in symbols:
            sym = symbol.split(',')[0]
            df = yf.download(sym, start="2022-01-01", end="2022-09-12")
            #print(df)
            if not df.empty:
                ##Indicators
                df['RSI'] = RSIIndicator(df['Close'], int(rsi_length)).rsi()
                df['RSIflag'] = 'neutral'
                condSold = (df['RSI'] < float(rsi_oversold))
                df['RSIflag'] = np.where(condSold, 'oversold', df['RSIflag'])
                condBought = (df['RSI'] > float(rsi_overbought))
                df['RSIflag'] = np.where(condBought, 'overbought', df['RSIflag'])
                

                df['fastk'], df['fastd'] = talib.STOCHRSI(df['Close'], int(stoch_length), int(stoch_k), int(stoch_d), 0)
                df['StochRSIflag'] = 'neutral'
                ##Stoch conditions to test for
                ### k val < 20 and crossing above d val => Buy pressure
                StochBuyCondition = (df['fastk'] < float(stoch_buy_level)) & (df['fastk'].shift(1) < df['fastd'].shift(1)) & (df['fastk'] >= df['fastd'])   
                df['StochRSIflag'] = np.where(StochBuyCondition,'Buy Pressure', df['StochRSIflag'])
            
                            
                ### k val > 80 and crossing above d val => Buy pressure
                StochSellCondition = (df['fastk'] > float(stoch_sell_level)) & (df['fastk'].shift(1) > df['fastd'].shift(1)) & (df['fastk'] <= df['fastd'])   
                df['StochRSIflag'] = np.where(StochSellCondition, 'Sell Pressure', df['StochRSIflag'])

                #macd, macdsignal, macdhist = MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
                df['macd'], df['macdsignal'], df['macdhist'] = talib.MACD(df['Close'], int(macd_fp), int(macd_slp), int(macd_sp))
                df['MACDflag'] = 'neutral'

                #200 EMA

                df['EMA_fast'] = EMAIndicator(df['Close'], int(ema_fast)).ema_indicator()    
                df['EMA_medium'] = EMAIndicator(df['Close'], int(ema_medium)).ema_indicator()    
                df['EMA_slow'] = EMAIndicator(df['Close'], int(ema_slow)).ema_indicator()    
                ##MACD Condition to test for Strong Buy
                MacdBuyCondition = (df['Close'] > df['EMA_medium']) & (df['macd'] < 0) & (df['macd'].shift(1) < df['macdsignal'].shift(1)) & (df['macd'] >= df['macdsignal'])
                df['MACDflag'] = np.where(MacdBuyCondition,'Buy Signal', df['MACDflag'])
            
                ##MACD Condition to test for Strong Sell
                MacdBuyCondition = (df['Close'] < df['EMA_medium']) & (df['macd'] > 0) & (df['macd'].shift(1) > df['macdsignal'].shift(1)) & (df['macd'] <= df['macdsignal'])
                df['MACDflag'] = np.where(MacdBuyCondition,'Sell Signal', df['MACDflag'])
            
                #Cipher b

                df['ap'] = (df['High'] + df['Low'] + df['Close'])/3
                n1 = int(cip_n1)
                n2  = int(cip_n2)
                #wma = WMAIndicator(df['close'], 20)
                esa = EMAIndicator(df['ap'], n1).ema_indicator()
                ##print(cci.__dict__)
                df['esa'] = esa
                #print(esa.__dict__)
                df['dval'] = abs(df['ap'] - df['esa'])
                df['d'] = EMAIndicator(df['dval'], n1).ema_indicator()
                 
                df['ci'] = (df['ap'] - df['esa'])/(0.015 * df['d'])
                df['tci'] = EMAIndicator(df['ci'], n2).ema_indicator()

                df['wt1'] = df['tci']
                df['wt2'] = SMAIndicator(df['wt1'], int(cip_wts)).sma_indicator()
                df['CipherFlag'] = 'neutral'

                CipherBullCond = (df['wt1'].shift(1) < df['wt2'].shift(1)) & (df['wt1'] >= df['wt2'])    
                df['CipherFlag'] = np.where(CipherBullCond,'Buy Signal', df['CipherFlag'])
                           
                CipherSellCond = (df['wt1'].shift(1) > df['wt2'].shift(1)) & (df['wt1'] <= df['wt2'])    
                df['CipherFlag'] = np.where(CipherSellCond,'Sell Signal', df['CipherFlag'])
                    
                df.to_csv('datasets/daily/{}.csv'.format(sym))
    
    stocks = {}
    with open('datasets/symbols.csv') as f:
        for row in csv.reader(f):
            stocks[row[0]] = {'company': row[1]}
            symbol = row[0]
            for filename in os.listdir('datasets/daily'):
                if symbol == filename.split('.')[0]:
                    df = pd.read_csv('datasets/daily/{}'.format(filename))
                    stocks[symbol]['data'] = json.loads(df.to_json(orient='records'))
                   
    RSIVals = {
        'rsi_length' : rsi_length,
        'rsi_overbought' : rsi_overbought,
        'rsi_oversold' : rsi_oversold
    }
    StochRSIVals = {
        'StochRSI Length' : stoch_length,
        'StochRSI K Val' : stoch_k,
        'StochRSI D Val' : stoch_d,
        'StochRSI Buy Level' : stoch_buy_level,
        'StochRSI Sell Level' : stoch_sell_level
    }

    MACDVals = {
        'MACD Slow' : macd_slp,
        'MACD Fast' : macd_fp,
        'MACD Signal' : macd_sp
    }
    EMAVals = {
        'EMA Fast' : ema_fast,
        'EMA Medium' : ema_medium,
        'EMA Slow' : ema_slow
    }
    CIPHERVals = {
       'n1' : cip_n1,
       'n2' : cip_n2,
        'obl1': cip_obl1,
        'obl2': cip_obl2,
        'osl1': cip_osl1,
        'osl2': cip_osl2,
        'wts': cip_wts
    }

    return render_template("index.html", stocks = stocks, RSIVals = RSIVals, StochRSIVals = StochRSIVals, MACDVals = MACDVals, EMAVals = EMAVals, CIPHERVals = CIPHERVals)

@app.route('/history')
def history():
    candlesticks = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_15MINUTE, "1 Jul, 2020", "12 Jul, 2020")

    processed_candlesticks = []

    for data in candlesticks:
        candlestick = { 
            "time": data[0] / 1000, 
            "open": data[1],
            "high": data[2], 
            "low": data[3], 
            "close": data[4]
        }

        processed_candlesticks.append(candlestick)

    return jsonify(processed_candlesticks)