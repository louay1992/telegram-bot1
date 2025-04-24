"""
معالجات المسؤول - تدير التفاعلات مع مستخدمي المسؤول
"""

import logging
import os
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

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
    is_admin,
    add_admin,
    remove_admin,
    get_admins,
    reset_admins,
    add_notification,
    get_notifications,
    get_notification,
    update_notification,
    delete_notification,
    search_notifications_by_name,
    search_notifications_by_phone,
    get_templates,
    update_template,
)

# معرّفات حالات المحادثة
(
    WAITING_FOR_NAME,
    WAITING_FOR_PHONE,
    WAITING_FOR_IMAGE,
    WAITING_FOR_DAYS,
    WAITING_FOR_ADMIN_ID,
) = range(5)

# معرّفات حالات المحادثة لإدارة القوالب
(
    WAITING_FOR_TEMPLATE_TEXT,
    WAITING_FOR_WELCOME_TEMPLATE_TEXT,
    WAITING_FOR_VERIFICATION_TEMPLATE_TEXT,
) = range(3)

# إعداد السجل
logger = logging.getLogger(__name__)

# المجلد الحالي
current_dir = Path(__file__).parent.parent.absolute()
IMAGES_DIR = current_dir / "data" / "images"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر البدء /start"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # التحقق من قائمة المسؤولين
    admins = get_admins()
    
    # إذا كانت القائمة فارغة، فإن أول مستخدم يصبح المسؤول الرئيسي
    if not admins:
        add_admin(user_id)
        await update.message.reply_text(
            f"مرحباً {user_name}! تم تعيينك كمسؤول رئيسي للنظام.\n"
            "يمكنك استخدام /admin للوصول إلى لوحة تحكم المسؤول."
        )
        logger.info(f"تم تعيين {user_id} كمسؤول رئيسي")
        return
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if is_admin(user_id):
        keyboard = [
            [
                InlineKeyboardButton("📋 قائمة الإشعارات", callback_data="list_notifications"),
                InlineKeyboardButton("➕ إضافة إشعار", callback_data="add_notification"),
            ],
            [
                InlineKeyboardButton("🔍 بحث بالاسم", callback_data="search_by_name"),
                InlineKeyboardButton("📱 بحث برقم الهاتف", callback_data="search_by_phone"),
            ],
            [
                InlineKeyboardButton("👥 إدارة المسؤولين", callback_data="manage_admins"),
                InlineKeyboardButton("✉️ قوالب الرسائل", callback_data="manage_templates"),
            ],
            [
                InlineKeyboardButton("❓ مساعدة", callback_data="admin_help"),
            ],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"مرحباً {user_name}! أنت مسؤول في نظام إشعارات الشحن.\n"
            "الرجاء اختيار أحد الخيارات أدناه:",
            reply_markup=reply_markup,
        )
    else:
        # رسالة للمستخدمين العاديين
        await update.message.reply_text(
            f"مرحباً {user_name}! هذا بوت إشعارات الشحن.\n"
            "يمكنك البحث عن إشعاراتك باستخدام أمر /search متبوعًا برقم هاتفك."
        )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة أمر المسؤول /admin"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.message.reply_text(
            "عذراً، هذا الأمر متاح للمسؤولين فقط."
        )
        return
    
    # إنشاء لوحة تحكم المسؤول
    keyboard = [
        [
            InlineKeyboardButton("📋 قائمة الإشعارات", callback_data="list_notifications"),
            InlineKeyboardButton("➕ إضافة إشعار", callback_data="add_notification"),
        ],
        [
            InlineKeyboardButton("🔍 بحث بالاسم", callback_data="search_by_name"),
            InlineKeyboardButton("📱 بحث برقم الهاتف", callback_data="search_by_phone"),
        ],
        [
            InlineKeyboardButton("👥 إدارة المسؤولين", callback_data="manage_admins"),
            InlineKeyboardButton("✉️ قوالب الرسائل", callback_data="manage_templates"),
        ],
        [
            InlineKeyboardButton("❓ مساعدة", callback_data="admin_help"),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "لوحة تحكم المسؤول. الرجاء اختيار أحد الخيارات أدناه:",
        reply_markup=reply_markup,
    )

async def add_notification_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية إضافة إشعار جديد"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.message.reply_text(
            "عذراً، هذا الأمر متاح للمسؤولين فقط."
        )
        return ConversationHandler.END
    
    # طلب اسم العميل
    await update.message.reply_text(
        "الرجاء إدخال اسم العميل:"
    )
    return WAITING_FOR_NAME

async def received_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اسم العميل المستلم"""
    context.user_data["customer_name"] = update.message.text
    
    # طلب رقم الهاتف
    await update.message.reply_text(
        "الرجاء إدخال رقم هاتف العميل:"
    )
    return WAITING_FOR_PHONE

async def received_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة رقم الهاتف المستلم"""
    phone_number = update.message.text
    
    # تنسيق رقم الهاتف وإضافة رمز البلد إذا لزم الأمر
    # تحقق من وجود رمز البلد
    if phone_number.startswith("+"):
        # الرقم يحتوي على رمز البلد بالفعل
        pass
    elif phone_number.startswith("09") or phone_number.startswith("9"):
        # إضافة رمز البلد لسوريا
        if phone_number.startswith("0"):
            phone_number = "+963" + phone_number[1:]
        else:
            phone_number = "+963" + phone_number
    elif phone_number.startswith("05") or phone_number.startswith("5"):
        # إضافة رمز البلد لتركيا
        if phone_number.startswith("0"):
            phone_number = "+90" + phone_number[1:]
        else:
            phone_number = "+90" + phone_number
    
    context.user_data["phone_number"] = phone_number
    
    # طلب صورة الإشعار
    await update.message.reply_text(
        "الرجاء إرسال صورة الإشعار:"
    )
    return WAITING_FOR_IMAGE

async def received_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة صورة الإشعار المستلمة"""
    # الحصول على أكبر نسخة من الصورة
    photo = update.message.photo[-1]
    
    # إنشاء معرّف فريد للصورة
    file_id = photo.file_id
    
    # تحميل الصورة
    IMAGES_DIR.mkdir(exist_ok=True, parents=True)
    file = await context.bot.get_file(file_id)
    image_uuid = str(uuid.uuid4())
    image_path = f"data/images/{image_uuid}.jpg"
    await file.download_to_drive(f"{current_dir}/{image_path}")
    
    context.user_data["image_path"] = image_path
    
    # طلب عدد أيام التذكير
    await update.message.reply_text(
        "الرجاء إدخال عدد أيام التذكير (سيتم إرسال رسالة تذكير بعد هذا العدد من الأيام):"
    )
    return WAITING_FOR_DAYS

async def received_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة عدد أيام التذكير المستلم"""
    try:
        days = int(update.message.text)
        if days < 1:
            await update.message.reply_text(
                "عذراً، يجب أن يكون عدد الأيام أكبر من أو يساوي 1. الرجاء المحاولة مرة أخرى:"
            )
            return WAITING_FOR_DAYS
        
        # إضافة الإشعار
        notification = add_notification(
            customer_name=context.user_data["customer_name"],
            phone_number=context.user_data["phone_number"],
            image_path=context.user_data["image_path"],
            reminder_days=days,
        )
        
        # إرسال رسالة تأكيد
        await update.message.reply_text(
            f"تم إضافة الإشعار بنجاح!\n\n"
            f"الاسم: {notification['customer_name']}\n"
            f"الهاتف: {notification['phone_number']}\n"
            f"رمز الإشعار: {notification['id'][:8]}\n"
            f"التذكير بعد: {days} يوم"
        )
        
        # إرسال صورة الإشعار المضافة
        with open(f"{current_dir}/{notification['image_path']}", "rb") as image_file:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_file,
                caption=f"صورة الإشعار لـ {notification['customer_name']}"
            )
        
        # مسح بيانات المستخدم
        context.user_data.clear()
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "عذراً، يجب إدخال رقم صحيح. الرجاء المحاولة مرة أخرى:"
        )
        return WAITING_FOR_DAYS

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء المحادثة الحالية"""
    await update.message.reply_text(
        "تم إلغاء العملية الحالية."
    )
    context.user_data.clear()
    return ConversationHandler.END

async def list_notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض قائمة الإشعارات"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.message.reply_text(
            "عذراً، هذا الأمر متاح للمسؤولين فقط."
        )
        return
    
    # الحصول على قائمة الإشعارات
    notifications = get_notifications()
    
    if not notifications:
        await update.message.reply_text(
            "لا توجد إشعارات حالياً."
        )
        return
    
    # تحديد عدد الإشعارات لكل صفحة
    ITEMS_PER_PAGE = 5
    total_pages = (len(notifications) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    # تحديد الصفحة الحالية
    current_page = 1
    context.user_data["current_page"] = current_page
    context.user_data["total_pages"] = total_pages
    
    # عرض الإشعارات في الصفحة الحالية
    await show_notifications_page(update, context)

async def show_notifications_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض صفحة من قائمة الإشعارات"""
    # الحصول على معلومات الصفحة
    current_page = context.user_data.get("current_page", 1)
    total_pages = context.user_data.get("total_pages", 1)
    
    # الحصول على قائمة الإشعارات
    notifications = get_notifications()
    
    # تحديد عدد الإشعارات لكل صفحة
    ITEMS_PER_PAGE = 5
    start_idx = (current_page - 1) * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(notifications))
    
    # إنشاء رسالة عرض الإشعارات
    message = f"قائمة الإشعارات (الصفحة {current_page} من {total_pages}):\n\n"
    
    for i, notification in enumerate(notifications[start_idx:end_idx], start=1):
        message += f"{i}. {notification['customer_name']} - {notification['phone_number']}\n"
        message += f"   رمز: {notification['id'][:8]}\n"
        
        # تحويل التاريخ إلى كائن datetime
        created_at = datetime.fromisoformat(notification['created_at'])
        message += f"   تاريخ الإنشاء: {created_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        # إضافة معلومات التذكير
        reminder_time = datetime.fromisoformat(notification['reminder_time'])
        reminder_sent = notification.get('reminder_sent', False)
        message += f"   التذكير: {reminder_time.strftime('%Y-%m-%d %H:%M')}"
        message += " (تم الإرسال)" if reminder_sent else " (لم يتم الإرسال بعد)"
        message += "\n\n"
    
    # إنشاء أزرار التنقل
    keyboard = []
    
    # إضافة أزرار السابق والتالي
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data="prev_page"))
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data="next_page"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # إضافة زر العودة
    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="back_to_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تحديث الرسالة إذا كانت من استعلام زر، وإلا إرسال رسالة جديدة
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup)

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة استعلامات أزرار المسؤول"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await query.edit_message_text(
            "عذراً، هذا الإجراء متاح للمسؤولين فقط."
        )
        return
    
    # معالجة الاستعلام بناءً على البيانات
    if query.data == "list_notifications":
        await list_notifications_command(update, context)
    elif query.data == "add_notification":
        await query.edit_message_text(
            "لإضافة إشعار جديد، الرجاء إدخال اسم العميل:"
        )
        context.user_data["conversation_type"] = "add_notification"
        context.user_data["state"] = WAITING_FOR_NAME
    elif query.data == "prev_page":
        # الانتقال إلى الصفحة السابقة
        current_page = context.user_data.get("current_page", 1)
        if current_page > 1:
            context.user_data["current_page"] = current_page - 1
            await show_notifications_page(update, context)
    elif query.data == "next_page":
        # الانتقال إلى الصفحة التالية
        current_page = context.user_data.get("current_page", 1)
        total_pages = context.user_data.get("total_pages", 1)
        if current_page < total_pages:
            context.user_data["current_page"] = current_page + 1
            await show_notifications_page(update, context)
    elif query.data == "back_to_admin":
        # العودة إلى لوحة تحكم المسؤول
        keyboard = [
            [
                InlineKeyboardButton("📋 قائمة الإشعارات", callback_data="list_notifications"),
                InlineKeyboardButton("➕ إضافة إشعار", callback_data="add_notification"),
            ],
            [
                InlineKeyboardButton("🔍 بحث بالاسم", callback_data="search_by_name"),
                InlineKeyboardButton("📱 بحث برقم الهاتف", callback_data="search_by_phone"),
            ],
            [
                InlineKeyboardButton("👥 إدارة المسؤولين", callback_data="manage_admins"),
                InlineKeyboardButton("✉️ قوالب الرسائل", callback_data="manage_templates"),
            ],
            [
                InlineKeyboardButton("❓ مساعدة", callback_data="admin_help"),
            ],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "لوحة تحكم المسؤول. الرجاء اختيار أحد الخيارات أدناه:",
            reply_markup=reply_markup,
        )
    elif query.data == "admin_help":
        # عرض مساعدة المسؤول
        help_text = (
            "دليل مساعدة المسؤول:\n\n"
            "- استخدم 'قائمة الإشعارات' لعرض جميع الإشعارات المسجلة.\n"
            "- استخدم 'إضافة إشعار' لإضافة إشعار جديد.\n"
            "- استخدم 'بحث بالاسم' للبحث عن الإشعارات حسب اسم العميل.\n"
            "- استخدم 'بحث برقم الهاتف' للبحث عن الإشعارات حسب رقم هاتف العميل.\n"
            "- استخدم 'إدارة المسؤولين' لإضافة أو إزالة مسؤولين.\n"
            "- استخدم 'قوالب الرسائل' لتعديل قوالب الرسائل المستخدمة في النظام.\n\n"
            "يمكنك دائمًا استخدام /admin للعودة إلى لوحة تحكم المسؤول."
        )
        
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="back_to_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(help_text, reply_markup=reply_markup)
    elif query.data == "manage_admins":
        # إدارة المسؤولين
        await manage_admins_command(update, context)
    elif query.data == "manage_templates":
        # إدارة قوالب الرسائل
        await manage_templates_command(update, context)
    elif query.data == "search_by_name":
        # البحث بالاسم
        await query.edit_message_text(
            "الرجاء إدخال اسم العميل للبحث عنه:"
        )
        context.user_data["conversation_type"] = "search_by_name"
        context.user_data["state"] = "waiting_for_search_name"
    elif query.data == "search_by_phone":
        # البحث برقم الهاتف
        await query.edit_message_text(
            "الرجاء إدخال رقم هاتف العميل للبحث عنه:"
        )
        context.user_data["conversation_type"] = "search_by_phone"
        context.user_data["state"] = "waiting_for_search_phone"

async def manage_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إدارة المسؤولين"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "عذراً، هذا الإجراء متاح للمسؤولين فقط."
            )
        else:
            await update.message.reply_text(
                "عذراً، هذا الإجراء متاح للمسؤولين فقط."
            )
        return
    
    # الحصول على قائمة المسؤولين
    admins = get_admins()
    
    # إنشاء رسالة عرض المسؤولين
    message = "إدارة المسؤولين:\n\n"
    
    if admins:
        message += "المسؤولون الحاليون:\n"
        for i, admin_id in enumerate(admins, start=1):
            message += f"{i}. {admin_id}\n"
    else:
        message += "لا يوجد مسؤولون حالياً.\n"
    
    # إنشاء أزرار إدارة المسؤولين
    keyboard = [
        [
            InlineKeyboardButton("➕ إضافة مسؤول", callback_data="add_admin"),
            InlineKeyboardButton("❌ إزالة مسؤول", callback_data="remove_admin"),
        ],
        [
            InlineKeyboardButton("🗑️ إعادة تعيين المسؤولين", callback_data="reset_admins"),
        ],
        [
            InlineKeyboardButton("🔙 العودة", callback_data="back_to_admin"),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تحديث الرسالة إذا كانت من استعلام زر، وإلا إرسال رسالة جديدة
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup)

async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية إضافة مسؤول جديد"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.callback_query.edit_message_text(
            "عذراً، هذا الإجراء متاح للمسؤولين فقط."
        )
        return ConversationHandler.END
    
    # طلب معرّف المسؤول الجديد
    await update.callback_query.edit_message_text(
        "الرجاء إدخال معرّف المسؤول الجديد:"
    )
    context.user_data["admin_action"] = "add"
    return WAITING_FOR_ADMIN_ID

async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية إزالة مسؤول"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.callback_query.edit_message_text(
            "عذراً، هذا الإجراء متاح للمسؤولين فقط."
        )
        return ConversationHandler.END
    
    # طلب معرّف المسؤول المراد إزالته
    await update.callback_query.edit_message_text(
        "الرجاء إدخال معرّف المسؤول المراد إزالته:"
    )
    context.user_data["admin_action"] = "remove"
    return WAITING_FOR_ADMIN_ID

async def reset_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إعادة تعيين جميع المسؤولين"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.callback_query.edit_message_text(
            "عذراً، هذا الإجراء متاح للمسؤولين فقط."
        )
        return
    
    # إعادة تعيين المسؤولين
    reset_admins()
    
    # إضافة المستخدم الحالي كمسؤول رئيسي
    add_admin(user_id)
    
    # إرسال رسالة تأكيد
    await update.callback_query.edit_message_text(
        "تم إعادة تعيين قائمة المسؤولين. أنت الآن المسؤول الرئيسي الوحيد.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="manage_admins")]])
    )

async def process_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة معرّف المسؤول المستلم"""
    admin_id_text = update.message.text
    
    try:
        admin_id = int(admin_id_text)
        
        # معالجة الإجراء بناءً على نوع العملية
        if context.user_data.get("admin_action") == "add":
            # إضافة مسؤول جديد
            if add_admin(admin_id):
                await update.message.reply_text(
                    f"تم إضافة المسؤول {admin_id} بنجاح.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="manage_admins")]])
                )
            else:
                await update.message.reply_text(
                    "حدث خطأ أثناء إضافة المسؤول. الرجاء المحاولة مرة أخرى.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="manage_admins")]])
                )
        elif context.user_data.get("admin_action") == "remove":
            # إزالة مسؤول
            if admin_id == update.effective_user.id:
                await update.message.reply_text(
                    "لا يمكنك إزالة نفسك من قائمة المسؤولين.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="manage_admins")]])
                )
            elif remove_admin(admin_id):
                await update.message.reply_text(
                    f"تم إزالة المسؤول {admin_id} بنجاح.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="manage_admins")]])
                )
            else:
                await update.message.reply_text(
                    "حدث خطأ أثناء إزالة المسؤول. الرجاء التأكد من أن المعرّف صحيح والمحاولة مرة أخرى.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="manage_admins")]])
                )
        
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "عذراً، يجب إدخال معرّف صالح (رقم صحيح). الرجاء المحاولة مرة أخرى:"
        )
        return WAITING_FOR_ADMIN_ID

async def handle_admin_manage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """معالجة استعلامات أزرار إدارة المسؤولين"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await query.edit_message_text(
            "عذراً، هذا الإجراء متاح للمسؤولين فقط."
        )
        return None
    
    # معالجة الاستعلام بناءً على البيانات
    if query.data == "add_admin":
        return await add_admin_command(update, context)
    elif query.data == "remove_admin":
        return await remove_admin_command(update, context)
    elif query.data == "reset_admins":
        await reset_admins_command(update, context)
    elif query.data == "manage_admins":
        await manage_admins_command(update, context)
    
    return None

async def manage_templates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إدارة قوالب الرسائل"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "عذراً، هذا الإجراء متاح للمسؤولين فقط."
            )
        else:
            await update.message.reply_text(
                "عذراً، هذا الإجراء متاح للمسؤولين فقط."
            )
        return
    
    # الحصول على قوالب الرسائل
    templates = get_templates()
    
    # إنشاء رسالة عرض القوالب
    message = "إدارة قوالب الرسائل:\n\n"
    message += "متغيرات القوالب المتاحة:\n"
    message += "{customer_name}: اسم العميل\n"
    message += "{notification_id}: معرّف الإشعار\n"
    message += "{phone_number}: رقم هاتف العميل\n\n"
    
    message += "القوالب الحالية:\n\n"
    
    # عرض القوالب
    message += "1. قالب الرسالة النصية:\n"
    message += f"{templates.get('sms_template', 'غير محدد')}\n\n"
    
    message += "2. قالب رسالة الترحيب:\n"
    message += f"{templates.get('welcome_template', 'غير محدد')}\n\n"
    
    message += "3. قالب رسالة التحقق:\n"
    message += f"{templates.get('verification_template', 'غير محدد')}\n\n"
    
    # إنشاء أزرار إدارة القوالب
    keyboard = [
        [
            InlineKeyboardButton("📝 تعديل الرسالة النصية", callback_data="edit_sms_template"),
        ],
        [
            InlineKeyboardButton("📝 تعديل رسالة الترحيب", callback_data="edit_welcome_template"),
        ],
        [
            InlineKeyboardButton("📝 تعديل رسالة التحقق", callback_data="edit_verification_template"),
        ],
        [
            InlineKeyboardButton("🔙 العودة", callback_data="back_to_admin"),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # تحديث الرسالة إذا كانت من استعلام زر، وإلا إرسال رسالة جديدة
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup)

async def edit_sms_template_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية تعديل قالب الرسالة النصية"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.callback_query.edit_message_text(
            "عذراً، هذا الإجراء متاح للمسؤولين فقط."
        )
        return ConversationHandler.END
    
    # الحصول على القالب الحالي
    templates = get_templates()
    current_template = templates.get("sms_template", "")
    
    # طلب نص القالب الجديد
    await update.callback_query.edit_message_text(
        f"الرجاء إدخال نص قالب الرسالة النصية الجديد:\n\n"
        f"القالب الحالي:\n{current_template}\n\n"
        f"متغيرات القوالب المتاحة:\n"
        f"{{customer_name}}: اسم العميل\n"
        f"{{notification_id}}: معرّف الإشعار\n"
        f"{{phone_number}}: رقم هاتف العميل"
    )
    context.user_data["template_action"] = "sms_template"
    return WAITING_FOR_TEMPLATE_TEXT

async def edit_welcome_template_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية تعديل قالب رسالة الترحيب"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.callback_query.edit_message_text(
            "عذراً، هذا الإجراء متاح للمسؤولين فقط."
        )
        return ConversationHandler.END
    
    # الحصول على القالب الحالي
    templates = get_templates()
    current_template = templates.get("welcome_template", "")
    
    # طلب نص القالب الجديد
    await update.callback_query.edit_message_text(
        f"الرجاء إدخال نص قالب رسالة الترحيب الجديد:\n\n"
        f"القالب الحالي:\n{current_template}\n\n"
        f"متغيرات القوالب المتاحة:\n"
        f"{{customer_name}}: اسم العميل\n"
        f"{{notification_id}}: معرّف الإشعار\n"
        f"{{phone_number}}: رقم هاتف العميل"
    )
    context.user_data["template_action"] = "welcome_template"
    return WAITING_FOR_WELCOME_TEMPLATE_TEXT

async def edit_verification_template_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء عملية تعديل قالب رسالة التحقق"""
    user_id = update.effective_user.id
    
    # التحقق مما إذا كان المستخدم مسؤولاً
    if not is_admin(user_id):
        await update.callback_query.edit_message_text(
            "عذراً، هذا الإجراء متاح للمسؤولين فقط."
        )
        return ConversationHandler.END
    
    # الحصول على القالب الحالي
    templates = get_templates()
    current_template = templates.get("verification_template", "")
    
    # طلب نص القالب الجديد
    await update.callback_query.edit_message_text(
        f"الرجاء إدخال نص قالب رسالة التحقق الجديد:\n\n"
        f"القالب الحالي:\n{current_template}\n\n"
        f"متغيرات القوالب المتاحة:\n"
        f"{{customer_name}}: اسم العميل\n"
        f"{{notification_id}}: معرّف الإشعار\n"
        f"{{phone_number}}: رقم هاتف العميل"
    )
    context.user_data["template_action"] = "verification_template"
    return WAITING_FOR_VERIFICATION_TEMPLATE_TEXT

async def process_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة نص القالب المستلم"""
    template_text = update.message.text
    template_type = context.user_data.get("template_action")
    
    # تحديث القالب
    if update_template(template_type, template_text):
        await update.message.reply_text(
            f"تم تحديث قالب {template_type} بنجاح.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="manage_templates")]])
        )
    else:
        await update.message.reply_text(
            f"حدث خطأ أثناء تحديث قالب {template_type}. الرجاء المحاولة مرة أخرى.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="manage_templates")]])
        )
    
    return ConversationHandler.END

async def process_search_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة البحث عن إشعار بواسطة اسم العميل"""
    search_name = update.message.text
    
    # البحث عن الإشعارات
    results = search_notifications_by_name(search_name)
    
    if not results:
        await update.message.reply_text(
            f"لم يتم العثور على إشعارات تطابق الاسم '{search_name}'.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="back_to_admin")]])
        )
        return
    
    # عرض نتائج البحث
    message = f"تم العثور على {len(results)} إشعارات تطابق الاسم '{search_name}':\n\n"
    
    for i, notification in enumerate(results, start=1):
        message += f"{i}. {notification['customer_name']} - {notification['phone_number']}\n"
        message += f"   رمز: {notification['id'][:8]}\n"
        
        # تحويل التاريخ إلى كائن datetime
        created_at = datetime.fromisoformat(notification['created_at'])
        message += f"   تاريخ الإنشاء: {created_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        # إضافة معلومات التذكير
        reminder_time = datetime.fromisoformat(notification['reminder_time'])
        reminder_sent = notification.get('reminder_sent', False)
        message += f"   التذكير: {reminder_time.strftime('%Y-%m-%d %H:%M')}"
        message += " (تم الإرسال)" if reminder_sent else " (لم يتم الإرسال بعد)"
        message += "\n\n"
    
    # إضافة زر العودة
    keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="back_to_admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup)
    
    # إرسال صور الإشعارات
    for notification in results:
        try:
            with open(f"{current_dir}/{notification['image_path']}", "rb") as image_file:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=image_file,
                    caption=f"صورة الإشعار لـ {notification['customer_name']} ({notification['id'][:8]})"
                )
        except Exception as e:
            logger.error(f"Error sending notification image: {e}")
            await update.message.reply_text(f"حدث خطأ أثناء إرسال صورة الإشعار {notification['id'][:8]}")

async def process_search_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة البحث عن إشعار بواسطة رقم الهاتف"""
    search_phone = update.message.text
    
    # تنظيف رقم الهاتف من الأحرف غير الرقمية
    clean_phone = ''.join(filter(str.isdigit, search_phone))
    
    # البحث عن الإشعارات
    results = search_notifications_by_phone(clean_phone)
    
    if not results:
        await update.message.reply_text(
            f"لم يتم العثور على إشعارات تطابق رقم الهاتف '{search_phone}'.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="back_to_admin")]])
        )
        return
    
    # عرض نتائج البحث
    message = f"تم العثور على {len(results)} إشعارات تطابق رقم الهاتف '{search_phone}':\n\n"
    
    for i, notification in enumerate(results, start=1):
        message += f"{i}. {notification['customer_name']} - {notification['phone_number']}\n"
        message += f"   رمز: {notification['id'][:8]}\n"
        
        # تحويل التاريخ إلى كائن datetime
        created_at = datetime.fromisoformat(notification['created_at'])
        message += f"   تاريخ الإنشاء: {created_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        # إضافة معلومات التذكير
        reminder_time = datetime.fromisoformat(notification['reminder_time'])
        reminder_sent = notification.get('reminder_sent', False)
        message += f"   التذكير: {reminder_time.strftime('%Y-%m-%d %H:%M')}"
        message += " (تم الإرسال)" if reminder_sent else " (لم يتم الإرسال بعد)"
        message += "\n\n"
    
    # إضافة زر العودة
    keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="back_to_admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup)
    
    # إرسال صور الإشعارات
    for notification in results:
        try:
            with open(f"{current_dir}/{notification['image_path']}", "rb") as image_file:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=image_file,
                    caption=f"صورة الإشعار لـ {notification['customer_name']} ({notification['id'][:8]})"
                )
        except Exception as e:
            logger.error(f"Error sending notification image: {e}")
            await update.message.reply_text(f"حدث خطأ أثناء إرسال صورة الإشعار {notification['id'][:8]}")

def get_admin_handlers() -> List[Any]:
    """
    الحصول على جميع معالجات المسؤول
    
    العائد:
        قائمة بمعالجات المسؤول
    """
    # معالج المحادثة لإضافة إشعار
    add_notification_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_notification_command, pattern="^add_notification$"),
            CommandHandler("add", add_notification_command),
        ],
        states={
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_name)],
            WAITING_FOR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_phone)],
            WAITING_FOR_IMAGE: [MessageHandler(filters.PHOTO, received_image)],
            WAITING_FOR_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    
    # معالج المحادثة لإدارة المسؤولين
    admin_management_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_admin_command, pattern="^add_admin$"),
            CallbackQueryHandler(remove_admin_command, pattern="^remove_admin$"),
        ],
        states={
            WAITING_FOR_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_admin_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    
    # معالج المحادثة لإدارة قالب الرسالة النصية
    sms_template_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_sms_template_command, pattern="^edit_sms_template$"),
        ],
        states={
            WAITING_FOR_TEMPLATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_template_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    
    # معالج المحادثة لإدارة قالب رسالة الترحيب
    welcome_template_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_welcome_template_command, pattern="^edit_welcome_template$"),
        ],
        states={
            WAITING_FOR_WELCOME_TEMPLATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_template_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    
    # معالج المحادثة لإدارة قالب رسالة التحقق
    verification_template_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_verification_template_command, pattern="^edit_verification_template$"),
        ],
        states={
            WAITING_FOR_VERIFICATION_TEMPLATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_template_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    
    # معالج المحادثة للبحث
    search_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(lambda u, c: u.callback_query.edit_message_text("الرجاء إدخال اسم العميل للبحث عنه:") or None, pattern="^search_by_name$"),
            CallbackQueryHandler(lambda u, c: u.callback_query.edit_message_text("الرجاء إدخال رقم هاتف العميل للبحث عنه:") or None, pattern="^search_by_phone$"),
        ],
        states={
            "waiting_for_search_name": [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search_name)],
            "waiting_for_search_phone": [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        name="search_handler",
        persistent=False,
    )
    
    # قائمة بجميع معالجات المسؤول
    handlers = [
        # أوامر المسؤول الأساسية
        CommandHandler("start", start_command),
        CommandHandler("admin", admin_command),
        CommandHandler("list", list_notifications_command),
        
        # معالج المحادثة لإضافة إشعار
        add_notification_handler,
        
        # معالج المحادثة لإدارة المسؤولين
        admin_management_handler,
        
        # معالج المحادثة لإدارة قوالب الرسائل
        sms_template_handler,
        welcome_template_handler,
        verification_template_handler,
        
        # معالج المحادثة للبحث
        search_handler,
        
        # معالج استعلامات أزرار المسؤول العامة
        CallbackQueryHandler(handle_admin_callback, pattern="^(list_notifications|prev_page|next_page|back_to_admin|admin_help|manage_admins|manage_templates|reset_admins)$"),
        
        # معالج استعلامات أزرار إدارة المسؤولين
        CallbackQueryHandler(reset_admins_command, pattern="^reset_admins$"),
        CallbackQueryHandler(manage_admins_command, pattern="^manage_admins$"),
        
        # معالج استعلامات أزرار إدارة القوالب
        CallbackQueryHandler(manage_templates_command, pattern="^manage_templates$"),
    ]
    
    return handlers