"""
Tool functions for the Gemini Live voice agent.

Contains callable tools that the voice agent can invoke during conversation,
such as booking meetings via external webhook integrations.
"""

import json
import logging
import httpx

logger = logging.getLogger(__name__)

# ── Webhook Configuration ────────────────────────────────────────────
from app.config import settings

BOOKING_WEBHOOK_URL = settings.booking_webhook_url


async def book_meeting(
    booking_id: str,
    customer_name: str,
    email: str,
    check_in: str,
    check_out: str,
) -> dict:
    """
    Book a hotel meeting/room by sending the booking details to the
    EasyWay booking webhook.

    This function is called by the voice agent when a customer wants to
    make a hotel booking. It sends the booking payload to the n8n webhook
    endpoint and returns the result.

    Args:
        booking_id: Unique booking identifier (e.g. "BK0008").
        customer_name: Full name of the customer making the booking.
        email: Customer's email address for booking confirmation.
        check_in: Check-in date in YYYY-MM-DD format (e.g. "2026-09-20").
        check_out: Check-out date in YYYY-MM-DD format (e.g. "2026-09-22").

    Returns:
        A dict with the booking status and any response from the webhook.
    """
    payload = {
        "booking_id": booking_id,
        "customer_name": customer_name,
        "email": email,
        "check_in": check_in,
        "check_out": check_out,
    }

    logger.info(
        "Calling booking webhook: booking_id=%s, customer=%s, check_in=%s, check_out=%s",
        booking_id,
        customer_name,
        check_in,
        check_out,
    )

    # ── Clear terminal output ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("📤  SENDING TO WEBHOOK")
    print("=" * 60)
    print(f"  URL        : {BOOKING_WEBHOOK_URL}")
    print(f"  booking_id : {booking_id}")
    print(f"  customer   : {customer_name}")
    print(f"  email      : {email}")
    print(f"  check_in   : {check_in}")
    print(f"  check_out  : {check_out}")
    print(f"  payload    : {json.dumps(payload, indent=2)}")
    print("=" * 60 + "\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                BOOKING_WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        # ── Print response ───────────────────────────────────────────
        print("\n" + "=" * 60)
        print(f"📥  WEBHOOK RESPONSE  (status: {response.status_code})")
        print("=" * 60)
        print(f"  {response.text}")
        print("=" * 60 + "\n")

        if response.status_code == 200:
            logger.info("Booking webhook returned 200 OK for %s", booking_id)
            try:
                result = response.json()
            except Exception:
                result = response.text
            return {
                "status": "success",
                "message": f"Booking {booking_id} confirmed successfully for {customer_name}.",
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
    except Exception as e:
        logger.error("Booking webhook error for %s: %s", booking_id, e)
        return {
            "status": "error",
            "message": f"An error occurred while processing the booking: {str(e)}",
        }


# ── Tool declaration for Gemini Live API ─────────────────────────────
BOOK_MEETING_DECLARATION = {
    "name": "book_meeting",
    "description": (
        "Book a hotel room or meeting for a customer. "
        "Call this function when the customer wants to make a hotel booking. "
        "Collect the customer's name, email address, preferred check-in date, "
        "and check-out date before calling this function. "
        "Generate a unique booking ID in the format 'BK' followed by 4 digits (e.g. BK0009)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "booking_id": {
                "type": "string",
                "description": "Unique booking identifier in the format 'BK' followed by 4 digits, e.g. 'BK0008'. Generate this automatically.",
            },
            "customer_name": {
                "type": "string",
                "description": "Full name of the customer making the booking.",
            },
            "email": {
                "type": "string",
                "description": "Customer's email address for booking confirmation.",
            },
            "check_in": {
                "type": "string",
                "description": "Check-in date in YYYY-MM-DD format, e.g. '2026-09-20'.",
            },
            "check_out": {
                "type": "string",
                "description": "Check-out date in YYYY-MM-DD format, e.g. '2026-09-22'.",
            },
        },
        "required": ["booking_id", "customer_name", "email", "check_in", "check_out"],
    },
}
