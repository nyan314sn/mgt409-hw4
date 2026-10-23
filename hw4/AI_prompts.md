# AI Prompts Log — HW4

## 2026-10-22 18:06 (EDT)

> Before starting the assignment, configure the project environment automatically.
>
> Use C:\Users\Pi\miniconda3\python.exe explicitly for every Python command. Do not rely on the shell's default python.
>
> Search the homework folder and its parent directories for a .env file. Load environment variables from the nearest applicable .env file without displaying or exposing secret values. If a required package is missing, install it into C:\Users\Pi\miniconda3 using that interpreter.
>
> Create or update a requirements.txt file for project dependencies. Verify the environment by importing each required package before implementing the assignment.
>
> Run the finished program with:
> C:\Users\Pi\miniconda3\python.exe
>
> Keep all generated files inside the homework folder, and record my prompts in AI_prompots.md throughout the assignment along with date/time stamp.

## 2026-10-22 18:11 (EDT)

> research https://yalebulldogblue.com and learn about it. This might be useful for our project later.

## 2026-10-22 18:13 (EDT)

> Look at the database `data/campus_customs.db` and help me understand the fields of each table

## 2026-10-22 18:15 (EDT)

> we now work on problem #2

## 2026-10-22 18:16 (EDT)

> give me a few sample rows from each data table

## 2026-10-22 18:20 (EDT)

> Start the file output/harness.md. Write down each table and its fields, and one short line on why each field matters for the shop or the chatbot.

## 2026-10-22 18:21 (EDT)

> we now work on Problem 3.
>
> Scaffold a React + Vite + TypeScript front end for Campus Customs. Put a nav bar at the top that links to the main pages:
>
> Home
> Products
> About Us
> Log in
> Create account
>
> Pull Campus Customs–style wording from yalebulldogblue.com for Home and About Us, but write these pages in your own voice (do not copy the original site text).
>
> Try to be creative.

## 2026-10-22 18:30 (EDT)

> On the Products page, show product images from the catalogue (use the image paths in the database) with basic product info (name, price, short description).
>
> Make each product open a single-item page (large image on one side, full product text on the other — description, price, sizes/stock when you have them). Clicking a card on Products should take the shopper there.
>
> Add a chat interface in the bottom right of the site (a floating chat panel is fine). It does not need to talk to an agent yet — a stub that will call your backend later is enough for this problem.

## 2026-10-22 18:35 (EDT)

> do you need the api to read the database?

## 2026-10-22 18:42 (EDT)

> Problem #4.
>
> Build a normal create-account / login flow.
>
> Create account: first name, last name, email, password (confirm password is a nice touch)
> Log in: email and password
> New accounts go into the users table. Make sure to store passwords securely so hackers (human or AI) cannot access them.
>
> The seed database already has a test user you can use while building:
>
> Email: test@campuscustoms.yale.edu
> Password: [redacted in log]
> Hash function: PBKDF2-HMAC-SHA256, 120,000 iterations (stored as pbkdf2_sha256$salt$hash)
> How login checks a password:
>
> You never un-hash the stored value. You re-hash what the user typed and compare.
> Read the salt out of the stored string (the middle piece) — do not make a new one at login.
> Hash the typed password with that same salt, then compare to the stored hash. Use a constant-time compare.
> Signup and login must use the same hash settings (same function, same salt handling, same iteration count). If they differ, even the right password will not match.
> Surest check: log in as the seeded test user and as a brand-new account you just created in your own app.
> Confirm you can log in as that user, and that a brand-new account you create also works.
>
> Update output/harness.md with how auth works (what you store for a user and how passwords are protected).
>
> , ensure that login failures return generic error messages (like 'Invalid email or password') to prevent account enumeration attacks. May be add a functionality to lock the account for some time if the same user name and wrong passwords are tried for a large number of times

## 2026-10-22 19:00 (EDT)

> give me a simple example of how the password, hashing and salt were used for security

## 2026-10-22 19:04 (EDT)

> if two users share password, won't the key used to gernate the hass be the same ?

## 2026-10-22 19:15 (EDT)

> we are working
>
> Problem 5:
>
> Build the shop chatbot as a PydanticAI agent behind FastAPI, plugged into your front-end chat widget. Put the API app in backend/main.py — that is the file you run with Uvicorn. Keep the agent as these four files next to it :
>
> backend/prompts/prompt.md — system prompt (grow this same file later)
> backend/agent.py — agent entry / wiring
> backend/tools.py — tools the agent can call
> backend/models.py — Pydantic / PydanticAI structured types
> In main.py, expose a chat route so a message from the website returns a reply from the agent (and whatever else you need for products/auth). You will need your AI model API key for the agent.
>
> Put Campus Customs voice and safety basics into prompts/prompt.md (you will expand tools and safety later). Start or update types in models.py for chat replies / product cards as needed.
>
> In output/harness.md, note how the front end talks to FastAPI and how the agent is loaded (prompt file + model).
>
> Make sure the backend runs from the backend/ folder like this:
>
> uvicorn main:app --reload --port 8000
>
> specify how the chat route should handle conversation history (e.g., passing previous messages or a session ID) so the agent maintains context across multiple turns."

## 2026-10-22 19:43 (EDT)

> Problem 6:
>
> Give the agent tools that look up real information from campus_customs.db:
>
> Product description
> Price
> How many are in stock (by size when the customer asks)
> The agent must use the database — it should not invent prices or quantities. If a size is out of stock, say so clearly.
>
> Expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. Add or update return types in models.py.
>
> In output/harness.md, list each tool and explain which model fields you chose for lookup results and why.
>
> Ensure the database query logic in tools.py handles case-insensitivity and partial text matches. So queries don't fail if a user slightly mispells a product name. Enusre that this app avoid connection leaks.

## 2026-10-22 19:58 (EDT)

> Problem 7:
>
> Now we will add a neat feature to the site. When a customer asks about a type of item — for example "what hoodies do you have?" — the agent should search the catalogue and the website should dynamically show those matching items as product cards (image, name, price, short info).
>
> This is an API contract: the agent returns structured product matches and then the front end renders them on the website. It MUST look super cool.
>
> After the dynamic product cards are loaded by your new feature, make sure the same single-item page behavior you built in Problem 3 still works: each product card — including the ones the chat just put on the page — should still open that detail view (large image + full info) when clicked.
>
> Update prompts/prompt.md and output/harness.md so it is clear how search results reach the page.
>
> Ensure the backend sends the chat message and the product data separately, and clearly define whether these new cards should appear inside the chat window or replace the main page layout.

## 2026-10-22 20:27 (EDT)

> Problem 8:
>
> When a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. The agent should know who is chatting (name, email) — put that in agent deps (or an equivalent clear pattern) and/or tools the agent can call.
>
> Also pass enough page context that if someone is on a product page and asks "do you have this in pink?", the agent knows which item they mean. You can put code into the agent context.
>
> Guests can still chat, but history only needs to persist for logged-in users. Eusure backend can accurately retrieve  saved history  and understand page-specific context.
>
> Document in output/harness.md: how user chat history is stored, what customer fields the agent sees, and how page context is passed.

## 2026-10-22 20:45 (EDT)

> is there any room for improvements? for both front end and back end. explain in simple language. don't make any changes yet.

## 2026-10-22 20:49 (EDT)

> is it possible to generate human models image with product images? don't implement yet. just answer

## 2026-10-22 20:52 (EDT)

> Problem 9:
>
> Now that the core shop works, improve it. Choose and implement:
>
>   Backend
>   - There's no record of which tools it called or what each chat cost. A simple log, or a tool like Logfire, would help with debugging and
>     cost tracking.
>   - Fairer limits. Guests have a message limit, but logged-in users don't, so one account could run up AI costs. Login lockout also lets someone lock out a known
>     email on purpose; adding limits per network address would help.
>   - Longer memory. The agent only sees the last 10 back-and-forths. Older parts of a long conversation could be summarized instead of dropped.
>
>   Frontend
>   - Page titles. Every browser tab says "Campus Customs". Product pages should say the product name, which helps bookmarks and history.
>   - Fresher stock numbers. The product list loads once and isn't refreshed until the page reloads, so stock shown on cards can go stale during a long visit. Chat
>     answers are always live.
>   - Better error recovery. If the server is down, the chat shows an error but has no "Try again" button.
>   - Shopping: add a cart and checkout.
>
> Write output/usability.md before or as you build. For each of the improvements, say:
>
> What you added
> Why it helps a Campus Customs shopper or the business
> Then make sure all improvements actually show up in the running app. Graders will read the write-up and look for the features.

## 2026-10-22 21:18 (EDT)

> I just started the chrome. see if you can test the features you just added.

## 2026-10-22 21:36 (EDT)

> Problem 10
>
> Add creative design so the site feels like a real Campus Customs storefront — fonts, color, hierarchy, motion, product presentation, chat feel. You will get more points for imaginative and innovative design. Be BOLD and imaginative. You want to stand out relative to dozens of campus stores. You want to capture attention and keep the customers enganged.
>
> Write `output/design.md`: what you changed and why it should help customers stick around and buy. Keep it concrete and short.

## 2026-10-22 22:03 (EDT)

> Problem 11
>
> Test the live site and document it in output/app_check.html (a page you can double-click open). Include clear screenshots and short captions for:
>
> Chat checking the inventory level of an item (honest stock/price from the DB)
> The dynamic search-result cards appearing after a category question (e.g. hoodies)
> ONE of the usability features you added in Problem 9 ( may be do the shopping cart)
>
> Make the HTML easy to grade: heading for each check, screenshot, one or two sentences on what the screenshot proves. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png).

## 2026-10-22 22:13 (EDT)

> Problem 12
>
> Keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). Do not wipe it between runs.
>
> Add these safety rules and put them in prompts/prompt.md.
>
>   1. Someone in distress. A campus site will occasionally get a message like "I'm so stressed I want to disappear." Right now the agent would say "I can only help with the shop," which is the wrong response. Rule: if someone mentions self-harm, crisis or danger, respond with care, step out of shopping mode, and point them to help, such as 988 (the US Suicide & Crisis Lifeline) and Yale's mental health services. This should be the one exception to "stay on topic".
>
>   2. No product claims beyond the database. The database has a description, colors, sizes, stock and price, and nothing about fabric, fit, washing, or whether something "runs small". Shoppers ask these things all the time. Rule: never state material, fit, care or sizing advice that isn't in the product data; say "I don't have that detail, the shop can tell you." The same goes for "Is this the official Yale design?": say it's officially licensed, as the shop describes itself, but don't add claims.
>
>   3. Custom printing requests. The agent mentions custom printing, so people will ask "Can you print our team logo / a Harvard joke / a Disney character?" Rule: never agree to or quote a custom job, and don't comment on whether someone else's logo can be used. Say the shop handles custom orders and their rules. Decline to help design anything offensive or harassing.
>
> Finish output/harness.md so it is clear how the system works.
>
> Model fields in models.py and why you chose them
> Tools and abilities
> Safety rules
> Specs (loop limits, result caps, models, how to run front + back)

## 2026-10-22 22:27 (EDT)

> does our folder structure look like this? (pasted target tree: hw4/ with AI_prompts.md, requirements.txt, .env.example, .gitignore, README.md, frontend/, backend/{main.py, agent.py, models.py, tools.py, prompts/prompt.md}, output/{harness.md, design.md, usability.md, app_check.html, app_check_images/, audit_trail.json})

## 2026-10-22 22:33 (EDT)

> let's fix that to meet with requirements

## 2026-10-22 22:37 (EDT)

> Problem 13
>
> Put your code in a folder named hw4 and push it to a public GitHub repository. On Canvas, submit the repo URL (the link graders can open and clone). You do not upload a zip for this homework.
>
> Do not put your real .env, campus_customs.db, or product images in the GitHub repo. Use .gitignore. Include .env.example with placeholders only.
>
> Expected file layout:
>
> hw4/
> ├── AI_prompts.md
> ├── requirements.txt
> ├── .env.example
> ├── .gitignore
> ├── README.md
> ├── frontend/                 # Vite React TypeScript app
> ├── backend/
> │   ├── main.py               # FastAPI app — run with: uvicorn main:app --reload --port 8000
> │   ├── agent.py
> │   ├── models.py
> │   ├── tools.py
> │   └── prompts/
> │       └── prompt.md
> └── output/
>     ├── harness.md
>     ├── design.md
>     ├── usability.md
>     ├── app_check.html
>     ├── app_check_images/     # screenshots linked from app_check.html
>     └── audit_trail.json
>
> Local-only data pack (not in git):
>
> data/
> ├── campus_customs.db
> └── products/                 # images referenced by the catalogue
>
> The agent itself is four files under backend/: prompts/prompt.md, agent.py, tools.py, and models.py.
>
> README.md should explain how to run the front end and back end after placing the data pack.
