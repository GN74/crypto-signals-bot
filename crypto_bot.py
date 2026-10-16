import ccxt
import pandas as pd
import requests
from datetime import datetime
import os

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SYMBOLS = ['SOL/USDT', 'SEI/USDT', 'NEAR/USDT', 'SUI/USDT', 'AVAX/USDT', 
           'RNDR/USDT', 'FET/USDT', 'WIF/USDT', 'PEPE/USDT', 'INJ/USDT']

# Функции для расчета индикаторов (вместо pandas_ta)
def calculate_ema(prices, length):
    return prices.ewm(span=length, adjust=False).mean()

def calculate_rsi(prices, length=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(
            url, 
            data={'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}, 
            timeout=10
        )
        if response.status_code == 200:
            print("✅ Сообщение успешно отправлено в Telegram!")
        else:
            print(f"❌ Ошибка Telegram API: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Сбой сети: {e}")

def check_strategy(symbol):
    try:
        exchange = ccxt.binance()
        
        # Проверяем тренд на 1H (цена выше EMA 21)
        ohlcv_1h = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
        df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1h['ema21'] = calculate_ema(df_1h['close'], 21)
        current_price = df_1h['close'].iloc[-1]
        ema21 = df_1h['ema21'].iloc[-1]
        
        # Проверяем RSI на 15m (зона 30-45)
        ohlcv_15m = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
        df_15m = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_15m['rsi'] = calculate_rsi(df_15m['close'], 14)
        rsi = df_15m['rsi'].iloc[-1]
        
        # Проверка условий стратегии
        if current_price > ema21 and 30 <= rsi <= 45:
            return f"✅ *PASS*: `{symbol}`\n💰 Цена: `{current_price:.4f}`\n📉 RSI 15m: `{rsi:.1f}`\n📈 Цена > EMA21 (1H)"
        return None
    except Exception as e:
        print(f"Ошибка при проверке {symbol}: {e}")
        return None

def main():
    print(f"[{datetime.now().strftime('%H:%M')}] Запуск сканирования...")
    signals = []
    
    for symbol in SYMBOLS:
        res = check_strategy(symbol)
        if res:
            signals.append(res)
    
    if signals:
        msg = "🚨 *СИГНАЛЫ: Стратегия Микро-импульс*\n\n" + "\n\n".join(signals)
        msg += "\n\n⚠️ *Проверьте график на BingX перед входом!*"
        send_telegram_message(msg)
    else:
        send_telegram_message("⚠️ *Рынок не дает setups по стратегии. Ждем. Капитал сохранен.*")

if __name__ == "__main__":
    main()
