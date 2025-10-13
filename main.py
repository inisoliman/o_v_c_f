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

# استيراد المكونات
from app.core.config import settings
from app.database.connection import check_database, init_database
from app.services.user_service import UserService
from app.handlers import register_all_handlers
from app.utils.keep_alive import run_keep_alive_system

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.LOG_LEVEL),
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def setup_scheduler():
    """إعداد المجدول للمهام التلقائية"""
    # جدولة تنظيف السجل يومياً في 3 صباحاً
    schedule.every().day.at("03:00").do(
        lambda: UserService.cleanup_old_history(settings.AUTO_DELETE_HISTORY_DAYS)
    )
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(3600)  # فحص كل ساعة
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("✅ Auto-cleanup scheduler started")


def main():
    """الدالة الرئيسية"""
    logger.info("🚀 بدء تشغيل بوت أرشيف الفيديوهات المتقدم...")
    
    # التحقق من متغيرات البيئة
    if not settings.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN غير موجود!")
        exit(1)
    
    if not settings.DATABASE_URL:
        logger.error("❌ DATABASE_URL غير موجود!")
        exit(1)
    
    # بدء نظام Keep Alive
    run_keep_alive_system()
    
    # إعداد المجدول
    setup_scheduler()
    
    # التحقق من قاعدة البيانات
    if not init_database():
        logger.error("❌ فشل الاتصال بقاعدة البيانات!")
        return
    
    logger.info("✅ تم الاتصال بقاعدة البيانات")
    
    # إنشاء البوت وتسجيل المعالجات
    bot = telebot.TeleBot(settings.BOT_TOKEN)
    register_all_handlers(bot)
    
    logger.info("🎉 البوت جاهز للعمل 24/7 مجاناً مع Keep Alive!")
    logger.info(f"🔧 المشرفون: {settings.admin_list}")
    logger.info("🛠️ لوحة التحكم: /admin")
    
    # بدء البوت
    bot.infinity_polling(timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    main()
