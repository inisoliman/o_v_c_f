"""
معالج الرسائل النصية والبحث المحسن - مع أزرار تحميل
"""
import logging
import math
from telebot import types
from app.services.video_service import VideoService
from app.handlers.callbacks import user_states

logger = logging.getLogger(__name__)


def handle_text_message(bot, message):
    user_id = message.from_user.id
    query = message.text.strip()
    
    # وضع البحث المتقدم
    if user_id in user_states and user_states[user_id].get('action') == 'searching':
        handle_search_input(bot, message, query)
        return
    
    if len(query) < 2:
        bot.send_message(message.chat.id, "🔍 يرجى كتابة كلمة بحث أكثر من حرف واحد")
        return
    
    # أرسل رسالة انتظار
    wait_msg = bot.send_message(message.chat.id, "🔍 جاري البحث الذكي في الأرشيف...")
    
    try:
        results = VideoService.search_videos(query, limit=15)
        total_count = VideoService.get_search_count(query)
        
        if not results:
            text = (
                f"❌ لم يتم العثور على نتائج: {query}\n\n"
                "💡 اقتراحات:\n"
                "• جرب كلمات أخرى\n"
                "• العربية أو الإنجليزية\n"
                "• كلمات أقل وأعم\n"
                "• تصفح التصنيفات أو الأشهر\n\n"
                "🎯 البحث في: العنوان، الوصف، اسم الملف، البيانات"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📚 التصنيفات", callback_data="categories"),
                types.InlineKeyboardButton("🔥 الأشهر", callback_data="popular")
            )
            markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
            bot.edit_message_text(text, wait_msg.chat.id, wait_msg.message_id, reply_markup=markup)
            return
        
        # صياغة النتائج مع أزرار التحميل
        text = f"🔍 نتائج البحث: {query}\n"
        text += f"📊 تم العثور على {total_count} نتيجة\n\n"
        text += "🎯 البحث تم في: العنوان، الوصف، اسم الملف، البيانات\n\n"
        
        markup = types.InlineKeyboardMarkup()
        for i, video in enumerate(results[:10], 1):
            title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
            title = title[:50] + "..." if len(title) > 50 else title
            views = video[3] if video[3] else 0
            text += f"{i}. {title}\n   👁️ {views:,}\n\n"
            
            # إضافة زرين: تفاصيل و جلب
            btn_details = types.InlineKeyboardButton(f"📺 {i}. {title[:20]}...", callback_data=f"video_{video[0]}")
            btn_download = types.InlineKeyboardButton("📥 جلب", callback_data=f"download_{video[0]}")
            markup.add(btn_details, btn_download)
        
        if total_count > 10:
            text += f"... و {total_count - 10} نتيجة أخرى\n"
        
        buttons_row = []
        if total_count > 15:
            buttons_row.append(types.InlineKeyboardButton("🔍 بحث متقدم", callback_data="search"))
        buttons_row.append(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
        if buttons_row:
            markup.add(*buttons_row)
        
        bot.edit_message_text(text, wait_msg.chat.id, wait_msg.message_id, reply_markup=markup)
    except Exception as e:
        logger.error(f"❌ خطأ في البحث: {e}")
        try:
            bot.edit_message_text(f"❌ حدث خطأ في البحث: {query}", wait_msg.chat.id, wait_msg.message_id)
        except Exception as e2:
            logger.error(f"❌ فشل تعديل رسالة البحث: {e2}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ في البحث: {query}")


def handle_search_input(bot, message, query):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    
    wait_msg = bot.send_message(message.chat.id, "🎯 جاري البحث المتقدم الشامل...")
    
    try:
        results = VideoService.search_videos(query, limit=25)
        total_count = VideoService.get_search_count(query)
        if not results:
            bot.edit_message_text(
                f"❌ لم يتم العثور على نتائج للبحث المتقدم: {query}",
                wait_msg.chat.id, wait_msg.message_id
            )
            return
        
        show_advanced_search_results(bot, wait_msg.chat.id, wait_msg.message_id, results, query, total_count)
    except Exception as e:
        logger.error(f"❌ خطأ في البحث: {e}")
        try:
            bot.edit_message_text(f"❌ حدث خطأ في البحث: {query}", wait_msg.chat.id, wait_msg.message_id)
        except Exception as e2:
            logger.error(f"❌ فشل تعديل رسالة البحث المتقدم: {e2}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ في البحث: {query}")


def show_advanced_search_results(bot, chat_id, message_id, results, query, total_count):
    per_page = 12
    
    text = f"🎯 نتائج البحث المتقدم: {query}\n"
    text += f"📊 العدد الإجمالي: {total_count}\n"
    text += f"📄 عرض أول {min(len(results), per_page)} نتيجة\n\n"
    text += "🔍 البحث الشامل: العنوان، الوصف، اسم الملف، البيانات\n\n"
    
    markup = types.InlineKeyboardMarkup()
    for i, video in enumerate(results[:per_page], 1):
        title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
        title_short = title[:35] + "..." if len(title) > 35 else title
        views = video[3] if video[3] else 0
        text += f"{i}. {title_short}\n   👁️ {views:,}\n\n"
        
        # إضافة زرين: تفاصيل و جلب
        btn_details = types.InlineKeyboardButton(f"📺 {i}. {title[:15]}...", callback_data=f"video_{video[0]}")
        btn_download = types.InlineKeyboardButton("📥 جلب", callback_data=f"download_{video[0]}")
        markup.add(btn_details, btn_download)
    
    if total_count > per_page:
        text += f"📋 للاطلاع على جميع النتائج ({total_count}) استخدم كلمات أكثر تحديداً\n\n"
    
    control_buttons = []
    if total_count > per_page:
        control_buttons.append(types.InlineKeyboardButton("🔍 تحسين البحث", callback_data="search"))
    control_buttons.append(types.InlineKeyboardButton("📚 التصنيفات", callback_data="categories"))
    if control_buttons:
        markup.add(*control_buttons)
    markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
    
    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)


def register_text_handlers(bot):
    bot.message_handler(content_types=['text'])(lambda message: handle_text_message(bot, message))
    logger.info("✅ تم تسجيل معالجات النصوص المحسنة")
