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

## 3. Deploying to PythonAnywhere (free tier, no credit card)

PythonAnywhere's free tier doesn't include a true always-on background
worker — that's a paid feature. The practical workaround: run the bot in a
**Bash console** and leave it open. Since the bot is mostly idle while
waiting for Telegram messages (long-polling), this works reasonably well
for low-traffic channels, though it's not a guaranteed 24/7 SLA — the
console can get killed after extended inactivity and may need a restart.

### Step 1: Sign up
Go to [pythonanywhere.com](https://www.pythonanywhere.com) → **Pricing &
signup** → choose the **Beginner (free)** account. No card required.

### Step 2: Upload your code
Easiest option — no git config needed:
1. Go to the **Files** tab in your PythonAnywhere dashboard
2. Create a new directory, e.g. `telegram-search-bot`
3. Upload `bot.py`, `database.py`, and `requirements.txt` into it
   (drag-and-drop or the upload button)

Alternatively, if you'd rather pull from GitHub:
1. Open a **Bash console** from the dashboard
2. Run: `git clone <your-repo-url>`

### Step 3: Install dependencies
In a Bash console, navigate into your project folder and run:
```bash
cd telegram-search-bot
pip3.10 install --user -r requirements.txt
```
(Use whichever Python version is shown as default in your console —
check with `python3 --version` if unsure.)

### Step 4: Set environment variables
PythonAnywhere doesn't have a dashboard env-var UI on the free tier the
same way Render/Railway do. Instead, set them directly in the same
console session before running the bot:
```bash
export BOT_TOKEN="your_botfather_token_here"
export ADMIN_IDS="123456789,987654321"
```
Note: these only last for that console session. You'll need to re-export
them each time you start a fresh console (or add them to a small shell
script you source each time — see the tip at the end of this section).

### Step 5: Run the bot
```bash
python3.10 bot.py
```
You should see "Bot starting..." in the console with no errors. Leave
this console tab open — closing it stops the bot. Test in Telegram with
`/start` and `/search`.

### Step 6: Keep it running
This is the real limitation of the free tier. A few practical tips:
- Don't close the browser tab with the console open while you need the
  bot live.
- If the console gets killed due to inactivity, just re-run the export
  commands and `python3.10 bot.py` again.
- To save retyping the export commands each time, create a file
  `start.sh` in your project folder:
  ```bash
  #!/bin/bash
  export BOT_TOKEN="your_botfather_token_here"
  export ADMIN_IDS="123456789,987654321"
  python3.10 bot.py
  ```
  Then just run `bash start.sh` each time instead of typing exports
  manually. **Do not commit this file to GitHub** — it has your real
  token in it. Keep it only on PythonAnywhere's filesystem.
- Set a reminder for yourself (or your client) to check the bot is still
  responding once a day or so until you upgrade to a paid host.

### When you're ready to upgrade
Once a client is paying you, move that bot to Railway Hobby ($5/mo) or
Render's paid tier — both now payable via UPI cards if you don't have a
traditional credit card. This gets you genuine always-on hosting without
the manual console-babysitting above. The bot code itself (`bot.py`,
`database.py`) doesn't need to change for this — only the deployment
steps differ, since `PORT` being set automatically switches on the
keep-alive server needed for Render (see section below), and Railway
doesn't need it at all.

---

## 4. Deploying to Render (free tier) + UptimeRobot

This is the alternative path if you get card access later (a friend's
card for verification, or your own once you have one) — Render also
requires a card on file even for the free instance type, per recent
reports.

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

## 5. Handing off to a client

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

## 6. Known limitations (be upfront with clients about these)

- **PythonAnywhere free tier needs manual restarts.** Unlike Railway or
  Render, there's no automatic redeploy/restart on crash — if the console
  session dies, someone has to manually re-run `bash start.sh`. Set
  expectations with early clients accordingly; this is a stopgap until
  you move to paid hosting.
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
