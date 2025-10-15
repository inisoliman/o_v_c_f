"""معالج الفيديوهات للأرشفة والمشاهدة - إصدار مُصحح وآمن"""
import logging
import json
from telebot import types
from app.services.video_service import VideoService
from app.services.user_service import UserService
from app.utils.metadata_extractor import extract_video_metadata, create_grouping_key

logger = logging.getLogger(__name__)


def handle_video_details(bot, call, user_id, video_id):
    try:
        video = VideoService.get_video_by_id(video_id)
        if not video:
            bot.answer_callback_query(call.id, "❌ الفيديو غير موجود")
            return

        VideoService.update_view_count(video_id)
        UserService.add_to_history(user_id, video_id)

        title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
        text = f"🎬 {title}\n\n"
        if video[2]:
            desc = video[2][:200] + "..." if len(video[2]) > 200 else video[2]
            text += f"📝 الوصف:\n{desc}\n\n"
        if len(video) > 12 and video[12]:
            text += f"📚 التصنيف: {video[12]}\n"
        if video[4]:
            file_name = video[4][:50] + "..." if len(video[4]) > 50 else video[4]
            text += f"📄 اسم الملف: {file_name}\n"
        text += "\n📊 الإحصائيات:\n"
        text += f"👁️ المشاهدات: {video[8]:,}\n"
        if video[11]:
            try:
                upload_date = video[11].strftime('%Y-%m-%d')
                text += f"📅 تاريخ الرفع: {upload_date}\n"
            except:
                pass

        is_fav = UserService.is_favorite(user_id, video_id)
        fav_text = "❤️ إزالة من المفضلة" if is_fav else "💖 إضافة للمفضلة"

        markup = types.InlineKeyboardMarkup()
        row = []
        if video[5]:
            row.append(types.InlineKeyboardButton("📥 تحميل", callback_data=f"download_{video_id}"))
        row.append(types.InlineKeyboardButton(fav_text, callback_data=f"favorite_{video_id}"))
        if row:
            markup.add(*row)
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))

        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            logger.error(f"❌ edit_message_text failed: {e}")
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
    except Exception as e:
        logger.error(f"❌ خطأ في تفاصيل الفيديو: {e}")
        try:
            bot.edit_message_text("❌ حدث خطأ في عرض الفيديو", call.message.chat.id, call.message.message_id)
        except:
            pass


def handle_video_download(bot, call, video_id):
    try:
        video = VideoService.get_video_by_id(video_id)
        if not video or not video[5]:
            bot.answer_callback_query(call.id, "❌ الفيديو غير متاح للتحميل", show_alert=True)
            return

        title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
        caption = f"🎬 {title}\n\n📥 من أرشيف الفيديوهات المتقدم"

        file_name = (video[4] or "").lower()
        if file_name.endswith(('.mp4', '.mkv', '.avi', '.mov')):
            bot.send_video(chat_id=call.message.chat.id, video=video[5], caption=caption)
        else:
            bot.send_document(chat_id=call.message.chat.id, document=video[5], caption=caption)

        bot.answer_callback_query(call.id, "✅ تم إرسال الفيديو!")
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال الفيديو: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء التحميل")


def handle_toggle_favorite(bot, call, user_id, video_id):
    try:
        is_added = UserService.toggle_favorite(user_id, video_id)
        if is_added:
            bot.answer_callback_query(call.id, "✅ تم إضافة للمفضلة!")
        else:
            bot.answer_callback_query(call.id, "❌ تم إزالة من المفضلة")
        handle_video_details(bot, call, user_id, video_id)
    except Exception as e:
        logger.error(f"❌ خطأ في المفضلة: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")


def handle_video_archive(bot, message):
    try:
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_name = getattr(message.video, 'file_name', '') or f"video_{message.message_id}.mp4"
        elif message.content_type == 'document':
            file_id = message.document.file_id
            file_name = message.document.file_name or f"document_{message.message_id}"
        else:
            return

        caption = message.caption or ""
        metadata = extract_video_metadata(caption, file_name)
        title = metadata.get('series_name', '') or file_name.split('.')[0]
        grouping_key = create_grouping_key(metadata, file_name)

        success = VideoService.add_video(
            message_id=message.message_id,
            caption=caption,
            chat_id=message.chat.id,
            file_name=file_name,
            file_id=file_id,
            category_id=1,
            metadata=json.dumps(metadata),
            title=title,
            grouping_key=grouping_key
        )

        if success:
            txt = f"✅ تم حفظ الفيديو\n🎬 العنوان: {title}"
            bot.send_message(message.chat.id, txt)
        else:
            bot.send_message(message.chat.id, "❌ حدث خطأ في حفظ الفيديو")
    except Exception as e:
        logger.error(f"❌ خطأ في أرشفة الفيديو: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ في حفظ الفيديو")


def register_video_handlers(bot):
    @bot.message_handler(content_types=['video', 'document'])
    def _vh(message):
        from main import ADMIN_IDS
        if message.from_user.id in ADMIN_IDS:
            handle_video_archive(bot, message)
    logger.info("✅ تم تسجيل معالجات الفيديوهات")
