# XMPP API Endpoints & Examples

## 1. Create XMPP Ticket

**Endpoint:** `POST /api/v1/xmpp/tickets`

```bash
curl -X POST http://localhost:8000/api/v1/xmpp/tickets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jid": "user@example.com",
    "message": "I need help configuring my email client",
    "resource": "desktop"
  }'
```

**Result:**
```json
{
  "success": true,
  "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
  "subject": "Email Client Configuration Help",
  "status": "OPEN"
}
```

## 2. List XMPP Tickets

**Endpoint:** `GET /api/v1/xmpp/tickets`

### Get all your XMPP tickets
```bash
curl -X GET "http://localhost:8000/api/v1/xmpp/tickets" \
  -H "Authorization: Bearer $TOKEN"
```

### Filter by JID
```bash
curl -X GET "http://localhost:8000/api/v1/xmpp/tickets?jid=user@example.com" \
  -H "Authorization: Bearer $TOKEN"
```

### Filter by status
```bash
curl -X GET "http://localhost:8000/api/v1/xmpp/tickets?status=OPEN&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Result:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "subject": "Email Client Configuration Help",
    "status": "OPEN",
    "priority": "NORMAL",
    "jid": "user@example.com",
    "created_at": "2024-01-15T10:00:00Z",
    "last_message": "2024-01-15T10:05:00Z"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440111",
    "subject": "Connection Issues",
    "status": "RESOLVED",
    "priority": "HIGH",
    "jid": "user@example.com",
    "created_at": "2024-01-14T14:00:00Z",
    "last_message": "2024-01-14T15:30:00Z"
  }
]
```

## 3. Send XMPP Message to Ticket

**Endpoint:** `POST /api/v1/xmpp/tickets/{ticket_id}/messages`

```bash
curl -X POST http://localhost:8000/api/v1/xmpp/tickets/550e8400-e29b-41d4-a716-446655440000/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "I am using Thunderbird on Ubuntu 22.04",
    "jid": "user@example.com"
  }'
```

**Result:**
```json
{
  "success": true,
  "message_id": "msg-123",
  "timestamp": "2024-01-15T10:05:00Z"
}
```

## 4. Sync XMPP Ticket (Get Updates)

**Endpoint:** `GET /api/v1/xmpp/tickets/{ticket_id}/sync`

```bash
curl -X GET http://localhost:8000/api/v1/xmpp/tickets/550e8400-e29b-41d4-a716-446655440000/sync \
  -H "Authorization: Bearer $TOKEN"
```

**Result:**
```json
{
  "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "OPEN",
  "subject": "Email Client Configuration Help",
  "messages": [
    {
      "id": "msg-001",
      "content": "I need help configuring my email client",
      "sender": "You",
      "timestamp": "2024-01-15T10:00:00Z",
      "is_agent": false
    },
    {
      "id": "msg-002",
      "content": "I'll help you configure your email client. What email service are you using?",
      "sender": "AI Assistant",
      "timestamp": "2024-01-15T10:00:05Z",
      "is_agent": true
    },
    {
      "id": "msg-003",
      "content": "I am using Thunderbird on Ubuntu 22.04",
      "sender": "You",
      "timestamp": "2024-01-15T10:05:00Z",
      "is_agent": false
    },
    {
      "id": "msg-004",
      "content": "Great! For Thunderbird on Ubuntu, here are the steps...",
      "sender": "AI Assistant",
      "timestamp": "2024-01-15T10:05:10Z",
      "is_agent": true
    }
  ],
  "updated_at": "2024-01-15T10:05:10Z"
}
```

## 5. Update XMPP Presence

**Endpoint:** `POST /api/v1/xmpp/presence`

```bash
curl -X POST http://localhost:8000/api/v1/xmpp/presence \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jid": "user@example.com",
    "status": "available",
    "show": "chat"
  }'
```

**Result:**
```json
{
  "success": true,
  "jid": "user@example.com",
  "status": "available"
}
```