"""Email notification system."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER, SMTP_SERVER, SMTP_PORT
from src.utils.logging import get_logger
logger = get_logger(__name__)

def send_email(
    subject: str,
    body: str,
    to: Optional[str] = None,
    sender: Optional[str] = None,
    password: Optional[str] = None,
) -> bool:
    """Send an email notification. Returns True on success."""
    to = to or EMAIL_RECEIVER
    sender = sender or EMAIL_SENDER
    password = password or EMAIL_PASSWORD

    if not all([sender, password, to]):
        logger.warning("[Email] Skipped — missing credentials")
        return False

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"[Email] Failed: {e}")
        return False


def notify_application_status(
    job_title: str,
    company: str,
    status: str,
    details: str = "",
):
    subject = f"[JobFinder] {job_title} @ {company} — {status}"
    body = f"Application status: {status}\nJob: {job_title}\nCompany: {company}\n\n{details}"
    send_email(subject, body)
    logger.info(f"[Notification] {subject}")
