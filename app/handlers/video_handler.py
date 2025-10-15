"""معالج الفيديوهات للأرشفة والمشاهدة - إصدار مُصحح مع حل chat not found"""
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
    """تحميل/جلب الفيديو - الطريقة المحسنة مع حل chat not found"""
    try:
        video = VideoService.get_video_by_id(video_id)
        if not video:
            bot.answer_callback_query(call.id, "❌ الفيديو غير متاح", show_alert=True)
            return

        title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
        file_id = video[5]  # file_id
        
        # الطريقة الأولى والأساسية: استخدام file_id مباشرة
        if file_id:
            try:
                caption = f"🎬 {title}\n\n📥 من الأرشيف المتقدم"
                
                # تحديد نوع الملف
                file_name = (video[4] or "").lower()
                if file_name.endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm')):
                    bot.send_video(chat_id=call.message.chat.id, video=file_id, caption=caption)
                else:
                    bot.send_document(chat_id=call.message.chat.id, document=file_id, caption=caption)
                
                bot.answer_callback_query(call.id, "✅ تم إرسال الفيديو!")
                logger.info(f"✅ تم إرسال الفيديو {video_id} بنجاح عبر file_id")
                return
                
            except Exception as file_error:
                logger.warning(f"⚠️ فشل إرسال file_id للفيديو {video_id}: {file_error}")
                # المتابعة للطريقة الثانية
        
        # الطريقة الثانية: copy_message من المصدر (إذا توفر الوصول)
        source_chat_id = video[3]     # chat_id حيث الرسالة الأصلية
        source_message_id = video[1]  # message_id للرسالة الأصلية
        
        if source_chat_id and source_message_id:
            try:
                logger.info(f"🔄 محاولة copy_message للفيديو {video_id} من المحادثة {source_chat_id}")
                
                bot.copy_message(
                    chat_id=call.message.chat.id,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id,
                    caption=f"🎬 {title}\n\n📥 تم جلبه من الأرشيف"
                )
                
                bot.answer_callback_query(call.id, "✅ تم جلب الفيديو من المصدر!")
                logger.info(f"✅ تم copy_message للفيديو {video_id} بنجاح")
                return
                
            except Exception as copy_error:
                logger.warning(f"⚠️ فشل copy_message للفيديو {video_id}: {copy_error}")
                
                # محاولة forward_message كبديل ثالث
                try:
                    logger.info(f"🔄 محاولة forward_message للفيديو {video_id}")
                    bot.forward_message(
                        chat_id=call.message.chat.id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id
                    )
                    bot.answer_callback_query(call.id, "✅ تم إعادة توجيه الفيديو!")
                    logger.info(f"✅ تم forward_message للفيديو {video_id} بنجاح")
                    return
                    
                except Exception as forward_error:
                    logger.warning(f"⚠️ فشل forward_message أيضاً للفيديو {video_id}: {forward_error}")
        
        # إذا فشلت جميع الطرق
        error_msg = (
            f"❌ تعذر الوصول للفيديو: {title}\n\n"
            "الأسباب المحتملة:\n"
            "• البوت غير مضاف للقناة المصدر\n"
            "• الملف منتهي الصلاحية\n"
            "• تم حذف الرسالة الأصلية\n\n"
            "اتصل بالمشرف لحل المشكلة"
        )
        bot.answer_callback_query(call.id, "❌ تعذر جلب الفيديو", show_alert=True)
        
        # إرسال رسالة تفصيلية للمشرف فقط
        from main import ADMIN_IDS
        if call.from_user.id in ADMIN_IDS:
            admin_error_msg = f"🔧 تفاصيل للمشرف:\n"
            admin_error_msg += f"🆔 الفيديو: {video_id}\n"
            admin_error_msg += f"💬 المحادثة المصدر: {source_chat_id}\n"
            admin_error_msg += f"📨 الرسالة المصدر: {source_message_id}\n"
            admin_error_msg += f"📄 File ID: {file_id[:50]}...\n\n"
            admin_error_msg += "تأكد من:\n"
            admin_error_msg += "1. إضافة البوت للقناة/الجروب المصدر\n"
            admin_error_msg += "2. صحة معرف المحادثة المصدر\n"
            admin_error_msg += "3. وجود الرسالة الأصلية"
            
            bot.send_message(call.message.chat.id, admin_error_msg)
            
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
        
        # الحصول على التصنيف الافتراضي
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
            response_text = f"✅ تم حفظ الفيديو في الأرشيف\n\n"
            response_text += f"🎬 العنوان: {title}\n"
            response_text += f"📄 اسم الملف: {file_name}\n"
            response_text += f"📚 التصنيف: افتراضي\n"
            
            if metadata.get('season'):
                response_text += f"📺 الموسم: {metadata['season']}\n"
            if metadata.get('episode'):
                response_text += f"📋 الحلقة: {metadata['episode']}\n"
            if metadata.get('quality'):
                response_text += f"🎥 الجودة: {metadata['quality']}\n"
            
            response_text += f"\n🆔 معرف الفيديو: {message.message_id}"
            
            bot.send_message(message.chat.id, response_text)
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
        from main import ADMIN_IDS
        if message.from_user.id in ADMIN_IDS:
            handle_video_archive(bot, message)
    
    logger.info("✅ تم تسجيل معالجات الفيديوهات")
