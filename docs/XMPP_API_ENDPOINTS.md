✅ XMPP Integration Complete!

What Changed:

1. Moved to /backend/app/integrations/xmpp/ - XMPP is now a proper service integration
2. Created webhook handler - XMPPWebhookHandler processes incoming Openfire messages
3. Added webhook routes - /api/v1/webhooks/xmpp/ endpoints with API key auth
4. Removed /xmpp folder - Old bot code deleted

---

## Configuration

**Environment Variables (.env.local)**

```bash
# XMPP Server Connection
XMPP_USERNAME=adrielleu
XMPP_SERVER=10.143.121.140
XMPP_PASSWORD=your_password
XMPP_PORT=5222

# API Integration
API_BASE_URL=https://apidemo1.techmanager.ai
API_TOKEN=sk_your-api-key-here

# Storage
PURPLE_DIR=.purple
```

**Note:** The client constructs the JID as `XMPP_USERNAME@XMPP_SERVER` automatically.

**Where incoming username is extracted:**
- File: `src/xmpp_client.py:281`
- Code: `sender = str(msg.getFrom())`
- Returns full JID: `username@server/resource`

---
XMPP Webhook Endpoints:

1. Receive Incoming Message

POST /api/v1/webhooks/xmpp/incoming
Authorization: Bearer sk_your-api-key-here
Content-Type: application/json

{
  "from_jid": "user@domain.com/resource",
  "to_jid": "support@domain.com",
  "body": "I need help",
  "message_type": "chat",
  "thread_id": null,
  "timestamp": "2024-01-15T10:00:00Z"
}

Note: Openfire sends responses back via XMPP to get responses with API key

---

2. Fetch Pending Tickets (Client → Backend)

GET /api/v1/tickets/pending-responses
Authorization: Bearer sk_your-api-key-here
Content-Type: application/json

Response:
[
  {
    "id": 123,
    "from_jid": "user@domain.com/resource",
    "subject": "Help with login",
    "body": "I can't log into my account",
    "status": "open",
    "created_at": "2024-01-15T10:00:00Z"
  }
]

---

3. Send Ticket Response (Client → Backend)

POST /api/v1/tickets/{ticket_id}/respond
Authorization: Bearer sk_your-api-key-here
Content-Type: application/json

{
  "response": "Please try resetting your password...",
  "timestamp": "2024-01-15T10:05:00Z"
}

Response:
{
  "status": "ok",
  "ticket_id": 123,
  "message": "Response sent"
}

---

## Complete Workflow

### Automatic Ticket Monitoring (Current Implementation)

```
1. XMPP User sends message
   ↓
2. Openfire forwards to Client
   ↓
3. Client POSTs to /api/v1/webhooks/xmpp/incoming
   ↓
4. Backend creates ticket and returns ticket_id
   ↓
5. Client starts background polling thread for this user
   ↓
6. Thread polls every 3 seconds:
   - GET /api/v1/webhooks/xmpp/user/{jid}/active-ticket
   - GET /api/v1/webhooks/xmpp/tickets/{ticket_id}/messages
   ↓
7. When new AI/Agent messages arrive:
   - Client sends them to user via XMPP
   ↓
8. Thread stops when ticket is RESOLVED/CLOSED
```

### Required Backend Endpoints (for auto-monitoring)

**4. Get User's Active Ticket**
```
GET /api/v1/webhooks/xmpp/user/{user_jid}/active-ticket
Authorization: Bearer sk_your-api-key-here

Response (if active ticket exists):
{
  "ticket_id": "123",
  "status": "OPEN",
  "created_at": "2024-01-15T10:00:00Z"
}

Response (if no active ticket):
null or 404
```

**5. Get Ticket Messages**
```
GET /api/v1/webhooks/xmpp/tickets/{ticket_id}/messages?limit=20
Authorization: Bearer sk_your-api-key-here

Response:
[
  {
    "id": "msg_1",
    "content": "I need help with login",
    "message_type": "CUSTOMER",
    "sender": "user@domain.com",
    "is_customer": true,
    "timestamp": "2024-01-15T10:00:00Z"
  },
  {
    "id": "msg_2",
    "content": "Please try resetting your password...",
    "message_type": "AI",
    "sender": "AI Assistant",
    "is_customer": false,
    "timestamp": "2024-01-15T10:01:00Z"
  },
  {
    "id": "msg_3",
    "content": "I'll help you with that. Let me look into your account.",
    "message_type": "AGENT",
    "sender": "Support Agent",
    "is_customer": false,
    "timestamp": "2024-01-15T10:02:00Z"
  }
]

Note: Messages are ordered chronologically. Client tracks count to detect new messages.
```

### Message Flow Example

```
User (XMPP): "I can't login"
    ↓
Client → Backend: POST /webhooks/xmpp/incoming
    ← ticket_id: 123
    ↓
[Client starts polling thread]
    ↓
Poll: GET /user/{jid}/active-ticket → ticket_id: 123, status: OPEN
Poll: GET /tickets/123/messages → [msg1: "I can't login"]
    ↓
[AI responds on backend]
    ↓
Poll: GET /tickets/123/messages → [msg1, msg2: "Try resetting password"]
    ↓
Client → User (XMPP): "Try resetting password"
    ↓
User (XMPP): "That worked, thanks!"
    ↓
Client → Backend: POST /webhooks/xmpp/incoming (same thread)
    ↓
[Agent marks ticket RESOLVED]
    ↓
Poll: GET /user/{jid}/active-ticket → status: RESOLVED
    ↓
[Client stops polling thread]
```
