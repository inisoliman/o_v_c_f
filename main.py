#!/usr/bin/env python3
"""
🎬 Telegram Video Archive Bot - Webhook Version
بوت أرشيف الفيديوهات مع Webhooks لتجنب التضارب
"""
import os
import sys
import time
import threading
import logging
import schedule
from dotenv import load_dotenv
import telebot
from flask import Flask, request

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
WEBHOOK_URL = os.getenv('RENDER_EXTERNAL_URL', 'https://o-v-c-f.onrender.com')

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN غير موجود!")
    sys.exit(1)

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL غير موجود!")
    sys.exit(1)

# إنشاء البوت و Flask
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# متغير للتحكم في إيقاف البوت
should_stop = False


def setup_scheduler():
    """إعداد المجدول للمهام التلقائية"""
    try:
        def cleanup_task():
            try:
                from app.services.user_service import UserService
                UserService.cleanup_old_history(15)
                logger.info("🧹 تم تنفيذ التنظيف الدوري")
            except Exception as e:
                logger.error(f"❌ خطأ في تنظيف السجل: {e}")
        
        schedule.every().day.at("03:00").do(cleanup_task)
        
        def run_scheduler():
            while not should_stop:
                try:
                    schedule.run_pending()
                    time.sleep(3600)  # فحص كل ساعة
                except Exception as e:
                    logger.error(f"❌ خطأ في المجدول: {e}")
                    time.sleep(3600)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("✅ Auto-cleanup scheduler started")
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


# === Flask Routes للـ Keep Alive و Webhooks ===

@app.route('/')
def home():
    try:
        from app.services.stats_service import StatsService
        stats = StatsService.get_general_stats()
    except:
        stats = {'videos': 0, 'users': 0, 'categories': 0}
    
    return {
        "status": "alive ✅",
        "service": "Telegram Video Archive Bot",
        "method": "Webhooks (No Conflicts)",
        "users": stats.get('users', 0),
        "videos": stats.get('videos', 0),
        "categories": stats.get('categories', 0),
        "version": "2.0 Webhook"
    }


@app.route('/health')
def health_check():
    try:
        from app.database.connection import check_database
        db_status = "connected ✅" if check_database() else "disconnected ❌"
    except:
        db_status = "unknown ❓"
    
    return {
        "status": "healthy",
        "database": db_status,
        "bot": "webhook_active ✅",
        "method": "Webhooks"
    }


@app.route('/ping')
def ping():
    return f"pong ✅ - البوت يعمل بـ Webhooks!"


@app.route('/stats')
def stats_endpoint():
    try:
        from app.services.stats_service import StatsService
        stats = StatsService.get_general_stats()
        return stats
    except Exception as e:
        return {"error": f"Failed to get stats: {str(e)}"}


@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    """معالج Webhook للبوت"""
    try:
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    except Exception as e:
        logger.error(f"❌ خطأ في Webhook: {e}")
        return '', 500


def setup_webhook():
    """إعداد Webhook للبوت"""
    try:
        # حذف أي webhook موجود
        bot.remove_webhook()
        time.sleep(1)
        
        # إعداد الـ webhook الجديد
        webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        success = bot.set_webhook(url=webhook_url)
        
        if success:
            logger.info(f"✅ تم إعداد Webhook: {webhook_url}")
            return True
        else:
            logger.error("❌ فشل في إعداد Webhook")
            return False
            
    except Exception as e:
        logger.error(f"❌ خطأ في إعداد Webhook: {e}")
        return False


def self_ping():
    """نظام الـ Self Ping لمنع السكون"""
    import requests
    time.sleep(60)  # انتظار دقيقة قبل البدء
    
    while not should_stop:
        try:
            time.sleep(840)  # 14 دقيقة
            response = requests.get(f"{WEBHOOK_URL}/ping", timeout=30)
            logger.info(f"✅ Self-ping successful: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Self-ping failed: {e}")


def main():
    """الدالة الرئيسية"""
    global should_stop
    
    logger.info("🚀 بدء تشغيل بوت أرشيف الفيديوهات (Webhook Mode)")
    
    try:
        # التحقق من قاعدة البيانات
        from app.database.connection import init_database
        if not init_database():
            logger.error("❌ فشل الاتصال بقاعدة البيانات!")
            return
        
        logger.info("✅ تم الاتصال بقاعدة البيانات")
        
        # تسجيل المعالجات
        register_all_handlers()
        
        # إعداد المجدول
        setup_scheduler()
        
        # إعداد Webhook
        if setup_webhook():
            logger.info("✅ تم إعداد Webhook بنجاح")
        else:
            logger.error("❌ فشل إعداد Webhook")
            return
        
        # بدء Self-Ping
        ping_thread = threading.Thread(target=self_ping, daemon=True)
        ping_thread.start()
        logger.info("✅ Self-ping system started")
        
        logger.info("🎉 البوت جاهز للعمل 24/7 بدون تضارب!")
        logger.info(f"🔧 المشرفون: {ADMIN_IDS}")
        logger.info("🛠️ لوحة التحكم: /admin")
        logger.info("🌐 الطريقة: Webhooks (لا توجد تضاربات)")
        
        # تشغيل Flask مع Webhook
        port = int(os.environ.get("PORT", 10000))
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ عام في تشغيل البوت: {e}")
    finally:
        should_stop = True
        try:
            bot.remove_webhook()
            logger.info("🧹 تم حذف Webhook")
        except:
            pass
        logger.info("👋 تم إنهاء البوت")


if __name__ == "__main__":
    main()
