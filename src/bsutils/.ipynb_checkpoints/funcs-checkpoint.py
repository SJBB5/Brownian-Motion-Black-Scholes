import requests
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
import yfinance as yf
from datetime import datetime
import matplotlib.pyplot as plt
from scipy.stats import norm

# Load the .env file
load_dotenv()

# API key
API_KEY = os.getenv("POLYGON_API_KEY")

def ticker_to_data(ticker_dict, start_date, end_date):
    """
    Calls API for inputted stock tickers and formats resulting dailty time series data
    
    Parameters
    ----------
    ticker_dcit : dictionary
        Dictionary with names of stocks as key and ticker as value.
    start_date : string
        Start of stock data
    end_date: sring
        End of stock data

    Returns
    -------
    Dictionary
        Dictionary with the tickers for stocks as key and a df of values for the value
    """
    data_dict = {}
    
    for company, ticker in ticker_dict.items():
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}?adjusted=true&sort=asc&apiKey={API_KEY}"
        response = requests.get(url)
        data = response.json()

        if "results" in data:
            df = create_df_ticker(pd.DataFrame(data["results"]))
            data_dict[ticker] = df
        else:
            print(f"No data found for {ticker}: {data}")

    return data_dict


def create_df_ticker(dfx):
    """
    Parameters
    ----------
    dfx : pd DataFrame
        Data Frame of "raw" data/results given by API 

    Returns
    -------
    pd DataFrame
        Organized df with descriptive column names and intuitive order
    """
    
    dfx['t'] = pd.to_datetime(dfx['t'], unit = 'ms')

    dfx = dfx.rename(columns = {
        'v': 'Volume',
        'vw': 'vwap',
        'o': 'Open',
        'c': 'Close',
        'h': 'High',
        'l': 'Low',
        't': 'Time',
        'n': 'Transactions'
    })[["Time", "Open", "High", "Low", "Close", "Volume", "vwap", "Transactions"]]

    return dfx


def plot_ticker(dat_dict, ticker):
    df = dat_dict[ticker]
    x = df['Time']
    high = df['High']
    low = df['Low']
    vwap = df['vwap']
        
    fig, ax = plt.subplots(figsize = (10,5))

    # left axis
    ax.plot(x, high, label='High', color='#1f77b4', linewidth=1, alpha=0.7)
    ax.plot(x, low, label='Low', color='#2ca02c', linewidth=1, alpha=0.7)
    ax.plot(x, vwap, label='VWAP', color='#d62728', linewidth=1, alpha=0.8)
    ax.set_xlabel('Date')
    ax.set_ylabel('(USD $)')
    
    # right axis (maybe vwap position ratio)
    # ax1 = ax.twinx()
    # ax1.plot(x, vwap, label = 'wvap', c = 'Red', alpha = .5)
    # ax1.set_ylabel('wvap')

    # combine legends
    # lines, labels = ax.get_legend_handles_labels()
    # lines2, labels2 = ax1.get_legend_handles_labels()
    # ax.legend(lines + lines2, labels + labels2, loc="upper left")
    
    # Formatting
    ax.set_title(f"{ticker} — High Price & vwap Over Time")
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    
    plt.show()

def blackScholes(r, S, K, T, sigma, type="C"):
    # Calculate BS option price for a call/put.
    d1 = (np.log(S/K) + (r + sigma**2/2)*T)/(sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    try:
        if type == "C":
            price = S*norm.cdf(d1, 0, 1) - K*np.exp(-r*T)*norm.cdf(d2,0,1)
        elif type == "P":
            price = K*np.exp(-r*T)*norm.cdf(-d2,0,1) - S*norm.cdf(-d1,0,1)
        return price
    except:
        print("Confirm all params above")

def build_bs_param_df(
    ticker="^SPX",
    expiration_index=5,
    r=0.04,
    opt_type="C",
    sigma=0.20,          # <--- constant volatility
):
    tk = yf.Ticker(ticker)

    # spot
    hist = tk.history(period="1d")
    if hist.empty:
        raise ValueError(f"No price history for {ticker}.")
    S = float(hist["Close"].iloc[-1])

    expirations = tk.options
    if not expirations:
        raise ValueError(f"No options data for {ticker}.")

    # pick expiration
    exp_str = expirations[expiration_index]

    from datetime import datetime
    today = datetime.now()
    T = (datetime.strptime(exp_str, "%Y-%m-%d") - today).days / 365.0
    if T <= 0:
        raise ValueError(f"Expiration {exp_str} has non-positive T={T:.6f}.")

    chain = tk.option_chain(exp_str)
    raw_df = chain.calls if opt_type == "C" else chain.puts

    df = raw_df.dropna(subset=["lastPrice", "strike"]).copy()

    params_df = pd.DataFrame({
        "S": S,
        "K": df["strike"].values,
        "T": T,
        "r": r,
        "sigma": sigma,          # <--- same sigma for all options
        "type": opt_type,
        "lastPrice": df["lastPrice"].values,
    })

    return params_df


