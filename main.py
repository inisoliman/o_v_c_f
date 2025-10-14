#!/usr/bin/env python3
"""
🎬 Telegram Video Archive Bot - Structured Architecture
بوت أرشيف الفيديوهات المتقدم مع الهيكل المنظم
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
SOURCE_CHAT_ID = int(os.getenv('SOURCE_CHAT_ID', '-1002674581978'))

if not BOT_TOKEN or not DATABASE_URL:
    logger.error("❌ متغيرات البيئة مفقودة!")
    sys.exit(1)

# إنشاء البوت و Flask
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# متغيرات النظام
should_stop = False
handlers_registered = False


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
    """تسجيل جميع المعالجات بالهيكل المنظم"""
    global handlers_registered
    
    logger.info("📝 تسجيل جميع المعالجات...")
    
    try:
        # معالجات البداية والأوامر الأساسية
        from app.handlers.start import register_start_handlers
        register_start_handlers(bot)
        logger.info("✅ تم تسجيل معالجات البداية")
        
        # معالجات الإدارة
        from app.handlers.admin import register_admin_handlers
        register_admin_handlers(bot)
        logger.info("✅ تم تسجيل معالجات الإدارة")
        
        # معالجات الأزرار
        from app.handlers.callbacks import register_all_callbacks
        register_all_callbacks(bot)
        logger.info("✅ تم تسجيل معالجات الأزرار")
        
        # معالجات النصوص
        from app.handlers.text import register_text_handlers
        register_text_handlers(bot)
        logger.info("✅ تم تسجيل معالجات النصوص")
        
        # معالج الفيديوهات (للمشرفين)
        from app.handlers.video_handler import register_video_handlers
        register_video_handlers(bot)
        logger.info("✅ تم تسجيل معالجات الفيديوهات")
        
        handlers_registered = True
        logger.info("🎉 تم تسجيل جميع المعالجات بنجاح")
        
    except Exception as e:
        logger.error(f"❌ خطأ في تسجيل المعالجات: {e}")
        # تسجيل أساسي فقط عند الفشل
        register_basic_handlers()


def register_basic_handlers():
    """تسجيل معالجات أساسية للطوارئ"""
    global handlers_registered
    
    logger.info("📝 تسجيل معالجات أساسية (الطوارئ)...")
    
    # معالج /start أساسي
    @bot.message_handler(commands=['start'])
    def emergency_start(message):
        user = message.from_user
        text = f"""🎬 **مرحباً {user.first_name}!**

✅ **البوت يعمل بكامل قوته مع Webhooks!**

🔍 **للبحث:** اكتب اسم الفيديو
🛠️ **لوحة الإدارة:** /admin (للمشرفين)

🤖 **الحالة:** متصل ويعمل 24/7
🌐 **نظام متطور مع هيكل منظم**"""
        
        markup = telebot.types.InlineKeyboardMarkup()
        btn_test = telebot.types.InlineKeyboardButton("🧪 اختبار", callback_data="emergency_test")
        markup.add(btn_test)
        
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    
    # معالج /admin أساسي
    @bot.message_handler(commands=['admin'])
    def emergency_admin(message):
        if message.from_user.id not in ADMIN_IDS:
            bot.reply_to(message, "❌ غير مصرح لك بالوصول")
            return
        
        try:
            from app.database.connection import check_database
            db_ok = check_database()
        except:
            db_ok = False
        
        text = f"""🛠️ **لوحة الإدارة (طارئ)**

👨‍💼 **المشرف:** {message.from_user.first_name}
🤖 **البوت:** ✅ يعمل
📡 **قاعدة البيانات:** {'✅ متصلة' if db_ok else '❌ منقطعة'}
🌐 **الطريقة:** Webhooks (مع هيكل منظم)

⚠️ **وضع طارئ - بعض الميزات قيد الاسترجاع**"""
        
        markup = telebot.types.InlineKeyboardMarkup()
        btn_test = telebot.types.InlineKeyboardButton("🧪 اختبار", callback_data="emergency_admin_test")
        markup.add(btn_test)
        
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
    
    # معالج الأزرار الأساسي
    @bot.callback_query_handler(func=lambda call: call.data.startswith('emergency_'))
    def emergency_callbacks(call):
        if call.data == "emergency_test":
            bot.answer_callback_query(call.id, "✅ البوت يعمل بكامل قوته!", show_alert=True)
        elif call.data == "emergency_admin_test":
            if call.from_user.id in ADMIN_IDS:
                bot.answer_callback_query(call.id, "✅ لوحة الإدارة تعمل!", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "❌ غير مصرح")
    
    # معالج بحث بسيط
    @bot.message_handler(content_types=['text'])
    def emergency_search(message):
        query = message.text.strip()
        if len(query) < 2:
            bot.reply_to(message, "🔍 اكتب نص أطول للبحث")
            return
        
        # محاولة بحث حقيقي
        try:
            from app.services.video_service import VideoService
            results = VideoService.search_videos(query, limit=5)
            
            if results:
                response = f"🔍 **نتائج البحث:** {query}\n\n📊 **العدد:** {len(results)}\n\n"
                for i, video in enumerate(results, 1):
                    title = video[1] or video[4] or f"فيديو {video[0]}"
                    title = title[:40] + "..." if len(title) > 40 else title
                    views = video[3] or 0
                    response += f"**{i}.** {title}\n   👁️ {views:,}\n\n"
                
                bot.reply_to(message, response, parse_mode='Markdown')
            else:
                bot.reply_to(message, f"❌ **لم يتم العثور على نتائج:** {query}\n\n💡 جرب كلمات أخرى", parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"❌ خطأ في البحث الطارئ: {e}")
            bot.reply_to(message, f"🔍 **تم البحث عن:** {query}\n\n❌ **لم يتم العثور على نتائج**\n\n💡 جرب كلمات أخرى أو تواصل مع المشرف", parse_mode='Markdown')
    
    handlers_registered = True
    logger.info("✅ تم تسجيل المعالجات الأساسية (طارئ)")


# === Flask Routes للـ Keep Alive و Webhooks ===

@app.route('/')
def home():
    try:
        from app.services.stats_service import StatsService
        stats = StatsService.get_general_stats()
    except Exception as e:
        stats = {'videos': 0, 'users': 0, 'categories': 0, 'error': str(e)}
    
    return {
        "status": "alive ✅",
        "service": "Telegram Video Archive Bot - Structured",
        "method": "Webhooks (No Conflicts)",
        "handlers": "registered ✅" if handlers_registered else "failed ❌",
        "architecture": "Organized Structure with Services",
        "users": stats.get('users', 0),
        "videos": stats.get('videos', 0),
        "categories": stats.get('categories', 0),
        "version": "2.0 Structured with pymediainfo",
        "features": [
            "Advanced Search with VideoService",
            "Smart Metadata Extraction (pymediainfo)", 
            "Favorites System with UserService",
            "Watch History Tracking",
            "Category Management with CategoryService",
            "Admin Panel",
            "Auto Archive with metadata parsing",
            "Organized Architecture"
        ]
    }


@app.route('/health')
def health_check():
    try:
        from app.database.connection import check_database
        db_status = "connected ✅" if check_database() else "disconnected ❌"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "bot": "webhook_active ✅",
        "handlers": "registered ✅" if handlers_registered else "failed ❌",
        "architecture": "structured",
        "method": "Webhooks"
    }


@app.route('/ping')
def ping():
    return f"pong ✅ - هيكل منظم مع Webhooks! - {time.strftime('%H:%M:%S')}"


@app.route('/stats')
def stats_endpoint():
    try:
        from app.services.stats_service import StatsService
        stats = StatsService.get_general_stats()
        return {
            "success": True,
            "data": stats,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to get stats: {str(e)}"}


@app.route('/structure')
def structure_info():
    """معلومات عن هيكل البوت"""
    return {
        "architecture": "Organized MVC Pattern",
        "components": {
            "handlers": ["start", "admin", "callbacks", "text", "video_handler"],
            "services": ["video_service", "user_service", "category_service", "stats_service"],
            "utils": ["metadata_extractor", "keep_alive"],
            "database": ["connection", "models"]
        },
        "features": {
            "search": "Advanced multi-field search with VideoService",
            "metadata": "Smart extraction with pymediainfo",
            "favorites": "User favorites management",
            "history": "Watch history tracking",
            "categories": "Hierarchical category system",
            "admin": "Complete admin panel"
        }
    }


@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    """معالج Webhook للبوت"""
    if not handlers_registered:
        logger.error("⚠️ Webhook received but handlers not registered!")
        return '', 500
        
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
    
    logger.info("🚀 بدء تشغيل بوت أرشيف الفيديوهات المتقدم (Structured Webhook Mode)")
    
    try:
        # التحقق من قاعدة البيانات
        from app.database.connection import init_database
        if not init_database():
            logger.warning("⚠️ مشكلة في قاعدة البيانات - البوت سيعمل بوضع محدود")
        else:
            logger.info("✅ تم الاتصال بقاعدة البيانات")
        
        # تسجيل المعالجات بالهيكل المنظم
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
        logger.info("🌐 الطريقة: Webhooks المتقدمة مع الهيكل المنظم")
        logger.info("⚙️ الميزات: بحث متقدم، بيانات وصفية، مفضلات، سجل مشاهدة")
        
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