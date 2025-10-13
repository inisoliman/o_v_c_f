"""
خدمات التصنيفات
"""
import logging
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from app.database.connection import get_db_cursor

logger = logging.getLogger(__name__)


class CategoryService:
    """خدمة إدارة التصنيفات"""
    
    @staticmethod
    def get_categories(include_counts: bool = True) -> List[Tuple]:
        """الحصول على جميع التصنيفات"""
        try:
            with get_db_cursor() as cursor:
                if include_counts:
                    cursor.execute("""
                        SELECT c.id, c.name, c.description, COUNT(v.id) as video_count
                        FROM categories c
                        LEFT JOIN video_archive v ON c.id = v.category_id
                        GROUP BY c.id, c.name, c.description
                        ORDER BY video_count DESC, c.name
                    """)
                else:
                    cursor.execute("""
                        SELECT id, name, description
                        FROM categories
                        ORDER BY name
                    """)
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على التصنيفات: {e}")
            return []
    
    @staticmethod
    def get_category_by_id(category_id: int) -> Optional[Tuple]:
        """الحصول على تصنيف بالمعرف"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT c.id, c.name, c.description, COUNT(v.id) as video_count
                    FROM categories c
                    LEFT JOIN video_archive v ON c.id = v.category_id
                    WHERE c.id = %s
                    GROUP BY c.id, c.name, c.description
                """, (category_id,))
                
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على التصنيف: {e}")
            return None
    
    @staticmethod
    def create_category(name: str, description: str = None) -> Optional[int]:
        """إنشاء تصنيف جديد"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO categories (name, description, created_at)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (name, description, datetime.now()))
                
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء التصنيف: {e}")
            return None
    
    @staticmethod
    def update_category(category_id: int, name: str = None, description: str = None) -> bool:
        """تحديث تصنيف"""
        try:
            with get_db_cursor() as cursor:
                updates = []
                params = []
                
                if name:
                    updates.append("name = %s")
                    params.append(name)
                
                if description is not None:
                    updates.append("description = %s")
                    params.append(description)
                
                if not updates:
                    return False
                
                params.append(category_id)
                
                cursor.execute(f"""
                    UPDATE categories 
                    SET {', '.join(updates)}
                    WHERE id = %s
                """, params)
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث التصنيف: {e}")
            return False
    
    @staticmethod
    def delete_category(category_id: int) -> bool:
        """حذف تصنيف"""
        try:
            with get_db_cursor() as cursor:
                # فحص إذا كان هناك فيديوهات في هذا التصنيف
                cursor.execute("SELECT COUNT(*) FROM video_archive WHERE category_id = %s", (category_id,))
                video_count = cursor.fetchone()[0]
                
                if video_count > 0:
                    # نقل الفيديوهات لتصنيف "غير مصنف" أو null
                    cursor.execute("UPDATE video_archive SET category_id = NULL WHERE category_id = %s", (category_id,))
                
                # حذف التصنيف
                cursor.execute("DELETE FROM categories WHERE id = %s", (category_id,))
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ خطأ في حذف التصنيف: {e}")
            return False
    
    @staticmethod
    def move_videos_between_categories(from_category_id: int, to_category_id: int) -> int:
        """نقل الفيديوهات بين التصنيفات"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    UPDATE video_archive 
                    SET category_id = %s 
                    WHERE category_id = %s
                """, (to_category_id, from_category_id))
                
                return cursor.rowcount
        except Exception as e:
            logger.error(f"❌ خطأ في نقل الفيديوهات: {e}")
            return 0
    
    @staticmethod
    def get_category_stats() -> Dict:
        """إحصائيات التصنيفات"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT c.id) as total_categories,
                        COUNT(v.id) as total_videos_categorized,
                        (SELECT COUNT(*) FROM video_archive WHERE category_id IS NULL) as uncategorized_videos
                    FROM categories c
                    LEFT JOIN video_archive v ON c.id = v.category_id
                """)
                
                result = cursor.fetchone()
                return {
                    'total_categories': result[0] or 0,
                    'categorized_videos': result[1] or 0,
                    'uncategorized_videos': result[2] or 0
                }
        except Exception as e:
            logger.error(f"❌ خطأ في إحصائيات التصنيفات: {e}")
            return {}
