from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import os
from dotenv import load_dotenv
from logzero import logger
import datetime
from collections import defaultdict, deque
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
from api import place_order,get_eq_symbol_token,available_cash,fetch_ltp

# Load env variables
load_dotenv('.env')
API_KEY = os.getenv("API_KEY")
CLIENT_CODE = os.getenv("CLIENT_CODE")
AUTH_TOKEN = os.getenv("jwtToken")
FEED_TOKEN = os.getenv("feedToken")

# Constants
CORRELATION_ID = "abc12abc12"
MODE = 2  # QUOTE mode

# Data storage
ltp_history = defaultdict(lambda: deque(maxlen=30))
time_history = defaultdict(lambda: deque(maxlen=30))
volume_history = defaultdict(lambda: deque(maxlen=30))
tick_volume_history = defaultdict(lambda: deque(maxlen=30))
buy_signals = defaultdict(lambda: deque(maxlen=10))
sell_signals = defaultdict(lambda: deque(maxlen=10))
buy_price = defaultdict(float)
sell_price = defaultdict(float)
gains = defaultdict(float)
last_signal = defaultdict(lambda: None)
qty = defaultdict(int)


def try_exec(type, symbol,stop_loss=0):
    print(f"Trying to {type} {symbol}")
    success = place_order(type, symbol,symboltoken=SYMBOL_TOKEN_MAP.get(symbol),qty=qty[symbol],stop_loss=stop_loss,override=True)
    log_msg = f"[{datetime.datetime.now().strftime('%c')}]{'PLACED'}:[{symbol}] | {'GAINS'}:{gains[symbol]:.2f}%\n"
    if success:
        with open("ledger.txt", "a") as f:
            f.write(log_msg)
    else:
        print("Execution failed.")
        
#INIT PRE-TRADE
stocks=["BPCL"]
BALANCE_PER_STOCK=available_cash()/len(stocks)
for stock in stocks:
    symb,tok= get_eq_symbol_token(stock)    
    TOKEN_SYMBOL_MAP = {tok: symb} 
    SYMBOL_TOKEN_MAP = {symb: tok} 
    ltp = fetch_ltp(list(TOKEN_SYMBOL_MAP.keys()))
    qty[symb]=BALANCE_PER_STOCK/ltp
    stop_loss = ltp - ltp*0.01 
    try_exec("SELL", symb,stop_loss)

def evaluate_strategy(symbol, timestamp, ltp_now, tick_volume):
    tick_volume_history[symbol].append(tick_volume)

    if len(tick_volume_history[symbol]) < 30:
        return

    avg_volume = sum(tick_volume_history[symbol]) / 30
    recent_high = max(ltp_history[symbol])
    recent_low = min(ltp_history[symbol])
    last = last_signal[symbol]
    buy_price_val = buy_price[symbol]

    if tick_volume > 1.1 * avg_volume:
        if last != "BUY" and ltp_now < recent_high:
            print(f"🔼 BUY SIGNAL [{symbol}] at ₹{ltp_now:.2f}")
            buy_signals[symbol].append((timestamp.strftime('%H:%M:%S'), ltp_now))
            try_exec("BUY", symbol)
            last_signal[symbol] = "BUY"
            buy_price[symbol] = ltp_now

        elif last == "BUY" and ltp_now > buy_price_val:
            print(f"🔽 SELL SIGNAL [{symbol}] at ₹{ltp_now:.2f}")
            sell_signals[symbol].append((timestamp.strftime('%H:%M:%S'), ltp_now))
            try_exec("SELL", symbol)
            last_signal[symbol] = "SELL"
            sell_price[symbol] = ltp_now

            if buy_price_val != 0:
                profit = ((ltp_now - buy_price_val) / buy_price_val) * 100
                gains[symbol] += profit


def on_data(wsapp, message):
    token = message.get("token")
    symbol = TOKEN_SYMBOL_MAP.get(token)
    if not symbol:
        return

    raw_ltp = message.get("last_traded_price", 0)
    if not raw_ltp:
        return
    ltp = raw_ltp / 100.0

    raw_vol = message.get("volume_trade_for_the_day", 0)
    timestamp_ms = message.get("exchange_timestamp", 0)
    timestamp = datetime.datetime.fromtimestamp(timestamp_ms / 1000.0)
    ts_str = timestamp.strftime('%H:%M:%S')

    # Volume delta calculation
    prev_total_vol = volume_history[symbol][-1] if volume_history[symbol] else 0
    tick_vol = raw_vol - prev_total_vol if raw_vol > prev_total_vol else 0
    volume_history[symbol].append(raw_vol)

    if sum(volume_history[symbol]) == tick_vol:
        return  # skip first volume tick

    # Store tick
    ltp_history[symbol].append(ltp)
    time_history[symbol].append(ts_str)

    if tick_vol > 0:
        print(f"[{ts_str}] {symbol} | LTP: ₹{ltp:.2f} | Vol: {tick_vol}")
        evaluate_strategy(symbol, timestamp, ltp, tick_vol)

# WebSocket callbacks
def on_open(wsapp):
    logger.info("WebSocket connection opened")
    sws.subscribe(CORRELATION_ID, MODE, [{
        "exchangeType": 1,
        "tokens": list(TOKEN_SYMBOL_MAP.keys())
    }])

def on_error(wsapp, error):
    logger.error(f"WebSocket error: {error}")

def on_close(wsapp):
    logger.info("WebSocket connection closed")

# Start WebSocket
def start_websocket():
    sws.connect()

sws = SmartWebSocketV2(AUTH_TOKEN, API_KEY, CLIENT_CODE, FEED_TOKEN)
sws.on_open = on_open
sws.on_data = on_data
sws.on_error = on_error
sws.on_close = on_close

threading.Thread(target=start_websocket, daemon=True).start()

# Plotting
def start_ltp_plot(ltp_history, time_history, buy_signals, sell_signals):
    fig, ax = plt.subplots()

    def animate(i):
        ax.clear()
        y_min, y_max = float('inf'), float('-inf')
        plotted = False  # track if any line is drawn

        for symbol in ltp_history:
            times = list(time_history[symbol])
            prices = list(ltp_history[symbol])

            if not times or not prices:
                continue

            ax.plot(times, prices, label=symbol, linewidth=2, color='#5e81ac')
            plotted = True  # a line was drawn

            latest_time = times[-1]
            time_cutoff = times[0]

            for t, p in buy_signals[symbol]:
                if time_cutoff <= t <= latest_time:
                    ax.vlines(t, p + 0.3, p, colors='lime', linestyles='dashed')
                    ax.text(t, p + 0.35, 'BUY', color='lime', ha='center', va='bottom',
                            fontweight='bold', fontsize=9, bbox=dict(facecolor='black', edgecolor='lime'))

            for t, p in sell_signals[symbol]:
                if time_cutoff <= t <= latest_time:
                    ax.vlines(t, p, p - 0.3, colors='orangered', linestyles='dashed')
                    ax.text(t, p - 0.35, 'SELL', color='orangered', ha='center', va='top',
                            fontweight='bold', fontsize=9, bbox=dict(facecolor='black', edgecolor='orangered'))
                
            y_min = min(y_min, min(prices))
            y_max = max(y_max, max(prices))

        if plotted:
            ax.legend(loc='upper left')
        # Only set ylim if we have valid data
        if y_min != float('inf') and y_max != float('-inf'):
            ax.set_ylim(y_min - 1, y_max + 1)

        ax.legend(loc='upper left')
        ax.set_title("LTP Plot with Buy/Sell Signals", color='white')
        ax.set_ylabel("Price (₹)", color='white')
        ax.set_xlabel("Time", color='white')
        plt.xticks(rotation=45)

        ax.set_facecolor("black")
        fig.patch.set_facecolor("black")
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        for spine in ax.spines.values():
            spine.set_color('white')

    ani = FuncAnimation(fig, animate, interval=100, cache_frame_data=False)
    plt.tight_layout()
    plt.show()

start_ltp_plot(ltp_history, time_history, buy_signals, sell_signals)
