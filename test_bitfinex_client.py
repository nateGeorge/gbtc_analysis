
import pandas as pd
import bitfinex
from bitfinex.backtest import data

# old data...up to 2016 or so
btc_charts_url = 'http://api.bitcoincharts.com/v1/csv/bitfinexUSD.csv.gz'
df = pd.read_csv(btc_charts_url, names=['time', 'price', 'volume'])
df['time'] = pd.to_datetime(df['time'], unit='s')
