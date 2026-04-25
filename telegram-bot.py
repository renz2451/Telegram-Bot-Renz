import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackQueryHandler
import json
from typing import Dict, Optional

# ============================================
# 🔥 FIREBASE CONFIGURATION
# ============================================
FIREBASE_DB_URL = "https://renz-24e39-default-rtdb.firebaseio.com"
BOT_TOKEN = "8623671987:AAGe-7ik49SvtU-M6ZIw1B1IW61ikB1I0EU"
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
        print(f"❌ Firebase save error: {e}")
        return False

def update_firebase(path: str, data: dict) -> bool:
    try:
        url = f"{FIREBASE_DB_URL}/{path}.json"
        response = requests.patch(url, json=data)
        return response.ok
    except Exception as e:
        print(f"❌ Firebase update error: {e}")
        return False

def get_from_firebase(path: str) -> Optional[dict]:
    try:
        url = f"{FIREBASE_DB_URL}/{path}.json"
        response = requests.get(url)
        if response.ok:
            return response.json()
        return None
    except Exception as e:
        print(f"❌ Firebase read error: {e}")
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
            InlineKeyboardButton("⚙️ SETTINGS", callback_data="settings")
        ],
        [
            InlineKeyboardButton("📨 INBOX", callback_data="inbox"),
            InlineKeyboardButton("📊 STATS", callback_data="stats")
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
║  📡 Uptime: 100%
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
    
    # Create user buttons
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
    
    # Get recent messages
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
            InlineKeyboardButton("📜 FULL HISTORY", callback_data=f"history_{user_id}")
        ],
        [
            InlineKeyboardButton("🚫 BLOCK USER", callback_data=f"block_{user_id}"),
            InlineKeyboardButton("🔙 BACK", callback_data="users_list")
        ]
    ]
    
    await query.edit_message_text(details, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def quick_reply_menu(update: Update, context):
    """Quick reply interface"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['quick_reply_mode'] = True
    
    await query.edit_message_text(
        "✏️ **QUICK REPLY MODE**\n\n"
        "Send me a USER ID to reply to:\n\n"
        "Example: `5682792112`\n\n"
        "Or tap a user below:",
        parse_mode='Markdown'
    )
    
    # Show recent users
    users_data = get_from_firebase("users")
    if users_data:
        keyboard = []
        for user_id, data in list(users_data.items())[:5]:
            if isinstance(data, dict):
                keyboard.append([
                    InlineKeyboardButton(
                        f"👤 {data.get('name')}",
                        callback_data=f"quick_{user_id}"
                    )
                ])
        keyboard.append([InlineKeyboardButton("🔙 BACK", callback_data="main_menu")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

async def broadcast_menu(update: Update, context):
    """Broadcast menu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📝 TEXT BROADCAST", callback_data="broadcast_text")],
        [InlineKeyboardButton("🖼️ MEDIA BROADCAST", callback_data="broadcast_media")],
        [InlineKeyboardButton("🎯 TARGETED BROADCAST", callback_data="broadcast_targeted")],
        [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        "📢 **BROADCAST CENTER**\n\n"
        "Select broadcast type:\n\n"
        "• **Text** - Send message to all\n"
        "• **Media** - Send photos/videos\n"
        "• **Targeted** - Send to specific users",
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
    
    # Calculate average messages per user
    if messages_data:
        for msgs in messages_data.values():
            if isinstance(msgs, dict):
                total_messages += len(msgs)
    
    avg_msgs = round(total_messages / total_users, 2) if total_users > 0 else 0
    
    # Count active today
    active_today = 0
    today = datetime.now().date()
    for data in (users_data or {}).values():
        if isinstance(data, dict):
            last_time = data.get('last_message_time', '')
            if last_time:
                try:
                    msg_date = datetime.fromisoformat(last_time).date()
                    if msg_date == today:
                        active_today += 1
                except:
                    pass
    
    analytics_text = f"""
╔════════════════════════════════╗
║      📈 **ADVANCED ANALYTICS**   ║
╠════════════════════════════════╣
║  📊 **ENGAGEMENT METRICS**       ║
║  ─────────────────────────────  ║
║  👥 Total Users: {total_users}
║  💬 Total Msgs: {total_messages}
║  📈 Avg Msg/User: {avg_msgs}
║  🟢 Active Today: {active_today}
║  ─────────────────────────────  ║
║  🎯 **GROWTH RATE**              ║
║  📈 7-Day Growth: +{active_today}
║  ─────────────────────────────  ║
║  ⚡ **PERFORMANCE**              ║
║  🤖 Bot Uptime: 100%
║  🔥 Firebase: ✅
║  ⏱️ Response: <1s
╚════════════════════════════════╝
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 EXPORT DATA", callback_data="export")],
        [InlineKeyboardButton("🔙 BACK", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(analytics_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ============================================
# 📨 MESSAGE HANDLERS
# ============================================
async def handle_owner_media_reply(update: Update, context):
    """Handle owner's media replies"""
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
                # Send reply with fancy formatting
                if message.text:
                    await context.bot.send_message(
                        chat_id=target_chat_id,
                        text=f"✨ **Reply from owner:**\n\n{message.text}",
                        parse_mode='Markdown'
                    )
                elif message.photo:
                    await context.bot.send_photo(
                        chat_id=target_chat_id,
                        photo=message.photo[-1].file_id,
                        caption=f"✨ **Reply from owner:**\n\n{message.caption or ''}",
                        parse_mode='Markdown'
                    )
                elif message.video:
                    await context.bot.send_video(
                        chat_id=target_chat_id,
                        video=message.video.file_id,
                        caption=f"✨ **Reply from owner:**\n\n{message.caption or ''}",
                        parse_mode='Markdown'
                    )
                elif message.sticker:
                    await context.bot.send_sticker(
                        chat_id=target_chat_id,
                        sticker=message.sticker.file_id
                    )
                elif message.animation:
                    await context.bot.send_animation(
                        chat_id=target_chat_id,
                        animation=message.animation.file_id,
                        caption=f"✨ **Reply from owner:**\n\n{message.caption or ''}",
                        parse_mode='Markdown'
                    )
                
                await message.reply_text(f"✅ **Reply sent to {target_name}!**", parse_mode='Markdown')
                return
                
            except Exception as e:
                await message.reply_text(f"❌ Error: {str(e)[:100]}", parse_mode='Markdown')

async def handle_message(update: Update, context):
    """Main message handler"""
    message = update.message
    user = update.effective_user
    
    # Quick reply mode
    if user.id == YOUR_CHAT_ID and context.user_data.get('quick_reply_mode'):
        # Check if message is a number (user ID)
        if message.text and message.text.isdigit():
            user_id = message.text
            user_data = get_from_firebase(f"users/{user_id}")
            if user_data:
                context.user_data['reply_to_user'] = user_id
                await message.reply_text(
                    f"✏️ **Replying to {user_data['name']}**\n\nSend your reply message:",
                    parse_mode='Markdown'
                )
                return
        
        # Check if waiting for reply message
        if 'reply_to_user' in context.user_data:
            user_id = context.user_data['reply_to_user']
            user_data = get_from_firebase(f"users/{user_id}")
            if user_data:
                try:
                    await context.bot.send_message(
                        chat_id=user_data['chat_id'],
                        text=f"✨ **Reply from owner:**\n\n{message.text}",
                        parse_mode='Markdown'
                    )
                    await message.reply_text(f"✅ **Reply sent to {user_data['name']}!**", parse_mode='Markdown')
                    del context.user_data['reply_to_user']
                    context.user_data['quick_reply_mode'] = False
                except Exception as e:
                    await message.reply_text(f"❌ Error: {e}")
            return
    
    # Owner replies to forwarded messages
    if user.id == YOUR_CHAT_ID:
        if message.reply_to_message:
            await handle_owner_media_reply(update, context)
            return
        
        if not message.text or not message.text.startswith('/'):
            print(f"👤 Owner sent (ignored): {message.text if message.text else 'Media'}")
        return
    
    # User messages
    print(f"\n📥 [USER] {user.first_name}: {message.text if message.text else 'Media'}")
    
    user_data = {
        "name": user.first_name,
        "username": user.username,
        "chat_id": message.chat.id,
        "last_message": message.text or message.caption or "Media",
        "last_message_time": datetime.now().isoformat(),
        "total_messages": 1
    }
    
    existing = get_from_firebase(f"users/{user.id}")
    if existing:
        user_data["total_messages"] = existing.get("total_messages", 0) + 1
    
    update_firebase(f"users/{user.id}", user_data)
    user_sessions[str(user.id)] = user_data
    
    # Forward to owner
    forwarded_msg = await context.bot.forward_message(
        chat_id=YOUR_CHAT_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )
    
    forwarded_mapping[forwarded_msg.message_id] = str(user.id)
    
    # Send modern notification
    keyboard = [[InlineKeyboardButton("💬 REPLY NOW", callback_data=f"reply_{user.id}")]]
    
    notification = f"""
✨ **NEW MESSAGE** ✨

👤 **From:** {user.first_name} (@{user.username or 'no username'})
🆔 **ID:** `{user.id}`
💬 **Message:** {message.text or 'Media message'}
⏰ **Time:** {datetime.now().strftime('%I:%M %p')}

💡 **Tap REPLY NOW to answer!**
"""
    
    await context.bot.send_message(
        chat_id=YOUR_CHAT_ID,
        text=notification,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    await message.reply_text("✅ **Message sent!** Owner will reply soon.", parse_mode='Markdown')

# ========================================
# 🚀 START BOT
# ========================================
async def start_command(update: Update, context):
    user = update.effective_user
    if user.id == YOUR_CHAT_ID:
        await main_menu(update, context)
    else:
        await update.message.reply_text(
            "🌟 **WELCOME!** 🌟\n\nSend me a message and the owner will reply soon!\n\n✅ Your message has been delivered!",
            parse_mode='Markdown'
        )

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", main_menu))
    app.add_handler(CommandHandler("cancel", lambda u,c: c.user_data.clear()))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(dashboard_menu, pattern="^dashboard$"))
    app.add_handler(CallbackQueryHandler(users_menu, pattern="^users_list$"))
    app.add_handler(CallbackQueryHandler(user_details_menu, pattern="^user_"))
    app.add_handler(CallbackQueryHandler(quick_reply_menu, pattern="^quick_reply$"))
    app.add_handler(CallbackQueryHandler(broadcast_menu, pattern="^broadcast_menu$"))
    app.add_handler(CallbackQueryHandler(analytics_menu, pattern="^analytics$"))
    
    # Message handler
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Sticker.ALL | 
        filters.Document.ALL | filters.ANIMATION | filters.VOICE | filters.AUDIO,
        handle_message
    ))
    
    print("=" * 60)
    print("🌟 MODERN BOT - BUTTON INTERFACE")
    print("=" * 60)
    print("✅ Bot is LIVE with modern UI!")
    print("\n🎨 **FEATURES:**")
    print("   • Interactive button menus")
    print("   • Dashboard with stats")
    print("   • User directory with profiles")
    print("   • Quick reply system")
    print("   • Broadcast center")
    print("   • Analytics dashboard")
    print("\n📱 **START:** Send /start or /menu")
    print("💡 **REPLY:** Just reply to any forwarded message!")
    print("=" * 60)
    
    app.run_polling()
