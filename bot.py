"""
ملف مركزي لإعداد وبناء تطبيق بوت التيليجرام
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from telegram import Update, Bot
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

# استيراد معالجات البوت
from handlers.admin_handlers import get_admin_handlers
from handlers.user_handlers import get_user_handlers
from handlers.notification_handlers import get_notification_handlers
from handlers.ai_handlers import get_ai_handlers
from utils.database import setup_database

# إعداد السجل
logger = logging.getLogger(__name__)

# استيراد السر
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("No TELEGRAM_BOT_TOKEN found in environment variables!")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

# متغير عام لتطبيق البوت
_application = None

def build_application(webhook_url: Optional[str] = None) -> Application:
    """
    بناء وإعداد تطبيق البوت
    
    المعلمات:
        webhook_url: عنوان URL للويب هوك، إذا كان None، يتم تعطيل الويب هوك
        
    العائد:
        تطبيق البوت بعد تهيئته
    """
    global _application
    
    # إذا كان التطبيق موجودًا بالفعل، قم بإرجاعه
    if _application:
        return _application
    
    # إنشاء المجلدات الضرورية إن لم تكن موجودة
    current_dir = Path(__file__).parent.absolute()
    Path(current_dir / "data").mkdir(exist_ok=True)
    Path(current_dir / "data/images").mkdir(exist_ok=True)
    Path(current_dir / "logs").mkdir(exist_ok=True)
    Path(current_dir / "temp_media").mkdir(exist_ok=True)
    
    # إعداد قاعدة البيانات
    setup_database()
    
    # بناء تطبيق البوت
    logger.info(f"Building application with token: {TELEGRAM_BOT_TOKEN[:5]}...{TELEGRAM_BOT_TOKEN[-5:]}")
    
    builder = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN)
    
    # إذا تم توفير Webhook URL، قم بتكوينه
    if webhook_url:
        logger.info(f"Setting webhook URL: {webhook_url}")
        builder = builder.webhook(
            webhook_url=webhook_url,
            allowed_updates=Update.ALL_TYPES
        )
    
    # بناء التطبيق
    _application = builder.build()
    
    # تسجيل معالجات البوت
    register_handlers(_application)
    
    return _application

def get_bot_instance() -> Application:
    """
    الحصول على مثيل تطبيق البوت
    
    العائد:
        تطبيق البوت المهيئ أو None إذا لم يتم تهيئته بعد
    """
    return _application

def register_handlers(application: Application) -> None:
    """
    تسجيل جميع معالجات البوت
    
    المعلمات:
        application: تطبيق البوت
    """
    # تسجيل معالجات المستخدم
    user_handlers = get_user_handlers()
    for handler in user_handlers:
        application.add_handler(handler)
    
    # تسجيل معالجات المسؤول
    admin_handlers = get_admin_handlers()
    for handler in admin_handlers:
        application.add_handler(handler)
    
    # تسجيل معالجات الإشعارات
    notification_handlers = get_notification_handlers()
    for handler in notification_handlers:
        application.add_handler(handler)
    
    # تسجيل معالجات الذكاء الاصطناعي
    ai_handlers = get_ai_handlers()
    for handler in ai_handlers:
        application.add_handler(handler)
    
    # إضافة معالج للأخطاء العامة
    application.add_error_handler(error_handler)
    
    logger.info("All handlers registered successfully")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالج الأخطاء للبوت
    
    المعلمات:
        update: تحديث التيليجرام
        context: سياق معالج البوت
    """
    logger.error(f"Update {update} caused error: {context.error}")