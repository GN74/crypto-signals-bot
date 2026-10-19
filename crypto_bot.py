import ccxt
import pandas as pd
import requests
from datetime import datetime
import os
import time
import html

# === НАСТРОЙКИ ===
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SYMBOLS = [
    'SOL/USDT', 'SEI/USDT', 'NEAR/USDT', 'SUI/USDT', 'AVAX/USDT',
    'RNDR/USDT', 'FET/USDT', 'WIF/USDT', 'PEPE/USDT', 'INJ/USDT'
]

# Задержка между запросами к бирже (секунды) для избежания rate limit
REQUEST_DELAY = 0.2


def calculate_ema(prices: pd.Series, length: int) -> pd.Series:
    """Расчёт EMA."""
    return prices.ewm(span=length, adjust=False).mean()


def calculate_rsi(prices: pd.Series, length: int = 14) -> pd.Series:
    """Расчёт RSI."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=length).mean()
    rs = gain / loss
    return 100.0 - (100.0 / (1.0 + rs))


def send_telegram_message(message: str) -> None:
    """Отправка сообщения в Telegram с безопасным форматированием HTML."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(
            url,
            data={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            },
            timeout=10
        )
        if response.status_code == 200:
            print("✅ Сообщение успешно отправлено в Telegram!")
        else:
            print(f"❌ Ошибка Telegram API ({response.status_code}): {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Сбой сети при отправке в Telegram: {e}")


def check_strategy(symbol: str) -> str | None:
    """Проверка стратегии Микро-импульс для одного символа."""
    try:
        exchange = ccxt.binance({'enableRateLimit': True})

        # Тренд на 1H: цена выше EMA 21
        ohlcv_1h = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
        df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1h['ema21'] = calculate_ema(df_1h['close'], 21)
        current_price = float(df_1h['close'].iloc[-1])
        ema21 = float(df_1h['ema21'].iloc[-1])

        # RSI на 15m: зона 30–45
        ohlcv_15m = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=50)
        df_15m = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_15m['rsi'] = calculate_rsi(df_15m['close'], 14)
        rsi = float(df_15m['rsi'].iloc[-1])

        # Условия стратегии
        if current_price > ema21 and 30 <= rsi <= 45:
            safe_symbol = html.escape(symbol)
            return (
                f"✅ <b>PASS</b>: <code>{safe_symbol}</code>\n"
                f"💰 Цена: <code>{current_price:.4f}</code>\n"
                f"📉 RSI 15m: <code>{rsi:.1f}</code>\n"
                f"📈 Цена &gt; EMA21 (1H)"
            )
        return None

    except Exception as e:
        print(f"❌ Ошибка при проверке {symbol}: {e}")
        return None


def main():
    # Проверка обязательных переменных окружения
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError(
            "❌ TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID не заданы в переменных окружения!\n"
            "Убедитесь, что секреты настроены в GitHub Actions Settings → Secrets."
        )

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Запуск сканирования...")
    signals = []

    for symbol in SYMBOLS:
        res = check_strategy(symbol)
        if res:
            signals.append(res)
        time.sleep(REQUEST_DELAY)

    if signals:
        msg = "🚨 <b>СИГНАЛЫ: Стратегия Микро-импульс</b>\n\n"
        msg += "\n\n".join(signals)
        msg += "\n\n⚠️ <i>Проверьте график на BingX перед входом!</i>"
    else:
        msg = "⚠️ <b>Рынок не даёт setups по стратегии. Ждём. Капитал сохранён.</b>"

    send_telegram_message(msg)


if __name__ == "__main__":
    main()
