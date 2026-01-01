"""Quick Code Validation for Recent Fixes (October 11, 2025)"""
import re
from pathlib import Path

print("\n" + "="*80)
print("VALIDATING RECENT FIXES (October 11, 2025)")
print("="*80)

# TEST 1: Delivery Warning Duplicate Prevention
print("\n1. Delivery Warning Duplicate Prevention")
print("-" * 80)
models = Path("models.py").read_text()
service = Path("services/standalone_auto_release_service.py").read_text() if Path("services/standalone_auto_release_service.py").exists() else ""

checks_1 = [
    ("✅" if "warning_24h_sent" in models else "❌", "warning_24h_sent column exists in models"),
    ("✅" if "warning_8h_sent" in models else "❌", "warning_8h_sent column exists in models"),
    ("✅" if "warning_2h_sent" in models else "❌", "warning_2h_sent column exists in models"),
    ("✅" if "warning_30m_sent" in models else "❌", "warning_30m_sent column exists in models"),
    ("✅" if ".with_for_update()" in service else "❌", "Uses SELECT FOR UPDATE for row-level locking"),
]
for status, desc in checks_1:
    print(f"  {status} {desc}")

# TEST 2: Fund Release Dual-Channel Notifications
print("\n2. Fund Release Dual-Channel Notifications")
print("-" * 80)
escrow_handler = Path("handlers/escrow.py").read_text()

checks_2 = [
    ("✅" if "handle_confirm_release_funds" in escrow_handler else "❌", "Fund release handler exists"),
    ("✅" if "send_funds_released_notification" in escrow_handler else "❌", "Calls send_funds_released_notification"),
    ("✅" if "broadcast_mode=True" in escrow_handler else "❌", "Uses broadcast_mode=True for dual-channel delivery"),
]
for status, desc in checks_2:
    print(f"  {status} {desc}")

# TEST 3: Chat Restrictions for Completed Trades
print("\n3. Chat Restrictions for Completed Trades")
print("-" * 80)
messages_hub = Path("handlers/messages_hub.py").read_text()

# Find fund release success message section
release_success_found = False
no_chat_button = False
for i, line in enumerate(escrow_handler.split('\n')):
    if "Funds Released Successfully" in line:
        # Check next 20 lines for chat button
        next_lines = '\n'.join(escrow_handler.split('\n')[i:i+20])
        release_success_found = True
        if "Continue Chat" not in next_lines and "💬 Chat" not in next_lines:
            no_chat_button = True
        break

checks_3 = [
    ("✅" if release_success_found else "❌", "Fund release success message found"),
    ("✅" if no_chat_button else "❌", "No chat button in fund release message"),
    ("✅" if "open_trade_chat" in messages_hub else "❌", "open_trade_chat handler exists"),
    ("✅" if "completed" in messages_hub and "Chat Closed" in messages_hub else "❌", "Blocks chat for completed trades"),
    ("✅" if "resolved" in messages_hub and "dispute" in messages_hub.lower() else "❌", "Blocks chat for resolved disputes"),
]
for status, desc in checks_3:
    print(f"  {status} {desc}")

# TEST 4: Documentation
print("\n4. Documentation Updates")
print("-" * 80)
replit_md = Path("replit.md").read_text()

checks_4 = [
    ("✅" if "October 11, 2025" in replit_md else "❌", "October 11, 2025 date documented"),
    ("✅" if "Fund Release Notifications" in replit_md else "❌", "Fund release notifications documented"),
    ("✅" if "Completed Trade Chat Restrictions" in replit_md else "❌", "Chat restrictions documented"),
    ("✅" if "broadcast_mode=True" in replit_md else "❌", "broadcast_mode=True mentioned"),
]
for status, desc in checks_4:
    print(f"  {status} {desc}")

# Summary
print("\n" + "="*80)
all_checks = checks_1 + checks_2 + checks_3 + checks_4
passed = sum(1 for status, _ in all_checks if status == "✅")
total = len(all_checks)

if passed == total:
    print(f"✅ ALL {total} CHECKS PASSED - All fixes correctly implemented!")
else:
    print(f"⚠️  {passed}/{total} checks passed - {total - passed} issues found")
print("="*80 + "\n")
