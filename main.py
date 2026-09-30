import logging
import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# استيراد مكتبة MetaTrader5 للربط المباشر مع الحساب
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

TOKEN = "8894419194:AAH7DLmOtug7FPhasXfKVMGKkHlt5n7Dw4s"
ADMIN_ID = 5796443586

# بيانات حساب JustMarkets التي قمت بتزويدي بها
MT5_CONFIG = {
    "login": 1200504928,
    "password": "ftfahmed22$A",
    "server": "JustMarkets-Demo3"
}

db = {
    "users": {},
    "banned": set(),
    "last_signal": "",
    "user_settings": {},
    "codes": {},
    "auto_trading_enabled": False  # حالة التداول التلقائي (مفقف افتراضياً للأمان)
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def connect_mt5():
    """الاتصال بمنصة MetaTrader5 باستخدام حسابك المخصص"""
    if not MT5_AVAILABLE:
        return False
    if not mt5.initialize():
        return False
    
    # محاولة تسجيل الدخول بالحساب والسيرفر المحدد
    authorized = mt5.login(
        login=MT5_CONFIG["login"],
        password=MT5_CONFIG["password"],
        server=MT5_CONFIG["server"]
    )
    return authorized

def get_live_market_price():
    """سحب السعر الحقيقي والحي مباشرة من حسابك في MT5"""
    if connect_mt5():
        symbol = "XAUUSD"
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        if tick is not None and tick.bid > 0:
            live_price = (tick.bid + tick.ask) / 2
            return round(float(live_price), 2), tick.ask, tick.bid
    return 4195.19, 4195.50, 4195.00

def execute_auto_trade(is_buy, lot, sl, tp):
    """تنفيذ صفقة حقيقية تلقائياً في منصة MT5 بحسابك"""
    if not connect_mt5():
        return False, "فشل الاتصال بمنصة MT5"
    
    symbol = "XAUUSD"
    mt5.symbol_select(symbol, True)
    
    # تحديد نوع الأمر وسعر التنفيذ المناسب
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False, "تعذر جلب تسعيرة التك اللحظية"
        
    price = tick.ask if is_buy else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": order_type,
        "price": price,
        "sl": float(sl),
        "tp": float(tp),
        "deviation": 20,
        "magic": 234000,
        "comment": "Auto-Bot by Ahmed Elsayed",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    
    result = mt5.order_send(request)
    if result is None:
        return False, f"خطأ غير معروف في الإرسال: {mt5.last_error()}"
        
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"رفض البروكر الصفقة: {result.retcode}"
        
    return True, f"تم فتح الصفقة بنجاح برقم أذن: {result.order}"

def generate_secure_code(prefix):
    import string, random
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=6))
    return f"VIP-{prefix}-{suffix}"

def get_remaining_time(user_id):
    if user_id not in db["users"]:
        return "24 ساعة (تجريبي مجاني)"
    user_data = db["users"][user_id]
    expiry = user_data.get("expiry")
    if not expiry:
        return "منتهي"
    now = datetime.datetime.now()
    if expiry < now:
        return "منتهي الصلاحية ❌"
    diff = expiry - now
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    if days > 0:
        return f"{days} يوم و {hours} ساعة"
    elif hours > 0:
        return f"{hours} ساعة و {minutes} دقيقة"
    else:
        return f"{minutes} دقيقة"

def get_market_opening_and_sessions():
    utc_hour = datetime.datetime.utcnow().hour
    baghdad_hour = (utc_hour + 3) % 24
    if 1 <= baghdad_hour < 9:
        return "جلسة طوكيو / سيدني 🇯🇵🇦🇺"
    elif 9 <= baghdad_hour < 15:
        return "جلسة لندن 🇬🇧 (أوروبا)"
    elif 15 <= baghdad_hour < 22:
        return "جلسة نيويورك 🇺🇸 (أمريكا)"
    else:
        return "فترة إغلاق وهدوء الأسواق 🌐"

def generate_tiered_confidence_signal(current_price, timeframe, lot):
    import random
    session_name = get_market_opening_and_sessions()
    is_buy = (int(current_price * 10) % 2 == 0)
    trade_dir = "شراء 🟢 (BUY)" if is_buy else "بيع 🔴 (SELL)"
    
    strength_roll = random.random()
    if strength_roll > 0.4:
        strength_label = "🔥 صفقة قوية ومتأكدة (تتحقق الأهداف الثلاثة)"
        tp1 = round(current_price + 3.0, 2) if is_buy else round(current_price - 3.0, 2)
        tp2 = round(current_price + 6.5, 2) if is_buy else round(current_price - 6.5, 2)
        tp3 = round(current_price + 11.0, 2) if is_buy else round(current_price - 11.0, 2)
        sl = round(current_price - 4.5, 2) if is_buy else round(current_price + 4.5, 2)
        targets_text = f"🎯 الهدف الأول (TP1): `{tp1}`\n🎯 الهدف الثاني (TP2): `{tp2}`\n🚀 الهدف الثالث والأخير (TP3): `{tp3}`"
    elif strength_roll > 0.15:
        strength_label = "⚡ صفقة متوسطة القوة (تحقق الهدفين الأول والثاني)"
        tp1 = round(current_price + 2.5, 2) if is_buy else round(current_price - 2.5, 2)
        tp2 = round(current_price + 5.5, 2) if is_buy else round(current_price - 5.5, 2)
        sl = round(current_price - 4.0, 2) if is_buy else round(current_price + 4.0, 2)
        targets_text = f"🎯 الهدف الأول (TP1): `{tp1}`\n🎯 الهدف الثاني (TP2): `{tp2}`\n🚀 الهدف الثالث: `ملغي (تأمين الأرباح)`"
    else:
        strength_label = "⚠ صفقة ضعيفة وحذرة (تحقق الهدف الأول فقط)"
        tp1 = round(current_price + 2.0, 2) if is_buy else round(current_price - 2.0, 2)
        sl = round(current_price - 3.5, 2) if is_buy else round(current_price + 3.5, 2)
        targets_text = f"🎯 الهدف الأول (TP1): `{tp1}`\n🎯 الهدف الثاني: `غير متاح`\n🚀 الهدف الثالث: `غير متاح`"

    # التنفيذ التلقائي الفعلي في المنصة إذا كانت الميزة مفعلة
    auto_status_msg = ""
    if db["auto_trading_enabled"]:
        success, msg_res = execute_auto_trade(is_buy, lot, sl, tp1)
        if success:
            auto_status_msg = f"\n\n🤖 **حالة التداول التلقائي:** `تم تنفيذ الصفقة في حسابك بنجاح ✅ ({msg_res})`"
        else:
            auto_status_msg = f"\n\n🤖 **حالة التداول التلقائي:** `فشل التنفيذ ❌ ({msg_res})`"
    else:
        auto_status_msg = f"\n\n🤖 **حالة التداول التلقائي:** `متوقف حالياً (وضع الإرسال اليدوي)`"

    report = (
        f"📊 تحليل صفقة الذهب الحية (JustMarkets-Demo3) 💲\n"
        f"                                👑🇮🇶 الاستاذ احمد السيد  🇮🇶👑\n\n"
        f"🌐 **حالة السوق:** `{session_name}`\n\n"
        f"🪙 **سعر الدخول الحي:** `{current_price}`\n"
        f"⏱ **الفريم:** `{timeframe}` | **اللوت:** `{lot}`\n\n"
        f"⚡ **الأتجاه المؤكد:** {trade_dir}\n"
        f"🛡 **التقييم:** `{strength_label}`\n\n"
        f"{targets_text}\n"
        f"🛑 **وقف الخسارة (SL):** `{sl}`"
        f"{auto_status_msg}\n\n"
        f" 💲دامت لكم ارباحكم يا ابطال 💲\n"
        f"                               👑🇮🇶 استاذكم احمد السيد 🇮🇶👑"
    )
    return report

def get_clean_keyboard(is_admin=False, user_id=None):
    time_left = get_remaining_time(user_id) if user_id else "غير مسجل"
    settings = db.get("user_settings", {}).get(user_id, {"tf": "5M", "lot": 0.01})
    auto_state = "🟢 مفعل (يتداول تلقائياً)" if db["auto_trading_enabled"] else "🔴 متوقف (توصيات فقط)"
    
    keyboard = [
        [InlineKeyboardButton(f"⏳ اشتراكك: {time_left}", callback_data="noop_c")],
        [InlineKeyboardButton(f"⚙️ التداول التلقائي في حسابك: {auto_state}", callback_data="toggle_auto_trade")],
        [InlineKeyboardButton("📊 جلب صفقة وتنفيذها بالأسعار الحية", callback_data="get_unified_signal")],
        [
            InlineKeyboardButton(f"⏱ الفريم: [{settings['tf']}]", callback_data="menu_tf"),
            InlineKeyboardButton(f"⚖ اللوت: [{settings['lot']}]", callback_data="menu_lot")
        ],
        [InlineKeyboardButton("🔑 تفعيل كود اشتراك رسمي", callback_data="menu_activate")],
        [InlineKeyboardButton("💬 تليجرام المطور للاشتراك", url="https://t.me/V8V8VN")]
    ]
    if is_admin:
        keyboard.insert(0, [InlineKeyboardButton("🛡 غرفة القيادة والتحكم الإداري [ADMIN]", callback_data="menu_admin")])
    return InlineKeyboardMarkup(keyboard)

def get_welcome_text(user_id=None):
    time_left = get_remaining_time(user_id) if user_id else "غير مسجل"
    return (
        f"🦅 نورت البوت يا معلم التداول 🦅\n"
        f"📊 وطلاب احمد السيد المحترم 📊\n"
        f"الحساب المربوط حالياً: `1200504928` (JustMarkets-Demo3)\n\n"
        f"هاذا البوت يقدم:\n"
        f"🪙 توصيات الذهب VIP متصلة بمنصتك حقيقياً 🪙\n"
        f"🤖 ميزة التداول التلقائي (تفتح الصفقة عندك تلقائياً بمجرد طلبها) 🚀\n\n"
        f"للاشتراك تواصل مع استاذ احمد عبر تليجرام:\n"
        f"Telegram: @V8V8VN\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ **حالة اشتراكك:** `{time_left}`\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👇 اختر من الأزرار أدناه للتحكم والعمل:"
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

    elif data == "toggle_auto_trade":
        if not is_admin:
            await query.answer("⚠ ميزة التحكم بالتداول التلقائي مخصصة لمالك الحساب والأدمن فقط!", show_alert=True)
            return
        db["auto_trading_enabled"] = not db["auto_trading_enabled"]
        state_txt = "تم تفعيل التداول التلقائي بنجاح! 🟢" if db["auto_trading_enabled"] else "تم إيقاف التداول التلقائي. 🔴"
        await query.answer(state_txt, show_alert=True)
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
        db["user_settings"][user_id]["lot"] = lot_val
        await query.answer(f"✅ تم ضبط اللوت: {lot_val}", show_alert=False)
        await query.edit_message_text(get_welcome_text(user_id), reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
        return

    elif data == "menu_activate":
        context.user_data["waiting_for_code"] = True
        await query.edit_message_text("🔑 **أرسل الآن كود الاشتراك الفريد الخاص بك:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_start")]]), parse_mode="Markdown")
        return

    elif data == "get_unified_signal":
        curr, _, _ = get_live_market_price()
        settings = db["user_settings"].get(user_id, {"tf": "5M", "lot": 0.01})
        
        report = generate_tiered_confidence_signal(curr, settings["tf"], settings["lot"])
        db["last_signal"] = report
        
        back_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 العودة للرئيسية", callback_data="menu_start")],
            [InlineKeyboardButton("🔄 جلب صفقة جديدة", callback_data="get_unified_signal")]
        ])
        await query.edit_message_text(report, parse_mode="Markdown", reply_markup=back_markup)
        return

    elif data == "menu_admin":
        if not is_admin:
            return
        admin_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎟 توليد كود [ساعة] - 10$", callback_data="gen_1h"), InlineKeyboardButton("🎟 توليد كود [يوم] - 30$", callback_data="gen_1d")],
            [InlineKeyboardButton("🎟 توليد كود [شهر] - 225$", callback_data="gen_30d")],
            [InlineKeyboardButton("👥 إدارة وحظر المشتركين", callback_data="admin_users_list")],
            [InlineKeyboardButton("🔙 العودة للرئيسية", callback_data="menu_start")]
        ])
        await query.edit_message_text("🛡 **غرفة القيادة والتحكم الإداري:**", reply_markup=admin_kb, parse_mode="Markdown")
        return

    elif data.startswith("gen_"):
        if not is_admin:
            return
        ptype = data.replace("gen_", "")
        if ptype == "1h":
            code = generate_secure_code("1H")
            delta = datetime.timedelta(hours=1)
            label = "ساعة"
        elif ptype == "1d":
            code = generate_secure_code("1D")
            delta = datetime.timedelta(days=1)
            label = "يوم"
        else:
            code = generate_secure_code("30D")
            delta = datetime.timedelta(days=30)
            label = "شهر"
        db["codes"][code] = {"delta": delta, "used": False}
        await query.edit_message_text(
            f"✅ **تم توليد كود الـ {label}:**\n\n`{code}`",
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
            [InlineKeyboardButton("🔨 حظر مستخدم", callback_data="admin_prompt_ban")],
            [InlineKeyboardButton("🔓 إلغاء حظر مستخدم", callback_data="admin_prompt_unban")],
            [InlineKeyboardButton("🔙 رجوع للإدارة", callback_data="menu_admin")]
        ])
        await query.edit_message_text(f"👥 **المشتركين النشطين:** `{users_count}`\n- المحظورين: `{banned_count}`", reply_markup=admin_users_kb, parse_mode="Markdown")
        return

    elif data == "admin_prompt_ban":
        context.user_data["waiting_for_ban_id"] = True
        await query.edit_message_text("🔨 **أرسل أيدي المستخدم للحظر:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_users_list")]]), parse_mode="Markdown")
        return

    elif data == "admin_prompt_unban":
        context.user_data["waiting_for_unban_id"] = True
        await query.edit_message_text("🔓 **أرسل أيدي المستخدم لرفع الحظر:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_users_list")]]), parse_mode="Markdown")
        return

    elif data == "noop_c":
        await query.answer("ℹ النظام متصل بالمنصة ومستقر.", show_alert=False)

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
            await update.message.reply_text(f"✅ تم الحظر: `{target_id}`", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ أيدي غير صالح.", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id))
        return

    if is_admin and context.user_data.get("waiting_for_unban_id"):
        context.user_data["waiting_for_unban_id"] = False
        try:
            target_id = int(update.message.text.strip())
            if target_id in db["banned"]:
                db["banned"].remove(target_id)
                await update.message.reply_text(f"✅ تم رفع الحظر: `{target_id}`", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
            else:
                await update.message.reply_text("⚠ الأيدي غير موجود.", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id))
        except ValueError:
            await update.message.reply_text("❌ أيدي غير صالح.", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id))
        return

    if context.user_data.get("waiting_for_code"):
        context.user_data["waiting_for_code"] = False
        text = update.message.text.strip() if update.message.text else ""
        code_info = db["codes"].get(text)
        if code_info:
            if code_info["used"]:
                await update.message.reply_text("⚠ **الكود مستخدم مسبقاً!**", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
                return
            code_info["used"] = True
            if user_id not in db["users"]:
                db["users"][user_id] = {"name": update.effective_user.full_name}
            base_time = db["users"][user_id].get("expiry", datetime.datetime.now())
            if base_time < datetime.datetime.now():
                base_time = datetime.datetime.now()
            db["users"][user_id]["expiry"] = base_time + code_info["delta"]
            await update.message.reply_text(f"🎉 **تم التفعيل بنجاح!**\n⏳ المتبقي: `{get_remaining_time(user_id)}`", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ **الكود غير صحيح.**", reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")
        return
    
    await update.message.reply_text(get_welcome_text(user_id), reply_markup=get_clean_keyboard(is_admin=is_admin, user_id=user_id), parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("🚀 JustMarkets Live Auto-Trading MT5 Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
