# Campus Customs — Usability & Operations Improvements (Problem 9)

Seven improvements: three on the backend, three on the frontend, and cart + checkout across both. For each one: **what was added**, **why it helps** a Campus Customs shopper or the business, and **where to see it** in the running app.

**Run the app**
```powershell
# terminal 1 (from hw4\backend)
uvicorn main:app --reload --port 8000
# terminal 2 (from hw4\frontend)
npm run dev        # then open http://localhost:5173
```
**Test login:** `test@campuscustoms.yale.edu` / `password`. This seeded account is also the staff (admin) account for the usage page.

| # | Improvement | See it at |
|---|---|---|
| 1 | Agent run log, tool calls, and cost, with a staff usage page | Log in as the test user → **Usage** in the nav (`/admin/usage`) |
| 2 | Fairer limits: per-account, per-network-address, and a lockout that can't be abused | Chat panel error messages; log-in page |
| 3 | Longer memory: old chat summarized, not dropped | Ask the assistant about something from early in a long conversation |
| 4 | Page titles | The browser tab on every page, e.g. a product page |
| 5 | Fresher stock numbers | "● Live stock · updated 20s ago ↻" on Products and product pages |
| 6 | Better error recovery | Stop the backend, then try to chat or load products |
| 7 | Cart & checkout (reserve for in-store pickup) | **Add to cart** on any product page → 🛍 cart icon → **Reserve for pickup** |

---

## 1. Agent run log & cost tracking

**What I added**
- **A run log.** Every time the assistant runs, the server writes one row to a new `agent_runs` table:
  - who it was (account or guest) and their network address
  - which **tools it called** and with what arguments, e.g. `check_stock {"product": "saybrook crewneck", "size": "M"}`
  - the number of model requests, **input and output tokens**, how long it took, and an **estimated cost in USD**
  - how many product cards it put on the page
  - whether it succeeded or failed, and the error type

  Failed runs are logged too. A history summary (see #3) is logged as its own run. Message text isn't copied here; it's already in `chat_messages`.
- **A server-console line per run**, e.g. `AGENT: chat ok user=1 7194ms requests=2 tokens=10909/120 cost=$0.0148 tools=[check_stock]`.
- **A staff "Usage & cost" page** (`/admin/usage`, linked as **Usage** in the nav for staff accounts only) with a Today / 7 days / 30 days switch:
  - summary tiles: agent runs, estimated cost, tokens, average response time, errors, number of shoppers
  - an **estimated cost per day** chart, with a hover tooltip and a "Show as table" view
  - a **Tools called** bar list
  - a **Recent runs** table (when, who, kind, status, tools, tokens, time, cost)
- **Staff list:** `ADMIN_EMAILS` in `.env`; it defaults to the test account. The API (`GET /api/admin/usage`) returns 403 for everyone else.
- **Cost estimates** use `MODEL_INPUT_PRICE_PER_MTOK` / `MODEL_OUTPUT_PRICE_PER_MTOK` from `.env`. The defaults ($1.25 / $10 per million tokens) are **placeholders**; set the real prices for the model you use.

**Why it helps**
- **Debugging:** when a shopper says "the assistant gave me the wrong price", staff can see which tool it called with which product, or that it called none.
- **Cost control:** the business can see what the assistant costs per day and per conversation, spot expensive patterns (for example, very long histories → many input tokens), and judge whether a smaller model would be enough.
- **Reliability:** errors and slow responses show up right away instead of only as unhappy shoppers.

**Where to see it:** log in as the test user → click **Usage** → ask the chat a question in another tab → refresh. The new run appears at the top of "Recent runs" with its tools and cost.

---

## 2. Fairer limits

**What I added**

*Chat (AI cost) limits.* Every message is checked before the AI is called:

| Who | Limit | Kept in |
|---|---|---|
| A logged-in shopper | 20 messages per 10 minutes, and 200 per rolling 24 hours | 24-hour count from `agent_runs` (survives restarts); burst count in memory |
| A guest session | 30 messages, then "log in to keep chatting" (from Problem 8) | memory |
| All guests from one network address | 60 messages per hour, so clearing cookies for a fresh guest session doesn't get around the limit | memory |
| One network address, all accounts and guests | 40 messages per 10 minutes | memory |

When a limit is hit, the shopper sees a clear message such as "You're sending messages very quickly. Please try again in 3 minutes." The response carries a `Retry-After` header. The chat doesn't offer a pointless "Try again" button for these.

*Log-in lockout that can't be turned against someone.* Before, 5 wrong passwords for an email locked that email for **everyone**, so anyone who knew a shopper's email could lock them out. Failed logins are now counted at three levels (new `login_locks` table):

| Level | Rule | Stops |
|---|---|---|
| One email **from one network address** | 5 failures in 15 min → that address is locked out of that email for 15 min | Password guessing. The real owner, on their own network, can still log in. |
| One network address, any emails | 20 failures in 15 min → 15-min lock | One machine trying passwords on many accounts ("spraying") |
| One email, all addresses | 30 failures in 1 hour → 30-min lock | A large attack spread over many addresses (backstop) |

Every failure still returns the same "Invalid email or password.", and unknown emails are counted the same way, so the limits don't reveal which emails have accounts.

*Real network addresses.* The Vite dev proxy now forwards the shopper's address (`X-Forwarded-For`). The backend trusts that header only when the request came from a known proxy, and reads the **rightmost** address the proxy added, not ones a browser could have written itself.

**Why it helps**
- **Business:** one account, one script, or one person clearing cookies can't run up a large AI bill.
- **Shoppers:** a stranger can no longer lock them out of their own account just by knowing their email, while attackers still get stopped.

**Where to see it:** this is easiest to see in the tests (`backend/tests/test_improvements.py`). In the live check (`backend/tests/e2e_improvements.py`), 5 wrong passwords from address 198.51.100.7 locked that address (`[401, 401, 401, 401, 429]`), while the same account then logged in successfully from 192.0.2.44.

---

## 3. Longer memory: older chat is summarized, not dropped

**What I added**
- **The model sees** every message that hasn't been summarized yet (20–29 of them) **plus a rolling summary of everything older**. It no longer just forgets anything beyond the last 10 back-and-forths.
- **When 30 or more messages are waiting,** a small summarizer agent folds all but the latest 20 into the summary (new `chat_summaries` table). The summary covers:
  - what the shopper wants: colleges, teams, recipients, sizes, colors, budget
  - which products were discussed (with ids) and what was decided
  - anything still unresolved
- **It runs in the background** after the reply is sent, so the shopper never waits for it. It's logged in the usage page as a "summary" run.
- **The summary reaches the agent** under "Earlier in this conversation", marked as data. Prices and stock in it are flagged as possibly out of date, so the agent re-checks with its tools.
- **Nothing is deleted.** The full history stays in `chat_messages`, and the chat panel still shows it.
- **Model choice:** the summarizer uses `SUMMARY_MODEL`, which defaults to the main model. Because it's a simple task, a smaller, cheaper model can be set here, as AGENTS.md suggests.
- **Guests** keep their short in-memory chat from Problem 8 and don't need a summary.

**Why it helps**
- **Shoppers:** a returning shopper planning gifts over several visits ("the Saybrook crewneck for my dad, size L, under $60") doesn't have to repeat themselves after a long conversation.
- **Business:** cost per message stays bounded. Sending a short summary is much cheaper than resending dozens of old messages.

**Where to see it:** the test user already had 64 saved messages. In the live check, the first chat triggered a summary that began *"Shopper is exploring Yale apparel… **Saybrook College Crewneck** (`saybrook-co…`"*. 20 recent messages stayed word for word, and all 66 remained saved. The **Usage** page shows the "summary" run and its cost.

---

## 4. Page titles

**What I added:** every page sets its browser-tab title (`useTitle`):

| Page | Tab title |
|---|---|
| Home | Campus Customs · Yale gear on Broadway |
| Products | "Products", or what's being browsed: "Hoodies", "Bulldog teams", "Search: saybrook" |
| Product page | **"Saybrook College Crewneck · $58.00 \| Campus Customs"** |
| Cart | "Your cart (3) \| Campus Customs" |
| Checkout, My orders, an order | "Checkout", "My orders", "Order CC-261023-5F2AE6" |
| About, Log in, Create account, staff page, 404 | Their own names |

**Why it helps:** shoppers with several tabs open (comparing crewnecks, say) can tell them apart. Bookmarks and browser history show real product names instead of a dozen identical "Campus Customs" entries. Shared links and screen readers announce the right page.

**Where to see it:** open any product page and look at the browser tab.

---

## 5. Fresher stock numbers

**What I added**
- **One shared, live product list.** It refreshes **every 45 seconds while the tab is visible**, and again whenever the shopper **comes back to the tab** or **comes back online**. Product cards, product pages, and the chat's "On this page" chip all update automatically.
- **A "● Live stock · updated 20s ago ↻" line** on the Products page and on every product page. The ↻ button refreshes right away.
- **If a refresh fails,** the last good numbers stay on screen with a yellow note ("Couldn't refresh stock… Showing numbers from 2 min ago") instead of the page going blank.
- **After a reservation,** stock refreshes immediately, so the shopper sees the new count.
- **The cart re-checks every line** against live stock whenever stock refreshes (see #7).

**Why it helps:** a shopper who leaves a product page open while they think about it won't plan around a size that has since sold out. The "Add to cart" button disables itself when a size sells out. Fewer disappointed pickups and fewer "it said it was in stock" complaints.

**Where to see it:** open a product page and watch the "updated …s ago" counter. Click ↻, or switch tabs and come back.

---

## 6. Better error recovery

**What I added**
- **Chat: "↻ Try again".** If a message can't be sent (server down, network drop, or assistant error), the message stays in the conversation, marked "⚠ Not sent", with a reason ("Couldn't reach the shop - check your connection."). It has a **↻ Try again** button that resends it, and an **Edit** button that puts it back in the text box. For rate limits it shows when to try again instead of offering a pointless retry.
- **Chat history: "Try again".** If earlier messages fail to load, there's a button to reload them.
- **Products: "Try again".** If products can't load on Home, Products, or a product page, a **Try again** button reloads them. Before, the page just said to refresh.
- **Cart, My orders, and the staff page** have their own Try again buttons.
- **Offline banner.** When the device loses its connection, a banner says "You're offline. Prices and stock may be out of date…". Stock refreshes automatically when it's back.
- **Checkout conflicts.** If someone buys the last item while a shopper is checking out, the order isn't placed. The shopper sees what changed ("only 1 left") with a link back to the cart.

**Why it helps:** a hiccup no longer means lost work or a dead end. Shoppers don't have to retype a question or guess whether to reload, so fewer of them give up mid-conversation or mid-checkout.

**Where to see it:** stop the backend (Ctrl+C in its terminal), send a chat message, and you'll see "⚠ Not sent" and **↻ Try again**. Restart the backend and click it. The Products page shows a **Try again** box if you reload it while the backend is down.

---

## 7. Cart & checkout: reserve online, pick up in store

**What I added**
- **Add to cart on every product page.** Pick a size, then a quantity (−/+). The button reads "🛍 Add to cart · $116.00". You can't add more than is in stock, minus what's already in your cart, and at most 10 per line. Sold-out sizes say "Sold out in XXL". A confirmation appears: "✓ Added 2 × M to your cart. View cart & reserve →".
- **A 🛍 cart icon** in the nav with a count badge, visible on phones too. The cart is saved in the browser, so guests can shop and it survives page reloads.
- **The cart page** (`/cart`):
  - each line has a photo, name, size, −/+ quantity, line total, and remove
  - every line is **re-priced and re-checked against live stock on the server** (`POST /api/cart/quote`); prices never come from the browser
  - problems are flagged in yellow ("⚠ Only 2 left in L." with a one-click "Change to 2", or "Sold out in XXL since you added it")
  - a summary panel shows items, subtotal, and "Pay: At pickup"
- **Checkout** (`/checkout`, which asks you to log in first if needed): a pickup name, prefilled from the account, and an optional note for the shop. **No payment details are collected online.** Shoppers pay at the counter at 57 Broadway, which fits a local shop and keeps card data out of the app entirely.
- **Placing the order is all-or-nothing on the server.** Stock is taken off with a conditional update (`quantity >= requested`), so two shoppers can't reserve the last item. Any shortfall cancels the whole order and returns the updated cart.
- **A confirmation page** (`/orders/CC-261023-5F2AE6`) says "✦ Reserved! Boola Boola, Test!", shows the order number to give at the counter, the items, and the total due at pickup.
- **My orders** (`/orders`, in the nav when logged in) lists past reservations with their status.
- **New tables:** `orders` and `order_items`.
- **The assistant** now explains how to add to cart and reserve, and it's told it can't place orders itself.

**Why it helps**
- **Business:** this is the first time the website can turn interest into a sale. Interest from the chat and the Spotlight becomes a reservation, and the shopper walks into the store, where they might buy more.
- **Shoppers:** they can make sure their size is held before making the trip, which matters for low-stock sizes. They also get a clear order number and a record under My orders.

**Where to see it:**
1. Log in as the test user and open any product page.
2. Pick a size, then **Add to cart**.
3. Click the **🛍** icon, then **Reserve for pickup**, then **Reserve**.
4. On the confirmation page, check that the product's stock went down by the quantity you reserved.

---

## How it was verified

- **Backend tests: 91 pass** (`python -m pytest tests -q` from `backend/`). `tests/test_improvements.py` adds 18 tests:
  - run logging, including failed runs
  - the admin-only usage API
  - the per-account burst limit and the daily limit
  - the guest per-address limit surviving cleared cookies
  - forwarded-address parsing that resists spoofing
  - the lockout not blocking the owner from another address
  - address spraying blocked, and the email-wide backstop
  - summarizing old messages without deleting them
  - cart quotes flagging problems
  - checkout requiring login, reserving stock, refusing when stock ran out (with no partial reservation), ignoring browser prices, and keeping orders private
- **Live check against the running app** (`backend/tests/e2e_improvements.py`). All checks passed:
  - attacker address locked, owner still logged in
  - a real chat logged with `check_stock`, 10,909/120 tokens, about $0.0148
  - older chat summarized in the background (20 recent of 66 kept word for word)
  - cart quote flagged a sold-out size
  - reservation CC-261023-5F2AE6 placed, with stock 20 → 19
  - the order listed under My orders
- **Frontend:** `npm run build` and `npm run lint` are clean.
- **Clicked through in Chrome 155** (each feature worked as described):
  - **Page title** on a product page: "Saybrook College Crewneck · $58.00 | Campus Customs".
  - **Live stock line:** "● Live stock · updated just now ↻".
  - **Add to cart limits:** on size L (2 left), quantity stopped at 2 and **+** turned off. The button changed to "All L stock is in your cart" and the 🛍 badge showed 2.
  - **Checkout while logged out** redirected to log in, then back to checkout with the pickup name filled in.
  - **Reserve** showed "Boola Boola, Test!" with the order number, and L then showed **Sold out** on the product page.
  - **Usage page:** the tiles, cost-per-day chart, tools list, and recent runs all showed the browser's own chats.
  - **Backend stopped:**
    - Chat showed "⚠ Not sent. Couldn't reach the shop - check your connection." with **↻ Try again**. After restarting the backend, Try again got an answer without reloading the page.
    - Products showed a **Try again** box that brought the catalogue back.
    - The live-stock line kept the old numbers with a yellow warning.

**Bugs the browser test found, all fixed:**

| Bug | Cause | Fix |
|---|---|---|
| **The whole site went blank** after loading. This had been there since Problem 3; tests and builds couldn't catch it. | In Chrome 155, `window.scrollTo()` returns a Promise. `useEffect(() => window.scrollTo(0, 0))` handed that Promise to React as a "cleanup", which crashed the app. | Braces, so the effect returns nothing (`App.tsx`). |
| Checkout showed "Can't reach the shop server" while working fine. | React runs effects twice in development; the first, deliberately cancelled price check was reported as a connection error. | Cancelled requests are no longer treated as errors (`ordersApi.ts`). |
| Error text said "the server answered 502" / "the assistant couldn't answer" when the backend was down. | The dev proxy answers 502 when the backend is down. | 502/504 now read "Can't reach the shop server" in chat, cart, and stock. |
| After an outage the site showed you as **logged out** (and the chat as a guest) even though your session was valid. | The "who am I" check failed once and was never retried. | Only a real 401 means logged out; otherwise it re-checks every 5 s until the server is back (`AuthProvider.tsx`). |
| **Wrong product:** on the Yale Mom Hoodie page, "is this in stock in medium?" was answered about the Saybrook crewneck from earlier turns. | The page context was only in the instructions, far above a long conversation. | A one-line page note now sits right after the shopper's message (the saved message is unchanged). Re-tested on the 1/4 Zip page: "is it in stock in XL?" was answered "the Benjamin Franklin 1/4 Zip is sold out in XL". |
| A sideways scrollbar inside the Spotlight. | Its blurred pink glow overhangs the panel. | `overflow-x: hidden` on the Spotlight. |

**Test data:**
- **Tests now use a frozen seed.** The backend tests copy `backend/tests/fixtures/seed.db`, a copy of the original seed, instead of the live database. Browser reservations no longer change test results (92 tests pass).
- **Test reservations cancelled.** The two reservations made while testing (1 logo tee S, 2 crewnecks L) were cancelled and their stock put back, so the live catalogue matches the seed again.

**Database changes:**
- **New tables:** `agent_runs`, `login_locks`, `chat_summaries`, `orders`, `order_items`. `init_schema()` creates them on startup.
- **`login_attempts`:** no longer used, but kept so the change is reversible.
- **Stock:** the live checks really reserved items (1 Saybrook Logo T Shirt S, then 2 Saybrook College Crewnecks L in the browser test). Both test reservations were later cancelled and the stock restored.
