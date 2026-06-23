"""
bot.py
A per-admin Telegram content-search bot.

Admins add/update/delete content entries (title, season, episode, language, link)
via DM commands. End users in the group use /search to find content.

Setup required before running:
1. Create a bot with @BotFather on Telegram, copy the token.
2. Set environment variables (see .env.example):
   - BOT_TOKEN
   - ADMIN_IDS (comma-separated Telegram numeric user IDs allowed to manage content)
3. Disable "Group Privacy" in BotFather if you want the bot to read plain
   group text. NOT required for this bot since we only use /search, /add, etc.
   which always work regardless of privacy mode.
"""

import logging
import os
import threading
from textwrap import dedent

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_IDS = {
    int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}

# Conversation states for the guided /add flow
TITLE, SEASON, EPISODE, LANGUAGE, LINK = range(5)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ---------- Basic commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        dedent(
            """
            👋 Welcome! Use /search <name> to find content.

            Example: /search Solo Leveling S2 dub
            """
        ).strip()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = dedent(
        """
        📖 *Available commands*

        /search <query> — find content (anyone can use this)
        /help — show this message
        """
    ).strip()
    if is_admin(user_id):
        text += "\n\n" + dedent(
            """
            🔑 *Admin commands*

            /add — add a new content entry (guided)
            /update <id> <new_link> — replace a dead link
            /delete <id> — remove an entry
            /list — show all entries with their IDs
            /cancel — cancel an in-progress /add
            """
        ).strip()
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------- Search (anyone, used in group) ----------

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search <name> [season] [episode] [sub/dub]")
        return

    query = " ".join(context.args)
    results = database.search(query)

    if not results:
        await update.message.reply_text(f'No results found for "{query}". Try fewer words.')
        return

    # Cap to avoid flooding the chat on broad queries
    MAX_RESULTS = 8
    shown = results[:MAX_RESULTS]

    reply_lines = [f'🔍 Results for "{query}":\n']
    for row in shown:
        reply_lines.append(
            f"• {row['title']}\n"
            f"  Season {row['season'] or '-'} • Episode {row['episode'] or '-'} • {row['language'] or '-'}\n"
            f"  🔗 {row['link']}\n"
        )

    if len(results) > MAX_RESULTS:
        reply_lines.append(f"...and {len(results) - MAX_RESULTS} more. Try a more specific search.")

    await update.message.reply_text("\n".join(reply_lines), disable_web_page_preview=True)


# ---------- Admin: /list ----------

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is for admins only.")
        return

    rows = database.list_all()
    if not rows:
        await update.message.reply_text("No entries yet. Use /add to create one.")
        return

    MAX_SHOWN = 30
    lines = []
    for row in rows[:MAX_SHOWN]:
        lines.append(
            f"#{row['id']} — {row['title']} "
            f"(S{row['season'] or '-'}E{row['episode'] or '-'}, {row['language'] or '-'})"
        )
    text = "\n".join(lines)
    if len(rows) > MAX_SHOWN:
        text += f"\n\n...and {len(rows) - MAX_SHOWN} more entries."

    await update.message.reply_text(text)


# ---------- Admin: /update ----------

async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is for admins only.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /update <id> <new_link>")
        return

    entry_id_raw, new_link = context.args[0], context.args[1]
    if not entry_id_raw.isdigit():
        await update.message.reply_text("The id must be a number. Use /list to find it.")
        return

    success = database.update_link(int(entry_id_raw), new_link)
    if success:
        await update.message.reply_text(f"✅ Updated link for entry #{entry_id_raw}.")
    else:
        await update.message.reply_text(f"⚠️ No entry found with id #{entry_id_raw}.")


# ---------- Admin: /delete ----------

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is for admins only.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /delete <id>")
        return

    entry_id = int(context.args[0])
    success = database.delete_entry(entry_id)
    if success:
        await update.message.reply_text(f"🗑️ Deleted entry #{entry_id}.")
    else:
        await update.message.reply_text(f"⚠️ No entry found with id #{entry_id}.")


# ---------- Admin: /add (guided conversation) ----------

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is for admins only.")
        return ConversationHandler.END

    await update.message.reply_text("Let's add a new entry. What's the title?")
    return TITLE


async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text.strip()
    await update.message.reply_text("Season? (e.g. 2, or type '-' if not applicable)")
    return SEASON


async def add_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["season"] = update.message.text.strip()
    await update.message.reply_text("Episode? (e.g. 5, or type '-' if not applicable)")
    return EPISODE


async def add_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["episode"] = update.message.text.strip()
    await update.message.reply_text("Language? (e.g. Sub, Dub, Sub+Dub)")
    return LANGUAGE


async def add_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["language"] = update.message.text.strip()
    await update.message.reply_text("Now send the link.")
    return LINK


async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    data = context.user_data

    new_id = database.add_entry(
        title=data["title"],
        season=data["season"],
        episode=data["episode"],
        language=data["language"],
        link=link,
    )

    await update.message.reply_text(
        f"✅ Added entry #{new_id}: {data['title']} "
        f"(S{data['season']}E{data['episode']}, {data['language']})"
    )
    context.user_data.clear()
    return ConversationHandler.END


async def add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ---------- Keep-alive web server (only needed for Render free tier + UptimeRobot) ----------
# Render's free tier only runs "web services" that bind to a port — it doesn't
# offer a free always-on worker process. So on Render we run a tiny Flask app
# alongside the bot's polling loop just to give Render (and UptimeRobot)
# something to ping. This is skipped automatically on hosts like PythonAnywhere
# where it isn't needed and there's no PORT env var set.

keep_alive_app = Flask(__name__)


@keep_alive_app.route("/")
def keep_alive_ping():
    return "Bot is alive."


def run_keep_alive_server():
    port = int(os.environ.get("PORT", 10000))
    keep_alive_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


# ---------- App setup ----------

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")
    if not ADMIN_IDS:
        logger.warning(
            "No ADMIN_IDS configured — nobody will be able to use /add, /update, /delete, /list."
        )

    database.init_db()

    # Only start the keep-alive web server if PORT is set (Render sets this
    # automatically). On PythonAnywhere or local runs, this is skipped.
    if os.environ.get("PORT"):
        keep_alive_thread = threading.Thread(target=run_keep_alive_server, daemon=True)
        keep_alive_thread.start()
        logger.info("Keep-alive server started (PORT detected — Render mode).")
    else:
        logger.info("No PORT set — skipping keep-alive server (PythonAnywhere/local mode).")

    app = Application.builder().token(BOT_TOKEN).build()

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
            SEASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_season)],
            EPISODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_episode)],
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_language)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_link)],
        },
        fallbacks=[CommandHandler("cancel", add_cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("update", update_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(add_conv)

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
