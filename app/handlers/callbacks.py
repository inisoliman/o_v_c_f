"""
معالج شامل لجميع أزرار البوت مع دعم التصفح - مُحدَث
"""
import logging
import math
from datetime import datetime
from telebot import types

logger = logging.getLogger(__name__)

# حالة المستخدمين للعمليات التفاعلية
user_states = {}


def handle_callback_query(bot, call):
    """معالج شامل للأزرار مع دعم التصفح"""
    try:
        user_id = call.from_user.id
        data = call.data
        
        if data == "main_menu":
            # العودة للقائمة الرئيسية
            from app.handlers.start import start_command
            # إنشاء mock message object
            mock_message = type('MockMessage', (), {
                'from_user': call.from_user,
                'chat': call.message.chat,
                'message_id': call.message.message_id
            })()
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start_command(bot, mock_message)
            
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
            # استخدام الدالة من video_handler
            from app.handlers.video_handler import handle_video_details
            video_id = int(data.replace("video_", ""))
            handle_video_details(bot, call, user_id, video_id)
            
        elif data.startswith("category_"):
            if "_page_" in data:
                # معالجة صفحات التصنيف
                parts = data.replace("category_", "").split("_page_")
                category_id = int(parts[0])
                page = int(parts[1])
                handle_category_videos(bot, call, category_id, page)
            else:
                # معالجة التصنيف العادي
                category_id = int(data.replace("category_", ""))
                handle_category_videos(bot, call, category_id)
            
        elif data.startswith("download_"):
            # استخدام الدالة من video_handler
            from app.handlers.video_handler import handle_video_download
            video_id = int(data.replace("download_", ""))
            handle_video_download(bot, call, video_id)
            
        elif data.startswith("favorite_"):
            # استخدام الدالة من video_handler
            from app.handlers.video_handler import handle_toggle_favorite
            video_id = int(data.replace("favorite_", ""))
            handle_toggle_favorite(bot, call, user_id, video_id)
            
        else:
            bot.answer_callback_query(call.id, "🔄 هذه الميزة قيد التطوير")
        
        # عدم استدعاء answer_callback_query للفيديوهات لأنها تتعامل معه بنفسها
        if not data.startswith(("video_", "download_", "favorite_")):
            bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالج الأزرار: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")


def handle_search_menu(bot, call):
    """معالج قائمة البحث"""
    search_text = """🔍 **البحث المتقدم**

📝 **يتم البحث في:**
• 📺 عنوان الفيديو
• 📝 وصف الفيديو (الكابشن)
• 📄 اسم الملف
• 🏷️ البيانات الوصفية

💡 **أمثلة للبحث:**
• `الاختيار` - للبحث عن مسلسل
• `2023` - للبحث عن فيديوهات سنة معينة
• `HD` - للبحث عن جودة معينة

📝 **اكتب كلمة البحث الآن:**"""
    
    user_states[call.from_user.id] = {'action': 'searching'}
    
    markup = types.InlineKeyboardMarkup()
    btn_cancel = types.InlineKeyboardButton("❌ إلغاء", callback_data="main_menu")
    markup.add(btn_cancel)
    
    bot.edit_message_text(search_text, call.message.chat.id, call.message.message_id,
                        reply_markup=markup, parse_mode='Markdown')


def handle_categories_menu(bot, call, page: int = 1):
    """معالج قائمة التصنيفات مع التصفح"""
    try:
        from app.services.category_service import CategoryService
        
        per_page = 10
        categories = CategoryService.get_categories(include_counts=True, page=page, per_page=per_page)
        total_categories = CategoryService.get_total_categories_count()
        
        if not categories:
            bot.edit_message_text("❌ لا توجد تصنيفات متاحة", 
                                call.message.chat.id, call.message.message_id)
            return
        
        total_pages = math.ceil(total_categories / per_page)
        
        text = f"📚 **التصنيفات المتاحة** (صفحة {page}/{total_pages})\n\n"
        text += f"اختر التصنيف لتصفح محتواه:\n\n"
        
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
        
        # أزرار التنقل
        nav_buttons = []
        if page > 1:
            nav_buttons.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"categories_page_{page-1}"))
        if page < total_pages:
            nav_buttons.append(types.InlineKeyboardButton("➡️ التالي", callback_data=f"categories_page_{page+1}"))
        
        if nav_buttons:
            markup.add(*nav_buttons)
        
        # زر العودة
        btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        markup.add(btn_back)
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ خطأ في التصنيفات: {e}")
        bot.edit_message_text("❌ حدث خطأ في عرض التصنيفات", 
                            call.message.chat.id, call.message.message_id)


def handle_category_videos(bot, call, category_id: int, page: int = 1):
    """معالج فيديوهات التصنيف مع التصفح"""
    try:
        from app.services.video_service import VideoService
        from app.services.category_service import CategoryService
        
        per_page = 8
        
        # الحصول على معلومات التصنيف
        category = CategoryService.get_category_by_id(category_id)
        if not category:
            bot.answer_callback_query(call.id, "❌ التصنيف غير موجود")
            return
        
        # الحصول على الفيديوهات
        videos = VideoService.get_videos_by_category(category_id, per_page, page)
        total_videos = VideoService.get_category_videos_count(category_id)
        
        if not videos:
            bot.answer_callback_query(call.id, "❌ لا توجد فيديوهات في هذا التصنيف")
            return
        
        total_pages = math.ceil(total_videos / per_page)
        category_name = category[1]
        
        text = f"📁 **{category_name}**\n"
        text += f"📊 {total_videos} فيديو | صفحة {page}/{total_pages}\n\n"
        
        markup = types.InlineKeyboardMarkup()
        
        for i, video in enumerate(videos, 1):
            title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
            title_short = title[:30] + "..." if len(title) > 30 else title
            views = video[3] if video[3] else 0
            
            # إضافة الفيديو للنص
            video_number = (page - 1) * per_page + i
            text += f"**{video_number}.** {title_short}\n   👁️ {views:,}\n\n"
            
            # زر الفيديو
            btn = types.InlineKeyboardButton(f"{video_number}. {title[:20]}...", callback_data=f"video_{video[0]}")
            markup.add(btn)
        
        # أزرار التنقل
        nav_buttons = []
        if page > 1:
            nav_buttons.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"category_{category_id}_page_{page-1}"))
        if page < total_pages:
            nav_buttons.append(types.InlineKeyboardButton("➡️ التالي", callback_data=f"category_{category_id}_page_{page+1}"))
        
        if nav_buttons:
            markup.add(*nav_buttons)
        
        # أزرار إضافية
        btn_categories = types.InlineKeyboardButton("📚 كل التصنيفات", callback_data="categories")
        btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        markup.add(btn_categories, btn_back)
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ خطأ في فيديوهات التصنيف: {e}")
        bot.edit_message_text("❌ حدث خطأ في عرض الفيديوهات", 
                            call.message.chat.id, call.message.message_id)


def handle_favorites_menu(bot, call, user_id):
    """معالج قائمة المفضلات"""
    try:
        from app.services.user_service import UserService
        
        favorites = UserService.get_user_favorites(user_id, 10)
        
        if not favorites:
            empty_text = f"⭐ **مفضلاتي**\n\n"
            empty_text += f"❌ لا توجد فيديوهات في المفضلة\n\n"
            empty_text += f"💡 **للإضافة:** اختر أي فيديو واضغط 💖"
            
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
        
        for i, video in enumerate(favorites, 1):
            title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
            title_short = title[:30] + "..." if len(title) > 30 else title
            
            text += f"**{i}.** {title_short}\n\n"
            
            btn = types.InlineKeyboardButton(f"{i}. {title[:20]}...", callback_data=f"video_{video[0]}")
            markup.add(btn)
            
        btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        markup.add(btn_back)
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ خطأ في المفضلات: {e}")


def handle_history_menu(bot, call, user_id):
    """معالج سجل المشاهدة"""
    try:
        from app.services.user_service import UserService
        
        history = UserService.get_user_history(user_id, 10)
        
        if not history:
            empty_text = f"📊 **سجل المشاهدة**\n\n"
            empty_text += f"❌ لا يوجد سجل مشاهدة\n\n"
            empty_text += f"💡 **للبدء:** اختر أي فيديو لمشاهدة تفاصيله"
            
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
        
        for i, video in enumerate(history, 1):
            title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
            title_short = title[:30] + "..." if len(title) > 30 else title
            
            text += f"**{i}.** {title_short}\n\n"
            
            btn = types.InlineKeyboardButton(f"{i}. {title[:20]}...", callback_data=f"video_{video[0]}")
            markup.add(btn)
            
        btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        markup.add(btn_back)
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ خطأ في السجل: {e}")


def handle_popular_videos(bot, call):
    """معالج الفيديوهات الشائعة"""
    try:
        from app.services.video_service import VideoService
        
        popular = VideoService.get_popular_videos(10)
        
        if not popular:
            bot.edit_message_text("❌ لا توجد فيديوهات شائعة", 
                                call.message.chat.id, call.message.message_id)
            return
            
        text = f"🔥 **الفيديوهات الأشهر**\n\n"
        
        markup = types.InlineKeyboardMarkup()
        
        for i, video in enumerate(popular, 1):
            title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
            title_short = title[:30] + "..." if len(title) > 30 else title
            views = video[3] if video[3] else 0
            
            text += f"**{i}.** {title_short}\n   👁️ {views:,}\n\n"
            
            btn = types.InlineKeyboardButton(f"{i}. {title[:20]}...", callback_data=f"video_{video[0]}")
            markup.add(btn)
            
        btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        markup.add(btn_back)
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ خطأ في الفيديوهات الشائعة: {e}")


def handle_recent_videos(bot, call):
    """معالج أحدث الفيديوهات"""
    try:
        from app.services.video_service import VideoService
        
        recent = VideoService.get_recent_videos(10)
        
        if not recent:
            bot.edit_message_text("❌ لا توجد فيديوهات حديثة", 
                                call.message.chat.id, call.message.message_id)
            return
            
        text = f"🆕 **أحدث الفيديوهات**\n\n"
        
        markup = types.InlineKeyboardMarkup()
        
        for i, video in enumerate(recent, 1):
            title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
            title_short = title[:30] + "..." if len(title) > 30 else title
            
            text += f"**{i}.** {title_short}\n\n"
            
            btn = types.InlineKeyboardButton(f"{i}. {title[:20]}...", callback_data=f"video_{video[0]}")
            markup.add(btn)
            
        btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        markup.add(btn_back)
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ خطأ في الفيديوهات الحديثة: {e}")


def handle_stats_menu(bot, call):
    """معالج الإحصائيات"""
    try:
        from app.services.stats_service import StatsService
        
        stats = StatsService.get_general_stats()
        
        stats_text = f"""📊 **إحصائيات أرشيف الفيديوهات**

🎬 **الفيديوهات:** {stats.get('videos', 0):,}
👥 **المستخدمون:** {stats.get('users', 0):,}  
📚 **التصنيفات:** {stats.get('categories', 0):,}
⭐ **المفضلات:** {stats.get('favorites', 0):,}
👁️ **إجمالي المشاهدات:** {stats.get('total_views', 0):,}

🤖 **حالة النظام:**
✅ **البوت يعمل 24/7** مع Webhooks
🌐 **الطريقة:** Webhooks (بدون تضارب)
🔄 **آخر تحديث:** {datetime.now().strftime('%H:%M')}

🚀 **استمتع بتصفح الأرشيف المجاني!**"""
        
        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        markup.add(btn_back)
        
        bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, 
                            reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ خطأ في الإحصائيات: {e}")


def handle_help_menu(bot, call):
    """معالج المساعدة"""
    help_text = """🎬 **مساعدة أرشيف الفيديوهات**

**🔍 البحث المحسن:**
• اكتب اسم الفيديو مباشرة
• البحث في العنوان والوصف واسم الملف

**📚 التصنيفات:**
• تصفح المحتوى منظم
• أزرار التالي والسابق

**⭐ المفضلة:**
• احفظ الفيديوهات المفضلة
• وصول سريع

**📊 سجل المشاهدة:**
• تتبع ما شاهدته
• حذف تلقائي بعد 15 يوم

**🤖 النظام:**
✅ يعمل 24/7 بـ Webhooks
✅ بدون تضارب
✅ استجابة فورية
✅ معالجة ذكية للبيانات pymediainfo"""
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_back)
    
    bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id,
                        reply_markup=markup, parse_mode='Markdown')


def register_all_callbacks(bot):
    """تسجيل معالجات الأزرار"""
    try:
        bot.callback_query_handler(func=lambda call: True)(lambda call: handle_callback_query(bot, call))
        logger.info("✅ تم تسجيل معالجات الأزرار بنجاح")
    except Exception as e:
        logger.error(f"❌ خطأ في تسجيل معالجات الأزرار: {e}")