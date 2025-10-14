"""
خدمات الفيديوهات مع بحث محسن - إصدار مُصحح
"""
import logging
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from app.database.connection import get_db_cursor

logger = logging.getLogger(__name__)


class VideoService:
    """خدمة إدارة الفيديوهات مع بحث محسن"""
    
    @staticmethod
    def search_videos(query: str, category_id: Optional[int] = None, limit: int = 20, page: int = 1) -> List[Tuple]:
        """البحث المحسن في الفيديوهات - يبحث في العنوان والوصف واسم الملف"""
        try:
            with get_db_cursor() as cursor:
                offset = (page - 1) * limit
                
                # بحث شامل في جميع الحقول المهمة (بدون file_size)
                where_clause = """
                (
                    title ILIKE %s OR 
                    caption ILIKE %s OR 
                    file_name ILIKE %s OR
                    metadata::text ILIKE %s
                )
                """
                params = [f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"]
                
                if category_id:
                    where_clause += " AND category_id = %s"
                    params.append(category_id)
                
                cursor.execute(f"""
                    SELECT id, title, caption, view_count, file_name, 
                           category_id, upload_date, file_id, message_id
                    FROM video_archive 
                    WHERE {where_clause}
                    ORDER BY 
                        CASE 
                            WHEN title ILIKE %s THEN 1
                            WHEN caption ILIKE %s THEN 2
                            WHEN file_name ILIKE %s THEN 3
                            ELSE 4
                        END,
                        view_count DESC, 
                        upload_date DESC
                    LIMIT %s OFFSET %s
                """, params + [f"%{query}%", f"%{query}%", f"%{query}%", limit, offset])
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في البحث: {e}")
            return []
    
    @staticmethod
    def get_search_count(query: str, category_id: Optional[int] = None) -> int:
        """الحصول على عدد نتائج البحث الإجمالي"""
        try:
            with get_db_cursor() as cursor:
                where_clause = """
                (
                    title ILIKE %s OR 
                    caption ILIKE %s OR 
                    file_name ILIKE %s OR
                    metadata::text ILIKE %s
                )
                """
                params = [f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"]
                
                if category_id:
                    where_clause += " AND category_id = %s"
                    params.append(category_id)
                
                cursor.execute(f"SELECT COUNT(*) FROM video_archive WHERE {where_clause}", params)
                
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"❌ خطأ في عدد البحث: {e}")
            return 0
    
    @staticmethod
    def get_video_by_id(video_id: int) -> Optional[Tuple]:
        """الحصول على فيديو بالمعرف"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT v.id, v.message_id, v.caption, v.chat_id, v.file_name, v.file_id, 
                           v.category_id, v.metadata, v.view_count, v.title, v.grouping_key, 
                           v.upload_date, c.name as category_name, c.full_path as category_path
                    FROM video_archive v
                    LEFT JOIN categories c ON v.category_id = c.id
                    WHERE v.id = %s
                """, (video_id,))
                
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على الفيديو: {e}")
            return None
    
    @staticmethod
    def get_videos_by_category(category_id: int, limit: int = 20, page: int = 1) -> List[Tuple]:
        """الحصول على فيديوهات تصنيف معين مع التصفح"""
        try:
            with get_db_cursor() as cursor:
                offset = (page - 1) * limit
                
                cursor.execute("""
                    SELECT id, title, caption, view_count, file_name, upload_date, file_id
                    FROM video_archive 
                    WHERE category_id = %s
                    ORDER BY view_count DESC, upload_date DESC
                    LIMIT %s OFFSET %s
                """, (category_id, limit, offset))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في فيديوهات التصنيف: {e}")
            return []
    
    @staticmethod
    def get_category_videos_count(category_id: int) -> int:
        """الحصول على عدد فيديوهات التصنيف"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM video_archive WHERE category_id = %s", (category_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"❌ خطأ في عدد فيديوهات التصنيف: {e}")
            return 0
    
    @staticmethod
    def update_view_count(video_id: int) -> bool:
        """زيادة عداد المشاهدة"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "UPDATE video_archive SET view_count = view_count + 1 WHERE id = %s", 
                    (video_id,)
                )
                return True
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث عداد المشاهدة: {e}")
            return False
    
    @staticmethod
    def get_popular_videos(limit: int = 10) -> List[Tuple]:
        """الحصول على أشهر الفيديوهات"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT id, title, caption, view_count, file_name, upload_date
                    FROM video_archive 
                    WHERE view_count > 0
                    ORDER BY view_count DESC, upload_date DESC
                    LIMIT %s
                """, (limit,))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في الفيديوهات الشائعة: {e}")
            return []
    
    @staticmethod
    def get_recent_videos(limit: int = 10) -> List[Tuple]:
        """الحصول على أحدث الفيديوهات"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT id, title, caption, view_count, file_name, upload_date
                    FROM video_archive 
                    ORDER BY upload_date DESC
                    LIMIT %s
                """, (limit,))
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ خطأ في الفيديوهات الحديثة: {e}")
            return []
    
    @staticmethod
    def delete_video(video_id: int) -> bool:
        """حذف فيديو (للمشرفين)"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("DELETE FROM video_archive WHERE id = %s", (video_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ خطأ في حذف الفيديو: {e}")
            return False
    
    @staticmethod
    def update_video_category(video_id: int, category_id: int) -> bool:
        """تحديث تصنيف الفيديو"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "UPDATE video_archive SET category_id = %s WHERE id = %s", 
                    (category_id, video_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث التصنيف: {e}")
            return False
    
    @staticmethod
    def get_video_stats() -> Dict:
        """إحصائيات الفيديوهات التفصيلية - بدون file_size"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_videos,
                        SUM(view_count) as total_views,
                        AVG(view_count) as avg_views,
                        COUNT(DISTINCT category_id) as categories_used
                    FROM video_archive
                """)
                
                result = cursor.fetchone()
                return {
                    'total_videos': result[0] or 0,
                    'total_views': result[1] or 0,
                    'avg_views': round(result[2] or 0, 2),
                    'categories_used': result[3] or 0
                }
        except Exception as e:
            logger.error(f"❌ خطأ في إحصائيات الفيديو: {e}")
            return {}
    
    @staticmethod
    def add_video(message_id: int, caption: str, chat_id: int, file_name: str, 
                  file_id: str, category_id: int, metadata: dict, title: str, 
                  grouping_key: str) -> bool:
        """إضافة فيديو جديد للأرشيف"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO video_archive 
                    (message_id, caption, chat_id, file_name, file_id, category_id, 
                     metadata, title, grouping_key, upload_date, view_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 0)
                """, (message_id, caption, chat_id, file_name, file_id, category_id, 
                     metadata, title, grouping_key))
                return True
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة الفيديو: {e}")
            return False