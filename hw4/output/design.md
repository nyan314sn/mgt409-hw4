# Campus Customs — Design (Problem 10)

## Concept: "Varsity After Dark"

A college locker room after a night game: **varsity lettering, neon pink on black, jersey stripes, pennants, and a scoreboard**. Most campus stores look like a generic online store with a crest on top. This one is meant to feel like *Yale merch from a shop with personality*. Every bit of motion either shows a product or moves the shopper one step closer to buying it.

## What changed, and why it helps people stay and buy

| Change | What it is | Why it should help |
|---|---|---|
| **Varsity type system** | Added **Graduate** (varsity block letters) for scoreboard numbers, prices, hang tags, pennants, and the brand mark. **Fraunces** stays for headlines and **Inter** for body text. | Instantly reads as "college athletics". Prices in varsity numerals get noticed, and three clear type roles make the hierarchy obvious. |
| **Neon "YALE" hero** | The word YALE switches on like a neon sign when the page loads. A giant outlined "BOOLA BOOLA" scrolls slowly behind it. | Gets attention in the first second, and the Yale cheer gives it local pride no generic store has. |
| **Hanging jersey rack** | Three real products hang on a rail with hooks. They sway gently and drift toward the cursor, each with a pink price tag. | Products, not stock photos, are the first thing you see, with prices up front. The motion invites the mouse to explore. |
| **Live scoreboard** | LED-style tiles: **102** pieces on the rack · **11** college crests · **33** team pieces · **57** Broadway. Counted from the live catalogue. | Real numbers show the range at a glance and build trust, with no made-up claims. |
| **"Live from the rack" ticker** | A strip of real low-stock sizes ("🔥 Only 2 left · Benjamin Franklin 1/4 Zip · S") mixed with Yale chants. Every item links to its product and the strip pauses on hover. | Honest urgency, since it comes straight from inventory. It gives shoppers a reason to act now and a one-click path to the product. |
| **Find Your Fit quiz** | Three tap-only questions (who it's for → vibe → budget). The answers reveal real, in-stock matches in the Spotlight, e.g. "Cozy picks for Mom under $80 · 8 of 37 matches". | Gift buyers (parents, alumni) are the shoppers most likely to get stuck. A playful quiz with no typing beats a filter panel and ends on products. |
| **Story "jerseys"** | The five "shop by story" tiles look like jersey backs: big outlined numbers 01–05 that light up neon on hover, with sleeve stripes along the hem. | Makes the ways into the catalogue fun to explore instead of a plain list of links. |
| **Pennant wall** | The 14 residential colleges hang as clipped pennants with item counts. They swing on hover; colleges with no gear yet are faded. | Every Yalie looks for their college. This is the most shareable, recognizable section and goes straight to that college's gear. |
| **Product cards that tilt** | Cards tilt toward the cursor with a light glare, wear a varsity **hang-tag price**, and show honest badges ("🔥 Only 2 left in L"). | Feels physical, like flipping through a rack. Scarcity is shown only when true. |
| **Quick add on every card** | Hover a card and a size bar slides up. One tap adds that size to the cart ("✓ Added M", and the cart badge pops). Sold-out sizes are struck through. Works in grids and in the Spotlight. | Removes steps between "I like that" and "it's in my cart". It works even on chat results. |
| **Product page** | Hover zoom on the photo (follows the cursor, so you can see crest stitching), jersey stripes under the name, plus the existing size picker with live stock. | Close-up detail answers "what does the crest look like?" without a trip to the store. |
| **Storefront block** | A pink-and-white scalloped awning, a flickering neon "CAMPUS CUSTOMS" sign, and a brass "57" door, with "Reserve online. Pick up on Broadway." | Ties the website to the real shop. Pickup reservations bring shoppers through the door, where they can try things on and buy more. |
| **Chat: "The Counter"** | The assistant is named after the shop counter. Its header has jersey stripes and the launcher has a pulsing neon ring. Replies pop in; while it thinks, paw prints 🐾 bounce. | A friendlier, branded helper gets used more than a generic "chat" button. |
| **Chat teaser** | After 6 seconds, a small bubble rotates through questions ("Shopping for Mom? I'll pick 3 in your budget."). One tap opens the chat with a matching question ready to send. Shown once per visit; easy to dismiss. | Starts conversations with people who wouldn't open a chat on their own. A ready question removes the blank-box problem. |
| **Follow-up chips** | After a reply that puts products on the page: "Which is the cheapest?", "Any in navy?", "What's in stock in M?". | Keeps the conversation going toward a decision without typing. |
| **Reservation confetti** | A pink-and-white confetti burst on the order confirmation page. | A small reward at the moment of commitment. Makes the purchase feel like a win and the pickup worth looking forward to. |
| **Texture & details** | Light film grain over the whole site, jersey stripes under the nav, glowing primary buttons, sections that fade in as you scroll. | Adds richness and depth so the dark theme feels designed, not empty. |

## Guardrails kept

- **Honest data:** every number, "only N left" badge, and ticker item comes from the live catalogue. Nothing is invented.
- **Accessible:**
  - Everything turns off under "reduce motion": no marquee, swaying, tilt, zoom, confetti, or scroll animation.
  - Quick add and the quiz are real buttons with labels.
  - Pennants and ticker links work with a keyboard.
  - Contrast stays high on the dark background.
- **Touch screens:** on phones, quick add shows below the photo instead of on hover. The hero, quiz, and storefront stack into one column.
- **Brand:** the black-and-pink style from AGENTS.md is kept, and pushed further.

## Checked in Chrome

All of this was clicked through in a real browser:
- **Home:** the hero, scoreboard, and ticker.
- **Quiz:** Mom → Cozy → Under $80 gave "Cozy picks for Mom under $80", 8 of 37 matches.
- **Story jerseys and pennant wall.**
- **Quick add:** added the Saybrook Sweater Fleece Jacket in M, and the cart badge showed 1.
- **Storefront block.**
- **Chat:** the teaser opened the chat with its question ready. The reply showed the Spotlight, the paw-print typing dots, and the follow-up chips.

Three layout bugs found while looking were fixed:
- The "Top pick" ribbon covered the price tag.
- The pennant wall wasn't aligned with the rest of the page.
- Item counts covered long college names.
