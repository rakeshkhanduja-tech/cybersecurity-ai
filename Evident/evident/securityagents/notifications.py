import logging
import abc
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class NotificationProvider(abc.ABC):
    @abc.abstractmethod
    def send(self, recipient: str, subject: str, body: str) -> bool:
        pass

class EmailNotificationProvider(NotificationProvider):
    def send(self, recipient: str, subject: str, body: str) -> bool:
        # Placeholder for actual email sending logic (SMTP, SendGrid, etc.)
        logger.info(f"[EMAIL NOTIFICATION] To: {recipient}, Subject: {subject}")
        # In a real implementation, we would use smtplib or a service API
        return True

class NotificationManager:
    def __init__(self):
        self._providers: Dict[str, NotificationProvider] = {
            "email": EmailNotificationProvider()
        }

    def notify(self, method: str, recipient: str, subject: str, message: str) -> bool:
        provider = self._providers.get(method.lower())
        if not provider:
            logger.error(f"Notification method '{method}' not supported.")
            return False
        
        try:
            return provider.send(recipient, subject, message)
        except Exception as e:
            logger.error(f"Failed to send notification via {method}: {e}")
            return False

# Global singleton
notification_manager = NotificationManager()
