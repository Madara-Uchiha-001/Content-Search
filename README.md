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

If it prints "Bot starting..." with no errors, it's working. You'll also
see a small Flask server start on port 10000 (or whatever `PORT` is set
to) — that's the Render keep-alive endpoint, not part of search itself.
You can ignore it locally; it only matters once deployed.

Test in Telegram:
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

## 3. Deploying to Render (free tier) + UptimeRobot

Render's free tier only runs **web services** — processes that bind to a
port and respond to HTTP — for free. It does not offer a free always-on
background worker. That's why this bot includes a tiny Flask server that
runs alongside the actual Telegram polling loop, just so Render has a port
to see and a URL to serve. The Flask server doesn't do anything related to
search — it's purely there to satisfy Render's free-tier requirements and
give UptimeRobot something to ping.

### Step 1: Push to GitHub
Push this folder to a new GitHub repo (one repo per client, your call on
structure).

### Step 2: Create the Render service
1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repo
3. Render should detect `render.yaml` in this repo and pre-fill the
   runtime, build command, and start command automatically (it leaves
   `BOT_TOKEN` and `ADMIN_IDS` blank for you to fill in — they're marked
   as secrets, not synced from the file, on purpose)
4. If `render.yaml` isn't picked up automatically, set these manually:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: Free
5. Add environment variables under **Environment**:
   - `BOT_TOKEN` = token from BotFather
   - `ADMIN_IDS` = client's Telegram numeric ID(s), comma-separated
   - Render automatically sets `PORT` for you — you don't need to set this
     yourself, the code reads it automatically
6. Deploy. Check the **Logs** tab — you should see "Bot starting..." with
   no errors, and the Flask server should report it's running on the
   assigned port.

### Step 3: Stop Render from sleeping the bot (UptimeRobot)
Render's free web services spin down after a period of inactivity (no
incoming HTTP requests). To prevent this:
1. Copy your Render service's public URL (shown on the service dashboard,
   looks like `https://yourbotname.onrender.com`)
2. Go to [uptimerobot.com](https://uptimerobot.com), create a free account
3. **Add New Monitor**:
   - Monitor Type: HTTP(s)
   - Friendly Name: anything, e.g. "AnimeVault bot keep-alive"
   - URL: your Render URL from step 1
   - Monitoring Interval: 5 minutes
4. Save. UptimeRobot will now ping your bot every 5 minutes, which counts
   as activity and stops Render from spinning it down.

**Important caveat**: this keeps the bot *mostly* always-on, but it's not
a guaranteed 100% uptime solution — there can be a brief cold-start delay
if Render does spin the service down between pings, and free-tier behavior
can change over time. Be upfront with clients that this is a best-effort
free setup, not an SLA-backed one.

### Step 4: Persistent storage caveat (read before clients add real content)
Render's free tier does **not** include a persistent disk — like Railway,
the filesystem resets on redeploy, meaning `data.db` (and the client's
whole content catalog) can be wiped when the service restarts or redeploys.

Options to handle this:
- **Accept the risk for now**: fine for early testing, risky once a client
  has dozens of real entries — a redeploy could erase their catalog.
- **Use Render's paid persistent disk add-on**: defeats the "free" goal,
  but an option if a client's catalog grows large and they're willing to
  cover a small cost.
- **Switch to a free external database** (recommended once a client goes
  live for real): services like Supabase or Neon offer free-tier hosted
  Postgres that survives redeploys independently of your app host. This
  would require swapping `database.py`'s SQLite calls for a Postgres
  connection — a moderate rewrite, not a config change. Flag this to me
  if/when you're ready to make that switch.

---

## 4. Handing off to a client

Each client gets:
- Their own bot (separate BotFather token)
- Their own Render web service (separate free-tier instance)
- Their own UptimeRobot monitor pinging that service
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
- Render free tier + UptimeRobot is a best-effort keep-alive setup, not a
  guaranteed-uptime solution. Occasional brief downtime or cold starts are
  possible. Be upfront with clients about this if they expect 24/7 SLA-grade
  uptime — that requires a paid tier on any host.
- No persistent disk on Render's free tier — see the storage caveat in
  the deployment section above before a client relies on this in production.
