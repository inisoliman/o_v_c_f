"""
معالجات التصنيفات
"""
import logging
from telebot import types
from app.services.category_service import CategoryService

logger = logging.getLogger(__name__)


def register_category_handlers(bot):
    """تسجيل معالجات التصنيفات"""
    print("✅ تم تسجيل معالجات التصنيفات")
