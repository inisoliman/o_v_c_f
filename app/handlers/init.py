"""
تسجيل جميع معالجات البوت
"""
from .start import register_start_handlers
from .search import register_search_handlers
from .video import register_video_handlers
from .category import register_category_handlers
from .user import register_user_handlers
from .admin import register_admin_handlers
from .callbacks import register_callback_handlers
from .text import register_text_handlers


def register_all_handlers(bot):
    """تسجيل جميع المعالجات"""
    
    # معالجات البداية والأوامر الأساسية
    register_start_handlers(bot)
    
    # معالجات البحث
    register_search_handlers(bot)
    
    # معالجات الفيديو
    register_video_handlers(bot)
    
    # معالجات التصنيفات
    register_category_handlers(bot)
    
    # معالجات المستخدم
    register_user_handlers(bot)
    
    # معالجات الإدارة
    register_admin_handlers(bot)
    
    # معالجات الأزرار
    register_callback_handlers(bot)
    
    # معالجات النصوص
    register_text_handlers(bot)
    
    print("✅ تم تسجيل جميع معالجات البوت")
