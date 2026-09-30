import random
import datetime

def get_live_gold_price():
    base_price = 2650.50
    fluctuation = round(random.uniform(-4.50, 4.50), 2)
    return round(base_price + fluctuation, 2)

def get_remaining_time(user_id, db):
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
