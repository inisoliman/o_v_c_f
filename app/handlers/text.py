"""
معالج الرسائل النصية والبحث
"""
import logging
from telebot import types
from app.services.video_service import VideoService
from app.handlers.callbacks import user_states

logger = logging.getLogger(__name__)


def handle_text_message(bot, message):
    """معالج الرسائل النصية العامة"""
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
    
    # بحث سريع
    wait_msg = bot.reply_to(message, "🔍 جاري البحث في الأرشيف...")
    
    results = VideoService.search_videos(query, limit=15)
    
    if not results:
        no_results_text = f"❌ **لم يتم العثور على نتائج للبحث:** {query}\n\n"
        no_results_text += "💡 **اقتراحات:**\n"
        no_results_text += "• جرب كلمات أخرى\n"
        no_results_text += "• البحث بالإنجليزية\n"
        no_results_text += "• تصفح التصنيفات\n"
        no_results_text += "• تصفح الأشهر والأحدث"
        
        markup = types.InlineKeyboardMarkup()
        btn_categories = types.InlineKeyboardButton("📚 التصنيفات", callback_data="categories")
        btn_popular = types.InlineKeyboardButton("🔥 الأشهر", callback_data="popular")
        btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
        markup.add(btn_categories, btn_popular)
        markup.add(btn_back)
        
        bot.edit_message_text(no_results_text, wait_msg.chat.id, wait_msg.message_id, 
                             reply_markup=markup, parse_mode='Markdown')
        return
    
    # تنسيق النتائج
    text = f"🔍 **نتائج البحث عن:** {query}\n"
    text += f"📊 تم العثور على **{len(results)}** نتيجة\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    for i, video in enumerate(results[:10], 1):
        title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
        title = title[:50] + "..." if len(title) > 50 else title
        
        views = video[3] if video[3] else 0
        size = f" | 💾 {video[5]//1024//1024:.0f}MB" if video[5] and video[5] > 0 else ""
        date = f" | 📅 {video[7].strftime('%m/%d')}" if len(video) > 7 and video[7] else ""
        
        text += f"**{i}.** {title}\n   👁️ {views:,}{size}{date}\n\n"
        
        btn = types.InlineKeyboardButton(f"📺 {title[:25]}...", callback_data=f"video_{video[0]}")
        markup.add(btn)
    
    if len(results) > 10:
        text += f"**... و {len(results) - 10} نتيجة أخرى**\n"
    
    btn_more = types.InlineKeyboardButton("🔍 بحث متقدم", callback_data="search")
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_more, btn_back)
    
    bot.edit_message_text(text, wait_msg.chat.id, wait_msg.message_id, 
                         reply_markup=markup, parse_mode='Markdown')


def handle_search_input(bot, message, query):
    """معالج إدخال البحث المتقدم"""
    user_id = message.from_user.id
    
    # إزالة حالة البحث
    if user_id in user_states:
        del user_states[user_id]
    
    # تنفيذ البحث المتقدم
    wait_msg = bot.reply_to(message, "🔍 جاري البحث المتقدم...")
    
    results = VideoService.search_videos(query, limit=20)
    
    if not results:
        bot.edit_message_text(f"❌ لم يتم العثور على نتائج للبحث: **{query}**", 
                             wait_msg.chat.id, wait_msg.message_id, parse_mode='Markdown')
        return
    
    # عرض النتائج مع خيارات متقدمة
    show_search_results(bot, wait_msg.chat.id, wait_msg.message_id, results, query)


def show_search_results(bot, chat_id, message_id, results, query):
    """عرض نتائج البحث مع التحكم"""
    text = f"🎯 **نتائج البحث المتقدم:** {query}\n"
    text += f"📊 العدد: **{len(results)}** نتيجة\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    # أول 8 نتائج
    for i, video in enumerate(results[:8], 1):
        title = video[1] if video[1] else (video[4] if video[4] else f"فيديو {video[0]}")
        title_short = title[:40] + "..." if len(title) > 40 else title
        
        text += f"**{i}.** {title_short}\n"
        
        btn = types.InlineKeyboardButton(f"{i}. {title[:20]}...", callback_data=f"video_{video[0]}")
        
        if i % 2 == 1 and i < len(results[:8]):
            # إضافة زرين في صف واحد
            next_video = results[i] if i < len(results[:8]) else None
            if next_video:
                next_title = next_video[1] if next_video[1] else (next_video[4] if next_video[4] else f"فيديو {next_video[0]}")
                btn2 = types.InlineKeyboardButton(f"{i+1}. {next_title[:20]}...", callback_data=f"video_{next_video[0]}")
                markup.add(btn, btn2)
                text += f"**{i+1}.** {next_title[:40] + '...' if len(next_title) > 40 else next_title}\n"
            else:
                markup.add(btn)
        elif i % 2 == 0:
            # تم إضافته مع السابق
            pass
        else:
            markup.add(btn)
        
        text += "\n"
    
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_back)
    
    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')


def register_text_handlers(bot):
    """تسجيل معالجات النصوص"""
    bot.message_handler(content_types=['text'])(lambda message: handle_text_message(bot, message))
    print("✅ تم تسجيل معالجات النصوص")
