import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from tvDatafeed import TvDatafeed, Interval
import openai

# Khai báo token và key từ biến môi trường
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai.api_key = OPENAI_API_KEY

# Khởi tạo TradingView datafeed - nếu bạn có username/password tradingview, truyền vào TvDatafeed(username, password)
# Nếu không, để trống thì có thể lấy dữ liệu hạn chế hoặc lỗi tùy tình trạng
tv = TvDatafeed()

# Mapping các khung thời gian
timeframes = {
    '5 phút': '5',
    '15 phút': '15',
    '1 giờ': '60',
    '4 giờ': '240',
    '12 giờ': '720',
    '1 ngày': 'D',
    '1 tuần': 'W',
    '1 tháng': 'M',
}

interval_map = {
    '5': Interval.in_5_minute,
    '15': Interval.in_15_minute,
    '60': Interval.in_1_hour,
    '240': Interval.in_4_hour,
    '720': Interval.in_12_hour,
    'D': Interval.in_daily,
    'W': Interval.in_weekly,
    'M': Interval.in_monthly,
}

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Chào bạn, gửi lệnh /phantich <cặp tiền ví dụ EURUSD> để phân tích cấu trúc thị trường.")

def phantich(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        update.message.reply_text("Vui lòng nhập đúng định dạng: /phantich <cặp tiền ví dụ: EURUSD>")
        return
    
    pair = context.args[0].upper()
    keyboard = [[InlineKeyboardButton(k, callback_data=f"{pair}|{v}")] for k, v in timeframes.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Chọn khung thời gian muốn phân tích:", reply_markup=reply_markup)

def get_candles_from_tradingview(pair, timeframe):
    try:
        interval = interval_map.get(timeframe, Interval.in_daily)
        data = tv.get_hist(pair, 'FX', interval, n_bars=100)
        candles = data.to_dict('records')
        return candles
    except Exception as e:
        return None

def analyze_market_structure_with_gpt(pair, timeframe, candles):
    if not candles:
        return "Không lấy được dữ liệu nến từ TradingView."

    simplified_candles = [{
        "datetime": c.get('datetime').strftime("%Y-%m-%d %H:%M") if c.get('datetime') else '',
        "open": c.get('open'),
        "high": c.get('high'),
        "low": c.get('low'),
        "close": c.get('close'),
        "volume": c.get('volume')
    } for c in candles]

    prompt = f"""
Bạn là chuyên gia phân tích cấu trúc thị trường Forex. 
Dữ liệu dưới đây là 100 cây nến gần nhất của cặp {pair} ở khung thời gian {timeframe}. 
Hãy phân tích xu hướng, chỉ ra các vùng hỗ trợ và kháng cự quan trọng, và các điểm cần lưu ý dựa trên cấu trúc thị trường.

Dữ liệu nến (đã được rút gọn):
{simplified_candles}
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=200000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Lỗi khi gọi OpenAI: {e}"

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    pair, timeframe = query.data.split('|')

    query.edit_message_text(text=f"Đang lấy dữ liệu và phân tích cặp {pair} khung {timeframe}... Vui lòng đợi.")

    candles = get_candles_from_tradingview(pair, timeframe)
    analysis = analyze_market_structure_with_gpt(pair, timeframe, candles)

    query.edit_message_text(text=f"Phân tích cấu trúc thị trường cặp {pair} khung {timeframe}:\n\n{analysis}")

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("phantich", phantich))
    dp.add_handler(CallbackQueryHandler(button_callback))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
