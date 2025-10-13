"""
🎬 Telegram Video Archive Bot - الإصدار الكامل
بوت أرشيف الفيديوهات المتقدم مع جميع الوظائف
"""
import os
import time
import threading
import logging
import requests
import psycopg2
from datetime import datetime, timedelta
from flask import Flask, jsonify
from dotenv import load_dotenv
import telebot
from telebot import types
import schedule
import json

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
SOURCE_CHAT_ID = int(os.getenv('SOURCE_CHAT_ID', '0')) if os.getenv('SOURCE_CHAT_ID') else None

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN غير موجود!")
    exit(1)

if not DATABASE_URL:
    logger.error("❌ DATABASE_URL غير موجود!")
    exit(1)

# إنشاء البوت
bot = telebot.TeleBot(BOT_TOKEN)

# حالة المستخدم (للبحث المتقدم)
user_states = {}

# === نظام Keep Alive ===
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return jsonify({
        "status": "alive ✅",
        "service": "Telegram Video Archive Bot",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running 24/7 - مجاني مدى الحياة 🎉",
        "users": get_users_count(),
        "videos": get_videos_count(),
        "categories": get_categories_count(),
        "version": "2.0 Full"
    })

@app_flask.route('/health')
def health_check():
    db_status = "connected ✅" if check_database() else "disconnected ❌"
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "bot": "active ✅",
        "timestamp": datetime.now().isoformat(),
        "features": ["search", "favorites", "history", "categories", "admin_panel"]
    })

@app_flask.route('/ping')
def ping():
    return f"pong ✅ - البوت يعمل بنجاح! | {datetime.now().strftime('%H:%M:%S')}"

@app_flask.route('/stats')
def stats():
    return jsonify({
        "users": get_users_count(),
        "videos": get_videos_count(),
        "categories": get_categories_count(),
        "favorites": get_favorites_count(),
        "last_update": datetime.now().isoformat()
    })

def run_flask():
    """تشغيل خادم Flask في خيط منفصل"""
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def self_ping():
    """نظام الـ Self Ping لمنع السكون"""
    time.sleep(60)
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

# === قاعدة البيانات الكاملة ===
def get_db_connection():
    """الاتصال بقاعدة البيانات"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
        return None

def check_database():
    """فحص اتصال قاعدة البيانات"""
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
    except:
        pass
    return False

def init_database():
    """تهيئة قاعدة البيانات"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # التحقق من وجود الجداول
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('video_archive', 'categories', 'bot_users', 'user_history', 'user_favorites')
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"✅ جداول موجودة: {existing_tables}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        return False

def get_users_count():
    """عدد المستخدمين"""
    try:
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bot_users")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except:
        return 0

def get_videos_count():
    """عدد الفيديوهات"""
    try:
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM video_archive")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except:
        return 0

def get_categories_count():
    """عدد التصنيفات"""
    try:
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except:
        return 0

def get_favorites_count():
    """عدد المفضلات الكلي"""
    try:
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_favorites")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except:
        return 0

def add_user(user_id, username, first_name, last_name=None):
    """إضافة/تحديث مستخدم"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO bot_users (user_id, username, first_name, join_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name
        """, (user_id, username, first_name, datetime.now()))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في إضافة المستخدم: {e}")
        return False

def search_videos(query, limit=20):
    """البحث في الفيديوهات"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, caption, view_count, file_name, file_size, category_id, upload_date
            FROM video_archive 
            WHERE (title ILIKE %s OR caption ILIKE %s OR file_name ILIKE %s)
            ORDER BY view_count DESC, upload_date DESC
            LIMIT %s
        """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"❌ خطأ في البحث: {e}")
        return []

def get_video_by_id(video_id):
    """الحصول على فيديو بالمعرف"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT v.id, v.message_id, v.caption, v.chat_id, v.file_name, v.file_id, 
                   v.category_id, v.metadata, v.view_count, v.title, v.grouping_key, 
                   v.upload_date, c.name as category_name, v.file_size
            FROM video_archive v
            LEFT JOIN categories c ON v.category_id = c.id
            WHERE v.id = %s
        """, (video_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"❌ خطأ في الحصول على الفيديو: {e}")
        return None

def get_categories():
    """الحصول على جميع التصنيفات"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.id, c.name, COUNT(v.id) as video_count
            FROM categories c
            LEFT JOIN video_archive v ON c.id = v.category_id
            GROUP BY c.id, c.name
            HAVING COUNT(v.id) > 0
            ORDER BY video_count DESC, c.name
            LIMIT 20
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"❌ خطأ في الحصول على التصنيفات: {e}")
        return []

def get_videos_by_category(category_id, limit=20):
    """الحصول على فيديوهات تصنيف معين"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, caption, view_count, file_name, upload_date
            FROM video_archive 
            WHERE category_id = %s
            ORDER BY view_count DESC, upload_date DESC
            LIMIT %s
        """, (category_id, limit))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"❌ خطأ في فيديوهات التصنيف: {e}")
        return []

def get_user_favorites(user_id, limit=20):
    """الحصول على مفضلات المستخدم"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT v.id, v.title, v.caption, v.view_count, v.file_name, f.added_date
            FROM user_favorites f
            JOIN video_archive v ON f.video_id = v.id
            WHERE f.user_id = %s
            ORDER BY f.added_date DESC
            LIMIT %s
        """, (user_id, limit))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"❌ خطأ في المفضلات: {e}")
        return []

def get_user_history(user_id, limit=20):
    """الحصول على سجل المستخدم"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT v.id, v.title, v.caption, v.view_count, v.file_name, h.last_watched
            FROM user_history h
            JOIN video_archive v ON h.video_id = v.id
            WHERE h.user_id = %s
            ORDER BY h.last_watched DESC
            LIMIT %s
        """, (user_id, limit))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"❌ خطأ في السجل: {e}")
        return []

def update_view_count(video_id):
    """زيادة عداد المشاهدة"""
    try:
        conn = get_db_connection()
        if not conn:
            return
        cursor = conn.cursor()
        cursor.execute("UPDATE video_archive SET view_count = view_count + 1 WHERE id = %s", (video_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث عداد المشاهدة: {e}")

def add_to_history(user_id, video_id):
    """إضافة إلى سجل المشاهدة"""
    try:
        conn = get_db_connection()
        if not conn:
            return
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_history (user_id, video_id, last_viewed, last_watched)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, video_id) DO UPDATE SET
                last_viewed = EXCLUDED.last_viewed,
                last_watched = EXCLUDED.last_watched
        """, (user_id, video_id, datetime.now(), datetime.now()))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ خطأ في إضافة إلى السجل: {e}")

def toggle_favorite(user_id, video_id):
    """إضافة/إزالة من المفضلة"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        
        # فحص إذا كان في المفضلة
        cursor.execute("SELECT id FROM user_favorites WHERE user_id = %s AND video_id = %s", (user_id, video_id))
        exists = cursor.fetchone()
        
        if exists:
            # إزالة من المفضلة
            cursor.execute("DELETE FROM user_favorites WHERE user_id = %s AND video_id = %s", (user_id, video_id))
            conn.commit()
            cursor.close()
            conn.close()
            return False  # تم إزالته
        else:
            # إضافة للمفضلة
            cursor.execute("""
                INSERT INTO user_favorites (user_id, video_id, added_date, date_added)
                VALUES (%s, %s, %s, %s)
            """, (user_id, video_id, datetime.now(), datetime.now()))
            conn.commit()
            cursor.close()
            conn.close()
            return True  # تم إضافته
            
    except Exception as e:
        logger.error(f"❌ خطأ في المفضلة: {e}")
        return False

def is_favorite(user_id, video_id):
    """فحص إذا كان الفيديو في المفضلة"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM user_favorites WHERE user_id = %s AND video_id = %s", (user_id, video_id))
        exists = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return bool(exists)
    except:
        return False

def get_popular_videos(limit=10):
    """الحصول على أشهر الفيديوهات"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, caption, view_count, file_name, upload_date
            FROM video_archive 
            WHERE view_count > 0
            ORDER BY view_count DESC, upload_date DESC
            LIMIT %s
        """, (limit,))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"❌ خطأ في الفيديوهات الشائعة: {e}")
        return []

def get_recent_videos(limit=10):
    """الحصول على أحدث الفيديوهات"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, caption, view_count, file_name, upload_date
            FROM video_archive 
            ORDER BY upload_date DESC
            LIMIT %s
        """, (limit,))
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"❌ خطأ في الفيديوهات الحديثة: {e}")
        return []

# === معالجات البوت الكاملة ===

@bot.message_handler(commands=['start'])
def start_command(message):
    """معالج أمر البداية"""
    user = message.from_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = f"""🎬 **مرحباً بك في أرشيف الفيديوهات المتقدم!**

👋 أهلاً {user.first_name}!

🔍 **للبحث السريع:** اكتب اسم الفيديو مباشرة
📚 **التصنيفات:** تصفح المحتوى حسب النوع
⭐ **المفضلة:** احفظ الفيديوهات المفضلة لديك
📊 **السجل:** راجع تاريخ مشاهدتك

📈 **إحصائيات الأرشيف:**
🎬 الفيديوهات: {get_videos_count():,}
👥 المستخدمون: {get_users_count():,}
📚 التصنيفات: {get_categories_count():,}
⭐ المفضلات: {get_favorites_count():,}

🤖 **البوت يعمل 24/7 مجاناً مع Keep Alive System!**

📝 اكتب اسم الفيديو للبحث أو استخدم الأزرار:"""
    
    # إنشاء لوحة المفاتيح
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_search = types.InlineKeyboardButton("🔍 البحث المتقدم", callback_data="search")
    btn_categories = types.InlineKeyboardButton("📚 التصنيفات", callback_data="categories")
    btn_favorites = types.InlineKeyboardButton("⭐ مفضلاتي", callback_data="favorites")
    btn_history = types.InlineKeyboardButton("📊 سجل المشاهدة", callback_data="history")
    btn_popular = types.InlineKeyboardButton("🔥 الأشهر", callback_data="popular")
    btn_recent = types.InlineKeyboardButton("🆕 الأحدث", callback_data="recent")
    btn_stats = types.InlineKeyboardButton("📈 الإحصائيات", callback_data="stats")
    btn_help = types.InlineKeyboardButton("❓ المساعدة", callback_data="help")
    
    markup.add(btn_search, btn_categories)
    markup.add(btn_favorites, btn_history)
    markup.add(btn_popular, btn_recent)
    markup.add(btn_stats, btn_help)
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['admin'])
def admin_command(message):
    """لوحة تحكم الإدارة الكاملة"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ غير مصرح لك بالوصول")
        return
    
    stats_text = f"""🛠️ **لوحة التحكم الإدارية الكاملة**

📊 **الإحصائيات التفصيلية:**
├ 🎬 الفيديوهات: {get_videos_count():,}
├ 👥 المستخدمون: {get_users_count():,}
├ 📚 التصنيفات: {get_categories_count():,}
├ ⭐ المفضلات: {get_favorites_count():,}
└ 🕒 آخر تحديث: {datetime.now().strftime('%H:%M')}

🤖 **حالة النظام:**
├ قاعدة البيانات: {'✅ متصلة' if check_database() else '❌ منقطعة'}
├ Keep Alive System: ✅ يعمل
├ Auto Cleanup: ✅ مفعل (15 يوم)
└ Self-Ping: ✅ كل 14 دقيقة

🌐 **روابط المراقبة:**
• [الحالة العامة](https://o-v-c-f.onrender.com)
• [فحص الصحة](https://o-v-c-f.onrender.com/health)
• [الإحصائيات](https://o-v-c-f.onrender.com/stats)

⚙️ **المدير:** {message.from_user.first_name}"""
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_back)
    
    bot.send_message(message.chat.id, stats_text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(content_types=['text'])
def text_handler(message):
    """معالج النصوص للبحث الذكي"""
    user_id = message.from_user.id
    query = message.text.strip()
    
    # التحقق من حالة المستخدم
    if user_id in user_states:
        state = user_states[user_id]
        if state.get('action') == 'searching':
            # المستخدم في وضع البحث المتقدم
            handle_search_input(message, query)
            return
    
    if len(query) < 2:
        bot.reply_to(message, "🔍 يرجى كتابة كلمة بحث أكثر من حرف واحد")
        return
    
    # بحث سريع
    wait_msg = bot.reply_to(message, "🔍 جاري البحث في الأرشيف...")
    
    results = search_videos(query, 15)
    
    if not results:
        no_results_text = f"❌ **لم يتم العثور على نتائج للبحث:** {query}\n\n"
        no_results_text += "💡 **اقتراحات:**\n"
        no_results_text += "• جرب كلمات أخرى\n"
        no_results_text += "• البحث بالإنجليزية\n"
        no_results_text += "• تصفح التصنيفات\n"
        no_results_text += "• تصفح الأشهر والأحدث"
        
        markup = types.InlineKeyboardMarkup()
        btn_categories = types.InlineKeyboardButton("📚 التصنيفات", callback_data="categories")
        btn_popular = types.InlineKeyboardButton("🔥 الأشهر", callback_data="popular")
        btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        markup.add(btn_categories, btn_popular)
        markup.add(btn_back)
        
        bot.edit_message_text(no_results_text, wait_msg.chat.id, wait_msg.message_id, 
                             reply_markup=markup, parse_mode='Markdown')
        return
    
    # تنسيق النتائج
    text = f"🔍 **نتائج البحث عن:** {query}\n"
    text += f"📊 تم العثور على **{len(results)}** نتيجة\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    for i, video in enumerate(results[:10], 1):
        title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
        title = title[:50] + "..." if len(title) > 50 else title
        
        views = video[3] if video[3] else 0
        size = f" | 💾 {video[5]//1024//1024:.0f}MB" if video[5] and video[5] > 0 else ""
        date = f" | 📅 {video[7].strftime('%m/%d')}" if video[7] else ""
        
        text += f"**{i}.** {title}\n   👁️ {views:,}{size}{date}\n\n"
        
        btn = types.InlineKeyboardButton(f"📺 {title[:25]}...", callback_data=f"video_{video[0]}")
        markup.add(btn)
    
    if len(results) > 10:
        text += f"**... و {len(results) - 10} نتيجة أخرى**\n"
    
    btn_more = types.InlineKeyboardButton("🔍 بحث متقدم", callback_data="search")
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_more, btn_back)
    
    bot.edit_message_text(text, wait_msg.chat.id, wait_msg.message_id, 
                         reply_markup=markup, parse_mode='Markdown')

def handle_search_input(message, query):
    """معالج إدخال البحث المتقدم"""
    user_id = message.from_user.id
    
    # إزالة حالة البحث
    if user_id in user_states:
        del user_states[user_id]
    
    # تنفيذ البحث المتقدم
    wait_msg = bot.reply_to(message, "🔍 جاري البحث المتقدم...")
    
    results = search_videos(query, 20)
    
    if not results:
        bot.edit_message_text(f"❌ لم يتم العثور على نتائج للبحث: **{query}**", 
                             wait_msg.chat.id, wait_msg.message_id, parse_mode='Markdown')
        return
    
    # عرض النتائج مع خيارات متقدمة
    show_search_results(wait_msg.chat.id, wait_msg.message_id, results, query)

def show_search_results(chat_id, message_id, results, query):
    """عرض نتائج البحث مع التحكم"""
    text = f"🎯 **نتائج البحث المتقدم:** {query}\n"
    text += f"📊 العدد: **{len(results)}** نتيجة\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    # أول 8 نتائج
    for i, video in enumerate(results[:8], 1):
        title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
        title_short = title[:40] + "..." if len(title) > 40 else title
        
        text += f"**{i}.** {title_short}\n"
        
        btn = types.InlineKeyboardButton(f"{i}. {title[:20]}...", callback_data=f"video_{video[0]}")
        
        if i % 2 == 1 and i < len(results[:8]):
            # إضافة زرين في صف واحد
            next_video = results[i] if i < len(results[:8]) else None
            if next_video:
                next_title = next_video[1] if next_video[1] else (next_video[4] if next_video[4] else f"فيديو {next_video[0]}")
                btn2 = types.InlineKeyboardButton(f"{i+1}. {next_title[:20]}...", callback_data=f"video_{next_video[0]}")
                markup.add(btn, btn2)
                text += f"**{i+1}.** {next_title[:40] + '...' if len(next_title) > 40 else next_title}\n"
            else:
                markup.add(btn)
        elif i % 2 == 0:
            # تم إضافته مع السابق
            pass
        else:
            markup.add(btn)
        
        text += "\n"
    
    if len(results) > 8:
        btn_more = types.InlineKeyboardButton(f"📋 عرض الكل ({len(results)})", callback_data=f"search_all_{query}")
        markup.add(btn_more)
    
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_back)
    
    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """معالج الأزرار الكامل"""
    try:
        user_id = call.from_user.id
        data = call.data
        
        if data == "main_menu":
            # العودة للقائمة الرئيسية
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start_command(call.message)
            
        elif data == "search":
            # البحث المتقدم
            search_text = """🔍 **البحث المتقدم**

📝 **كيفية البحث:**
• اكتب اسم الفيديو أو المسلسل
• يمكن البحث بالعربية أو الإنجليزية
• البحث في العنوان والوصف واسم الملف

💡 **أمثلة للبحث:**
• `الاختيار` - للبحث عن مسلسل
• `2023` - للبحث عن فيديوهات سنة معينة
• `HD` - للبحث عن جودة معينة

📝 **اكتب كلمة البحث الآن:**"""
            
            # تعيين حالة المستخدم
            user_states[user_id] = {'action': 'searching'}
            
            markup = types.InlineKeyboardMarkup()
            btn_cancel = types.InlineKeyboardButton("❌ إلغاء", callback_data="main_menu")
            markup.add(btn_cancel)
            
            bot.edit_message_text(search_text, call.message.chat.id, call.message.message_id,
                                reply_markup=markup, parse_mode='Markdown')
                                
        elif data == "categories":
            # عرض التصنيفات
            categories = get_categories()
            
            if not categories:
                bot.edit_message_text("❌ لا توجد تصنيفات متاحة", 
                                    call.message.chat.id, call.message.message_id)
                return
            
            text = f"📚 **التصنيفات المتاحة**\n\n"
            text += f"اختر التصنيف لتصفح محتواه:\n\n"
            
            markup = types.InlineKeyboardMarkup()
            
            for category in categories[:15]:
                cat_name = category[1][:30] + "..." if len(category[1]) > 30 else category[1]
                text += f"📁 **{cat_name}** - {category[2]} فيديو\n"
                
                btn = types.InlineKeyboardButton(f"📁 {cat_name} ({category[2]})", 
                                               callback_data=f"category_{category[0]}")
                markup.add(btn)
            
            btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            markup.add(btn_back)
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=markup, parse_mode='Markdown')
                                
        elif data.startswith("category_"):
            # عرض فيديوهات تصنيف معين
            category_id = int(data.replace("category_", ""))
            videos = get_videos_by_category(category_id, 15)
            
            if not videos:
                bot.answer_callback_query(call.id, "❌ لا توجد فيديوهات في هذا التصنيف")
                return
                
            text = f"📁 **فيديوهات التصنيف**\n\n"
            
            markup = types.InlineKeyboardMarkup()
            
            for i, video in enumerate(videos[:10], 1):
                title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
                title_short = title[:45] + "..." if len(title) > 45 else title
                views = video[3] if video[3] else 0
                
                text += f"**{i}.** {title_short}\n   👁️ {views:,}\n\n"
                
                btn = types.InlineKeyboardButton(f"{i}. {title[:25]}...", callback_data=f"video_{video[0]}")
                markup.add(btn)
            
            btn_categories = types.InlineKeyboardButton("📚 التصنيفات", callback_data="categories")
            btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            markup.add(btn_categories, btn_back)
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=markup, parse_mode='Markdown')
                                
        elif data == "favorites":
            # عرض المفضلات
            favorites = get_user_favorites(user_id, 15)
            
            if not favorites:
                empty_text = f"⭐ **مفضلاتي**\n\n"
                empty_text += f"❌ لا توجد فيديوهات في المفضلة بعد\n\n"
                empty_text += f"💡 **كيفية الإضافة:**\n"
                empty_text += f"• اختر أي فيديو\n"
                empty_text += f"• اضغط زر 💖 مفضلة"
                
                markup = types.InlineKeyboardMarkup()
                btn_search = types.InlineKeyboardButton("🔍 البحث", callback_data="search")
                btn_popular = types.InlineKeyboardButton("🔥 الأشهر", callback_data="popular")
                btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
                markup.add(btn_search, btn_popular)
                markup.add(btn_back)
                
                bot.edit_message_text(empty_text, call.message.chat.id, call.message.message_id,
                                    reply_markup=markup, parse_mode='Markdown')
                return
                
            text = f"⭐ **مفضلاتي** ({len(favorites)})\n\n"
            
            markup = types.InlineKeyboardMarkup()
            
            for i, video in enumerate(favorites[:10], 1):
                title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
                title_short = title[:45] + "..." if len(title) > 45 else title
                added_date = video[5].strftime('%m/%d') if video[5] else ""
                
                text += f"**{i}.** {title_short}\n   ⭐ {added_date}\n\n"
                
                btn = types.InlineKeyboardButton(f"{i}. {title[:25]}...", callback_data=f"video_{video[0]}")
                markup.add(btn)
                
            btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            markup.add(btn_back)
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=markup, parse_mode='Markdown')
                                
        elif data == "history":
            # عرض سجل المشاهدة
            history = get_user_history(user_id, 15)
            
            if not history:
                empty_text = f"📊 **سجل المشاهدة**\n\n"
                empty_text += f"❌ لا يوجد سجل مشاهدة بعد\n\n"
                empty_text += f"💡 **كيفية تكوين السجل:**\n"
                empty_text += f"• اختر أي فيديو لمشاهدة تفاصيله\n"
                empty_text += f"• سيتم حفظه في السجل تلقائياً\n"
                empty_text += f"• السجل يُحذف تلقائياً بعد 15 يوم"
                
                markup = types.InlineKeyboardMarkup()
                btn_search = types.InlineKeyboardButton("🔍 البحث", callback_data="search")
                btn_categories = types.InlineKeyboardButton("📚 التصنيفات", callback_data="categories")
                btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
                markup.add(btn_search, btn_categories)
                markup.add(btn_back)
                
                bot.edit_message_text(empty_text, call.message.chat.id, call.message.message_id,
                                    reply_markup=markup, parse_mode='Markdown')
                return
                
            text = f"📊 **سجل المشاهدة** ({len(history)})\n\n"
            
            markup = types.InlineKeyboardMarkup()
            
            for i, video in enumerate(history[:10], 1):
                title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
                title_short = title[:45] + "..." if len(title) > 45 else title
                watch_date = video[5].strftime('%m/%d %H:%M') if video[5] else ""
                
                text += f"**{i}.** {title_short}\n   🕒 {watch_date}\n\n"
                
                btn = types.InlineKeyboardButton(f"{i}. {title[:25]}...", callback_data=f"video_{video[0]}")
                markup.add(btn)
                
            btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            markup.add(btn_back)
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=markup, parse_mode='Markdown')
                                
        elif data == "popular":
            # عرض الأشهر
            popular = get_popular_videos(15)
            
            if not popular:
                bot.edit_message_text("❌ لا توجد فيديوهات شائعة", 
                                    call.message.chat.id, call.message.message_id)
                return
                
            text = f"🔥 **الفيديوهات الأشهر**\n\n"
            
            markup = types.InlineKeyboardMarkup()
            
            for i, video in enumerate(popular[:10], 1):
                title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
                title_short = title[:45] + "..." if len(title) > 45 else title
                views = video[3] if video[3] else 0
                
                text += f"**{i}.** {title_short}\n   👁️ {views:,} مشاهدة\n\n"
                
                btn = types.InlineKeyboardButton(f"{i}. {title[:25]}...", callback_data=f"video_{video[0]}")
                markup.add(btn)
                
            btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            markup.add(btn_back)
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=markup, parse_mode='Markdown')
                                
        elif data == "recent":
            # عرض الأحدث
            recent = get_recent_videos(15)
            
            if not recent:
                bot.edit_message_text("❌ لا توجد فيديوهات حديثة", 
                                    call.message.chat.id, call.message.message_id)
                return
                
            text = f"🆕 **أحدث الفيديوهات**\n\n"
            
            markup = types.InlineKeyboardMarkup()
            
            for i, video in enumerate(recent[:10], 1):
                title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
                title_short = title[:45] + "..." if len(title) > 45 else title
                upload_date = video[5].strftime('%m/%d') if video[5] else ""
                
                text += f"**{i}.** {title_short}\n   📅 {upload_date}\n\n"
                
                btn = types.InlineKeyboardButton(f"{i}. {title[:25]}...", callback_data=f"video_{video[0]}")
                markup.add(btn)
                
            btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            markup.add(btn_back)
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=markup, parse_mode='Markdown')
                                
        elif data == "stats":
            # الإحصائيات التفصيلية
            stats_text = f"""📊 **إحصائيات أرشيف الفيديوهات**

📈 **الأرقام الإجمالية:**
🎬 **الفيديوهات:** {get_videos_count():,}
👥 **المستخدمون:** {get_users_count():,}  
📚 **التصنيفات:** {get_categories_count():,}
⭐ **المفضلات:** {get_favorites_count():,}

🤖 **حالة النظام:**
✅ **البوت يعمل 24/7** مع نظام Keep Alive
🔄 **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
🗂️ **تنظيف تلقائي:** كل 15 يوم للسجل
🔁 **Self-ping:** كل 14 دقيقة لمنع السكون

🌐 **روابط المراقبة:**
• [الصفحة الرئيسية](https://o-v-c-f.onrender.com)
• [فحص الصحة](https://o-v-c-f.onrender.com/health)

🚀 **استمتع بتصفح الأرشيف المجاني!**"""
            
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            markup.add(btn_back)
            
            bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, 
                                reply_markup=markup, parse_mode='Markdown')
                                
        elif data == "help":
            # المساعدة الشاملة
            help_text = """🎬 **مساعدة أرشيف الفيديوهات**

**🔍 البحث:**
• **البحث السريع:** اكتب اسم الفيديو مباشرة
• **البحث المتقدم:** استخدم زر "البحث المتقدم"
• **يدعم العربية والإنجليزية**
• **يبحث في:** العنوان، الوصف، اسم الملف

**📚 التصنيفات:**
• تصفح المحتوى حسب النوع
• أكثر من 20 تصنيف متاح
• مئات الفيديوهات منظمة

**⭐ المفضلة:**
• احفظ الفيديوهات المفضلة
• وصول سريع لمحتواك
• إضافة/إزالة بضغطة واحدة

**📊 سجل المشاهدة:**
• تتبع تلقائي لما شاهدته
• **حذف تلقائي بعد 15 يوم**
• مراجعة سريعة لآخر نشاطك

**🔥 الأشهر & 🆕 الأحدث:**
• اكتشف المحتوى الشائع
• آخر الإضافات للأرشيف

**🤖 مميزات النظام:**
✅ **يعمل 24/7 مجاناً**
✅ **Keep Alive System**
✅ **تنظيف تلقائي للسجل**
✅ **استجابة فورية**

**🌐 المراقبة والحالة:**
يمكن متابعة حالة البوت على:
[o-v-c-f.onrender.com](https://o-v-c-f.onrender.com)

للمساعدة أو الاستفسار تواصل مع المشرف"""
            
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            markup.add(btn_back)
            
            bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id,
                                reply_markup=markup, parse_mode='Markdown')
                                
        elif data.startswith("video_"):
            # عرض تفاصيل الفيديو
            video_id = int(data.replace("video_", ""))
            video = get_video_by_id(video_id)
            
            if not video:
                bot.answer_callback_query(call.id, "❌ الفيديو غير موجود")
                return
            
            # زيادة عداد المشاهدة وإضافة للسجل
            update_view_count(video_id)
            add_to_history(user_id, video_id)
            
            # تنسيق معلومات الفيديو
            title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
            text = f"🎬 **{title}**\n\n"
            
            if video[2]:  # caption/description
                desc = video[2][:300] + "..." if len(video[2]) > 300 else video[2]
                text += f"📝 **الوصف:**\n{desc}\n\n"
            
            if video[12]:  # category_name
                text += f"📚 **التصنيف:** {video[12]}\n"
            
            if video[4]:  # file_name
                file_name = video[4][:60] + "..." if len(video[4]) > 60 else video[4]
                text += f"📄 **اسم الملف:** {file_name}\n"
                
            if video[13] and video[13] > 0:  # file_size
                size_mb = video[13] / (1024 * 1024)
                text += f"💾 **الحجم:** {size_mb:.1f} MB\n"
                
            text += f"\n📊 **الإحصائيات:**\n"
            text += f"👁️ **المشاهدات:** {video[8]:,}\n"  # view_count
            
            if video[11]:  # upload_date
                upload_date = video[11].strftime('%Y-%m-%d')
                text += f"📅 **تاريخ الرفع:** {upload_date}\n"
            
            # فحص إذا كان في المفضلة
            is_fav = is_favorite(user_id, video_id)
            fav_text = "❤️ إزالة من المفضلة" if is_fav else "💖 إضافة للمفضلة"
            
            markup = types.InlineKeyboardMarkup()
            
            # أزرار التحكم
            buttons_row1 = []
            buttons_row2 = []
            
            if video[5]:  # file_id exists - يمكن التحميل
                btn_download = types.InlineKeyboardButton("📥 تحميل", callback_data=f"download_{video_id}")
                buttons_row1.append(btn_download)
            
            btn_favorite = types.InlineKeyboardButton(fav_text, callback_data=f"favorite_{video_id}")
            buttons_row1.append(btn_favorite)
            
            if len(buttons_row1) > 0:
                markup.add(*buttons_row1)
            
            # أزرار إضافية
            if video[6]:  # category_id - عرض المزيد من نفس التصنيف
                btn_more_cat = types.InlineKeyboardButton("📚 المزيد من التصنيف", callback_data=f"category_{video[6]}")
                buttons_row2.append(btn_more_cat)
            
            btn_share = types.InlineKeyboardButton("📤 مشاركة", callback_data=f"share_{video_id}")
            buttons_row2.append(btn_share)
            
            if len(buttons_row2) > 0:
                markup.add(*buttons_row2)
            
            # أزرار التنقل
            btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
            markup.add(btn_back)
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=markup, parse_mode='Markdown')
                                
        elif data.startswith("download_"):
            # تحميل الفيديو
            video_id = int(data.replace("download_", ""))
            video = get_video_by_id(video_id)
            
            if not video or not video[5]:  # لا يوجد file_id
                bot.answer_callback_query(call.id, "❌ الفيديو غير متاح للتحميل", show_alert=True)
                return
            
            try:
                # إرسال الفيديو
                title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
                caption = f"🎬 **{title}**\n\n"
                caption += f"📥 **من أرشيف الفيديوهات المجاني**\n"
                caption += f"🤖 **البوت يعمل 24/7 مع Keep Alive System**\n"
                caption += f"⚡ **تحميل فوري بدون انتظار**"
                
                bot.send_document(
                    chat_id=call.message.chat.id,
                    document=video[5],  # file_id
                    caption=caption,
                    parse_mode="Markdown"
                )
                
                # تحديث عداد التحميل (إذا كان موجود)
                try:
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE video_archive SET download_count = download_count + 1 WHERE id = %s", (video_id,))
                        conn.commit()
                        cursor.close()
                        conn.close()
                except:
                    pass
                
                bot.answer_callback_query(call.id, "✅ تم إرسال الفيديو بنجاح!", show_alert=True)
                
            except Exception as e:
                logger.error(f"❌ خطأ في إرسال الفيديو: {e}")
                bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء التحميل، جرب مرة أخرى", show_alert=True)
                
        elif data.startswith("favorite_"):
            # إضافة/إزالة من المفضلة
            video_id = int(data.replace("favorite_", ""))
            
            # تغيير حالة المفضلة
            is_added = toggle_favorite(user_id, video_id)
            
            if is_added:
                bot.answer_callback_query(call.id, "✅ تم إضافة الفيديو للمفضلة بنجاح!", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "❌ تم إزالة الفيديو من المفضلة", show_alert=True)
            
            # تحديث أزرار الفيديو
            video = get_video_by_id(video_id)
            if video:
                # إعادة إنشاء الرسالة مع الأزرار المحدثة
                title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
                text = f"🎬 **{title}**\n\n"
                
                if video[2]:
                    desc = video[2][:300] + "..." if len(video[2]) > 300 else video[2]
                    text += f"📝 **الوصف:**\n{desc}\n\n"
                
                if video[12]:
                    text += f"📚 **التصنيف:** {video[12]}\n"
                
                if video[4]:
                    file_name = video[4][:60] + "..." if len(video[4]) > 60 else video[4]
                    text += f"📄 **اسم الملف:** {file_name}\n"
                    
                if video[13] and video[13] > 0:
                    size_mb = video[13] / (1024 * 1024)
                    text += f"💾 **الحجم:** {size_mb:.1f} MB\n"
                    
                text += f"\n📊 **الإحصائيات:**\n"
                text += f"👁️ **المشاهدات:** {video[8]:,}\n"
                
                if video[11]:
                    upload_date = video[11].strftime('%Y-%m-%d')
                    text += f"📅 **تاريخ الرفع:** {upload_date}\n"
                
                # إعادة إنشاء الأزرار
                is_fav = is_favorite(user_id, video_id)
                fav_text = "❤️ إزالة من المفضلة" if is_fav else "💖 إضافة للمفضلة"
                
                markup = types.InlineKeyboardMarkup()
                
                buttons_row1 = []
                buttons_row2 = []
                
                if video[5]:
                    btn_download = types.InlineKeyboardButton("📥 تحميل", callback_data=f"download_{video_id}")
                    buttons_row1.append(btn_download)
                
                btn_favorite = types.InlineKeyboardButton(fav_text, callback_data=f"favorite_{video_id}")
                buttons_row1.append(btn_favorite)
                
                if len(buttons_row1) > 0:
                    markup.add(*buttons_row1)
                
                if video[6]:
                    btn_more_cat = types.InlineKeyboardButton("📚 المزيد من التصنيف", callback_data=f"category_{video[6]}")
                    buttons_row2.append(btn_more_cat)
                
                btn_share = types.InlineKeyboardButton("📤 مشاركة", callback_data=f"share_{video_id}")
                buttons_row2.append(btn_share)
                
                if len(buttons_row2) > 0:
                    markup.add(*buttons_row2)
                
                btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
                markup.add(btn_back)
                
                try:
                    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                        reply_markup=markup, parse_mode='Markdown')
                except:
                    # في حالة فشل التحديث، لا مشكلة
                    pass
                    
        elif data.startswith("share_"):
            # مشاركة الفيديو
            video_id = int(data.replace("share_", ""))
            video = get_video_by_id(video_id)
            
            if not video:
                bot.answer_callback_query(call.id, "❌ الفيديو غير موجود")
                return
            
            title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
            share_text = f"🎬 **شاهد هذا الفيديو:**\n\n"
            share_text += f"📺 {title}\n\n"
            
            if video[12]:  # category
                share_text += f"📚 التصنيف: {video[12]}\n"
            
            share_text += f"👁️ المشاهدات: {video[8]:,}\n\n"
            share_text += f"🤖 **أرشيف الفيديوهات المجاني**\n"
            share_text += f"📱 البوت: @{bot.get_me().username}\n"
            share_text += f"🔍 ابحث عن: `{title[:50]}`"
            
            try:
                # إرسال رسالة المشاركة
                bot.send_message(
                    chat_id=call.message.chat.id,
                    text=share_text,
                    parse_mode="Markdown"
                )
                
                bot.answer_callback_query(call.id, "✅ تم إنشاء رسالة المشاركة!")
                
            except Exception as e:
                logger.error(f"❌ خطأ في المشاركة: {e}")
                bot.answer_callback_query(call.id, "❌ حدث خطأ في المشاركة")
                
        else:
            # معالج افتراضي للأزرار غير المعروفة
            bot.answer_callback_query(call.id, "🔄 جاري العمل على هذه الميزة...")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالج الأزرار: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ، جرب مرة أخرى")

# === تنظيف السجل التلقائي ===
def cleanup_old_history():
    """حذف سجل المشاهدة القديم (15 يوم كما طلبت)"""
    try:
        conn = get_db_connection()
        if not conn:
            return
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=15)
        cursor.execute("DELETE FROM user_history WHERE last_watched < %s", (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"🧹 تم حذف {deleted_count} سجل قديم من قاعدة البيانات")
        else:
            logger.info("🧹 لا توجد سجلات قديمة للحذف")
            
    except Exception as e:
        logger.error(f"❌ خطأ في تنظيف السجل: {e}")

# جدولة تنظيف السجل يومياً في 3 صباحاً
schedule.every().day.at("03:00").do(cleanup_old_history)

def run_scheduler():
    """تشغيل المجدول في خيط منفصل"""
    while True:
        schedule.run_pending()
        time.sleep(3600)  # فحص كل ساعة

# === بدء التشغيل ===
def main():
    """الدالة الرئيسية"""
    logger.info("🚀 بدء تشغيل بوت أرشيف الفيديوهات المجاني - الإصدار الكامل...")
    
    # بدء خادم Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask Keep Alive server started")
    
    # بدء نظام Self-Ping
    ping_thread = threading.Thread(target=self_ping, daemon=True)
    ping_thread.start()
    logger.info("✅ Self-ping anti-sleep system started")
    
    # بدء المجدول
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("✅ Auto-cleanup scheduler started (15 days)")
    
    # تهيئة قاعدة البيانات
    if init_database():
        logger.info("✅ Database connection successful")
    else:
        logger.error("❌ Database connection failed")
        return
    
    logger.info("🎬 Starting Telegram bot with Keep Alive...")
    logger.info("🎉 البوت يعمل بنجاح 24/7 مجاناً مع جميع الوظائف!")
    logger.info("🔄 Keep Alive prevents sleeping every 14 minutes")
    logger.info("🧹 Auto cleanup history every 15 days at 03:00")
    logger.info(f"📊 إحصائيات: {get_videos_count()} فيديو | {get_users_count()} مستخدم | {get_categories_count()} تصنيف")
    
    # بدء البوت
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == "__main__":
    main()
