from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Represents a single XMPP message"""
    
    id: str = Field(..., description="Unique message ID")
    jid: str = Field(..., description="Jabber ID of the sender/recipient")
    body: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_outgoing: bool = Field(default=False, description="True if message was sent by us")
    thread_id: Optional[str] = None
    message_type: str = Field(default="chat", description="XMPP message type")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Chat(BaseModel):
    """Represents a chat session with a contact"""
    
    jid: str = Field(..., description="Jabber ID of the contact")
    nickname: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    unread_count: int = Field(default=0)
    
    def add_message(self, message: Message) -> None:
        """Add a message to the chat history"""
        self.messages.append(message)
        self.last_activity = message.timestamp
        if not message.is_outgoing:
            self.unread_count += 1
    
    def mark_as_read(self) -> None:
        """Mark all messages as read"""
        self.unread_count = 0