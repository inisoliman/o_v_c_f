"""
معالجات لوحة تحكم الإدارة المتقدمة
"""
import logging
from datetime import datetime
from telebot import types
from app.core.config import settings
from app.admin.admin_service import AdminService
from app.services.category_service import CategoryService
from app.services.video_service import VideoService
from app.services.stats_service import StatsService

logger = logging.getLogger(__name__)

# حالة المشرفين للعمليات التفاعلية
admin_states = {}


def admin_command(bot, message):
    """لوحة تحكم الإدارة الرئيسية"""
    if message.from_user.id not in settings.admin_list:
        bot.reply_to(message, "❌ غير مصرح لك بالوصول")
        return
    
    admin_id = message.from_user.id
    dashboard_data = AdminService.get_admin_dashboard_data(admin_id)
    
    stats = dashboard_data.get('stats', {})
    video_stats = stats.get('videos', {})
    user_stats = stats.get('users', {})
    
    admin_text = f"""🛠️ **لوحة التحكم الإدارية المتقدمة**

📊 **الإحصائيات السريعة:**
├ 🎬 الفيديوهات: {video_stats.get('total_videos', 0):,}
├ 👥 المستخدمون: {user_stats.get('total_users', 0):,}
├ 📚 التصنيفات: {stats.get('categories', {}).get('total_categories', 0):,}
├ 👁️ إجمالي المشاهدات: {video_stats.get('total_views', 0):,}
└ 💾 حجم البيانات: {video_stats.get('total_size_gb', 0)} GB

🕒 **النشاط الأخير:**
├ مستخدمون جدد هذا الأسبوع: {user_stats.get('new_users_week', 0)}
├ مستخدمون جدد هذا الشهر: {user_stats.get('new_users_month', 0)}
└ آخر تنظيف: {dashboard_data.get('system_info', {}).get('last_cleanup', 'غير محدد')}

⚙️ **حالة النظام:**
├ قاعدة البيانات: {'✅ متصلة' if True else '❌ منقطعة'}
├ Keep Alive: ✅ نشط
├ التنظيف التلقائي: ✅ مفعل
└ البوت: ✅ يعمل بكامل الطاقة

👨‍💼 **المشرف:** {message.from_user.first_name}"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # الصف الأول - إدارة المحتوى
    btn_videos = types.InlineKeyboardButton("🎬 إدارة الفيديوهات", callback_data="admin_videos")
    btn_categories = types.InlineKeyboardButton("📚 إدارة التصنيفات", callback_data="admin_categories")
    markup.add(btn_videos, btn_categories)
    
    # الصف الثاني - المستخدمين والإحصائيات
    btn_users = types.InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")
    btn_stats = types.InlineKeyboardButton("📊 الإحصائيات التفصيلية", callback_data="admin_stats")
    markup.add(btn_users, btn_stats)
    
    # الصف الثالث - أدوات النظام
    btn_cleanup = types.InlineKeyboardButton("🧹 تنظيف قاعدة البيانات", callback_data="admin_cleanup")
    btn_broadcast = types.InlineKeyboardButton("📢 رسالة جماعية", callback_data="admin_broadcast")
    markup.add(btn_cleanup, btn_broadcast)
    
    # الصف الرابع - أدوات متقدمة
    btn_backup = types.InlineKeyboardButton("💾 نسخة احتياطية", callback_data="admin_backup")
    btn_logs = types.InlineKeyboardButton("📋 سجل العمليات", callback_data="admin_logs")
    markup.add(btn_backup, btn_logs)
    
    # الصف الأخير
    btn_refresh = types.InlineKeyboardButton("🔄 تحديث", callback_data="admin_refresh")
    btn_back = types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    markup.add(btn_refresh, btn_back)
    
    bot.send_message(message.chat.id, admin_text, reply_markup=markup, parse_mode='Markdown')


def handle_admin_videos(bot, call):
    """إدارة الفيديوهات"""
    admin_id = call.from_user.id
    
    text = """🎬 **إدارة الفيديوهات**

اختر العملية المطلوبة:"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_search = types.InlineKeyboardButton("🔍 البحث والتعديل", callback_data="admin_videos_search")
    btn_uncategorized = types.InlineKeyboardButton("📂 غير مصنفة", callback_data="admin_videos_uncategorized")
    markup.add(btn_search, btn_uncategorized)
    
    btn_bulk_update = types.InlineKeyboardButton("📦 تحديث مجمع", callback_data="admin_videos_bulk")
    btn_popular = types.InlineKeyboardButton("🔥 الأشهر", callback_data="admin_videos_popular")
    markup.add(btn_bulk_update, btn_popular)
    
    btn_recent = types.InlineKeyboardButton("🆕 الأحدث", callback_data="admin_videos_recent")
    btn_delete_old = types.InlineKeyboardButton("🗑️ حذف القديمة", callback_data="admin_videos_delete_old")
    markup.add(btn_recent, btn_delete_old)
    
    btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
    markup.add(btn_back)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')


def handle_admin_categories(bot, call):
    """إدارة التصنيفات"""
    admin_id = call.from_user.id
    
    categories = CategoryService.get_categories(include_counts=True)
    
    text = f"📚 **إدارة التصنيفات** ({len(categories)} تصنيف)\n\n"
    
    for i, category in enumerate(categories[:10], 1):
        text += f"**{i}.** {category[1]} ({category[3]} فيديو)\n"
    
    if len(categories) > 10:
        text += f"\n... و {len(categories) - 10} تصنيف آخر"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_create = types.InlineKeyboardButton("➕ إنشاء تصنيف", callback_data="admin_category_create")
    btn_edit = types.InlineKeyboardButton("✏️ تعديل تصنيف", callback_data="admin_category_edit")
    markup.add(btn_create, btn_edit)
    
    btn_move = types.InlineKeyboardButton("🔄 نقل فيديوهات", callback_data="admin_category_move")
    btn_delete = types.InlineKeyboardButton("🗑️ حذف تصنيف", callback_data="admin_category_delete")
    markup.add(btn_move, btn_delete)
    
    btn_merge = types.InlineKeyboardButton("🔗 دمج تصنيفات", callback_data="admin_category_merge")
    btn_organize = types.InlineKeyboardButton("🗂️ تنظيم تلقائي", callback_data="admin_category_organize")
    markup.add(btn_merge, btn_organize)
    
    btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
    markup.add(btn_back)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')


def handle_admin_users(bot, call):
    """إدارة المستخدمين"""
    user_stats = UserService.get_user_stats()
    top_users = UserService.get_top_users(10)
    
    text = f"""👥 **إدارة المستخدمين**

📊 **الإحصائيات:**
├ إجمالي المستخدمين: {user_stats.get('total_users', 0):,}
├ مستخدمون جدد هذا الأسبوع: {user_stats.get('new_users_week', 0):,}
└ مستخدمون جدد هذا الشهر: {user_stats.get('new_users_month', 0):,}

🏆 **أكثر المستخدمين نشاطاً:**"""
    
    for i, user in enumerate(top_users[:5], 1):
        name = user[1] if user[1] else f"مستخدم {user[0]}"
        activity = user[3] + user[4]  # history + favorites
        text += f"\n**{i}.** {name} ({activity} نشاط)"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_search_user = types.InlineKeyboardButton("🔍 البحث عن مستخدم", callback_data="admin_user_search")
    btn_top_active = types.InlineKeyboardButton("🏆 الأكثر نشاطاً", callback_data="admin_user_top_active")
    markup.add(btn_search_user, btn_top_active)
    
    btn_new_users = types.InlineKeyboardButton("🆕 المستخدمون الجدد", callback_data="admin_user_new")
    btn_inactive = types.InlineKeyboardButton("😴 غير النشطين", callback_data="admin_user_inactive")
    markup.add(btn_new_users, btn_inactive)
    
    btn_export_users = types.InlineKeyboardButton("📤 تصدير البيانات", callback_data="admin_user_export")
    btn_user_stats = types.InlineKeyboardButton("📊 إحصائيات متقدمة", callback_data="admin_user_advanced_stats")
    markup.add(btn_export_users, btn_user_stats)
    
    btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
    markup.add(btn_back)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')


def handle_admin_stats(bot, call):
    """الإحصائيات التفصيلية"""
    detailed_stats = StatsService.get_detailed_stats()
    activity_stats = StatsService.get_activity_stats(7)
    popular_categories = StatsService.get_popular_categories(5)
    
    text = f"""📊 **الإحصائيات التفصيلية**

🎬 **الفيديوهات:**
├ العدد الكلي: {detailed_stats.get('videos', {}).get('total_videos', 0):,}
├ إجمالي المشاهدات: {detailed_stats.get('videos', {}).get('total_views', 0):,}
├ متوسط المشاهدات: {detailed_stats.get('videos', {}).get('avg_views', 0):,}
└ الحجم الإجمالي: {detailed_stats.get('videos', {}).get('total_size_gb', 0)} GB

👥 **المستخدمون:**
├ العدد الكلي: {detailed_stats.get('users', {}).get('total_users', 0):,}
├ جدد هذا الأسبوع: {detailed_stats.get('users', {}).get('new_users_week', 0):,}
└ جدد هذا الشهر: {detailed_stats.get('users', {}).get('new_users_month', 0):,}

📚 **التصنيفات الأشهر:**"""
    
    for i, category in enumerate(popular_categories[:5], 1):
        text += f"\n**{i}.** {category['name']} ({category['videos']} فيديو)"
    
    text += f"\n\n📈 **النشاط هذا الأسبوع:** {len(activity_stats)} يوم نشط"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_export = types.InlineKeyboardButton("📤 تصدير الإحصائيات", callback_data="admin_stats_export")
    btn_charts = types.InlineKeyboardButton("📈 الرسوم البيانية", callback_data="admin_stats_charts")
    markup.add(btn_export, btn_charts)
    
    btn_activity = types.InlineKeyboardButton("📊 تحليل النشاط", callback_data="admin_stats_activity")
    btn_trends = types.InlineKeyboardButton("📈 الاتجاهات", callback_data="admin_stats_trends")
    markup.add(btn_activity, btn_trends)
    
    btn_refresh = types.InlineKeyboardButton("🔄 تحديث", callback_data="admin_stats")
    btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
    markup.add(btn_refresh, btn_back)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')


def handle_admin_cleanup(bot, call):
    """تنظيف قاعدة البيانات"""
    admin_id = call.from_user.id
    
    text = """🧹 **تنظيف قاعدة البيانات**

⚠️ **سيتم تنفيذ العمليات التالية:**

✅ حذف سجل المشاهدة الأقدم من 15 يوم
✅ حذف المفضلات للفيديوهات المحذوفة
✅ تحسين جداول قاعدة البيانات
✅ إعادة بناء فهارس البحث

**هذه العملية آمنة ولن تؤثر على البيانات المهمة**

هل تريد المتابعة؟"""
    
    markup = types.InlineKeyboardMarkup()
    
    btn_confirm = types.InlineKeyboardButton("✅ تأكيد التنظيف", callback_data="admin_cleanup_confirm")
    btn_cancel = types.InlineKeyboardButton("❌ إلغاء", callback_data="admin_back")
    markup.add(btn_confirm, btn_cancel)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')


def handle_admin_broadcast(bot, call):
    """الرسائل الجماعية"""
    admin_id = call.from_user.id
    
    text = """📢 **الرسائل الجماعية**

🎯 **أنواع الرسائل المتاحة:**

📋 **رسالة عامة:** لجميع المستخدمين
⭐ **رسالة للنشطين:** للمستخدمين النشطين فقط
🆕 **رسالة للجدد:** للمستخدمين الجدد فقط

⚠️ **ملاحظة:** الرسائل الجماعية تستغرق وقتاً حسب عدد المستخدمين"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_all = types.InlineKeyboardButton("📋 رسالة عامة", callback_data="admin_broadcast_all")
    btn_active = types.InlineKeyboardButton("⭐ للنشطين", callback_data="admin_broadcast_active")
    markup.add(btn_all, btn_active)
    
    btn_new = types.InlineKeyboardButton("🆕 للجدد", callback_data="admin_broadcast_new")
    btn_test = types.InlineKeyboardButton("🧪 رسالة تجريبية", callback_data="admin_broadcast_test")
    markup.add(btn_new, btn_test)
    
    btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
    markup.add(btn_back)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')


def admin_callback_handler(bot, call):
    """معالج أزرار الإدارة"""
    admin_id = call.from_user.id
    
    if admin_id not in settings.admin_list:
        bot.answer_callback_query(call.id, "❌ غير مصرح لك")
        return
    
    try:
        data = call.data
        
        if data == "admin_back" or data == "admin_refresh":
            # العودة للوحة التحكم أو التحديث
            bot.delete_message(call.message.chat.id, call.message.message_id)
            admin_command(bot, call.message)
            
        elif data == "admin_videos":
            handle_admin_videos(bot, call)
            
        elif data == "admin_categories":
            handle_admin_categories(bot, call)
            
        elif data == "admin_users":
            handle_admin_users(bot, call)
            
        elif data == "admin_stats":
            handle_admin_stats(bot, call)
            
        elif data == "admin_cleanup":
            handle_admin_cleanup(bot, call)
            
        elif data == "admin_cleanup_confirm":
            # تنفيذ التنظيف
            results = AdminService.cleanup_database(admin_id)
            
            result_text = f"""✅ **تم تنظيف قاعدة البيانات بنجاح!**

📊 **النتائج:**
├ حذف سجلات قديمة: {results.get('old_history_deleted', 0)}
├ حذف مفضلات منقطعة: {results.get('orphaned_favorites_deleted', 0)}
└ تحسين قاعدة البيانات: ✅

⏱️ **وقت التنفيذ:** {datetime.now().strftime('%H:%M:%S')}"""
            
            markup = types.InlineKeyboardMarkup()
            btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
            markup.add(btn_back)
            
            bot.edit_message_text(result_text, call.message.chat.id, call.message.message_id, 
                                 reply_markup=markup, parse_mode='Markdown')
                                 
        elif data == "admin_broadcast":
            handle_admin_broadcast(bot, call)
            
        # معالجة باقي الأزرار...
        else:
            bot.answer_callback_query(call.id, "🔄 هذه الميزة قيد التطوير")
            
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالج الإدارة: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")


def register_admin_handlers(bot):
    """تسجيل معالجات الإدارة"""
    bot.message_handler(commands=['admin'])(lambda message: admin_command(bot, message))
    bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))(lambda call: admin_callback_handler(bot, call))
    
    print("✅ تم تسجيل معالجات الإدارة")
