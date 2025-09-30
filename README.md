# XMPP Client (Pidgin-like Python Client)

A Python-based XMPP client that mimics Pidgin's functionality while integrating with the ticket management API.

## Features

- **XMPP Protocol Support**: Full XMPP client implementation using slixmpp
- **Pidgin-like Storage**: Stores chat history in `~/.purple` directory structure
- **Ticket Integration**: Create support tickets directly from XMPP conversations
- **Rich CLI Interface**: Beautiful terminal UI using Rich library
- **Multi-account Support**: Connect to multiple XMPP servers
- **Message History**: Persistent chat history with search capabilities

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your credentials:
   ```ini
   XMPP_JID=your_username@example.com
   XMPP_PASSWORD=your_password
   XMPP_SERVER=xmpp.example.com  # Optional
   XMPP_PORT=5222  # Optional
   
   # API Integration (optional)
   API_BASE_URL=http://localhost:8000
   API_TOKEN=your_api_token
   ```

## Usage

### Basic Client

Run the interactive XMPP client:

```bash
python app/main.py
```

### Commands

- `/list` - Show all chats
- `/chat <jid>` - Open chat with a contact
- `/send <message>` - Send message to current chat
- `/ticket <message>` - Create support ticket
- `/quit` - Exit the client

### Creating Support Tickets

Users can create support tickets in two ways:

1. Using the `/ticket` command in the client
2. Sending messages starting with `/help`, `/support`, or `/ticket` to the bot

## Chat History

Chat history is stored in Pidgin-compatible format:

```
~/.purple/
├── logs/
│   └── xmpp/
│       └── user_at_example.com/
│           └── 2024-01-15.txt
├── accounts/
└── xmpp_settings.json
```

## API Integration

The client integrates with the ticket API to:

- Create tickets from XMPP messages
- Sync ticket status and updates
- Send follow-up messages to tickets
- Track user presence

### API Endpoints

The backend provides these XMPP-specific endpoints:

- `POST /api/v1/xmpp/tickets` - Create ticket from XMPP
- `GET /api/v1/xmpp/tickets` - List XMPP tickets
- `POST /api/v1/xmpp/tickets/{id}/messages` - Send ticket message
- `GET /api/v1/xmpp/tickets/{id}/sync` - Sync ticket updates
- `POST /api/v1/xmpp/presence` - Update presence status

## Development

### Project Structure

```
xmpp/
├── app/
│   ├── __init__.py
│   └── main.py         # Main CLI application
├── models/
│   ├── __init__.py
│   ├── chat.py         # Chat and Message models
│   └── ticket.py       # Ticket integration models
├── services/
│   ├── __init__.py
│   ├── xmpp_client.py  # XMPP client implementation
│   ├── storage.py      # Purple directory storage
│   └── api_client.py   # API integration client
├── utils/              # Utility functions
├── requirements.txt
├── .env.example
└── README.md
```

### Extending the Client

To add new features:

1. **New XMPP plugins**: Add to `XMPPClient.__init__()` in `services/xmpp_client.py`
2. **New commands**: Add to `handle_command()` in `app/main.py`
3. **API integration**: Extend `APIClient` in `services/api_client.py`

## Security

- Credentials are stored in `.env` file (never commit this)
- API tokens are used for backend authentication
- XMPP passwords are not stored in chat logs
- TLS/SSL is used for XMPP connections

## Troubleshooting

1. **Connection issues**: Check firewall and XMPP server settings
2. **Authentication fails**: Verify JID format (user@domain)
3. **No chat history**: Check `~/.purple` directory permissions
4. **API errors**: Ensure API token is valid and server is running