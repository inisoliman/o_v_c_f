"""
معالجات المستخدمين
"""
import logging
from telebot import types
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


def register_user_handlers(bot):
    """تسجيل معالجات المستخدمين"""
    print("✅ تم تسجيل معالجات المستخدمين")
