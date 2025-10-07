#!/usr/bin/env python3
"""
XMPP Client Class - handles connection, authentication, and message handling
"""
import xmpp
import os
import threading
import queue
import requests
import time
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

        # API configuration
        self.api_base_url = os.getenv('API_BASE_URL', '')
        self.api_token = os.getenv('API_TOKEN', '')

        # Track active tickets per user
        self.user_tickets = {}  # {jid: {'ticket_id': str, 'last_message_count': int}}
        self.polling_threads = {}  # {jid: thread}

        # Track current log file counter per person/date
        self.log_counters = {}  # {person_folder: {date: counter}}

        # Track contacts from presence/messages (fallback for roster issues)
        self.discovered_contacts = set()  # Set of JIDs we've seen

    def connect(self, jabberid=None, password=None, resource=None):
        """Connect to XMPP server"""
        if not jabberid:
            # Construct JID from XMPP_USERNAME@XMPP_SERVER
            username = os.getenv('XMPP_USERNAME', '')
            server = os.getenv('XMPP_SERVER', '')
            if username and server:
                jabberid = f"{username}@{server}"
        if not password:
            password = os.getenv('XMPP_PASSWORD', '')
        if not resource:
            resource = os.getenv('XMPP_RESOURCE', 'Desktop')

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

        # Send presence (this automatically requests roster)
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

    def send_message(self, to_jid, body, from_ai=False):
        """Send a message

        Args:
            to_jid: Recipient JID
            body: Message content
            from_ai: If True, log as "AI Bot" instead of "Me"
        """
        if not self.connection:
            raise ConnectionError("Not connected")

        # Convert markdown links to plain URLs for XMPP compatibility
        body = self._convert_markdown_links(body)

        msg = xmpp.protocol.Message(to=to_jid, body=body, typ='chat')
        self.connection.send(msg)

        # Log sent message with appropriate sender label
        msg_type = 'ai_sent' if from_ai else 'sent'
        self._log_message(self.jid, to_jid, body, msg_type)

    def set_status(self, status='available', status_message=''):
        """Set XMPP presence status

        Args:
            status: One of 'available', 'away', 'xa' (extended away), 'dnd' (do not disturb), 'invisible'
            status_message: Optional custom status message
        """
        if not self.connection:
            raise ConnectionError("Not connected")

        # Map friendly names to XMPP show values
        show_mapping = {
            'available': None,  # No show element means available
            'away': 'away',
            'xa': 'xa',  # Extended Away
            'dnd': 'dnd',  # Do Not Disturb
            'invisible': None  # Handled by type='unavailable'
        }

        if status == 'invisible':
            # Send unavailable presence (appears offline)
            pres = xmpp.Presence(typ='unavailable')
            if status_message:
                pres.setStatus(status_message)
            self.connection.send(pres)
            print(f"Status set to: Invisible")
        else:
            # Send normal presence with show element
            pres = xmpp.Presence()
            show_value = show_mapping.get(status)

            if show_value:
                pres.setShow(show_value)

            if status_message:
                pres.setStatus(status_message)

            self.connection.send(pres)
            print(f"Status set to: {status.title()}" + (f" - {status_message}" if status_message else ""))

        return True

    def get_all_tickets(self, status=None, channel_source=None, skip=0, limit=100):
        """Get all tickets for organization from backend

        Args:
            status: Optional filter (values: open, in_progress, resolved, closed)
            channel_source: Optional filter (values: xmpp, webchat, email, etc.)
            skip: Pagination offset (default: 0)
            limit: Max results (default: 100, max: 100)

        Returns:
            dict with 'data' (list of tickets) and 'count' (int)
        """
        if not self.api_base_url or not self.api_token:
            return {'data': [], 'count': 0}

        try:
            url = f"{self.api_base_url}/api/v1/webhooks/xmpp/tickets"
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }

            params = {'skip': skip, 'limit': limit}
            if status:
                params['status'] = status
            if channel_source:
                params['channel_source'] = channel_source

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️  Failed to fetch tickets: {response.status_code}")
                print(f"   Response: {response.text}")
                return {'data': [], 'count': 0}

        except Exception as e:
            print(f"⚠️  Error fetching tickets: {e}")
            return {'data': [], 'count': 0}

    def fetch_ticket_updates(self):
        """Get currently active tickets being monitored

        Uses the existing webhook endpoint that works with API keys:
        GET /api/v1/webhooks/xmpp/tickets/{ticket_id}/messages
        """
        if not self.api_base_url or not self.api_token:
            return []

        tickets = []

        # Get all tickets we're currently monitoring
        for jid, ticket_info in list(self.user_tickets.items()):
            ticket_id = ticket_info.get('ticket_id')

            # Fetch messages for this ticket using the webhook endpoint
            try:
                url = f"{self.api_base_url}/api/v1/webhooks/xmpp/tickets/{ticket_id}/messages"
                headers = {
                    'Authorization': f'Bearer {self.api_token}',
                    'Content-Type': 'application/json'
                }

                response = requests.get(url, headers=headers, params={'limit': 5}, timeout=10)

                if response.status_code == 200:
                    messages = response.json()

                    # Get first customer message as subject
                    customer_msg = next((m for m in messages if m.get('is_customer')), None)

                    tickets.append({
                        'id': ticket_id,
                        'from_jid': jid,
                        'subject': f"Chat with {jid.split('@')[0]}",
                        'body': customer_msg.get('content', 'New conversation') if customer_msg else 'New conversation',
                        'status': ticket_info.get('status', 'open'),
                        'created_at': 'Active',
                        'message_count': len(messages)
                    })
                else:
                    print(f"⚠️  Could not fetch messages for ticket {ticket_id[:8]}: {response.status_code}")

            except Exception as e:
                print(f"⚠️  Error fetching ticket {ticket_id[:8]}: {e}")

        print(f"📋 Found {len(tickets)} active tickets")
        return tickets

    def send_ticket_response(self, ticket_id, response_text, to_jid=None):
        """Send response to a ticket and notify user via XMPP"""
        if not self.api_base_url or not self.api_token:
            print("⚠️  API not configured")
            return False

        try:
            url = f"{self.api_base_url}/api/v1/tickets/{ticket_id}/respond"
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            payload = {
                'response': response_text,
                'timestamp': datetime.now().isoformat() + 'Z'
            }

            print(f"\n📤 Sending response to ticket #{ticket_id}")
            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                print(f"   ✅ Response saved to ticket #{ticket_id}")

                # Send XMPP message to user if JID provided (mark as AI-sent)
                if to_jid and self.connection:
                    self.send_message(to_jid, response_text, from_ai=True)
                    print(f"   ✅ XMPP message sent to {to_jid}")

                return True
            else:
                print(f"   ❌ Failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error sending ticket response: {e}")
            return False

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

    def get_roster(self):
        """Get list of contacts from XMPP roster with fallback strategies

        Returns:
            list: List of dicts with 'jid', 'name', and 'subscription' keys
        """
        if not self.connection:
            return []

        contacts = []

        # Strategy 1: Try to get from XMPP roster (may fail with XML errors)
        try:
            roster = self.connection.Roster
            if roster:
                items = roster.getItems()
                if items:
                    for jid in items:
                        try:
                            item = roster.getItem(jid)
                            if item:
                                name = item.get('name') or jid.split('@')[0]
                                contacts.append({
                                    'jid': jid,
                                    'name': name,
                                    'subscription': item.get('subscription', 'none')
                                })
                        except Exception:
                            continue

                    if contacts:
                        contacts.sort(key=lambda x: x['name'].lower())
                        return contacts
        except Exception as e:
            print(f"Roster unavailable (this is OK): {e}")

        # Strategy 2: Use discovered contacts from presence/messages
        if self.discovered_contacts:
            print(f"Using {len(self.discovered_contacts)} discovered contacts")
            for jid in sorted(self.discovered_contacts):
                contacts.append({
                    'jid': jid,
                    'name': jid.split('@')[0],
                    'subscription': 'discovered'
                })
            return contacts

        # Strategy 3: Get contacts from message log directories
        try:
            if os.path.exists(self.log_dir):
                # Look for current username folder (just username, not full JID)
                bare_jid = self.jid.split('/')[0]
                current_username = bare_jid.split('@')[0]
                jid_log_dir = os.path.join(self.log_dir, current_username)

                if os.path.exists(jid_log_dir):
                    # Get person folders under current JID folder
                    for folder in os.listdir(jid_log_dir):
                        folder_path = os.path.join(jid_log_dir, folder)
                        if os.path.isdir(folder_path):
                            # Convert folder name back to JID
                            jid = folder.replace('_at_', '@')
                            contacts.append({
                                'jid': jid,
                                'name': jid.split('@')[0],
                                'subscription': 'from_logs'
                            })

            if contacts:
                contacts.sort(key=lambda x: x['name'].lower())
                print(f"Using {len(contacts)} contacts from message logs")
                return contacts
        except Exception as e:
            print(f"Error reading log directories: {e}")

        print("No contacts found")
        return []

    def _message_handler(self, conn, msg):
        """Handle incoming messages"""
        body = msg.getBody()
        sender = str(msg.getFrom())
        msg_type = msg.getType() or 'chat'

        # Skip protocol messages (no body)
        if not body:
            return

        # Track this contact (bare JID without resource)
        bare_jid = sender.split('/')[0]
        if bare_jid and '@' in bare_jid:
            self.discovered_contacts.add(bare_jid)

        # Log received message
        recipient = str(msg.getTo()) if msg.getTo() else self.jid
        self._log_message(sender, recipient, body, 'received')

        # Get optional metadata (can be enhanced later to fetch from roster/vCard)
        sender_metadata = self._get_sender_metadata(sender)

        # Send to API webhook if configured
        self._send_to_api(sender, recipient, body, msg_type, sender_metadata)

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

        # Track this contact (bare JID without resource)
        bare_jid = sender.split('/')[0]
        if bare_jid and '@' in bare_jid and bare_jid != self.jid:
            self.discovered_contacts.add(bare_jid)

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

    def _get_sender_metadata(self, sender_jid):
        """Get metadata about sender from XMPP roster/vCard

        Returns dict with optional fields:
        - sender_name: Display name from roster or vCard
        - sender_email: Email from vCard
        - sender_groups: Roster groups the sender belongs to

        Note: This is a basic implementation. Can be enhanced to:
        1. Query vCard for full name and email
        2. Query roster for groups
        3. Cache results to avoid repeated lookups
        """
        metadata = {}

        try:
            if not self.connection:
                return metadata

            # Get bare JID (without resource)
            bare_jid = sender_jid.split('/')[0]

            # Try to get roster item
            roster = self.connection.getRoster()
            if roster:
                roster_item = roster.getItem(bare_jid)
                if roster_item:
                    # Get display name from roster
                    name = roster_item.get('name')
                    if name:
                        metadata['sender_name'] = name

                    # Get groups from roster
                    groups = roster_item.get('groups', [])
                    if groups:
                        metadata['sender_groups'] = groups

            # TODO: Query vCard for email and full name
            # This requires implementing vCard IQ queries
            # For now, metadata extraction from roster only

        except Exception as e:
            # Silently fail - metadata is optional
            print(f"   ⚠️  Could not fetch metadata for {sender_jid}: {e}")

        return metadata

    def _send_to_api(self, from_jid, to_jid, body, msg_type, sender_metadata=None):
        """Send incoming message to API webhook

        Args:
            from_jid: Sender's JID (REQUIRED)
            to_jid: Recipient JID (REQUIRED)
            body: Message content (REQUIRED)
            msg_type: Message type (default: 'chat')
            sender_metadata: Optional dict with sender_name, sender_email, sender_groups
        """
        if not self.api_base_url or not self.api_token:
            print("⚠️  API not configured (missing API_BASE_URL or API_TOKEN)")
            return

        try:
            url = f"{self.api_base_url}/api/v1/webhooks/xmpp/incoming"
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }

            # Required fields
            payload = {
                'from_jid': from_jid,
                'to_jid': to_jid,
                'body': body,
                'message_type': msg_type,
                'timestamp': datetime.now().isoformat() + 'Z'
            }

            # Optional fields - only include if provided
            if sender_metadata:
                if sender_metadata.get('sender_name'):
                    payload['sender_name'] = sender_metadata['sender_name']
                if sender_metadata.get('sender_email'):
                    payload['sender_email'] = sender_metadata['sender_email']
                if sender_metadata.get('sender_groups'):
                    payload['sender_groups'] = sender_metadata['sender_groups']
                if sender_metadata.get('thread_id'):
                    payload['thread_id'] = sender_metadata['thread_id']

            print(f"\n📤 Sending message to API webhook")
            print(f"   URL: {url}")
            print(f"   From: {from_jid}")
            print(f"   To: {to_jid}")
            print(f"   Body: {body[:50]}..." if len(body) > 50 else f"   Body: {body}")
            print(f"   Headers: Authorization: Bearer {self.api_token[:20]}...")

            response = requests.post(url, json=payload, headers=headers, timeout=10)

            print(f"\n📥 API Response:")
            print(f"   Status Code: {response.status_code}")

            if response.status_code == 200:
                print(f"   ✅ SUCCESS - Message delivered to backend")
                try:
                    response_data = response.json()
                    print(f"   Response: {response_data}")

                    # Extract ticket_id and start monitoring
                    ticket_id = response_data.get('ticket_id')
                    if ticket_id:
                        # Store both full JID (sent to backend) and bare JID (for lookups)
                        bare_jid = from_jid.split('/')[0]  # Remove resource
                        full_jid = from_jid  # Keep resource for API calls

                        print(f"\n🔍 JID Debug:")
                        print(f"   Full JID sent to backend: {full_jid}")
                        print(f"   Bare JID for monitoring: {bare_jid}")

                        # Start monitoring this ticket if not already monitoring
                        if bare_jid not in self.polling_threads or not self.polling_threads[bare_jid].is_alive():
                            print(f"\n👀 Starting ticket monitor for {bare_jid} (ticket {ticket_id})")
                            self.user_tickets[bare_jid] = {
                                'ticket_id': ticket_id,
                                'last_message_count': 0,
                                'status': 'OPEN',
                                'full_jid': full_jid  # Store for API calls if needed
                            }

                            # Start background polling thread
                            poll_thread = threading.Thread(
                                target=self._monitor_ticket_until_resolved,
                                args=(bare_jid,),
                                daemon=True
                            )
                            poll_thread.start()
                            self.polling_threads[bare_jid] = poll_thread
                        else:
                            print(f"\n♻️  Already monitoring ticket for {bare_jid}")
                except Exception as e:
                    print(f"   ⚠️  Error processing response: {e}")
                    print(f"   Response: {response.text}")
            else:
                print(f"   ❌ FAILED - Non-200 status code")
                print(f"   Response: {response.text}")

            response.raise_for_status()

        except requests.exceptions.HTTPError as e:
            print(f"\n❌ HTTP Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Status: {e.response.status_code}")
                print(f"   Response Body: {e.response.text}")
        except requests.exceptions.ConnectionError as e:
            print(f"\n❌ Connection Error: Cannot reach {url}")
            print(f"   Details: {e}")
        except requests.exceptions.Timeout as e:
            print(f"\n❌ Timeout Error: Request took longer than 10 seconds")
            print(f"   Details: {e}")
        except requests.exceptions.RequestException as e:
            print(f"\n❌ Request Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Status: {e.response.status_code}")
                print(f"   Response: {e.response.text}")
        except Exception as e:
            print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")

    def _monitor_ticket_until_resolved(self, user_jid):
        """Continuously monitor a ticket until it's resolved"""
        poll_interval = 3  # Check every 3 seconds
        consecutive_errors = 0
        max_errors = 5

        while not self.stop_event.is_set():
            try:
                # Get ticket info (from cache)
                if user_jid not in self.user_tickets:
                    print(f"\n✅ Ticket monitor stopped - no cached ticket for {user_jid}")
                    break

                ticket_id = self.user_tickets[user_jid].get('ticket_id')
                status = self.user_tickets[user_jid].get('status', 'OPEN')

                print(f"   🔄 Polling ticket {ticket_id[:8]}... (status: {status})")

                # Check if ticket is resolved/closed
                if status in ['RESOLVED', 'CLOSED']:
                    print(f"\n✅ Ticket {ticket_id} {status} for {user_jid}")
                    self.user_tickets.pop(user_jid, None)
                    break

                # Check for new messages
                new_messages = self._get_new_ticket_messages(user_jid, ticket_id)

                if new_messages is None:
                    # Error fetching messages
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        print(f"\n⚠️  Too many errors polling {user_jid} - stopping monitor")
                        self.user_tickets.pop(user_jid, None)
                        break
                else:
                    consecutive_errors = 0  # Reset error count

                    for msg in new_messages:
                        content = msg.get('content')
                        msg_type = msg.get('message_type')  # "AGENT" or "AI"
                        sender = msg.get('sender', 'Unknown')
                        is_customer = msg.get('is_customer', False)

                        # Only send non-customer messages (AI/AGENT responses)
                        if not is_customer and content:
                            print(f"\n🤖 [{msg_type}] {sender}: New response for {user_jid}")
                            print(f"   {content[:100]}...")
                            # Mark as AI-sent so it shows as "AI Bot" in logs
                            self.send_message(user_jid, content, from_ai=True)
                            print(f"   ✅ Sent to {user_jid}")

                        # Check if this message indicates ticket is resolved
                        if msg.get('ticket_status') in ['RESOLVED', 'CLOSED']:
                            self.user_tickets[user_jid]['status'] = msg.get('ticket_status')

                time.sleep(poll_interval)

            except Exception as e:
                print(f"\n⚠️  Monitor error for {user_jid}: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_errors:
                    print(f"\n⚠️  Too many errors - stopping monitor for {user_jid}")
                    self.user_tickets.pop(user_jid, None)
                    break
                time.sleep(poll_interval * 2)  # Back off on errors

        print(f"📴 Stopped monitoring {user_jid}")

    def _get_active_ticket(self, user_jid):
        """Check if user has an active ticket"""
        if not self.api_base_url or not self.api_token:
            return None

        # First check if we already have ticket info stored locally
        if user_jid in self.user_tickets:
            ticket_info = self.user_tickets[user_jid]
            ticket_id = ticket_info.get('ticket_id')
            print(f"   📦 Using cached ticket: {ticket_id}")

            # Simply return cached info - we'll check messages to determine if still active
            return ticket_info

        # If not cached, try querying by JID
        try:
            # Try bare JID first
            url = f"{self.api_base_url}/api/v1/webhooks/xmpp/user/{user_jid}/active-ticket"
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }

            print(f"   🔍 Checking active ticket: {url}")
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                ticket_data = response.json()
                print(f"   🎫 Active ticket for {user_jid}: {ticket_data.get('ticket_id') if ticket_data else 'None'}")
                return ticket_data if ticket_data else None
            elif response.status_code == 404:
                print(f"   ℹ️  No active ticket found for {user_jid}")
                return None
            else:
                print(f"⚠️  Error checking active ticket: {response.status_code}")
                print(f"   Response: {response.text}")
                return None

        except Exception as e:
            print(f"⚠️  Error checking active ticket: {e}")
            return None

    def _get_new_ticket_messages(self, user_jid, ticket_id):
        """Get new messages from a ticket since last check

        Returns:
            list: New messages (empty list if none)
            None: On error
        """
        if not self.api_base_url or not self.api_token:
            return []

        try:
            url = f"{self.api_base_url}/api/v1/webhooks/xmpp/tickets/{ticket_id}/messages"
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }

            response = requests.get(url, headers=headers, params={'limit': 20}, timeout=10)

            if response.status_code == 200:
                messages = response.json()

                # Get count of messages we've already seen
                last_count = self.user_tickets[user_jid].get('last_message_count', 0)
                total_messages = len(messages)

                print(f"   📊 {total_messages} total msg, {last_count} seen, {total_messages - last_count} new")

                # Only return new messages (ones we haven't sent yet)
                if total_messages > last_count:
                    new_messages = messages[last_count:]
                    self.user_tickets[user_jid]['last_message_count'] = total_messages
                    return new_messages

                return []  # No new messages
            elif response.status_code == 404:
                print(f"   ⚠️  Ticket {ticket_id[:8]}... not found (404)")
                return None  # Error - ticket not found
            else:
                print(f"   ⚠️  Failed to fetch messages: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return None  # Error

        except Exception as e:
            print(f"   ⚠️  Error fetching messages: {e}")
            return None  # Error

    def _convert_markdown_links(self, text):
        """Convert markdown-style links to plain URLs for XMPP clients

        Converts [https://example.com](https://example.com) to https://example.com
        """
        import re
        # Pattern matches [text](url)
        pattern = r'\[([^\]]+)\]\(([^\)]+)\)'

        def replace_link(match):
            link_text = match.group(1)
            link_url = match.group(2)
            # If text and URL are the same, just return the URL
            if link_text == link_url:
                return link_url
            # Otherwise, return "text: url" format
            return f"{link_text}: {link_url}"

        return re.sub(pattern, replace_link, text)

    def _log_message(self, sender, recipient, body, msg_type='received'):
        """Save message to text file organized by current JID, then by person and date with sequential numbering"""
        try:
            # Determine conversation partner
            if msg_type == 'received':
                conversation_with = sender.split('/')[0]
            else:
                conversation_with = recipient.split('/')[0]

            # Create folder for current logged-in user (just username, not full JID)
            bare_jid = self.jid.split('/')[0]  # Remove resource if present
            current_username = bare_jid.split('@')[0]  # Just the username part
            jid_log_dir = os.path.join(self.log_dir, current_username)
            os.makedirs(jid_log_dir, exist_ok=True)

            # Create folder for conversation partner under current JID folder
            person_folder = conversation_with.replace('@', '_at_')
            person_dir = os.path.join(jid_log_dir, person_folder)
            os.makedirs(person_dir, exist_ok=True)

            # Get current date
            now = datetime.now()
            date_str = now.strftime('%Y-%m-%d')

            # Create unique key for counter tracking (current_username/person_folder)
            counter_key = f"{current_username}/{person_folder}"

            # Initialize counter tracking for this person if needed
            if counter_key not in self.log_counters:
                self.log_counters[counter_key] = {}

            # Determine current counter for today
            if date_str not in self.log_counters[counter_key]:
                # Find highest existing counter for today
                import glob
                existing_files = glob.glob(os.path.join(person_dir, f"{date_str}_*.txt"))
                if existing_files:
                    # Extract counters from filenames
                    counters = []
                    for filepath in existing_files:
                        filename = os.path.basename(filepath)
                        # Extract counter from YYYY-MM-DD_XXX.txt
                        try:
                            counter_str = filename.split('_')[-1].replace('.txt', '')
                            counters.append(int(counter_str))
                        except (ValueError, IndexError):
                            pass
                    self.log_counters[counter_key][date_str] = max(counters) if counters else 1
                else:
                    self.log_counters[counter_key][date_str] = 1

            counter = self.log_counters[counter_key][date_str]
            filename = f"{date_str}_{counter:03d}.txt"
            filepath = os.path.join(person_dir, filename)

            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

            # Write message to file
            with open(filepath, 'a', encoding='utf-8') as f:
                if msg_type == 'received':
                    f.write(f"({timestamp}) {sender}: {body}\n")
                elif msg_type == 'ai_sent':
                    f.write(f"({timestamp}) AI Bot: {body}\n")
                else:  # msg_type == 'sent'
                    f.write(f"({timestamp}) Me: {body}\n")

            # Check if this is a sent message containing "closing ticket"
            # If so, increment counter for next message
            if msg_type in ['sent', 'ai_sent'] and 'closing ticket' in body.lower():
                self.log_counters[counter_key][date_str] += 1
                print(f"   📝 Rotating log file for {counter_key} (ticket closed)")

        except Exception as e:
            pass  # Silently fail


def main():
    """Command-line version"""
    client = XMPPClient()

    # Construct JID from XMPP_USERNAME@XMPP_SERVER
    username = os.getenv('XMPP_USERNAME', '')
    server = os.getenv('XMPP_SERVER', '')
    jabberid = f"{username}@{server}" if username and server else ''
    password = os.getenv('XMPP_PASSWORD', '')

    print(f"Connecting as: {jabberid}")

    try:
        client.connect(jabberid, password)  # Uses XMPP_RESOURCE from .env
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
