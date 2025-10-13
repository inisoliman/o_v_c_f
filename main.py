"""
🎬 Telegram Video Archive Bot - نقطة الدخول الرئيسية
بوت أرشيف الفيديوهات المتقدم مع Keep Alive System
"""
import os
import time
import threading
import logging
import schedule
from dotenv import load_dotenv
import telebot

# تحميل متغيرات البيئة
load_dotenv()

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# إعدادات البوت
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN غير موجود!")
    exit(1)

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL غير موجود!")
    exit(1)

# استيراد المكونات بعد التحقق من المتغيرات
from app.database.connection import check_database, init_database
from app.services.user_service import UserService
from app.utils.keep_alive import run_keep_alive_system
from app.handlers.callbacks import register_all_callbacks
from app.handlers.text import register_text_handlers
from app.handlers.start import register_start_handlers
from app.handlers.admin import register_admin_handlers

# إنشاء البوت
bot = telebot.TeleBot(BOT_TOKEN)


def setup_scheduler():
    """إعداد المجدول للمهام التلقائية"""
    # جدولة تنظيف السجل يومياً في 3 صباحاً
    schedule.every().day.at("03:00").do(
        lambda: UserService.cleanup_old_history(15)  # 15 يوم
    )
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(3600)  # فحص كل ساعة
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("✅ Auto-cleanup scheduler started (15 days)")


def register_all_handlers():
    """تسجيل جميع المعالجات"""
    # معالجات البداية والأوامر الأساسية
    register_start_handlers(bot)
    
    # معالجات الإدارة
    register_admin_handlers(bot)
    
    # معالجات الأزرار
    register_all_callbacks(bot)
    
    # معالجات النصوص
    register_text_handlers(bot)
    
    logger.info("✅ تم تسجيل جميع معالجات البوت")


def main():
    """الدالة الرئيسية"""
    logger.info("🚀 بدء تشغيل بوت أرشيف الفيديوهات المتقدم...")
    
    # بدء نظام Keep Alive
    run_keep_alive_system()
    
    # إعداد المجدول
    setup_scheduler()
    
    # التحقق من قاعدة البيانات
    if not init_database():
        logger.error("❌ فشل الاتصال بقاعدة البيانات!")
        return
    
    logger.info("✅ تم الاتصال بقاعدة البيانات")
    
    # تسجيل المعالجات
    register_all_handlers()
    
    logger.info("🎉 البوت جاهز للعمل 24/7 مجاناً مع Keep Alive!")
    logger.info(f"🔧 المشرفون: {ADMIN_IDS}")
    logger.info("🛠️ لوحة التحكم: /admin")
    
    # بدء البوت
    bot.infinity_polling(timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    main()
