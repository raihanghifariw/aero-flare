"""
Telegram alert dispatcher.
FR-11: Telegram bot message delivery to configured channel.
"""
from __future__ import annotations

import structlog
from telegram import Bot
from telegram.error import TelegramError

logger = structlog.get_logger()


async def send_telegram_alert(
    message: str,
    channel_id: str,
    bot_token: str,
) -> bool:
    """
    Send a formatted alert message to a Telegram channel.

    Args:
        message: Markdown-formatted alert string.
        channel_id: Telegram channel or chat ID (e.g. '-1001234567890').
        bot_token: Telegram Bot API token.

    Returns:
        True on successful delivery, False on any error.
    """
    try:
        bot = Bot(token=bot_token)
        async with bot:
            try:
                await bot.send_message(
                    chat_id=channel_id,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except TelegramError as html_err:
                logger.warning(
                    "telegram_html_parse_failed_falling_back_to_plain",
                    channel_id=channel_id,
                    error=str(html_err),
                )
                import re
                plain_text = re.sub(r"<[^>]+>", "", message)
                await bot.send_message(
                    chat_id=channel_id,
                    text=plain_text,
                )
        logger.info("telegram_alert_sent", channel_id=channel_id)
        return True

    except TelegramError as e:
        logger.error(
            "telegram_alert_failed",
            channel_id=channel_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False

    except Exception as e:
        logger.error(
            "telegram_alert_unexpected_error",
            channel_id=channel_id,
            error=str(e),
        )
        return False
