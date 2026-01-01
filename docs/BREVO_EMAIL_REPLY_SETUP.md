# Brevo Email Reply Configuration Guide

## Overview
This guide explains how to configure Brevo (formerly SendinBlue) to enable admin replies via email for LockBay support tickets.

## How It Works

```
User sends support message
    ↓
Admin receives email with Reply-To: support+sup-001@lockbay.io
    ↓
Admin clicks reply and types response
    ↓
Brevo receives the email reply
    ↓
Brevo sends webhook to your server: POST /webhook/email/support-reply
    ↓
Server extracts ticket ID from subject (SUP-001)
    ↓
Server sends admin's reply to user in Telegram bot
```

## Prerequisites

1. **Brevo Account** - Active account with API access
2. **Domain ownership** - You must own `lockbay.io` domain
3. **DNS access** - Ability to add DNS records to your domain

## Step 1: Domain Verification in Brevo

### 1.1 Add Domain to Brevo

1. Log in to [Brevo Dashboard](https://app.brevo.com)
2. Go to **Settings** → **Senders, Domains & Dedicated IPs**
3. Click **Domains** tab
4. Click **Add a Domain**
5. Enter: `lockbay.io`
6. Click **Add**

### 1.2 Configure DNS Records

Brevo will provide DNS records. Add these to your domain's DNS settings:

#### SPF Record (TXT)
```
Type: TXT
Host: @
Value: v=spf1 include:spf.brevo.com ~all
TTL: 3600
```

#### DKIM Record (TXT)
```
Type: TXT
Host: mail._domainkey
Value: [Provided by Brevo - unique for your account]
TTL: 3600
```

#### MX Record (For receiving emails)
```
Type: MX
Host: @
Value: in.mail-tester.com
Priority: 10
TTL: 3600
```

**Note:** Brevo's inbound email service uses `in.mail-tester.com` as the mail server.

### 1.3 Verify Domain

1. After adding DNS records, wait 5-10 minutes for propagation
2. In Brevo dashboard, click **Verify** next to your domain
3. If successful, you'll see green checkmarks ✅

## Step 2: Configure Inbound Webhook

### 2.1 Get Your Webhook URL

Your webhook URL depends on where you're deployed:

**Replit Deployment:**
```
https://[your-replit-domain].repl.co/webhook/email/support-reply
```

**Railway Deployment:**
```
https://[your-railway-domain].up.railway.app/webhook/email/support-reply
```

**Custom Domain:**
```
https://api.lockbay.io/webhook/email/support-reply
```

### 2.2 Generate Webhook Secret

Generate a secure random token for webhook authentication:

```bash
# Generate a secure random secret (32 characters)
openssl rand -hex 32
```

**Save this secret** - you'll need it in steps 2.3 and 5.

### 2.3 Configure Webhook in Brevo

1. Go to **Settings** → **Webhooks**
2. Click **Add a new webhook**
3. Configure:
   - **Webhook URL**: `https://your-domain.com/webhook/email/support-reply`
   - **Events**: Select **Inbound Email**
   - **Description**: `LockBay Support Email Replies`
4. Click **Advanced Settings** or **Add Headers**
5. Add custom header for authentication:
   - **Header Name**: `X-Webhook-Token`
   - **Header Value**: [Paste the secret you generated in step 2.2]
6. Click **Save**

**⚠️ SECURITY**: Without this custom header, anyone could send fake admin replies to your users!

### 2.4 Test Webhook

Brevo provides a **Test** button next to your webhook. Click it to verify connectivity.

**Expected response:**
```json
{
  "status": "error",
  "message": "No ticket ID found"
}
```

This is correct! The test doesn't include a real ticket ID, but it confirms your server is reachable.

## Step 3: Configure Inbound Email Routing

### 3.1 Set Up Email Forwarding Rules

1. In Brevo, go to **Settings** → **Inbound Parsing**
2. Click **Add a new rule**
3. Configure:
   - **Domain**: `lockbay.io`
   - **Recipient pattern**: `support+*@lockbay.io`
   - **Forward to webhook**: Select your webhook from dropdown
4. Click **Save**

**Important:** The `+` symbol creates a "plus address" that Brevo will parse:
- `support+sup-001@lockbay.io` → Ticket SUP-001
- `support+sup-042@lockbay.io` → Ticket SUP-042

## Step 4: Verify Configuration

### 4.1 Test Email Flow

1. **Create a test support ticket** in your bot
2. **Send a message** as a user
3. **Check admin email** - You should receive:
   ```
   From: hi@lockbay.io
   Reply-To: support+sup-001@lockbay.io
   Subject: Support Message: SUP-001 - UserName
   ```

4. **Reply to the email** with a test message
5. **Check Telegram bot** - User should receive your reply

### 4.2 Check Logs

Monitor your server logs for:
```
📧 Received support email reply: {...}
✅ Admin email reply forwarded to user for ticket SUP-001
```

## Step 5: Environment Variables

Ensure these are set in your deployment:

```bash
# Brevo API Key
BREVO_API_KEY=your_brevo_api_key_here

# CRITICAL: Webhook Security (generate with: openssl rand -hex 32)
BREVO_WEBHOOK_SECRET=your_32_char_secret_from_step_2.2

# Email sender
FROM_EMAIL=hi@lockbay.io
FROM_NAME=LockBay Support

# Admin email (receives notifications)
ADMIN_EMAIL=moxxcompany@gmail.com
```

**⚠️ CRITICAL**: `BREVO_WEBHOOK_SECRET` must match the `X-Webhook-Token` header value you configured in Brevo (Step 2.3).

**Security Note**: If `BREVO_WEBHOOK_SECRET` is not set, the webhook will accept requests from anyone (SECURITY RISK). Always set this in production!

## Troubleshooting

### Issue: Domain Not Verifying

**Solution:**
- Wait 30 minutes for DNS propagation
- Use [MXToolbox](https://mxtoolbox.com) to verify DNS records
- Check SPF: `dig TXT lockbay.io`
- Check DKIM: `dig TXT mail._domainkey.lockbay.io`

### Issue: Webhook Not Receiving Data

**Solution:**
1. Check webhook URL is publicly accessible
2. Verify SSL certificate is valid (https required)
3. Check Brevo webhook logs in dashboard
4. Test with: `curl -X POST https://your-domain.com/webhook/email/support-reply -d '{}'`

### Issue: Ticket ID Not Found

**Solution:**
- Verify subject line contains "SUP-001" format
- Admin must reply to the notification email (preserves subject)
- Don't manually compose new email - always use Reply

### Issue: Admin Reply Not Reaching User

**Solution:**
- Check server logs for errors
- Verify TELEGRAM_BOT_TOKEN is set correctly
- Ensure user hasn't blocked the bot
- Check database for ticket existence

## Security Notes

1. **Webhook Authentication**: Uses custom header (`X-Webhook-Token`) to verify requests are from Brevo. **CRITICAL**: Always set `BREVO_WEBHOOK_SECRET` in production.
2. **Admin Verification**: Only emails from verified admin accounts (with `is_admin=True`) are processed.
3. **Token Security**: Keep `BREVO_WEBHOOK_SECRET` confidential. Rotate periodically (update both Brevo and your environment).
4. **Rate Limiting**: Consider adding rate limits to prevent abuse (recommended for high-traffic deployments).
5. **Testing Security**: Test with both valid and invalid tokens to confirm authentication works.

## Testing Checklist

- [ ] Domain verified in Brevo (green checkmarks)
- [ ] SPF record added and verified
- [ ] DKIM record added and verified
- [ ] MX record added (if receiving emails)
- [ ] **Webhook secret generated** (32 characters minimum)
- [ ] **Custom header configured** in Brevo (`X-Webhook-Token`)
- [ ] **BREVO_WEBHOOK_SECRET set** in environment variables
- [ ] Inbound webhook configured
- [ ] Email routing rule added for `support+*@lockbay.io`
- [ ] **Security test**: Try webhook without token (should be rejected)
- [ ] **Security test**: Try webhook with wrong token (should be rejected)
- [ ] Test ticket created
- [ ] Admin received email with correct Reply-To
- [ ] Admin replied to email
- [ ] User received reply in Telegram
- [ ] Check logs show successful processing
- [ ] Logs show "authenticated" in webhook success message

## Support Resources

- [Brevo Documentation](https://developers.brevo.com/)
- [Brevo Inbound Email Guide](https://help.brevo.com/hc/en-us/articles/360000991960)
- [DNS Propagation Checker](https://dnschecker.org/)
- [MXToolbox](https://mxtoolbox.com/) - Verify email DNS records

## Next Steps

After configuration:
1. Train admin team on email reply workflow
2. Monitor logs for first week
3. Set up alerts for failed webhook deliveries
4. Consider adding reply templates for common responses
