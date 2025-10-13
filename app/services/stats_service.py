"""
خدمات الإحصائيات
"""
import logging
from typing import Dict, List
from datetime import datetime
from app.database.connection import get_db_cursor

logger = logging.getLogger(__name__)


class StatsService:
    """خدمة الإحصائيات الشاملة"""
    
    @staticmethod
    def get_general_stats() -> Dict:
        """الإحصائيات العامة للبوت"""
        try:
            with get_db_cursor() as cursor:
                # إحصائيات أساسية
                cursor.execute("""
                    SELECT 
                        (SELECT COUNT(*) FROM video_archive) as videos,
                        (SELECT COUNT(*) FROM bot_users) as users,
                        (SELECT COUNT(*) FROM categories) as categories,
                        (SELECT COUNT(*) FROM user_favorites) as favorites,
                        (SELECT SUM(view_count) FROM video_archive) as total_views
                """)
                
                result = cursor.fetchone()
                
                return {
                    'videos': result[0] or 0,
                    'users': result[1] or 0,
                    'categories': result[2] or 0,
                    'favorites': result[3] or 0,
                    'total_views': result[4] or 0,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
        except Exception as e:
            logger.error(f"❌ خطأ في الإحصائيات العامة: {e}")
            return {
                'videos': 0,
                'users': 0,
                'categories': 0,
                'favorites': 0,
                'total_views': 0,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
    
    @staticmethod
    def get_detailed_stats() -> Dict:
        """الإحصائيات التفصيلية للإدارة"""
        try:
            # استيراد الخدمات محلياً لتجنب circular imports
            from app.services.video_service import VideoService
            from app.services.user_service import UserService
            from app.services.category_service import CategoryService
            
            video_stats = VideoService.get_video_stats()
            user_stats = UserService.get_user_stats()
            category_stats = CategoryService.get_category_stats()
            
            return {
                'videos': video_stats,
                'users': user_stats,
                'categories': category_stats,
                'system': {
                    'last_updated': datetime.now().isoformat(),
                    'uptime_hours': 24,  # يمكن حسابها من وقت بدء التشغيل
                    'database_status': 'connected'
                }
            }
        except Exception as e:
            logger.error(f"❌ خطأ في الإحصائيات التفصيلية: {e}")
            return {
                'videos': {},
                'users': {},
                'categories': {},
                'system': {
                    'last_updated': datetime.now().isoformat(),
                    'uptime_hours': 0,
                    'database_status': 'error'
                }
            }
    
    @staticmethod
    def get_activity_stats(days: int = 7) -> Dict:
        """إحصائيات النشاط لعدد معين من الأيام"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        DATE(last_watched) as activity_date,
                        COUNT(DISTINCT user_id) as active_users,
                        COUNT(*) as total_activities
                    FROM user_history
                    WHERE last_watched >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE(last_watched)
                    ORDER BY activity_date DESC
                """, (days,))
                
                results = cursor.fetchall()
                
                activity_data = {}
                for result in results:
                    date_str = result[0].strftime('%Y-%m-%d')
                    activity_data[date_str] = {
                        'active_users': result[1],
                        'activities': result[2]
                    }
                
                return activity_data
                
        except Exception as e:
            logger.error(f"❌ خطأ في إحصائيات النشاط: {e}")
            return {}
    
    @staticmethod
    def get_popular_categories(limit: int = 10) -> List[Dict]:
        """التصنيفات الأكثر شعبية"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT c.name, COUNT(v.id) as video_count, SUM(v.view_count) as total_views
                    FROM categories c
                    LEFT JOIN video_archive v ON c.id = v.category_id
                    GROUP BY c.id, c.name
                    HAVING COUNT(v.id) > 0
                    ORDER BY total_views DESC, video_count DESC
                    LIMIT %s
                """, (limit,))
                
                return [
                    {
                        'name': result[0],
                        'videos': result[1],
                        'views': result[2] or 0
                    }
                    for result in cursor.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"❌ خطأ في التصنيفات الشعبية: {e}")
            return []
    
    @staticmethod
    def export_stats() -> Dict:
        """تصدير جميع الإحصائيات للنسخ الاحتياطي"""
        try:
            return {
                'general': StatsService.get_general_stats(),
                'detailed': StatsService.get_detailed_stats(),
                'activity': StatsService.get_activity_stats(30),
                'popular_categories': StatsService.get_popular_categories(20),
                'export_timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ خطأ في تصدير الإحصائيات: {e}")
            return {
                'general': {},
                'detailed': {},
                'activity': {},
                'popular_categories': [],
                'export_timestamp': datetime.now().isoformat()
            }
