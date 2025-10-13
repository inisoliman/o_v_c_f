"""
معالجات الفيديو
"""
import logging
from telebot import types
from app.services.video_service import VideoService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


def register_video_handlers(bot):
    """تسجيل معالجات الفيديو"""
    print("✅ تم تسجيل معالجات الفيديو")
