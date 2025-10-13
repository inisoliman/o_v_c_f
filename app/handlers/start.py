"""
معالجات البداية والقوائم الرئيسية
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from sqlalchemy import text
from datetime import datetime

from app.core.database import get_session
from app.core.config import settings

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج أمر /start"""
    user = update.effective_user
    if not user:
        return
    
    welcome_text = f"""🎬 **مرحباً بك في أرشيف الفيديوهات المتقدم!**

👋 أهلاً {user.first_name}!

🔍 **يمكنك البحث** عن أي فيديو بكتابة اسمه
📚 **تصفح التصنيفات** المختلفة  
⭐ **إضافة الفيديوهات** للمفضلة
🎯 **تقييم الفيديوهات** ومراجعتها

📝 **للبحث:** اكتب اسم الفيديو مباشرة
🎛️ **أو استخدم الأزرار أدناه:**"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 البحث المتقدم", callback_data="search_videos"),
            InlineKeyboardButton("📚 التصنيفات", callback_data="browse_categories")
        ],
        [
            InlineKeyboardButton("⭐ مفضلاتي", callback_data="my_favorites"),
            InlineKeyboardButton("📊 سجل المشاهدة", callback_data="my_history")
        ],
        [
            InlineKeyboardButton("❓ مساعدة", callback_data="help"),
            InlineKeyboardButton("📈 إحصائيات", callback_data="stats")
        ]
    ])
    
    # حفظ/تحديث المستخدم في قاعدة البيانات
    try:
        async for session in get_session():
            await session.execute(text("""
                INSERT INTO bot_users (user_id, username, first_name, last_name, language_code, last_activity)
                VALUES (:user_id, :username, :first_name, :last_name, :language_code, :last_activity)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    last_activity = EXCLUDED.last_activity
            """), {
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name, 
                "last_name": user.last_name,
                "language_code": user.language_code,
                "last_activity": datetime.utcnow()
            })
            await session.commit()
            logger.info(f"✅ تم حفظ/تحديث المستخدم: {user.first_name} ({user.id})")
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ المستخدم: {e}")
    
    await update.message.reply_text(welcome_text, reply_markup=keyboard, parse_mode="Markdown")


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج المساعدة"""
    query = update.callback_query
    await query.answer()
    
    help_text = """🎬 **مساعدة أرشيف الفيديوهات**

**🔍 البحث:**
• اكتب اسم الفيديو مباشرة
• استخدم الفلاتر المتقدمة
• ابحث بالجودة أو النوع

**📚 التصنيفات:**
• تصفح حسب النوع
• تصنيفات فرعية متعددة المستويات

**⭐ المفضلة:**
• احفظ الفيديوهات المفضلة
• إنشاء قوائم مخصصة
• وصول سريع لمحتواك

**🎯 التقييم:**
• قيم الفيديوهات من 1-5 نجوم
• اكتب مراجعات
• ساعد المجتمع في الاختيار

**📊 السجل:**
• متابعة تاريخ المشاهدة
• استكمال المشاهدة من النقطة المحفوظة
• إحصائيات شخصية

**🎬 البوت يعمل 24/7 مع Keep Alive System**

للمساعدة أو الاستفسار تواصل مع المشرف"""
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
    ]])
    
    await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=keyboard)


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض إحصائيات البوت"""
    query = update.callback_query
    await query.answer()
    
    try:
        async for session in get_session():
            # إحصائيات عامة
            stats_query = await session.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM video_archive WHERE is_active = true) as total_videos,
                    (SELECT COUNT(*) FROM bot_users WHERE is_active = true) as total_users,
                    (SELECT COUNT(*) FROM categories WHERE is_active = true) as total_categories,
                    (SELECT SUM(view_count) FROM video_archive WHERE is_active = true) as total_views,
                    (SELECT SUM(download_count) FROM video_archive WHERE is_active = true) as total_downloads
            """))
            
            stats = stats_query.fetchone()
            
            stats_text = f"""📊 **إحصائيات أرشيف الفيديوهات**

🎬 **الفيديوهات:** {stats[0]:,}
👥 **المستخدمون:** {stats[1]:,}  
📚 **التصنيفات:** {stats[2]:,}
👁️ **المشاهدات:** {stats[3]:,}
📥 **التحميلات:** {stats[4]:,}

🤖 **البوت يعمل 24/7 مع نظام Keep Alive**
🔄 **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

🚀 **استمتع بتصفح الأرشيف!**"""
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
            ]])
            
            await query.edit_message_text(stats_text, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"❌ خطأ في الإحصائيات: {e}")
        await query.edit_message_text("❌ حدث خطأ في تحميل الإحصائيات")


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """العودة للقائمة الرئيسية"""
    query = update.callback_query
    await query.answer()
    
    # إعادة إرسال رسالة الترحيب
    await start_command(update, context)


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الرسائل النصية العامة"""
    text = update.message.text.strip()
    
    if len(text) > 2:
        # بحث تلقائي
        from app.handlers.search import handle_search_query
        await handle_search_query(update, context, text)
    else:
        await update.message.reply_text(
            "🔍 **للبحث:** اكتب اسم الفيديو (أكثر من حرفين)\n"
            "🎛️ **أو استخدم الأزرار:**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
            ]]),
            parse_mode="Markdown"
        )


def register_start_handlers(app) -> None:
    """تسجيل معالجات البداية"""
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(help_callback, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(stats_callback, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    
    print("✅ تم تسجيل معالجات البداية")
