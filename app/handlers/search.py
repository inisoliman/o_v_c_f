"""معالج البحث"""
import logging
from telebot import types
from app.services.video_service import VideoService

logger = logging.getLogger(__name__)



def register_search_handlers(bot):
    """تسجيل معالجات البحث"""
    print("✅ تم تسجيل معالجات البحث")

    
async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str = None) -> None:
    if not query:
        query = update.message.text if update.message else ""
    
    if len(query.strip()) < 2:
        await update.message.reply_text("🔍 يرجى كتابة كلمة بحث أكثر من حرفين")
        return
    
    loading_message = await update.message.reply_text("🔍 جاري البحث...")
    
    try:
        async for session in get_session():
            # البحث في الفيديوهات
            result = await session.execute(text("""
                SELECT id, title, description, view_count, download_count, 
                       file_size, duration, metadata
                FROM video_archive 
                WHERE is_active = true 
                AND (title ILIKE :query OR description ILIKE :query)
                ORDER BY view_count DESC
                LIMIT 10
            """), {"query": f"%{query}%"})
            
            results = result.fetchall()
            
            if not results:
                await loading_message.edit_text(f"❌ لم يتم العثور على نتائج للبحث: **{query}**\n\n💡 جرب استخدام كلمات أخرى", parse_mode="Markdown")
                return
            
            text = f"🔍 **نتائج البحث عن:** {query}\n"
            text += f"📊 تم العثور على {len(results)} نتيجة\n\n"
            
            keyboard = []
            
            for i, video in enumerate(results[:5], 1):
                title = video[1][:50] + "..." if len(video[1]) > 50 else video[1]
                text += f"**{i}.** {title}\n"
                text += f"   👁️ {video[3]} | 📥 {video[4]}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(f"📺 {title[:30]}...", callback_data=f"video_{video[0]}")
                ])
            
            keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")])
            
            await loading_message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            
    except Exception as e:
        logger.error(f"خطأ في البحث: {e}")
        await loading_message.edit_text("❌ حدث خطأ أثناء البحث")

def register_search_handlers(app) -> None:
    pass