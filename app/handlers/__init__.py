"""
تسجيل جميع معالجات البوت
"""
from telegram.ext import Application

from .start import register_start_handlers
from .search import register_search_handlers
from .video_handler import register_video_handlers
from .admin import register_admin_handlers
from .user import register_user_handlers


def register_handlers(app: Application) -> None:
    """تسجيل جميع المعالجات"""
    
    # معالجات البداية والأوامر الأساسية
    register_start_handlers(app)
    
    # معالجات البحث
    register_search_handlers(app)
    
    # معالجات الفيديو
    register_video_handlers(app)
    
    # معالجات الإدارة
    register_admin_handlers(app)
    
    # معالجات المستخدم
    register_user_handlers(app)
    
    print("✅ تم تسجيل جميع معالجات البوت")
