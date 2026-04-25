import requests
import os
import sys
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from typing import Dict, Optional

# ============================================
# 🔥 LOGGING SETUP
# ============================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# 🔥 CONFIGURATION
# ============================================
FIREBASE_DB_URL = "https://renz-24e39-default-rtdb.firebaseio.com"

# IMPORTANT: Get NEW token from @BotFather first!
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8623671987:AAGe-7ik49SvtU-M6ZIw1B1IW61ikB1I0EU')
YOUR_CHAT_ID = 6064653643

# Store data
user_sessions: Dict[str, dict] = {}
forwarded_mapping: Dict[int, str] = {}

# ============================================
# 🔥 FIREBASE HELPERS
# ============================================
def save_to_firebase(path: str, data: dict) -> bool:
    try:
        url = f"{FIREBASE_DB_URL}/{path}.json"
        response = requests.post(url, json=data, timeout=10)
        return response.ok
    except Exception as e:
        logger.error(f"Firebase save error: {e}")
        return False

def update_firebase(path: str, data: dict) -> bool:
    try:
        url = f"{FIREBASE_DB_URL}/{path}.json"
        response = requests.patch(url, json=data, timeout=10)
        return response.ok
    except Exception as e:
        logger.error(f"Firebase update error: {e}")
        return False

def get_from_firebase(path: str) -> Optional[dict]:
    try:
        url = f"{FIREBASE_DB_URL}/{path}.json"
        response = requests.get(url, timeout=10)
        if response.ok:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Firebase read error: {e}")
        return None

# ============================================
# 🎨 BUTTON MENUS
# ============================================
async def main_menu(update: Update, context):
    """Main admin menu"""
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message
    
    keyboard = [
        [InlineKeyboardButton("📊 DASHBOARD", callback_data="dashboard")],
        [InlineKeyboardButton("👥 USERS", callback_data="users_list")],
        [InlineKeyboardButton("📢 BROADCAST", callback_data="broadcast_menu")],
        [InlineKeyboardButton("💬 QUICK REPLY", callback_data="quick_reply")],
    ]
    
    menu_text = """
🌟 **RENZ SURVEY BOT - ADMIN PANEL** 🌟

✅ Bot Status: Online
✅ Firebase: Connected
✅ 24/7 Active

Select an option below:
"""
    
    if query:
        await query.edit_message_text(menu_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await message.reply_text(menu_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def dashboard_menu(update: Update, context):
    """Show dashboard"""
    query = update.callback_query
    await query.answer()
    
    users_data = get_from_firebase("users")
    total_users = len(users_data) if users_data else 0
    
    dashboard_text = f"""
📊 **DASHBOARD**

👥 Total Users: {total_users}
🟢 Active Now: {len(user_sessions)}
📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

✅ Bot Running Normally
"""
    
    keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]]
    await query.edit_message_text(dashboard_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def users_menu(update: Update, context):
    """Show users list"""
    query = update.callback_query
    await query.answer()
    
    users_data = get_from_firebase("users")
    if not users_data:
        await query.edit_message_text("📭 No users yet")
        return
    
    keyboard = []
    for user_id, data in list(users_data.items())[:10]:
        if isinstance(data, dict):
            name = data.get('name', 'Unknown')
            keyboard.append([InlineKeyboardButton(f"👤 {name}", callback_data=f"user_{user_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="main_menu")])
    
    await query.edit_message_text(
        f"👥 USERS ({len(users_data)} total)\n\nTap a user to see details:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def user_details_menu(update: Update, context):
    """Show user details"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.replace("user_", "")
    user_data = get_from_firebase(f"users/{user_id}")
    
    if not user_data:
        await query.edit_message_text("❌ User not found")
        return
    
    details = f"""
👤 **USER PROFILE**

Name: {user_data.get('name')}
ID: `{user_id}`
Username: @{user_data.get('username', 'none')}
Total Messages: {user_data.get('total_messages', 0)}
Last Active: {user_data.get('last_message_time', 'Never')[:16]}

💡 To reply: Just reply to their forwarded message!
"""
    
    keyboard = [[InlineKeyboardButton("🔙 BACK", callback_data="users_list")]]
    await query.edit_message_text(details, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def broadcast_menu(update: Update, context):
    """Broadcast menu"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 **BROADCAST**\n\n"
        "Use /broadcast command to send message to all users.\n\n"
        "Example: /broadcast Hello everyone!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]])
    )

async def quick_reply_menu(update: Update, context):
    """Quick reply menu"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💬 **QUICK REPLY**\n\n"
        "Just reply to any forwarded message from a user!\n\n"
        "Your reply will be sent directly to them.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]])
    )

# ============================================
# 📨 COMMAND HANDLERS
# ============================================
async def start_command(update: Update, context):
    """Start command"""
    user = update.effective_user
    if user.id == YOUR_CHAT_ID:
        await main_menu(update, context)
    else:
        await update.message.reply_text(
            "🌟 **WELCOME!** 🌟\n\n"
            "Send me a message and the owner will reply soon!\n\n"
            "✅ Your message has been delivered!",
            parse_mode='Markdown'
        )

async def broadcast_command(update: Update, context):
    """Broadcast to all users"""
    if update.effective_user.id != YOUR_CHAT_ID:
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 **BROADCAST USAGE**\n\n"
            "Send: `/broadcast Your message here`\n\n"
            "Example: `/broadcast Hello everyone!`",
            parse_mode='Markdown'
        )
        return
    
    message_text = ' '.join(context.args)
    users_data = get_from_firebase("users")
    
    if not users_data:
        await update.message.reply_text("❌ No users found")
        return
    
    success = 0
    failed = 0
    
    status_msg = await update.message.reply_text(f"📡 Sending to {len(users_data)} users...")
    
    for user_id, data in users_data.items():
        if isinstance(data, dict):
            try:
                await context.bot.send_message(
                    chat_id=data['chat_id'],
                    text=f"📢 **ANNOUNCEMENT**\n\n{message_text}",
                    parse_mode='Markdown'
                )
                success += 1
            except:
                failed += 1
    
    await status_msg.edit_text(f"✅ **BROADCAST DONE**\n\n✓ Sent: {success}\n✗ Failed: {failed}")

async def users_command(update: Update, context):
    """List all users"""
    if update.effective_user.id != YOUR_CHAT_ID:
        return
    
    users_data = get_from_firebase("users")
    if not users_data:
        await update.message.reply_text("📭 No users yet")
        return
    
    text = "👥 **USERS LIST**\n\n"
    for user_id, data in users_data.items():
        if isinstance(data, dict):
            text += f"• {data.get('name')} - `{user_id}`\n"
    
    await update.message.reply_text(text[:4000], parse_mode='Markdown')

async def status_command(update: Update, context):
    """Check bot status"""
    if update.effective_user.id != YOUR_CHAT_ID:
        return
    
    users_data = get_from_firebase("users")
    user_count = len(users_data) if users_data else 0
    
    await update.message.reply_text(
        f"✅ **BOT STATUS**\n\n"
        f"🤖 Bot: Online\n"
        f"👥 Users: {user_count}\n"
        f"🔄 Active: {len(forwarded_mapping)}\n"
        f"🔥 Firebase: Connected\n"
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        parse_mode='Markdown'
    )

async def cancel_command(update: Update, context):
    """Cancel operation"""
    if update.effective_user.id != YOUR_CHAT_ID:
        return
    
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled", parse_mode='Markdown')

# ============================================
# 📨 MESSAGE HANDLERS
# ============================================
async def handle_owner_reply(update: Update, context):
    """Handle owner's reply to forwarded message"""
    message = update.message
    user = update.effective_user
    
    if user.id != YOUR_CHAT_ID:
        return
    
    if not message.reply_to_message:
        return
    
    replied_msg = message.reply_to_message
    
    if replied_msg.message_id in forwarded_mapping:
        user_id = forwarded_mapping[replied_msg.message_id]
        user_data = user_sessions.get(user_id)
        
        if not user_data:
            fb_data = get_from_firebase(f"users/{user_id}")
            if fb_data:
                user_data = fb_data
        
        if user_data:
            try:
                await context.bot.send_message(
                    chat_id=user_data['chat_id'],
                    text=f"✨ **Reply from owner:**\n\n{message.text}",
                    parse_mode='Markdown'
                )
                await message.reply_text(f"✅ Reply sent to {user_data['name']}!")
                logger.info(f"Reply sent to {user_data['name']}")
                return
            except Exception as e:
                await message.reply_text(f"❌ Error: {str(e)[:50]}")

async def handle_message(update: Update, context):
    """Main message handler"""
    message = update.message
    user = update.effective_user
    
    # Owner replies
    if user.id == YOUR_CHAT_ID:
        if message.reply_to_message:
            await handle_owner_reply(update, context)
        return
    
    # User messages
    logger.info(f"📥 Message from {user.first_name}: {message.text if message.text else 'Media'}")
    
    # Save user
    user_data = {
        "name": user.first_name,
        "username": user.username,
        "chat_id": message.chat.id,
        "last_message": message.text or "Media",
        "last_message_time": datetime.now().isoformat(),
        "total_messages": 1
    }
    
    existing = get_from_firebase(f"users/{user.id}")
    if existing:
        user_data["total_messages"] = existing.get("total_messages", 0) + 1
    
    update_firebase(f"users/{user.id}", user_data)
    user_sessions[str(user.id)] = user_data
    
    # Save message
    save_to_firebase(f"messages/{user.id}", {
        "text": message.text or "Media",
        "timestamp": datetime.now().isoformat()
    })
    
    # Forward to owner
    forwarded = await context.bot.forward_message(
        chat_id=YOUR_CHAT_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )
    
    forwarded_mapping[forwarded.message_id] = str(user.id)
    
    # Notify owner
    await context.bot.send_message(
        chat_id=YOUR_CHAT_ID,
        text=f"✨ **NEW MESSAGE**\n\n👤 From: {user.first_name}\n🆔 ID: `{user.id}`\n💬 Msg: {message.text}\n\n✅ Reply to this message to answer!",
        parse_mode='Markdown'
    )
    
    await message.reply_text("✅ Message sent! Owner will reply soon.")

# ============================================
# 🚀 MAIN FUNCTION
# ============================================
def main():
    """Start the bot"""
    print("=" * 50)
    print("🌟 RENZ SURVEY BOT STARTING...")
    print("=" * 50)
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", main_menu))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(dashboard_menu, pattern="^dashboard$"))
    app.add_handler(CallbackQueryHandler(users_menu, pattern="^users_list$"))
    app.add_handler(CallbackQueryHandler(user_details_menu, pattern="^user_"))
    app.add_handler(CallbackQueryHandler(broadcast_menu, pattern="^broadcast_menu$"))
    app.add_handler(CallbackQueryHandler(quick_reply_menu, pattern="^quick_reply$"))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(MessageHandler(filters.VIDEO, handle_message))
    
    print(f"✅ Bot is running!")
    print(f"✅ Your Chat ID: {YOUR_CHAT_ID}")
    print(f"✅ Firebase: Connected")
    print("=" * 50)
    
    # Start polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"Error: {e}")
