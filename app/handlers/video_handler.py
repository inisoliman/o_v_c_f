"""معالج الفيديوهات"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from sqlalchemy import text
from app.core.database import get_session
from app.core.config import settings

logger = logging.getLogger(__name__)

async def video_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    video_id = int(query.data.replace("video_", ""))
    
    try:
        async for session in get_session():
            result = await session.execute(text("""
                SELECT v.*, c.name as category_name
                FROM video_archive v
                LEFT JOIN categories c ON v.category_id = c.id
                WHERE v.id = :video_id AND v.is_active = true
            """), {"video_id": video_id})
            
            video = result.fetchone()
            if not video:
                await query.edit_message_text("❌ الفيديو غير موجود")
                return
            
            # زيادة عداد المشاهدة
            await session.execute(text("UPDATE video_archive SET view_count = view_count + 1 WHERE id = :id"), {"id": video_id})
            await session.commit()
            
            # تنسيق المعلومات
            text = f"🎬 **{video[3]}**\n\n"  # title
            
            if video[4]:  # description
                desc = video[4][:200] + "..." if len(video[4]) > 200 else video[4]
                text += f"📝 {desc}\n\n"
            
            if video[-1]:  # category_name
                text += f"📚 **التصنيف:** {video[-1]}\n"
            
            # معلومات الملف
            if video[6]:  # file_size
                size_mb = video[6] / (1024 * 1024)
                text += f"💾 **الحجم:** {size_mb:.1f} MB\n"
            
            if video[7]:  # duration
                minutes = video[7] // 60
                seconds = video[7] % 60
                text += f"⏱️ **المدة:** {minutes:02d}:{seconds:02d}\n"
            
            text += f"\n📊 **الإحصائيات:**\n"
            text += f"👁️ المشاهدات: {video[10]:,}\n"  # view_count
            text += f"📥 التحميلات: {video[11]:,}\n"  # download_count
            
            keyboard = [
                [
                    InlineKeyboardButton("📥 تحميل", callback_data=f"download_{video_id}"),
                    InlineKeyboardButton("💖 مفضلة", callback_data=f"toggle_favorite_{video_id}")
                ],
                [
                    InlineKeyboardButton("⭐ تقييم", callback_data=f"rate_{video_id}"),
                    InlineKeyboardButton("📤 مشاركة", callback_data=f"share_{video_id}")
                ],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            
    except Exception as e:
        logger.error(f"خطأ في عرض الفيديو: {e}")
        await query.edit_message_text("❌ حدث خطأ في تحميل الفيديو")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    video_id = int(query.data.replace("download_", ""))
    
    try:
        async for session in get_session():
            result = await session.execute(text("SELECT file_id, title FROM video_archive WHERE id = :id"), {"id": video_id})
            video = result.fetchone()
            
            if not video:
                await query.answer("❌ الفيديو غير متاح", show_alert=True)
                return
            
            # زيادة عداد التحميل
            await session.execute(text("UPDATE video_archive SET download_count = download_count + 1 WHERE id = :id"), {"id": video_id})
            await session.commit()
            
            # إرسال الفيديو
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=video[0],  # file_id
                caption=f"🎬 **{video[1]}**\n📥 من أرشيف الفيديوهات",
                parse_mode="Markdown"
            )
            
            await query.answer("✅ تم إرسال الفيديو", show_alert=True)
            
    except Exception as e:
        logger.error(f"خطأ في التحميل: {e}")
        await query.answer("❌ حدث خطأ أثناء التحميل", show_alert=True)

def register_video_handlers(app) -> None:
    app.add_handler(CallbackQueryHandler(video_callback, pattern="^video_\d+$"))
    app.add_handler(CallbackQueryHandler(download_video, pattern="^download_\d+$"))