"""
إعدادات التطبيق الرئيسية
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """إعدادات التطبيق"""
    
    # Bot Configuration
    BOT_TOKEN: str = Field(..., description="رمز البوت من BotFather")
    ADMIN_IDS: str = Field(..., description="معرفات المشرفين مفصولة بفاصلة")
    BOT_USERNAME: Optional[str] = Field(None, description="اسم المستخدم للبوت")
    SOURCE_CHAT_ID: Optional[int] = Field(None, description="معرف المجموعة المصدر")
    
    # Database
    DATABASE_URL: str = Field(..., description="رابط قاعدة البيانات")
    
    # Redis (Optional)
    REDIS_URL: Optional[str] = Field(None, description="رابط Redis للتخزين المؤقت")
    
    # App Settings
    DEBUG: bool = Field(False, description="وضع التطوير")
    ENVIRONMENT: str = Field("production", description="بيئة التشغيل")
    LOG_LEVEL: str = Field("INFO", description="مستوى التسجيل")
    
    # File Upload
    MAX_FILE_SIZE_MB: int = Field(2000, description="أقصى حجم ملف بالميجابايت")
    ALLOWED_VIDEO_FORMATS: str = Field(
        "mp4,mkv,avi,mov,wmv,flv,webm,m4v",
        description="صيغ الفيديو المسموحة"
    )
    
    # Features
    AUTO_DELETE_HISTORY_DAYS: int = Field(15, description="مدة حفظ التاريخ بالأيام")
    MAX_FAVORITES_PER_USER: int = Field(1000, description="أقصى عدد مفضلات للمستخدم")
    ENABLE_NOTIFICATIONS: bool = Field(True, description="تفعيل الإشعارات")
    
    # Security
    SECRET_KEY: str = Field(..., description="المفتاح السري للتطبيق")
    RATE_LIMIT_REQUESTS: int = Field(30, description="عدد الطلبات المسموحة")
    RATE_LIMIT_WINDOW: int = Field(60, description="نافزة الوقت للطلبات بالثواني")
    
    # External Services
    TMDB_API_KEY: Optional[str] = Field(None, description="مفتاح TMDB للمعلومات")
    
    @property
    def admin_list(self) -> List[int]:
        """قائمة معرفات المشرفين"""
        try:
            return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]
        except:
            return []
    
    @property
    def allowed_formats(self) -> List[str]:
        """قائمة الصيغ المسموحة"""
        return [x.strip().lower() for x in self.ALLOWED_VIDEO_FORMATS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# إنشاء كائن الإعدادات
settings = Settings()
