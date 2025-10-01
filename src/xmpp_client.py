#!/usr/bin/env python3
"""
XMPP Client Class - handles connection, authentication, and message handling
"""
import xmpp
import os
import threading
import queue
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class XMPPClient:
    def __init__(self, log_dir='.purple/logs'):
        self.connection = None
        self.jid = None
        self.stop_event = threading.Event()
        self.process_thread = None
        self.message_queue = queue.Queue()
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    def connect(self, jabberid=None, password=None, resource='Streamlit'):
        """Connect to XMPP server"""
        if not jabberid:
            jabberid = os.getenv('XMPP_JID', '')
        if not password:
            password = os.getenv('XMPP_PASSWORD', '')

        if not jabberid or not password:
            raise ValueError("JID and password are required")

        # Parse JID
        jid = xmpp.protocol.JID(jabberid)
        self.jid = jabberid

        # Create connection
        self.connection = xmpp.Client(server=jid.getDomain(), debug=False)

        # Connect without TLS
        result = self.connection.connect(secure=False)
        if not result:
            raise ConnectionError("Failed to connect to XMPP server")

        # Authenticate
        auth = self.connection.auth(user=jid.getNode(), password=password, resource=resource, sasl=1)
        if not auth:
            raise ConnectionError("Authentication failed")

        # Register handlers
        self.connection.RegisterHandler('message', self._message_handler)
        self.connection.RegisterHandler('presence', self._presence_handler)

        # Send presence
        self.connection.sendInitPresence()

        # Start background processing thread
        self.stop_event.clear()
        self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.process_thread.start()

        return True

    def disconnect(self):
        """Disconnect from XMPP server"""
        if self.connection:
            self.stop_event.set()
            if self.process_thread:
                self.process_thread.join(timeout=1)
            self.connection.disconnect()
            self.connection = None

    def send_message(self, to_jid, body):
        """Send a message"""
        if not self.connection:
            raise ConnectionError("Not connected")

        msg = xmpp.protocol.Message(to=to_jid, body=body, typ='chat')
        self.connection.send(msg)

        # Log sent message
        self._log_message(self.jid, to_jid, body, 'sent')

    def get_messages(self):
        """Get all queued messages"""
        messages = []
        while not self.message_queue.empty():
            try:
                messages.append(self.message_queue.get_nowait())
            except queue.Empty:
                break
        return messages

    def is_connected(self):
        """Check if connected"""
        return self.connection is not None and not self.stop_event.is_set()

    def _message_handler(self, conn, msg):
        """Handle incoming messages"""
        body = msg.getBody()
        sender = str(msg.getFrom())
        msg_type = msg.getType() or 'chat'

        # Skip protocol messages (no body)
        if not body:
            return

        # Log received message
        recipient = str(msg.getTo()) if msg.getTo() else self.jid
        self._log_message(sender, recipient, body, 'received')

        # Add to queue
        self.message_queue.put({
            'from': sender,
            'body': body,
            'type': msg_type,
            'timestamp': datetime.now().timestamp()
        })

    def _presence_handler(self, conn, pres):
        """Handle presence updates"""
        sender = str(pres.getFrom())
        pres_type = pres.getType()
        status = pres.getStatus()

        self.message_queue.put({
            'from': sender,
            'body': f"[Presence: {pres_type or 'available'}] {status or ''}",
            'type': 'presence',
            'timestamp': datetime.now().timestamp()
        })

    def _process_loop(self):
        """Background thread to process XMPP events"""
        try:
            while not self.stop_event.is_set():
                self.connection.Process(1)
        except Exception as e:
            self.message_queue.put({
                'from': 'System',
                'body': f"Error: {str(e)}",
                'type': 'error',
                'timestamp': datetime.now().timestamp()
            })

    def _log_message(self, sender, recipient, body, msg_type='received'):
        """Save message to text file organized by person and date"""
        try:
            # Determine conversation partner
            if msg_type == 'received':
                conversation_with = sender.split('/')[0]
            else:
                conversation_with = recipient.split('/')[0]

            # Create folder for this person
            person_folder = conversation_with.replace('@', '_at_')
            person_dir = os.path.join(self.log_dir, person_folder)
            os.makedirs(person_dir, exist_ok=True)

            # Create filename with just date (one file per day)
            now = datetime.now()
            date_str = now.strftime('%Y-%m-%d')
            filename = f"{date_str}.txt"
            filepath = os.path.join(person_dir, filename)

            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

            with open(filepath, 'a', encoding='utf-8') as f:
                if msg_type == 'received':
                    f.write(f"({timestamp}) {sender}: {body}\n")
                else:
                    f.write(f"({timestamp}) Me: {body}\n")
        except Exception:
            pass  # Silently fail


def main():
    """Command-line version"""
    client = XMPPClient()

    jabberid = os.getenv('XMPP_JID', '')
    password = os.getenv('XMPP_PASSWORD', '')

    print(f"Connecting as: {jabberid}")

    try:
        client.connect(jabberid, password, resource='Python')
        print("Connected successfully!")
        print("Status: Available")
        print("\nPress Ctrl+C to disconnect")

        while True:
            # Get and display new messages
            messages = client.get_messages()
            for msg in messages:
                if msg['type'] != 'presence':
                    print(f"{msg['from']}: {msg['body']}")

    except KeyboardInterrupt:
        print("\nDisconnecting...")
    finally:
        client.disconnect()

    return True


if __name__ == "__main__":
    main()
