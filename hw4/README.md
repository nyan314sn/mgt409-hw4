# Campus Customs — HW4 (Yale SOM MGT 409)

A storefront for Campus Customs (Yale merch, 57 Broadway, New Haven), with a shop-assistant chatbot.

- **Front end:** React + Vite + TypeScript (`frontend/`), styled "Varsity After Dark" (black and pink).
- **Back end:** FastAPI (`backend/main.py`) with a PydanticAI agent that looks up live stock and prices in `data/campus_customs.db`. Its model is `gpt-5.6-luna`, reached through Portkey.

Shoppers can browse, take a "Find your fit" quiz, add to cart, and reserve for in-store pickup. They can also chat; the agent puts matching products on the page as cards in the Spotlight.

> A class project. Campus Customs / Yale Bulldog Blue is a local setting for the course; this site is not affiliated with or endorsed by the shop or Yale University.

## Data pack (not in git — place it first)

The database and product photos are **not** in this repository. Get the course data pack and put it in
`hw4/data/` so it looks like this:

```
hw4/
└── data/
    ├── campus_customs.db     # catalogue, inventory, users, chat_messages
    └── products/             # product photos referenced by catalogue.image_file_path
```

On first start the backend adds its own tables to `campus_customs.db` (sessions, login locks, orders,
agent run log, chat summaries). The original seed tables are left as they are.

## Run it

Requirements: Python 3.12+ and Node.js 20+. On the author's machine every Python command uses
`C:\Users\Pi\miniconda3\python.exe`; anywhere else, use the `python` you installed the requirements into.

```powershell
# 1. One time: Python packages (from hw4)
python -m pip install -r requirements.txt

# 2. One time: secrets. Copy .env.example to .env (in hw4 or any parent folder) and set PORTKEY_API_KEY.
copy .env.example .env
python check_env.py          # checks .env + packages + data pack; never prints secret values

# 3. Backend (from hw4\backend) - needs the data pack in hw4\data
cd backend
uvicorn main:app --reload --port 8000

# 4. Frontend (from hw4\frontend, second terminal)
cd frontend
npm install          # first time only
npm run dev          # open http://localhost:5173
```

The front end's dev server forwards `/api/*` and `/data/products/*` to the backend on port 8000, so
open only `http://localhost:5173`. Product photos are served by the backend from `data/products/`.

**Test login:** `test@campuscustoms.yale.edu` / `password`. This seeded test account can also open the staff page `/admin/usage`.

## Tests

```powershell
# from hw4\backend: 100 tests, no AI calls. Needs the data pack: the first run copies the
# database to backend\tests\fixtures\seed.db, so tests never touch the live data.
python -m pytest tests -q

# from hw4, with both servers running: live checks against the real model
python backend\tests\e2e_safety.py

# from hw4\frontend
npm run build
npm run lint
```

## Folder layout

```
hw4/
├── AI_prompts.md          # every prompt for this homework, time-stamped
├── requirements.txt       # Python dependencies
├── .env.example           # variable names only (real .env is git-ignored)
├── .gitignore
├── README.md
├── config.py, check_env.py
├── data/                  # LOCAL ONLY (git-ignored): campus_customs.db + products/ photos
├── frontend/              # Vite React TypeScript app
├── backend/
│   ├── main.py            # FastAPI app: uvicorn main:app --reload --port 8000
│   ├── agent.py           # agent wiring: model + prompt + tools + history
│   ├── models.py          # Pydantic / PydanticAI types
│   ├── tools.py           # tools the agent can call (read-only DB lookups)
│   ├── prompts/prompt.md  # system prompt: voice, tool rules, safety rules
│   ├── auth.py, orders.py, catalogue.py, memory.py, usage.py, audit.py, ...
│   └── tests/
└── output/
    ├── harness.md         # how the system works (start with Part A)
    ├── design.md          # Problem 10 design write-up
    ├── usability.md       # Problem 9 improvements
    ├── app_check.html     # Problem 11 live test report (double-click to open)
    ├── app_check_images/  # screenshots linked from app_check.html
    └── audit_trail.json   # append-only log of agent-loop steps
```
