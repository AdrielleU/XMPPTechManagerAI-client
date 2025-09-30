#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.prompt import Prompt
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

from services import XMPPClient, PurpleStorage, APIClient
from models import Message


console = Console()


class XMPPClientApp:
    """Main XMPP client application"""
    
    def __init__(self):
        self.load_config()
        self.setup_logging()
        
        # Initialize services
        self.storage = PurpleStorage(self.purple_dir)
        self.api_client = None
        if self.api_base_url and self.api_token:
            self.api_client = APIClient(self.api_base_url, self.api_token)
        
        # XMPP client will be initialized when connecting
        self.xmpp_client: Optional[XMPPClient] = None
        self.current_chat: Optional[str] = None
        self.running = False
    
    def load_config(self):
        """Load configuration from .env file"""
        load_dotenv()
        
        self.jid = os.getenv("XMPP_JID")
        self.password = os.getenv("XMPP_PASSWORD")
        self.server = os.getenv("XMPP_SERVER")
        self.port = int(os.getenv("XMPP_PORT", "5222"))
        
        self.api_base_url = os.getenv("API_BASE_URL")
        self.api_token = os.getenv("API_TOKEN")
        
        self.purple_dir = os.getenv("PURPLE_DIR", "~/.purple")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        if not self.jid or not self.password:
            console.print("[red]Error: XMPP_JID and XMPP_PASSWORD must be set in .env file[/red]")
            sys.exit(1)
    
    def setup_logging(self):
        """Setup logging with rich handler"""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format="%(message)s",
            handlers=[RichHandler(console=console, rich_tracebacks=True)]
        )
    
    async def connect(self):
        """Connect to XMPP server"""
        server_tuple = (self.server, self.port) if self.server else None
        
        self.xmpp_client = XMPPClient(
            self.jid,
            self.password,
            self.storage,
            self.api_client,
            server_tuple
        )
        
        # Add message callback
        self.xmpp_client.add_message_callback(self.on_new_message)
        
        console.print(f"[green]Connecting to XMPP server as {self.jid}...[/green]")
        
        if server_tuple:
            self.xmpp_client.connect(server_tuple)
        else:
            self.xmpp_client.connect()
    
    async def on_new_message(self, jid: str, message: Message):
        """Handle new incoming messages"""
        if self.current_chat == jid:
            # Display in current chat
            console.print(f"\n[cyan]{jid}:[/cyan] {message.body}")
        else:
            # Show notification
            console.print(f"\n[yellow]New message from {jid}[/yellow]")
    
    def display_chat_list(self):
        """Display list of chats"""
        table = Table(title="Chats", show_header=True)
        table.add_column("Contact", style="cyan")
        table.add_column("Last Message", style="white")
        table.add_column("Unread", style="yellow")
        
        for jid, chat in self.xmpp_client.chats.items():
            last_msg = chat.messages[-1].body[:50] if chat.messages else "No messages"
            unread = str(chat.unread_count) if chat.unread_count > 0 else ""
            table.add_row(jid, last_msg, unread)
        
        console.print(table)
    
    def display_chat(self, jid: str):
        """Display chat history with a contact"""
        if jid not in self.xmpp_client.chats:
            console.print(f"[red]No chat history with {jid}[/red]")
            return
        
        chat = self.xmpp_client.chats[jid]
        chat.mark_as_read()
        
        console.print(f"\n[bold]Chat with {jid}[/bold]\n")
        
        for msg in chat.messages[-20:]:  # Show last 20 messages
            timestamp = msg.timestamp.strftime("%H:%M")
            if msg.is_outgoing:
                console.print(f"[dim]{timestamp}[/dim] [green]You:[/green] {msg.body}")
            else:
                console.print(f"[dim]{timestamp}[/dim] [cyan]{jid}:[/cyan] {msg.body}")
    
    async def send_message(self, body: str):
        """Send a message to current chat"""
        if not self.current_chat:
            console.print("[red]No chat selected[/red]")
            return
        
        await self.xmpp_client.send_message_to(self.current_chat, body)
        console.print(f"[green]You:[/green] {body}")
    
    async def create_ticket(self, message: str):
        """Create a support ticket"""
        if not self.api_client:
            console.print("[red]API client not configured[/red]")
            return
        
        try:
            ticket = await self.api_client.create_ticket(
                message=message,
                jid=self.jid,
                metadata={"created_from": "xmpp_client"}
            )
            console.print(f"[green]Ticket created: {ticket.id} - {ticket.subject}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to create ticket: {e}[/red]")
    
    async def run_interactive(self):
        """Run interactive CLI"""
        self.running = True
        
        # Connect to XMPP
        await self.connect()
        
        # Wait for connection
        await asyncio.sleep(2)
        
        console.print("\n[bold]XMPP Client (Pidgin-like)[/bold]")
        console.print("Commands: /list, /chat <jid>, /send <message>, /ticket <message>, /quit\n")
        
        while self.running:
            try:
                command = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    Prompt.ask, 
                    f"[{self.current_chat or 'no chat'}]"
                )
                
                if command.startswith("/"):
                    await self.handle_command(command)
                elif self.current_chat:
                    await self.send_message(command)
                else:
                    console.print("[yellow]Select a chat first with /chat <jid>[/yellow]")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        
        # Cleanup
        if self.xmpp_client:
            self.xmpp_client.disconnect()
        if self.api_client:
            await self.api_client.close()
    
    async def handle_command(self, command: str):
        """Handle slash commands"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "/list":
            self.display_chat_list()
        
        elif cmd == "/chat":
            if args:
                self.current_chat = args
                self.display_chat(args)
            else:
                console.print("[red]Usage: /chat <jid>[/red]")
        
        elif cmd == "/send":
            if args:
                await self.send_message(args)
            else:
                console.print("[red]Usage: /send <message>[/red]")
        
        elif cmd == "/ticket":
            if args:
                await self.create_ticket(args)
            else:
                console.print("[red]Usage: /ticket <message>[/red]")
        
        elif cmd == "/quit":
            self.running = False
            console.print("[yellow]Disconnecting...[/yellow]")
        
        else:
            console.print(f"[red]Unknown command: {cmd}[/red]")


async def main():
    """Main entry point"""
    app = XMPPClientApp()
    await app.run_interactive()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        logging.exception("Fatal error")