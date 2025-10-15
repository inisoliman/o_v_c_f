"""
خدمات التصنيفات مع دعم التصنيفات الفرعية
"""
import logging
from typing import List, Optional, Tuple
from app.database.connection import get_db_cursor

logger = logging.getLogger(__name__)


class CategoryService:
    """خدمة إدارة التصنيفات"""
    
    @staticmethod
    def get_categories(include_counts: bool = False, page: int = 1, per_page: int = 20, parent_id: Optional[int] = None) -> List[Tuple]:
        """الحصول على قائمة التصنيفات مع إمكانية التصفح والتصنيفات الفرعية"""
        try:
            with get_db_cursor() as cursor:
                offset = (page - 1) * per_page
                
                if include_counts:
                    if parent_id is not None:
                        # جلب التصنيفات الفرعية لتصنيف معين مع العدادات
                        cursor.execute("""
                            SELECT c.id, c.name, c.parent_id, c.full_path, 
                                   COUNT(v.id) as video_count
                            FROM categories c
                            LEFT JOIN video_archive v ON c.id = v.category_id
                            WHERE c.parent_id = %s
                            GROUP BY c.id, c.name, c.parent_id, c.full_path
                            ORDER BY c.name
                            LIMIT %s OFFSET %s
                        """, (parent_id, per_page, offset))
                    else:
                        # جلب التصنيفات الرئيسية مع العدادات
                        cursor.execute("""
                            SELECT c.id, c.name, c.parent_id, c.full_path, 
                                   COUNT(v.id) as video_count
                            FROM categories c
                            LEFT JOIN video_archive v ON c.id = v.category_id
                            WHERE c.parent_id IS NULL OR c.parent_id = 0
                            GROUP BY c.id, c.name, c.parent_id, c.full_path
                            ORDER BY c.name
                            LIMIT %s OFFSET %s
                        """, (per_page, offset))
                else:
                    if parent_id is not None:
                        cursor.execute("""
                            SELECT id, name, parent_id, full_path
                            FROM categories 
                            WHERE parent_id = %s
                            ORDER BY name
                            LIMIT %s OFFSET %s
                        """, (parent_id, per_page, offset))
                    else:
                        cursor.execute("""
                            SELECT id, name, parent_id, full_path
                            FROM categories 
                            WHERE parent_id IS NULL OR parent_id = 0
                            ORDER BY name
                            LIMIT %s OFFSET %s
                        """, (per_page, offset))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على التصنيفات: {e}")
            return []
    
    @staticmethod
    def get_subcategories(parent_id: int) -> List[Tuple]:
        """الحصول على التصنيفات الفرعية لتصنيف معين"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT c.id, c.name, c.parent_id, c.full_path, 
                           COUNT(v.id) as video_count
                    FROM categories c
                    LEFT JOIN video_archive v ON c.id = v.category_id
                    WHERE c.parent_id = %s
                    GROUP BY c.id, c.name, c.parent_id, c.full_path
                    ORDER BY c.name
                """, (parent_id,))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في جلب التصنيفات الفرعية: {e}")
            return []
    
    @staticmethod
    def get_category_by_id(category_id: int) -> Optional[Tuple]:
        """الحصول على تصنيف بالمعرف"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, parent_id, full_path
                    FROM categories 
                    WHERE id = %s
                """, (category_id,))
                
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على التصنيف: {e}")
            return None
    
    @staticmethod
    def get_total_categories_count(parent_id: Optional[int] = None) -> int:
        """الحصول على إجمالي عدد التصنيفات"""
        try:
            with get_db_cursor() as cursor:
                if parent_id is not None:
                    cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id = %s", (parent_id,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id IS NULL OR parent_id = 0")
                
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"❌ خطأ في عدد التصنيفات: {e}")
            return 0
