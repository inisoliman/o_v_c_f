"""
معالج شامل لجميع أزرار البوت مع دعم التصفح
"""
import logging
import math
from datetime import datetime
from telebot import types
from app.services.video_service import VideoService
from app.services.category_service import CategoryService
from app.services.user_service import UserService
from app.services.stats_service import StatsService

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


def handle_categories_menu(bot, call, page: int = 1):
    """معالج قائمة التصنيفات مع التصفح"""
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
        cat_name = category[1][:30] + "..." if len(category[1]) > 30 else category[1]
        video_count = category[4] if len(category) > 4 else 0
        subcategory_count = category[5] if len(category) > 5 else 0
        
        # إظهار التصنيفات الفرعية إن وجدت
        display_name = cat_name
        if subcategory_count > 0:
            display_name += f" ({video_count} فيديو، {subcategory_count} قسم فرعي)"
        else:
            display_name += f" ({video_count} فيديو)"
        
        text += f"📁 **{cat_name}** - {video_count} فيديو"
        if subcategory_count > 0:
            text += f" + {subcategory_count} قسم فرعي"
        text += "\n"
        
        btn = types.InlineKeyboardButton(f"📁 {display_name}", callback_data=f"category_{category[0]}")
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


def handle_category_videos(bot, call, category_id: int, page: int = 1):
    """معالج فيديوهات التصنيف مع التصفح"""
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
    category_path = category[3] if category[3] else category_name
    
    text = f"📁 **{category_path}**\n"
    text += f"📊 {total_videos} فيديو | صفحة {page}/{total_pages}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    for i, video in enumerate(videos, 1):
        title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
        title_short = title[:40] + "..." if len(title) > 40 else title
        views = video[3] if video[3] else 0
        
        # إضافة الفيديو للنص
        video_number = (page - 1) * per_page + i
        text += f"**{video_number}.** {title_short}\n   👁️ {views:,} مشاهدة\n\n"
        
        # زر الفيديو
        btn = types.InlineKeyboardButton(f"{video_number}. {title[:25]}...", callback_data=f"video_{video[0]}")
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
• `testament` - بالإنجليزية

📝 **اكتب كلمة البحث الآن:**"""
    
    user_states[call.from_user.id] = {'action': 'searching'}
    
    markup = types.InlineKeyboardMarkup()
    btn_cancel = types.InlineKeyboardButton("❌ إلغاء", callback_data="main_menu")
    markup.add(btn_cancel)
    
    bot.edit_message_text(search_text, call.message.chat.id, call.message.message_id,
                        reply_markup=markup, parse_mode='Markdown')


def handle_video_details(bot, call, user_id):
    """معالج تفاصيل الفيديو المحسن"""
    video_id = int(call.data.replace("video_", ""))
    video = VideoService.get_video_by_id(video_id)
    
    if not video:
        bot.answer_callback_query(call.id, "❌ الفيديو غير موجود")
        return
    
    # زيادة عداد المشاهدة وإضافة للسجل
    VideoService.update_view_count(video_id)
    UserService.add_to_history(user_id, video_id)
    
    # تنسيق معلومات الفيديو
    title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
    text = f"🎬 **{title}**\n\n"
    
    if video[2]:  # caption/description
        desc = video[2][:300] + "..." if len(video[2]) > 300 else video[2]
        text += f"📝 **الوصف:**\n{desc}\n\n"
    
    # عرض مسار التصنيف الكامل
    if video[13]:  # category_path
        text += f"📚 **التصنيف:** {video[13]}\n"
    elif video[12]:  # category_name
        text += f"📚 **التصنيف:** {video[12]}\n"
    
    if video[4]:  # file_name
        file_name = video[4][:60] + "..." if len(video[4]) > 60 else video[4]
        text += f"📄 **اسم الملف:** {file_name}\n"
        
    if video[14] and video[14] > 0:  # file_size
        size_mb = video[14] / (1024 * 1024)
        text += f"💾 **الحجم:** {size_mb:.1f} MB\n"
        
    text += f"\n📊 **الإحصائيات:**\n"
    text += f"👁️ **المشاهدات:** {video[8]:,}\n"  # view_count
    
    if video[11]:  # upload_date
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
    
    # أزرار إضافية
    buttons_row2 = []
    if video[6]:  # category_id - عرض المزيد من نفس التصنيف
        btn_more_cat = types.InlineKeyboardButton("📚 المزيد من التصنيف", callback_data=f"category_{video[6]}")
        buttons_row2.append(btn_more_cat)
    
    if len(buttons_row2) > 0:
        markup.add(*buttons_row2)
    
    # زر العودة
    btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
    markup.add(btn_back)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                        reply_markup=markup, parse_mode='Markdown')


def handle_favorites_menu(bot, call, user_id):
    """معالج قائمة المفضلات"""
    favorites = UserService.get_user_favorites(user_id, 15)
    
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


def handle_history_menu(bot, call, user_id):
    """معالج سجل المشاهدة"""
    history = UserService.get_user_history(user_id, 15)
    
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


def handle_popular_videos(bot, call):
    """معالج الفيديوهات الشائعة"""
    popular = VideoService.get_popular_videos(15)
    
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


def handle_recent_videos(bot, call):
    """معالج أحدث الفيديوهات"""
    recent = VideoService.get_recent_videos(15)
    
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


def handle_stats_menu(bot, call):
    """معالج الإحصائيات"""
    stats = StatsService.get_general_stats()
    
    stats_text = f"""📊 **إحصائيات أرشيف الفيديوهات**

🎬 **الفيديوهات:** {stats.get('videos', 0):,}
👥 **المستخدمون:** {stats.get('users', 0):,}  
📚 **التصنيفات:** {stats.get('categories', 0):,}
⭐ **المفضلات:** {stats.get('favorites', 0):,}
👁️ **إجمالي المشاهدات:** {stats.get('total_views', 0):,}

🤖 **حالة النظام:**
✅ **البوت يعمل 24/7** مع نظام Keep Alive
🔄 **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
🗂️ **تنظيف تلقائي:** كل 15 يوم للسجل
🔁 **Self-ping:** كل 14 دقيقة لمنع السكون

🌐 **روابط المراقبة:**
• يمكن متابعة حالة البوت مباشرة

🚀 **استمتع بتصفح الأرشيف المجاني!**"""
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_back)
    
    bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, 
                        reply_markup=markup, parse_mode='Markdown')


def handle_help_menu(bot, call):
    """معالج المساعدة"""
    help_text = """🎬 **مساعدة أرشيف الفيديوهات**

**🔍 البحث المحسن:**
• **البحث السريع:** اكتب اسم الفيديو مباشرة
• **البحث المتقدم:** استخدم زر "البحث المتقدم"
• **يدعم العربية والإنجليزية**
• **يبحث في:** العنوان، الوصف، اسم الملف، البيانات

**📚 التصنيفات:**
• تصفح المحتوى حسب النوع
• دعم التصنيفات الفرعية
• أزرار التالي والسابق للتنقل
• مسار التصنيف الكامل

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
✅ **بحث محسن في جميع الحقول**
✅ **تصفح مع أزرار التنقل**
✅ **دعم التصنيفات الفرعية**

للمساعدة أو الاستفسار تواصل مع المشرف"""
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_back)
    
    bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id,
                        reply_markup=markup, parse_mode='Markdown')


def handle_video_download(bot, call):
    """معالج تحميل الفيديو"""
    video_id = int(call.data.replace("download_", ""))
    video = VideoService.get_video_by_id(video_id)
    
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
        
        bot.answer_callback_query(call.id, "✅ تم إرسال الفيديو بنجاح!", show_alert=True)
        
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال الفيديو: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء التحميل، جرب مرة أخرى", show_alert=True)


def handle_toggle_favorite(bot, call, user_id):
    """معالج إضافة/إزالة المفضلة"""
    video_id = int(call.data.replace("favorite_", ""))
    
    # تغيير حالة المفضلة
    is_added = UserService.toggle_favorite(user_id, video_id)
    
    if is_added:
        bot.answer_callback_query(call.id, "✅ تم إضافة الفيديو للمفضلة بنجاح!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "❌ تم إزالة الفيديو من المفضلة", show_alert=True)
    
    # إعادة تحميل صفحة الفيديو لتحديث أزرار المفضلة
    handle_video_details(bot, call, user_id)


def register_all_callbacks(bot):
    """تسجيل معالجات الأزرار"""
    bot.callback_query_handler(func=lambda call: True)(lambda call: handle_callback_query(bot, call))
    logger.info("✅ تم تسجيل معالجات الأزرار المحسنة")
