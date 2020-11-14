import os
import sqlite3

import pytz
import pandas_market_calendars as mcal
import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
import matplotlib.pyplot as plt

import cufflinks as cf  # interactive plotting
cf.go_offline()

# annoying orca/plotly issue
import plotly
plotly.io.orca.config.executable = '/home/nate/anaconda3/envs/selenium/bin/orca'


STORAGE = 'sqlite'
DB_LOC = '~/.gbtc_data/'
DB_NAME = 'gbtc_data.db'


def load_page():
    """
    loads GBTC page and closes popup if there
    """
    driver = webdriver.Firefox()
    driver.get('https://grayscale.co/bitcoin-investment-trust/#market-performance')

    # popup box with 'The Grayscale Bitcoin Trust private placement is 
    # offered on a periodic basis throughout the year and is currently closed.'

    try:
        close_button = driver.find_element_by_class_name('close-button')
        close_button.click()
    except (NoSuchElementException, ElementNotInteractableException) as e:
        print(e)
    
    return driver


def get_gbtc_web_data(return_driver=False):
    """
    gets data from GBTC plot on their site
    """
    driver = load_page()

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

    gbtc_df = pd.DataFrame(data = {'mkt_time': x_val_mkt,
                                    'mkt_val': y_val_mkt,
                                    'btc_time': x_val_btc,
                                    'btc_val': y_val_btc})
    # double check times are the same
    if not all(gbtc_df['mkt_time'] == gbtc_df['btc_time']):
        print('WARNING: times from scraped data do not line up')

    # clean up time and add premium column
    gbtc_df['mkt_time'] = pd.to_datetime(gbtc_df['mkt_time'], unit='ms', utc=True)
    gbtc_df.drop(columns='btc_time', inplace=True)
    gbtc_df.set_index('mkt_time', inplace=True)
    gbtc_df['premium'] = (gbtc_df['mkt_val'] - gbtc_df['btc_val']) / gbtc_df['btc_val']

    if return_driver:
        return gbtc_df, driver

    driver.quit()    
    return gbtc_df


def save_data(gbtc_df):
    """
    saves scraped data to a DB
    for now only works with sqlite
    """
    if STORAGE == 'sqlite':
        save_data_sqlite(gbtc_df)


def save_data_sqlite(gbtc_df):
    path = os.path.expanduser(DB_LOC)
    if not os.path.exists(path):
        # ideally should step through each directory in
        # the path and make it if not exists
        os.mkdir(path)

    db_path = os.path.join(path, DB_NAME)
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        latest = get_latest_data_sqlite(conn)
        # enter new data into db
        new_data = gbtc_df[gbtc_df.index > latest.index[-1]]
        if new_data.shape[0] > 0:
            new_data.to_sql('gbtc', conn, if_exists='append')
    else:
        conn = sqlite3.connect(db_path)
        gbtc_df.to_sql('gbtc', conn)
    
    conn.close()


def get_latest_data_sqlite(conn):
    latest = pd.read_sql('SELECT * from gbtc order by mkt_time desc limit 1',
                            conn,
                            index_col='mkt_time',
                            parse_dates='mkt_time')
    return latest


def get_data():
    """
    first checks if latest data is in database; otherwise, 
    """
    def check_latest_data_sqlite():
        update = False

        # see if any db exists
        path = os.path.expanduser(DB_LOC)
        db_path = os.path.join(path, DB_NAME)
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            latest = get_latest_data_sqlite(conn)
            conn.close()

            # stonks market calendar
            now = pd.datetime.now(pytz.timezone('US/Eastern'))
            ndq = mcal.get_calendar('NASDAQ').schedule('2010-01-01', now)
            ndq.market_close = ndq.market_close.dt.tz_convert('US/Eastern')

            # if the latest trading day is after the latest date we have,
            # and we are past the last day's close, update 
            if ndq.index.max().date() > latest.index[-1].date():
                if ndq.iloc[-1].market_close < now:
                    update = True
        else:
            update = True
        
        return update

    if STORAGE == 'sqlite':
        update = check_latest_data_sqlite()
        if update:
            gbtc_df = get_gbtc_web_data()
            save_data(gbtc_df)
        else:
            path = os.path.expanduser(DB_LOC)
            db_path = os.path.join(path, DB_NAME)
            conn = sqlite3.connect(db_path)
            gbtc_df = pd.read_sql('SELECT * from gbtc order by mkt_time asc',
                                    conn,
                                    index_col='mkt_time',
                                    parse_dates='mkt_time')

        return gbtc_df


if __name__ == "__main__":
    gbtc_df = get_data()
    gbtc_df['premium'].iplot()

    # what is our current location in the range of premiums?

    todays_date = pd.datetime.now(tz=pytz.timezone('US/Eastern'))
    filename = os.path.join(os.getcwd(),'current_gbtc_premium_{}.png'.format(todays_date.strftime('%m-%d-%Y')))
    todays_date = todays_date.strftime('%B %d, %Y')
    latest_premium = gbtc_df.iloc[-1]['premium']
    fig = gbtc_df['premium'].iplot(kind='hist',
                            vline=[{'x':latest_premium, 'color':'orange', 'width':5}],
                            color='blue',
                            title=todays_date,
                            xTitle='GBTC premium',
                            yTitle='binned frequency',
                            width=5,
                            asFigure=True)
    fig.update_layout(
        annotations=[dict(
            showarrow=False,
            x=latest_premium,
            y=122,
            text="current premium",
            xanchor="left",
            xshift=5
        )]
    )
    fig.write_image(filename, scale=3)
    fig.show()


    gbtc_df.plot(subplots=True, logy=True)
    plot = plt.gcf()
    plot.axes[2].set_yscale('linear')
    min_premium_date = gbtc_df['premium'].dropna().index.min()
    plt.xlim(min_premium_date, gbtc_df.index.max())
    plt.show()