"""معالج الفيديوهات للأرشفة والمشاهدة - إصدار مُصحح نهائي"""
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
    """تحميل/جلب الفيديو - طريقة محسنة مع حل جميع المشاكل"""
    try:
        video = VideoService.get_video_by_id(video_id)
        if not video:
            bot.answer_callback_query(call.id, "❌ الفيديو غير متاح", show_alert=True)
            return

        title = video[9] if video[9] else (video[4] if video[4] else f"فيديو {video[0]}")
        file_id = video[5]  # file_id
        
        # الطريقة الأولى: استخدام file_id مباشرة (الأكثر موثوقية)
        if file_id and file_id != "":
            try:
                caption = f"🎬 {title}\n\n📥 من أرشيف الفيديوهات المتقدم\n🤖 تم الجلب تلقائياً"
                
                # تحديد نوع الملف وإرساله
                file_name = (video[4] or "").lower()
                if file_name.endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv')):
                    sent_msg = bot.send_video(chat_id=call.message.chat.id, video=file_id, caption=caption)
                elif file_name.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    sent_msg = bot.send_photo(chat_id=call.message.chat.id, photo=file_id, caption=caption)
                else:
                    sent_msg = bot.send_document(chat_id=call.message.chat.id, document=file_id, caption=caption)
                
                bot.answer_callback_query(call.id, "✅ تم إرسال الفيديو بنجاح!")
                logger.info(f"✅ تم إرسال الفيديو {video_id} بنجاح عبر file_id للمستخدم {call.from_user.id}")
                return
                
            except Exception as file_error:
                logger.warning(f"⚠️ فشل إرسال file_id للفيديو {video_id}: {file_error}")
                # المتابعة للطريقة التالية
        
        # الطريقة الثانية: محاولة الحصول على ملف جديد من التيليجرام
        if file_id and file_id != "":
            try:
                # محاولة الحصول على معلومات الملف المُحدثة
                file_info = bot.get_file(file_id)
                if file_info and file_info.file_path:
                    # إرسال الملف بطريقة مختلفة
                    caption = f"🎬 {title}\n\n📥 تم جلبه من الأرشيف (طريقة 2)"
                    
                    file_name = (video[4] or "").lower()
                    if file_name.endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm')):
                        bot.send_video(chat_id=call.message.chat.id, video=file_id, caption=caption, timeout=60)
                    else:
                        bot.send_document(chat_id=call.message.chat.id, document=file_id, caption=caption, timeout=60)
                    
                    bot.answer_callback_query(call.id, "✅ تم جلب الفيديو (الطريقة 2)!")
                    logger.info(f"✅ تم إرسال الفيديو {video_id} عبر get_file للمستخدم {call.from_user.id}")
                    return
                    
            except Exception as get_file_error:
                logger.warning(f"⚠️ فشل get_file للفيديو {video_id}: {get_file_error}")
        
        # الطريقة الثالثة: copy_message من المصدر (إذا توفرت المعلومات)
        source_chat_id = video[3]  # chat_id
        source_message_id = video[1]  # message_id
        
        if source_chat_id and source_message_id:
            try:
                logger.info(f"🔄 محاولة copy_message للفيديو {video_id} من {source_chat_id}:{source_message_id}")
                
                copied_msg = bot.copy_message(
                    chat_id=call.message.chat.id,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id,
                    caption=f"🎬 {title}\n\n📥 تم جلبه من المصدر الأصلي"
                )
                
                bot.answer_callback_query(call.id, "✅ تم جلب الفيديو من المصدر!")
                logger.info(f"✅ تم copy_message للفيديو {video_id} بنجاح")
                return
                
            except Exception as copy_error:
                logger.warning(f"⚠️ فشل copy_message للفيديو {video_id}: {copy_error}")
                
                # محاولة forward_message كبديل
                try:
                    logger.info(f"🔄 محاولة forward_message للفيديو {video_id}")
                    forwarded_msg = bot.forward_message(
                        chat_id=call.message.chat.id,
                        from_chat_id=source_chat_id,
                        message_id=source_message_id
                    )
                    bot.answer_callback_query(call.id, "✅ تم إعادة توجيه الفيديو!")
                    logger.info(f"✅ تم forward_message للفيديو {video_id} بنجاح")
                    return
                    
                except Exception as forward_error:
                    logger.warning(f"⚠️ فشل forward_message للفيديو {video_id}: {forward_error}")
        
        # إذا فشلت جميع الطرق - إرسال رسالة مساعدة
        help_text = f"❌ تعذر جلب الفيديو: {title}\n\n"
        help_text += "الأسباب المحتملة:\n"
        help_text += "• انتهت صلاحية الملف\n"
        help_text += "• تم حذف الرسالة الأصلية\n"
        help_text += "• البوت غير مضاف للقناة المصدر\n"
        help_text += "• مشكلة في الاتصال بالتيليجرام\n\n"
        help_text += "💡 جرب مرة أخرى أو اتصل بالمشرف"
        
        # إرسال معلومات مفصلة للمشرف
        from main import ADMIN_IDS
        if call.from_user.id in ADMIN_IDS:
            help_text += f"\n\n🔧 تفاصيل للمشرف:\n"
            help_text += f"🆔 الفيديو: {video_id}\n"
            help_text += f"💬 المصدر: {source_chat_id}\n"
            help_text += f"📨 الرسالة: {source_message_id}\n"
            help_text += f"📄 File ID: {(file_id or 'غير متوفر')[:30]}...\n"
        
        bot.answer_callback_query(call.id, "❌ تعذر جلب الفيديو - راجع الرسالة", show_alert=True)
        bot.send_message(call.message.chat.id, help_text)
        logger.error(f"❌ فشل جلب الفيديو {video_id} بجميع الطرق")
            
    except Exception as e:
        logger.error(f"❌ خطأ عام في جلب الفيديو: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ غير متوقع", show_alert=True)


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
            
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id  # أكبر حجم
            file_name = f"photo_{message.message_id}.jpg"
            
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
            response_text = f"✅ تم حفظ الملف في الأرشيف بنجاح\n\n"
            response_text += f"🎬 العنوان: {title}\n"
            response_text += f"📄 اسم الملف: {file_name}\n"
            response_text += f"📚 التصنيف: افتراضي (غير مصنف)\n"
            response_text += f"💬 المحادثة المصدر: {message.chat.id}\n"
            response_text += f"📨 معرف الرسالة: {message.message_id}\n"
            
            if metadata.get('season'):
                response_text += f"📺 الموسم: {metadata['season']}\n"
            if metadata.get('episode'):
                response_text += f"📋 الحلقة: {metadata['episode']}\n"
            if metadata.get('quality'):
                response_text += f"🎥 الجودة: {metadata['quality']}\n"
            
            response_text += f"\n🤖 تم الحفظ تلقائياً بواسطة النظام المتطور!"
            
            # إنشاء أزرار للإجراءات السريعة
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📚 تغيير التصنيف", callback_data=f"admin_video_move_{message.message_id}"),
                types.InlineKeyboardButton("✏️ تعديل العنوان", callback_data=f"admin_video_edit_{message.message_id}")
            )
            markup.add(types.InlineKeyboardButton("🔍 عرض التفاصيل", callback_data=f"video_{message.message_id}"))
            
            bot.send_message(message.chat.id, response_text, reply_markup=markup)
            logger.info(f"✅ تم أرشفة الملف بنجاح: {title} من المحادثة {message.chat.id}")
            
        else:
            bot.send_message(message.chat.id, "❌ حدث خطأ في حفظ الملف - تحقق من قاعدة البيانات")
            logger.error(f"❌ فشل في حفظ الملف: {file_name}")

    except Exception as e:
        logger.error(f"❌ خطأ في أرشفة الملف: {e}")
        bot.send_message(message.chat.id, f"❌ حدث خطأ في حفظ الملف: {str(e)[:100]}...")


def register_video_handlers(bot):
    """تسجيل معالجات الفيديوهات"""
    
    @bot.message_handler(content_types=['video', 'document', 'photo'])
    def video_archive_handler(message):
        from main import ADMIN_IDS
        if message.from_user.id in ADMIN_IDS:
            handle_video_archive(bot, message)
        else:
            logger.info(f"ℹ️ تم تجاهل ملف من مستخدم غير مشرف: {message.from_user.id}")
    
    logger.info("✅ تم تسجيل معالجات الفيديوهات")
