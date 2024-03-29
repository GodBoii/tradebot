from datetime import datetime, time
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dhanhq import dhanhq
import time as sleep_time

# Function to check if the current time is within trading hours
def is_trading_time():
    current_time = datetime.now().time()
    trading_start_time = time(9, 45)
    trading_end_time = time(14, 30)  # 2:30 PM
    return trading_start_time <= current_time <= trading_end_time

# Function to fetch historical data from Yahoo Finance with a specified interval
def fetch_historical_data(symbol, start_date, end_date, interval='1d'):
    try:
        stock_data = yf.download(symbol, start=start_date, end=end_date, interval=interval)
        return stock_data

    except Exception as e:
        print("Error fetching historical data:", str(e))
        return None

# Function to calculate volatility using historical data
def calculate_volatility(data):
    try:
        # Calculate volatility using standard deviation
        volatility = data['Close'].pct_change().std()
        return volatility

    except Exception as e:
        print("Error calculating volatility:", str(e))
        return None

# Function to implement EMA crossover strategy with buy/sell signals at crossover points
def ema_crossover_strategy(data, order_size, stop_loss, take_profit, backtest_mode=False, save_path='', dhan=None):
    try:
        # Calculate 30EMA and 3EMA
        data['30EMA'] = data['Close'].ewm(span=30, adjust=False).mean()
        data['3EMA'] = data['Close'].ewm(span=3, adjust=False).mean()

        # Identify crossover points
        data['Crossover'] = np.where(data['30EMA'] > data['3EMA'], 1, -1)

        # Shift the crossover column by one row to identify the previous state
        data['Previous_Crossover'] = data['Crossover'].shift(1)

        # Identify candle direction based on previous close and open prices
        data['Candle_Direction'] = np.where(data['Close'] > data['Open'], 1, -1)

        # Identify buy and sell signals based on crossover points and previous candle direction
        data['Signal'] = np.where((data['Crossover'] == 1) & (data['Previous_Crossover'] == -1) & 
                                  (data['Candle_Direction'].shift(1) == -1), 1,
                                  np.where((data['Crossover'] == -1) & (data['Previous_Crossover'] == 1) & 
                                           (data['Candle_Direction'].shift(1) == 1), -1, 0))

        # Filter signals for buy and sell
        buy_signals = data[data['Signal'] == -1].tail(3)
        sell_signals = data[data['Signal'] == 1].tail(3)

        # Implement your trading logic here
        if not backtest_mode and dhan is not None:
            # Live trading: Execute orders
            if not buy_signals.empty:
                print("Executing Buy Order...")
                # Place your buy order using the Dhan API
                dhan.place_order(
                    security_id='1333',  # HDFC Bank
                    exchange_segment=dhan.NSE,
                    transaction_type=dhan.BUY,
                    quantity=order_size,
                    order_type=dhan.MARKET,
                    product_type=dhan.INTRA,
                    price=0
                )

            elif not sell_signals.empty:
                print("Executing Sell Order...")
                # Place your sell order using the Dhan API
                dhan.place_order(
                    security_id='1333',  # HDFC Bank
                    exchange_segment=dhan.NSE,
                    transaction_type=dhan.SELL,
                    quantity=order_size,
                    order_type=dhan.MARKET,
                    product_type=dhan.INTRA,
                    price=0
                )

        else:
            # Backtesting: Plot signals
            plot_signals(data, buy_signals, sell_signals, save_path)

    except Exception as e:
        print("Error implementing strategy:", str(e))

# Function to plot 5-minute timeframe data with 30EMA and 3EMA lines
def plot_signals(data, buy_signals, sell_signals, save_path):
    fig = go.Figure()

    # Plot 5-minute timeframe data
    fig.add_trace(
        go.Candlestick(x=data.index,
                       open=data['Open'],
                       high=data['High'],
                       low=data['Low'],
                       close=data['Close'],
                       name='5min Candlesticks')
    )

    # Plot 30EMA line
    fig.add_trace(
        go.Scatter(x=data.index,
                   y=data['30EMA'],
                   mode='lines',
                   name='30EMA',
                   line=dict(color='green', width=2))
    )

    # Plot 3EMA line
    fig.add_trace(
        go.Scatter(x=data.index,
                   y=data['3EMA'],
                   mode='lines',
                   name='3EMA',
                   line=dict(color='red', width=2))
    )

    # Plot Buy signals
    fig.add_trace(
        go.Scatter(x=buy_signals.index,
                   y=buy_signals['Low'],
                   mode='markers',
                   marker=dict(color='green', size=8),
                   name='Buy Signals')
    )

    # Plot Sell signals
    fig.add_trace(
        go.Scatter(x=sell_signals.index,
                   y=sell_signals['High'],
                   mode='markers',
                   marker=dict(color='red', size=8),
                   name='Sell Signals')
    )

    fig.update_layout(title_text="5-Minute Timeframe with EMA Lines and Signals",
                      xaxis_title="Time",
                      yaxis_title="Price",
                      showlegend=True)

    # Save the plot as HTML file
    html_file_path = f"{save_path}\\backtesting_signals_5min.html"
    fig.write_html(html_file_path)
    print(f"Backtesting signals saved at: {html_file_path}")

# Main program
if __name__ == "__main__":
    nifty_symbol = '^NSEI'  # Example: Nifty 50 index
    order_size = 1  # Adjust as needed
    stop_loss = 10  # Adjust as needed
    take_profit = 10  # Adjust as needed

    backtest_save_path = 'E:\\backtesting'  # Adjust the path as needed

    # Initialize the Dhan API
    client_id = "1102524211"
    access_token = "your_access_token_here"
    dhan = dhanhq(client_id, access_token)

    while True:
        if is_trading_time():
            # Live Trading Mode
            print("Live Trading Mode - Executing Strategy...")

            # Fetch live data from Yahoo Finance with a 5-minute interval
            live_data_5min = fetch_historical_data(
                symbol=nifty_symbol,
                start_date=datetime.now().strftime('2024-02-28'),
                end_date=datetime.now().strftime('2024-02-29'),
                interval='5m'
            )

            if live_data_5min is not None:
                # Calculate volatility (for live data)
                volatility = calculate_volatility(live_data_5min)
                print(f"Volatility: {volatility}")

                # Implement EMA Crossover Strategy (for live data)
                ema_crossover_strategy(
                    data=live_data_5min,
                    order_size=order_size,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    backtest_mode=True,  # Set backtest_mode to False for live trading
                    dhan=dhan  # Pass the Dhan API object to the strategy function
                )

        # Sleep for 5 minutes before fetching data again
        sleep_time.sleep(300)  # 300 seconds = 5 minutes
