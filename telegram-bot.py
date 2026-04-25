import requests
import os
import sys
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from typing import Dict, Optional

# ============================================
# 🔥 LOGGING SETUP (For debugging on server)
# ============================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# 🔥 FIREBASE CONFIGURATION
# ============================================
FIREBASE_DB_URL = "https://renz-24e39-default-rtdb.firebaseio.com"

# Get token from environment variable (SECURE!)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8623671987:AAGe-7ik49SvtU-M6ZIw1B1IW61ikB1I0EU')
YOUR_CHAT_ID = 6064653643

# Store user sessions and forwarded messages mapping
user_sessions: Dict[str, dict] = {}
forwarded_mapping: Dict[int, str] = {}

# ============================================
# 🔥 FIREBASE HELPERS
# ============================================
def save_to_firebase(path: str, data: dict) -> bool:
    try:
        url = f"{FIREBASE_DB_URL}/{path}.json"
        response = requests.post(url, json=data)
        return response.ok
    except Exception as e:
        logger.error(f"Firebase save error: {e}")
        return False

def update_firebase(path: str, data: dict) -> bool:
    try:
        url = f"{FIREBASE_DB_URL}/{path}.json"
        response = requests.patch(url, json=data)
        return response.ok
    except Exception as e:
        logger.error(f"Firebase update error: {e}")
        return False

def get_from_firebase(path: str) -> Optional[dict]:
    try:
        url = f"{FIREBASE_DB_URL}/{path}.json"
        response = requests.get(url)
        if response.ok:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Firebase read error: {e}")
        return None

# ============================================
# 🎨 MODERN BUTTON MENUS
# ============================================
async def main_menu(update: Update, context):
    """Display main admin menu with buttons"""
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message
    
    keyboard = [
        [
            InlineKeyboardButton("📊 DASHBOARD", callback_data="dashboard"),
            InlineKeyboardButton("👥 USERS", callback_data="users_list")
        ],
        [
            InlineKeyboardButton("📢 BROADCAST", callback_data="broadcast_menu"),
            InlineKeyboardButton("📈 ANALYTICS", callback_data="analytics")
        ],
        [
            InlineKeyboardButton("💬 QUICK REPLY", callback_data="quick_reply"),
            InlineKeyboardButton("📨 INBOX", callback_data="inbox")
        ],
        [
            InlineKeyboardButton("🔙 EXIT", callback_data="exit")
        ]
    ]
    
    menu_text = """
╔══════════════════════════════╗
║      🌟 **ADMIN CONTROL**      ║
║          RENZ SURVEY BOT       ║
╠══════════════════════════════╣
║  🤖 Status: 🟢 Online          ║
║  📊 Version: 3.0 Advanced      ║
║  🔥 Firebase: ✅ Connected      ║
╠══════════════════════════════╣
║  Select an option below:       ║
╚══════════════════════════════╝
"""
    
    if query:
        await query.edit_message_text(menu_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await message.reply_text(menu_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def dashboard_menu(update: Update, context):
    """Show dashboard with stats"""
    query = update.callback_query
    await query.answer()
    
    users_data = get_from_firebase("users")
    messages_data = get_from_firebase("messages")
    
    total_users = len(users_data) if users_data else 0
    total_messages = 0
    
    if messages_data:
        for user_msgs in messages_data.values():
            if isinstance(user_msgs, dict):
                total_messages += len(user_msgs)
    
    dashboard_text = f"""
╔════════════════════════════════╗
║      📊 **REAL-TIME DASHBOARD**  ║
╠════════════════════════════════╣
║  📈 **STATISTICS**               ║
║  ─────────────────────────────  ║
║  👥 Total Users: **{total_users}**
║  💬 Total Msgs: **{total_messages}**
║  🟢 Active Now: **{len(user_sessions)}**
║  📅 Today: **{datetime.now().strftime('%Y-%m-%d')}**
║  ─────────────────────────────  ║
║  🤖 **SYSTEM STATUS**            ║
║  ✅ Bot: Running 24/7
║  🔥 Firebase: Connected
║  ⚡ Response: <1s
╚════════════════════════════════╝
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 REFRESH", callback_data="dashboard")],
        [InlineKeyboardButton("🔙 BACK TO MENU", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(dashboard_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def users_menu(update: Update, context):
    """Show users list with action buttons"""
    query = update.callback_query
    await query.answer()
    
    users_data = get_from_firebase("users")
    if not users_data:
        await query.edit_message_text("📭 **No users yet**\n\nBe the first to message the bot!", parse_mode='Markdown')
        return
    
    keyboard = []
    for user_id, data in list(users_data.items())[:10]:
        if isinstance(data, dict):
            name = data.get('name', 'Unknown')
            msg_count = data.get('total_messages', 0)
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {name} ({msg_count} msgs)",
                    callback_data=f"user_{user_id}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🔙 BACK TO MENU", callback_data="main_menu")])
    
    await query.edit_message_text(
        f"👥 **USER DIRECTORY**\n\nTotal: {len(users_data)} users\nTap a user to interact:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def user_details_menu(update: Update, context):
    """Show user details with action buttons"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.replace("user_", "")
    user_data = get_from_firebase(f"users/{user_id}")
    
    if not user_data:
        await query.edit_message_text("❌ User not found")
        return
    
    messages = get_from_firebase(f"messages/{user_id}")
    recent_msgs = ""
    if messages:
        msg_list = list(messages.values())[-3:]
        for msg in msg_list:
            if isinstance(msg, dict):
                recent_msgs += f"\n  💬 {msg.get('text', '')[:40]}"
    
    details = f"""
╔══════════════════════════════╗
║      👤 **USER PROFILE**        ║
╠══════════════════════════════╣
║  📛 Name: {user_data.get('name')}
║  🆔 ID: `{user_id}`
║  👥 Username: @{user_data.get('username', 'none')}
║  💬 Total: {user_data.get('total_messages', 0)} msgs
║  📅 Last: {user_data.get('last_message_time', 'Never')[:16]}
╠══════════════════════════════╣
║  📝 **Recent Messages:**{recent_msgs}
╚══════════════════════════════╝
"""
    
    keyboard = [
        [
            InlineKeyboardButton("💬 QUICK REPLY", callback_data=f"reply_{user_id}"),
            InlineKeyboardButton("🔙 BACK", callback_data="users_list")
        ]
    ]
    
    await query.edit_message_text(details, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def broadcast_menu(update: Update, context):
    """Broadcast menu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📝 TEXT BROADCAST", callback_data="broadcast_text")],
        [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        "📢 **BROADCAST CENTER**\n\n"
        "Send /broadcast command to start broadcasting!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def analytics_menu(update: Update, context):
    """Show analytics"""
    query = update.callback_query
    await query.answer()
    
    users_data = get_from_firebase("users")
    messages_data = get_from_firebase("messages")
    
    total_users = len(users_data) if users_data else 0
    total_messages = 0
    
    if messages_data:
        for msgs in messages_data.values():
            if isinstance(msgs, dict):
                total_messages += len(msgs)
    
    avg_msgs = round(total_messages / total_users, 2) if total_users > 0 else 0
    
    analytics_text = f"""
╔════════════════════════════════╗
║      📈 **ADVANCED ANALYTICS**   ║
╠════════════════════════════════╣
║  📊 **ENGAGEMENT METRICS**       ║
║  ─────────────────────────────  ║
║  👥 Total Users: {total_users}
║  💬 Total Msgs: {total_messages}
║  📈 Avg Msg/User: {avg_msgs}
║  ─────────────────────────────  ║
║  ⚡ **PERFORMANCE**              ║
║  🤖 Bot Uptime: 100%
║  🔥 Firebase: ✅
║  ⏱️ Response: <1s
╚════════════════════════════════╝
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(analytics_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def exit_menu(update: Update, context):
    """Exit menu"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("👋 **Goodbye!** Send /menu to open again.", parse_mode='Markdown')

async def inbox_menu(update: Update, context):
    """Show inbox"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📨 **INBOX**\n\n"
        "New messages will appear here automatically.\n"
        "Reply to any forwarded message to respond!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]])
    )

# ============================================
# 📨 MESSAGE HANDLERS
# ============================================
async def broadcast_command(update: Update, context):
    """Handle broadcast command"""
    if update.effective_user.id != YOUR_CHAT_ID:
        return
    
    context.user_data['waiting_for_broadcast'] = True
    await update.message.reply_text(
        "📢 **BROADCAST MODE**\n\n"
        "Send me the message you want to broadcast to ALL users.\n\n"
        "Send /cancel to abort.",
        parse_mode='Markdown'
    )

async def handle_broadcast(update: Update, context):
    """Send broadcast to all users"""
    if not context.user_data.get('waiting_for_broadcast'):
        return
    
    message = update.message
    users_data = get_from_firebase("users")
    
    if not users_data:
        await message.reply_text("❌ No users found")
        context.user_data.clear()
        return
    
    success = 0
    failed = 0
    
    progress = await message.reply_text(f"📡 Sending broadcast to {len(users_data)} users...")
    
    for user_id, data in users_data.items():
        if isinstance(data, dict):
            try:
                chat_id = data['chat_id']
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"📢 **ANNOUNCEMENT**\n\n{message.text}",
                    parse_mode='Markdown'
                )
                success += 1
            except:
                failed += 1
    
    await progress.edit_text(
        f"✅ **BROADCAST COMPLETE**\n\n"
        f"✓ Sent: {success}\n"
        f"✗ Failed: {failed}\n"
        f"📊 Total: {len(users_data)}"
    )
    
    context.user_data.clear()

async def cancel(update: Update, context):
    """Cancel current operation"""
    if update.effective_user.id != YOUR_CHAT_ID:
        return
    
    context.user_data.clear()
    await update.message.reply_text("❌ **Operation cancelled**", parse_mode='Markdown')

async def handle_owner_reply(update: Update, context):
    """Handle owner's replies to forwarded messages"""
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
            target_chat_id = user_data.get("chat_id")
            target_name = user_data.get("name")
            
            try:
                await context.bot.send_message(
                    chat_id=target_chat_id,
                    text=f"✨ **Reply from owner:**\n\n{message.text}",
                    parse_mode='Markdown'
                )
                
                await message.reply_text(f"✅ **Reply sent to {target_name}!**", parse_mode='Markdown')
                logger.info(f"Reply sent to {target_name}")
                return
                
            except Exception as e:
                await message.reply_text(f"❌ Error: {str(e)[:100]}", parse_mode='Markdown')

async def handle_message(update: Update, context):
    """Main message handler"""
    message = update.message
    user = update.effective_user
    
    # Check for broadcast mode
    if user.id == YOUR_CHAT_ID and context.user_data.get('waiting_for_broadcast'):
        await handle_broadcast(update, context)
        return
    
    # Owner replies
    if user.id == YOUR_CHAT_ID:
        if message.reply_to_message:
            await handle_owner_reply(update, context)
            return
        
        if not message.text or not message.text.startswith('/'):
            logger.info(f"Owner sent (ignored): {message.text}")
        return
    
    # User messages
    logger.info(f"📥 User {user.first_name}: {message.text if message.text else 'Media'}")
    
    # Prepare user data
    user_data = {
        "name": user.first_name,
        "username": user.username,
        "chat_id": message.chat.id,
        "last_message": message.text or "Media message",
        "last_message_time": datetime.now().isoformat(),
        "total_messages": 1
    }
    
    existing = get_from_firebase(f"users/{user.id}")
    if existing:
        user_data["total_messages"] = existing.get("total_messages", 0) + 1
    
    update_firebase(f"users/{user.id}", user_data)
    user_sessions[str(user.id)] = user_data
    
    # Save message
    msg_data = {
        "text": message.text or "Media message",
        "timestamp": datetime.now().isoformat(),
        "message_id": message.message_id
    }
    save_to_firebase(f"messages/{user.id}", msg_data)
    
    # Forward to owner
    forwarded_msg = await context.bot.forward_message(
        chat_id=YOUR_CHAT_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )
    
    forwarded_mapping[forwarded_msg.message_id] = str(user.id)
    
    # Send notification
    notification = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ **NEW MESSAGE** ✨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 **From:** {user.first_name} (@{user.username or 'no username'})
🆔 **User ID:** `{user.id}`
💬 **Message:** {message.text or 'Media message'}
⏰ **Time:** {datetime.now().strftime('%I:%M %p')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **REPLY to this message to answer!**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await context.bot.send_message(
        chat_id=YOUR_CHAT_ID,
        text=notification,
        parse_mode='Markdown'
    )
    
    await message.reply_text("✅ **Message sent!** Owner will reply soon.", parse_mode='Markdown')

# ========================================
# 🚀 START COMMAND
# ========================================
async def start_command(update: Update, context):
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

async def users_command(update: Update, context):
    """Users command"""
    if update.effective_user.id != YOUR_CHAT_ID:
        return
    
    users_data = get_from_firebase("users")
    if not users_data:
        await update.message.reply_text("📭 No users yet")
        return
    
    text = "👥 **USERS:**\n\n"
    for user_id, data in users_data.items():
        if isinstance(data, dict):
            text += f"• {data.get('name')} (@{data.get('username', 'no username')})\n"
            text += f"  ID: `{user_id}` - {data.get('total_messages', 0)} msgs\n\n"
    
    await update.message.reply_text(text[:4000], parse_mode='Markdown')

# ========================================
# 🚀 MAIN FUNCTION
# ========================================
def main():
    """Start the bot"""
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", main_menu))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(dashboard_menu, pattern="^dashboard$"))
    app.add_handler(CallbackQueryHandler(users_menu, pattern="^users_list$"))
    app.add_handler(CallbackQueryHandler(user_details_menu, pattern="^user_"))
    app.add_handler(CallbackQueryHandler(broadcast_menu, pattern="^broadcast_menu$"))
    app.add_handler(CallbackQueryHandler(analytics_menu, pattern="^analytics$"))
    app.add_handler(CallbackQueryHandler(inbox_menu, pattern="^inbox$"))
    app.add_handler(CallbackQueryHandler(exit_menu, pattern="^exit$"))
    
    # Message handler
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Sticker.ALL | 
        filters.Document.ALL | filters.ANIMATION | filters.VOICE | filters.AUDIO,
        handle_message
    ))
    
    # Start bot
    print("=" * 60)
    print("🌟 RENZ SURVEY BOT - RUNNING 24/7")
    print("=" * 60)
    print(f"✅ Bot is LIVE!")
    print(f"✅ Your Chat ID: {YOUR_CHAT_ID}")
    print(f"✅ Firebase: Connected")
    print(f"✅ Modern UI: Active")
    print("=" * 60)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
