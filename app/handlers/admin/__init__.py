"""معالجات الإدارة"""
from telegram.ext import Application, CommandHandler
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def admin_command(update, context):
    user_id = update.effective_user.id
    if user_id not in settings.admin_list:
        await update.message.reply_text("❌ غير مصرح لك بالوصول")
        return
    
    await update.message.reply_text("🛠️ **لوحة التحكم الإدارية**\n\nقريباً ستتوفر جميع أدوات الإدارة المتقدمة", parse_mode="Markdown")

def register_admin_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("admin", admin_command))