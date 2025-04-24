"""
معالجات المستخدم - تدير التفاعلات مع المستخدمين العاديين
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

from utils.database import (
    search_notifications_by_phone,
    get_notification,
)

# إعداد السجل
logger = logging.getLogger(__name__)

# المجلد الحالي
current_dir = Path(__file__).parent.parent.absolute()

# معرّفات حالات المحادثة
WAITING_FOR_PHONE = 0

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة أمر البحث /search"""
    if context.args and len(context.args) > 0:
        # البحث باستخدام الوسيطة المقدمة
        phone_number = context.args[0]
        await search_notification(update, context, phone_number)
        return ConversationHandler.END
    
    # طلب رقم الهاتف
    await update.message.reply_text(
        "الرجاء إدخال رقم هاتفك للبحث عن إشعاراتك:"
    )
    return WAITING_FOR_PHONE

async def received_search_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة رقم الهاتف المستلم للبحث"""
    phone_number = update.message.text
    await search_notification(update, context, phone_number)
    return ConversationHandler.END

async def search_notification(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str) -> None:
    """البحث عن إشعار بواسطة رقم الهاتف"""
    # تنظيف رقم الهاتف من الأحرف غير الرقمية
    clean_phone = ''.join(filter(str.isdigit, phone_number))
    
    # البحث عن الإشعارات
    results = search_notifications_by_phone(clean_phone)
    
    if not results:
        await update.message.reply_text(
            f"لم يتم العثور على إشعارات مطابقة لرقم الهاتف '{phone_number}'."
        )
        return
    
    # عرض نتائج البحث
    message = f"تم العثور على {len(results)} إشعارات مطابقة لرقم الهاتف '{phone_number}':\n\n"
    
    for i, notification in enumerate(results, start=1):
        message += f"{i}. اسم العميل: {notification['customer_name']}\n"
        # تجنب عرض رقم الهاتف الكامل للمستخدمين العاديين
        message += f"   رقم الهاتف: {'*' * (len(notification['phone_number']) - 4) + notification['phone_number'][-4:]}\n"
        message += f"   رمز الإشعار: {notification['id'][:8]}\n\n"
    
    await update.message.reply_text(message)
    
    # إرسال صور الإشعارات
    for notification in results:
        try:
            with open(f"{current_dir}/{notification['image_path']}", "rb") as image_file:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=image_file,
                    caption=f"صورة الإشعار رقم {notification['id'][:8]}"
                )
        except Exception as e:
            logger.error(f"Error sending notification image: {e}")
            await update.message.reply_text(f"حدث خطأ أثناء إرسال صورة الإشعار {notification['id'][:8]}")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء المحادثة الحالية"""
    await update.message.reply_text(
        "تم إلغاء العملية الحالية."
    )
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر المساعدة /help"""
    help_text = (
        "مرحباً بك في بوت إشعارات الشحن!\n\n"
        "الأوامر المتاحة:\n"
        "/start - بدء استخدام البوت\n"
        "/search - البحث عن إشعاراتك باستخدام رقم هاتفك\n"
        "/help - عرض هذه الرسالة\n\n"
        "يمكنك أيضاً استخدام /search متبوعاً برقم هاتفك مباشرة، مثل:\n"
        "/search 0912345678"
    )
    
    await update.message.reply_text(help_text)

def get_user_handlers() -> List[Any]:
    """
    الحصول على جميع معالجات المستخدم
    
    العائد:
        قائمة بمعالجات المستخدم
    """
    # معالج المحادثة للبحث
    search_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_command)],
        states={
            WAITING_FOR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_search_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    
    # قائمة بجميع معالجات المستخدم
    handlers = [
        # أمر المساعدة
        CommandHandler("help", help_command),
        
        # معالج البحث
        search_handler,
    ]
    
    return handlers