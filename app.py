"""
نقطة دخول رئيسية لبوت التيليجرام على منصة Render
يستخدم Webhook للاتصال بواجهة برمجة تطبيق تيليجرام
"""

import logging
import os
import sys
from pathlib import Path

# إعداد مسار المجلدات الضرورية
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# إنشاء المجلدات اللازمة إن لم تكن موجودة
Path(current_dir / "data").mkdir(exist_ok=True)
Path(current_dir / "data/images").mkdir(exist_ok=True)
Path(current_dir / "logs").mkdir(exist_ok=True)
Path(current_dir / "temp_media").mkdir(exist_ok=True)

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(current_dir / "logs/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# استيراد Flask بعد إعداد مسارات المجلدات
from flask import Flask, request, jsonify, render_template
from bot import build_application, get_bot_instance

# إعداد Flask
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "naturecare_telegram_bot_secret")

# استيراد السر
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("No TELEGRAM_BOT_TOKEN found in environment variables!")
    sys.exit(1)

# الحصول على عنوان Webhook
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
if not WEBHOOK_URL:
    logger.warning("No WEBHOOK_URL found in environment variables! "
                  "Webhook will not be set automatically.")

# صفحة الترحيب
@app.route('/')
def index():
    return render_template('index.html')

# نقطة نهاية الويب هوك
@app.route(f'/webhook/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.json
    application = get_bot_instance()
    
    if application and update:
        application.process_update(update)
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error", "message": "Could not process update"}), 400

# نقطة نهاية للتحقق من الحالة
@app.route('/health')
def health():
    return jsonify({"status": "ok", "message": "Bot is running"}), 200

# تهيئة التطبيق عند بدء التشغيل
async def init_app():
    try:
        logger.info("Starting bot with webhook.")
        webhook_path = f"/webhook/{TELEGRAM_BOT_TOKEN}"
        webhook_url = f"{WEBHOOK_URL}{webhook_path}" if WEBHOOK_URL else None
        
        # بناء وتهيئة التطبيق
        await build_application(webhook_url=webhook_url)
        logger.info(f"Bot started successfully with webhook URL: {webhook_url}")
        
        return True
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return False

# تهيئة التطبيق عند بدء التشغيل
import asyncio
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_app())

# نقطة الدخول للتشغيل
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)