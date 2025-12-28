from abc import ABC, abstractmethod
from typing import Dict, Any, List
import smtplib
from email.message import EmailMessage
import json
import urllib.request
import logging

logger = logging.getLogger("notifications")

class INotificationChannel(ABC):
    @abstractmethod
    def send(self, message: str, level: str = "info") -> bool:
        pass

class EmailChannel(INotificationChannel):
    def __init__(self, config: Dict[str, Any]):
        self.host = config.get("smtp_host", "smtp.gmail.com")
        self.port = config.get("smtp_port", 587)
        self.user = config.get("user")
        self.password = config.get("password")
        self.recipients = config.get("recipients", [])
        
        if not self.user or not self.password or not self.recipients:
            logger.warning("EmailChannel initialized with missing credentials or recipients")

    def send(self, message: str, level: str = "info") -> bool:
        if not self.recipients:
            return False
            
        msg = EmailMessage()
        msg.set_content(message)
        msg["Subject"] = f"[{level.upper()}] Hygiene Suite Notification"
        msg["From"] = self.user
        msg["To"] = ", ".join(self.recipients)

        try:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

class WebhookChannel(INotificationChannel):
    def __init__(self, config: Dict[str, Any]):
        self.url = config.get("url")
        if not self.url:
            logger.warning("WebhookChannel initialized without URL")

    def send(self, message: str, level: str = "info") -> bool:
        if not self.url:
            return False
            
        payload = {
            "content": f"**[{level.upper()}]** {message}",
            "username": "Hygiene Suite Bot"
        }
        
        # Adapt payload for Slack if needed (Slack uses 'text')
        if "slack.com" in self.url:
            payload = {"text": f"[{level.upper()}] {message}"}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.url, 
            data=data, 
            headers={"Content-Type": "application/json", "User-Agent": "HygieneSuite/1.0"}
        )

        try:
            with urllib.request.urlopen(req) as response:
                return 200 <= response.getcode() < 300
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return False

class NotificationManager:
    def __init__(self):
        self.channels: List[INotificationChannel] = []

    def register(self, channel: INotificationChannel):
        self.channels.append(channel)

    def load_from_config(self, config: Dict[str, Any]):
        """
        Load channels from configuration dictionary.
        Expected structure:
        {
            "email": { "enabled": bool, ... },
            "webhook": { "enabled": bool, ... }
        }
        """
        # Email
        email_conf = config.get("email", {})
        if email_conf.get("enabled"):
            self.register(EmailChannel(email_conf))

        # Webhook
        webhook_conf = config.get("webhook", {})
        if webhook_conf.get("enabled"):
            self.register(WebhookChannel(webhook_conf))

    def notify(self, message: str, level: str = "info"):
        for channel in self.channels:
            try:
                channel.send(message, level)
            except Exception as e:
                # Log error but don't crash
                logging.error(f"Notification failed: {e}")
