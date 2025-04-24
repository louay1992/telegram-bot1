"""
معالجات الإشعارات - تدير العمليات المتعلقة بالإشعارات والتذكيرات
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from utils.database import (
    is_admin,
    get_notifications,
    get_notification,
    mark_reminder_sent,
    get_pending_reminders,
    get_templates,
    mark_delivery_confirmed,
)

# استيراد Twilio إذا كان موجوداً
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

# إعداد السجل
logger = logging.getLogger(__name__)

# المجلد الحالي
current_dir = Path(__file__).parent.parent.absolute()

# الحصول على بيانات Twilio من متغيرات البيئة
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

def can_send_twilio_messages() -> bool:
    """
    التحقق مما إذا كان يمكن إرسال رسائل Twilio
    
    العائد:
        True إذا كان يمكن إرسال رسائل Twilio، False خلاف ذلك
    """
    return TWILIO_AVAILABLE and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER

async def confirm_delivery_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر تأكيد التسليم /confirm"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.message.reply_text(
            "عذراً، هذا الأمر متاح للمسؤولين فقط."
        )
        return
    
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "الرجاء توفير معرّف الإشعار بعد الأمر، مثل: /confirm abc123"
        )
        return
    
    notification_id = context.args[0]
    
    # الحصول على الإشعار
    notification = get_notification(notification_id)
    
    if not notification:
        await update.message.reply_text(
            f"لم يتم العثور على إشعار بالمعرّف '{notification_id}'."
        )
        return
    
    # تعليم الإشعار بأنه تم تأكيد التسليم
    if mark_delivery_confirmed(notification_id):
        await update.message.reply_text(
            f"تم تأكيد تسليم الإشعار لـ {notification['customer_name']} بنجاح."
        )
    else:
        await update.message.reply_text(
            "حدث خطأ أثناء تأكيد التسليم. الرجاء المحاولة مرة أخرى."
        )

async def send_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر إرسال تذكير /remind"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.message.reply_text(
            "عذراً، هذا الأمر متاح للمسؤولين فقط."
        )
        return
    
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "الرجاء توفير معرّف الإشعار بعد الأمر، مثل: /remind abc123"
        )
        return
    
    notification_id = context.args[0]
    
    # الحصول على الإشعار
    notification = get_notification(notification_id)
    
    if not notification:
        await update.message.reply_text(
            f"لم يتم العثور على إشعار بالمعرّف '{notification_id}'."
        )
        return
    
    # إرسال التذكير
    success = await send_reminder(context, notification)
    
    if success:
        # تعليم الإشعار بأنه تم إرسال تذكير له
        mark_reminder_sent(notification_id)
        
        await update.message.reply_text(
            f"تم إرسال تذكير للعميل {notification['customer_name']} بنجاح."
        )
    else:
        await update.message.reply_text(
            "حدث خطأ أثناء إرسال التذكير. الرجاء التأكد من تكوين Twilio بشكل صحيح."
        )

async def verify_delivery_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر التحقق من التسليم /verify"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.message.reply_text(
            "عذراً، هذا الأمر متاح للمسؤولين فقط."
        )
        return
    
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "الرجاء توفير معرّف الإشعار بعد الأمر، مثل: /verify abc123"
        )
        return
    
    notification_id = context.args[0]
    
    # الحصول على الإشعار
    notification = get_notification(notification_id)
    
    if not notification:
        await update.message.reply_text(
            f"لم يتم العثور على إشعار بالمعرّف '{notification_id}'."
        )
        return
    
    # إرسال رسالة التحقق
    success = await send_verification(context, notification)
    
    if success:
        await update.message.reply_text(
            f"تم إرسال رسالة تحقق للعميل {notification['customer_name']} بنجاح."
        )
    else:
        await update.message.reply_text(
            "حدث خطأ أثناء إرسال رسالة التحقق. الرجاء التأكد من تكوين Twilio بشكل صحيح."
        )

async def check_for_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """فحص الإشعارات التي تحتاج إلى إرسال تذكير"""
    # الحصول على قائمة الإشعارات التي تحتاج إلى تذكير
    pending_reminders = get_pending_reminders()
    
    if not pending_reminders:
        logger.info("لا توجد تذكيرات بحاجة إلى إرسال في هذا الوقت")
        return
    
    logger.info(f"تم العثور على {len(pending_reminders)} تذكيرات بحاجة إلى إرسال")
    
    for notification in pending_reminders:
        # إرسال التذكير
        success = await send_reminder(context, notification)
        
        if success:
            # تعليم الإشعار بأنه تم إرسال تذكير له
            mark_reminder_sent(notification["id"])
            logger.info(f"تم إرسال تذكير للعميل {notification['customer_name']} بنجاح")
        else:
            logger.error(f"حدث خطأ أثناء إرسال تذكير للعميل {notification['customer_name']}")

async def send_reminder(context: ContextTypes.DEFAULT_TYPE, notification: Dict[str, Any]) -> bool:
    """
    إرسال تذكير للعميل
    
    المعلمات:
        context: سياق المعالج
        notification: بيانات الإشعار
        
    العائد:
        True إذا تم إرسال التذكير بنجاح، False خلاف ذلك
    """
    try:
        # الحصول على قالب الرسالة
        templates = get_templates()
        template = templates.get("sms_template", "")
        
        # استبدال المتغيرات في القالب
        message = template.replace("{customer_name}", notification["customer_name"])
        message = message.replace("{notification_id}", notification["id"][:8])
        message = message.replace("{phone_number}", notification["phone_number"])
        
        # إرسال رسالة Twilio إذا كان متاحاً
        if can_send_twilio_messages():
            try:
                client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                
                # إرسال الرسالة النصية
                twilio_message = client.messages.create(
                    body=message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=notification["phone_number"]
                )
                
                logger.info(f"تم إرسال رسالة تذكير عبر Twilio بنجاح: {twilio_message.sid}")
                
                # إرسال الصورة إذا كانت موجودة
                try:
                    image_path = f"{current_dir}/{notification['image_path']}"
                    if os.path.exists(image_path):
                        media_message = client.messages.create(
                            body=f"صورة الإشعار لـ {notification['customer_name']}",
                            from_=TWILIO_PHONE_NUMBER,
                            to=notification["phone_number"],
                            media_url=[f"file://{image_path}"]
                        )
                        
                        logger.info(f"تم إرسال صورة إشعار عبر Twilio بنجاح: {media_message.sid}")
                except Exception as e:
                    logger.error(f"حدث خطأ أثناء إرسال صورة الإشعار عبر Twilio: {e}")
            except Exception as e:
                logger.error(f"حدث خطأ أثناء إرسال رسالة Twilio: {e}")
                return False
        
        # إرسال رسالة على التيليجرام للمسؤولين
        admins = []  # هنا يجب الحصول على قائمة المسؤولين
        
        for admin_id in admins:
            try:
                # إرسال رسالة تذكير
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"تم إرسال تذكير للعميل:\n\n"
                         f"الاسم: {notification['customer_name']}\n"
                         f"الهاتف: {notification['phone_number']}\n"
                         f"رمز الإشعار: {notification['id'][:8]}"
                )
                
                # إرسال صورة الإشعار
                try:
                    with open(f"{current_dir}/{notification['image_path']}", "rb") as image_file:
                        await context.bot.send_photo(
                            chat_id=admin_id,
                            photo=image_file,
                            caption=f"صورة الإشعار لـ {notification['customer_name']}"
                        )
                except Exception as e:
                    logger.error(f"حدث خطأ أثناء إرسال صورة الإشعار للمسؤول: {e}")
            except Exception as e:
                logger.error(f"حدث خطأ أثناء إرسال رسالة للمسؤول: {e}")
        
        return True
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إرسال التذكير: {e}")
        return False

async def send_verification(context: ContextTypes.DEFAULT_TYPE, notification: Dict[str, Any]) -> bool:
    """
    إرسال رسالة تحقق من التسليم للعميل
    
    المعلمات:
        context: سياق المعالج
        notification: بيانات الإشعار
        
    العائد:
        True إذا تم إرسال رسالة التحقق بنجاح، False خلاف ذلك
    """
    try:
        # الحصول على قالب الرسالة
        templates = get_templates()
        template = templates.get("verification_template", "")
        
        # استبدال المتغيرات في القالب
        message = template.replace("{customer_name}", notification["customer_name"])
        message = message.replace("{notification_id}", notification["id"][:8])
        message = message.replace("{phone_number}", notification["phone_number"])
        
        # إرسال رسالة Twilio إذا كان متاحاً
        if can_send_twilio_messages():
            try:
                client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                
                # إرسال الرسالة النصية
                twilio_message = client.messages.create(
                    body=message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=notification["phone_number"]
                )
                
                logger.info(f"تم إرسال رسالة تحقق عبر Twilio بنجاح: {twilio_message.sid}")
            except Exception as e:
                logger.error(f"حدث خطأ أثناء إرسال رسالة Twilio: {e}")
                return False
        
        # إرسال رسالة على التيليجرام للمسؤولين
        admins = []  # هنا يجب الحصول على قائمة المسؤولين
        
        for admin_id in admins:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"تم إرسال رسالة تحقق للعميل:\n\n"
                         f"الاسم: {notification['customer_name']}\n"
                         f"الهاتف: {notification['phone_number']}\n"
                         f"رمز الإشعار: {notification['id'][:8]}"
                )
            except Exception as e:
                logger.error(f"حدث خطأ أثناء إرسال رسالة للمسؤول: {e}")
        
        return True
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إرسال رسالة التحقق: {e}")
        return False

def get_notification_handlers() -> List[Any]:
    """
    الحصول على جميع معالجات الإشعارات
    
    العائد:
        قائمة بمعالجات الإشعارات
    """
    # قائمة بجميع معالجات الإشعارات
    handlers = [
        # أوامر تأكيد التسليم
        CommandHandler("confirm", confirm_delivery_command),
        CommandHandler("verify", verify_delivery_command),
        CommandHandler("remind", send_reminder_command),
    ]
    
    return handlers