# XMPP Client (Simple Python XMPP Client)

A simple Python-based XMPP client using xmpppy that connects to XMPP servers.

## Features

- **XMPP Protocol Support**: XMPP client implementation using xmpppy
- **Simple & Clean**: Minimalistic design, easy to understand and extend
- **OpenFire Compatible**: Works with OpenFire and other XMPP servers
- **Presence Support**: Set status to Available, Away, etc.
- **Non-TLS Mode**: Connect without TLS for compatibility

## Setup

### 1. Create Virtual Environment

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```ini
# XMPP Configuration
XMPP_JID=username@10.143.121.140
XMPP_PASSWORD=your_password
XMPP_SERVER=
XMPP_PORT=5222
```

**Important:** Do not put quotes around the password value.

### 4. Run the Application

```bash
python main.py
```

Expected output:
```
Connecting as: username@10.143.121.140
Connected: tcp
Authenticating user: username
Authenticated successfully!
Status: Available

Press Ctrl+C to disconnect
```

### Deactivate Virtual Environment
```bash
deactivate
```

## Requirements

- Python 3.9+
- xmpppy 0.7.2
- python-dotenv

## Project Structure

```
pidgin-client/
├── main.py                 # Entry point - runs the XMPP client
├── src/
│   ├── __init__.py
│   └── xmpp_client.py     # Core XMPP client implementation
├── .env                    # Your credentials (not in git)
├── .env.example           # Template for credentials
├── requirements.txt       # Python dependencies
├── venv/                  # Virtual environment (created by setup)
├── .purple/               # Pidgin-compatible storage (future use)
├── README.md              # This file
└── CLAUDE.md              # Developer context and notes
```

## How It Works

1. **Load credentials** from `.env` file
2. **Parse JID** (Jabber ID) into username and domain
3. **Create XMPP client** with server domain
4. **Connect** to server without TLS (`secure=False`)
5. **Authenticate** using SASL PLAIN mechanism
6. **Send presence** to appear as "Available"
7. **Stay online** and process messages until Ctrl+C

## Technical Details

### Authentication
- Uses SASL PLAIN authentication
- xmpppy library was patched to prefer PLAIN over DIGEST-MD5
- Modified file: `venv/lib64/python3.9/site-packages/xmpp/auth.py`

### Connection
- Non-TLS connection mode (`secure=False`)
- Default port: 5222
- Synchronous message processing

### Tested With
- OpenFire server at 10.143.121.140
- Port 5222
- PLAIN authentication

## Development

See `CLAUDE.md` for detailed development context and notes.

### Adding Features

**Receive messages:**
```python
def message_handler(conn, msg):
    if msg.getBody():
        print(f"Message from {msg.getFrom()}: {msg.getBody()}")

connection.RegisterHandler('message', message_handler)
```

**Send messages:**
```python
msg = xmpp.protocol.Message(to='user@domain', body='Hello!', typ='chat')
connection.send(msg)
```

**Get roster (contact list):**
```python
roster = connection.getRoster()
```

## Troubleshooting

### Authentication Fails
- Check credentials in `.env`
- Ensure password has NO quotes around it
- Verify username is correct (without @domain part)

### Connection Hangs
- Ensure `Process()` loop uses `while True:` not `while connection.Process(1):`
- Check network connectivity to server:port

### Import Errors
- Activate virtual environment first
- Run `pip install -r requirements.txt`

### Module Not Found: xmpp
- The library is called `xmpppy` but imported as `xmpp`
- Install with: `pip install xmpppy`

## Security Notes

- Using non-TLS connection (plaintext)
- PLAIN authentication over unencrypted stream
- Never commit `.env` file (already in `.gitignore`)
- Suitable for internal/trusted networks

## Future Enhancements

- [ ] Receive and display messages
- [ ] Send messages to contacts
- [ ] Roster/contact list display
- [ ] TLS/SSL support
- [ ] Certificate handling (save to .purple/)
- [ ] Message history storage
- [ ] Multiple status types (Away, DND, etc.)
- [ ] Group chat support

## License

This project is for internal use and development.
