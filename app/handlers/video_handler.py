"""معالج الفيديوهات للأرشفة والمشاهدة - إصدار مُصحح"""
import logging
import json
from telebot import types
from app.services.video_service import VideoService
from app.services.user_service import UserService
from app.utils.metadata_extractor import extract_video_metadata, create_grouping_key

logger = logging.getLogger(__name__)


def handle_video_details(bot, call, user_id, video_id):
    """معالج تفاصيل الفيديو"""
    try:
        video = VideoService.get_video_by_id(video_id)
        
        if not video:
            bot.answer_callback_query(call.id, "❌ الفيديو غير موجود")
            return
        
        # تحديث عداد المشاهدة وإضافة للسجل
        VideoService.update_view_count(video_id)
        UserService.add_to_history(user_id, video_id)
        
        # تنسيق معلومات الفيديو
        title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
        text = f"🎬 **{title}**\n\n"
        
        if video[2]:  # caption
            desc = video[2][:200] + "..." if len(video[2]) > 200 else video[2]
            text += f"📝 **الوصف:**\n{desc}\n\n"
        
        # معلومات إضافية
        if len(video) > 12 and video[12]:  # category_name
            text += f"📚 **التصنيف:** {video[12]}\n"
        
        if video[4]:  # file_name
            file_name = video[4][:50] + "..." if len(video[4]) > 50 else video[4]
            text += f"📄 **اسم الملف:** {file_name}\n"
        
        text += f"\n📊 **الإحصائيات:**\n"
        text += f"👁️ **المشاهدات:** {video[8]:,}\n"
        
        if video[11]:  # upload_date
            upload_date = video[11].strftime('%Y-%m-%d')
            text += f"📅 **تاريخ الرفع:** {upload_date}\n"
        
        # معلومات الميتاداتا
        if video[7]:  # metadata
            try:
                metadata = json.loads(video[7]) if isinstance(video[7], str) else video[7]
                if metadata:
                    text += f"\n🔍 **تفاصيل إضافية:**\n"
                    if metadata.get('season_number'):
                        text += f"📺 **الموسم:** {metadata['season_number']}\n"
                    if metadata.get('episode_number'):
                        text += f"🎬 **الحلقة:** {metadata['episode_number']}\n"
                    if metadata.get('quality_resolution'):
                        text += f"🎥 **الجودة:** {metadata['quality_resolution']}\n"
                    if metadata.get('status'):
                        text += f"🎭 **الحالة:** {metadata['status']}\n"
            except:
                pass
        
        # فحص المفضلة
        is_fav = UserService.is_favorite(user_id, video_id)
        fav_text = "❤️ إزالة من المفضلة" if is_fav else "💖 إضافة للمفضلة"
        
        markup = types.InlineKeyboardMarkup()
        
        # أزرار التحكم
        buttons_row1 = []
        
        if video[5]:  # file_id exists
            btn_download = types.InlineKeyboardButton("📥 تحميل", callback_data=f"download_{video_id}")
            buttons_row1.append(btn_download)
        
        btn_favorite = types.InlineKeyboardButton(fav_text, callback_data=f"favorite_{video_id}")
        buttons_row1.append(btn_favorite)
        
        if buttons_row1:
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


def handle_video_download(bot, call, video_id):
    """معالج تحميل الفيديو"""
    try:
        video = VideoService.get_video_by_id(video_id)
        
        if not video or not video[5]:  # لا يوجد file_id
            bot.answer_callback_query(call.id, "❌ الفيديو غير متاح للتحميل", show_alert=True)
            return
        
        # إرسال الفيديو
        title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
        caption = f"🎬 **{title}**\n\n📥 **من أرشيف الفيديوهات المتقدم**"
        
        # فحص نوع الملف
        file_name = video[4] or ""
        if file_name.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
            bot.send_video(
                chat_id=call.message.chat.id,
                video=video[5],  # file_id
                caption=caption,
                parse_mode="Markdown"
            )
        else:
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


def handle_toggle_favorite(bot, call, user_id, video_id):
    """معالج إضافة/إزالة المفضلة"""
    try:
        is_added = UserService.toggle_favorite(user_id, video_id)
        
        if is_added:
            bot.answer_callback_query(call.id, "✅ تم إضافة للمفضلة!")
        else:
            bot.answer_callback_query(call.id, "❌ تم إزالة من المفضلة")
        
        # إعادة تحميل صفحة الفيديو
        handle_video_details(bot, call, user_id, video_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في المفضلة: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")


def handle_video_archive(bot, message):
    """معالج أرشفة الفيديوهات (للمشرفين)"""
    try:
        # استخلاص معلومات الفيديو
        file_id = None
        file_name = None
        duration = 0
        
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_name = getattr(message.video, 'file_name', '') or f"video_{message.message_id}.mp4"
            duration = getattr(message.video, 'duration', 0)
        elif message.content_type == 'document':
            file_id = message.document.file_id
            file_name = message.document.file_name or f"document_{message.message_id}"
        
        if not file_id:
            return
        
        # استخلاص البيانات الوصفية من الكابشن
        caption = message.caption or ""
        metadata = extract_video_metadata(caption, file_name)
        
        # استخلاص العنوان
        title = metadata.get('series_name', '') or file_name.split('.')[0]
        
        # إنشاء grouping_key
        grouping_key = create_grouping_key(metadata, file_name)
        
        # حفظ في قاعدة البيانات
        success = VideoService.add_video(
            message_id=message.message_id,
            caption=caption,
            chat_id=message.chat.id,
            file_name=file_name,
            file_id=file_id,
            category_id=1,  # Uncategorized بشكل افتراضي
            metadata=json.dumps(metadata),
            title=title,
            grouping_key=grouping_key
        )
        
        if success:
            response = f"✅ **تم حفظ الفيديو بنجاح!**\n\n"
            response += f"🎬 **العنوان:** {title}\n"
            
            if metadata:
                response += "\n🔍 **البيانات المستخرجة:**\n"
                if metadata.get('series_name'):
                    response += f"• الاسم: {metadata['series_name']}\n"
                if metadata.get('season_number'):
                    response += f"• الموسم: {metadata['season_number']}\n"
                if metadata.get('episode_number'):
                    response += f"• الحلقة: {metadata['episode_number']}\n"
                if metadata.get('quality_resolution'):
                    response += f"• الجودة: {metadata['quality_resolution']}\n"
                if metadata.get('status'):
                    response += f"• الحالة: {metadata['status']}\n"
            
            bot.reply_to(message, response, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ حدث خطأ في حفظ الفيديو")
            
    except Exception as e:
        logger.error(f"❌ خطأ في أرشفة الفيديو: {e}")
        bot.reply_to(message, "❌ حدث خطأ في حفظ الفيديو")


def register_video_handlers(bot):
    """تسجيل معالجات الفيديوهات"""
    try:
        # معالج الفيديوهات للمشرفين فقط
        @bot.message_handler(content_types=['video', 'document'])
        def video_handler(message):
            from main import ADMIN_IDS
            if message.from_user.id in ADMIN_IDS:
                handle_video_archive(bot, message)
        
        logger.info("✅ تم تسجيل معالجات الفيديوهات")
        
    except Exception as e:
        logger.error(f"❌ خطأ في تسجيل معالجات الفيديوهات: {e}")