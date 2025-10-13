"""
إعداد قاعدة البيانات وإدارة الاتصالات
"""
import psycopg2
import logging
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def get_db_connection():
    """الاتصال بقاعدة البيانات"""
    try:
        import main
        conn = psycopg2.connect(main.DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
        return None


@contextmanager
def get_db_cursor():
    """Context manager لإدارة الاتصال والcursor"""
    conn = get_db_connection()
    if not conn:
        raise Exception("فشل الاتصال بقاعدة البيانات")
    
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ خطأ في قاعدة البيانات: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def check_database() -> bool:
    """فحص اتصال قاعدة البيانات"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            return True
    except:
        return False


def init_database():
    """تهيئة قاعدة البيانات والتحقق من الجداول"""
    try:
        with get_db_cursor() as cursor:
            # التحقق من وجود الجداول الأساسية
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('video_archive', 'categories', 'bot_users', 'user_history', 'user_favorites')
            """)
            
            existing_tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"✅ جداول موجودة: {existing_tables}")
            
            return len(existing_tables) >= 3
            
    except Exception as e:
        logger.error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
        return False
