"""
خدمات التصنيفات مع دعم التصنيفات الفرعية
"""
import logging
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from app.database.connection import get_db_cursor

logger = logging.getLogger(__name__)


class CategoryService:
    """خدمة إدارة التصنيفات مع دعم التصنيفات الفرعية"""
    
    @staticmethod
    def get_categories(include_counts: bool = True, parent_id: Optional[int] = None, page: int = 1, per_page: int = 20) -> List[Tuple]:
        """الحصول على التصنيفات مع دعم التصنيفات الفرعية والتصفح"""
        try:
            with get_db_cursor() as cursor:
                offset = (page - 1) * per_page
                
                if include_counts:
                    if parent_id is None:
                        # الحصول على التصنيفات الرئيسية فقط
                        cursor.execute("""
                            SELECT c.id, c.name, c.parent_id, c.full_path, COUNT(v.id) as video_count,
                                   COUNT(sub.id) as subcategory_count
                            FROM categories c
                            LEFT JOIN video_archive v ON c.id = v.category_id
                            LEFT JOIN categories sub ON c.id = sub.parent_id
                            WHERE c.parent_id IS NULL
                            GROUP BY c.id, c.name, c.parent_id, c.full_path
                            ORDER BY video_count DESC, c.name
                            LIMIT %s OFFSET %s
                        """, (per_page, offset))
                    else:
                        # الحصول على التصنيفات الفرعية لتصنيف معين
                        cursor.execute("""
                            SELECT c.id, c.name, c.parent_id, c.full_path, COUNT(v.id) as video_count,
                                   COUNT(sub.id) as subcategory_count
                            FROM categories c
                            LEFT JOIN video_archive v ON c.id = v.category_id
                            LEFT JOIN categories sub ON c.id = sub.parent_id
                            WHERE c.parent_id = %s
                            GROUP BY c.id, c.name, c.parent_id, c.full_path
                            ORDER BY video_count DESC, c.name
                            LIMIT %s OFFSET %s
                        """, (parent_id, per_page, offset))
                else:
                    if parent_id is None:
                        cursor.execute("""
                            SELECT id, name, parent_id, full_path
                            FROM categories
                            WHERE parent_id IS NULL
                            ORDER BY name
                            LIMIT %s OFFSET %s
                        """, (per_page, offset))
                    else:
                        cursor.execute("""
                            SELECT id, name, parent_id, full_path
                            FROM categories
                            WHERE parent_id = %s
                            ORDER BY name
                            LIMIT %s OFFSET %s
                        """, (parent_id, per_page, offset))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على التصنيفات: {e}")
            return []
    
    @staticmethod
    def get_category_by_id(category_id: int) -> Optional[Tuple]:
        """الحصول على تصنيف بالمعرف مع معلومات الوالد"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT c.id, c.name, c.parent_id, c.full_path, 
                           COUNT(v.id) as video_count,
                           COUNT(sub.id) as subcategory_count,
                           p.name as parent_name
                    FROM categories c
                    LEFT JOIN video_archive v ON c.id = v.category_id
                    LEFT JOIN categories sub ON c.id = sub.parent_id
                    LEFT JOIN categories p ON c.parent_id = p.id
                    WHERE c.id = %s
                    GROUP BY c.id, c.name, c.parent_id, c.full_path, p.name
                """, (category_id,))
                
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على التصنيف: {e}")
            return None
    
    @staticmethod
    def get_category_breadcrumb(category_id: int) -> List[Tuple]:
        """الحصول على مسار التصنيف الكامل (breadcrumb)"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    WITH RECURSIVE category_path AS (
                        SELECT id, name, parent_id, 1 as level
                        FROM categories
                        WHERE id = %s
                        
                        UNION ALL
                        
                        SELECT c.id, c.name, c.parent_id, cp.level + 1
                        FROM categories c
                        INNER JOIN category_path cp ON c.id = cp.parent_id
                    )
                    SELECT id, name, parent_id, level
                    FROM category_path
                    ORDER BY level DESC
                """, (category_id,))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في مسار التصنيف: {e}")
            return []
    
    @staticmethod
    def get_total_categories_count(parent_id: Optional[int] = None) -> int:
        """الحصول على العدد الإجمالي للتصنيفات"""
        try:
            with get_db_cursor() as cursor:
                if parent_id is None:
                    cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id IS NULL")
                else:
                    cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id = %s", (parent_id,))
                
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"❌ خطأ في عدد التصنيفات: {e}")
            return 0
    
    @staticmethod
    def create_category(name: str, parent_id: Optional[int] = None) -> Optional[int]:
        """إنشاء تصنيف جديد"""
        try:
            with get_db_cursor() as cursor:
                # بناء المسار الكامل
                if parent_id:
                    cursor.execute("SELECT full_path FROM categories WHERE id = %s", (parent_id,))
                    parent_path = cursor.fetchone()[0]
                    full_path = f"{parent_path} > {name}"
                else:
                    full_path = name
                
                cursor.execute("""
                    INSERT INTO categories (name, parent_id, full_path)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (name, parent_id, full_path))
                
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء التصنيف: {e}")
            return None
    
    @staticmethod
    def update_category(category_id: int, name: str = None, parent_id: int = None) -> bool:
        """تحديث تصنيف"""
        try:
            with get_db_cursor() as cursor:
                updates = []
                params = []
                
                if name:
                    updates.append("name = %s")
                    params.append(name)
                
                if parent_id is not None:
                    updates.append("parent_id = %s")
                    params.append(parent_id)
                
                if not updates:
                    return False
                
                params.append(category_id)
                
                cursor.execute(f"""
                    UPDATE categories 
                    SET {', '.join(updates)}
                    WHERE id = %s
                """, params)
                
                # إعادة بناء المسار الكامل إذا تغير الاسم أو الوالد
                if name or parent_id is not None:
                    CategoryService._rebuild_full_path(category_id)
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث التصنيف: {e}")
            return False
    
    @staticmethod
    def _rebuild_full_path(category_id: int):
        """إعادة بناء المسار الكامل لتصنيف ومن يتبعونه"""
        try:
            with get_db_cursor() as cursor:
                # الحصول على معلومات التصنيف
                cursor.execute("SELECT name, parent_id FROM categories WHERE id = %s", (category_id,))
                result = cursor.fetchone()
                if not result:
                    return
                
                name, parent_id = result
                
                # بناء المسار الجديد
                if parent_id:
                    cursor.execute("SELECT full_path FROM categories WHERE id = %s", (parent_id,))
                    parent_path = cursor.fetchone()[0]
                    full_path = f"{parent_path} > {name}"
                else:
                    full_path = name
                
                # تحديث المسار
                cursor.execute("UPDATE categories SET full_path = %s WHERE id = %s", (full_path, category_id))
                
                # إعادة بناء مسارات التصنيفات الفرعية
                cursor.execute("SELECT id FROM categories WHERE parent_id = %s", (category_id,))
                children = cursor.fetchall()
                
                for child in children:
                    CategoryService._rebuild_full_path(child[0])
                    
        except Exception as e:
            logger.error(f"❌ خطأ في إعادة بناء المسار: {e}")
    
    @staticmethod
    def delete_category(category_id: int) -> bool:
        """حذف تصنيف"""
        try:
            with get_db_cursor() as cursor:
                # فحص إذا كان هناك فيديوهات في هذا التصنيف
                cursor.execute("SELECT COUNT(*) FROM video_archive WHERE category_id = %s", (category_id,))
                video_count = cursor.fetchone()[0]
                
                # فحص إذا كان هناك تصنيفات فرعية
                cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id = %s", (category_id,))
                subcategory_count = cursor.fetchone()[0]
                
                if video_count > 0 or subcategory_count > 0:
                    # لا يمكن الحذف
                    return False
                
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
                        COUNT(DISTINCT CASE WHEN c.parent_id IS NULL THEN c.id END) as main_categories,
                        COUNT(DISTINCT CASE WHEN c.parent_id IS NOT NULL THEN c.id END) as subcategories,
                        COUNT(v.id) as total_videos_categorized,
                        (SELECT COUNT(*) FROM video_archive WHERE category_id IS NULL) as uncategorized_videos
                    FROM categories c
                    LEFT JOIN video_archive v ON c.id = v.category_id
                """)
                
                result = cursor.fetchone()
                return {
                    'total_categories': result[0] or 0,
                    'main_categories': result[1] or 0,
                    'subcategories': result[2] or 0,
                    'categorized_videos': result[3] or 0,
                    'uncategorized_videos': result[4] or 0
                }
        except Exception as e:
            logger.error(f"❌ خطأ في إحصائيات التصنيفات: {e}")
            return {}
