# Campus Customs — Front End

React + Vite + TypeScript front end for the HW4 Campus Customs project (Yale SOM MGT 409).
Black-and-pink theme, with a nav bar linking Home, Products, About Us, Log in, and Create account.

## Run it

```powershell
# 1. Start the API (from hw4\backend)
uvicorn main:app --reload --port 8000        # http://127.0.0.1:8000

# 2. Start the dev server (from hw4\frontend, in a second terminal)
npm install
npm run dev        # http://localhost:5173  (proxies /api and /data/products to the API)
```

`npm run build` type-checks and builds to `dist/`. `npm run lint` runs oxlint.
Backend tests: from `hw4\backend`, `C:\Users\Pi\miniconda3\python.exe -m pytest tests -q`.
How the front end talks to FastAPI, auth, and the agent are documented in `output/harness.md`.

## Pages

| Route | Page | Notes |
|---|---|---|
| `/` | Home | Hero, "shop by story" collections, residential-college crests, favorites, gift finder, visit info |
| `/products` | Products | Cards with image, name, price, and short description; search + filters (collection, category, color, size in stock, price, sort) kept in the URL |
| `/products/:id` | Product detail | Large image beside the full text: description, price, colors, size picker with stock, search tags, "Ask about this item", and related products |
| `/about` | About Us | Shop story, values, visit info — written in our own words |
| `/login` | Log in | Email + password against `/api/auth/login`; generic error on failure; lockout after repeated failures |
| `/register` | Create account | First/last name, email, password + confirm; creates a `users` row and logs in |
| `/cart` | Cart | Lines re-checked against live stock and prices; reserve for pickup |
| `/checkout` | Checkout | Log-in required; pickup name + note; no online payment |
| `/orders`, `/orders/:number` | My orders | Reservation history and confirmation page |
| `/admin/usage` | Usage & cost (staff) | Agent runs, tools called, tokens, estimated cost; `ADMIN_EMAILS` only |

Every page sets its browser-tab title. Stock refreshes live every 45 seconds and when you return
to the tab. Errors offer "Try again". See `output/usability.md` for all Problem 9 improvements.

## Data

Products come live from `GET /api/products` (catalogue + stock by size from
`data/campus_customs.db`). Photos are served by the API at `/data/products/<file>.jpg`,
matching the database's `image_file_path`.

## Chat panel

The floating "Ask us" button (bottom right, every page) opens the shop assistant, a
PydanticAI agent behind `POST /api/chat`. Anyone can chat. Logged-in shoppers' history is
saved to their account and reloaded from `GET /api/chat/history` when the panel opens;
guest chats last only for the visit. The browser sends `{ message, page }`, where `page` is
the current path plus any Spotlight cards, so the agent knows what "this one" or "the second
one" means on every page. Replies render light Markdown (bold, bullets) safely.

Each reply has two separate parts: `message` (text for the chat bubble) and `showcase`
(product data). A showcase is rendered on the page in the **Spotlight**
(`components/Spotlight.tsx`), a panel that slides over the main page beside the chat. The
cards are the normal `ProductCard`, so clicking one opens the product page. The chat bubble
only shows a chip that re-opens the showcase. Details: `output/harness.md`, Problem 7.

## Layout

```
src/
  main.tsx, App.tsx         router + layout
  index.css                 theme tokens and all styles
  lib/catalogue.ts          types, catalogue loader, collections, color families
  lib/auth.ts, authApi.ts   auth context + /api/auth client
  lib/chat.ts, chatApi.ts   chat context + /api/chat client
  components/               NavBar, Footer, ProductCard, AuthLayout, AuthProvider,
                            ChatProvider, ChatWidget, Spotlight, RichText
  pages/                    Home, Products, ProductDetail, About, Login, Register, NotFound
```

Campus Customs / Yale Bulldog Blue is a local setting for class; this site is not affiliated
with or endorsed by the shop or Yale University.
