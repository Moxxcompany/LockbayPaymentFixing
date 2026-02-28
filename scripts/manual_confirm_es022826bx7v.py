#!/usr/bin/env python3
"""
Manual notification trigger for escrow ES022826BX7V payment confirmation.
Sends notifications to: buyer, seller, admin, and group.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, '/app')
os.chdir('/app')

from dotenv import load_dotenv
load_dotenv('/app/.env', override=True)

async def send_notifications():
    from decimal import Decimal
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
    from config import Config
    
    bot_token = Config.TELEGRAM_BOT_TOKEN
    bot = Bot(token=bot_token)
    
    # Escrow details
    escrow_id = "ES022826BX7V"
    escrow_amount = Decimal("100.00")
    buyer_fee = Decimal("5.00")
    total_paid = escrow_amount + buyer_fee
    
    buyer_telegram_id = 5336660667
    buyer_username = "Technine1738"
    seller_telegram_id = 1046923090
    seller_username = "Donxlane"
    admin_ids = [1531772316]
    
    results = []
    
    # 1. BUYER NOTIFICATION - Payment Confirmed
    try:
        buyer_message = f"""✅ Payment Confirmed

#{escrow_id[-8:]} • ${float(escrow_amount):.2f}
Paid: ${float(total_paid):.2f} (inc. ${float(buyer_fee):.2f} fee)
To: @{seller_username}

⏰ Awaiting seller (24h)
🔒 Funds secured"""
        
        await bot.send_message(
            chat_id=buyer_telegram_id,
            text=buyer_message,
            parse_mode=None
        )
        results.append(f"✅ Buyer notification sent to @{buyer_username}")
    except Exception as e:
        results.append(f"❌ Buyer notification failed: {e}")
    
    # 2. SELLER NOTIFICATION - New escrow offer
    try:
        seller_message = f"""🔔 New Escrow Offer

#{escrow_id[-8:]} • ${float(escrow_amount):.2f}
From: @{buyer_username}
⏰ 24h delivery window

💰 Payment confirmed and secured in escrow.
Tap Accept to start the trade.

/start to manage your trades"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Accept Trade", callback_data=f"accept_escrow_{escrow_id}")],
            [InlineKeyboardButton("❌ Decline", callback_data=f"decline_escrow_{escrow_id}")]
        ])
        
        await bot.send_message(
            chat_id=seller_telegram_id,
            text=seller_message,
            reply_markup=keyboard,
            parse_mode=None
        )
        results.append(f"✅ Seller notification sent to @{seller_username}")
    except Exception as e:
        results.append(f"❌ Seller notification failed: {e}")
    
    # 3. ADMIN NOTIFICATION - Payment confirmed
    try:
        admin_message = f"""💰 Payment Confirmed - Admin Alert

Escrow: {escrow_id}
Amount: ${float(escrow_amount):.2f}
Buyer: @{buyer_username} ({buyer_telegram_id})
Seller: @{seller_username} ({seller_telegram_id})
Payment: USDT-TRC20
TxHash: 7791b74e...d6cde3c9
Status: payment_confirmed (manual update)"""
        
        for admin_id in admin_ids:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode=None
            )
        results.append(f"✅ Admin notification sent")
    except Exception as e:
        results.append(f"❌ Admin notification failed: {e}")
    
    # 4. ADMIN EMAIL NOTIFICATION
    try:
        from services.email import email_service
        email_result = await email_service.send_email(
            to_email="moxxcompany@gmail.com",
            subject=f"💰 Payment Confirmed - Escrow {escrow_id}",
            html_content=f"""
            <h2>Payment Confirmed</h2>
            <p><strong>Escrow:</strong> {escrow_id}</p>
            <p><strong>Amount:</strong> ${float(escrow_amount):.2f}</p>
            <p><strong>Buyer:</strong> @{buyer_username} ({buyer_telegram_id})</p>
            <p><strong>Seller:</strong> @{seller_username} ({seller_telegram_id})</p>
            <p><strong>Payment:</strong> USDT-TRC20</p>
            <p><strong>TxHash:</strong> 7791b74e765d7ae4745efba0a7b40d31c827df9d2d8a4a9c91e7e316d6cde3c9</p>
            <p><strong>Status:</strong> payment_confirmed</p>
            <p><em>Note: This was manually confirmed after DynoPay webhook processing bug was fixed.</em></p>
            """
        )
        results.append(f"✅ Admin email sent: {email_result}")
    except Exception as e:
        results.append(f"❌ Admin email failed: {e}")
    
    # 5. GROUP BROADCAST - Trade funded
    try:
        from services.group_event_service import group_event_service
        payment_data = {
            'escrow_id': escrow_id,
            'amount': float(escrow_amount),
            'payment_method': 'crypto',
            'buyer_info': f"@{buyer_username}",
            'seller_info': f"@{seller_username}"
        }
        await group_event_service.broadcast_trade_funded(payment_data)
        results.append(f"✅ Group broadcast sent")
    except Exception as e:
        results.append(f"❌ Group broadcast failed: {e}")
    
    print("\n=== NOTIFICATION RESULTS ===")
    for r in results:
        print(r)

if __name__ == "__main__":
    asyncio.run(send_notifications())
