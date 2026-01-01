"""Stripe webhook handler for subscription management.

Handles Stripe webhook events for subscription lifecycle management:
- customer.subscription.created
- customer.subscription.updated
- customer.subscription.deleted
- invoice.payment_succeeded
- invoice.payment_failed
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from fastapi import APIRouter, Request, HTTPException, Header, Depends

from ...config import get_settings
from ...db.repositories.subscription_repository import (
    SubscriptionRepository,
    get_subscription_repository,
)


router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Stripe Signature Verification
# =============================================================================


def verify_stripe_signature(
    payload: bytes,
    sig_header: str,
    webhook_secret: str,
) -> Dict[str, Any]:
    """
    Verify Stripe webhook signature and construct event.

    Args:
        payload: Raw request body bytes
        sig_header: Stripe-Signature header value
        webhook_secret: Stripe webhook secret for verification

    Returns:
        Constructed Stripe event dictionary

    Raises:
        HTTPException: If signature verification fails
    """
    try:
        import stripe
        stripe.api_key = get_settings().stripe_secret_key

        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except ValueError as e:
        logger.error(f"Invalid Stripe payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")


# =============================================================================
# Event Handlers
# =============================================================================


async def handle_subscription_created(
    subscription: Dict[str, Any],
    subscription_repo: SubscriptionRepository,
) -> None:
    """
    Handle customer.subscription.created event.

    Creates or updates the user's subscription record when a new
    Stripe subscription is created.

    Args:
        subscription: Stripe subscription object
        subscription_repo: Repository for subscription operations
    """
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")
    status = subscription.get("status", "active")

    # Determine plan from Stripe price ID
    items = subscription.get("items", {}).get("data", [])
    plan_id = "pro"  # Default to pro for paid subscriptions

    if items:
        price_id = items[0].get("price", {}).get("id")
        settings = get_settings()
        if price_id == settings.stripe_price_id_pro_monthly:
            plan_id = "pro"
        elif price_id == settings.stripe_price_id_pro_yearly:
            plan_id = "pro"

    # Get period dates
    current_period_start = None
    current_period_end = None
    if subscription.get("current_period_start"):
        current_period_start = datetime.fromtimestamp(
            subscription["current_period_start"]
        )
    if subscription.get("current_period_end"):
        current_period_end = datetime.fromtimestamp(
            subscription["current_period_end"]
        )

    # Trial end
    trial_end = None
    if subscription.get("trial_end"):
        trial_end = datetime.fromtimestamp(subscription["trial_end"])

    logger.info(
        f"Subscription created: customer={customer_id}, "
        f"subscription={subscription_id}, plan={plan_id}, status={status}"
    )

    # Find existing subscription by stripe_customer_id and update it
    # or create a new one if needed
    existing = _find_subscription_by_customer_id(subscription_repo, customer_id)

    if existing:
        subscription_repo.update_subscription(
            user_id=existing.user_id,
            plan_id=plan_id,
            status=status,
            stripe_subscription_id=subscription_id,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            trial_end=trial_end,
        )
    else:
        # Log warning - subscription should already exist from checkout
        logger.warning(
            f"No existing subscription found for customer {customer_id}. "
            "User may need to be created first via checkout session."
        )


async def handle_subscription_updated(
    subscription: Dict[str, Any],
    subscription_repo: SubscriptionRepository,
) -> None:
    """
    Handle customer.subscription.updated event.

    Updates the user's subscription when changes occur (plan change,
    status change, cancellation scheduling, etc.).

    Args:
        subscription: Stripe subscription object
        subscription_repo: Repository for subscription operations
    """
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")
    status = subscription.get("status", "active")
    cancel_at_period_end = subscription.get("cancel_at_period_end", False)

    # Determine plan from Stripe price ID
    items = subscription.get("items", {}).get("data", [])
    plan_id = "pro"

    if items:
        price_id = items[0].get("price", {}).get("id")
        settings = get_settings()
        if price_id == settings.stripe_price_id_pro_monthly:
            plan_id = "pro"
        elif price_id == settings.stripe_price_id_pro_yearly:
            plan_id = "pro"

    # Get period dates
    current_period_start = None
    current_period_end = None
    if subscription.get("current_period_start"):
        current_period_start = datetime.fromtimestamp(
            subscription["current_period_start"]
        )
    if subscription.get("current_period_end"):
        current_period_end = datetime.fromtimestamp(
            subscription["current_period_end"]
        )

    logger.info(
        f"Subscription updated: customer={customer_id}, "
        f"subscription={subscription_id}, status={status}, "
        f"cancel_at_period_end={cancel_at_period_end}"
    )

    # Find and update subscription
    existing = _find_subscription_by_customer_id(subscription_repo, customer_id)

    if existing:
        subscription_repo.update_subscription(
            user_id=existing.user_id,
            plan_id=plan_id,
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            cancel_at_period_end=cancel_at_period_end,
        )
    else:
        logger.warning(
            f"No subscription found for customer {customer_id} during update"
        )


async def handle_subscription_deleted(
    subscription: Dict[str, Any],
    subscription_repo: SubscriptionRepository,
) -> None:
    """
    Handle customer.subscription.deleted event.

    Downgrades the user to the free tier when their subscription is
    cancelled and the period ends.

    Args:
        subscription: Stripe subscription object
        subscription_repo: Repository for subscription operations
    """
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")

    logger.info(
        f"Subscription deleted: customer={customer_id}, "
        f"subscription={subscription_id}"
    )

    # Find and downgrade subscription to free
    existing = _find_subscription_by_customer_id(subscription_repo, customer_id)

    if existing:
        subscription_repo.update_subscription(
            user_id=existing.user_id,
            plan_id="free",
            status="canceled",
            stripe_subscription_id=None,
            current_period_start=None,
            current_period_end=None,
            cancel_at_period_end=False,
        )
        logger.info(f"User {existing.user_id} downgraded to free tier")
    else:
        logger.warning(
            f"No subscription found for customer {customer_id} during deletion"
        )


async def handle_payment_succeeded(
    invoice: Dict[str, Any],
    subscription_repo: SubscriptionRepository,
) -> None:
    """
    Handle invoice.payment_succeeded event.

    Updates the subscription status to active when payment succeeds,
    particularly useful for recovering from past_due status.

    Args:
        invoice: Stripe invoice object
        subscription_repo: Repository for subscription operations
    """
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")
    amount_paid = invoice.get("amount_paid", 0)

    logger.info(
        f"Payment succeeded: customer={customer_id}, "
        f"subscription={subscription_id}, amount={amount_paid}"
    )

    # Only process subscription invoices
    if not subscription_id:
        return

    # Find and ensure subscription is active
    existing = _find_subscription_by_customer_id(subscription_repo, customer_id)

    if existing:
        # Ensure status is active after successful payment
        if existing.status != "active":
            subscription_repo.update_subscription(
                user_id=existing.user_id,
                status="active",
            )
            logger.info(
                f"User {existing.user_id} subscription reactivated after payment"
            )


async def handle_payment_failed(
    invoice: Dict[str, Any],
    subscription_repo: SubscriptionRepository,
) -> None:
    """
    Handle invoice.payment_failed event.

    Updates the subscription status to past_due when payment fails.
    The user should be notified to update their payment method.

    Args:
        invoice: Stripe invoice object
        subscription_repo: Repository for subscription operations
    """
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")
    attempt_count = invoice.get("attempt_count", 0)

    logger.warning(
        f"Payment failed: customer={customer_id}, "
        f"subscription={subscription_id}, attempt={attempt_count}"
    )

    # Only process subscription invoices
    if not subscription_id:
        return

    # Find and update subscription status
    existing = _find_subscription_by_customer_id(subscription_repo, customer_id)

    if existing:
        subscription_repo.update_subscription(
            user_id=existing.user_id,
            status="past_due",
        )
        logger.warning(
            f"User {existing.user_id} subscription marked as past_due"
        )


# =============================================================================
# Helper Functions
# =============================================================================


def _find_subscription_by_customer_id(
    subscription_repo: SubscriptionRepository,
    stripe_customer_id: str,
) -> Optional[Any]:
    """
    Find a user subscription by Stripe customer ID.

    Args:
        subscription_repo: Repository for subscription operations
        stripe_customer_id: Stripe customer ID to search for

    Returns:
        UserSubscription if found, None otherwise
    """
    # This requires a custom query since we don't have a direct method
    # In a production system, this would be a dedicated repository method
    import sqlite3
    from pathlib import Path

    try:
        with subscription_repo._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_subscriptions WHERE stripe_customer_id = ?",
                (stripe_customer_id,)
            ).fetchone()

            if row:
                return subscription_repo._row_to_subscription(row)
            return None
    except Exception as e:
        logger.error(f"Error finding subscription by customer ID: {e}")
        return None


# =============================================================================
# Webhook Endpoint
# =============================================================================


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    subscription_repo: SubscriptionRepository = Depends(get_subscription_repository),
):
    """
    Handle Stripe webhook events.

    This endpoint receives webhook events from Stripe for subscription
    lifecycle management. Events are verified using the webhook signature
    before processing.

    Supported events:
    - customer.subscription.created: New subscription created
    - customer.subscription.updated: Subscription modified
    - customer.subscription.deleted: Subscription cancelled
    - invoice.payment_succeeded: Payment successful
    - invoice.payment_failed: Payment failed

    Returns:
        dict: Status response indicating success or failure
    """
    settings = get_settings()

    # Validate configuration
    if not settings.stripe_webhook_secret:
        logger.error("Stripe webhook secret not configured")
        raise HTTPException(
            status_code=500,
            detail="Webhook not configured"
        )

    if not stripe_signature:
        logger.error("Missing Stripe-Signature header")
        raise HTTPException(
            status_code=400,
            detail="Missing signature header"
        )

    # Get raw payload
    payload = await request.body()

    # Verify signature and construct event
    event = verify_stripe_signature(
        payload=payload,
        sig_header=stripe_signature,
        webhook_secret=settings.stripe_webhook_secret,
    )

    event_type = event.get("type")
    event_data = event.get("data", {}).get("object", {})

    logger.info(f"Received Stripe webhook: {event_type}")

    try:
        # Route to appropriate handler
        if event_type == "customer.subscription.created":
            await handle_subscription_created(event_data, subscription_repo)
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(event_data, subscription_repo)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(event_data, subscription_repo)
        elif event_type == "invoice.payment_succeeded":
            await handle_payment_succeeded(event_data, subscription_repo)
        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(event_data, subscription_repo)
        else:
            logger.debug(f"Unhandled Stripe event type: {event_type}")

        return {"status": "ok"}

    except Exception as e:
        logger.exception(f"Error handling Stripe webhook {event_type}: {e}")
        # Return 200 to prevent Stripe from retrying on application errors
        # Log the error for investigation
        return {"status": "error", "message": str(e)}
