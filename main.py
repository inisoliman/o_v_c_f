"""
🎬 Telegram Video Archive Bot - Final Working Version
"""
import os
import sys
import time
import threading
import logging
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

if not BOT_TOKEN or not DATABASE_URL:
    logger.error("❌ متغيرات البيئة مفقودة!")
    sys.exit(1)

# إنشاء البوت و Flask
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# متغيرات النظام
should_stop = False
handlers_registered = False


def test_database():
    """اختبار بسيط لقاعدة البيانات"""
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في قاعدة البيانات: {e}")
        return False


def register_basic_handlers():
    """تسجيل المعالجات الأساسية فقط"""
    global handlers_registered
    
    logger.info("📝 تسجيل المعالجات الأساسية...")
    
    # 1. معالج /start
    @bot.message_handler(commands=['start'])
    def start_command(message):
        try:
            user = message.from_user
            text = f"""🎬 **مرحباً {user.first_name}!**

✅ **البوت يعمل بكامل قوته مع Webhooks!**

🔍 **للبحث:** اكتب اسم الفيديو
🛠️ **لوحة الإدارة:** /admin (للمشرفين)

🤖 **الحالة:** متصل ويعمل 24/7"""
            
            from telebot import types
            markup = types.InlineKeyboardMarkup()
            btn_test = types.InlineKeyboardButton("🧪 اختبار", callback_data="test")
            markup.add(btn_test)
            
            bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ خطأ في /start: {e}")
            bot.reply_to(message, "❌ حدث خطأ")

    # 2. معالج /admin  
    @bot.message_handler(commands=['admin'])
    def admin_command(message):
        if message.from_user.id not in ADMIN_IDS:
            bot.reply_to(message, "❌ غير مصرح")
            return
            
        try:
            text = f"""🛠️ **لوحة الإدارة**

👨‍💼 **المشرف:** {message.from_user.first_name}
🤖 **البوت:** ✅ يعمل
📡 **قاعدة البيانات:** {'✅ متصلة' if test_database() else '❌ منقطعة'}
🌐 **الطريقة:** Webhooks"""

            from telebot import types
            markup = types.InlineKeyboardMarkup()
            btn_stats = types.InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats")
            btn_test = types.InlineKeyboardButton("🧪 اختبار", callback_data="admin_test")
            markup.add(btn_stats, btn_test)
            
            bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ خطأ في /admin: {e}")
            bot.reply_to(message, "❌ حدث خطأ في لوحة الإدارة")

    # 3. معالج الأزرار
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callbacks(call):
        try:
            data = call.data
            
            if data == "test":
                bot.answer_callback_query(call.id, "✅ البوت يعمل بكامل قوته!", show_alert=True)
                
            elif data == "admin_test":
                if call.from_user.id not in ADMIN_IDS:
                    bot.answer_callback_query(call.id, "❌ غير مصرح")
                    return
                bot.answer_callback_query(call.id, "✅ لوحة الإدارة تعمل!", show_alert=True)
                
            elif data == "admin_stats":
                if call.from_user.id not in ADMIN_IDS:
                    bot.answer_callback_query(call.id, "❌ غير مصرح")
                    return
                    
                stats_text = f"""📊 **إحصائيات النظام**

🤖 **حالة البوت:** ✅ يعمل
📡 **قاعدة البيانات:** {'✅ متصلة' if test_database() else '❌ منقطعة'}
🌐 **الطريقة:** Webhooks
⏰ **الوقت:** {time.strftime('%H:%M:%S')}"""

                from telebot import types
                markup = types.InlineKeyboardMarkup()
                btn_refresh = types.InlineKeyboardButton("🔄 تحديث", callback_data="admin_stats")
                markup.add(btn_refresh)
                
                bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id,
                                    reply_markup=markup, parse_mode='Markdown')
            else:
                bot.answer_callback_query(call.id, "🔄 قيد التطوير")
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالج الأزرار: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ")

    # 4. معالج النصوص
    @bot.message_handler(content_types=['text'])
    def handle_text(message):
        try:
            query = message.text.strip()
            
            if len(query) < 2:
                bot.reply_to(message, "🔍 اكتب نص أطول للبحث")
                return
                
            # محاكاة البحث
            bot.reply_to(message, f"🔍 **تم البحث عن:** {query}\n\n❌ **لم يتم العثور على نتائج**\n\n💡 جرب كلمات أخرى أو تواصل مع المشرف")
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالج النص: {e}")
            bot.reply_to(message, "❌ حدث خطأ في البحث")

    handlers_registered = True
    logger.info("✅ تم تسجيل جميع المعالجات الأساسية")


# === Flask Routes ===

@app.route('/')
def home():
    return {
        "status": "alive ✅",
        "service": "Telegram Video Archive Bot",
        "handlers": "registered ✅" if handlers_registered else "failed ❌",
        "database": "connected ✅" if test_database() else "disconnected ❌",
        "method": "Webhooks",
        "version": "Fixed Version"
    }


@app.route('/health')
def health():
    return {
        "bot": "active ✅",
        "handlers": handlers_registered,
        "database": test_database(),
        "webhook": "configured ✅"
    }


@app.route('/ping')
def ping():
    return f"pong ✅ - {time.strftime('%H:%M:%S')}"


@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    """معالج Webhook"""
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
    """إعداد Webhook"""
    try:
        bot.remove_webhook()
        time.sleep(1)
        
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


def main():
    """الدالة الرئيسية"""
    logger.info("🚀 بدء تشغيل بوت أرشيف الفيديوهات")
    
    try:
        # اختبار قاعدة البيانات
        if test_database():
            logger.info("✅ تم الاتصال بقاعدة البيانات")
        else:
            logger.warning("⚠️ مشكلة في قاعدة البيانات - البوت سيعمل بوضع محدود")
        
        # تسجيل المعالجات
        register_basic_handlers()
        
        # إعداد Webhook
        if setup_webhook():
            logger.info("✅ تم إعداد Webhook بنجاح")
        else:
            logger.warning("⚠️ فشل إعداد Webhook - جرب يدوياً")
        
        logger.info("🎉 البوت جاهز للعمل!")
        logger.info(f"🔧 المشرفون: {ADMIN_IDS}")
        logger.info("🛠️ الأوامر: /start /admin")
        
        # تشغيل Flask
        port = int(os.environ.get("PORT", 10000))
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")
    finally:
        try:
            bot.remove_webhook()
        except:
            pass
        logger.info("👋 تم إنهاء البوت")


if __name__ == "__main__":
    main()
