# Stock Screener

This repository is a streamlit wesbite where one can analyse and filter stocks based on custom conditions.


## Cloning and running

Here is a bunch of code to launch the streamlit app.

```
git clone git@github.com:hyperwebpages/Technical-Stock-Screener.git
cd Technical-Stock-Screener
pip install -r requirements.txt
streamlit run app.py
```


## Usefulness of files.

Here is a table containing the usefulness of files / folders.

| File / Folder          | Usefulness                                                                                              |
|------------------------|---------------------------------------------------------------------------------------------------------|
| .streamlit/config.toml | Configuration files for streamlit. Nothing really important.                                            |
| datasets/symbols.csv   | Symbols of the stocks to analyse.                                                                       |
| datasets/daily/        | Folder containing the daily OHLC candlesticks of the stocks.                                            |
| templates/             | Template folder for the string contained in the streamlit app.                                          |
| app.py                 | Main file for streamlit.                                                                                |
| indicator.py           | Define indicators, columns and conditions that need to be made.                                         |
| market_data.py         | Download and save online candlesticks from Yahoo Finance API <br>into the folder `datasets/daily/`.     |
| plotting.py            | Create the beautiful figures for the streamlit app, using Plotly.                                       |
| stock.py               | Define the stock class. Useful for storing candlesticks, symbol, <br>global score, score per indicator. |

## How to update code

What mattters is your ability to define new conditions, new indicators or even new plot.
Let's say we want to define a new indicator, you need to:
    1. create a new `my_dummy_indicator` class in the `indicator.py` file. This class is a dataclass, meaning you can store whatever you want
    2. There are 3 types of variables:
        * variable the user can finetune. This variable can be stored simply as dataclass field.
        * the name of the dataframe column which gives the buy/sell pressure. This variable needs to be called `flag_column`. If your indicator doesn't give any buy/sell pressure, you can simply omit this variable.
        * variable the user can't finetune. This variable can be stored as dataclass field, BUT its name must begin with an underscore `_`.
    3. implement a class function 
    ```apply_indicator(self, ohlc: pd.DataFrame) -> pd.DataFrame``` 
    which applies the indicator columns and more on the given `ohlc` dataframe, and returns the modified dataframe.
    4. add your indicator in the streamlit app, at the top. 

TO TEST