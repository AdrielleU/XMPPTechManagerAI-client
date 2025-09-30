from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TicketMessage(BaseModel):
    """Message within a ticket"""
    
    id: str
    content: str
    message_type: str
    sender_id: Optional[str] = None
    service_bot_id: Optional[str] = None
    is_public: bool = True
    created_at: datetime
    sender: Optional[Dict[str, Any]] = None


class Ticket(BaseModel):
    """Support ticket model matching the API"""
    
    id: str
    subject: str
    description: Optional[str] = None
    status: str = "OPEN"
    priority: str = "NORMAL"
    category: Optional[str] = None
    requester_id: str
    assignee_id: Optional[str] = None
    service_bot_id: Optional[str] = None
    channel_source: str = "xmpp"
    channel_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_xmpp_message(cls, jid: str, message: str, user_id: str) -> "Ticket":
        """Create a ticket from an XMPP message"""
        now = datetime.utcnow()
        return cls(
            id="",  # Will be set by API
            subject=f"XMPP Support Request from {jid}",
            description=message,
            requester_id=user_id,
            channel_source="xmpp",
            channel_metadata={
                "jid": jid,
                "source": "xmpp"
            },
            created_at=now,
            updated_at=now
        )