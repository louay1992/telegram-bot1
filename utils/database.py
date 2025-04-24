"""
وحدة قاعدة البيانات - تدير تخزين واسترجاع الإشعارات والبيانات الأخرى
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# إعداد السجل
logger = logging.getLogger(__name__)

# تعريف مسارات الملفات
BASE_DIR = Path(__file__).parent.parent.absolute()
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
ADMINS_FILE = DATA_DIR / "admins.json"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"
TEMPLATES_FILE = DATA_DIR / "templates.json"

# التأكد من وجود المجلدات اللازمة
DATA_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

def setup_database() -> None:
    """
    إعداد قاعدة البيانات وملفات التخزين الأولية
    """
    # إنشاء ملف المسؤولين إذا لم يكن موجوداً
    if not ADMINS_FILE.exists():
        with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    # إنشاء ملف الإشعارات إذا لم يكن موجوداً
    if not NOTIFICATIONS_FILE.exists():
        with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    # إنشاء ملف القوالب إذا لم يكن موجوداً
    if not TEMPLATES_FILE.exists():
        default_templates = {
            "sms_template": "السلام عليكم {customer_name}،\nلديك شحنة جديدة رقم {notification_id} بانتظار التسليم.\nيرجى التواصل مع المسوق لاستلام طلبك.\nNatureCare",
            "welcome_template": "مرحباً {customer_name}،\nشكراً لطلبك من NatureCare! تم تسجيل شحنتك برقم {notification_id} وسيتم التسليم قريباً.",
            "verification_template": "تأكيد استلام الشحنة رقم {notification_id}\nالاسم: {customer_name}\nالرجاء الرد بكلمة 'تم' لتأكيد الاستلام.\nNatureCare"
        }
        with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_templates, f, ensure_ascii=False)
    
    logger.info("Database setup completed successfully")

def save_admins(admins: List[int]) -> bool:
    """
    حفظ قائمة المسؤولين
    
    المعلمات:
        admins: قائمة معرفات المسؤولين
        
    العائد:
        True إذا تم الحفظ بنجاح، False خلاف ذلك
    """
    try:
        with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(admins, f)
        return True
    except Exception as e:
        logger.error(f"Error saving admins: {e}")
        return False

def get_admins() -> List[int]:
    """
    الحصول على قائمة المسؤولين
    
    العائد:
        قائمة معرفات المسؤولين
    """
    try:
        if not ADMINS_FILE.exists():
            return []
        
        with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading admins: {e}")
        return []

def is_admin(user_id: int) -> bool:
    """
    التحقق مما إذا كان المستخدم مسؤولاً
    
    المعلمات:
        user_id: معرف المستخدم
        
    العائد:
        True إذا كان المستخدم مسؤولاً، False خلاف ذلك
    """
    return user_id in get_admins()

def add_admin(user_id: int) -> bool:
    """
    إضافة مسؤول جديد
    
    المعلمات:
        user_id: معرف المستخدم
        
    العائد:
        True إذا تمت الإضافة بنجاح، False خلاف ذلك
    """
    admins = get_admins()
    if user_id in admins:
        return True
    
    admins.append(user_id)
    return save_admins(admins)

def remove_admin(user_id: int) -> bool:
    """
    إزالة مسؤول
    
    المعلمات:
        user_id: معرف المستخدم
        
    العائد:
        True إذا تمت الإزالة بنجاح، False خلاف ذلك
    """
    admins = get_admins()
    if user_id not in admins:
        return True
    
    admins.remove(user_id)
    return save_admins(admins)

def reset_admins() -> bool:
    """
    إعادة تعيين قائمة المسؤولين (إزالة جميع المسؤولين)
    
    العائد:
        True إذا تم إعادة التعيين بنجاح، False خلاف ذلك
    """
    return save_admins([])

def save_notifications(notifications: List[Dict[str, Any]]) -> bool:
    """
    حفظ قائمة الإشعارات
    
    المعلمات:
        notifications: قائمة الإشعارات
        
    العائد:
        True إذا تم الحفظ بنجاح، False خلاف ذلك
    """
    try:
        with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(notifications, f, ensure_ascii=False, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving notifications: {e}")
        return False

def get_notifications() -> List[Dict[str, Any]]:
    """
    الحصول على قائمة الإشعارات
    
    العائد:
        قائمة الإشعارات
    """
    try:
        if not NOTIFICATIONS_FILE.exists():
            return []
        
        with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading notifications: {e}")
        return []

def add_notification(customer_name: str, phone_number: str, image_path: str, reminder_days: int = 3) -> Dict[str, Any]:
    """
    إضافة إشعار جديد
    
    المعلمات:
        customer_name: اسم العميل
        phone_number: رقم الهاتف
        image_path: مسار الصورة
        reminder_days: عدد أيام التذكير
        
    العائد:
        الإشعار المضاف
    """
    notifications = get_notifications()
    
    notification_id = str(uuid.uuid4())
    created_at = datetime.now()
    reminder_time = created_at + timedelta(days=reminder_days)
    
    notification = {
        "id": notification_id,
        "customer_name": customer_name,
        "phone_number": phone_number,
        "image_path": image_path,
        "created_at": created_at.isoformat(),
        "reminder_time": reminder_time.isoformat(),
        "reminder_sent": False,
        "reminder_days": reminder_days,
        "delivery_confirmed": False,
        "delivery_date": None,
        "delivery_proof_image": None
    }
    
    notifications.append(notification)
    save_notifications(notifications)
    
    return notification

def get_notification(notification_id: str) -> Optional[Dict[str, Any]]:
    """
    الحصول على إشعار بواسطة المعرف
    
    المعلمات:
        notification_id: معرف الإشعار
        
    العائد:
        الإشعار إذا وجد، None خلاف ذلك
    """
    notifications = get_notifications()
    
    for notification in notifications:
        if notification["id"] == notification_id:
            return notification
    
    return None

def update_notification(notification_id: str, updates: Dict[str, Any]) -> bool:
    """
    تحديث إشعار
    
    المعلمات:
        notification_id: معرف الإشعار
        updates: التحديثات المطلوبة
        
    العائد:
        True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    notifications = get_notifications()
    
    for i, notification in enumerate(notifications):
        if notification["id"] == notification_id:
            notifications[i].update(updates)
            return save_notifications(notifications)
    
    return False

def delete_notification(notification_id: str) -> bool:
    """
    حذف إشعار
    
    المعلمات:
        notification_id: معرف الإشعار
        
    العائد:
        True إذا تم الحذف بنجاح، False خلاف ذلك
    """
    notifications = get_notifications()
    
    for i, notification in enumerate(notifications):
        if notification["id"] == notification_id:
            del notifications[i]
            return save_notifications(notifications)
    
    return False

def search_notifications_by_name(customer_name: str) -> List[Dict[str, Any]]:
    """
    البحث عن الإشعارات بواسطة اسم العميل
    
    المعلمات:
        customer_name: اسم العميل
        
    العائد:
        قائمة الإشعارات المطابقة
    """
    notifications = get_notifications()
    results = []
    
    customer_name = customer_name.lower()
    
    for notification in notifications:
        if customer_name in notification["customer_name"].lower():
            results.append(notification)
    
    return results

def search_notifications_by_phone(phone_number: str) -> List[Dict[str, Any]]:
    """
    البحث عن الإشعارات بواسطة رقم الهاتف
    
    المعلمات:
        phone_number: رقم الهاتف
        
    العائد:
        قائمة الإشعارات المطابقة
    """
    notifications = get_notifications()
    results = []
    
    # تنظيف رقم الهاتف من الأحرف غير الرقمية
    phone_number = ''.join(filter(str.isdigit, phone_number))
    
    for notification in notifications:
        # تنظيف رقم الهاتف المخزن من الأحرف غير الرقمية
        stored_phone = ''.join(filter(str.isdigit, notification["phone_number"]))
        
        # البحث عن التطابق الجزئي في آخر الرقم
        if stored_phone.endswith(phone_number) or phone_number.endswith(stored_phone):
            results.append(notification)
    
    return results

def get_templates() -> Dict[str, str]:
    """
    الحصول على قوالب الرسائل
    
    العائد:
        قاموس قوالب الرسائل
    """
    try:
        if not TEMPLATES_FILE.exists():
            # إنشاء قوالب افتراضية
            default_templates = {
                "sms_template": "السلام عليكم {customer_name}،\nلديك شحنة جديدة رقم {notification_id} بانتظار التسليم.\nيرجى التواصل مع المسوق لاستلام طلبك.\nNatureCare",
                "welcome_template": "مرحباً {customer_name}،\nشكراً لطلبك من NatureCare! تم تسجيل شحنتك برقم {notification_id} وسيتم التسليم قريباً.",
                "verification_template": "تأكيد استلام الشحنة رقم {notification_id}\nالاسم: {customer_name}\nالرجاء الرد بكلمة 'تم' لتأكيد الاستلام.\nNatureCare"
            }
            with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_templates, f, ensure_ascii=False)
            return default_templates
        
        with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading templates: {e}")
        # إرجاع قوالب افتراضية في حالة الخطأ
        return {
            "sms_template": "السلام عليكم {customer_name}،\nلديك شحنة جديدة رقم {notification_id} بانتظار التسليم.\nيرجى التواصل مع المسوق لاستلام طلبك.\nNatureCare",
            "welcome_template": "مرحباً {customer_name}،\nشكراً لطلبك من NatureCare! تم تسجيل شحنتك برقم {notification_id} وسيتم التسليم قريباً.",
            "verification_template": "تأكيد استلام الشحنة رقم {notification_id}\nالاسم: {customer_name}\nالرجاء الرد بكلمة 'تم' لتأكيد الاستلام.\nNatureCare"
        }

def update_template(template_name: str, template_text: str) -> bool:
    """
    تحديث قالب رسالة
    
    المعلمات:
        template_name: اسم القالب
        template_text: نص القالب
        
    العائد:
        True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    try:
        templates = get_templates()
        templates[template_name] = template_text
        
        with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
            json.dump(templates, f, ensure_ascii=False)
        
        return True
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        return False

def get_notification_count() -> int:
    """
    الحصول على عدد الإشعارات
    
    العائد:
        عدد الإشعارات
    """
    return len(get_notifications())

def get_pending_reminders() -> List[Dict[str, Any]]:
    """
    الحصول على قائمة الإشعارات التي تحتاج إلى إرسال تذكير
    
    العائد:
        قائمة الإشعارات التي تحتاج إلى تذكير
    """
    notifications = get_notifications()
    now = datetime.now()
    pending_reminders = []
    
    for notification in notifications:
        if notification.get("reminder_sent", False):
            continue
        
        reminder_time = datetime.fromisoformat(notification["reminder_time"])
        
        if reminder_time <= now:
            pending_reminders.append(notification)
    
    return pending_reminders

def mark_reminder_sent(notification_id: str) -> bool:
    """
    تعليم الإشعار بأنه تم إرسال تذكير له
    
    المعلمات:
        notification_id: معرف الإشعار
        
    العائد:
        True إذا تم التعليم بنجاح، False خلاف ذلك
    """
    return update_notification(notification_id, {"reminder_sent": True})

def mark_delivery_confirmed(notification_id: str, proof_image_path: Optional[str] = None) -> bool:
    """
    تعليم الإشعار بأنه تم تأكيد التسليم
    
    المعلمات:
        notification_id: معرف الإشعار
        proof_image_path: مسار صورة إثبات التسليم (اختياري)
        
    العائد:
        True إذا تم التعليم بنجاح، False خلاف ذلك
    """
    updates = {
        "delivery_confirmed": True,
        "delivery_date": datetime.now().isoformat()
    }
    
    if proof_image_path:
        updates["delivery_proof_image"] = proof_image_path
    
    return update_notification(notification_id, updates)