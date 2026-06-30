import logging
import re

from bot.bot import bot
from bot.config import settings
from bot.utils.logger import get_logger

logger = get_logger(__name__)


def extract_channel_id_from_url(url: str) -> str | None:
    """Extract channel username or ID from Telegram URL.
    
    Examples:
    - https://t.me/+t9OydpPAwvtjNmVi -> +t9OydpPAwvtjNmVi
    - https://t.me/channelname -> channelname
    - @channelname -> channelname
    """
    if not url:
        return None
    
    url = url.strip()
    
    # If it's already a username (@name) or ID number, return as-is
    if url.startswith("@") or url.startswith("-"):
        return url
    
    # Try to extract from URL
    if "t.me" in url:
        # Handle URLs like https://t.me/+xxx or https://t.me/channelname
        match = re.search(r"t\.me/(\+?\w+)", url)
        if match:
            return match.group(1)
    
    return None


def format_order_message(order: dict) -> str:
    items_lines = []
    for item in order.get("items", []):
        items_lines.append(
            f"  • {item['product_name']} × {item['quantity']} = "
            f"{item['price'] * item['quantity']:,.0f} so'm"
        )

    order_id = order["id"]
    user_name = order.get("user_name") or "Noma'lum"
    phone = order.get("phone") or "Keltirilmagan"
    address = order.get("address") or "Keltirilmagan"
    total = order["total_amount"]

    return (
        f"🆕 <b>Yangi buyurtma! #{order_id}</b>\n\n"
        f"👤 <b>Mijoz:</b> {user_name}\n"
        f"📞 <b>Telefon:</b> {phone}\n"
        f"📍 <b>Manzil:</b> {address}\n\n"
        f"<b>Buyurtma:</b>\n" + "\n".join(items_lines) +
        f"\n\n💰 <b>Jami:</b> {total:,.0f} so'm\n"
        f"📅 {order['created_at'].strftime('%d.%m.%Y %H:%M') if order.get('created_at') else '—'}"
    )


async def notify_channel(order: dict):
    """Send order notification to Telegram channel."""
    if not settings.channel_id:
        logger.warning("CHANNEL_ID not configured. Skipping notification.")
        return
    
    try:
        # Extract channel ID from URL if needed
        channel = extract_channel_id_from_url(settings.channel_id)
        
        if not channel:
            logger.warning(
                "Failed to parse CHANNEL_ID: %s. Expected format: @channelname, -ID, or https://t.me/...",
                settings.channel_id
            )
            return
        
        text = format_order_message(order)
        await bot.send_message(
            chat_id=channel,
            text=text,
            parse_mode="HTML",
        )
        logger.info("Order notification sent for order #%s", order["id"])
    except Exception as e:
        logger.error("Failed to send channel notification for order #%s: %s", order["id"], e)

