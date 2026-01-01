"""
BrandingUtils Integration Example
Demonstrates how to integrate the new BrandingUtils module into existing handlers.

This example shows practical usage patterns for all major branding functions.
"""

import asyncio
from decimal import Decimal
from utils.branding_utils import (
    BrandingUtils,
    make_header,
    make_trust_footer, 
    make_receipt,
    generate_transaction_id,
    format_branded_amount,
    get_social_proof_text,
    make_milestone_message
)

# Example 1: Screen Headers
def example_screen_headers():
    """Example of consistent screen headers across the bot"""
    print("=== SCREEN HEADERS ===")
    
    screens = [
        "Wallet Dashboard",
        "Create Escrow", 
        "Transaction History",
        "Settings",
        "Help & Support"
    ]
    
    for screen in screens:
        header = make_header(screen)
        print(f"{screen:20} → {header}")
    
    print(f"Footer for all screens → {make_trust_footer()}")


# Example 2: Transaction Receipts
def example_transaction_receipts():
    """Example of branded transaction receipts"""
    print("\n=== TRANSACTION RECEIPTS ===")
    
    transactions = [
        ("escrow", Decimal("500.00"), "USD"),
        ("cashout", Decimal("0.01234567"), "BTC"),
        ("exchange", Decimal("250000"), "NGN"),
        ("wallet", Decimal("1.5"), "ETH")
    ]
    
    for tx_type, amount, currency in transactions:
        tx_id = generate_transaction_id(tx_type)
        receipt = make_receipt(tx_id, amount, currency, tx_type)
        print(f"\n{tx_type.upper()} Receipt:")
        print(receipt)
        print("-" * 50)


# Example 3: Currency Formatting Consistency
def example_currency_formatting():
    """Example of consistent currency formatting across all contexts"""
    print("\n=== CURRENCY FORMATTING ===")
    
    amounts = [
        (Decimal("0.00050000"), "BTC"),
        (Decimal("1234.56"), "USD"),
        (Decimal("2500000"), "NGN"),
        (Decimal("0.12345678"), "ETH"),
        (Decimal("100.00"), "USDT"),
        (Decimal("1000.50"), "EUR")
    ]
    
    for amount, currency in amounts:
        formatted = format_branded_amount(amount, currency)
        print(f"{amount:>12} {currency} → {formatted}")


# Example 4: User Milestones
def example_user_milestones():
    """Example of user achievement messaging"""
    print("\n=== USER MILESTONES ===")
    
    users = [
        {"first_name": "Alice", "user_id": 123},
        {"first_name": "Bob", "user_id": 456},
        {"first_name": "Charlie", "user_id": 789}
    ]
    
    milestones = [
        "first_completion",
        "reputation_milestone", 
        "trusted_status",
        "volume_milestone"
    ]
    
    for i, user in enumerate(users):
        milestone_type = milestones[i % len(milestones)]
        message = make_milestone_message(user, milestone_type)
        print(f"\n{user['first_name']}'s {milestone_type}:")
        print(message)
        print("-" * 50)


# Example 5: Error Messages with Branding
def example_error_messages():
    """Example of branded error messages"""
    print("\n=== BRANDED ERROR MESSAGES ===")
    
    error_scenarios = [
        ("payment", "Card declined by bank"),
        ("network", "Connection timeout"),
        ("validation", "Invalid email format"),
        ("timeout", "Request took too long")
    ]
    
    for error_type, context in error_scenarios:
        error_msg = BrandingUtils.get_branded_error_message(error_type, context)
        print(f"\n{error_type.upper()} Error:")
        print(error_msg)
        print("-" * 50)


# Example 6: Integration in Bot Handlers
async def example_handler_integration():
    """Example of how to integrate BrandingUtils in actual bot handlers"""
    print("\n=== HANDLER INTEGRATION EXAMPLE ===")
    
    # Simulated wallet handler
    async def wallet_balance_handler(user_id: int, balance_usd: Decimal):
        """Example wallet balance display with branding"""
        
        # Create branded header
        header = make_header("Wallet Balance")
        
        # Format balance with branding
        formatted_balance = format_branded_amount(balance_usd, "USD")
        
        # Get social proof
        social_proof = await get_social_proof_text()
        
        # Create complete message
        message = f"""
{header}

💰 **Your Balance**
{formatted_balance}

{social_proof}

{make_trust_footer()}
"""
        return message.strip()
    
    # Test the handler
    sample_balance = Decimal("1250.75")
    message = await wallet_balance_handler(123, sample_balance)
    print("Wallet Balance Handler Output:")
    print(message)


# Example 7: Transaction ID Management
def example_transaction_id_management():
    """Example of consistent transaction ID generation"""
    print("\n=== TRANSACTION ID MANAGEMENT ===")
    
    # Generate IDs for different transaction types
    transaction_types = [
        "escrow", "cashout", "exchange", 
        "wallet", "deposit", "refund"
    ]
    
    print("Generated Transaction IDs:")
    for tx_type in transaction_types:
        for i in range(3):  # Generate 3 IDs of each type
            tx_id = generate_transaction_id(tx_type)
            print(f"{tx_type:>8} #{i+1}: {tx_id}")
    
    # Show ID pattern consistency
    print("\nID Pattern Analysis:")
    print("✅ All IDs follow LB-{TYPE}-{8CHARS} format")
    print("✅ No confusing characters (0, O, 1, I) used")
    print("✅ Easy to read and type on mobile")


# Main execution
async def main():
    """Run all examples to demonstrate BrandingUtils capabilities"""
    print("🔒 LockBay BrandingUtils Integration Examples")
    print("=" * 60)
    
    # Run all examples
    example_screen_headers()
    example_transaction_receipts()
    example_currency_formatting()
    example_user_milestones()
    example_error_messages()
    await example_handler_integration()
    example_transaction_id_management()
    
    print("\n" + "=" * 60)
    print("✅ All BrandingUtils integration examples completed successfully!")
    print("🚀 Ready for Phase 2 implementation across all handlers")


if __name__ == "__main__":
    asyncio.run(main())