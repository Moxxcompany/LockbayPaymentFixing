# Admin Broadcast Feature Guide

## ✅ Updated Telegram Compliance Settings

**Batch Configuration:**
- ✅ Batch Size: 30 users per batch
- ✅ Batch Delay: **3 seconds** between batches (Telegram compliant)
- ✅ Max Retries: 3 attempts per message
- ✅ Retry Delay: 2 seconds between retries

## 📢 How Admins Access Broadcast Features

### Method 1: Via Admin Panel (PRIMARY - Now Enabled)

1. **Open Admin Panel**
   ```
   /admin
   ```

2. **Main Admin Panel Menu**
   ```
   🔧 Admin Panel
   📊 {active} active • {users} users • {new} new today

   Choose action:

   [🎯 Referrals] [🏥 Health]
   [📊 System]    [📈 Analytics]
   [⚖️ Disputes]  [💰 Transactions]
   [📢 Broadcast] [💳 Payment Config]  ← NEW!
   ```

3. **Click "📢 Broadcast"**
   - Opens Notification Management Center
   - Shows delivery statistics, success rates
   - Access to broadcast tools

### Method 2: Via Direct Command

1. **Use Broadcast Command**
   ```
   /broadcast
   ```

2. **Broadcast Menu**
   ```
   📢 Broadcast Command
   
   Send a message to all users. Use carefully!
   
   [📢 Send Broadcast] [🏠 Admin Panel]
   ```

3. **Click "📢 Send Broadcast"**
   - Starts broadcast campaign

## 🎯 Broadcast Flow

### Text Broadcast

```python
# Admin triggers broadcast
await broadcast_service.start_broadcast_campaign(
    message="Your message here",
    admin_user_id=admin_id,
    target_users=None  # None = all users, or specific list
)
```

**What Happens:**
1. ✅ System counts total users with Telegram IDs
2. ✅ Divides users into batches of 30
3. ✅ Sends campaign start notification to admin:
   ```
   🚀 Broadcast Campaign Started
   
   📋 Campaign ID: abc12345
   👥 Target Users: 1,250
   📦 Total Batches: 42
   ⏱️ Estimated Duration: 126.0s
   ```

4. ✅ Processes each batch (30 users):
   - Sends messages with 3 retry attempts
   - Waits 3 seconds before next batch
   - Handles errors (blocked users, invalid chats)

5. ✅ Admin receives batch updates:
   ```
   📊 Batch 1/42 Completed
   
   🎯 Campaign: abc12345
   📦 Batch Stats:
   ├ 👥 Users: 30
   ├ ✅ Successful: 28
   ├ ❌ Failed: 2
   └ ⏱️ Time: 2.3s
   
   📈 Overall Progress:
   ├ 🎯 Total Delivered: 28
   ├ ❌ Total Failed: 2
   ├ 📊 Progress: 2.4%
   └ ⏳ Est. Remaining: 123.0s
   ```

6. ✅ Final statistics when complete:
   ```
   🎉 Campaign abc12345 Completed!
   
   📊 Final Statistics:
   ├ 👥 Total Users: 1,250
   ├ ✅ Successful: 1,198 (95.8%)
   ├ ❌ Failed: 52
   ├ 📦 Total Batches: 42
   ├ ⏱️ Duration: 128.5s
   └ 📅 Completed: 14:25:30 UTC
   
   🎯 Campaign Performance: 🟢 Excellent
   ```

### Multimedia Broadcast

Supports:
- ✅ **Photos** (with captions)
- ✅ **Videos** (with captions)
- ✅ **Documents** (with captions)
- ✅ **Audio** (with captions)
- ✅ **Polls** (anonymous)
- ✅ **Formatted Text** (with entities)

```python
# Example: Photo broadcast
await broadcast_service.start_multimedia_broadcast_campaign(
    broadcast_data={
        "type": "photo",
        "file_id": "AgACAgIAAxkBAAI...",
        "caption": "Check out this update!"
    },
    admin_user_id=admin_id,
    target_users=None
)
```

## 🛡️ Error Handling

### Smart Retry Logic

1. **Blocked Users (Forbidden Error)**
   - ❌ No retry - user has blocked bot
   - Logged and skipped

2. **Invalid Chat (BadRequest Error)**
   - ❌ No retry - chat doesn't exist
   - Logged and skipped

3. **Network Issues (TelegramError)**
   - ✅ Retry 3 times with 2-second delay
   - Logged if all retries fail

4. **Unknown Errors**
   - ✅ Retry 3 times with 2-second delay
   - Logged for investigation

## 📊 Notification Management Center

Accessible via: **Admin Panel → 📢 Broadcast**

### Features:

1. **Today's Activity**
   - Total notifications sent
   - Success rate percentage
   - Email vs Telegram breakdown

2. **User Preferences**
   - Total users count
   - Configured preferences
   - Coverage percentage

3. **Channel Configuration**
   - 📧 Email (Brevo): Active/Inactive
   - 💬 Telegram: Active/Inactive

4. **Quick Actions**
   ```
   [👥 User Preferences] [📊 Delivery Stats]
   [🔧 Channel Config]   [🧪 Test Notifications]
   [📋 Notification Log] [⚙️ Templates]
   [🏠 Admin]
   ```

## ⚡ Telegram Rate Limit Compliance

### Current Settings (COMPLIANT ✅)

```python
BATCH_SIZE = 30       # 30 users per batch
BATCH_DELAY = 3.0     # 3 seconds between batches
MAX_RETRIES = 3       # 3 retry attempts
RETRY_DELAY = 2.0     # 2 seconds between retries
```

### Why These Settings?

1. **30 users per batch**
   - Telegram recommends < 30 messages/second
   - Safe buffer for API stability

2. **3-second delay**
   - Prevents rate limiting
   - Ensures reliable delivery
   - Protects against throttling

3. **3 retries**
   - Handles temporary network issues
   - Smart skip for permanent failures (blocked/invalid)

4. **Background processing**
   - Non-blocking for admin
   - Real-time progress updates
   - Campaign tracking

## 🎯 Target User Selection

### Broadcast to All Users

```python
# No target_users = all users with Telegram ID
await broadcast_service.start_broadcast_campaign(
    message="System update announcement",
    admin_user_id=admin_id,
    target_users=None  # Broadcasts to ALL
)
```

### Broadcast to Specific Users

```python
# Filter specific users
session = get_session()
active_traders = session.query(User).filter(
    User.trader_level.in_(['silver', 'gold', 'platinum'])
).all()

await broadcast_service.start_broadcast_campaign(
    message="VIP trader announcement",
    admin_user_id=admin_id,
    target_users=active_traders  # Specific group
)
```

## 📝 Best Practices

1. **Use Carefully**
   - Broadcast reaches ALL users
   - Ensure message is relevant
   - Test with small group first

2. **Monitor Campaign**
   - Watch batch analytics
   - Track success rates
   - Review failed deliveries

3. **Timing**
   - Consider user time zones
   - Avoid peak trading hours
   - Schedule important announcements

4. **Message Quality**
   - Clear and concise
   - Proper formatting
   - Call-to-action when needed

## 🔧 Technical Implementation

**Service Location:** `services/broadcast_service.py`

**Handler Location:** `handlers/admin_broadcast.py`

**Direct Access:** `handlers/admin_broadcast_direct.py`

**Main Entry Points:**
- `/admin` → 📢 Broadcast button (NEW!)
- `/broadcast` → Direct broadcast command
- `admin_notifications` callback

**Database Models:**
- `NotificationLog` - Delivery tracking
- `NotificationQueue` - Queued messages
- `NotificationPreference` - User preferences
- `NotificationActivity` - Activity logs

## 🚀 Summary

✅ **Batch Size:** 30 users per batch
✅ **Batch Delay:** 3 seconds (Telegram compliant)
✅ **Max Retries:** 3 attempts
✅ **Access:** Now visible in main Admin Panel
✅ **Target:** All users OR specific users
✅ **Multimedia:** Photos, videos, documents, audio, polls
✅ **Analytics:** Real-time batch updates + final statistics
✅ **Error Handling:** Smart retry logic with permanent failure detection
