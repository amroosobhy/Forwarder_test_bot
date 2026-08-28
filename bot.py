"""
Telegram Multi-Group Forwarder Bot
-----------------------------------
Forwards every message from a set of source groups to a chosen destination
chat/channel per group. The bot only needs to be a MEMBER of each source
group (not an admin) — but it does need "privacy mode" turned OFF in
BotFather, otherwise Telegram only lets it see messages that mention it or
reply to it.

IMPORTANT — do this before running:
  1. Message @BotFather -> /mybots -> select your bot -> Bot Settings
     -> Group Privacy -> Turn OFF.
     (If you already added the bot to groups before turning this off,
     remove and re-add it to each group afterwards — privacy mode is
     locked in at the moment the bot joins.)
  2. Add the bot as a normal member to every source group.
  3. Add the bot to every destination chat/channel too (if the destination
     is a channel, add it as admin there — channels require bot admin
     rights to post, even though source groups do not).

Requirements:
    pip install python-telegram-bot==21.*

Run:
    export BOT_TOKEN="123456:ABC-your-telegram-bot-token"
    python bot.py

--------------------------------------------------------------------------
FINDING CHAT IDs
--------------------------------------------------------------------------
Every chat (group, channel, or user) has a numeric ID. To find them:
  1. Add the bot to the chat (as member, or admin for channels).
  2. Send any message in that chat.
  3. Run this same bot with LOG_UNKNOWN_CHATS = True (default) and watch
     the console/logs — it prints the chat ID and title for every message
     it sees that ISN'T already in FORWARD_MAP below.
  4. Copy that ID into FORWARD_MAP.

--------------------------------------------------------------------------
CONFIGURATION
--------------------------------------------------------------------------
Edit FORWARD_MAP below: each key is a SOURCE group's chat ID, each value
is the DESTINATION chat ID that group's messages should be forwarded to.
"""

import logging
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIGURATION — edit this mapping
# ---------------------------------------------------------------------------
# source_group_chat_id -> list of destination_chat_ids
# A source can forward to ONE destination or SEVERAL — always use a list.
FORWARD_MAP: dict[int, list[int]] = {
    # -1001111111111: [-1002222222222],                # Group A -> one destination
   -5417239309: [-5529613398, 6428188260],
  -5529613398: [-5529613398, 6428188260], # Group B -> a group AND a DM
}

# If True, the bot logs the chat ID/title of any message it receives from a
# chat NOT already in FORWARD_MAP — useful for discovering IDs (see above).
LOG_UNKNOWN_CHATS = True


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Replies with the chat ID of wherever this command was sent.
    Use this in a DM with the bot to get a personal user ID for FORWARD_MAP,
    or in a group to get that group's ID."""
    chat = update.effective_chat
    await update.message.reply_text(
        f"This chat's ID is: {chat.id}\n(type: {chat.type})"
    )


async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.effective_message

    if chat is None or message is None:
        return

    destinations = FORWARD_MAP.get(chat.id)

    if destinations is None:
        if LOG_UNKNOWN_CHATS:
            logger.info(
                "Message from UNMAPPED chat -> id=%s title=%r. "
                "Add this id to FORWARD_MAP to start forwarding it.",
                chat.id,
                chat.title or chat.username or chat.full_name,
            )
        return

    for destination in destinations:
        try:
            await context.bot.forward_message(
                chat_id=destination,
                from_chat_id=chat.id,
                message_id=message.message_id,
            )
            logger.info("Forwarded message %s from %s to %s", message.message_id, chat.id, destination)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to forward message from %s to %s: %s", chat.id, destination, exc
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Missing BOT_TOKEN environment variable. "
            "Get a token from @BotFather and set it with:\n"
            "  export BOT_TOKEN='123456:ABC-your-telegram-bot-token'"
        )

    application = Application.builder().token(token).build()

    # /whoami — send this to the bot (in a DM or a group) to get that chat's ID
    application.add_handler(CommandHandler("whoami", whoami))

    # Listen to every message in every group/channel the bot is a member of.
    application.add_handler(
        MessageHandler(filters.ALL & (~filters.COMMAND), forward_message)
    )

    logger.info("Forwarder bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
