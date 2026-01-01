# Telegram Escrow Bot - API Documentation

## Overview

This document provides comprehensive API documentation for the Telegram Escrow Bot system, including internal APIs, webhook endpoints, health monitoring endpoints, and integration interfaces.

## Table of Contents

1. [Health Check Endpoints](#health-check-endpoints)
2. [Webhook Endpoints](#webhook-endpoints)
3. [Internal API Services](#internal-api-services)
4. [Database API](#database-api)
5. [External Service Integrations](#external-service-integrations)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Authentication & Authorization](#authentication--authorization)

---

## Health Check Endpoints

### GET /health
Returns comprehensive system health status.

**Response Format:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2025-01-04T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 45,
      "details": "Connection successful"
    },
    "memory": {
      "status": "healthy",
      "usage_percent": 65.4,
      "available_mb": 1024
    },
    "disk": {
      "status": "healthy", 
      "usage_percent": 78.2,
      "free_gb": 8.5
    },
    "scheduler": {
      "status": "healthy",
      "active_jobs": 6,
      "next_job": "2025-01-04T10:35:00Z"
    }
  }
}
```

### GET /ping
Simple availability check.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-04T10:30:00Z"
}
```

### GET /sysinfo
Detailed system information.

**Response Format:**
```json
{
  "system": {
    "platform": "linux",
    "python_version": "3.11.0",
    "uptime_hours": 48.5
  },
  "application": {
    "version": "1.0.0",
    "environment": "production",
    "features_enabled": ["rate_limiting", "caching", "monitoring"]
  },
  "resources": {
    "cpu_percent": 12.5,
    "memory_usage_mb": 245,
    "disk_usage_gb": 15.2
  }
}
```

---

## Internal API Services

### Escrow Service API

#### Create Escrow
```python
async def create_escrow(
    buyer_id: str,
    seller_username: str, 
    amount: Decimal,
    description: str,
    timeout_hours: int = 72
) -> Dict[str, Any]
```

**Parameters:**
- `buyer_id`: Telegram user ID of buyer
- `seller_username`: Telegram username of seller 
- `amount`: Escrow amount in USD
- `description`: Escrow description
- `timeout_hours`: Timeout in hours (default: 72)

**Returns:**
```json
{
  "escrow_id": "ESC123456",
  "status": "pending_acceptance",
  "created_at": "2025-01-04T10:30:00Z",
  "expires_at": "2025-01-07T10:30:00Z"
}
```

#### Accept Escrow
```python
async def accept_escrow(escrow_id: str, seller_id: str) -> Dict[str, Any]
```

#### Release Escrow
```python
async def release_escrow(escrow_id: str, released_by: str) -> Dict[str, Any]
```

### Wallet Service API

#### Credit Wallet
```python
async def credit_wallet(
    user_id: str,
    amount: Decimal, 
    description: str,
    transaction_type: str = "deposit"
) -> Dict[str, Any]
```

**Returns:**
```json
{
  "transaction_id": "TXN789012",
  "new_balance": "150.75",
  "amount_credited": "50.00",
  "description": "Crypto deposit from Bitcoin"
}
```

#### Debit Wallet
```python
async def debit_wallet(
    user_id: str,
    amount: Decimal,
    description: str,
    transaction_type: str = "withdrawal"
) -> Dict[str, Any]
```

### Notification Service API

#### Send Notification
```python
async def send_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    channels: List[str] = ["telegram"],
    action_buttons: Optional[List[Dict]] = None
) -> Dict[str, Any]
```

**Notification Types:**
- `escrow_created`
- `escrow_accepted` 
- `escrow_funded`
- `escrow_released`
- `payment_received`
- `dispute_opened`
- `system_maintenance`

**Channels:**
- `telegram`: Telegram bot message
- `email`: Email notification

---

## Database API

### Models

#### User Model
```python
class User(Base):
    telegram_id: str
    username: str
    wallet_balance: Decimal
    reputation_score: float
    email: str
    notification_preferences: str  # JSON
    created_at: datetime
    last_active: datetime
```

#### Escrow Model
```python
class Escrow(Base):
    escrow_id: str
    buyer_id: str
    seller_id: str
    amount: Decimal
    status: str
    description: str
    created_at: datetime
    expires_at: datetime
    released_at: datetime
```

#### Transaction Model
```python
class Transaction(Base):
    transaction_id: str
    user_id: str
    amount: Decimal
    transaction_type: str
    status: str
    description: str
    escrow_id: str  # Optional
    created_at: datetime
```

### Database Operations

#### Query Examples
```python
# Get user by Telegram ID
user = session.query(User).filter(User.telegram_id == user_id).first()

# Get active escrows for user
escrows = session.query(Escrow).filter(
    and_(
        or_(Escrow.buyer_id == user_id, Escrow.seller_id == user_id),
        Escrow.status == 'active'
    )
).all()

# Get transaction history
transactions = session.query(Transaction).filter(
    Transaction.user_id == user_id
).order_by(Transaction.created_at.desc()).limit(50).all()
```

---

## External Service Integrations

### Telegram Bot API

#### Webhook Configuration
```python
# Set webhook URL
webhook_url = "https://your-domain.com/webhook/telegram"
await bot.set_webhook(webhook_url)
```

#### Message Handling
```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming Telegram messages"""
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    
    # Rate limiting check
    if rate_limiter.is_limited(user_id, "message"):
        await update.message.reply_text("Too many requests. Please slow down.")
        return
    
    # Process message
    response = await process_user_message(user_id, message_text)
    await update.message.reply_text(response)
```

### Cryptocurrency APIs

#### Exchange Rate Service
```python
async def get_exchange_rate(crypto_symbol: str) -> Decimal:
    """Get current exchange rate for cryptocurrency"""
    # Implementation depends on chosen API (CoinGecko, CoinMarketCap, etc.)
    rate = await crypto_api.get_price(crypto_symbol)
    return Decimal(str(rate))
```

#### Blockchain Monitoring
```python
async def check_deposit_confirmations():
    """Check for confirmed cryptocurrency deposits"""
    pending_deposits = await get_pending_deposits()
    
    for deposit in pending_deposits:
        confirmations = await blockchain_api.get_confirmations(
            deposit.txid, 
            deposit.network
        )
        
        if confirmations >= required_confirmations[deposit.network]:
            await process_confirmed_deposit(deposit)
```

### Email Service (Brevo)

#### Send Email Notification
```python
async def send_email_notification(
    recipient_email: str,
    template_id: int,
    template_data: Dict[str, Any]
) -> bool:
    """Send email using Brevo template"""
    try:
        api_instance = TransactionalEmailsApi(brevo_client)
        
        send_smtp_email = SendSmtpEmail(
            to=[{"email": recipient_email}],
            template_id=template_id,
            params=template_data
        )
        
        response = api_instance.send_transac_email(send_smtp_email)
        return True
        
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False
```

---

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid amount format",
    "details": {
      "field": "amount",
      "provided": "abc",
      "expected": "decimal number"
    },
    "timestamp": "2025-01-04T10:30:00Z",
    "request_id": "req_123456789"
  }
}
```

### Error Categories

#### ValidationError
- Invalid input format
- Missing required fields
- Value out of range

#### AuthorizationError  
- Insufficient permissions
- Invalid user credentials
- Access denied

#### PaymentError
- Insufficient funds
- Payment processing failure
- Invalid cryptocurrency address

#### DatabaseError
- Connection failure
- Query timeout
- Constraint violation

#### ServiceError
- External API failure
- Network timeout
- Service unavailable

### Exception Handling Decorators

```python
@handle_bot_errors
async def escrow_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handler implementation
    pass

@safe_operation("wallet_credit")
async def credit_user_wallet(user_id: str, amount: Decimal):
    # Wallet operation implementation
    pass
```

---

## Rate Limiting

### Rate Limit Configuration
```python
RATE_LIMITS = {
    "create_escrow": {"requests": 3, "window": 300},  # 3 per 5 minutes
    "send_message": {"requests": 5, "window": 60},    # 5 per minute
    "admin_operation": {"requests": 10, "window": 60}, # 10 per minute
    "general": {"requests": 30, "window": 60}         # 30 per minute
}
```

### Rate Limit Headers
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1704367800
X-RateLimit-Retry-After: 60
```

### Rate Limit Response
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after": 60,
    "limit": 30,
    "window": 60
  }
}
```

---

## Authentication & Authorization

### Admin Authentication
```python
from config_admin import AdminConfig

def is_admin(user_id: str) -> bool:
    """Check if user is admin"""
    return AdminConfig.is_admin(user_id)

def require_admin(func):
    """Decorator requiring admin privileges"""
    @wraps(func)
    async def wrapper(user_id: str, *args, **kwargs):
        if not is_admin(user_id):
            raise AuthorizationError("Admin access required")
        return await func(user_id, *args, **kwargs)
    return wrapper
```

### User Authentication
```python
async def authenticate_user(telegram_id: str) -> Optional[User]:
    """Authenticate user by Telegram ID"""
    session = SessionLocal()
    try:
        user = session.query(User).filter(
            User.telegram_id == telegram_id
        ).first()
        return user
    finally:
        session.close()
```

---

## Caching

### Cache Configuration
```python
# Cache TTL settings
CACHE_TTL = {
    "user_profile": 300,      # 5 minutes
    "escrow_data": 120,       # 2 minutes  
    "exchange_rates": 30,     # 30 seconds
    "general": 60             # 1 minute
}
```

### Cache Usage Examples
```python
from caching.simple_cache import cache

# Cache user profile
@cache.cached(ttl=300, key_prefix="user_profile")
async def get_user_profile(user_id: str) -> Dict:
    # Database query implementation
    pass

# Cache exchange rates
@cache.cached(ttl=30, key_prefix="exchange_rate")
async def get_btc_rate() -> Decimal:
    # API call implementation
    pass
```

---

## Monitoring & Metrics

### Custom Metrics
```python
from monitoring.health_check import health_monitor

# Record custom metrics
health_monitor.record_metric("escrow_created", 1)
health_monitor.record_metric("wallet_balance", user_balance)
health_monitor.record_metric("api_response_time", response_time_ms)
```

### Health Check Integration
```python
async def custom_health_check() -> Dict[str, Any]:
    """Custom application health check"""
    return {
        "status": "healthy",
        "active_escrows": await count_active_escrows(),
        "pending_deposits": await count_pending_deposits(),
        "last_backup": await get_last_backup_time()
    }

# Register custom health check
health_monitor.register_check("application", custom_health_check)
```

---

## Development & Testing

### Testing Endpoints
```bash
# Health check
curl -X GET http://localhost:5000/health

# System info
curl -X GET http://localhost:5000/sysinfo

# Test rate limiting
for i in {1..35}; do curl -X GET http://localhost:5000/ping; done
```

### Mock Services
```python
class MockCryptoService:
    """Mock crypto service for testing"""
    
    async def get_exchange_rate(self, symbol: str) -> Decimal:
        mock_rates = {
            "BTC": Decimal("45000.00"),
            "ETH": Decimal("2500.00"),
            "USDT": Decimal("1.00")
        }
        return mock_rates.get(symbol, Decimal("1.00"))
```

---

## Security Considerations

### Input Validation
- All user inputs validated using `utils.input_validation`
- SQL injection prevention through parameterized queries
- XSS prevention through input sanitization

### Data Protection
- Sensitive data encrypted at rest
- API keys stored in environment variables
- User passwords never stored (Telegram authentication)

### Rate Limiting
- Per-user rate limiting prevents abuse
- Different limits for different operations
- Automatic blocking of excessive requests

### Audit Logging
- All financial operations logged
- Admin actions tracked
- Failed authentication attempts recorded

---

This API documentation serves as a comprehensive reference for developers working with the Telegram Escrow Bot system. For specific implementation details, refer to the source code and additional technical documentation.