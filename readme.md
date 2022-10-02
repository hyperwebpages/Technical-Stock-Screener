# Stock Screener

This repository is a streamlit wesbite where one can analyse and filter stocks based on custom conditions.


## Cloning and running

Here is a bunch of code to launch the streamlit app.

```
git clone git@github.com:hyperwebpages/Technical-Stock-Screener.git
cd Technical-Stock-Screener
pip install -r requirements.txt
pip install --editable .
```

> If you are on MacOS:
    ```
    export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
    ```

and finally
```
streamlit run app/main.py
```

## Changing configuration

You can easily change the configuration of the app:

* `.streamlit/config.toml` changes the appearance of the website in streamlit
* `config.toml` changes the parameters of the app:
    * `length_displayed_stocks`: number of visible expanders at once.
    * `length_displayed_tweets`: number of tweets displayed in a row per stock.
    * `path_to_symbols`: path to the list of symbols
    * `path_to_ohlcv`: path to the list of OHLCV data
    * `path_to_financials`: path to the list of financial data
    * `fork_mode`: fork mode. One of ["fork", "spawn"]
    * `retrieve_mode`: retrieve mode, see later



## Twitter API

To run the app, you will need a bearer token from the Twitter API. 
You can follow this tutorial to obtain it: https://towardsdatascience.com/how-to-access-data-from-the-twitter-api-using-tweepy-python-e2d9e4d54978.

## Add stock to watchlist

If you want to add a stock to the watchlist, you can simply add his symbol to the specific csv file. You just need to make sure that this symbol is the one use in the yfinance API:

* go to the yahoo finance page of your stock
* the symbol should be between parenthesis `()`.

The path to csv file of symbols is indicated in `config.toml > [data_access] > path_to_stock_symbols`.

## Add index to watchlist

If you want to add an index to the watchlist, there is 2 steps:

* add a human readable symbol in the specific csv file. The path to csv file of symbols is indicated in `config.toml > [data_access] > path_to_index_symbols`.
* add the real symbol of that index to the `INDICES_TRANSLATIONS` dictionnary located at `get_data/ohlcv_data.py`. To find the real symbol of the index:
    * go to the yahoo finance page of your index
    * the symbol should be between parenthesis `()`.



For instance, if I want to add the Russian Ruble/USD as an index:

* I add this symbol `Ruble` into the file located at `path_to_index_symbols`
* I add this line `"Ruble": "RUBUSD=X"`into the `INDICES_TRANSLATIONS` dictionnary located at `get_data/ohlcv_data.py`


## Usefulness of files.

Here is a table containing the usefulness of files / folders.

| File / Folder | Usefulness |
|---|---|
| .streamlit/config.toml | Configuration files for streamlit. Nothing really important. |
| app/ | Main files for streamlit. |
| datasets/stocks.csv | Symbols of the stocks to analyse. |
| datasets/indices.csv | Symbols of indices to analyse |
| datasets/daily/ | Folder containing the daily OHLCV candlesticks and <br>financials of the stocks. |
| docker | Folder containing 2 dockers: one running the webapp on port 8501, and one running <br>the cron job to update local data every day at 17h05 on market's close |
| get_data/ | Files in charge of retrieving online data from <br>Yahoo Finance API, saving it in the folder <br>`datasets/daily/` and return it. |
| models/ | Files defining the 3 dataclasses we use: Stock, Indicator and Tweet. |
| models/indicator.py | Define indicators, columns and conditions that need to be made. |
| models/asset.py | Define the stock and index class. Useful for storing candlesticks, symbol, <br>global score, score per indicator. |
| models/tweet.py | Define the tweet and the tweet search classes. |
| templates/ | Template folder for the string contained in the streamlit app. |
| config.toml | Config file for the webapp. |

## Create a new indicators

What mattters is your ability to define new conditions, new indicators or even new plot. 

> It is important to notice that an indicator is based on an asset. Thus you can define on indicator on an asset financial. For instance, you can whitelist stocks that have a Market Cap > $100 000 000 000

Let's say we want to define a new indicator, you need to:

1. create a new `my_dummy_indicator` class in the `indicator.py` file. This class is a dataclass, meaning you can store whatever you want
2. There are 3 types of variables:
    * variable the user can finetune. This variable can be stored simply as dataclass field.
    * the name of the dataframe column which gives the buy/sell pressure. This variable needs to be called `flag_column`. 
        If your indicator doesn't give any buy/sell pressure, you can simply omit this variable.
    * variable the user can't finetune. This variable can be stored as dataclass field, BUT its name must begin with an underscore `_`.
3. implement a class function 
    `apply_indicator(self, ohlc: pd.DataFrame) -> pd.DataFrame` 
    which applies the indicator columns and more on the given `ohlc` dataframe, and returns the modified dataframe.
4. add your indicator in the streamlit app, at the top. 


### Example

```{python}
@dataclass
class DummyIndicator(Indicator):
    period_to_finetune_by_user: int = 14

    flag_column: str = "direction"

    _period_i_finetune: int = 15

    def apply_indicator(self, stock: Union[Index, Stock]) -> pd.DataFrame:
        ohlc[self.flag_column] = ohlc["Close"]
        return ohlc
```