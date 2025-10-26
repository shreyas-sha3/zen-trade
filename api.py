from SmartApi.smartConnect import SmartConnect
import pyotp
import os
from dotenv import load_dotenv, set_key
import pandas as pd

# Load environment variables from .env
env_path = '.env'
load_dotenv()

API_KEY = os.getenv("API_KEY")
CLIENT_CODE = os.getenv("CLIENT_CODE")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")

jwtToken = os.getenv("jwtToken")
refreshToken = os.getenv("refreshToken")
feedToken = os.getenv("feedToken")

# Generate OTP from TOTP secret
otp = pyotp.TOTP(TOTP_SECRET).now()

# Create SmartAPI client
smartApi = SmartConnect(api_key=API_KEY)
def login():
    try:
        response = smartApi.generateSession(CLIENT_CODE, PASSWORD, otp)
        print("Login response:")
        print(response)\
        #set access token in the API 
        smartApi.setAccessToken(response["data"]["jwtToken"])
        smartApi.setRefreshToken(response["data"]["refreshToken"])
        #Update tokens in .env to autologin in future
        set_key(env_path,"jwtToken", response["data"]["jwtToken"][7:])
        set_key(env_path,"refreshToken", response["data"]["refreshToken"])
        set_key(env_path,"feedToken", response["data"]["feedToken"])
        return response
    except Exception as e:
        print("Login failed:", e)
        return None

# login()

def get_holdings():
    try:
        # print("Using Token:",jwtToken)
        holdings = smartApi.allholding()
        print("Your Holdings:")
        df = pd.DataFrame(holdings["data"]["holdings"])
        df = df[["tradingsymbol", "quantity", "averageprice", "ltp", "profitandloss", "pnlpercentage"]]
        return(df)
    except Exception as e:
        print("Failed to fetch holdings:", e)
        return None

def get_eq_symbol_token(user_input: str) -> tuple[str, str] | tuple[None, None]:
    try:
        results = smartApi.searchScrip("NSE", user_input)["data"]
        print()
        for item in results:
            ts = item.get("tradingsymbol", "")
            if ts.endswith("-EQ"):
                return ts, item["symboltoken"]
        print(f"No -EQ symbol found for '{user_input}'")
        return None, None
    except Exception as e:
        return None, None
    
def fetch_ltp(symboltokens):
    try:
        exchangeTokens = { "NSE": [token for token in symboltokens] }
        response=smartApi.getMarketData("LTP",exchangeTokens)["data"]["fetched"]
        df = pd.DataFrame(response)
        print(df)
        return df["tradingsymbol","ltp"].tolist()
    except Exception as e:
        print("Failed to place buy order:", e)
        return None


def place_order(transactiontype, tradingsymbol, symboltoken=0, qty=1,stop_loss=0,override=False):
    if not override:
        tradingsybmol, symboltoken = get_eq_symbol_token(tradingsymbol)

    if symboltoken:
        if not override:
            if transactiontype == "BUY":
                fetch_ltp(symboltoken)
                qty = input("Enter quantity:")   
                confirm = input(f"Confirm Buying {qty} Stock of {tradingsybmol} id= {symboltoken}...(y/n)").lower()
            elif transactiontype == "SELL":
                holdings_df = get_holdings()
                print(holdings_df[holdings_df["tradingsymbol"] == tradingsybmol])
                qty = input("Enter quantity:")
                confirm = input(f"Confirm Selling {qty} Stock of {tradingsybmol} id= {symboltoken}...(y/n)").lower()
            if confirm == "n":
                return 
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": tradingsymbol,
                "symboltoken": symboltoken,
                "transactiontype": transactiontype,
                "exchange": "NSE",
                "ordertype": "MARKET",
                "producttype": "DELIVERY",
                "duration": "DAY",
                "price": 0,
                "quantity": qty
            }
        elif stop_loss==0:
            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": tradingsymbol,
                "symboltoken": symboltoken,
                "transactiontype": transactiontype,  # "BUY" or "SELL"
                "exchange": "NSE",
                "ordertype": "MARKET",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": 0,
                "quantity": qty
            }
        else:
            order_params = {
                "variety": "STOPLOSS",
                "tradingsymbol": tradingsymbol,
                "symboltoken": symboltoken,
                "transactiontype": transactiontype,
                "exchange": "NSE",
                "ordertype": "STOPLOSS_MARKET",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "triggerprice": stop_loss,
                "price": 0,
                "quantity": qty
            }

        try:
            order_id = smartApi.placeOrder(order_params)
            print(f"Order Placed! Order ID: {order_id}")
            return order_id
        except Exception as e:
            print("Failed to place order:", e)
            return None

def cancel_order():
    df = pd.DataFrame(smartApi.orderBook()["data"])
    df = df[["variety","tradingsymbol", "transactiontype", "quantity", "status", "orderid"]]
    print(df)
    try:
        selected = int(input("\nEnter the index of the order you want to cancel: "))
        if 0 <= selected < len(df):
            order_id = df.loc[selected, "orderid"]
            # variety = df.loc[selected, "variety"]
            variety = "NORMAL"
            response = smartApi.cancelOrder(order_id,variety)
            print(f"Order {order_id} cancelled successfully!")
        else:
            print("Invalid index")
    except Exception as e:
        print("Failed to cancel order:", e)


#CHOICE
smartApi.setAccessToken(jwtToken)
smartApi.setRefreshToken(refreshToken)


import threading
import json
import websocket

ORDER_STATUS_URL = "wss://tns.angelone.in/smart-order-update"

def _on_order_message(ws, message):
    try:
        data = json.loads(message)
        order = data.get("orderData", {})
        status = data.get("order-status", "UNKNOWN")
        if order.get('tradingsymbol'):
            print(f"[Order Update] {order.get('transactiontype')} {order.get('tradingsymbol')} | "
                f"Qty: {order.get('quantity')} | Status: {order.get('orderstatus')} | "
                f"Filled: {order.get('filledshares')}/{order.get('quantity')}")
    except Exception as e:
        print("Error in order status message:", e)

def _on_order_open(ws):
    print("[✓] Order status WebSocket connected")

def _on_order_error(ws, error):
    print("[!] Order WebSocket error:", error)

def _on_order_close(ws):
    print("[x] Order WebSocket closed")

def _start_order_status_ws():
    ws = websocket.WebSocketApp(
        ORDER_STATUS_URL,
        header=[f"Authorization: Bearer {jwtToken}"],
        on_open=_on_order_open,
        on_message=_on_order_message,
        on_error=_on_order_error,
        on_close=_on_order_close
    )
    threading.Thread(target=ws.run_forever, daemon=True).start()

_start_order_status_ws()

def available_cash():
    return (smartApi.rmsLimit()["data"]["availablecash"])

def cliangel():
    while True:
        choice = input("\nWhat?\n 1) Login/Relogin\n 2) Get Holdings\n 3) Place Order\n 4) Sell Stock\n 5) View/Cancel Orders\n> ")
        if choice == "1":
            smartApi = login()  
        elif choice == "2":
            print(get_holdings())
        elif choice == "3":
            symbol = input("Enter stock symbol:")
            place_order("BUY",symbol)
        elif choice == "4":
            print("Sell Stock")
            symbol = input("Enter stock symbol:")
            place_order("SELL",symbol)
            break
        elif choice == "5":
            cancel_order()
        else:
            break

cliangel()