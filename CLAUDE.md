# XMPP Client Project - Claude Context

## Project Overview
Python-based XMPP client mimicking Pidgin functionality with ticket management API integration.

## Tech Stack
- **Language**: Python 3
- **XMPP Library**: slixmpp (>=1.8.3)
- **Async**: asyncio
- **HTTP Client**: httpx (>=0.24.1)
- **UI**: rich (>=13.5.2) for CLI
- **Data Validation**: pydantic (>=2.0.0)
- **File I/O**: aiofiles (>=23.2.1)
- **Config**: python-dotenv (>=1.0.0)
- **Date Utils**: python-dateutil (>=2.8.2)

## Project Structure
```
/home/pidgin-client/
├── app/
│   ├── __init__.py
│   └── main.py              # Main CLI application entry point
├── models/
│   ├── __init__.py
│   ├── chat.py              # Chat and Message data models
│   └── ticket.py            # Ticket integration models
├── services/
│   ├── __init__.py
│   ├── xmpp_client.py       # XMPP client implementation (slixmpp)
│   ├── storage.py           # Purple directory (~/.purple) storage
│   └── api_client.py        # API integration client
├── requirements.txt         # Python dependencies
├── README.md               # User documentation
├── CLAUDE.md              # This file - AI context
└── .env                   # Environment config (not in git)
```

## Key Features
1. **XMPP Protocol**: Full client using slixmpp
2. **Pidgin-Compatible Storage**: Chat logs in `~/.purple/` format
3. **Ticket Integration**: Create support tickets from XMPP messages
4. **Rich CLI**: Terminal UI with Rich library
5. **Multi-account Support**: Multiple XMPP connections
6. **Persistent History**: Searchable chat logs

## Setup & Running

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
# Edit .env with your XMPP credentials
```

### 4. Run Application
```bash
python app/main.py
```

### Deactivate Virtual Environment
```bash
deactivate
```

## Storage Format
```
~/.purple/
├── logs/xmpp/user_at_example.com/2024-01-15.txt
├── accounts/
└── xmpp_settings.json
```

## API Integration
Backend endpoints for ticket management:
- `POST /api/v1/xmpp/tickets` - Create ticket
- `GET /api/v1/xmpp/tickets` - List tickets
- `POST /api/v1/xmpp/tickets/{id}/messages` - Add message
- `GET /api/v1/xmpp/tickets/{id}/sync` - Sync updates
- `POST /api/v1/xmpp/presence` - Update presence

## Commands
- `/list` - Show all chats
- `/chat <jid>` - Open chat
- `/send <message>` - Send message
- `/ticket <message>` - Create ticket
- `/quit` - Exit

## Configuration
`.env` file contains:
- XMPP credentials (JID, password, server, port)
- API settings (base URL, token)

## Development Notes
- Async architecture throughout
- Pydantic models for data validation
- TLS/SSL for XMPP connections
- API token authentication
- Never commit `.env` file
