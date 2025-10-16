"""معالج شامل لجميع أزرار البوت مع دعم التصفح وأزرار الإدارة"""
import logging
import math
from datetime import datetime
from telebot import types

logger = logging.getLogger(__name__)

# حالة المستخدمين للعمليات التفاعلية
user_states = {}


def safe_edit(bot, chat_id, message_id, text, markup=None, allow_html=False):
    """تحرير رسالة بأمان بدون تعقيد Markdown. استخدم HTML فقط عند ضمان سلامة النص."""
    try:
        if allow_html:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
        else:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"❌ edit_message_text failed: {e}")
        # كحل بديل: أرسل رسالة جديدة بدل التعديل
        try:
            if allow_html:
                bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
            else:
                bot.send_message(chat_id, text, reply_markup=markup)
        except Exception as e2:
            logger.error(f"❌ send_message fallback failed: {e2}")


def safe_send(bot, chat_id, text, markup=None, allow_html=False):
    try:
        if allow_html:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(chat_id, text, reply_markup=markup)
    except Exception as e:
        logger.error(f"❌ send_message failed: {e}")


def handle_callback_query(bot, call):
    """معالج شامل للأزرار مع دعم التصفح وأزرار الإدارة"""
    try:
        user_id = call.from_user.id
        data = call.data
        
        # استيراد قائمة المشرفين
        from main import ADMIN_IDS
        
        if data == "main_menu":
            from app.handlers.start import start_command
            # لا تستخدم delete ثم reply_to. احذف الرسالة ثم أعد إرسال رسالة جديدة.
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            start_command(bot, call.message)
            
        elif data == "search":
            handle_search_menu(bot, call)
            
        elif data == "categories":
            handle_categories_menu(bot, call)
            
        elif data.startswith("categories_page_"):
            page = int(data.replace("categories_page_", ""))
            handle_categories_menu(bot, call, page)
            
        elif data == "favorites":
            handle_favorites_menu(bot, call, user_id)
            
        elif data == "history":
            handle_history_menu(bot, call, user_id)
            
        elif data == "popular":
            handle_popular_videos(bot, call)
            
        elif data == "recent":
            handle_recent_videos(bot, call)
            
        elif data == "stats":
            handle_stats_menu(bot, call)
            
        elif data == "help":
            handle_help_menu(bot, call)
            
        elif data.startswith("video_"):
            from app.handlers.video_handler import handle_video_details
            video_id = int(data.replace("video_", ""))
            handle_video_details(bot, call, user_id, video_id)
            
        elif data.startswith("category_"):
            if "_page_" in data:
                parts = data.replace("category_", "").split("_page_")
                category_id = int(parts[0])
                page = int(parts[1])
                handle_category_videos(bot, call, category_id, page)
            else:
                category_id = int(data.replace("category_", ""))
                handle_category_videos(bot, call, category_id)
            
        elif data.startswith("download_"):
            from app.handlers.video_handler import handle_video_download
            video_id = int(data.replace("download_", ""))
            handle_video_download(bot, call, video_id)
            
        elif data.startswith("favorite_"):
            from app.handlers.video_handler import handle_toggle_favorite
            video_id = int(data.replace("favorite_", ""))
            handle_toggle_favorite(bot, call, user_id, video_id)
            
        # معالجة أزرار الإدارة
        elif data.startswith("admin_"):
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "❌ غير مصرح لك بهذه العملية")
                return
            
            # استدعاء معالج أزرار الإدارة
            from app.handlers.admin import handle_admin_callback
            handle_admin_callback(bot, call)
            return  # عدم استدعاء answer_callback_query مرة أخرى
            
        else:
            bot.answer_callback_query(call.id, "🔄 هذه الميزة قيد التطوير")
        
        # تأكيد الضغط (بدون رسالة في حال تم التعامل داخل دوال الفيديو)
        if not data.startswith(("video_", "download_", "favorite_", "admin_")):
            bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالج الأزرار: {e}")
        try:
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
        except:
            pass


def handle_search_menu(bot, call):
    """معالج قائمة البحث"""
    search_text = (
        "🔍 البحث المتقدم\n\n"
        "📝 يتم البحث في:\n"
        "• عنوان الفيديو\n"
        "• وصف الفيديو\n"
        "• اسم الملف\n"
        "• البيانات الوصفية\n\n"
        "📝 اكتب كلمة البحث الآن:"
    )
    user_states[call.from_user.id] = {'action': 'searching'}
    
    markup = types.InlineKeyboardMarkup()
    btn_cancel = types.InlineKeyboardButton("❌ إلغاء", callback_data="main_menu")
    markup.add(btn_cancel)
    
    safe_edit(bot, call.message.chat.id, call.message.message_id, search_text, markup)


def handle_categories_menu(bot, call, page: int = 1):
    """معالج قائمة التصنيفات مع التصفح"""
    try:
        from app.services.category_service import CategoryService
        
        per_page = 10
        categories = CategoryService.get_categories(include_counts=True, page=page, per_page=per_page)
        total_categories = CategoryService.get_total_categories_count()
        
        if not categories:
            safe_edit(bot, call.message.chat.id, call.message.message_id, "❌ لا توجد تصنيفات متاحة")
            return
        
        total_pages = max(1, math.ceil(total_categories / per_page))
        
        text = f"📚 التصنيفات المتاحة (صفحة {page}/{total_pages})\n\n"
        text += "اختر التصنيف لتصفح محتواه:\n\n"
        
        markup = types.InlineKeyboardMarkup()
        
        for category in categories:
            cat_name = category[1][:25] + "..." if len(category[1]) > 25 else category[1]
            video_count = category[4] if len(category) > 4 else 0
            
            display_text = f"📁 {cat_name}"
            if video_count > 0:
                display_text += f" ({video_count})"
            
            text += f"{display_text}\n"
            btn = types.InlineKeyboardButton(display_text, callback_data=f"category_{category[0]}")
            markup.add(btn)
        
        nav_buttons = []
        if page > 1:
            nav_buttons.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"categories_page_{page-1}"))
        if page < total_pages:
            nav_buttons.append(types.InlineKeyboardButton("➡️ التالي", callback_data=f"categories_page_{page+1}"))
        if nav_buttons:
            markup.add(*nav_buttons)
        
        btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        markup.add(btn_back)
        
        safe_edit(bot, call.message.chat.id, call.message.message_id, text, markup)
    except Exception as e:
        logger.error(f"❌ خطأ في التصنيفات: {e}")
        safe_edit(bot, call.message.chat.id, call.message.message_id, "❌ حدث خطأ في عرض التصنيفات")


def handle_category_videos(bot, call, category_id: int, page: int = 1):
    """معالج فيديوهات التصنيف مع دعم التصنيفات الفرعية والتصفح"""
    try:
        from app.services.video_service import VideoService
        from app.services.category_service import CategoryService
        
        per_page = 8
        category = CategoryService.get_category_by_id(category_id)
        if not category:
            bot.answer_callback_query(call.id, "❌ التصنيف غير موجود")
            return
        
        category_name = category[1]
        
        # جلب التصنيفات الفرعية
        subcategories = []
        try:
            if hasattr(CategoryService, 'get_subcategories'):
                subcategories = CategoryService.get_subcategories(category_id)
        except Exception as sc_err:
            logger.error(f"❌ خطأ في جلب التصنيفات الفرعية: {sc_err}")
        
        # جلب الفيديوهات
        videos = VideoService.get_videos_by_category(category_id, per_page, page)
        total_videos = VideoService.get_category_videos_count(category_id)
        
        # التحقق من وجود محتوى
        if not subcategories and not videos:
            bot.answer_callback_query(call.id, "❌ لا توجد عناصر في هذا التصنيف")
            return
        
        text = f"📁 {category_name}\n\n"
        markup = types.InlineKeyboardMarkup()
        
        # عرض التصنيفات الفرعية إن وجدت
        if subcategories:
            text += "📂 التصنيفات الفرعية:\n"
            for sub in subcategories:
                sub_name = sub[1][:30] + "..." if len(sub[1]) > 30 else sub[1]
                video_count = sub[4] if len(sub) > 4 else 0
                display_text = f"📂 {sub_name}"
                if video_count > 0:
                    display_text += f" ({video_count})"
                
                text += f"• {sub_name}\n"
                markup.add(types.InlineKeyboardButton(display_text, callback_data=f"category_{sub[0]}"))
            text += "\n"
        
        # عرض الفيديوهات إن وجدت
        if videos:
            if subcategories:
                text += "🎬 الفيديوهات:\n"
            
            total_pages = max(1, math.ceil(total_videos / per_page))
            text += f"📊 {total_videos} فيديو"
            if total_pages > 1:
                text += f" | صفحة {page}/{total_pages}"
            text += "\n\n"
            
            for i, video in enumerate(videos, 1):
                title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
                title_short = title[:30] + "..." if len(title) > 30 else title
                views = video[3] if video[3] else 0
                
                video_number = (page - 1) * per_page + i
                text += f"{video_number}. {title_short}\n   👁️ {views:,}\n\n"
                
                # أضف زرين لكل فيديو: تفاصيل وجلب
                btn_details = types.InlineKeyboardButton(f"📺 {video_number}. {title[:15]}...", callback_data=f"video_{video[0]}")
                btn_download = types.InlineKeyboardButton("📥 جلب", callback_data=f"download_{video[0]}")
                markup.add(btn_details, btn_download)
            
            # أزرار التصفح للفيديوهات
            if total_pages > 1:
                nav_buttons = []
                if page > 1:
                    nav_buttons.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"category_{category_id}_page_{page-1}"))
                if page < total_pages:
                    nav_buttons.append(types.InlineKeyboardButton("➡️ التالي", callback_data=f"category_{category_id}_page_{page+1}"))
                if nav_buttons:
                    markup.add(*nav_buttons)
        
        # أزرار التنقل
        btn_categories = types.InlineKeyboardButton("📚 كل التصنيفات", callback_data="categories")
        btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        markup.add(btn_categories, btn_back)
        
        safe_edit(bot, call.message.chat.id, call.message.message_id, text, markup)
    except Exception as e:
        logger.error(f"❌ خطأ في فيديوهات التصنيف: {e}")
        safe_edit(bot, call.message.chat.id, call.message.message_id, "❌ حدث خطأ في عرض التصنيف")


def handle_favorites_menu(bot, call, user_id):
    """معالج قائمة المفضلات"""
    try:
        from app.services.user_service import UserService
        favorites = UserService.get_user_favorites(user_id, 10)
        
        if not favorites:
            empty_text = (
                "⭐ مفضلاتي\n\n"
                "❌ لا توجد فيديوهات في المفضلة\n\n"
                "💡 للإضافة: اختر أي فيديو واضغط 💖"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔍 البحث", callback_data="search"),
                       types.InlineKeyboardButton("🔥 الأشهر", callback_data="popular"))
            markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
            safe_edit(bot, call.message.chat.id, call.message.message_id, empty_text, markup)
            return
            
        text = f"⭐ مفضلاتي ({len(favorites)})\n\n"
        markup = types.InlineKeyboardMarkup()
        
        for i, video in enumerate(favorites, 1):
            title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
            title_short = title[:30] + "..." if len(title) > 30 else title
            text += f"{i}. {title_short}\n\n"
            
            # أضف زرين لكل فيديو: تفاصيل وجلب
            btn_details = types.InlineKeyboardButton(f"📺 {i}. {title[:15]}...", callback_data=f"video_{video[0]}")
            btn_download = types.InlineKeyboardButton("📥 جلب", callback_data=f"download_{video[0]}")
            markup.add(btn_details, btn_download)
            
        markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
        safe_edit(bot, call.message.chat.id, call.message.message_id, text, markup)
    except Exception as e:
        logger.error(f"❌ خطأ في المفضلات: {e}")


def handle_history_menu(bot, call, user_id):
    """معالج سجل المشاهدة"""
    try:
        from app.services.user_service import UserService
        history = UserService.get_user_history(user_id, 10)
        
        if not history:
            empty_text = (
                "📊 سجل المشاهدة\n\n"
                "❌ لا يوجد سجل مشاهدة\n\n"
                "💡 للبدء: اختر أي فيديو لمشاهدة تفاصيله"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔍 البحث", callback_data="search"),
                       types.InlineKeyboardButton("📚 التصنيفات", callback_data="categories"))
            markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
            safe_edit(bot, call.message.chat.id, call.message.message_id, empty_text, markup)
            return
            
        text = f"📊 سجل المشاهدة ({len(history)})\n\n"
        markup = types.InlineKeyboardMarkup()
        
        for i, video in enumerate(history, 1):
            title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
            title_short = title[:30] + "..." if len(title) > 30 else title
            text += f"{i}. {title_short}\n\n"
            
            # أضف زرين لكل فيديو: تفاصيل وجلب
            btn_details = types.InlineKeyboardButton(f"📺 {i}. {title[:15]}...", callback_data=f"video_{video[0]}")
            btn_download = types.InlineKeyboardButton("📥 جلب", callback_data=f"download_{video[0]}")
            markup.add(btn_details, btn_download)
            
        markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
        safe_edit(bot, call.message.chat.id, call.message.message_id, text, markup)
    except Exception as e:
        logger.error(f"❌ خطأ في السجل: {e}")


def handle_popular_videos(bot, call):
    """معالج الفيديوهات الشائعة"""
    try:
        from app.services.video_service import VideoService
        popular = VideoService.get_popular_videos(10)
        
        if not popular:
            safe_edit(bot, call.message.chat.id, call.message.message_id, "❌ لا توجد فيديوهات شائعة")
            return
            
        text = "🔥 الفيديوهات الأشهر\n\n"
        markup = types.InlineKeyboardMarkup()
        
        for i, video in enumerate(popular, 1):
            title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
            title_short = title[:30] + "..." if len(title) > 30 else title
            views = video[3] if video[3] else 0
            
            text += f"{i}. {title_short}\n   👁️ {views:,}\n\n"
            
            # أضف زرين لكل فيديو: تفاصيل وجلب
            btn_details = types.InlineKeyboardButton(f"📺 {i}. {title[:15]}...", callback_data=f"video_{video[0]}")
            btn_download = types.InlineKeyboardButton("📥 جلب", callback_data=f"download_{video[0]}")
            markup.add(btn_details, btn_download)
            
        markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
        safe_edit(bot, call.message.chat.id, call.message.message_id, text, markup)
    except Exception as e:
        logger.error(f"❌ خطأ في الفيديوهات الشائعة: {e}")


def handle_recent_videos(bot, call):
    """معالج أحدث الفيديوهات"""
    try:
        from app.services.video_service import VideoService
        recent = VideoService.get_recent_videos(10)
        
        if not recent:
            safe_edit(bot, call.message.chat.id, call.message.message_id, "❌ لا توجد فيديوهات حديثة")
            return
            
        text = "🆕 أحدث الفيديوهات\n\n"
        markup = types.InlineKeyboardMarkup()
        
        for i, video in enumerate(recent, 1):
            title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
            title_short = title[:30] + "..." if len(title) > 30 else title
            text += f"{i}. {title_short}\n\n"
            
            # أضف زرين لكل فيديو: تفاصيل وجلب
            btn_details = types.InlineKeyboardButton(f"📺 {i}. {title[:15]}...", callback_data=f"video_{video[0]}")
            btn_download = types.InlineKeyboardButton("📥 جلب", callback_data=f"download_{video[0]}")
            markup.add(btn_details, btn_download)
            
        markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
        safe_edit(bot, call.message.chat.id, call.message.message_id, text, markup)
    except Exception as e:
        logger.error(f"❌ خطأ في الفيديوهات الحديثة: {e}")


def handle_stats_menu(bot, call):
    """معالج الإحصائيات"""
    try:
        from app.services.stats_service import StatsService
        stats = StatsService.get_general_stats()
        
        stats_text = (
            "📊 إحصائيات أرشيف الفيديوهات\n\n"
            f"🎬 الفيديوهات: {stats.get('videos', 0):,}\n"
            f"👥 المستخدمون: {stats.get('users', 0):,}\n"
            f"📚 التصنيفات: {stats.get('categories', 0):,}\n"
            f"⭐ المفضلات: {stats.get('favorites', 0):,}\n"
            f"👁️ إجمالي المشاهدات: {stats.get('total_views', 0):,}\n\n"
            "🤖 النظام:\n"
            "✅ يعمل 24/7 مع Webhooks\n"
            "🌐 بدون تضارب\n"
            f"🔄 آخر تحديث: {datetime.now().strftime('%H:%M')}\n"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
        safe_edit(bot, call.message.chat.id, call.message.message_id, stats_text, markup)
    except Exception as e:
        logger.error(f"❌ خطأ في الإحصائيات: {e}")


def handle_help_menu(bot, call):
    """معالج المساعدة"""
    help_text = (
        "🎬 مساعدة أرشيف الفيديوهات\n\n"
        "🔍 البحث: اكتب الاسم مباشرة\n"
        "📚 التصنيفات: تصفح المحتوى\n"
        "⭐ المفضلة: احفظ ما تحب\n"
        "📊 السجل: تتبع مشاهداتك\n"
        "📥 الجلب: تحميل الملفات تلقائياً\n"
        "🤖 Webhooks: استجابة فورية"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
    safe_edit(bot, call.message.chat.id, call.message.message_id, help_text, markup)


def register_all_callbacks(bot):
    """تسجيل معالجات الأزرار"""
    bot.callback_query_handler(func=lambda call: True)(lambda call: handle_callback_query(bot, call))
    logger.info("✅ تم تسجيل معالجات الأزرار")
