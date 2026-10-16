import ccxt
import pandas as pd
import pandas_ta as ta
import requests
from datetime import datetime

# === ВСТАВЬ СЮДА СВОИ ДАННЫЕ ===
TELEGRAM_BOT_TOKEN = '8817909083:AAFv5Fr2o121Pepgs35ehHHhmh6h03mcoqQ'
TELEGRAM_CHAT_ID = '778908720'

# Список монет для проверки
SYMBOLS = ['SOL/USDT', 'SEI/USDT', 'NEAR/USDT', 'SUI/USDT', 'AVAX/USDT',
           'RNDR/USDT', 'FET/USDT', 'WIF/USDT', 'PEPE/USDT', 'INJ/USDT']

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'})

def check_strategy(symbol):
    try:
        exchange = ccxt.binance()

        # Проверяем тренд на 1-часовом графике
        ohlcv_1h = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
        df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1h['ema21'] = ta.ema(df_1h['close'], length=21)
        current_price = df_1h['close'].iloc[-1]
        ema21 = df_1h['ema21'].iloc[-1]

        # Проверяем RSI на 15-минутном графике
        ohlcv_15m = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
        df_15m = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_15m['rsi'] = ta.rsi(df_15m['close'], length=14)
        rsi = df_15m['rsi'].iloc[-1]

        # Если условия стратегии выполнены
        if current_price > ema21 and 30 <= rsi <= 45:
            return f"✅ *PASS*: `{symbol}`\n💰 Цена: `{current_price}`\n📉 RSI 15m: `{rsi:.1f}`\n📈 Цена > EMA21 (1H)"
        return None
    except Exception as e:
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
