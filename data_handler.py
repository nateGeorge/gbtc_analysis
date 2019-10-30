import pandas as pd
import yfinance as yf
import pandas_market_calendars as mcal
import sys

# TODO: package this as pypi package
sys.path.append('../')
import bitfinex_ohlc_import.load_candle_data as ld

gbtc = yf.Ticker("GBTC")

# get historical market data
hist = gbtc.history(period="max")

# load bitfinex data
df = ld.load_data(candle_size='1m')

# stonks market calendar
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