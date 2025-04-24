"""
نقطة دخول رئيسية للتوافق مع منصة Render
"""

from app import app

# يتم التنفيذ من هنا في بيئة Render
if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)