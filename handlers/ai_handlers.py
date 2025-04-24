"""
معالجات الذكاء الاصطناعي - تدير تفاعلات الذكاء الاصطناعي
"""

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

from utils.database import is_admin, search_notifications_by_phone, add_notification

# التحقق مما إذا كانت مكتبات الذكاء الاصطناعي متاحة
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# إعداد السجل
logger = logging.getLogger(__name__)

# المجلد الحالي
current_dir = Path(__file__).parent.parent.absolute()
IMAGES_DIR = current_dir / "data" / "images"
TEMP_MEDIA_DIR = current_dir / "temp_media"

# التأكد من وجود المجلدات اللازمة
IMAGES_DIR.mkdir(exist_ok=True, parents=True)
TEMP_MEDIA_DIR.mkdir(exist_ok=True, parents=True)

# الحصول على مفاتيح API من متغيرات البيئة
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# معرّفات حالات المحادثة
(
    WAITING_FOR_CHAT,
    WAITING_FOR_IMAGE,
    WAITING_FOR_EXTRACTION_CONFIRMATION,
) = range(3)

def is_ai_available() -> bool:
    """
    التحقق مما إذا كانت ميزات الذكاء الاصطناعي متاحة
    
    العائد:
        True إذا كانت ميزات الذكاء الاصطناعي متاحة، False خلاف ذلك
    """
    return (OPENAI_AVAILABLE and OPENAI_API_KEY) or (ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY)

def get_openai_client() -> Optional[Any]:
    """
    الحصول على عميل OpenAI
    
    العائد:
        عميل OpenAI إذا كان متاحاً، None خلاف ذلك
    """
    if OPENAI_AVAILABLE and OPENAI_API_KEY:
        try:
            return OpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            logger.error(f"حدث خطأ أثناء إنشاء عميل OpenAI: {e}")
    
    return None

def get_anthropic_client() -> Optional[Any]:
    """
    الحصول على عميل Anthropic
    
    العائد:
        عميل Anthropic إذا كان متاحاً، None خلاف ذلك
    """
    if ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY:
        try:
            return Anthropic(api_key=ANTHROPIC_API_KEY)
        except Exception as e:
            logger.error(f"حدث خطأ أثناء إنشاء عميل Anthropic: {e}")
    
    return None

async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة أمر الذكاء الاصطناعي /ai"""
    if not is_ai_available():
        await update.message.reply_text(
            "عذراً، ميزات الذكاء الاصطناعي غير متاحة حالياً. الرجاء التحقق من تكوين مفاتيح API."
        )
        return ConversationHandler.END
    
    # إنشاء لوحة تحكم الذكاء الاصطناعي
    keyboard = [
        [
            InlineKeyboardButton("💬 محادثة ذكية", callback_data="ai_chat"),
            InlineKeyboardButton("🖼️ تحليل صورة", callback_data="ai_image"),
        ],
        [
            InlineKeyboardButton("❌ إلغاء", callback_data="ai_cancel"),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "مرحباً بك في واجهة الذكاء الاصطناعي! الرجاء اختيار أحد الخيارات أدناه:",
        reply_markup=reply_markup,
    )
    
    # تهيئة سياق المحادثة
    context.user_data["ai_mode"] = None
    context.user_data["ai_messages"] = []
    
    return WAITING_FOR_CHAT

async def handle_ai_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة استعلامات أزرار الذكاء الاصطناعي"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "ai_chat":
        # بدء محادثة ذكية
        await query.edit_message_text(
            "أرسل لي رسالة وسأرد عليك باستخدام الذكاء الاصطناعي.\n"
            "يمكنك استخدام هذه الميزة للاستفسار عن الشحنات أو طلب معلومات.\n\n"
            "أرسل /cancel للإلغاء."
        )
        context.user_data["ai_mode"] = "chat"
        return WAITING_FOR_CHAT
    
    elif query.data == "ai_image":
        # بدء تحليل صورة
        await query.edit_message_text(
            "الرجاء إرسال صورة الشحنة لتحليلها باستخدام الذكاء الاصطناعي.\n"
            "سأحاول استخراج المعلومات المهمة مثل اسم العميل ورقم الهاتف وتفاصيل الشحنة.\n\n"
            "أرسل /cancel للإلغاء."
        )
        context.user_data["ai_mode"] = "image"
        return WAITING_FOR_IMAGE
    
    elif query.data == "ai_cancel":
        # إلغاء الذكاء الاصطناعي
        await query.edit_message_text(
            "تم إلغاء عملية الذكاء الاصطناعي."
        )
        return ConversationHandler.END
    
    elif query.data.startswith("extract_"):
        # معالجة تأكيد استخراج معلومات الشحنة
        parts = query.data.split("_")
        if len(parts) >= 3 and parts[1] == "confirm":
            # إنشاء إشعار جديد من البيانات المستخرجة
            extracted_data = context.user_data.get("extracted_data", {})
            customer_name = extracted_data.get("customer_name", "")
            phone_number = extracted_data.get("phone_number", "")
            image_path = context.user_data.get("image_path", "")
            days = 3  # قيمة افتراضية
            
            if customer_name and phone_number and image_path:
                notification = add_notification(
                    customer_name=customer_name,
                    phone_number=phone_number,
                    image_path=image_path,
                    reminder_days=days
                )
                
                await query.edit_message_text(
                    f"تم إنشاء إشعار جديد بنجاح!\n\n"
                    f"الاسم: {notification['customer_name']}\n"
                    f"الهاتف: {notification['phone_number']}\n"
                    f"رمز الإشعار: {notification['id'][:8]}\n"
                    f"التذكير بعد: {days} يوم"
                )
            else:
                await query.edit_message_text(
                    "حدث خطأ أثناء إنشاء الإشعار. الرجاء التحقق من البيانات المستخرجة."
                )
        
        return ConversationHandler.END
    
    return WAITING_FOR_CHAT

async def handle_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة رسائل المحادثة الذكية"""
    if context.user_data.get("ai_mode") != "chat":
        return WAITING_FOR_CHAT
    
    user_message = update.message.text
    
    # أضف رسالة المستخدم إلى سياق المحادثة
    messages = context.user_data.get("ai_messages", [])
    messages.append({"role": "user", "content": user_message})
    
    # إرسال مؤشر الكتابة
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # فحص رسالة المستخدم بحثًا عن أرقام هواتف
    phone_numbers = extract_phone_numbers(user_message)
    
    if phone_numbers:
        # البحث عن الإشعارات بواسطة رقم الهاتف
        results = []
        for phone in phone_numbers:
            results.extend(search_notifications_by_phone(phone))
        
        if results:
            notification_info = "وجدت بعض الإشعارات المطابقة لرقم الهاتف المذكور:\n\n"
            
            for i, notification in enumerate(results, start=1):
                notification_info += f"{i}. اسم العميل: {notification['customer_name']}\n"
                notification_info += f"   رقم الهاتف: {notification['phone_number']}\n"
                notification_info += f"   رمز الإشعار: {notification['id'][:8]}\n\n"
            
            # إرسال رد الذكاء الاصطناعي مع معلومات الإشعارات
            ai_response = f"أرى أنك تبحث عن معلومات مرتبطة برقم هاتف. {notification_info}"
            await update.message.reply_text(ai_response)
            
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
                    logger.error(f"حدث خطأ أثناء إرسال صورة الإشعار: {e}")
            
            # أضف رد الذكاء الاصطناعي إلى سياق المحادثة
            messages.append({"role": "assistant", "content": ai_response})
            context.user_data["ai_messages"] = messages
            
            return WAITING_FOR_CHAT
    
    # استخدام الذكاء الاصطناعي للرد
    ai_response = await generate_ai_response(user_message, messages)
    
    # إرسال رد الذكاء الاصطناعي
    await update.message.reply_text(ai_response)
    
    # أضف رد الذكاء الاصطناعي إلى سياق المحادثة
    messages.append({"role": "assistant", "content": ai_response})
    context.user_data["ai_messages"] = messages
    
    return WAITING_FOR_CHAT

async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة رسائل تحليل الصور"""
    if context.user_data.get("ai_mode") != "image":
        return WAITING_FOR_CHAT
    
    # الحصول على أكبر نسخة من الصورة
    photo = update.message.photo[-1]
    
    # إنشاء معرّف فريد للصورة
    file_id = photo.file_id
    
    # تحميل الصورة
    TEMP_MEDIA_DIR.mkdir(exist_ok=True, parents=True)
    file = await context.bot.get_file(file_id)
    temp_image_path = f"temp_media/{file_id}.jpg"
    await file.download_to_drive(f"{current_dir}/{temp_image_path}")
    
    # حفظ مسار الصورة لاستخدامه لاحقًا
    context.user_data["temp_image_path"] = temp_image_path
    
    # إرسال مؤشر الكتابة
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # تحليل الصورة باستخدام الذكاء الاصطناعي
    analysis_result = await analyze_image(f"{current_dir}/{temp_image_path}")
    
    # استخراج المعلومات المهمة
    extracted_data = extract_shipping_info(analysis_result)
    
    # حفظ البيانات المستخرجة
    context.user_data["extracted_data"] = extracted_data
    
    # إنشاء نسخة دائمة من الصورة
    if extracted_data.get("customer_name") and extracted_data.get("phone_number"):
        IMAGES_DIR.mkdir(exist_ok=True, parents=True)
        image_uuid = str(uuid.uuid4())
        image_path = f"data/images/{image_uuid}.jpg"
        
        # نسخ الصورة من المجلد المؤقت إلى مجلد الصور
        import shutil
        shutil.copy(f"{current_dir}/{temp_image_path}", f"{current_dir}/{image_path}")
        
        # حفظ مسار الصورة الدائم
        context.user_data["image_path"] = image_path
    
    # إرسال التحليل
    if extracted_data:
        message = "تحليل الصورة:\n\n"
        
        if "customer_name" in extracted_data:
            message += f"🧑 اسم العميل: {extracted_data['customer_name']}\n"
        
        if "phone_number" in extracted_data:
            message += f"📱 رقم الهاتف: {extracted_data['phone_number']}\n"
        
        if "shipping_date" in extracted_data:
            message += f"📅 تاريخ الشحن: {extracted_data['shipping_date']}\n"
        
        if "destination" in extracted_data:
            message += f"📍 الوجهة: {extracted_data['destination']}\n"
        
        if "value" in extracted_data:
            message += f"💰 قيمة الشحنة: {extracted_data['value']}\n"
        
        message += f"\nالتحليل الكامل:\n{analysis_result}"
        
        # إنشاء أزرار إجراءات
        keyboard = []
        
        if extracted_data.get("customer_name") and extracted_data.get("phone_number"):
            keyboard.append([
                InlineKeyboardButton("✅ إنشاء إشعار من هذه البيانات", callback_data="extract_confirm_1")
            ])
        
        keyboard.append([
            InlineKeyboardButton("❌ إلغاء", callback_data="ai_cancel")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        
        return WAITING_FOR_EXTRACTION_CONFIRMATION
    else:
        await update.message.reply_text(
            "عذراً، لم أتمكن من استخراج معلومات مفيدة من هذه الصورة.\n"
            "الرجاء التأكد من أن الصورة تحتوي على معلومات شحنة واضحة وإرسالها مرة أخرى."
        )
        
        return WAITING_FOR_IMAGE

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء المحادثة الحالية"""
    await update.message.reply_text(
        "تم إلغاء عملية الذكاء الاصطناعي."
    )
    
    # مسح سياق المحادثة
    if "ai_mode" in context.user_data:
        del context.user_data["ai_mode"]
    
    if "ai_messages" in context.user_data:
        del context.user_data["ai_messages"]
    
    return ConversationHandler.END

async def generate_ai_response(user_message: str, messages: List[Dict[str, str]]) -> str:
    """
    توليد رد باستخدام الذكاء الاصطناعي
    
    المعلمات:
        user_message: رسالة المستخدم
        messages: سجل المحادثة
        
    العائد:
        رد الذكاء الاصطناعي
    """
    try:
        # محاولة استخدام OpenAI أولاً
        openai_client = get_openai_client()
        if openai_client:
            try:
                # تحويل المحادثة إلى تنسيق OpenAI
                openai_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages[-5:]]
                
                response = openai_client.chat.completions.create(
                    model="gpt-4o",  # استخدام أحدث نموذج
                    messages=openai_messages,
                    max_tokens=500,
                    temperature=0.7
                )
                
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"حدث خطأ أثناء استخدام OpenAI: {e}")
        
        # إذا فشل OpenAI، جرب Anthropic
        anthropic_client = get_anthropic_client()
        if anthropic_client:
            try:
                # تحويل المحادثة إلى تنسيق Anthropic
                anthropic_messages = []
                for msg in messages[-5:]:
                    anthropic_messages.append({"role": msg["role"], "content": msg["content"]})
                
                response = anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",  # استخدام أحدث نموذج
                    max_tokens=500,
                    temperature=0.7,
                    messages=anthropic_messages
                )
                
                return response.content[0].text
            except Exception as e:
                logger.error(f"حدث خطأ أثناء استخدام Anthropic: {e}")
        
        # إذا فشلت جميع المحاولات، أرجع رسالة افتراضية
        return "عذراً، حدث خطأ أثناء توليد الرد. الرجاء المحاولة مرة أخرى لاحقاً."
    
    except Exception as e:
        logger.error(f"حدث خطأ عام أثناء توليد رد الذكاء الاصطناعي: {e}")
        return "عذراً، حدث خطأ أثناء معالجة طلبك. الرجاء المحاولة مرة أخرى لاحقاً."

async def analyze_image(image_path: str) -> str:
    """
    تحليل صورة باستخدام الذكاء الاصطناعي
    
    المعلمات:
        image_path: مسار الصورة
        
    العائد:
        نتيجة التحليل
    """
    try:
        # محاولة استخدام OpenAI Vision أولاً
        openai_client = get_openai_client()
        if openai_client:
            try:
                import base64
                
                # تحويل الصورة إلى base64
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
                response = openai_client.chat.completions.create(
                    model="gpt-4o",  # استخدام أحدث نموذج
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "أنت محلل شحنات خبير. قم بتحليل صورة الشحنة واستخراج المعلومات المهمة التالية:\n"
                                "1. اسم العميل\n"
                                "2. رقم الهاتف\n"
                                "3. تاريخ الشحن\n"
                                "4. وجهة الشحنة\n"
                                "5. قيمة الشحنة\n\n"
                                "قدم تحليلاً مفصلاً لمحتوى الصورة. ركز على المعلومات المتعلقة بالشحنة."
                            )
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "قم بتحليل هذه الصورة وحدد اسم العميل ورقم الهاتف وتاريخ الشحن والوجهة والقيمة إن وجدت."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000
                )
                
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"حدث خطأ أثناء استخدام OpenAI Vision: {e}")
        
        # إذا فشل OpenAI، جرب Anthropic
        anthropic_client = get_anthropic_client()
        if anthropic_client:
            try:
                import base64
                
                # تحويل الصورة إلى base64
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
                response = anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",  # استخدام أحدث نموذج
                    max_tokens=1000,
                    temperature=0.7,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "أنت محلل شحنات خبير. قم بتحليل صورة الشحنة واستخراج المعلومات المهمة التالية:\n"
                                        "1. اسم العميل\n"
                                        "2. رقم الهاتف\n"
                                        "3. تاريخ الشحن\n"
                                        "4. وجهة الشحنة\n"
                                        "5. قيمة الشحنة\n\n"
                                        "قدم تحليلاً مفصلاً لمحتوى الصورة. ركز على المعلومات المتعلقة بالشحنة."
                                    )
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": base64_image
                                    }
                                }
                            ]
                        }
                    ]
                )
                
                return response.content[0].text
            except Exception as e:
                logger.error(f"حدث خطأ أثناء استخدام Anthropic: {e}")
        
        # إذا فشلت جميع المحاولات، أرجع رسالة افتراضية
        return "عذراً، لم أتمكن من تحليل الصورة. الرجاء التأكد من أن الصورة واضحة ومقروءة."
    
    except Exception as e:
        logger.error(f"حدث خطأ عام أثناء تحليل الصورة: {e}")
        return "عذراً، حدث خطأ أثناء تحليل الصورة. الرجاء المحاولة مرة أخرى لاحقاً."

def extract_shipping_info(analysis_text: str) -> Dict[str, str]:
    """
    استخراج معلومات الشحنة من نص التحليل
    
    المعلمات:
        analysis_text: نص التحليل
        
    العائد:
        قاموس يحتوي على المعلومات المستخرجة
    """
    extracted_data = {}
    
    # أنماط التعرف على البيانات
    name_patterns = [
        r"اسم العميل:?\s*([^\n:;,،]+)",
        r"اسم المستلم:?\s*([^\n:;,،]+)",
        r"العميل:?\s*([^\n:;,،]+)",
        r"المستلم:?\s*([^\n:;,،]+)",
        r"اسم:?\s*([^\n:;,،]+)",
    ]
    
    phone_patterns = [
        r"رقم الهاتف:?\s*([+\d\s\-()]+)",
        r"الهاتف:?\s*([+\d\s\-()]+)",
        r"رقم الجوال:?\s*([+\d\s\-()]+)",
        r"الجوال:?\s*([+\d\s\-()]+)",
        r"رقم:?\s*([+\d\s\-()]+)",
        r"(\+?90\d{10})",
        r"(\+?963\d{9})",
        r"(\d{10,11})",
    ]
    
    date_patterns = [
        r"تاريخ الشحن:?\s*([^\n:;,،]+)",
        r"تاريخ:?\s*([^\n:;,،]+)",
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{2}/\d{2}/\d{4})",
        r"(\d{2}-\d{2}-\d{4})",
    ]
    
    destination_patterns = [
        r"وجهة الشحنة:?\s*([^\n:;,،]+)",
        r"الوجهة:?\s*([^\n:;,،]+)",
        r"المدينة:?\s*([^\n:;,،]+)",
        r"العنوان:?\s*([^\n:;,،]+)",
        r"مدينة:?\s*([^\n:;,،]+)",
    ]
    
    value_patterns = [
        r"قيمة الشحنة:?\s*([^\n:;,،]+)",
        r"قيمة:?\s*([^\n:;,،]+)",
        r"المبلغ:?\s*([^\n:;,،]+)",
        r"السعر:?\s*([^\n:;,،]+)",
        r"(\d+(?:,\d+)*(?:\.\d+)?\s*(?:ليرة|ل\.س|دولار|\$|TL|₺))",
    ]
    
    # اسم العميل
    for pattern in name_patterns:
        matches = re.search(pattern, analysis_text, re.IGNORECASE | re.MULTILINE)
        if matches:
            customer_name = matches.group(1).strip()
            if 3 <= len(customer_name) <= 50:  # التحقق من أن الاسم منطقي
                extracted_data["customer_name"] = customer_name
                break
    
    # رقم الهاتف
    for pattern in phone_patterns:
        matches = re.search(pattern, analysis_text, re.IGNORECASE | re.MULTILINE)
        if matches:
            phone_number = matches.group(1).strip()
            # تنظيف رقم الهاتف
            phone_number = ''.join(filter(lambda x: x.isdigit() or x == '+', phone_number))
            
            # إضافة رمز البلد إذا لزم الأمر
            if phone_number.startswith("09") or phone_number.startswith("9"):
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
            
            extracted_data["phone_number"] = phone_number
            break
    
    # تاريخ الشحن
    for pattern in date_patterns:
        matches = re.search(pattern, analysis_text, re.IGNORECASE | re.MULTILINE)
        if matches:
            shipping_date = matches.group(1).strip()
            extracted_data["shipping_date"] = shipping_date
            break
    
    # وجهة الشحنة
    for pattern in destination_patterns:
        matches = re.search(pattern, analysis_text, re.IGNORECASE | re.MULTILINE)
        if matches:
            destination = matches.group(1).strip()
            extracted_data["destination"] = destination
            break
    
    # قيمة الشحنة
    for pattern in value_patterns:
        matches = re.search(pattern, analysis_text, re.IGNORECASE | re.MULTILINE)
        if matches:
            value = matches.group(1).strip()
            extracted_data["value"] = value
            break
    
    return extracted_data

def extract_phone_numbers(text: str) -> List[str]:
    """
    استخراج أرقام الهواتف من النص
    
    المعلمات:
        text: النص المراد البحث فيه
        
    العائد:
        قائمة بأرقام الهواتف المستخرجة
    """
    phone_patterns = [
        r"\+?90\d{10}",  # رقم تركي مع رمز البلد
        r"\+?963\d{9}",  # رقم سوري مع رمز البلد
        r"0?9\d{8}",     # رقم سوري بدون رمز البلد
        r"0?5\d{9}",     # رقم تركي بدون رمز البلد
        r"\d{10,11}",    # أي رقم هاتف عام
    ]
    
    phone_numbers = []
    
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        if matches:
            for match in matches:
                # تنظيف رقم الهاتف
                phone_number = ''.join(filter(lambda x: x.isdigit() or x == '+', match))
                
                # إضافة رمز البلد إذا لزم الأمر
                if phone_number.startswith("09") or phone_number.startswith("9"):
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
                
                if phone_number not in phone_numbers:
                    phone_numbers.append(phone_number)
    
    return phone_numbers

def get_ai_handlers() -> List[Any]:
    """
    الحصول على جميع معالجات الذكاء الاصطناعي
    
    العائد:
        قائمة بمعالجات الذكاء الاصطناعي
    """
    # معالج المحادثة للذكاء الاصطناعي
    ai_conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler("ai", ai_command),
            CallbackQueryHandler(handle_ai_callback, pattern="^ai_")
        ],
        states={
            WAITING_FOR_CHAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_message),
                CallbackQueryHandler(handle_ai_callback, pattern="^ai_")
            ],
            WAITING_FOR_IMAGE: [
                MessageHandler(filters.PHOTO, handle_image_message),
                CallbackQueryHandler(handle_ai_callback, pattern="^ai_")
            ],
            WAITING_FOR_EXTRACTION_CONFIRMATION: [
                CallbackQueryHandler(handle_ai_callback, pattern="^extract_")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
    
    # معالج تحليل الصور المباشر
    direct_image_handler = MessageHandler(
        filters.PHOTO & ~filters.COMMAND,
        handle_image_message
    )
    
    # قائمة بجميع معالجات الذكاء الاصطناعي
    handlers = [
        # معالج المحادثة للذكاء الاصطناعي
        ai_conversation_handler,
        
        # معالج تحليل الصور المباشر
        # ملاحظة: يجب أن يكون هذا المعالج آخر معالج في القائمة لتجنب التداخل مع المعالجات الأخرى
        # direct_image_handler
    ]
    
    return handlers