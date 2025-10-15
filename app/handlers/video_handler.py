"""معالج الفيديوهات للأرشفة والمشاهدة - إصدار مُصحح مع جلب من المصدر"""
import logging
import json
import os
from telebot import types
from app.services.video_service import VideoService
from app.services.user_service import UserService
from app.utils.metadata_extractor import extract_video_metadata, create_grouping_key

logger = logging.getLogger(__name__)


def handle_video_details(bot, call, user_id, video_id):
    """عرض تفاصيل الفيديو مع إحصائيات وأزرار التحكم"""
    try:
        video = VideoService.get_video_by_id(video_id)
        if not video:
            bot.answer_callback_query(call.id, "❌ الفيديو غير موجود")
            return

        # تحديث عداد المشاهدة وإضافة للسجل
        VideoService.update_view_count(video_id)
        UserService.add_to_history(user_id, video_id)

        # بناء معلومات الفيديو
        title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
        
        text = f"🎬 {title}\n\n"
        
        # إضافة الوصف إن وُجد
        if video[2]:
            desc = video[2][:300] + "..." if len(video[2]) > 300 else video[2]
            text += f"📝 الوصف:\n{desc}\n\n"
        
        # معلومات إضافية
        if len(video) > 12 and video[12]:  # category_name
            text += f"📚 التصنيف: {video[12]}\n"
        
        if video[4]:  # file_name
            file_name = video[4][:50] + "..." if len(video[4]) > 50 else video[4]
            text += f"📄 اسم الملف: {file_name}\n"
        
        # إحصائيات الفيديو
        text += f"\n📊 الإحصائيات:\n"
        text += f"👁️ المشاهدات: {video[8]:,}\n"  # view_count
        
        if video[11]:  # upload_date
            try:
                upload_date = video[11].strftime('%Y-%m-%d %H:%M')
                text += f"📅 تاريخ الرفع: {upload_date}\n"
            except:
                pass
        
        # معلومات المصدر للمشرفين
        from main import ADMIN_IDS
        if user_id in ADMIN_IDS:
            text += f"\n🔧 معلومات المصدر (للمشرف):\n"
            text += f"🆔 معرف الفيديو: {video[0]}\n"
            text += f"💬 معرف المحادثة: {video[3]}\n"
            text += f"📨 معرف الرسالة: {video[1]}\n"

        # التحقق من المفضلة
        is_fav = UserService.is_favorite(user_id, video_id)
        fav_text = "❤️ إزالة من المفضلة" if is_fav else "💖 إضافة للمفضلة"

        # إنشاء لوحة الأزرار
        markup = types.InlineKeyboardMarkup()
        
        # صف الأزرار الأول: تحميل ومفضلة
        first_row = []
        
        # زر التحميل - متاح دائماً
        first_row.append(types.InlineKeyboardButton("📥 جلب الفيديو", callback_data=f"download_{video_id}"))
        
        # زر المفضلة
        first_row.append(types.InlineKeyboardButton(fav_text, callback_data=f"favorite_{video_id}"))
        
        markup.add(*first_row)
        
        # أزرار إضافية للمشرفين
        if user_id in ADMIN_IDS:
            admin_row = []
            admin_row.append(types.InlineKeyboardButton("🗂️ نقل التصنيف", callback_data=f"admin_video_move_{video_id}"))
            admin_row.append(types.InlineKeyboardButton("🗑️ حذف", callback_data=f"admin_video_delete_{video_id}"))
            markup.add(*admin_row)
        
        # زر العودة
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))

        # إرسال التفاصيل
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            logger.error(f"❌ فشل تعديل رسالة التفاصيل: {e}")
            # كبديل: أرسل رسالة جديدة
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
            
    except Exception as e:
        logger.error(f"❌ خطأ في تفاصيل الفيديو: {e}")
        try:
            bot.edit_message_text("❌ حدث خطأ في عرض الفيديو", call.message.chat.id, call.message.message_id)
        except:
            bot.send_message(call.message.chat.id, "❌ حدث خطأ في عرض الفيديو")


def handle_video_download(bot, call, video_id):
    """تحميل/جلب الفيديو من المصدر الأصلي"""
    try:
        video = VideoService.get_video_by_id(video_id)
        if not video:
            bot.answer_callback_query(call.id, "❌ الفيديو غير متاح", show_alert=True)
            return

        # معلومات المصدر
        source_chat_id = video[3]     # chat_id حيث الرسالة الأصلية
        source_message_id = video[1]  # message_id للرسالة الأصلية
        
        title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")

        # التحقق من وجود بيانات المصدر
        if not source_chat_id or not source_message_id:
            # محاولة استخدام SOURCE_CHAT_ID من متغيرات البيئة كبديل
            source_chat_id = source_chat_id or int(os.getenv('SOURCE_CHAT_ID', '0'))
            
            if not source_chat_id or not source_message_id:
                # آخر محاولة: استخدام file_id إذا كان متوفراً
                file_id = video[5]  # file_id
                if file_id:
                    logger.warning(f"⚠️ استخدام file_id مباشرة للفيديو {video_id}")
                    try:
                        caption = f"🎬 {title}\n\n📥 من الأرشيف المتقدم"
                        
                        # تحديد نوع الملف
                        file_name = (video[4] or "").lower()
                        if file_name.endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm')):
                            bot.send_video(chat_id=call.message.chat.id, video=file_id, caption=caption)
                        else:
                            bot.send_document(chat_id=call.message.chat.id, document=file_id, caption=caption)
                        
                        bot.answer_callback_query(call.id, "✅ تم إرسال الفيديو!")
                        return
                    except Exception as file_error:
                        logger.error(f"❌ فشل إرسال file_id: {file_error}")
                        bot.answer_callback_query(call.id, "❌ file_id غير صالح", show_alert=True)
                        return
                else:
                    bot.answer_callback_query(call.id, "❌ بيانات المصدر غير مكتملة", show_alert=True)
                    return

        # الطريقة المثلى: copy_message من المصدر
        try:
            logger.info(f"📥 جلب الفيديو {video_id} من المحادثة {source_chat_id} الرسالة {source_message_id}")
            
            # نسخ الرسالة من المصدر إلى المستخدم
            copied_message = bot.copy_message(
                chat_id=call.message.chat.id,
                from_chat_id=source_chat_id,
                message_id=source_message_id,
                caption=f"🎬 {title}\n\n📥 تم جلبه من الأرشيف المتقدم"
            )
            
            bot.answer_callback_query(call.id, "✅ تم جلب الفيديو بنجاح!")
            logger.info(f"✅ تم جلب الفيديو {video_id} بنجاح للمستخدم {call.from_user.id}")
            
        except Exception as copy_error:
            logger.error(f"❌ فشل في copy_message للفيديو {video_id}: {copy_error}")
            
            # محاولة أخيرة: forward_message
            try:
                logger.info(f"🔄 محاولة forward_message للفيديو {video_id}")
                bot.forward_message(
                    chat_id=call.message.chat.id,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id
                )
                bot.answer_callback_query(call.id, "✅ تم إعادة توجيه الفيديو!")
                
            except Exception as forward_error:
                logger.error(f"❌ فشل في forward_message أيضاً: {forward_error}")
                bot.answer_callback_query(call.id, "❌ تعذر الوصول للفيديو من المصدر", show_alert=True)

    except Exception as e:
        logger.error(f"❌ خطأ عام في جلب الفيديو: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ أثناء جلب الفيديو", show_alert=True)


def handle_toggle_favorite(bot, call, user_id, video_id):
    """إضافة/إزالة فيديو من المفضلة"""
    try:
        is_added = UserService.toggle_favorite(user_id, video_id)
        
        if is_added:
            bot.answer_callback_query(call.id, "✅ تم إضافة للمفضلة!", show_alert=False)
        else:
            bot.answer_callback_query(call.id, "❌ تم إزالة من المفضلة", show_alert=False)
        
        # تحديث عرض التفاصيل
        handle_video_details(bot, call, user_id, video_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في المفضلة: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")


def handle_video_archive(bot, message):
    """أرشفة فيديو جديد من المشرفين"""
    try:
        # تحديد نوع المحتوى والحصول على معلومات الملف
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_name = getattr(message.video, 'file_name', '') or f"video_{message.message_id}.mp4"
            
        elif message.content_type == 'document':
            file_id = message.document.file_id
            file_name = message.document.file_name or f"document_{message.message_id}"
            
        else:
            logger.warning(f"⚠️ نوع محتوى غير مدعوم: {message.content_type}")
            return

        # استخراج معلومات الفيديو
        caption = message.caption or ""
        metadata = extract_video_metadata(caption, file_name)
        
        # تحديد العنوان
        title = metadata.get('series_name', '') or metadata.get('title', '') or file_name.split('.')[0]
        
        # إنشاء مفتاح التجميع
        grouping_key = create_grouping_key(metadata, file_name)
        
        # الحصول على التصنيف الافتراضي (يمكن تطويره لاحقاً للحصول من الإعدادات)
        default_category_id = 1  # Uncategorized
        
        # حفظ في قاعدة البيانات
        success = VideoService.add_video(
            message_id=message.message_id,
            caption=caption,
            chat_id=message.chat.id,
            file_name=file_name,
            file_id=file_id,
            category_id=default_category_id,
            metadata=json.dumps(metadata),
            title=title,
            grouping_key=grouping_key
        )

        if success:
            # رسالة تأكيد الحفظ
            response_text = f"✅ تم حفظ الفيديو في الأرشيف\n\n"
            response_text += f"🎬 العنوان: {title}\n"
            response_text += f"📄 اسم الملف: {file_name}\n"
            response_text += f"📚 التصنيف: افتراضي\n"
            
            # معلومات إضافية من الميتاداتا
            if metadata.get('season'):
                response_text += f"📺 الموسم: {metadata['season']}\n"
            if metadata.get('episode'):
                response_text += f"📋 الحلقة: {metadata['episode']}\n"
            if metadata.get('quality'):
                response_text += f"🎥 الجودة: {metadata['quality']}\n"
            
            response_text += f"\n🆔 معرف الفيديو: {message.message_id}"
            
            # إضافة أزرار للمشرف
            markup = types.InlineKeyboardMarkup()
            # يمكن إضافة أزرار تصنيف سريع هنا لاحقاً
            markup.add(types.InlineKeyboardButton("📚 تغيير التصنيف", callback_data=f"admin_video_move_new_{message.message_id}"))
            
            bot.send_message(message.chat.id, response_text, reply_markup=markup)
            logger.info(f"✅ تم أرشفة الفيديو بنجاح: {title}")
            
        else:
            bot.send_message(message.chat.id, "❌ حدث خطأ في حفظ الفيديو")
            logger.error(f"❌ فشل في حفظ الفيديو: {file_name}")

    except Exception as e:
        logger.error(f"❌ خطأ في أرشفة الفيديو: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ في حفظ الفيديو")


def register_video_handlers(bot):
    """تسجيل معالجات الفيديوهات"""
    
    @bot.message_handler(content_types=['video', 'document'])
    def video_archive_handler(message):
        # التحقق من أن المرسل مشرف
        from main import ADMIN_IDS
        if message.from_user.id in ADMIN_IDS:
            handle_video_archive(bot, message)
        else:
            logger.info(f"ℹ️ تم تجاهل رسالة فيديو من مستخدم غير مشرف: {message.from_user.id}")
    
    logger.info("✅ تم تسجيل معالجات الفيديوهات")
