"""
🎬 Telegram Video Archive Bot - مع Keep Alive مدمج
بوت أرشيف الفيديوهات المتقدم مع نظام منع السكون
"""
import asyncio
import logging
import sys
import os
import threading
import time
from datetime import datetime
from pathlib import Path

# Flask للـ Keep Alive
from flask import Flask, jsonify
import requests

sys.path.append(str(Path(__file__).parent))

from app.core.config import settings
from app.core.database import init_db, close_db
from telegram.ext import Application
from app.handlers import register_handlers

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === نظام Keep Alive ===
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return jsonify({
        "status": "alive",
        "service": "Telegram Video Archive Bot",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running 24/7"
    })

@app_flask.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "database": "connected",
        "bot": "active",
        "timestamp": datetime.now().isoformat()
    })

@app_flask.route('/ping')
def ping():
    return "pong - Bot is alive!"

def run_flask():
    """تشغيل خادم Flask في خيط منفصل"""
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def self_ping():
    """نظام الـ Self Ping لمنع السكون"""
    time.sleep(60)  # انتظار دقيقة قبل البدء
    while True:
        try:
            time.sleep(840)  # 14 دقيقة
            render_url = os.environ.get("RENDER_EXTERNAL_URL")
            if render_url:
                response = requests.get(f"{render_url}/ping", timeout=30)
                logger.info(f"✅ Self-ping successful: {response.status_code}")
            else:
                # إذا لم يكن الرابط متاح، استخدم localhost
                response = requests.get("http://localhost:10000/ping", timeout=10)
                logger.info(f"✅ Local ping successful: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Self-ping failed: {e}")

async def main() -> None:
    """نقطة الدخول الرئيسية للبوت"""
    try:
        logger.info("🚀 بدء تشغيل بوت أرشيف الفيديوهات...")
        
        # بدء خادم Flask في خيط منفصل
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logger.info("✅ Flask server started for Keep Alive")
        
        # بدء نظام Self-Ping في خيط منفصل
        ping_thread = threading.Thread(target=self_ping, daemon=True)
        ping_thread.start()
        logger.info("✅ Self-ping system started")
        
        # تهيئة قاعدة البيانات
        await init_db()
        logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")
        
        # إنشاء تطبيق التليجرام
        application = (
            Application.builder()
            .token(settings.BOT_TOKEN)
            .concurrent_updates(True)
            .connect_timeout(60)
            .read_timeout(60)
            .write_timeout(60)
            .build()
        )
        
        # تسجيل المعالجات
        register_handlers(application)
        logger.info("✅ تم تسجيل جميع المعالجات")
        
        # بدء البوت
        logger.info("🎬 بدء تشغيل البوت مع Keep Alive...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
        
        logger.info("🎉 البوت يعمل بنجاح مع Keep Alive System!")
        logger.info("🔄 النظام سيمنع السكون تلقائياً كل 14 دقيقة")
        
        # إبقاء البوت يعمل
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")
        raise
    finally:
        if 'application' in locals():
            await application.stop()
        await close_db()
        logger.info("⏹️ تم إيقاف البوت")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")
        sys.exit(1)
