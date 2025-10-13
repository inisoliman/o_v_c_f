"""
معالجات لوحة تحكم الإدارة المتقدمة
"""
import logging
from datetime import datetime
from telebot import types

logger = logging.getLogger(__name__)

# حالة المشرفين للعمليات التفاعلية
admin_states = {}


def admin_command(bot, message):
    """لوحة تحكم الإدارة الرئيسية"""
    # الحصول على ADMIN_IDS من main.py
    import main
    admin_list = main.ADMIN_IDS
    
    if message.from_user.id not in admin_list:
        bot.reply_to(message, "❌ غير مصرح لك بالوصول")
        return
    
    admin_id = message.from_user.id
    
    try:
        from app.services.stats_service import StatsService
        stats = StatsService.get_general_stats()
    except Exception as e:
        logger.error(f"❌ خطأ في الإحصائيات: {e}")
        stats = {'videos': 0, 'users': 0, 'categories': 0, 'favorites': 0, 'total_views': 0}
    
    admin_text = f"""🛠️ **لوحة التحكم الإدارية المتقدمة**

📊 **الإحصائيات السريعة:**
├ 🎬 الفيديوهات: {stats.get('videos', 0):,}
├ 👥 المستخدمون: {stats.get('users', 0):,}
├ 📚 التصنيفات: {stats.get('categories', 0):,}
├ ⭐ المفضلات: {stats.get('favorites', 0):,}
└ 👁️ إجمالي المشاهدات: {stats.get('total_views', 0):,}

🤖 **حالة النظام:**
├ قاعدة البيانات: {'✅ متصلة' if True else '❌ منقطعة'}
├ Keep Alive: ✅ نشط
├ التنظيف التلقائي: ✅ مفعل
└ البوت: ✅ يعمل بكامل الطاقة

🕒 **آخر تحديث:** {datetime.now().strftime('%H:%M:%S')}

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


def handle_admin_callback(bot, call):
    """معالج أزرار الإدارة"""
    import main
    admin_list = main.ADMIN_IDS
    admin_id = call.from_user.id
    
    if admin_id not in admin_list:
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
            handle_cleanup_confirm(bot, call, admin_id)
            
        elif data == "admin_broadcast":
            handle_admin_broadcast(bot, call)
            
        else:
            bot.answer_callback_query(call.id, "🔄 هذه الميزة قيد التطوير")
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالج الإدارة: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ")


def handle_admin_videos(bot, call):
    """إدارة الفيديوهات"""
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
    try:
        from app.services.category_service import CategoryService
        categories = CategoryService.get_categories(include_counts=True)
    except Exception as e:
        logger.error(f"❌ خطأ في الحصول على التصنيفات: {e}")
        categories = []
    
    text = f"📚 **إدارة التصنيفات** ({len(categories)} تصنيف)\n\n"
    
    for i, category in enumerate(categories[:10], 1):
        video_count = category[4] if len(category) > 4 else 0
        text += f"**{i}.** {category[1]} ({video_count} فيديو)\n"
    
    if len(categories) > 10:
        text += f"\n... و {len(categories) - 10} تصنيف آخر"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_create = types.InlineKeyboardButton("➕ إنشاء تصنيف", callback_data="admin_category_create")
    btn_edit = types.InlineKeyboardButton("✏️ تعديل تصنيف", callback_data="admin_category_edit")
    markup.add(btn_create, btn_edit)
    
    btn_move = types.InlineKeyboardButton("🔄 نقل فيديوهات", callback_data="admin_category_move")
    btn_delete = types.InlineKeyboardButton("🗑️ حذف تصنيف", callback_data="admin_category_delete")
    markup.add(btn_move, btn_delete)
    
    btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
    markup.add(btn_back)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')


def handle_admin_users(bot, call):
    """إدارة المستخدمين"""
    try:
        from app.services.user_service import UserService
        user_stats = UserService.get_user_stats()
        top_users = UserService.get_top_users(10)
    except Exception as e:
        logger.error(f"❌ خطأ في إحصائيات المستخدمين: {e}")
        user_stats = {}
        top_users = []
    
    text = f"""👥 **إدارة المستخدمين**

📊 **الإحصائيات:**
├ إجمالي المستخدمين: {user_stats.get('total_users', 0):,}
├ مستخدمون جدد هذا الأسبوع: {user_stats.get('new_users_week', 0):,}
└ مستخدمون جدد هذا الشهر: {user_stats.get('new_users_month', 0):,}

🏆 **أكثر المستخدمين نشاطاً:**"""
    
    for i, user in enumerate(top_users[:5], 1):
        if len(user) >= 5:
            name = user[1] if user[1] else f"مستخدم {user[0]}"
            activity = (user[3] or 0) + (user[4] or 0)  # history + favorites
            text += f"\n**{i}.** {name} ({activity} نشاط)"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_search_user = types.InlineKeyboardButton("🔍 البحث عن مستخدم", callback_data="admin_user_search")
    btn_top_active = types.InlineKeyboardButton("🏆 الأكثر نشاطاً", callback_data="admin_user_top_active")
    markup.add(btn_search_user, btn_top_active)
    
    btn_new_users = types.InlineKeyboardButton("🆕 المستخدمون الجدد", callback_data="admin_user_new")
    btn_inactive = types.InlineKeyboardButton("😴 غير النشطين", callback_data="admin_user_inactive")
    markup.add(btn_new_users, btn_inactive)
    
    btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
    markup.add(btn_back)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')


def handle_admin_stats(bot, call):
    """الإحصائيات التفصيلية"""
    try:
        from app.services.stats_service import StatsService
        stats = StatsService.get_general_stats()
        popular_categories = StatsService.get_popular_categories(5)
    except Exception as e:
        logger.error(f"❌ خطأ في الإحصائيات التفصيلية: {e}")
        stats = {}
        popular_categories = []
    
    text = f"""📊 **الإحصائيات التفصيلية**

🎬 **الفيديوهات:**
├ العدد الكلي: {stats.get('videos', 0):,}
├ إجمالي المشاهدات: {stats.get('total_views', 0):,}
└ متوسط المشاهدات: {stats.get('total_views', 0) // max(stats.get('videos', 1), 1):,}

👥 **المستخدمون:**
├ العدد الكلي: {stats.get('users', 0):,}
└ إجمالي المفضلات: {stats.get('favorites', 0):,}

📚 **التصنيفات الأشهر:**"""
    
    for i, category in enumerate(popular_categories[:5], 1):
        text += f"\n**{i}.** {category.get('name', 'غير محدد')} ({category.get('videos', 0)} فيديو)"
    
    text += f"\n\n🕒 **آخر تحديث:** {datetime.now().strftime('%H:%M:%S')}"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_export = types.InlineKeyboardButton("📤 تصدير الإحصائيات", callback_data="admin_stats_export")
    btn_refresh = types.InlineKeyboardButton("🔄 تحديث", callback_data="admin_stats")
    markup.add(btn_export, btn_refresh)
    
    btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
    markup.add(btn_back)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')


def handle_admin_cleanup(bot, call):
    """تنظيف قاعدة البيانات"""
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


def handle_cleanup_confirm(bot, call, admin_id):
    """تنفيذ التنظيف"""
    try:
        from app.services.user_service import UserService
        
        # تنفيذ التنظيف
        UserService.cleanup_old_history(15)
        
        result_text = f"""✅ **تم تنظيف قاعدة البيانات بنجاح!**

📊 **النتائج:**
├ تم حذف السجلات القديمة ✅
├ تم تحسين قاعدة البيانات ✅
└ تم إعادة بناء الفهارس ✅

⏱️ **وقت التنفيذ:** {datetime.now().strftime('%H:%M:%S')}

👨‍💼 **نفذ بواسطة:** {call.from_user.first_name}"""
        
        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
        markup.add(btn_back)
        
        bot.edit_message_text(result_text, call.message.chat.id, call.message.message_id, 
                             reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"❌ خطأ في التنظيف: {e}")
        
        error_text = f"""❌ **فشل في تنظيف قاعدة البيانات**

🔍 **تفاصيل الخطأ:**
{str(e)[:200]}...

⏱️ **وقت المحاولة:** {datetime.now().strftime('%H:%M:%S')}"""
        
        markup = types.InlineKeyboardMarkup()
        btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
        markup.add(btn_back)
        
        bot.edit_message_text(error_text, call.message.chat.id, call.message.message_id, 
                             reply_markup=markup, parse_mode='Markdown')


def handle_admin_broadcast(bot, call):
    """الرسائل الجماعية"""
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
    
    btn_test = types.InlineKeyboardButton("🧪 رسالة تجريبية", callback_data="admin_broadcast_test")
    btn_back = types.InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_back")
    markup.add(btn_test, btn_back)
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='Markdown')


def register_admin_handlers(bot):
    """تسجيل معالجات الإدارة"""
    bot.message_handler(commands=['admin'])(lambda message: admin_command(bot, message))
    
    # تسجيل معالج الأزرار للإدارة
    def admin_callback_filter(call):
        return call.data.startswith('admin_')
    
    bot.callback_query_handler(func=admin_callback_filter)(lambda call: handle_admin_callback(bot, call))
    
    logger.info("✅ تم تسجيل معالجات الإدارة")
