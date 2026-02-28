#!/usr/bin/env python3
"""
Manual notification trigger for escrow ES022826BX7V payment confirmation.
Uses direct Telegram HTTP API and Brevo email API.
"""
import asyncio
import aiohttp
import json
import os
import sys

sys.path.insert(0, '/app')
os.chdir('/app')

from dotenv import load_dotenv
load_dotenv('/app/.env', override=True)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

async def send_telegram_message(chat_id, text, reply_markup=None):
    """Send message via Telegram Bot API directly"""
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{TELEGRAM_API}/sendMessage", json=payload) as resp:
            data = await resp.json()
            if data.get("ok"):
                return True, "sent"
            else:
                return False, data.get("description", "Unknown error")

async def send_brevo_email(to_email, subject, html_content):
    """Send email via Brevo API directly"""
    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "sender": {"name": "Lockbay", "email": "hi@lockbay.io"},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.brevo.com/v3/smtp/email", headers=headers, json=payload) as resp:
            data = await resp.json()
            if resp.status in [200, 201]:
                return True, data.get("messageId", "sent")
            else:
                return False, str(data)

async def main():
    escrow_id = "ES022826BX7V"
    escrow_amount = 100.00
    buyer_fee = 5.00
    total_paid = escrow_amount + buyer_fee
    
    buyer_telegram_id = 5336660667
    buyer_username = "Technine1738"
    seller_telegram_id = 1046923090
    seller_username = "Donxlane"
    admin_id = 1531772316
    
    results = []
    
    # 1. BUYER - Payment Confirmed
    buyer_msg = (
        f"✅ Payment Confirmed\n\n"
        f"#{escrow_id[-8:]} • ${escrow_amount:.2f}\n"
        f"Paid: ${total_paid:.2f} (inc. ${buyer_fee:.2f} fee)\n"
        f"To: @{seller_username}\n\n"
        f"⏰ Awaiting seller (24h)\n"
        f"🔒 Funds secured"
    )
    ok, msg = await send_telegram_message(buyer_telegram_id, buyer_msg)
    results.append(f"{'✅' if ok else '❌'} Buyer @{buyer_username}: {msg}")
    
    # 2. SELLER - New escrow offer with accept/decline buttons
    seller_msg = (
        f"🔔 New Escrow Offer\n\n"
        f"#{escrow_id[-8:]} • ${escrow_amount:.2f}\n"
        f"From: @{buyer_username}\n"
        f"⏰ 24h delivery window\n\n"
        f"💰 Payment confirmed and secured in escrow.\n"
        f"Tap Accept to start the trade."
    )
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ Accept Trade", "callback_data": f"accept_escrow_{escrow_id}"}],
            [{"text": "❌ Decline", "callback_data": f"decline_escrow_{escrow_id}"}]
        ]
    }
    ok, msg = await send_telegram_message(seller_telegram_id, seller_msg, reply_markup)
    results.append(f"{'✅' if ok else '❌'} Seller @{seller_username}: {msg}")
    
    # 3. ADMIN - Telegram alert
    admin_msg = (
        f"💰 Payment Confirmed - Admin Alert\n\n"
        f"Escrow: {escrow_id}\n"
        f"Amount: ${escrow_amount:.2f}\n"
        f"Buyer: @{buyer_username} ({buyer_telegram_id})\n"
        f"Seller: @{seller_username} ({seller_telegram_id})\n"
        f"Payment: USDT-TRC20\n"
        f"TxHash: 7791b74e...d6cde3c9\n"
        f"Status: payment_confirmed (manual fix)\n\n"
        f"Note: DynoPay webhook bug fixed - reference_id fallback added."
    )
    ok, msg = await send_telegram_message(admin_id, admin_msg)
    results.append(f"{'✅' if ok else '❌'} Admin Telegram: {msg}")
    
    # 4. ADMIN EMAIL
    html = f"""
    <h2>💰 Payment Confirmed - Escrow {escrow_id}</h2>
    <table style="border-collapse:collapse;width:100%;max-width:500px;">
        <tr><td style="padding:8px;border:1px solid #ddd;"><strong>Escrow</strong></td><td style="padding:8px;border:1px solid #ddd;">{escrow_id}</td></tr>
        <tr><td style="padding:8px;border:1px solid #ddd;"><strong>Amount</strong></td><td style="padding:8px;border:1px solid #ddd;">${escrow_amount:.2f}</td></tr>
        <tr><td style="padding:8px;border:1px solid #ddd;"><strong>Buyer</strong></td><td style="padding:8px;border:1px solid #ddd;">@{buyer_username} ({buyer_telegram_id})</td></tr>
        <tr><td style="padding:8px;border:1px solid #ddd;"><strong>Seller</strong></td><td style="padding:8px;border:1px solid #ddd;">@{seller_username} ({seller_telegram_id})</td></tr>
        <tr><td style="padding:8px;border:1px solid #ddd;"><strong>Payment</strong></td><td style="padding:8px;border:1px solid #ddd;">USDT-TRC20</td></tr>
        <tr><td style="padding:8px;border:1px solid #ddd;"><strong>TxHash</strong></td><td style="padding:8px;border:1px solid #ddd;font-size:12px;">7791b74e765d7ae4745efba0a7b40d31c827df9d2d8a4a9c91e7e316d6cde3c9</td></tr>
        <tr><td style="padding:8px;border:1px solid #ddd;"><strong>Status</strong></td><td style="padding:8px;border:1px solid #ddd;">payment_confirmed</td></tr>
    </table>
    <p style="color:#666;margin-top:15px;"><em>Note: Manually confirmed after DynoPay webhook processing bug was fixed (missing reference_id + NoneType overpayment).</em></p>
    """
    ok, msg = await send_brevo_email("moxxcompany@gmail.com", f"💰 Payment Confirmed - {escrow_id}", html)
    results.append(f"{'✅' if ok else '❌'} Admin email: {msg}")
    
    # 5. Buyer email confirmation
    buyer_html = f"""
    <h2>✅ Payment Confirmed</h2>
    <p>Your payment for escrow <strong>{escrow_id}</strong> has been confirmed.</p>
    <table style="border-collapse:collapse;width:100%;max-width:400px;">
        <tr><td style="padding:6px;"><strong>Amount:</strong></td><td>${escrow_amount:.2f}</td></tr>
        <tr><td style="padding:6px;"><strong>Fee:</strong></td><td>${buyer_fee:.2f}</td></tr>
        <tr><td style="padding:6px;"><strong>Total Paid:</strong></td><td>${total_paid:.2f}</td></tr>
        <tr><td style="padding:6px;"><strong>Seller:</strong></td><td>@{seller_username}</td></tr>
    </table>
    <p>⏰ Awaiting seller acceptance (24h). Your funds are secured in escrow.</p>
    """
    ok, msg = await send_brevo_email("stefaniemiller606@gmail.com", f"✅ Payment Confirmed - {escrow_id}", buyer_html)
    results.append(f"{'✅' if ok else '❌'} Buyer email: {msg}")
    
    print("\n=== NOTIFICATION RESULTS ===")
    for r in results:
        print(r)

if __name__ == "__main__":
    asyncio.run(main())
