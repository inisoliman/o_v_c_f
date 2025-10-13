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
    
    # App Settings
    DEBUG: bool = Field(False, description="وضع التطوير")
    ENVIRONMENT: str = Field("production", description="بيئة التشغيل")
    LOG_LEVEL: str = Field("INFO", description="مستوى التسجيل")
    
    # Features
    AUTO_DELETE_HISTORY_DAYS: int = Field(15, description="مدة حفظ التاريخ بالأيام")
    MAX_FAVORITES_PER_USER: int = Field(1000, description="أقصى عدد مفضلات")
    ENABLE_NOTIFICATIONS: bool = Field(True, description="تفعيل الإشعارات")
    
    # Admin Features
    ADMIN_LOG_CHANNEL: Optional[int] = Field(None, description="قناة تسجيل أنشطة الإدارة")
    BACKUP_INTERVAL_HOURS: int = Field(24, description="فترة النسخ الاحتياطي بالساعات")
    
    # Security
    SECRET_KEY: str = Field(..., description="المفتاح السري للتطبيق")
    RATE_LIMIT_REQUESTS: int = Field(30, description="عدد الطلبات المسموحة")
    
    @property
    def admin_list(self) -> List[int]:
        """قائمة معرفات المشرفين"""
        try:
            return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]
        except:
            return []
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# إنشاء كائن الإعدادات
settings = Settings()
