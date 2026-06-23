# Telegram Content Search Bot

A per-channel/group bot that lets admins maintain a searchable catalog of
content (title, season, episode, sub/dub, link) and lets group members
search it with `/search`. Built so dead links can be fixed in one command
instead of re-posting.

This is a **template** — you deploy one fresh copy per paying admin/client.

---

## 1. Local setup (test before deploying)

```bash
git clone <your-repo-url>
cd telegram-search-bot
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `BOT_TOKEN` — get this from @BotFather on Telegram (see step 2 below)
- `ADMIN_IDS` — comma-separated numeric Telegram user IDs who can manage
  content. Get your own ID by messaging @userinfobot on Telegram.

Run it locally:

```bash
export $(cat .env | xargs)   # loads .env vars into your shell (Mac/Linux)
python bot.py
```

If it prints "Bot starting..." with no errors, it's working. Test in Telegram:
- DM the bot `/start`
- As an admin, DM `/add` and follow the prompts
- In a group the bot has been added to, try `/search <title>`

---

## 2. Creating the bot with BotFather (one-time per client)

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Choose a display name (e.g. "AnimeVault Search") and a username ending
   in `bot` (e.g. `animevault_search_bot`)
4. BotFather gives you a token like `123456:ABC-DEF...` — this is `BOT_TOKEN`
5. Add the bot to the client's group as a member (admin rights NOT required —
   `/search`, `/add` etc. are commands and work regardless of group privacy
   settings)

---

## 3. Deploying to Railway (free tier)

1. Push this folder to a **new GitHub repo** (one repo per client, or one
   repo with branches — your call, but separate repos are simpler to manage)
2. Go to [railway.app](https://railway.app), click **New Project** →
   **Deploy from GitHub repo**
3. Select the repo
4. Go to the project's **Variables** tab and add:
   - `BOT_TOKEN` = the token from BotFather
   - `ADMIN_IDS` = the client's Telegram numeric ID(s), comma-separated
5. **Important — add a persistent volume** so the SQLite database survives
   restarts/redeploys:
   - Go to your service → **Settings** → **Volumes**
   - Click **Add Volume**, mount path: `/app/data`
   - This keeps `data.db` from being wiped on redeploy. Without this step,
     the client's entire content catalog can disappear the next time
     Railway restarts the container.
   - If you add the volume, update `database.py`'s `DB_PATH` to point at
     `/app/data/data.db` instead of the local folder — do this **before**
     the client starts adding real content, not after.
6. Railway should auto-detect the `Procfile` and run `python bot.py` as a
   worker process (not a web service — this bot doesn't serve HTTP, it
   long-polls Telegram, so no public URL/port is needed)
7. Check the **Deployments** logs tab — you should see "Bot starting..."
   with no errors

---

## 4. Handing off to a client

Each client gets:
- Their own bot (separate BotFather token)
- Their own Railway project (separate free-tier allowance)
- Their own GitHub repo (or branch) — optional to share repo access with
  them; most clients won't need it

What you tell the client:
- Add `/add` entries yourself, or train them to do it
- `/update <id> <new_link>` whenever a link dies — no need to contact you
- `/list` to find an entry's ID before updating/deleting

---

## 5. Known limitations (be upfront with clients about these)

- Search is word-overlap based, not true fuzzy matching — typos may not
  match. Good enough for short titles; for very large catalogs (500+
  entries) consider upgrading to a fuzzy library like `rapidfuzz` later.
- No pagination UI — `/search` caps results at 8, `/list` caps at 30 to
  avoid flooding the chat.
- Single admin set per bot — there's no per-group role separation since
  each deployment already serves one client.
