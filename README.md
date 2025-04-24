# بوت إشعارات الشحن NatureCare - نسخة Render

بوت تيليجرام مخصص لإدارة إشعارات الشحن باللغة العربية، مع دعم الويب هوك وجاهز للنشر على منصة Render.

## الميزات

- 📦 إدارة إشعارات الشحن مع صور
- 📱 دعم أرقام الهواتف السورية والتركية
- 🔔 إرسال رسائل تذكير عبر Twilio/WhatsApp
- 🔍 البحث عن الإشعارات بالاسم أو رقم الهاتف
- 👤 نظام متكامل لإدارة المستخدمين والصلاحيات
- 🧠 ميزات الذكاء الاصطناعي لتحليل صور الشحن
- 📊 واجهة ويب بسيطة لعرض حالة البوت

## الخطوات الأساسية للنشر

### 1. إنشاء بوت تيليجرام

1. افتح محادثة مع [@BotFather](https://t.me/BotFather) على تيليجرام
2. أرسل الأمر `/newbot` واتبع التعليمات لإنشاء بوت جديد
3. احتفظ بتوكن البوت الذي ستحصل عليه (سيبدو مثل: `123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ`)
4. أرسل الأمر `/setcommands` لتعيين أوامر البوت، واختر البوت الجديد
5. أرسل القائمة التالية:

```
start - بدء استخدام البوت
search - البحث عن إشعار باستخدام رقم الهاتف
help - عرض رسالة المساعدة
admin - الوصول إلى لوحة تحكم المسؤول
ai - استخدام ميزات الذكاء الاصطناعي
```

### 2. رفع المشروع على GitHub

1. قم بإنشاء مستودع جديد على GitHub
2. قم برفع المشروع إليه باستخدام الأوامر التالية:

```bash
git init
git add .
git commit -m "النسخة الأولية من بوت إشعارات الشحن"
git branch -M main
git remote add origin https://github.com/username/repository-name.git
git push -u origin main
```

### 3. إعداد البوت على Render

1. أنشئ حساباً على [Render](https://render.com/) إذا لم يكن لديك حساب
2. اضغط على "New" واختر "Web Service"
3. اختر "Build and deploy from a Git repository"
4. اختر مستودع GitHub الخاص بك
5. املأ البيانات التالية:
   - Name: naturecare-shipping-bot (أو أي اسم آخر)
   - Region: اختر المنطقة الأقرب لموقعك
   - Branch: main
   - Root Directory: اترك فارغاً
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Instance Type: Free (يمكن ترقيته لاحقاً)

6. أضف متغيرات البيئة التالية في قسم "Environment Variables":
   - `TELEGRAM_BOT_TOKEN`: توكن البوت الذي حصلت عليه من BotFather
   - `WEBHOOK_URL`: عنوان الويب سيرفيس بالكامل (مثل: `https://naturecare-shipping-bot.onrender.com`)
   - `FLASK_SECRET_KEY`: مفتاح عشوائي آمن (يمكنك توليده باستخدام أي مولد كلمات مرور قوية)

7. (اختياري) أضف متغيرات البيئة التالية إذا كنت ترغب في استخدام Twilio:
   - `TWILIO_ACCOUNT_SID`: معرف حساب Twilio
   - `TWILIO_AUTH_TOKEN`: توكن مصادقة Twilio
   - `TWILIO_PHONE_NUMBER`: رقم هاتف Twilio

8. (اختياري) أضف متغيرات البيئة التالية إذا كنت ترغب في استخدام الذكاء الاصطناعي:
   - `OPENAI_API_KEY`: مفتاح API من OpenAI
   - `ANTHROPIC_API_KEY`: مفتاح API من Anthropic

9. اضغط على "Create Web Service"

### 4. تفعيل الويب هوك

1. بعد اكتمال النشر، الويب هوك سيتم تعيينه تلقائيًا باستخدام `WEBHOOK_URL`
2. إذا كنت ترغب في تعيينه يدوياً، يمكنك زيارة الرابط:
   ```
   https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<WEBHOOK_URL>/<TELEGRAM_BOT_TOKEN>
   ```
   (استبدل `<TELEGRAM_BOT_TOKEN>` و `<WEBHOOK_URL>` بالقيم الخاصة بك)

3. للتحقق من حالة الويب هوك، يمكنك زيارة:
   ```
   https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo
   ```

### 5. بدء استخدام البوت

1. افتح محادثة مع البوت على تيليجرام (باستخدام الرابط الذي قدمه لك BotFather)
2. أرسل الأمر `/start`
3. ستصبح تلقائيًا المسؤول الرئيسي للبوت
4. استخدم أمر `/admin` للوصول إلى لوحة تحكم المسؤول

## معلومات إضافية

### الدعم المستمر

- منصة Render توفر خدمة دائمة التشغيل للخطط المدفوعة
- خطة Render المجانية ستدخل في وضع السكون بعد فترة من عدم النشاط

### ترقية البوت

- للحصول على أداء أفضل، يمكنك ترقية خطة Render إلى خطة مدفوعة
- للعمل مع WhatsApp، قم بتكوين Twilio مع حساب WhatsApp Business

### استكشاف الأخطاء وإصلاحها

- إذا توقف البوت عن العمل، تحقق من سجلات Render
- تأكد من أن الويب هوك مضبوط بشكل صحيح
- تحقق من صلاحية توكن البوت

## ترخيص

هذا المشروع مرخص تحت رخصة MIT. راجع ملف LICENSE للحصول على التفاصيل.