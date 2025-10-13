"""
إعداد قاعدة البيانات وإدارة الجلسات
"""
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    async_sessionmaker, 
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# إنشاء محرك قاعدة البيانات
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    connect_args={
        "server_settings": {
            "jit": "off"
        }
    }
)

# إنشاء مصنع الجلسات
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """الحصول على جلسة قاعدة البيانات"""
    async with async_session_maker() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"خطأ في قاعدة البيانات: {e}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """تهيئة قاعدة البيانات والتحقق من الاتصال"""
    try:
        async with engine.begin() as conn:
            # التحقق من الاتصال
            await conn.execute(text("SELECT 1"))
            logger.info("✅ تم الاتصال بقاعدة البيانات بنجاح")
            
            # التحقق من وجود الجداول الأساسية
            tables_check = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('video_archive', 'categories', 'bot_users')
            """))
            
            existing_tables = [row[0] for row in tables_check.fetchall()]
            
            if len(existing_tables) < 3:
                logger.warning("⚠️ بعض الجداول الأساسية غير موجودة في قاعدة البيانات")
                logger.info("📋 الجداول الموجودة: " + ", ".join(existing_tables))
            else:
                logger.info("✅ جميع الجداول الأساسية موجودة")
                
    except Exception as e:
        logger.error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        raise


async def close_db() -> None:
    """إغلاق اتصالات قاعدة البيانات"""
    await engine.dispose()
    logger.info("✅ تم إغلاق اتصالات قاعدة البيانات")


async def get_db_stats() -> dict:
    """الحصول على إحصائيات قاعدة البيانات"""
    try:
        async with async_session_maker() as session:
            # إحصائيات الفيديوهات
            videos_count = await session.execute(
                text("SELECT COUNT(*) FROM video_archive WHERE is_active = true")
            )
            
            # إحصائيات المستخدمين
            users_count = await session.execute(
                text("SELECT COUNT(*) FROM bot_users WHERE is_active = true")
            )
            
            # إحصائيات التصنيفات
            categories_count = await session.execute(
                text("SELECT COUNT(*) FROM categories WHERE is_active = true")
            )
            
            return {
                "videos": videos_count.scalar() or 0,
                "users": users_count.scalar() or 0,
                "categories": categories_count.scalar() or 0
            }
    except Exception as e:
        logger.error(f"❌ خطأ في الحصول على إحصائيات قاعدة البيانات: {e}")
        return {"videos": 0, "users": 0, "categories": 0}
