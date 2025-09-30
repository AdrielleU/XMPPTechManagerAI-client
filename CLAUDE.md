# XMPP Client Project - Development Context

## Quick Reference

**Project Root:** `/home/pidgin-client/`
**Entry Point:** `main.py`
**Language:** Python 3
**Main Library:** xmpppy (XMPP protocol)

## Project Structure

```
pidgin-client/
├── main.py                 # Entry point
├── src/
│   ├── __init__.py
│   └── xmpp_client.py     # Core XMPP client implementation
├── .env                    # Credentials (not in git)
├── .env.example           # Template for credentials
├── requirements.txt       # Python dependencies
├── venv/                  # Virtual environment
└── .purple/               # Pidgin-compatible storage (created at runtime)
```

## Architecture Overview

### Core Components

1. **XMPP Client** (`src/xmpp_client.py`)
   - Simple xmpppy-based XMPP client
   - Handles connection, authentication, presence
   - Non-TLS connection (secure=False) for compatibility
   - SASL PLAIN authentication

2. **Main Entry** (`main.py`)
   - Imports and runs the XMPP client
   - Simple wrapper for execution

## Key Technologies

| Purpose | Library | Notes |
|---------|---------|-------|
| XMPP Protocol | xmpppy 0.7.2 | Simple, synchronous XMPP library |
| Config | python-dotenv | Environment variable management |

## Current Implementation

### Connection Flow
1. Load credentials from `.env`
2. Parse JID (jabber ID)
3. Create xmpp.Client with server domain
4. Connect with `secure=False` (no TLS)
5. Authenticate with SASL (PLAIN mechanism preferred)
6. Send initial presence (Available)
7. Process messages in loop until Ctrl+C

### Important Note: SASL Authentication
The xmpppy library has been patched to prefer PLAIN over DIGEST-MD5:
- Modified file: `venv/lib64/python3.9/site-packages/xmpp/auth.py`
- Changed lines 153-163 to try PLAIN before DIGEST-MD5
- This was necessary because DIGEST-MD5 implementation has a bug with the challenge response

## Configuration

### Environment Variables (.env)
- `XMPP_JID` - User JID (e.g., adrielleu@10.143.121.140)
- `XMPP_PASSWORD` - XMPP password
- `XMPP_SERVER` - (Optional) Server override
- `XMPP_PORT` - (Optional) Port override (default: 5222)

### Server Details
- Current server: OpenFire at 10.143.121.140
- Port: 5222
- Connection: Non-TLS (plaintext)
- Auth mechanisms: PLAIN, SCRAM-SHA-1, CRAM-MD5, DIGEST-MD5

## Running the Client

### Activate Virtual Environment
**Linux/Mac:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

### Run Client
```bash
python main.py
```

### Expected Output
```
Connecting as: user@domain
Connected: tcp
Authenticating user: user
Authenticated successfully!
Status: Available

Press Ctrl+C to disconnect
```

## Development Notes

### Adding Features
1. **Message Handling** - Add event handlers in xmpp_client.py
2. **Roster Management** - Use connection.getRoster()
3. **Send Messages** - Use connection.send(xmpp.protocol.Message(...))

### Common Patterns

**Send a message:**
```python
msg = xmpp.protocol.Message(to='user@domain', body='Hello', typ='chat')
connection.send(msg)
```

**Add message handler:**
```python
def message_handler(conn, msg):
    if msg.getBody():
        print(f"Got: {msg.getBody()}")

connection.RegisterHandler('message', message_handler)
```

## Security Notes

- Currently using non-TLS connection (secure=False)
- PLAIN authentication over unencrypted stream
- Never commit `.env` file (already in `.gitignore`)
- Passwords not logged (masked with asterisks)

## Troubleshooting

### Authentication Fails
- Check credentials in `.env`
- Ensure no quotes around password
- Verify server accepts PLAIN auth

### Connection Hangs
- Check `Process(1)` loop - should be `while True:` not `while connection.Process(1):`
- Ensure network can reach server:port

### Import Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

## Project Status

**Current State:** Basic working client
**Main Branch:** main
**Last Commit:** Start of XMPP client to link with TechManagerAI

## Next Steps

- [x] Basic connection and authentication
- [x] Send presence (Available status)
- [ ] Receive and display messages
- [ ] Send messages to contacts
- [ ] Roster/contact list management
- [ ] Certificate handling (save to .purple/)
- [ ] Message history storage
- [ ] Multiple status types (Away, DND, etc.)
