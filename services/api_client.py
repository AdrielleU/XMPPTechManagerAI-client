import httpx
from typing import Dict, Any, Optional, List
from models.ticket import Ticket, TicketMessage


class APIClient:
    """Client for interacting with the ticket API"""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.client = httpx.AsyncClient(headers=self.headers)
    
    async def create_ticket(self, message: str, jid: str, metadata: Optional[Dict[str, Any]] = None) -> Ticket:
        """Create a new ticket from XMPP message"""
        payload = {
            "message": message,
            "channel_source": "xmpp",
            "channel_metadata": {
                "jid": jid,
                "source": "xmpp",
                **(metadata or {})
            }
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/tickets",
            json=payload
        )
        response.raise_for_status()
        return Ticket(**response.json())
    
    async def get_ticket(self, ticket_id: str) -> Ticket:
        """Get ticket details"""
        response = await self.client.get(f"{self.base_url}/api/v1/tickets/{ticket_id}")
        response.raise_for_status()
        return Ticket(**response.json())
    
    async def list_tickets(self, status: Optional[str] = None, limit: int = 10) -> List[Ticket]:
        """List tickets with optional filters"""
        params = {"limit": limit}
        if status:
            params["status"] = status
        
        response = await self.client.get(
            f"{self.base_url}/api/v1/tickets",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        return [Ticket(**t) for t in data.get("data", [])]
    
    async def send_ticket_message(self, ticket_id: str, content: str) -> TicketMessage:
        """Send a message to a ticket"""
        payload = {
            "content": content,
            "message_type": "CUSTOMER",
            "channel_metadata": {
                "source": "xmpp"
            }
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/tickets/{ticket_id}/messages",
            json=payload
        )
        response.raise_for_status()
        return TicketMessage(**response.json())
    
    async def get_ticket_messages(self, ticket_id: str) -> List[TicketMessage]:
        """Get all messages for a ticket"""
        response = await self.client.get(
            f"{self.base_url}/api/v1/tickets/{ticket_id}/messages"
        )
        response.raise_for_status()
        data = response.json()
        return [TicketMessage(**m) for m in data.get("data", [])]
    
    async def close(self) -> None:
        """Close the HTTP client"""
        await self.client.aclose()