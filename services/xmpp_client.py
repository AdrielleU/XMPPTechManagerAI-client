import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import slixmpp
from slixmpp import ClientXMPP
from slixmpp.exceptions import IqError, IqTimeout

from models.chat import Chat, Message
from .storage import PurpleStorage
from .api_client import APIClient


class XMPPClient(ClientXMPP):
    """XMPP client that mimics Pidgin functionality"""
    
    def __init__(
        self, 
        jid: str, 
        password: str,
        storage: PurpleStorage,
        api_client: Optional[APIClient] = None,
        server: Optional[tuple] = None
    ):
        super().__init__(jid, password)
        
        self.storage = storage
        self.api_client = api_client
        self.server_address = server
        self.chats: Dict[str, Chat] = {}
        self.message_callbacks: List[Callable] = []
        
        # Register plugins
        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0004')  # Data Forms
        self.register_plugin('xep_0060')  # PubSub
        self.register_plugin('xep_0199')  # XMPP Ping
        self.register_plugin('xep_0045')  # Multi-User Chat
        self.register_plugin('xep_0085')  # Chat State Notifications
        self.register_plugin('xep_0184')  # Message Delivery Receipts
        
        # Event handlers
        self.add_event_handler("session_start", self.on_session_start)
        self.add_event_handler("message", self.on_message)
        self.add_event_handler("presence", self.on_presence)
        self.add_event_handler("disconnected", self.on_disconnected)
        
        # Chat state events
        self.add_event_handler("chatstate_composing", self.on_composing)
        self.add_event_handler("chatstate_paused", self.on_paused)
        self.add_event_handler("chatstate_active", self.on_active)
    
    async def on_session_start(self, event):
        """Handle session start"""
        self.send_presence()
        await self.get_roster()
        
        logging.info(f"Session started for {self.boundjid}")
        
        # Load chat history for all contacts
        roster = self.client_roster
        for jid in roster:
            if jid != self.boundjid.bare:
                await self.load_chat_history(jid)
    
    async def on_message(self, msg):
        """Handle incoming messages"""
        if msg['type'] in ('chat', 'normal'):
            jid = msg['from'].bare
            body = msg['body']
            
            if not body:
                return
            
            # Create message object
            message = Message(
                id=msg['id'] or f"msg_{datetime.now().timestamp()}",
                jid=jid,
                body=body,
                timestamp=datetime.now(),
                is_outgoing=False,
                thread_id=msg.get('thread'),
                message_type=msg['type']
            )
            
            # Add to chat
            if jid not in self.chats:
                self.chats[jid] = Chat(jid=jid)
            
            self.chats[jid].add_message(message)
            
            # Save to storage
            await self.storage.save_message(jid, message)
            
            # Send delivery receipt if supported
            if msg['request_receipt']:
                self.send_receipt(msg)
            
            # Call message callbacks
            for callback in self.message_callbacks:
                await callback(jid, message)
            
            # Check if this should create a support ticket
            if self.api_client and message.body.lower().startswith(("/help", "/support", "/ticket")):
                await self.create_support_ticket(jid, message.body)
    
    async def on_presence(self, pres):
        """Handle presence updates"""
        jid = pres['from'].bare
        pres_type = pres['type']
        
        if pres_type == 'available':
            logging.info(f"{jid} is online")
        elif pres_type == 'unavailable':
            logging.info(f"{jid} went offline")
    
    async def on_disconnected(self, event):
        """Handle disconnection"""
        logging.warning("Disconnected from XMPP server")
    
    async def on_composing(self, msg):
        """Handle typing notifications"""
        jid = msg['from'].bare
        logging.debug(f"{jid} is typing...")
    
    async def on_paused(self, msg):
        """Handle paused typing"""
        jid = msg['from'].bare
        logging.debug(f"{jid} stopped typing")
    
    async def on_active(self, msg):
        """Handle active chat state"""
        jid = msg['from'].bare
        if jid in self.chats:
            self.chats[jid].mark_as_read()
    
    async def send_message_to(self, jid: str, body: str, mtype: str = 'chat') -> Message:
        """Send a message to a contact"""
        msg_id = f"msg_{datetime.now().timestamp()}"
        
        # Send the message
        self.send_message(
            mto=jid,
            mbody=body,
            mtype=mtype,
            mid=msg_id
        )
        
        # Create message object
        message = Message(
            id=msg_id,
            jid=jid,
            body=body,
            timestamp=datetime.now(),
            is_outgoing=True,
            message_type=mtype
        )
        
        # Add to chat
        if jid not in self.chats:
            self.chats[jid] = Chat(jid=jid)
        
        self.chats[jid].add_message(message)
        
        # Save to storage
        await self.storage.save_message(jid, message)
        
        return message
    
    async def load_chat_history(self, jid: str) -> None:
        """Load chat history from storage"""
        messages = await self.storage.load_chat_history(jid)
        
        if jid not in self.chats:
            self.chats[jid] = Chat(jid=jid)
        
        # Add historical messages
        for msg in messages:
            self.chats[jid].messages.append(msg)
    
    async def create_support_ticket(self, jid: str, message: str) -> None:
        """Create a support ticket from XMPP message"""
        if not self.api_client:
            await self.send_message_to(
                jid,
                "Support ticket creation is not available at the moment."
            )
            return
        
        try:
            # Remove command prefix
            clean_message = message
            for prefix in ("/help", "/support", "/ticket"):
                if message.lower().startswith(prefix):
                    clean_message = message[len(prefix):].strip()
                    break
            
            # Create ticket
            ticket = await self.api_client.create_ticket(
                message=clean_message or "Help requested via XMPP",
                jid=jid,
                metadata={"resource": self.boundjid.resource}
            )
            
            # Send confirmation
            await self.send_message_to(
                jid,
                f"Support ticket created! Ticket ID: {ticket.id}\n"
                f"Subject: {ticket.subject}\n"
                f"We'll get back to you as soon as possible."
            )
            
        except Exception as e:
            logging.error(f"Failed to create ticket: {e}")
            await self.send_message_to(
                jid,
                "Sorry, I couldn't create a support ticket. Please try again later."
            )
    
    def send_receipt(self, msg):
        """Send message delivery receipt"""
        receipt = self.Message()
        receipt['to'] = msg['from']
        receipt['receipt'] = msg['id']
        receipt.send()
    
    def add_message_callback(self, callback: Callable):
        """Add a callback for incoming messages"""
        self.message_callbacks.append(callback)
    
    async def connect_and_run(self):
        """Connect to server and run the client"""
        if self.server_address:
            self.connect(self.server_address)
        else:
            self.connect()
        
        # Process XMPP stanzas
        await self.disconnected