# Stock Screener

This repository is a streamlit wesbite where one can analyse and filter stocks based on custom conditions.


## Cloning and running

Here is a bunch of code to launch the streamlit app.

```
git clone git@github.com:hyperwebpages/Technical-Stock-Screener.git
cd Technical-Stock-Screener
pip install -r requirements.txt
pip install --editable .
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
    * `max_workers`: max workers for the multiprocessing
    * `retrieve_mode`: retrieve mode, see later
    * `bearer_token`: token for the Twitter API, sell later.



## Twitter API

To run the app, you will need a bearer token from the Twitter API. 
You can follow this tutorial to obtain it: https://towardsdatascience.com/how-to-access-data-from-the-twitter-api-using-tweepy-python-e2d9e4d54978.

You then need to copy it into the `config.toml` file. For now, you can use my token, but I will revoke it soon. 

> **WARNING**: this method to store token is good only for local development. If you intend to deploy the app, it is better to store the token in the environment variables and load it with python.

## Retrieve mode and force download

I implemented a few features for retrieving the data. In the code, you will find 2 variables: `retrieve_mode` and `force_download`:

* `retrieve_mode` is one of ["get", "fetch"].
    * `fetch` will only retrieve data from online, and won't save them.
    * `get` will first try to retrieve data from the disk before trying online.
* `force_download` is useful when `retrieve_mode=get`. 
If `True`, the algorithm will always fetch data from online and save it.

If you don't know what option to use, ask you these questions:

* do I want most up-to-date data every time I run the program ?
    * No. Use `retrieve_mode="get"` and `force_download=False`. In that case, data will always be updated daily (or more if I click the `Update data` button in the app.)
    * Yes. Use `retrieve_mode="fetch"` and `force_download=False`.


## Usefulness of files.

Here is a table containing the usefulness of files / folders.

| File / Folder          | Usefulness                                                                                                                         |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| .streamlit/config.toml | Configuration files for streamlit. Nothing really important.                                                                       |
| app/                   | Main files for streamlit.                                                                                                          |
| datasets/symbols.csv   | Symbols of the stocks to analyse.                                                                                                  |
| datasets/daily/        | Folder containing the daily OHLCV candlesticks and <br>financials of the stocks.                                                   |
| get_data/              | Files in charge of retrieving online data from <br>Yahoo Finance API, saving it in the folder <br>`datasets/daily/` and return it. |
| models/                | Files defining the 3 dataclasses we use: Stock, Indicator and Tweet.                                                               |
| models/indicator.py    | Define indicators, columns and conditions that need to be made.                                                                    |
| models/stock.py        | Define the stock class. Useful for storing candlesticks, symbol, <br>global score, score per indicator.                            |
| models/tweet.py        | Define the tweet and the tweet search classes.                                                                                     |
| templates/             | Template folder for the string contained in the streamlit app.                                                                     |

## How to update code

What mattters is your ability to define new conditions, new indicators or even new plot.
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

    def apply_indicator(self, ohlc: pd.DataFrame) -> pd.DataFrame:
        ohlc[self.flag_column] = ohlc["Close"]
        return ohlc
```