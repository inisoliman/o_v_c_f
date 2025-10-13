#!/usr/bin/env python3
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

# إنشاء البوت
bot = telebot.TeleBot(BOT_TOKEN)

def setup_scheduler():
    """إعداد المجدول للمهام التلقائية"""
    try:
        # جدولة تنظيف السجل يومياً في 3 صباحاً
        def cleanup_task():
            try:
                from app.services.user_service import UserService
                UserService.cleanup_old_history(15)
            except Exception as e:
                logger.error(f"❌ خطأ في تنظيف السجل: {e}")
        
        schedule.every().day.at("03:00").do(cleanup_task)
        
        def run_scheduler():
            while True:
                try:
                    schedule.run_pending()
                    time.sleep(3600)  # فحص كل ساعة
                except Exception as e:
                    logger.error(f"❌ خطأ في المجدول: {e}")
                    time.sleep(3600)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("✅ Auto-cleanup scheduler started (15 days)")
    except Exception as e:
        logger.error(f"❌ خطأ في إعداد المجدول: {e}")


def register_all_handlers():
    """تسجيل جميع المعالجات"""
    try:
        # معالجات البداية والأوامر الأساسية
        from app.handlers.start import register_start_handlers
        register_start_handlers(bot)
        
        # معالجات الإدارة
        from app.handlers.admin import register_admin_handlers
        register_admin_handlers(bot)
        
        # معالجات الأزرار
        from app.handlers.callbacks import register_all_callbacks
        register_all_callbacks(bot)
        
        # معالجات النصوص
        from app.handlers.text import register_text_handlers
        register_text_handlers(bot)
        
        logger.info("✅ تم تسجيل جميع معالجات البوت")
        
    except Exception as e:
        logger.error(f"❌ خطأ في تسجيل المعالجات: {e}")


def main():
    """الدالة الرئيسية"""
    logger.info("🚀 بدء تشغيل بوت أرشيف الفيديوهات المتقدم...")
    
    try:
        # بدء نظام Keep Alive
        from app.utils.keep_alive import run_keep_alive_system
        run_keep_alive_system()
        
        # إعداد المجدول
        setup_scheduler()
        
        # التحقق من قاعدة البيانات
        from app.database.connection import init_database
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
        
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")
    finally:
        logger.info("👋 تم إنهاء البوت")


if __name__ == "__main__":
    main()
