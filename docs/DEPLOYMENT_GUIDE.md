# Telegram Escrow Bot - Deployment Guide

## Overview

This comprehensive deployment guide covers production deployment of the Telegram Escrow Bot on Replit and other platforms, including all necessary configurations, security considerations, and operational procedures.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Replit Deployment](#replit-deployment)
3. [Environment Configuration](#environment-configuration)
4. [Database Setup](#database-setup)
5. [External Service Configuration](#external-service-configuration)
6. [Security Configuration](#security-configuration)
7. [Monitoring Setup](#monitoring-setup)
8. [Backup Configuration](#backup-configuration)
9. [Post-Deployment Verification](#post-deployment-verification)
10. [Maintenance & Operations](#maintenance--operations)
11. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### ✅ Required Services
- [ ] Telegram Bot Token obtained from @BotFather
- [ ] PostgreSQL database provisioned
- [ ] Brevo email service account created
- [ ] Admin Telegram IDs identified
- [ ] Domain/subdomain for webhooks (if applicable)

### ✅ Development Complete
- [ ] All production hardening implemented
- [ ] Tests passing (6/6 systems)
- [ ] Code quality improvements applied
- [ ] Documentation complete
- [ ] Backup system configured

### ✅ Security Review
- [ ] Environment variables configured
- [ ] Admin access restricted
- [ ] Rate limiting enabled
- [ ] Input validation active
- [ ] Error handling secured

---

## Replit Deployment

### Step 1: Repository Setup

1. **Create New Replit Project**
   ```bash
   # Clone repository or upload files to Replit
   # Ensure all files are present in root directory
   ```

2. **Verify File Structure**
   ```
   /
   ├── handlers/
   ├── services/
   ├── utils/
   ├── middleware/
   ├── monitoring/
   ├── caching/
   ├── main.py
   ├── config.py
   ├── database.py
   ├── models.py
   ├── pyproject.toml
   └── .env.example
   ```

### Step 2: Configure Replit Environment

1. **Install Dependencies**
   ```bash
   # Dependencies automatically installed from pyproject.toml
   # Verify installation in Shell tab
   pip list | grep telegram
   ```

2. **Configure Replit Secrets**
   - Open Secrets tab in Replit
   - Add all required environment variables (see Environment Configuration section)

3. **Set Up Database**
   - Enable PostgreSQL in Replit Database tab
   - Note the DATABASE_URL provided by Replit

### Step 3: Deploy Application

1. **Configure Run Command**
   ```python
   # In main.py, ensure proper configuration
   if __name__ == "__main__":
       app.run_polling()  # For Replit deployment
   ```

2. **Start Application**
   - Click "Run" button in Replit
   - Monitor console for startup messages
   - Verify all systems initialize correctly

3. **Enable Always On** (Replit Hacker Plan)
   - Navigate to project settings
   - Enable "Always On" to prevent sleeping

---

## Environment Configuration

### Required Environment Variables

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/database

# Admin Configuration
ADMIN_IDS=1085125393,1531772316

# Email Service (Brevo)
BREVO_API_KEY=your_brevo_api_key
BREVO_SENDER_EMAIL=noreply@yourdomain.com
BREVO_SENDER_NAME="CryptoEscrow Bot"

# Application Configuration
PLATFORM_FEE_PERCENTAGE=10
MINIMUM_ESCROW_AMOUNT=50
MAX_ESCROW_AMOUNT=10000

# Network Fees (in USD)
BITCOIN_NETWORK_FEE=5.00
ETHEREUM_NETWORK_FEE=15.00
LITECOIN_NETWORK_FEE=0.50
DOGECOIN_NETWORK_FEE=1.00
BITCOIN_CASH_NETWORK_FEE=0.25
BINANCE_SMART_CHAIN_NETWORK_FEE=0.50
TRON_NETWORK_FEE=1.00
USDT_ERC20_NETWORK_FEE=15.00
USDT_TRC20_NETWORK_FEE=1.00

# Rate Limiting Configuration
RATE_LIMIT_CREATE_ESCROW_REQUESTS=3
RATE_LIMIT_CREATE_ESCROW_WINDOW=300
RATE_LIMIT_SEND_MESSAGE_REQUESTS=5
RATE_LIMIT_SEND_MESSAGE_WINDOW=60
RATE_LIMIT_ADMIN_OPERATION_REQUESTS=10
RATE_LIMIT_ADMIN_OPERATION_WINDOW=60
RATE_LIMIT_GENERAL_REQUESTS=30
RATE_LIMIT_GENERAL_WINDOW=60

# Backup Configuration
BACKUP_DAILY_RETENTION=7
BACKUP_WEEKLY_RETENTION=4
BACKUP_MONTHLY_RETENTION=6

# Security Configuration
JWT_SECRET_KEY=your_jwt_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here

# External API Keys (Optional)
COINGECKO_API_KEY=your_coingecko_api_key
BLOCKCHAIN_INFO_API_KEY=your_blockchain_api_key
```

### Environment File Setup

1. **Create .env file** (for local development)
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

2. **Replit Secrets Configuration**
   - Use Replit Secrets tab for production
   - Never commit .env file to repository
   - Verify all secrets are properly set

---

## Database Setup

### Step 1: PostgreSQL Configuration

1. **Enable Replit Database**
   ```bash
   # Replit automatically provides PostgreSQL
   # DATABASE_URL will be available in environment
   ```

2. **Create Database Tables**
   ```python
   # Run database initialization
   python -c "from database import init_db; init_db()"
   ```

### Step 2: Database Migration

1. **Run Initial Migration**
   ```python
   # Execute from Python console
   from models import Base
   from database import engine
   Base.metadata.create_all(bind=engine)
   ```

2. **Verify Tables Created**
   ```sql
   -- Connect to database and verify
   \dt  -- List tables
   SELECT * FROM users LIMIT 1;
   SELECT * FROM escrows LIMIT 1;
   SELECT * FROM transactions LIMIT 1;
   ```

### Step 3: Database Backup Setup

1. **Configure Backup Service**
   ```python
   # Backup service automatically configured
   # Verify backup directory exists
   from services.backup_service import backup_service
   await backup_service.get_backup_status()
   ```

---

## External Service Configuration

### Telegram Bot Setup

1. **Create Bot with BotFather**
   ```
   /newbot
   Bot Name: CryptoEscrow Bot
   Username: @your_escrow_bot
   ```

2. **Configure Bot Settings**
   ```
   /setcommands
   start - Start using the bot
   help - Get help and support
   menu - Open main menu
   wallet - Manage wallet
   profile - View profile
   ```

3. **Set Bot Description**
   ```
   /setdescription
   Secure cryptocurrency escrow service for safe trading. 
   Hold crypto until both parties confirm transaction completion.
   ```

### Brevo Email Service

1. **Create Brevo Account**
   - Sign up at brevo.com
   - Verify email domain
   - Generate API key

2. **Create Email Templates**
   ```html
   <!-- Welcome Email Template -->
   <h1>Welcome to CryptoEscrow!</h1>
   <p>Hello {{FIRSTNAME}},</p>
   <p>Your account has been created successfully.</p>
   
   <!-- Escrow Notification Template -->
   <h1>Escrow Update</h1>
   <p>Escrow {{ESCROW_ID}} status: {{STATUS}}</p>
   ```

3. **Configure Sender Domain**
   - Add and verify sender domain
   - Set up SPF/DKIM records
   - Configure sender reputation

---

## Security Configuration

### SSL/TLS Setup

1. **Replit HTTPS**
   ```bash
   # Replit provides automatic HTTPS
   # Your bot will be available at:
   # https://your-repl-name.your-username.repl.co
   ```

2. **Custom Domain** (Optional)
   - Configure custom domain in Replit
   - Update DNS records
   - Verify SSL certificate

### Admin Security

1. **Admin Access Configuration**
   ```python
   # Verify admin configuration
   from config_admin import AdminConfig
   print(AdminConfig.get_admin_ids())
   print(AdminConfig.is_admin("1085125393"))
   ```

2. **Security Audit**
   ```python
   # Run security audit
   python -c "
   from utils.security_audit import run_security_audit
   run_security_audit()
   "
   ```

### Rate Limiting Verification

1. **Test Rate Limits**
   ```bash
   # Test API endpoints
   for i in {1..35}; do curl https://your-bot.repl.co/ping; done
   ```

---

## Monitoring Setup

### Health Check Endpoints

1. **Configure Health Monitoring**
   ```python
   # Health endpoints automatically available:
   # GET /health - Full system health
   # GET /ping - Simple availability
   # GET /sysinfo - System information
   ```

2. **External Monitoring Setup**
   ```bash
   # Configure external monitoring service
   # Examples: UptimeRobot, Pingdom, StatusCake
   
   Monitor URLs:
   - https://your-bot.repl.co/ping (every 1 minute)
   - https://your-bot.repl.co/health (every 5 minutes)
   ```

### Logging Configuration

1. **Production Logging**
   ```python
   # Logging automatically configured
   # Logs available in Replit console
   # Configure log levels as needed
   import logging
   logging.getLogger().setLevel(logging.INFO)
   ```

---

## Backup Configuration

### Automated Backup Setup

1. **Configure Backup Schedule**
   ```python
   # Backups automatically scheduled:
   # - Daily: Full backup at 2 AM UTC
   # - Weekly: Archive backup on Sundays
   # - Cleanup: Remove old backups per retention policy
   ```

2. **Manual Backup**
   ```python
   # Create manual backup
   from services.backup_service import backup_service
   await backup_service.create_full_backup()
   ```

3. **Backup Verification**
   ```python
   # Check backup status
   status = await backup_service.get_backup_status()
   print(f"Latest backup: {status['latest_backup']}")
   print(f"Total backups: {status['backup_counts']}")
   ```

---

## Post-Deployment Verification

### System Health Check

1. **Verify All Systems**
   ```bash
   # Check that the bot is running properly
   # Monitor logs for any errors
   # Verify all services are accessible
   ```

2. **Check Health Endpoints**
   ```bash
   # Test health endpoints
   curl https://your-bot.repl.co/health
   curl https://your-bot.repl.co/ping
   curl https://your-bot.repl.co/sysinfo
   ```

### Bot Functionality Test

1. **Basic Bot Test**
   ```
   # Send messages to your bot:
   /start - Should show welcome message
   /help - Should show help information
   /menu - Should show main menu
   ```

2. **Create Test Escrow**
   ```
   # Test escrow creation:
   1. Start escrow creation
   2. Enter amount ($50+)
   3. Enter seller username
   4. Verify escrow created successfully
   ```

### Database Verification

1. **Check Database Connection**
   ```python
   from database import SessionLocal
   session = SessionLocal()
   try:
       result = session.execute("SELECT 1")
       print("Database connection: OK")
   except Exception as e:
       print(f"Database error: {e}")
   finally:
       session.close()
   ```

---

## Maintenance & Operations

### Daily Operations

1. **Monitor Health Dashboard**
   - Check /health endpoint daily
   - Review system resource usage
   - Monitor error logs

2. **Review Backup Status**
   ```python
   # Check daily backup completion
   from services.backup_service import backup_service
   status = await backup_service.get_backup_status()
   ```

### Weekly Operations

1. **System Performance Review**
   - Analyze response times
   - Review rate limiting logs
   - Check cache hit rates

2. **Security Audit**
   ```python
   # Run weekly security audit
   from utils.security_audit import run_security_audit
   run_security_audit()
   ```

### Monthly Operations

1. **Database Maintenance**
   ```sql
   -- Analyze database performance
   ANALYZE;
   
   -- Clean up old data (if needed)
   -- DELETE FROM transactions WHERE created_at < NOW() - INTERVAL '1 year';
   ```

2. **Backup Archive**
   - Archive monthly backups
   - Clean up old backup files
   - Verify backup integrity

### Emergency Procedures

1. **Bot Downtime**
   ```bash
   # Quick restart
   # Stop application in Replit
   # Check logs for errors
   # Restart application
   ```

2. **Database Issues**
   ```python
   # Database connection issues
   # 1. Check DATABASE_URL
   # 2. Verify PostgreSQL service
   # 3. Restart database connection
   ```

3. **Performance Issues**
   ```python
   # High resource usage
   # 1. Check /sysinfo endpoint
   # 2. Review active processes
   # 3. Clear cache if needed
   from caching.simple_cache import cache
   cache.clear()
   ```

---

## Troubleshooting

### Common Issues

#### 1. Bot Not Responding
```bash
# Check bot status
curl https://your-bot.repl.co/ping

# Verify bot token
# Check Telegram webhook status
# Review application logs
```

#### 2. Database Connection Errors
```python
# Verify DATABASE_URL
import os
print(os.getenv('DATABASE_URL'))

# Test connection
from database import SessionLocal
session = SessionLocal()
# Connection should succeed
```

#### 3. Email Notifications Not Working
```python
# Check Brevo configuration
import os
print(os.getenv('BREVO_API_KEY'))

# Test email service
from services.email import send_test_email
await send_test_email("test@example.com")
```

#### 4. Rate Limiting Issues
```python
# Check rate limit configuration
from middleware.rate_limiter import rate_limiter
print(rate_limiter.get_stats())

# Reset rate limits if needed
rate_limiter.clear_all()
```

#### 5. High Memory Usage
```bash
# Check system resources
curl https://your-bot.repl.co/sysinfo

# Clear cache
python -c "from caching.simple_cache import cache; cache.clear()"

# Restart application if needed
```

### Log Analysis

1. **Application Logs**
   ```bash
   # Monitor logs in Replit console
   # Look for ERROR and WARNING messages
   # Check for patterns in failures
   ```

2. **Error Patterns**
   ```python
   # Common error patterns to watch:
   # - Database connection timeouts
   # - Rate limit exceeded messages
   # - External API failures
   # - Memory allocation errors
   ```

### Performance Optimization

1. **Database Optimization**
   ```sql
   -- Add indexes for common queries
   CREATE INDEX idx_escrows_status ON escrows(status);
   CREATE INDEX idx_transactions_user_id ON transactions(user_id);
   CREATE INDEX idx_users_telegram_id ON users(telegram_id);
   ```

2. **Cache Optimization**
   ```python
   # Adjust cache TTL settings
   CACHE_TTL = {
       "user_profile": 600,    # Increase to 10 minutes
       "exchange_rates": 60,   # Increase to 1 minute
       "escrow_data": 300      # Increase to 5 minutes
   }
   ```

---

## Support & Documentation

### Getting Help

1. **Documentation Resources**
   - API Documentation: `docs/API_DOCUMENTATION.md`
   - Project Documentation: `replit.md`
   - Code Comments: Inline documentation

2. **Monitoring Resources**
   - Health Dashboard: `/health`
   - System Information: `/sysinfo`
   - Backup Status: Backup service API

3. **Community Support**
   - Replit Community Forums
   - Telegram Bot API Documentation
   - PostgreSQL Documentation

---

## Deployment Success Criteria

### ✅ Deployment Complete When:
- [ ] Bot responds to commands
- [ ] Database connection stable
- [ ] Health endpoints return healthy status
- [ ] All 6 production systems working
- [ ] Backups running successfully
- [ ] Rate limiting active
- [ ] Error handling functional
- [ ] Monitoring configured
- [ ] Admin access verified

### 🎉 Production Ready!

Your Telegram Escrow Bot is now successfully deployed and ready for production use. The system includes enterprise-grade security, monitoring, and backup capabilities to ensure reliable operation.

---

*Deployment Guide - Version 1.0*  
*Last Updated: January 2025*