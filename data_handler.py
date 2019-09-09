import pandas as pd

# filepath = '/home/nate/Dropbox/data/ib_full_adj/data/'
# filename = 'GBTC_trades_3_mins.h5'

# # need to figure out why data only goes to 2018
# df = pd.read_hdf(filepath + filename)

import yfinance as yf

gbtc = yf.Ticker("GBTC")

# get historical market data
hist = gbtc.history(period="max")


# load bitfinex data
import sys

sys.path.append('../')
import bitfinex_ohlc_import.load_candle_data as ld

df = ld.load_data(candle_size='1m')

import pandas_market_calendars as mcal
ndq = mcal.get_calendar('NASDAQ')

sched = ndq.schedule(hist.index.min(), hist.index.max())

bardata = []
for i, day in sched.iterrows():
    bardata.append(df.loc[day[0]:day[1]])

bardf = pd.concat(bardata)

bitfinex_1d_bars = bardf.resample('1D').agg({'open': 'first', 
                                            'high': 'max', 
                                            'low': 'min', 
                                            'close': 'last'})

bitfinex_1d_bars.dropna(inplace=True)

hist.columns = ['GBTC_' + c for c in hist.columns]
bitfinex_1d_bars.columns = ['BTC_' + c for c in bitfinex_1d_bars.columns]

hist.index = hist.index.tz_localize('UTC')

full_df = bitfinex_1d_bars.merge(hist, left_index=True, right_index=True)

# todo: scrape this dynamically from here: https://grayscale.co/bitcoin-trust/
btc_per_share = 0.00097555
shares = 244951500
coins = btc_per_share * shares
# also get btc holdings per share from here: https://grayscale.co/bitcoin-investment-trust/#market-performance

from selenium import webdriver
driver = webdriver.Firefox()
driver.get('https://grayscale.co/bitcoin-investment-trust/#market-performance')


get_hc_data = """
// js for extracting data, from here: http://codyaray.com/2018/09/quick-tip-extract-data-from-highcharts
// market price
x_values_mkt = [];
y_values_mkt = [];
Highcharts.charts[0].series[0].data.forEach(function(d){ x_values_mkt.push(d.x); y_values_mkt.push(d.y)});

// bitcoin holdings per share
x_values_btc = [];
y_values_btc = [];
Highcharts.charts[0].series[1].data.forEach(function(d){ x_values_btc.push(d.x); y_values_btc.push(d.y)});

return [x_values_mkt, y_values_mkt, x_values_btc, y_values_btc];
"""

x_val_mkt, y_val_mkt, x_val_btc, y_val_btc = driver.execute_script(get_hc_data)

gbtc_df = pd.DataFrame(data = {'mkt_time': x_val_mkt, 'mkt_val': y_val_mkt, 'btc_time': x_val_btc, 'btc_val': y_val_btc})
# todo: double check times are the same
all(gbtc_df['mkt_time'] == gbtc_df['btc_time'])

gbtc_df['mkt_time'] = pd.to_datetime(gbtc_df['mkt_time'], unit='ms', utc=True)
gbtc_df.drop(columns='btc_time', inplace=True)
gbtc_df.set_index('mkt_time', inplace=True)
gbtc_df['premium'] = (gbtc_df['mkt_val'] - gbtc_df['btc_val']) / gbtc_df['btc_val']

import matplotlib.pyplot as plt
gbtc_df['premium'].plot()
plt.show()