"""
معالج الرسائل النصية والبحث المحسن - مُصحح
"""
import logging
import math
from telebot import types
from app.services.video_service import VideoService
from app.handlers.callbacks import user_states

logger = logging.getLogger(__name__)


def handle_text_message(bot, message):
    """معالج الرسائل النصية العامة مع البحث المحسن"""
    user_id = message.from_user.id
    query = message.text.strip()
    
    # التحقق من حالة المستخدم
    if user_id in user_states:
        state = user_states[user_id]
        if state.get('action') == 'searching':
            # المستخدم في وضع البحث المتقدم
            handle_search_input(bot, message, query)
            return
    
    if len(query) < 2:
        bot.reply_to(message, "🔍 يرجى كتابة كلمة بحث أكثر من حرف واحد")
        return
    
    # بحث سريع محسن
    wait_msg = bot.reply_to(message, "🔍 جاري البحث الذكي في الأرشيف...")
    
    try:
        results = VideoService.search_videos(query, limit=15)
        total_count = VideoService.get_search_count(query)
        
        if not results:
            no_results_text = f"❌ **لم يتم العثور على نتائج للبحث:** {query}\n\n"
            no_results_text += "💡 **اقتراحات للبحث:**\n"
            no_results_text += "• جرب كلمات مختلفة أو مرادفات\n"
            no_results_text += "• ابحث بالإنجليزية أو العربية\n"
            no_results_text += "• استخدم كلمات أقل وأكثر عمومية\n"
            no_results_text += "• تصفح التصنيفات أو الأشهر\n\n"
            no_results_text += "🎯 **البحث يتم في:**\n"
            no_results_text += "• 📺 عنوان الفيديو\n"
            no_results_text += "• 📝 وصف الفيديو (الكابشن)\n"
            no_results_text += "• 📄 اسم الملف\n"
            no_results_text += "• 🏷️ البيانات الوصفية"
            
            markup = types.InlineKeyboardMarkup()
            btn_categories = types.InlineKeyboardButton("📚 التصنيفات", callback_data="categories")
            btn_popular = types.InlineKeyboardButton("🔥 الأشهر", callback_data="popular")
            btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
            markup.add(btn_categories, btn_popular)
            markup.add(btn_back)
            
            bot.edit_message_text(no_results_text, chat_id, message_id, 
                                 reply_markup=markup, parse_mode='Markdown')
            return
        
        # تنسيق النتائج المحسن
        text = f"🔍 **نتائج البحث عن:** {query}\n"
        text += f"📊 تم العثور على **{total_count}** نتيجة"
        if total_count > 15:
            text += f" (عرض أول 15)\n\n"
        else:
            text += "\n\n"
        
        text += "🎯 **البحث تم في:** العنوان، الوصف، اسم الملف، البيانات\n\n"
        
        markup = types.InlineKeyboardMarkup()
        
        for i, video in enumerate(results[:10], 1):
            title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
            title = title[:50] + "..." if len(title) > 50 else title
            
            views = video[3] if video[3] else 0
            
            # عرض معلومات بسيطة (بدون file_size)
            extra_info = ""
            if len(video) > 7 and video[7]:  # upload_date
                try:
                    extra_info += f" | 📅 {video[7].strftime('%m/%d')}"
                except:
                    pass
            
            text += f"**{i}.** {title}\n   👁️ {views:,}{extra_info}\n\n"
            
            btn = types.InlineKeyboardButton(f"📺 {i}. {title[:25]}...", callback_data=f"video_{video[0]}")
            markup.add(btn)
        
        if total_count > 10:
            text += f"**... و {total_count - 10} نتيجة أخرى**\n"
        
        # أزرار إضافية
        buttons_row = []
        if total_count > 15:
            buttons_row.append(types.InlineKeyboardButton("🔍 بحث متقدم", callback_data="search"))
        buttons_row.append(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu"))
        
        if len(buttons_row) > 0:
            markup.add(*buttons_row)
        
        bot.edit_message_text(text, chat_id, message_id, 
                             reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ خطأ في البحث: {e}")
        bot.edit_message_text(f"❌ حدث خطأ في البحث: {query}", chat_id, message_id)


def handle_search_input(bot, message, query):
    """معالج إدخال البحث المتقدم"""
    user_id = message.from_user.id
    
    # إزالة حالة البحث
    if user_id in user_states:
        del user_states[user_id]
    
    # تنفيذ البحث المتقدم
    wait_msg = bot.reply_to(message, "🎯 جاري البحث المتقدم الشامل...")
    
    try:
        results = VideoService.search_videos(query, limit=25)
        total_count = VideoService.get_search_count(query)
        
        if not results:
            bot.edit_message_text(f"❌ لم يتم العثور على نتائج للبحث المتقدم: **{query}**\n\n"
                                 f"🔍 تم البحث في جميع الحقول: العنوان، الوصف، اسم الملف، البيانات الوصفية", 
                                 wait_msg.chat.id, wait_msg.message_id, parse_mode='Markdown')
            return
        
        # عرض النتائج مع خيارات متقدمة
        show_advanced_search_results(bot, wait_msg.chat.id, wait_msg.message_id, results, query, total_count)
        
    except Exception as e:
        logger.error(f"❌ خطأ في البحث: {e}")
        bot.edit_message_text(f"❌ حدث خطأ في البحث: {query}", wait_msg.chat.id, wait_msg.message_id)


def show_advanced_search_results(bot, chat_id, message_id, results, query, total_count):
    """عرض نتائج البحث المتقدم مع التحكم الكامل"""
    per_page = 12
    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
    
    text = f"🎯 **نتائج البحث المتقدم:** {query}\n"
    text += f"📊 العدد الإجمالي: **{total_count}** نتيجة\n"
    text += f"📄 عرض أول {min(len(results), per_page)} نتيجة\n\n"
    text += f"🔍 **البحث الشامل في:** العنوان، الوصف، اسم الملف، البيانات\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    # أول 12 نتيجة
    for i, video in enumerate(results[:per_page], 1):
        title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
        title_short = title[:35] + "..." if len(title) > 35 else title
        
        views = video[3] if video[3] else 0
        extra_info = f"👁️ {views:,}"
        
        # بدون file_size لأنه غير موجود
        
        text += f"**{i}.** {title_short}\n   {extra_info}\n\n"
        
        btn = types.InlineKeyboardButton(f"{i}. {title[:20]}...", callback_data=f"video_{video[0]}")
        
        # إضافة زرين في صف واحد
        if i % 2 == 1 and i < len(results[:per_page]):
            next_video = results[i] if i < len(results[:per_page]) else None
            if next_video:
                next_title = next_video[1] if next_video[1] else (next_video[4] if next_video[4] else f"فيديو {next_video[0]}")
                next_title_short = next_title[:20] + "..." if len(next_title) > 20 else next_title
                btn2 = types.InlineKeyboardButton(f"{i+1}. {next_title_short}", callback_data=f"video_{next_video[0]}")
                markup.add(btn, btn2)
                
                # إضافة معلومات الفيديو الثاني للنص
                next_views = next_video[3] if next_video[3] else 0
                next_extra_info = f"👁️ {next_views:,}"
                
                text += f"**{i+1}.** {next_title[:35] + '...' if len(next_title) > 35 else next_title}\n   {next_extra_info}\n\n"
            else:
                markup.add(btn)
        elif i % 2 == 0:
            # تم إضافته مع السابق
            pass
        else:
            markup.add(btn)
    
    # معلومات إضافية
    if total_count > per_page:
        text += f"📋 **للاطلاع على جميع النتائج البالغة {total_count} نتيجة، استخدم كلمات بحث أكثر تحديداً**\n\n"
    
    # أزرار التحكم
    control_buttons = []
    if total_count > per_page:
        control_buttons.append(types.InlineKeyboardButton("🔍 تحسين البحث", callback_data="search"))
    control_buttons.append(types.InlineKeyboardButton("📚 التصنيفات", callback_data="categories"))
    
    if len(control_buttons) > 0:
        markup.add(*control_buttons)
    
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_back)
    
    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')


def register_text_handlers(bot):
    """تسجيل معالجات النصوص المحسنة"""
    try:
        bot.message_handler(content_types=['text'])(lambda message: handle_text_message(bot, message))
        logger.info("✅ تم تسجيل معالجات النصوص المحسنة")
    except Exception as e:
        logger.error(f"❌ خطأ في تسجيل معالجات النصوص: {e}")