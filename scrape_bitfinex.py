import os

import quandl
import pandas as pd


class bitfinex_downloader(object):
    def __init__(self):
        key = os.environ.get('quandl_api')
        quandl.ApiConfig.api_key = key
        self.filepath = '/home/nate/Dropbox/data/crypto/bitfinex/daily_data.hdf'


    def download_initial_daily_data(self):
        data = quandl.get('BITFINEX/BTCUSD')
        return data


    def download_data_update(self):
        pass


    def download_save_data(self):
