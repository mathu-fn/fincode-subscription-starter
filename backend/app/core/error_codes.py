"""code から既定メッセージへのマップ。AppError がメッセージ解決に使う。"""

ERROR_DEFAULTS: dict[str, str] = {
    "active_subscription_exists": "An active subscription already exists for this user.",
    "subscription_cancel_scheduled": "The subscription is already scheduled for cancellation.",
    "card_in_use": "The card is referenced by an active subscription.",
    "card_not_found": "The card does not exist.",
    "expired_card": "The card has expired.",
    "card_required": "A card is required to subscribe to a paid plan.",
    "plan_unavailable": "The selected plan is unavailable.",
    "subscription_not_found": "No active subscription was found.",
    "forbidden": "You cannot access this resource.",
    "invalid_credentials": "Invalid email or password.",
    "invalid_google_token": "Google sign-in could not be verified.",
    "google_email_not_verified": "The Google account email address is not verified.",
    "unauthenticated": "Authentication is required.",
    "token_expired": "Token expired.",
    "invalid_token": "Invalid token.",
    "email_already_registered": "This email is already registered.",
    "invalid_webhook_signature": "Webhook signature verification failed.",
    "invalid_webhook_payload": "Webhook payload is malformed or missing required fields.",
}
