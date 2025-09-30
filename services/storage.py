import os
import json
import aiofiles
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from models.chat import Chat, Message


class PurpleStorage:
    """Storage manager that mimics Pidgin's .purple directory structure"""
    
    def __init__(self, purple_dir: str = "~/.purple"):
        self.base_dir = Path(purple_dir).expanduser()
        self.logs_dir = self.base_dir / "logs" / "xmpp"
        self.accounts_dir = self.base_dir / "accounts"
        self.settings_file = self.base_dir / "xmpp_settings.json"
        
        # Create directory structure
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.accounts_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_message(self, jid: str, message: Message) -> None:
        """Save a message to the log file"""
        # Create directory for contact if it doesn't exist
        contact_dir = self.logs_dir / jid.replace("@", "_at_")
        contact_dir.mkdir(exist_ok=True)
        
        # Create log file for today
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = contact_dir / f"{date_str}.txt"
        
        # Format message (Pidgin-style)
        timestamp = message.timestamp.strftime("[%H:%M:%S]")
        sender = "You" if message.is_outgoing else jid
        log_entry = f"{timestamp} {sender}: {message.body}\n"
        
        # Append to file
        async with aiofiles.open(log_file, mode='a', encoding='utf-8') as f:
            await f.write(log_entry)
    
    async def load_chat_history(self, jid: str, days: int = 7) -> List[Message]:
        """Load chat history for a contact"""
        messages = []
        contact_dir = self.logs_dir / jid.replace("@", "_at_")
        
        if not contact_dir.exists():
            return messages
        
        # Get log files for the past N days
        from datetime import timedelta
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            log_file = contact_dir / f"{date_str}.txt"
            
            if log_file.exists():
                async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    # Parse log file (simplified - you might want to improve this)
                    for line in content.strip().split('\n'):
                        if line:
                            messages.append(self._parse_log_line(line, jid))
        
        return sorted(messages, key=lambda m: m.timestamp)
    
    def _parse_log_line(self, line: str, jid: str) -> Message:
        """Parse a log line into a Message object"""
        # Simple parser - you might want to make this more robust
        import re
        match = re.match(r'\[(\d{2}:\d{2}:\d{2})\] ([^:]+): (.+)', line)
        if match:
            time_str, sender, body = match.groups()
            is_outgoing = sender == "You"
            # For simplicity, using today's date with the time
            timestamp = datetime.strptime(
                f"{datetime.now().date()} {time_str}", 
                "%Y-%m-%d %H:%M:%S"
            )
            return Message(
                id=f"log_{timestamp.timestamp()}",
                jid=jid,
                body=body,
                timestamp=timestamp,
                is_outgoing=is_outgoing
            )
        return Message(id="unknown", jid=jid, body=line, timestamp=datetime.now())
    
    async def save_settings(self, settings: Dict) -> None:
        """Save client settings"""
        async with aiofiles.open(self.settings_file, 'w') as f:
            await f.write(json.dumps(settings, indent=2))
    
    async def load_settings(self) -> Dict:
        """Load client settings"""
        if not self.settings_file.exists():
            return {}
        
        async with aiofiles.open(self.settings_file, 'r') as f:
            content = await f.read()
            return json.loads(content) if content else {}