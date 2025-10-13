"""
نظام Keep Alive لمنع سكون البوت على Render.com
"""
import os
import time
import threading
import logging
import requests
from datetime import datetime
from flask import Flask, jsonify

logger = logging.getLogger(__name__)

app_flask = Flask(__name__)


@app_flask.route('/')
def home():
    # استيراد محلي لتجنب circular imports
    try:
        from app.services.stats_service import StatsService
        stats = StatsService.get_general_stats()
    except:
        stats = {'videos': 0, 'users': 0, 'categories': 0}
    
    return jsonify({
        "status": "alive ✅",
        "service": "Telegram Video Archive Bot",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running 24/7 - مجاني مدى الحياة 🎉",
        "users": stats.get('users', 0),
        "videos": stats.get('videos', 0),
        "categories": stats.get('categories', 0),
        "version": "2.0 Full Architecture"
    })


@app_flask.route('/health')
def health_check():
    try:
        from app.database.connection import check_database
        db_status = "connected ✅" if check_database() else "disconnected ❌"
    except:
        db_status = "unknown ❓"
    
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "bot": "active ✅",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "search", "favorites", "history", "categories", 
            "admin_panel", "keep_alive", "auto_cleanup"
        ]
    })


@app_flask.route('/ping')
def ping():
    return f"pong ✅ - البوت يعمل بنجاح! | {datetime.now().strftime('%H:%M:%S')}"


@app_flask.route('/stats')
def stats_endpoint():
    try:
        from app.services.stats_service import StatsService
        stats = StatsService.get_general_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({
            "error": f"Failed to get stats: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })


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
                response = requests.get("http://localhost:10000/ping", timeout=10)
                logger.info(f"✅ Local ping successful")
                
        except Exception as e:
            logger.warning(f"⚠️ Self-ping failed: {e}")


def run_keep_alive_system():
    """بدء نظام Keep Alive الكامل"""
    # بدء خادم Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask Keep Alive server started")
    
    # بدء نظام Self-Ping
    ping_thread = threading.Thread(target=self_ping, daemon=True)
    ping_thread.start()
    logger.info("✅ Self-ping anti-sleep system started")
