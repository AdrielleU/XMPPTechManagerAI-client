#!/usr/bin/env python3
"""
Streamlit Web UI for XMPP Client
"""
import streamlit as st
import os
import time
from src.xmpp_client import XMPPClient

# Message log directory
LOG_DIR = os.path.join(os.path.dirname(__file__), '.purple', 'logs')

# Initialize session state
if 'xmpp_client' not in st.session_state:
    st.session_state.xmpp_client = None

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'connected' not in st.session_state:
    st.session_state.connected = False


def connect_xmpp():
    """Connect to XMPP server"""
    try:
        client = XMPPClient(log_dir=LOG_DIR)
        client.connect(resource='x105')

        st.session_state.xmpp_client = client
        st.session_state.connected = True

        st.session_state.messages.append({
            'from': 'System',
            'body': f"Connected as {client.jid}",
            'type': 'system',
            'timestamp': time.time()
        })

        return True

    except Exception as e:
        st.error(f"Connection error: {str(e)}")
        return False


def disconnect_xmpp():
    """Disconnect from XMPP server"""
    if st.session_state.xmpp_client:
        st.session_state.xmpp_client.disconnect()
        st.session_state.xmpp_client = None
        st.session_state.connected = False

        st.session_state.messages.append({
            'from': 'System',
            'body': 'Disconnected',
            'type': 'system',
            'timestamp': time.time()
        })


def send_message(to_jid, body):
    """Send XMPP message"""
    if not st.session_state.xmpp_client or not st.session_state.connected:
        st.error("Not connected!")
        return

    try:
        st.session_state.xmpp_client.send_message(to_jid, body)

        # Add directly to session state for sent messages
        st.session_state.messages.append({
            'from': 'Me',
            'body': f"To {to_jid}: {body}",
            'type': 'sent',
            'timestamp': time.time()
        })
    except Exception as e:
        st.error(f"Failed to send: {str(e)}")


# Streamlit UI
st.title("XMPP Client")

# Page navigation
page = st.sidebar.radio("Page", ["Chat", "Tickets"])

st.sidebar.divider()

# Drain message queue into session state
if st.session_state.xmpp_client:
    messages = st.session_state.xmpp_client.get_messages()
    for msg in messages:
        st.session_state.messages.append(msg)

# Sidebar controls
with st.sidebar:
    st.header("Connection")

    if not st.session_state.connected:
        if st.button("Connect", use_container_width=True):
            connect_xmpp()
            st.rerun()
    else:
        st.success("Connected")
        if st.button("Disconnect", use_container_width=True):
            disconnect_xmpp()
            st.rerun()

    st.divider()

    # Send message form
    st.header("Send Message")
    to_jid = st.text_input("To (JID)")
    message_body = st.text_area("Message")

    if st.button("Send", use_container_width=True, disabled=not st.session_state.connected):
        if to_jid and message_body:
            send_message(to_jid, message_body)
            st.rerun()
        else:
            st.warning("Enter both JID and message")

    st.divider()

    # Clear messages
    if st.button("Clear Messages", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # Auto-refresh
    st.header("Settings")
    auto_refresh = st.checkbox("Auto-refresh", value=True)
    if auto_refresh:
        refresh_interval = st.slider("Refresh interval (seconds)", 1, 10, 3)

# Page content
if page == "Tickets":
    # ===== TICKETS PAGE =====
    st.header("Support Tickets")

    if not st.session_state.connected:
        st.warning("⚠️ Connect to XMPP first to manage tickets")
    else:
        # Fetch tickets button
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔄 Refresh Tickets", use_container_width=True):
                st.rerun()

        # Fetch tickets from API
        if st.session_state.xmpp_client:
            tickets = st.session_state.xmpp_client.fetch_ticket_updates()

            if tickets:
                st.success(f"Found {len(tickets)} pending tickets")

                # Display each ticket
                for ticket in tickets:
                    with st.expander(f"🎫 Ticket #{ticket.get('id', 'N/A')} - {ticket.get('subject', 'No subject')}"):
                        # Ticket details
                        st.write(f"**From:** {ticket.get('from_jid', 'Unknown')}")
                        st.write(f"**Status:** {ticket.get('status', 'open')}")
                        st.write(f"**Created:** {ticket.get('created_at', 'N/A')}")

                        st.divider()

                        st.write("**Question:**")
                        st.info(ticket.get('body', 'No message'))

                        # Response area
                        st.write("**Your Response:**")
                        response_key = f"response_{ticket.get('id', 0)}"
                        response_text = st.text_area(
                            "Type your response:",
                            key=response_key,
                            height=100
                        )

                        col1, col2 = st.columns([1, 3])
                        with col1:
                            if st.button(f"Send Response", key=f"send_{ticket.get('id', 0)}"):
                                if response_text:
                                    success = st.session_state.xmpp_client.send_ticket_response(
                                        ticket_id=ticket.get('id'),
                                        response_text=response_text,
                                        to_jid=ticket.get('from_jid')
                                    )
                                    if success:
                                        st.success("✅ Response sent!")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to send response")
                                else:
                                    st.warning("Please enter a response")
            else:
                st.info("📭 No pending tickets at the moment")

                # Show placeholder data structure
                st.subheader("Expected API Response Format")
                st.code('''
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
                ''', language='json')

else:
    # ===== CHAT PAGE =====
    st.header("Messages")

    # Show message logs section
    st.subheader("Message History (from logs)")

    # Get list of person folders
    person_folders = [d for d in os.listdir(LOG_DIR) if os.path.isdir(os.path.join(LOG_DIR, d))]

    if person_folders:
        # Convert folder names to JIDs for display
        jid_display = {}
        for folder in person_folders:
            # Convert username_at_servername -> username@servername
            jid = folder.replace('_at_', '@')
            jid_display[jid] = folder

        selected_jid = st.selectbox("Select conversation:", list(jid_display.keys()))

        if selected_jid:
            person_dir = os.path.join(LOG_DIR, jid_display[selected_jid])

            # Get all date files for this person
            date_files = sorted([f for f in os.listdir(person_dir) if f.endswith('.txt')], reverse=True)

            if date_files:
                # Create display names without .txt extension
                date_display = {f.replace('.txt', ''): f for f in date_files}
                selected_date_display = st.selectbox("Select date:", list(date_display.keys()))
                selected_date = date_display[selected_date_display]

                if selected_date:
                    log_path = os.path.join(person_dir, selected_date)
                    with open(log_path, 'r', encoding='utf-8') as f:
                        log_content = f.read()

                    st.text_area("Conversation history:", log_content, height=300)

            # Quick reply section
            st.subheader(f"Reply to {selected_jid}")
            col1, col2 = st.columns([4, 1])
            with col1:
                reply_text = st.text_input("Your message:", key=f"reply_{selected_jid}")
            with col2:
                st.write("")  # Spacing
                if st.button("Send", key=f"send_{selected_jid}", disabled=not st.session_state.connected):
                    if reply_text:
                        send_message(selected_jid, reply_text)
                        st.success(f"Sent to {selected_jid}")
                        st.rerun()
    else:
        st.info("No message history yet. Send a message to start logging.")

    st.divider()

    # Display messages (skip presence updates)
    for msg in st.session_state.messages:
        msg_type = msg.get('type', 'chat')
        sender = msg.get('from', 'Unknown')
        body = msg.get('body', '')

        # Skip presence messages in UI
        if msg_type == 'presence':
            continue

        if msg_type == 'system':
            st.info(f"**System:** {body}")
        elif msg_type == 'error':
            st.error(f"**Error:** {body}")
        elif msg_type == 'sent':
            st.success(f"**{sender}:** {body}")
        else:
            st.chat_message("user").write(f"**{sender}:** {body}")

    # Auto-refresh
    if auto_refresh and st.session_state.connected:
        time.sleep(refresh_interval)
        st.rerun()
