import os
import yfinance as yf
import pandas as pd
import talib, numpy as np

from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def index():

    return render_template("index.html")

@app.route("/snapshot")
def snapshot():
    with open ('datasets/symbols.csv') as f:
        symbols = f.read().splitlines()
        for symbol in symbols:
            sym = symbol.split(',')[0]
            df = yf.download(sym, start="2022-01-01", end="2022-09-12")
            #print(df)
            if not df.empty:
                ##Indicators
                df['RSI14'] = talib.RSI(df['Close'])
                df['slowk'], df['slowd'] = talib.STOCH(df['High'], df['Low'], df['Close'])
                #macd, macdsignal, macdhist = MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
                df['macd'], df['macdsignal'], df['macdhist'] = talib.MACD(df['Close'])

                ##Cipher_B_Free
                df['n1'] = 10 #Channel length
                df['n2'] = 21 #Average length
                df['obLevel1'] = 60 #Over bought level 1
                df['obLevel2'] = 53 #Over bought level 2
                df['sLevel1'] = -60 #Over sold level 1
                df['osLevel2'] = -53 #Over sold level 2

                df['ap'] = (df['High'] + df['Low'] + df['Close'])/3
                n1 = 10
                df['esa'] = talib.EMA(df['ap'], n1)
                df['d'] = talib.EMA(abs(df['ap'] - df['esa']), n1)
                df['ci'] = (df['ap'] - df['esa'])/(0.015 * df['d'])
                n2 = 21
                df['tci'] = talib.EMA(df['ci'], n2) 

                df['wt1'] = df['tci']
                df['wt2'] = talib.SMA(df['wt1'],4)
                df['wt1 - wt2'] = df['wt1'] - df['wt2']
                
                ##Crossing wt1 with wt2
                df['wt1 & wt2 crossing'] = '0'
                
                if df['wt1'].shift(1).notnull and df['wt2'].shift(1).notnull:
                    previous_wt1 = df['wt1'].shift(1)
                    previous_wt2 = df['wt2'].shift(1)
                    current_wt1 = df['wt1']
                    current_wt2 = df['wt2']

                    df['wt1 & wt2 crossing'] = np.where(((df['wt1'] < df['wt2']) and (previous_wt1 >= previous_wt2)) or ((df['wt1'] > df['wt2']) and (previous_wt1 <= previous_wt2)),1,0)
                    df['CrossColor'] = np.where((df['wt1 & wt2 crossing'] == '1') and (df['wt2'] > df['wt1']), 'red', 'lime' )
                    #if float(previous_wt1) < float(current_wt1):
                    #    print('yes')
                    #if (df['wt1'] < df['wt2']) and (previous_wt1 >= previous_wt2) #or ((df['wt1'] > df['wt2']) and (previous_wt1 <= previous_wt2))):
                    #    df['wt1 & wt2 crossing'] = '1'    
                    #    df['wt1/wt2 black'] = df['wt2']
                    #    if ((df['wt2'] - df['wt1']) > 0):
                    #        df['CrossColor'] = 'red'
                    #    else:
                    #        df['CrossColor'] = 'lime'

                df.to_csv('datasets/daily/{}.csv'.format(sym))

    return {
        'code':'success'
    }