"""
معالج شامل لجميع أزرار البوت مع دعم التصفح
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
            bot.delete_message(call.message.chat.id, call.message.message_id)
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
            handle_video_details(bot, call, user_id)
            
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
            handle_video_download(bot, call)
            
        elif data.startswith("favorite_"):
            handle_toggle_favorite(bot, call, user_id)
            
        else:
            bot.answer_callback_query(call.id, "🔄 هذه الميزة قيد التطوير")
        
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
            subcategory_count = category[5] if len(category) > 5 else 0
            
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


def handle_video_details(bot, call, user_id):
    """معالج تفاصيل الفيديو"""
    try:
        from app.services.video_service import VideoService
        from app.services.user_service import UserService
        
        video_id = int(call.data.replace("video_", ""))
        video = VideoService.get_video_by_id(video_id)
        
        if not video:
            bot.answer_callback_query(call.id, "❌ الفيديو غير موجود")
            return
        
        # زيادة عداد المشاهدة وإضافة للسجل
        VideoService.update_view_count(video_id)
        UserService.add_to_history(user_id, video_id)
        
        # تنسيق معلومات الفيديو
        title = video[9] if len(video) > 9 and video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
        text = f"🎬 **{title}**\n\n"
        
        if video[2]:  # caption/description
            desc = video[2][:200] + "..." if len(video[2]) > 200 else video[2]
            text += f"📝 **الوصف:**\n{desc}\n\n"
        
        # معلومات إضافية
        if len(video) > 12 and video[12]:  # category_name
            text += f"📚 **التصنيف:** {video[12]}\n"
        
        if video[4]:  # file_name
            file_name = video[4][:50] + "..." if len(video[4]) > 50 else video[4]
            text += f"📄 **اسم الملف:** {file_name}\n"
        
        text += f"\n📊 **الإحصائيات:**\n"
        text += f"👁️ **المشاهدات:** {video[8]:,}\n"  # view_count
        
        if len(video) > 11 and video[11]:  # upload_date
            upload_date = video[11].strftime('%Y-%m-%d')
            text += f"📅 **تاريخ الرفع:** {upload_date}\n"
        
        # فحص إذا كان في المفضلة
        is_fav = UserService.is_favorite(user_id, video_id)
        fav_text = "❤️ إزالة من المفضلة" if is_fav else "💖 إضافة للمفضلة"
        
        markup = types.InlineKeyboardMarkup()
        
        # أزرار التحكم
        buttons_row1 = []
        
        if video[5]:  # file_id exists - يمكن التحميل
            btn_download = types.InlineKeyboardButton("📥 تحميل", callback_data=f"download_{video_id}")
            buttons_row1.append(btn_download)
        
        btn_favorite = types.InlineKeyboardButton(fav_text, callback_data=f"favorite_{video_id}")
        buttons_row1.append(btn_favorite)
        
        if len(buttons_row1) > 0:
            markup.add(*buttons_row1)
        
        # زر العودة
        btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
        markup.add(btn_back)
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                            reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ خطأ في تفاصيل الفيديو: {e}")
        bot.edit_message_text("❌ حدث خطأ في عرض الفيديو", 
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
✅ استجابة فورية"""
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_back)
    
    bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id,
                        reply_markup=markup, parse_mode='Markdown')


def handle_video_download(bot, call):
    """معالج تحميل الفيديو"""
    try:
        from app.services.video_service import VideoService
        
        video_id = int(call.data.replace("download_", ""))
        video = VideoService.get_video_by_id(video_id)
        
        if not video or not video[5]:  # لا يوجد file_id
            bot.answer_callback_query(call.id, "❌ الفيديو غير متاح للتحميل", show_alert=True)
            return
        
        # إرسال الفيديو
        title = video[9] if len(video) > 9 and video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
        caption = f"🎬 **{title}**\n\n📥 **من أرشيف الفيديوهات**"
        
        bot.send_document(
            chat_id=call.message.chat.id,
            document=video[5],  # file_id
            caption=caption,
            parse_mode="Markdown"
        )
        
        bot.answer_callback_query(call.id, "✅ تم إرسال الفيديو!")
        
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال الفيديو: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء التحميل")


def handle_toggle_favorite(bot, call, user_id):
    """معالج إضافة/إزالة المفضلة"""
    try:
        from app.services.user_service import UserService
        
        video_id = int(call.data.replace("favorite_", ""))
        
        # تغيير حالة المفضلة
        is_added = UserService.toggle_favorite(user_id, video_id)
        
        if is_added:
            bot.answer_callback_query(call.id, "✅ تم إضافة للمفضلة!")
        else:
            bot.answer_callback_query(call.id, "❌ تم إزالة من المفضلة")
        
        # إعادة تحميل صفحة الفيديو
        handle_video_details(bot, call, user_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في المفضلة: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")


def register_all_callbacks(bot):
    """تسجيل معالجات الأزرار"""
    bot.callback_query_handler(func=lambda call: True)(lambda call: handle_callback_query(bot, call))
    logger.info("✅ تم تسجيل معالجات الأزرار")
