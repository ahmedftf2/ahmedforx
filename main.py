import logging
import datetime
import random
import string
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from utils import get_live_gold_price, get_remaining_time

TOKEN = "8884364042:AAEPwYmYQiZ1sN7GUGouMVrgtT3EyNL1d7w"
ADMIN_ID = 5796443586

db = {
    "users": {},
    "banned": set(),
    "last_signal": "",
    "user_settings": {},
    "codes": {}
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def generate_secure_code(prefix):
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=6))
    return f"VIP-{prefix}-{suffix}"

def get_current_session_and_country():
    utc_hour = datetime.datetime.utcnow().hour
    baghdad_hour = (utc_hour + 3) % 24

    if 9 <= baghdad_hour < 17:
        return "جلسة لندن 🇬🇧 (أوروبا)", "المملكة المتحدة / أوروبا"
    elif 15 <= baghdad_hour < 24:
        return "جلسة نيويورك 🇺🇸 (أمريكا)", "الولايات المتحدة الأمريكية"
    elif 1 <= baghdad_hour < 9:
        return "جلسة طوكيو / سيدني 🇯🇵🇦🇺 (آسيا)", "اليابان / أستراليا"
    else:
        return "جلسة تداول انتقالية (ما بين الجلسات) 🌐", "السوق العالمي (الأسواق الإلكترونية)"

def generate_custom_institutional_signal(current_price, timeframe, lot):
    session_name, country_name = get_current_session_and_country()
    
    trade_dir = random.choice(["شراء 🟢", "بيع 🔴"])
    strength_type = random.choice(["قوية", "وسط", "ضعيفة"])
    
    if strength_type == "قوية":
        strength_icon = "قوية ⚪"
        top_val = "توب 3 🌟"
        confidence = random.randint(88, 99)
        if "شراء" in trade_dir:
            targets_str = (
                f"🎯 **الهدف الأول (TP1):** `{round(current_price + 3.8, 2)}`\n"
                f"🎯 **الهدف الثاني (TP2):** `{round(current_price + 7.5, 2)}`\n"
                f"🚀 **الهدف الثالث (TP3):** `{round(current_price + 13.0, 2)}`\n"
            )
            sl = round(current_price - 4.5, 2)
        else:
            targets_str = (
                f"🎯 **الهدف الأول (TP1):** `{round(current_price - 3.8, 2)}`\n"
                f"🎯 **الهدف الثاني (TP2):** `{round(current_price - 7.5, 2)}`\n"
                f"🚀 **الهدف الثالث (TP3):** `{round(current_price - 13.0, 2)}`\n"
            )
            sl = round(current_price + 4.5, 2)

    elif strength_type == "وسط":
        strength_icon = "وسط 🔵"
        top_val = "توب 2 ⭐"
        confidence = random.randint(70, 86)
        if "شراء" in trade_dir:
            targets_str = (
                f"🎯 **الهدف الأول (TP1):** `{round(current_price + 3.2, 2)}`\n"
                f"🎯 **الهدف الثاني (TP2):** `{round(current_price + 6.5, 2)}`\n"
            )
            sl = round(current_price - 4.0, 2)
        else:
            targets_str = (
                f"🎯 **الهدف الأول (TP1):** `{round(current_price - 3.2, 2)}`\n"
                f"🎯 **الهدف الثاني (TP2):** `{round(current_price - 6.5, 2)}`\n"
            )
            sl = round(current_price + 4.0, 2)

    else:
        strength_icon = "ضعيفة 🟠"
        top_val = "توب 1 🔸"
        confidence = random.randint(55, 68)
        if "شراء" in trade_dir:
            targets_str = (
                f"🎯 **الهدف الأول (TP1):** `{round(current_price + 2.8, 2)}`\n"
            )
            sl = round(current_price - 3.0, 2)
        else:
            targets_str = (
                f"🎯 **الهدف الأول (TP1):** `{round(current_price - 2.8, 2)}`\n"
            )
            sl = round(current_price + 3.0, 2)

    report = (
        f"📊 صفقات الاستاذ وخبير التداول 💲\n"
        f"                                👑🇮🇶 الاستاذ احمد السيد  🇮🇶👑\n\n"
        f"🌐 **جلسة الصفقة:** `{session_name}`\n"
        f"📍 **الدولة المصدرة للسيولة:** `{country_name}`\n"
        f"🪙 **السعر الحالي للذهب (حي):** `{current_price}`\n"
        f"⏱ **الفريم:** `{timeframe}` | **اللوت:** `{lot}`\n\n"
        f"⚡ **نوع الصفقة:** {trade_dir}\n"
        f"💪 **قوة الصفقة:** {strength_icon}\n"
        f"🎯 **تاكيد الصفقة:** `{confidence}%` ({top_val})\n\n"
        f"{targets_str}"
        f"🛑 **وقف الخسارة (SL):** `{sl}`\n\n"
        f" 💲دامت لكم ارباحكم يا ابطال 💲\n"
        f"                               👑🇮🇶 استاذكم احمد السيد 🇮🇶👑"
    )
    return report

def get_clean_keyboard(is_admin=False, user_id=None):
    time_left = get_remaining_time(user_id, db) if user_id else "غير مسجل"
    settings = db.get("user_settings", {}).get(user_id, {"tf": "5M", "lot": 0.01})
    
    keyboard = [
        [InlineKeyboardButton(f"⏳ الوقت المتبقي لاشتراكك: {time_left}", callback_data="noop_c")],
        [InlineKeyboardButton("📊 جلب تحليل وصفقة الذهب VIP", callback_data="get_unified_signal")],
        [
            InlineKeyboardButton(f"⏱ الفريم: [{settings['tf']}]", callback_data="menu_tf"),
            InlineKeyboardButton(f"⚖ اللوت: [{settings['lot']}]", callback_data="menu_lot")
        ],
        [InlineKeyboardButton("🔑 تفعيل كود اشتراك رسمي", callback_data="menu_activate")],
        [
            InlineKeyboardButton("📸 إنستغرام", url="https://instagram.com/_7ok6"),
            InlineKeyboardButton("🎵 تيك توك", url="https://tiktok.com/@7ok6_"),
            InlineKeyboardButton("💬 تليجرام المطور", url="https://t.me/V8V8VN")
        ]
    ]
    if is_admin:
        keyboard.insert(0, [InlineKeyboardButton("🛡 غرفة القيادة وحماية النظام [ADMIN]", callback_data="menu_admin")])
    return InlineKeyboardMarkup(keyboard)

def get_welcome_text(user_id=None):
    time_left = get_remaining_time(user_id, db) if user_id else "غير مسجل"
    return (
        f"🦅 نورت البوت يا معلم التداول 🦅\n"
        f"📊 وطلاب احمد السيد المحترم 📊\n"
        f"اقدم لكم الاستاذ 🐦‍🔥 احمد السيد 🐦‍🔥\n"
        f"خبير تداول الفوركس والذهب 🪙 \n"
        f"🤴🏻 خبرة تحليل ومدارس على مدى 3 سنوات 🇮🇶👑\n"
        f"📈خبرة صنع مؤشرات عالميا و وشرق اوسط 📉\n\n"
        f"هاذا البوت يقدم \n"
        f"🪙توصيات الذهب VIP 🪙\n"
        f"💎ويقدم ايضا اشتراك 💸\n"
        f" كورس لتعليم التداول 📊\n\n"
        f"للاشتراك تواصل مع استاذ احمد \n"
        f"Telegram:  @V8V8VN\n"
        f"Instagram: _7ok6\n"
        f"TikTok:  7ok6_\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ **حالة اشتراكك:** `{time_left}`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👇 اختر من الأزرار أدناه للتحكم بالفريم، اللوت، أو جلب الصفقة الحقيقية الفورية:"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in db["banned"]:
        return

    if user.id not in db["users"] and user.id != ADMIN_ID:
        db["users"][user.id] = {
            "name": user.full_name,
            "username": f"@{user.username}" if user.username else "بدون معرف",
            "expiry": datetime.datetime.now() + datetime.timedelta(hours=24)
        }
        
    if user.id not in db["user_settings"]:
        db["user_settings"][user.id] = {"tf": "5M", "lot": 0.01}

    is_admin = (user.id == ADMIN_ID)
    msg = get_welcome_text(user.id)
    keyboard = get_clean_keyboard(is_admin=is_admin, user_id=user.id)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(msg, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=keyboard, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id in db["banned"]:
        return

    data = query.data
    is_admin = (user_id == ADMIN_ID)

    if data == "menu_start":
        await query.edit_message_text(get_welcome_text(user_id), reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
        return

    elif data == "menu_tf":
        tf_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1M", callback_data="tf_1M"), InlineKeyboardButton("5M", callback_data="tf_5M"), InlineKeyboardButton("15M", callback_data="tf_15M")],
            [InlineKeyboardButton("30M", callback_data="tf_30M"), InlineKeyboardButton("1H", callback_data="tf_1H"), InlineKeyboardButton("4H", callback_data="tf_4H")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_start")]
        ])
        await query.edit_message_text("⏱ **اختر فريم التحليل المطلوب:**", reply_markup=tf_kb, parse_mode="Markdown")
        return

    elif data.startswith("tf_"):
        tf_val = data.replace("tf_", "")
        if user_id not in db["user_settings"]:
            db["user_settings"][user_id] = {"tf": "5M", "lot": 0.01}
        db["user_settings"][user_id]["tf"] = tf_val
        await query.answer(f"✅ تم ضبط الفريم: {tf_val}", show_alert=False)
        await query.edit_message_text(get_welcome_text(user_id), reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
        return

    elif data == "menu_lot":
        lot_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("0.01", callback_data="lot_0.01"), InlineKeyboardButton("0.05", callback_data="lot_0.05"), InlineKeyboardButton("0.10", callback_data="lot_0.10")],
            [InlineKeyboardButton("0.50", callback_data="lot_0.50"), InlineKeyboardButton("1.00", callback_data="lot_1.00"), InlineKeyboardButton("5.00", callback_data="lot_5.00")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_start")]
        ])
        await query.edit_message_text("⚖ **اختر حجم اللوت المناسب:**", reply_markup=lot_kb, parse_mode="Markdown")
        return

    elif data.startswith("lot_"):
        lot_val = float(data.replace("lot_", ""))
        if user_id not in db["user_settings"]:
            db["user_settings"][user_id] = {"tf": "5M", "lot": 0.01}
        db["user_settings"][user_id]["lot"] = lot_val
        await query.answer(f"✅ تم ضبط اللوت: {lot_val}", show_alert=False)
        await query.edit_message_text(get_welcome_text(user_id), reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
        return

    elif data == "menu_activate":
        context.user_data["waiting_for_code"] = True
        await query.edit_message_text("🔑 **أرسل الآن كود الاشتراك الفريد الخاص بك في الرسائل لتفعيله فوراً:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_start")]]), parse_mode="Markdown")
        return

    elif data == "get_unified_signal":
        curr = get_live_gold_price()
        settings = db["user_settings"].get(user_id, {"tf": "5M", "lot": 0.01})
        
        report = generate_custom_institutional_signal(curr, settings["tf"], settings["lot"])
        db["last_signal"] = report
        
        back_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 العودة للرئيسية", callback_data="menu_start")],
            [InlineKeyboardButton("🔄 تحديث حالة الصفقة", callback_data="get_unified_signal")]
        ])
        
        await query.edit_message_text(report, parse_mode="Markdown", reply_markup=back_markup)
        return

    elif data == "menu_admin":
        if not is_admin:
            return
        admin_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎟 توليد كود [ساعة] - 10$", callback_data="gen_1h"), InlineKeyboardButton("🎟 توليد كود [يوم] - 30$", callback_data="gen_1d")],
            [InlineKeyboardButton("🎟 توليد كود [أسبوع] - 80$", callback_data="gen_1w"), InlineKeyboardButton("🎟 توليد كود [أسبوعين] - 140$", callback_data="gen_2w")],
            [InlineKeyboardButton("🎟 توليد كود [شهر] - 225$", callback_data="gen_30d")],
            [InlineKeyboardButton("👥 إدارة وحظر المشتركين والأيديات", callback_data="admin_users_list")],
            [InlineKeyboardButton("🔙 العودة للرئيسية", callback_data="menu_start")]
        ])
        await query.edit_message_text("🛡 **غرفة الحماية وتوليد الأكواد الديناميكية الفردية:**\nاختر فئة الاشتراك لتوليد كود رسمي:", reply_markup=admin_kb, parse_mode="Markdown")
        return

    elif data.startswith("gen_"):
        if not is_admin:
            return
        ptype = data.replace("gen_", "")
        if ptype == "1h":
            code = generate_secure_code("1H")
            delta = datetime.timedelta(hours=1)
            label = "ساعة (10$)"
        elif ptype == "1d":
            code = generate_secure_code("1D")
            delta = datetime.timedelta(days=1)
            label = "يوم (30$)"
        elif ptype == "1w":
            code = generate_secure_code("1W")
            delta = datetime.timedelta(weeks=1)
            label = "أسبوع (80$)"
        elif ptype == "2w":
            code = generate_secure_code("2W")
            delta = datetime.timedelta(weeks=2)
            label = "أسبوعين (140$)"
        else:
            code = generate_secure_code("30D")
            delta = datetime.timedelta(days=30)
            label = "شهر (225$)"
            
        db["codes"][code] = {"delta": delta, "used": False}
        
        await query.edit_message_text(
            f"✅ **تم توليد كود الـ {label} بنجاح (مخصص لمرة واحدة):**\n\n`{code}`\n\n*(انسخ هذا الكود وأعطه للزبون حصراً)*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للإدارة", callback_data="menu_admin")]]),
            parse_mode="Markdown"
        )
        return

    elif data == "admin_users_list":
        if not is_admin:
            return
        users_count = len(db["users"])
        banned_count = len(db["banned"])
        admin_users_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔨 حظر مستخدم (أرسل الأيدي)", callback_data="admin_prompt_ban")],
            [InlineKeyboardButton("🔓 إلغاء حظر مستخدم", callback_data="admin_prompt_unban")],
            [InlineKeyboardButton("🔙 رجوع للإدارة", callback_data="menu_admin")]
        ])
        await query.edit_message_text(f"👥 **إدارة المشتركين والأمان:**\n- المشتركين النشطين: `{users_count}`\n- المحظورين أمنياً: `{banned_count}`", reply_markup=admin_users_kb, parse_mode="Markdown")
        return

    elif data == "admin_prompt_ban":
        context.user_data["waiting_for_ban_id"] = True
        await query.edit_message_text("🔨 **أرسل الآن (أيدي المستخدم - ID) المراد حظره:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_users_list")]]), parse_mode="Markdown")
        return

    elif data == "admin_prompt_unban":
        context.user_data["waiting_for_unban_id"] = True
        await query.edit_message_text("🔓 **أرسل الآن (أيدي المستخدم - ID) المراد رفع الحظر عنه:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_users_list")]]), parse_mode="Markdown")
        return

    elif data == "noop_c":
        await query.answer("ℹ النظام فعال.", show_alert=False)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in db["banned"]:
        return

    is_admin = (user_id == ADMIN_ID)

    if is_admin and context.user_data.get("waiting_for_ban_id"):
        context.user_data["waiting_for_ban_id"] = False
        try:
            target_id = int(update.message.text.strip())
            db["banned"].add(target_id)
            await update.message.reply_text(f"✅ تم حظر المستخدم برقم الأيدي: `{target_id}`", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ أيدي غير صالح.", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id))
        return

    if is_admin and context.user_data.get("waiting_for_unban_id"):
        context.user_data["waiting_for_unban_id"] = False
        try:
            target_id = int(update.message.text.strip())
            if target_id in db["banned"]:
                db["banned"].remove(target_id)
                await update.message.reply_text(f"✅ تم رفع الحظر عن المستخدم: `{target_id}`", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
            else:
                await update.message.reply_text("⚠ الأيدي غير موجود في قائمة المحظورين.", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id))
        except ValueError:
            await update.message.reply_text("❌ أيدي غير صالح.", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id))
        return

    if context.user_data.get("waiting_for_code"):
        context.user_data["waiting_for_code"] = False
        text = update.message.text.strip() if update.message.text else ""
        code_info = db["codes"].get(text)
        
        if code_info:
            if code_info["used"]:
                await update.message.reply_text("⚠️ **هذا الكود مستخدم مسبقاً ولا يمكن استخدامه مرة أخرى!**", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
                return
                
            code_info["used"] = True
            
            if user_id not in db["users"]:
                db["users"][user_id] = {"name": update.effective_user.full_name}
            
            base_time = db["users"][user_id].get("expiry", datetime.datetime.now())
            if base_time < datetime.datetime.now():
                base_time = datetime.datetime.now()
            db["users"][user_id]["expiry"] = base_time + code_info["delta"]
            
            await update.message.reply_text(f"🎉 **تم تفعيل الاشتراك بنجاح تام!**\n⏳ الوقت المتبقي: `{get_remaining_time(user_id, db)}`", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ **الكود غير صحيح أو منتهي.** تأكد من نسخه بدقة.", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
        return
    
    await update.message.reply_text(get_welcome_text(user_id), reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("🚀 Ultimate Institutional Trading Bot Running (v2026 - Clean Code)...")
    app.run_polling()

if __name__ == "__main__":
    main()
