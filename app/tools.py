"""
Tool functions for the Gemini Live voice agent.

Contains callable tools that the voice agent can invoke during conversation,
such as booking meetings via external webhook integrations.
"""

import logging
from urllib.parse import urlparse
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

# ── Webhook Configuration ────────────────────────────────────────────
from app.config import settings


async def book_meeting(
    customer_name: str,
    email: str,
    phone: str,
    interest: str,
    date: str,
    time: str,
    meeting_purpose: str,
) -> dict:
    """
    Schedule a meeting with the Ayro AI team by sending booking details
    to the webhook endpoint.

    Args:
        customer_name: Full name of the person requesting the meeting.
        email: Email address for meeting confirmation.
        phone: Contact phone number of the customer.
        interest: Solution/area of interest (e.g. "Voice AI", "Sales Automation").
        date: Meeting date in YYYY-MM-DD format (e.g. "2026-09-20").
        time: Meeting time in HH:MM format (e.g. "14:30").
        meeting_purpose: Purpose or objective of the meeting.

    Returns:
        A dict with the booking status and any response from the webhook.
    """
    # Booking IDs must not come from the language model: short model-generated
    # IDs can repeat and overwrite an existing Firebase document.
    booking_id = f"BK-{uuid4().hex.upper()}"

    payload = {
        "booking_id": booking_id,
        "customer_name": customer_name,
        "email": email,
        "phone": phone,
        "interest": interest,
        "date": date,
        "time": time,
        "meeting_purpose": meeting_purpose,
    }

    logger.info(
        "Calling booking webhook: booking_id=%s, customer=%s, phone=%s, interest=%s, purpose=%s, date=%s, time=%s",
        booking_id,
        customer_name,
        phone,
        interest,
        meeting_purpose,
        date,
        time,
    )

    webhook_url = settings.booking_webhook_url.strip()
    parsed_url = urlparse(webhook_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        logger.error("BOOKING_WEBHOOK_URL is missing or invalid")
        return {
            "status": "error",
            "message": "The booking service is not configured. Please contact support.",
        }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.post(
                webhook_url,
                json=payload,
            )

        if response.is_success:
            logger.info(
                "Booking webhook returned status %s for %s",
                response.status_code,
                booking_id,
            )
            try:
                result = response.json()
            except Exception:
                result = response.text
            return {
                "status": "success",
                "message": f"Meeting {booking_id} confirmed successfully for {customer_name} on {date} at {time}.",
                "booking_details": payload,
                "webhook_response": result,
            }
        else:
            logger.warning(
                "Booking webhook returned status %s for %s: %s",
                response.status_code,
                booking_id,
                response.text,
            )
            return {
                "status": "error",
                "message": f"Booking failed with status {response.status_code}.",
                "details": response.text,
            }

    except httpx.TimeoutException:
        logger.error("Booking webhook timed out for %s", booking_id)
        return {
            "status": "error",
            "message": "The booking service timed out. Please try again.",
        }
    except httpx.RequestError as exc:
        logger.error(
            "Could not reach booking webhook for %s: %s",
            booking_id,
            exc,
        )
        return {
            "status": "error",
            "message": "The booking service could not be reached. Please try again.",
        }


# ── Tool declaration for Gemini Live API ─────────────────────────────
BOOK_MEETING_DECLARATION = {
    "name": "book_meeting",
    "description": (
        "Schedule a meeting with the Ayro AI team for a potential customer. "
        "IMPORTANT: Only call this function AFTER you have read back ALL the collected details "
        "(name, email, phone, interest, meeting_purpose, date, time) to the user and the user has explicitly confirmed that "
        "the information is correct. Never call this function without user confirmation. "
        "The booking ID is generated securely by the backend."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "customer_name": {
                "type": "string",
                "description": "Full name of the person requesting the meeting.",
            },
            "email": {
                "type": "string",
                "description": "Email address for sending the meeting confirmation.",
            },
            "phone": {
                "type": "string",
                "description": "Contact phone or mobile number of the customer.",
            },
            "interest": {
                "type": "string",
                "description": "The AI solution or area of interest (e.g. 'Voice AI', 'Customer Support Automation', 'Sales AI', 'Business Process Automation').",
            },
            "date": {
                "type": "string",
                "description": "Meeting date in YYYY-MM-DD format, e.g. '2026-09-20'.",
            },
            "time": {
                "type": "string",
                "description": "Meeting time in HH:MM format (24-hour), e.g. '14:30'.",
            },
            "meeting_purpose": {
                "type": "string",
                "description": "Purpose or reason for the meeting (e.g. 'Discussion on building a voice bot for appointment scheduling').",
            },
        },
        "required": [
            "customer_name",
            "email",
            "phone",
            "interest",
            "date",
            "time",
            "meeting_purpose",
        ],
    },
}
