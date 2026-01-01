# System Monitoring & Alerting Documentation

## Overview
Comprehensive monitoring system that tracks system health, service availability, and sends automated alerts to administrators when issues are detected.

## Components

### 1. System Monitor (`services/system_monitor.py`)
Monitors core system health including:
- **Database Health**: Connection times, query performance, active connections
- **Security Events**: Intrusion detection, failed login attempts, suspicious activity
- **High-Value Transactions**: Monitors escrows and withdrawals above configured thresholds
- **System Resources**: CPU, memory, and disk usage monitoring

### 2. Service Health Monitor (`services/service_health_monitor.py`)
Monitors external API services:
- **BlockBee API**: Payment address generation, deposit confirmations
- **Fincra API**: NGN payments and account balance
- **Binance API**: Cryptocurrency withdrawals and balance checks
- **External Dependencies**: Internet connectivity and DNS resolution

### 3. Alert Manager (`services/alert_manager.py`)
Centralized alert coordination:
- **Alert Routing**: Sends critical alerts to both admin DMs and notification groups
- **Cooldown Management**: Prevents alert spam with configurable cooldown periods
- **Severity Levels**: Different alert types (system, service, transaction)
- **Message Formatting**: Professional alert messages with actionable information

### 4. Enhanced Error Handler (`services/error_handler.py`)
Automatic error detection and alerting:
- **API Error Handling**: Captures and analyzes service failures
- **Critical Error Detection**: Identifies patterns like BlockBee 404 errors
- **Automatic Alerting**: Sends immediate notifications for critical failures
- **Error Tracking**: Maintains error counts and patterns for analysis

## Monitoring Jobs

### System Health Monitoring (Every 5 minutes)
```
Job ID: system_monitoring
Frequency: 5 minutes
Checks: Database, Security, Transactions, System Resources
```

### Service Health Monitoring (Every 1 minute)  
```
Job ID: service_health_monitoring
Frequency: 1 minute
Checks: BlockBee, Fincra, Binance APIs
```

### Enhanced Balance Monitoring (Every 30 minutes)
```
Job ID: enhanced_balance_monitoring  
Frequency: 30 minutes
Checks: Fincra and Binance balances with improved alerting
```

## Alert Types

### System Alerts
- Database connection issues
- High CPU/memory/disk usage  
- Security intrusion attempts
- High-value transaction activity

### Service Alerts
- **BlockBee Failures**: API 404 errors, callback issues, timeout
- **Fincra Issues**: Authentication problems, balance issues
- **Binance Problems**: API key issues, withdrawal failures
- **Network Connectivity**: DNS resolution, internet access

### Transaction Alerts
- High-value escrows (>$5,000 default)
- High-value withdrawals (>$5,000 default)
- Suspicious transaction patterns
- Multiple high-value activities

## Configuration

### Environment Variables
```bash
# Monitoring intervals
SYSTEM_MONITOR_INTERVAL_MINUTES=5
SERVICE_HEALTH_CHECK_INTERVAL_MINUTES=1

# Thresholds
HIGH_VALUE_TRANSACTION_THRESHOLD_USD=5000.0
FAILED_API_CALLS_THRESHOLD=5
DATABASE_ERROR_THRESHOLD=3

# Alert cooldowns (prevent spam)
SERVICE_ALERT_COOLDOWN_MINUTES=15
SYSTEM_ALERT_COOLDOWN_MINUTES=30

# Timeouts
DB_CONNECTION_TIMEOUT_SECONDS=30
API_TIMEOUT_SECONDS=30
```

### Alert Routing
- **Admin DMs**: All alerts sent to configured admin users
- **Notification Group**: System and service alerts (if NOTIFICATION_GROUP_ID set)
- **Email Alerts**: Critical system alerts (if COMPANY_EMAIL configured)

## Critical Error Detection

### BlockBee API Issues
The system specifically detects and alerts on:
- `404 "Callback not found"` errors (affects exchange processing)
- `500` server errors
- Timeout and connectivity issues

### Fincra Problems
- Authentication failures
- Insufficient balance warnings
- Payment processing failures

### Binance Issues  
- API key or signature problems
- Withdrawal failures
- Balance threshold alerts

## Sample Alerts

### Service Failure Alert
```
🚨 SERVICE FAILURE ALERT

Service: BLOCKBEE
Status: FAILING
Time: 2025-08-23 00:18:44 UTC

Recent Failures:
• BlockBee API returning 404 errors - Callback/Address issues detected
• Context: crypto_deposit_check

Immediate Actions:
• Check BlockBee API status and callback URLs
• Verify API key configuration  
• Review address generation logs

Platform: LockBay
Action Required: Immediate investigation needed
```

### System Alert
```
🔴 SYSTEM ALERT: DATABASE

Status: DEGRADED  
Time: 2025-08-23 00:20:15 UTC

Issues Detected:
• Slow database connection: 8.5s
• High connection count: 67
• Query performance degraded: 12.2s

Platform: LockBay
```

## Monitoring Dashboard Access

The monitoring system integrates with:
- **Admin Panel**: Real-time monitoring status
- **Telegram Alerts**: Immediate notifications  
- **Email Reports**: Daily summaries and critical alerts
- **Log Analysis**: Detailed error tracking and patterns

## Troubleshooting

### No Alerts Received
1. Check `NOTIFICATION_GROUP_ID` is configured
2. Verify admin user IDs in `ADMIN_USER_IDS`
3. Confirm `BOT_TOKEN` has proper permissions
4. Review cooldown settings

### False Positives
1. Adjust threshold values in configuration
2. Review cooldown periods
3. Check service availability settings

### Missing Service Monitoring
1. Verify API credentials are configured
2. Check service availability flags
3. Review import paths in monitoring jobs

## Best Practices

1. **Regular Review**: Check monitoring logs weekly
2. **Threshold Tuning**: Adjust based on normal operation patterns  
3. **Alert Fatigue**: Balance sensitivity with spam prevention
4. **Documentation**: Keep runbooks updated for common alerts
5. **Testing**: Regularly verify alert delivery channels

## Integration with Existing Systems

The monitoring seamlessly integrates with:
- **Existing Scheduler**: Uses current APScheduler infrastructure
- **Notification Service**: Leverages existing Telegram/email systems
- **Admin Interface**: Provides monitoring status in admin panel
- **Balance Monitoring**: Enhances existing balance alert system
- **Error Logging**: Integrates with current logging infrastructure