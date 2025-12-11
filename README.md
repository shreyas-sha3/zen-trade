# ZenTrade - Automated Trading System for Angel One

ZenTrade is an automated trading system that interfaces with Angel One's SmartAPI to execute trades based on volume and price movements. The system includes real-time market data monitoring, automated trading signals, and live visualization of price movements.

## Features

- Real-time market data monitoring via WebSocket
- Volume-based trading strategy
- Automated buy/sell signal generation
- Real-time price visualization with trading signals
- Automatic stop-loss implementation
- Performance tracking and trade logging
- Equal balance distribution among tracked stocks

## Trading Strategy

The system implements a volume-based trading strategy:

- **Buy Signals** trigger when:
  - Current volume exceeds 1.1x the 30-tick average volume
  - Current price is below recent high

- **Sell Signals** trigger when:
  - Volume spike occurs (>1.1x average)
  - Current price is higher than buy price

- **Risk Management**:
  - Automatic stop-loss at 1% below entry price
  - Equal distribution of available balance among tracked stocks
  - Comprehensive trade logging

## Prerequisites

- Python 3.x
- Angel One Trading Account
- Smart API Credentials

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ZenTrade.git
cd ZenTrade
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your Angel One credentials:
```
API_KEY=your_api_key
CLIENT_CODE=your_client_code
PASSWORD=your_password
TOTP_SECRET=your_totp_secret
jwtToken=your_jwt_token
refreshToken=your_refresh_token
feedToken=your_feed_token
```

## Usage

1. Run the main trading program:
```bash
python livefeed.py
```

The program will:
- Connect to market data feed
- Initialize the trading algorithm
- Display real-time price chart with buy/sell signals
- Log all trades to `ledger.txt`

## Project Structure

- `livefeed.py`: Main trading program with WebSocket implementation for market data
- `api.py`: Angel One API interface for executing trades and account management
- `ledger.txt`: Log file for all executed trades
- Various `.log` files: System and error logging

## Configuration

Edit the `stocks` list in `livefeed.py` to modify which stocks to track:
```python
stocks = ["BPCL"]  # Add more stock symbols as needed
```

## Security Notes

- Never commit your `.env` file
- Keep your API credentials secure
- Regularly update your authentication tokens

## Disclaimer

This is an automated trading system. Please use it at your own risk and ensure you understand the trading strategy before deploying with real funds. Past performance does not guarantee future results.
