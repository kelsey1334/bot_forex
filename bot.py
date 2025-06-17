import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from tradingview_ta import TA_Handler, Interval
import openai

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai.api_key = OPENAI_API_KEY

timeframes = {
    '5 phút': '5',
    '15 phút': '15',
    '1 giờ': '60',
    '2 giờ': '120',
    '4 giờ': '240',
    '1 ngày': 'D',
    '1 tuần': 'W',
    '1 tháng': 'M',
}

interval_map = {
    '5': Interval.INTERVAL_5_MINUTES,
    '15': Interval.INTERVAL_15_MINUTES,
    '60': Interval.INTERVAL_1_HOUR,
    '120': Interval.INTERVAL_2_HOURS,
    '240': Interval.INTERVAL_4_HOURS,
    'D': Interval.INTERVAL_1_DAY,
    'W': Interval.INTERVAL_1_WEEK,
    'M': Interval.INTERVAL_1_MONTH,
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Chào bạn! Gửi lệnh /phantich <cặp tiền ví dụ EURUSD> để phân tích cấu trúc thị trường Forex."
    )

async def phantich(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Vui lòng nhập đúng định dạng: /phantich <cặp tiền ví dụ: EURUSD>")
        return
    
    pair = context.args[0].upper()
    keyboard = [[InlineKeyboardButton(k, callback_data=f"{pair}|{v}")] for k, v in timeframes.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Chọn khung thời gian muốn phân tích:", reply_markup=reply_markup)

def get_analysis_from_tradingview(pair: str, timeframe: str):
    try:
        interval = interval_map.get(timeframe, Interval.INTERVAL_1_DAY)
        handler = TA_Handler(
            symbol=pair,
            exchange="FX_IDC",
            screener="forex",
            interval=interval
        )
        analysis = handler.get_analysis()
        return {
            "summary": analysis.summary,
            "oscillators": analysis.oscillators,
            "moving_averages": analysis.moving_averages
        }
    except Exception:
        return None

def analyze_market_structure_with_gpt(pair: str, timeframe: str, data: dict):
    if not data:
        return "Không lấy được dữ liệu phân tích từ TradingView."

    prompt = f"""
Bạn là chuyên gia phân tích cấu trúc thị trường Forex.
Dữ liệu phân tích kỹ thuật dưới đây là cho cặp {pair} ở khung thời gian {timeframe}:
- Tổng quan: {data['summary']}
- Dao động (Oscillators): {data['oscillators']}
- Trung bình động (Moving Averages): {data['moving_averages']}

Hãy phân tích xu hướng, chỉ ra các vùng hỗ trợ và kháng cự quan trọng, và các điểm cần lưu ý dựa trên dữ liệu này.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Lỗi khi gọi OpenAI: {e}"

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pair, timeframe = query.data.split('|')
    await query.edit_message_text(text=f"Đang lấy dữ liệu và phân tích cặp {pair} khung {timeframe}... Vui lòng đợi.")

    data = get_analysis_from_tradingview(pair, timeframe)
    analysis = analyze_market_structure_with_gpt(pair, timeframe, data)

    await query.edit_message_text(text=f"Phân tích cấu trúc thị trường cặp {pair} khung {timeframe}:\n\n{analysis}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("phantich", phantich))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.run_polling()

if __name__ == '__main__':
    main()
