"""
معالجات البداية والقوائم الرئيسية
"""
import logging
from telebot import types

logger = logging.getLogger(__name__)


def start_command(bot, message):
    """معالج أمر البداية"""
    try:
        from app.services.user_service import UserService
        from app.services.stats_service import StatsService
        
        user = message.from_user
        UserService.add_user(user.id, user.username, user.first_name, user.last_name)
        
        stats = StatsService.get_general_stats()
        
        welcome_text = f"""🎬 **مرحباً بك في أرشيف الفيديوهات المتقدم!**

👋 أهلاً {user.first_name}!

🔍 **للبحث السريع:** اكتب اسم الفيديو مباشرة
📚 **التصنيفات:** تصفح المحتوى حسب النوع
⭐ **المفضلة:** احفظ الفيديوهات المفضلة لديك
📊 **السجل:** راجع تاريخ مشاهدتك

📈 **إحصائيات الأرشيف:**
🎬 الفيديوهات: {stats.get('videos', 0):,}
👥 المستخدمون: {stats.get('users', 0):,}
📚 التصنيفات: {stats.get('categories', 0):,}
⭐ المفضلات: {stats.get('favorites', 0):,}

🤖 **البوت يعمل 24/7 مجاناً مع Webhooks!**

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
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالج البداية: {e}")
        bot.reply_to(message, "❌ حدث خطأ في بدء البوت")


def register_start_handlers(bot):
    """تسجيل معالجات البداية"""
    bot.message_handler(commands=['start'])(lambda message: start_command(bot, message))
    logger.info("✅ تم تسجيل معالجات البداية")
