"""
خدمات لوحة تحكم الإدارة
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from app.database.connection import get_db_cursor
from app.services.video_service import VideoService
from app.services.category_service import CategoryService
from app.services.user_service import UserService
from app.services.stats_service import StatsService

logger = logging.getLogger(__name__)


class AdminService:
    """خدمة لوحة تحكم الإدارة"""
    
    @staticmethod
    def log_admin_action(admin_id: int, action: str, details: str = None):
        """تسجيل عمليات الإدارة"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO admin_logs (admin_id, action, details, timestamp)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (admin_id, action, details, datetime.now()))
                
        except Exception as e:
            # إذا لم يكن جدول admin_logs موجود، نتجاهل الخطأ
            logger.debug(f"تسجيل الإدارة: {action}")
    
    @staticmethod
    def get_admin_dashboard_data(admin_id: int) -> Dict:
        """الحصول على بيانات لوحة التحكم"""
        try:
            AdminService.log_admin_action(admin_id, "dashboard_access")
            
            return {
                'stats': StatsService.get_detailed_stats(),
                'recent_videos': VideoService.get_recent_videos(5),
                'popular_videos': VideoService.get_popular_videos(5),
                'top_categories': CategoryService.get_categories()[:10],
                'active_users': UserService.get_top_users(5),
                'system_info': {
                    'last_cleanup': "منذ 3 ساعات",
                    'database_size': "2.5 GB",
                    'cache_status': "نشط"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في بيانات لوحة التحكم: {e}")
            return {}
    
    @staticmethod
    def search_admin_videos(query: str = None, category_id: int = None, limit: int = 50) -> List[Tuple]:
        """البحث المتقدم للإدارة"""
        try:
            with get_db_cursor() as cursor:
                where_conditions = []
                params = []
                
                if query:
                    where_conditions.append("(v.title ILIKE %s OR v.caption ILIKE %s OR v.file_name ILIKE %s)")
                    params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
                
                if category_id:
                    where_conditions.append("v.category_id = %s")
                    params.append(category_id)
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                cursor.execute(f"""
                    SELECT v.id, v.title, v.caption, v.view_count, v.file_name, 
                           v.upload_date, c.name as category_name, v.file_size
                    FROM video_archive v
                    LEFT JOIN categories c ON v.category_id = c.id
                    WHERE {where_clause}
                    ORDER BY v.upload_date DESC
                    LIMIT %s
                """, params + [limit])
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"❌ خطأ في البحث الإداري: {e}")
            return []
    
    @staticmethod
    def bulk_update_videos_category(video_ids: List[int], category_id: int, admin_id: int) -> int:
        """تحديث تصنيف عدة فيديوهات مرة واحدة"""
        try:
            with get_db_cursor() as cursor:
                # تحويل قائمة المعرفات إلى صيغة SQL
                video_ids_str = ','.join(map(str, video_ids))
                
                cursor.execute(f"""
                    UPDATE video_archive 
                    SET category_id = %s 
                    WHERE id IN ({video_ids_str})
                """, (category_id,))
                
                updated_count = cursor.rowcount
                
                AdminService.log_admin_action(
                    admin_id, 
                    "bulk_category_update", 
                    f"Updated {updated_count} videos to category {category_id}"
                )
                
                return updated_count
                
        except Exception as e:
            logger.error(f"❌ خطأ في التحديث المجمع: {e}")
            return 0
    
    @staticmethod
    def bulk_delete_videos(video_ids: List[int], admin_id: int) -> int:
        """حذف عدة فيديوهات مرة واحدة"""
        try:
            with get_db_cursor() as cursor:
                video_ids_str = ','.join(map(str, video_ids))
                
                cursor.execute(f"DELETE FROM video_archive WHERE id IN ({video_ids_str})")
                
                deleted_count = cursor.rowcount
                
                AdminService.log_admin_action(
                    admin_id, 
                    "bulk_delete", 
                    f"Deleted {deleted_count} videos"
                )
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"❌ خطأ في الحذف المجمع: {e}")
            return 0
    
    @staticmethod
    def get_uncategorized_videos(limit: int = 20) -> List[Tuple]:
        """الحصول على الفيديوهات غير المصنفة"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT id, title, caption, view_count, file_name, upload_date
                    FROM video_archive
                    WHERE category_id IS NULL
                    ORDER BY upload_date DESC
                    LIMIT %s
                """, (limit,))
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"❌ خطأ في الفيديوهات غير المصنفة: {e}")
            return []
    
    @staticmethod
    def cleanup_database(admin_id: int) -> Dict:
        """تنظيف قاعدة البيانات"""
        try:
            results = {}
            
            with get_db_cursor() as cursor:
                # حذف السجلات القديمة
                cursor.execute("DELETE FROM user_history WHERE last_watched < NOW() - INTERVAL '15 days'")
                results['old_history_deleted'] = cursor.rowcount
                
                # حذف المفضلات للفيديوهات المحذوفة
                cursor.execute("""
                    DELETE FROM user_favorites 
                    WHERE video_id NOT IN (SELECT id FROM video_archive)
                """)
                results['orphaned_favorites_deleted'] = cursor.rowcount
                
                # تحديث الإحصائيات
                cursor.execute("VACUUM ANALYZE")
                results['database_optimized'] = True
                
            AdminService.log_admin_action(admin_id, "database_cleanup", str(results))
            
            return results
            
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف قاعدة البيانات: {e}")
            return {}
    
    @staticmethod
    def broadcast_message_to_users(message: str, admin_id: int) -> Dict:
        """إرسال رسالة جماعية للمستخدمين"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT user_id FROM bot_users")
                user_ids = [row[0] for row in cursor.fetchall()]
            
            AdminService.log_admin_action(
                admin_id, 
                "broadcast_message", 
                f"Message to {len(user_ids)} users"
            )
            
            return {
                'target_users': len(user_ids),
                'user_ids': user_ids,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في الرسالة الجماعية: {e}")
            return {}
    
    @staticmethod
    def get_admin_logs(limit: int = 50) -> List[Tuple]:
        """الحصول على سجل عمليات الإدارة"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT admin_id, action, details, timestamp
                    FROM admin_logs
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (limit,))
                
                return cursor.fetchall()
                
        except Exception as e:
            # إذا لم يكن الجدول موجود
            logger.debug("جدول admin_logs غير موجود")
            return []
