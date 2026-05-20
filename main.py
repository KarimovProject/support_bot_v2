import logging
import asyncio
import aiosqlite
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.error import Forbidden
import os
from dotenv import load_dotenv

# Tizimdagi yoki .env fayldagi maxfiy o'zgaruvchilarni yuklash
load_dotenv()

# Sirlarni xavfsiz tarzda chaqirib olish
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")

# Kichik himoya: Agar token topilmasa, dastur xato berib to'xtaydi (bu xatoni erta topishga yordam beradi)
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylini yoki GitHub Secrets'ni tekshiring.")

if not GROUP_ID:
    raise ValueError("GROUP_ID topilmadi! .env faylini tekshiring.")

try:
    ADMIN_GROUP_ID = int(GROUP_ID)
except ValueError:
    raise ValueError("GROUP_ID butun son bo'lishi kerak.")

# ... Qolgan kodingiz shu yerdan davom etadi ...
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
async def init_db():
    async with aiosqlite.connect("support.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_user_to_db(user):
    async with aiosqlite.connect("support.db") as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, full_name, username)
            VALUES (?, ?, ?)
        """, (user.id, user.full_name, user.username))
        await db.commit()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_user_to_db(user)
    msg = (
        f"Assalomu alaykum, {user.first_name}! 👋\n\n"
        "Savolingizni shu yerga yozing. Adminlarimiz javob berishadi. CI/CD fayli tayyorlangan tayyor project!"
    )
    await update.message.reply_text(msg)

async def forward_to_admin_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == ADMIN_GROUP_ID:
        return

    user = update.effective_user
    await add_user_to_db(user)

    try:
        forwarded_msg = await update.message.forward(chat_id=ADMIN_GROUP_ID)
        context.bot_data[forwarded_msg.message_id] = user.id
        
        if user.username:
            info_text = f"Foydalanuvchi: @{user.username} ({user.full_name})"
        else:
            info_text = f"Foydalanuvchi: {user.full_name}"
    except Exception as e:
        logging.error(f"Forward xatosi: {e}")

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_GROUP_ID or not update.message.reply_to_message:
        return
    user_status = await context.bot.get_chat_member(ADMIN_GROUP_ID, update.effective_user.id)
    if user_status.status not in ['administrator', 'creator']:
        await update.message.reply_text("⛔️ Siz admin emassiz, javob yuborilmadi.")
        return

    original_msg = update.message.reply_to_message
    user_id = None

    if original_msg.message_id in context.bot_data:
        user_id = context.bot_data[original_msg.message_id]
    
    if not user_id:
        if hasattr(original_msg, 'forward_origin') and original_msg.forward_origin:
             if original_msg.forward_origin.type == 'user':
                 user_id = original_msg.forward_origin.sender_user.id
        elif hasattr(original_msg, 'forward_from') and original_msg.forward_from:
            user_id = original_msg.forward_from.id
    if user_id:
        try:
            await update.message.copy(chat_id=user_id)
            await update.message.reply_text("✅ Javob yuborildi!")
        except Forbidden:
            await update.message.reply_text("❌ User botni bloklagan.")
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {e}")
    else:
        await update.message.reply_text(
            "⚠️ **Diqqat:** Foydalanuvchi aniqlanmadi.\n\n"
            "Sababi: Bot qayta ishga tushgan bo'lishi mumkin yoki foydalanuvchi profili yopiq.\n"
            "Iltimos, foydalanuvchi yangi xabar yozishini kuting.", 
            parse_mode="Markdown"
        )

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.REPLY, 
        reply_to_user
    ))

    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & ~filters.ChatType.GROUPS, 
        forward_to_admin_group
    ))

    print("Bot ishga tushdi...")
    application.run_polling()
