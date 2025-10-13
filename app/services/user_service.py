"""
خدمات المستخدمين
"""
import logging
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
from app.database.connection import get_db_cursor

logger = logging.getLogger(__name__)


class UserService:
    """خدمة إدارة المستخدمين"""
    
    @staticmethod
    def add_user(user_id: int, username: str, first_name: str, last_name: str = None) -> bool:
        """إضافة/تحديث مستخدم"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO bot_users (user_id, username, first_name, join_date)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name
                """, (user_id, username, first_name, datetime.now()))
                
                return True
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة المستخدم: {e}")
            return False
    
    @staticmethod
    def get_user_favorites(user_id: int, limit: int = 20) -> List[Tuple]:
        """الحصول على مفضلات المستخدم"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT v.id, v.title, v.caption, v.view_count, v.file_name, f.added_date
                    FROM user_favorites f
                    JOIN video_archive v ON f.video_id = v.id
                    WHERE f.user_id = %s
                    ORDER BY f.added_date DESC
                    LIMIT %s
                """, (user_id, limit))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في المفضلات: {e}")
            return []
    
    @staticmethod
    def get_user_history(user_id: int, limit: int = 20) -> List[Tuple]:
        """الحصول على سجل المستخدم"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT v.id, v.title, v.caption, v.view_count, v.file_name, h.last_watched
                    FROM user_history h
                    JOIN video_archive v ON h.video_id = v.id
                    WHERE h.user_id = %s
                    ORDER BY h.last_watched DESC
                    LIMIT %s
                """, (user_id, limit))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في السجل: {e}")
            return []
    
    @staticmethod
    def toggle_favorite(user_id: int, video_id: int) -> bool:
        """إضافة/إزالة من المفضلة"""
        try:
            with get_db_cursor() as cursor:
                # فحص إذا كان في المفضلة
                cursor.execute("SELECT id FROM user_favorites WHERE user_id = %s AND video_id = %s", (user_id, video_id))
                exists = cursor.fetchone()
                
                if exists:
                    # إزالة من المفضلة
                    cursor.execute("DELETE FROM user_favorites WHERE user_id = %s AND video_id = %s", (user_id, video_id))
                    return False  # تم إزالته
                else:
                    # إضافة للمفضلة
                    cursor.execute("""
                        INSERT INTO user_favorites (user_id, video_id, added_date, date_added)
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, video_id, datetime.now(), datetime.now()))
                    return True  # تم إضافته
                    
        except Exception as e:
            logger.error(f"❌ خطأ في المفضلة: {e}")
            return False
    
    @staticmethod
    def is_favorite(user_id: int, video_id: int) -> bool:
        """فحص إذا كان الفيديو في المفضلة"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT id FROM user_favorites WHERE user_id = %s AND video_id = %s", (user_id, video_id))
                return cursor.fetchone() is not None
        except:
            return False
    
    @staticmethod
    def add_to_history(user_id: int, video_id: int):
        """إضافة إلى سجل المشاهدة"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_history (user_id, video_id, last_viewed, last_watched)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, video_id) DO UPDATE SET
                        last_viewed = EXCLUDED.last_viewed,
                        last_watched = EXCLUDED.last_watched
                """, (user_id, video_id, datetime.now(), datetime.now()))
                
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة إلى السجل: {e}")
    
    @staticmethod
    def cleanup_old_history(days: int = 15):
        """حذف سجل المشاهدة القديم"""
        try:
            with get_db_cursor() as cursor:
                cutoff_date = datetime.now() - timedelta(days=days)
                cursor.execute("DELETE FROM user_history WHERE last_watched < %s", (cutoff_date,))
                
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    logger.info(f"🧹 تم حذف {deleted_count} سجل قديم")
                    
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف السجل: {e}")
    
    @staticmethod
    def get_user_stats() -> Dict:
        """إحصائيات المستخدمين"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN join_date >= NOW() - INTERVAL '7 days' THEN 1 END) as new_users_week,
                        COUNT(CASE WHEN join_date >= NOW() - INTERVAL '30 days' THEN 1 END) as new_users_month
                    FROM bot_users
                """)
                
                result = cursor.fetchone()
                return {
                    'total_users': result[0] or 0,
                    'new_users_week': result[1] or 0,
                    'new_users_month': result[2] or 0
                }
        except Exception as e:
            logger.error(f"❌ خطأ في إحصائيات المستخدمين: {e}")
            return {}
    
    @staticmethod
    def get_top_users(limit: int = 10) -> List[Tuple]:
        """الحصول على أكثر المستخدمين نشاطاً"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT u.user_id, u.first_name, u.username, 
                           COUNT(h.id) as history_count,
                           COUNT(f.id) as favorites_count
                    FROM bot_users u
                    LEFT JOIN user_history h ON u.user_id = h.user_id
                    LEFT JOIN user_favorites f ON u.user_id = f.user_id
                    GROUP BY u.user_id, u.first_name, u.username
                    ORDER BY (COUNT(h.id) + COUNT(f.id)) DESC
                    LIMIT %s
                """, (limit,))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في أكثر المستخدمين نشاطاً: {e}")
            return []
