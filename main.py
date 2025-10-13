"""
🎬 Telegram Video Archive Bot - مع Keep Alive مدمج
بوت أرشيف الفيديوهات المتقدم مع نظام منع السكون
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

# === نظام Keep Alive ===
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return jsonify({
        "status": "alive",
        "service": "Telegram Video Archive Bot",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running 24/7 - مجاني مدى الحياة",
        "users": get_users_count(),
        "videos": get_videos_count()
    })

@app_flask.route('/health')
def health_check():
    db_status = "connected" if check_database() else "disconnected"
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "bot": "active",
        "timestamp": datetime.now().isoformat()
    })

@app_flask.route('/ping')
def ping():
    return "pong - البوت يعمل بنجاح!"

@app_flask.route('/stats')
def stats():
    return jsonify({
        "users": get_users_count(),
        "videos": get_videos_count(),
        "categories": get_categories_count(),
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

# === قاعدة البيانات - مُصححة لتتناسب مع قاعدة بياناتك ===
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
        
        # التحقق من وجود الجداول (أسماء جداولك الحقيقية)
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('video_archive', 'categories', 'bot_users')
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
        # استخدام أسماء الأعمدة الحقيقية
        cursor.execute("SELECT COUNT(*) FROM bot_users")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        logger.error(f"❌ خطأ في عدد المستخدمين: {e}")
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
    except Exception as e:
        logger.error(f"❌ خطأ في عدد الفيديوهات: {e}")
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
    except Exception as e:
        logger.error(f"❌ خطأ في عدد التصنيفات: {e}")
        return 0

def add_user(user_id, username, first_name, last_name=None):
    """إضافة/تحديث مستخدم - مُصحح للأعمدة الحقيقية"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        
        # استخدام الأعمدة الموجودة فعلياً: user_id, username, first_name, join_date
        cursor.execute("""
            INSERT INTO bot_users (user_id, username, first_name, join_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                join_date = CURRENT_TIMESTAMP
        """, (user_id, username, first_name, datetime.now()))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في إضافة المستخدم: {e}")
        return False

def search_videos(query, limit=10):
    """البحث في الفيديوهات - مُصحح للأعمدة الحقيقية"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor()
        
        # استخدام الأعمدة الموجودة: id, title, caption, view_count, file_name, file_size
        cursor.execute("""
            SELECT id, title, caption, view_count, file_name, file_size, category_id
            FROM video_archive 
            WHERE (title ILIKE %s OR caption ILIKE %s OR file_name ILIKE %s)
            ORDER BY view_count DESC
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
    """الحصول على فيديو بالمعرف - مُصحح للأعمدة الحقيقية"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        
        # استخدام أسماء الأعمدة الصحيحة من قاعدة بياناتك
        cursor.execute("""
            SELECT v.id, v.message_id, v.caption, v.chat_id, v.file_name, v.file_id, 
                   v.category_id, v.metadata, v.view_count, v.title, v.grouping_key, 
                   v.upload_date, c.name as category_name
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
        
        # استخدام أسماء الأعمدة الحقيقية
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

# === معالجات البوت ===

@bot.message_handler(commands=['start'])
def start_command(message):
    """معالج أمر البداية"""
    user = message.from_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = f"""🎬 **مرحباً بك في أرشيف الفيديوهات المتقدم!**

👋 أهلاً {user.first_name}!

🔍 **للبحث:** اكتب اسم الفيديو مباشرة
📚 **التصنيفات:** تصفح حسب النوع
⭐ **المفضلة:** احفظ الفيديوهات المفضلة
🎯 **التقييم:** قيم الفيديوهات من 1-5 نجوم

📊 **إحصائيات الأرشيف:**
🎬 الفيديوهات: {get_videos_count():,}
👥 المستخدمون: {get_users_count():,}
📚 التصنيفات: {get_categories_count():,}

🤖 **البوت يعمل 24/7 مجاناً مع Keep Alive System!**

📝 اكتب اسم الفيديو للبحث أو استخدم الأزرار:"""
    
    # إنشاء لوحة المفاتيح
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_search = types.InlineKeyboardButton("🔍 البحث", callback_data="search")
    btn_categories = types.InlineKeyboardButton("📚 التصنيفات", callback_data="categories")
    btn_favorites = types.InlineKeyboardButton("⭐ المفضلة", callback_data="favorites")
    btn_stats = types.InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")
    btn_help = types.InlineKeyboardButton("❓ المساعدة", callback_data="help")
    
    markup.add(btn_search, btn_categories)
    markup.add(btn_favorites, btn_stats)
    markup.add(btn_help)
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['admin'])
def admin_command(message):
    """لوحة تحكم الإدارة"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ غير مصرح لك بالوصول")
        return
    
    stats_text = f"""🛠️ **لوحة التحكم الإدارية**

📊 **إحصائيات سريعة:**
├ 🎬 الفيديوهات: {get_videos_count():,}
├ 👥 المستخدمون: {get_users_count():,}
└ 📚 التصنيفات: {get_categories_count():,}

🤖 **حالة النظام:**
├ قاعدة البيانات: {'✅ متصلة' if check_database() else '❌ منقطعة'}
├ Keep Alive: ✅ يعمل
└ آخر تحديث: {datetime.now().strftime('%H:%M')}

🌐 **رابط المراقبة:**
[https://o-v-c-f.onrender.com](https://o-v-c-f.onrender.com)"""
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_back)
    
    bot.send_message(message.chat.id, stats_text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(content_types=['text'])
def text_handler(message):
    """معالج النصوص للبحث"""
    query = message.text.strip()
    
    if len(query) < 3:
        bot.reply_to(message, "🔍 يرجى كتابة كلمة بحث أكثر من حرفين")
        return
    
    # إرسال رسالة انتظار
    wait_msg = bot.reply_to(message, "🔍 جاري البحث في الأرشيف...")
    
    # البحث في الفيديوهات
    results = search_videos(query)
    
    if not results:
        bot.edit_message_text(
            f"❌ لم يتم العثور على نتائج للبحث: **{query}**\n\n💡 جرب:\n• استخدام كلمات أخرى\n• البحث بالإنجليزية\n• البحث في التصنيفات",
            wait_msg.chat.id, wait_msg.message_id, parse_mode='Markdown'
        )
        return
    
    # تنسيق النتائج
    text = f"🔍 **نتائج البحث عن:** {query}\n📊 تم العثور على {len(results)} نتيجة\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    for i, video in enumerate(results[:10], 1):
        # video = (id, title, caption, view_count, file_name, file_size, category_id)
        title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
        title = title[:50] + "..." if len(title) > 50 else title
        
        views = video[3] if video[3] else 0
        size = f" | 💾 {video[5]//1024//1024:.0f}MB" if video[5] else ""
        
        text += f"**{i}.** {title}\n   👁️ {views:,}{size}\n\n"
        
        btn = types.InlineKeyboardButton(f"📺 {title[:25]}...", callback_data=f"video_{video[0]}")
        markup.add(btn)
    
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_back)
    
    bot.edit_message_text(text, wait_msg.chat.id, wait_msg.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """معالج الأزرار"""
    try:
        if call.data == "main_menu":
            start_command(call.message)
            
        elif call.data == "stats":
            stats_text = f"""📊 **إحصائيات أرشيف الفيديوهات**

🎬 **الفيديوهات:** {get_videos_count():,}
👥 **المستخدمون:** {get_users_count():,}  
📚 **التصنيفات:** {get_categories_count():,}

🤖 **البوت يعمل 24/7 مع نظام Keep Alive**
🔄 **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

🌐 **رابط المراقبة:**
[https://o-v-c-f.onrender.com/health](https://o-v-c-f.onrender.com/health)

🚀 **استمتع بتصفح الأرشيف المجاني!**"""
            
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            markup.add(btn_back)
            
            bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, 
                                reply_markup=markup, parse_mode='Markdown')
            
        elif call.data == "help":
            help_text = """🎬 **مساعدة أرشيف الفيديوهات**

**🔍 البحث:**
• اكتب اسم الفيديو مباشرة
• البحث يدعم العربية والإنجليزية
• يبحث في العنوان والوصف واسم الملف

**📚 التصنيفات:**
• تصفح حسب النوع
• تصنيفات متعددة المستويات
• مئات الفيديوهات المنظمة

**⭐ المفضلة:**
• احفظ الفيديوهات المفضلة
• وصول سريع لمحتواك

**🤖 البوت يعمل 24/7 مجاناً مع Keep Alive System**
**🔄 نظام تنظيف تلقائي للسجل كل 15 يوم**

للمساعدة تواصل مع المشرف"""
            
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            markup.add(btn_back)
            
            bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id,
                                reply_markup=markup, parse_mode='Markdown')
            
        elif call.data.startswith("video_"):
            video_id = int(call.data.replace("video_", ""))
            video = get_video_by_id(video_id)
            
            if not video:
                bot.answer_callback_query(call.id, "❌ الفيديو غير موجود")
                return
            
            # زيادة عداد المشاهدة وإضافة للسجل
            update_view_count(video_id)
            add_to_history(call.from_user.id, video_id)
            
            # تنسيق معلومات الفيديو
            # video = (id, message_id, caption, chat_id, file_name, file_id, category_id, metadata, view_count, title, grouping_key, upload_date, category_name)
            title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
            text = f"🎬 **{title}**\n\n"
            
            if video[2]:  # caption/description
                desc = video[2][:200] + "..." if len(video[2]) > 200 else video[2]
                text += f"📝 {desc}\n\n"
            
            if video[12]:  # category_name
                text += f"📚 **التصنيف:** {video[12]}\n"
            
            if video[4]:  # file_name
                text += f"📄 **اسم الملف:** {video[4][:50]}\n"
                
            text += f"\n📊 **الإحصائيات:**\n"
            text += f"👁️ المشاهدات: {video[8]:,}\n"  # view_count
            
            if video[11]:  # upload_date
                upload_date = video[11].strftime('%Y-%m-%d')
                text += f"📅 تاريخ الرفع: {upload_date}\n"
            
            markup = types.InlineKeyboardMarkup()
            
            if video[5]:  # file_id exists - يمكن التحميل
                btn_download = types.InlineKeyboardButton("📥 تحميل", callback_data=f"download_{video_id}")
                btn_favorite = types.InlineKeyboardButton("💖 مفضلة", callback_data=f"favorite_{video_id}")
                markup.add(btn_download, btn_favorite)
            else:
                btn_favorite = types.InlineKeyboardButton("💖 مفضلة", callback_data=f"favorite_{video_id}")
                markup.add(btn_favorite)
            
            btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
            markup.add(btn_back)
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                reply_markup=markup, parse_mode='Markdown')
        
        elif call.data.startswith("download_"):
            video_id = int(call.data.replace("download_", ""))
            video = get_video_by_id(video_id)
            
            if not video or not video[5]:  # لا يوجد file_id
                bot.answer_callback_query(call.id, "❌ الفيديو غير متاح للتحميل", show_alert=True)
                return
            
            try:
                # إرسال الفيديو
                title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
                bot.send_document(
                    chat_id=call.message.chat.id,
                    document=video[5],  # file_id
                    caption=f"🎬 **{title}**\n📥 من أرشيف الفيديوهات المجاني\n🤖 البوت يعمل 24/7",
                    parse_mode="Markdown"
                )
                
                bot.answer_callback_query(call.id, "✅ تم إرسال الفيديو", show_alert=True)
                
            except Exception as e:
                logger.error(f"❌ خطأ في إرسال الفيديو: {e}")
                bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء التحميل", show_alert=True)
        
        elif call.data.startswith("favorite_"):
            video_id = int(call.data.replace("favorite_", ""))
            
            # تغيير حالة المفضلة
            is_added = toggle_favorite(call.from_user.id, video_id)
            
            if is_added:
                bot.answer_callback_query(call.id, "✅ تم إضافة الفيديو للمفضلة", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "❌ تم إزالة الفيديو من المفضلة", show_alert=True)
        
        else:
            bot.answer_callback_query(call.id, "🔄 هذه الميزة قيد التطوير")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالج الأزرار: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")

# === تنظيف السجل التلقائي (كما طلبت 15 يوم) ===
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
            logger.info(f"🧹 تم حذف {deleted_count} سجل قديم")
            
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
    logger.info("🚀 بدء تشغيل بوت أرشيف الفيديوهات المجاني...")
    
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
    logger.info("🎉 البوت يعمل بنجاح 24/7 مجاناً!")
    logger.info("🔄 Keep Alive prevents sleeping every 14 minutes")
    logger.info(f"📊 إحصائيات: {get_videos_count()} فيديو | {get_users_count()} مستخدم")
    
    # بدء البوت
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == "__main__":
    main()
