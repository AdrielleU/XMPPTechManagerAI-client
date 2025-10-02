✅ XMPP Integration Complete!

What Changed:

1. Moved to /backend/app/integrations/xmpp/ - XMPP is now a proper service integration
2. Created webhook handler - XMPPWebhookHandler processes incoming Openfire messages
3. Added webhook routes - /api/v1/webhooks/xmpp/ endpoints with API key auth
4. Removed /xmpp folder - Old bot code deleted

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
