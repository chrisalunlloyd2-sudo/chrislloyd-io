# Blog draft templates (ready-to-paste `add_post.py` commands)

Three reusable skeletons for `scripts/add_post.py`. **These templates are NOT in
`data/posts.json` — nothing here is live until you run the command yourself.**

## How publishing works (read once)

- `scripts/add_post.py` appends to `data/posts.json`. Everything in that file
  renders publicly on `blog.html` (client-side) and is listed in `sitemap.xml`
  (regenerated automatically by `add_post.py`).
- Therefore: **edit the body file first, run the command only when the draft is
  final.** If you must stage an unfinished post, keep the word `PLACEHOLDER` in
  its excerpt — `scripts/gen_sitemap.py` skips posts whose excerpt/body contain
  that word, so crawlers never see it.
- The blog renders body paragraphs as flat `<p>` (no markdown). Section headings
  below are written as led paragraphs ("Assess and repair — ...") to match the
  style already used by the drafts in `blog-drafts/`.
- Workflow per template:
  1. Save the fenced body block to `blog-drafts/<filename>.md`
     (blank lines split paragraphs — same convention as `--body-file`).
  2. Replace every `[EDIT-ME: ...]` marker and set the real publish date.
  3. Run the command. Slugs are auto-deduped ("-2" suffix) — if the title
     collides with an existing post, that's a hint the topic already exists
     (template 1 overlaps the live DRAFT "How to prep walls before painting:
     Edmonton interior checklist"), so confirm the duplicate is intended.

Business facts used below come from existing site copy only (services:
interior/exterior painting, home renovation; service areas: Edmonton,
Sherwood Park, Spruce Grove, St. Albert, Leduc). Verify against the live copy
before publishing.

---

## Template 1 — Paint prep

Title (question-style): **How do I prep walls before painting in Edmonton?**
Local angle: Edmonton's dry winter air and what it does to drying times.

```bash
python3 scripts/add_post.py \
  --title "How do I prep walls before painting in Edmonton?" \
  --date 2026-04-01 \
  --excerpt "What wall prep actually involves before paint goes on in an Edmonton home — assessment, cleaning, filling and sanding, masking, and priming — and why dry winter air changes drying times." \
  --body-file blog-drafts/how-do-i-prep-walls-before-painting-in-edmonton.md
```

Body (save as `blog-drafts/how-do-i-prep-walls-before-painting-in-edmonton.md`;
`--date` above is an example — set it to the day you publish):

```
A paint job is only as good as the surface under it. Before any interior
painting job in Edmonton gets a roller near it, the walls go through five
stages: assess and repair, clean, fill and sand, tape and mask, and prime.
Skipping any of them is why a fresh coat starts looking tired within a season.

Assess and repair — walk every wall with a bright light raked across the
surface and mark what the paint is hiding: nail pops, dents, hairline cracks,
and any previous filler that has crumbled or let go. [EDIT-ME: describe the
repair approach for the specific walls in the job — e.g. drywall patches vs.
plaster, who does the repair, what gets redone rather than painted over.]

Clean — dust, kitchen grease and scuffs all stop paint from gripping.
Wash-down and a vacuum before anything wet goes on. [EDIT-ME: cleaners/method
used on the actual job.]

Fill and sand — fill dents and dimples, then sand flush and feathered past
the edge of every repair. Edmonton's heated indoor air is very dry, which
pulls moisture out of fillers and primers quickly: patches can shrink or
flash off faster than the label time suggests, so check each one before the
next coat and don't trust the clock alone. [EDIT-ME: filler/primers used on
the job and observed dry times in your conditions.]

Tape and mask — cut lines, outlets, trim and floors protected before the
first brush opens. [EDIT-ME: what on the actual job needed masking and why.]

Prime — new drywall, repaired spots, stains and dark colour changes all get
primer so the top coat covers evenly. [EDIT-ME: priming decisions on the
actual job.]

Prep is most of the hours on an interior repaint, which is why quotes should
spell it out rather than promise a same day transformation. If you're
comparing painters in Edmonton, ask what their prep includes.
```

---

## Template 2 — Renovation checklist

Title: **Room renovation checklist: a contractor's order of operations**
(Informational long-tail title; per `add_post.py` SEO note, avoid
transactional titles like "buy..." — this one qualifies.)

```bash
python3 scripts/add_post.py \
  --title "Room renovation checklist: a contractor's order of operations" \
  --date 2026-05-01 \
  --excerpt "The order a room renovation follows end to end — plan, permits, protection, demo, rough-in, drywall, paint, floors, trim and the punch list — from a contractor who runs them in Edmonton." \
  --body-file blog-drafts/room-renovation-checklist-contractors-order-of-operations.md
```

Body (save as
`blog-drafts/room-renovation-checklist-contractors-order-of-operations.md`):

```
A room renovation goes wrong in the same way every time: steps done out of
order. Paint before drywall repairs show through, floors before paint means
overspray on a brand new surface. This is the order of operations that holds
whether the room is a bathroom, basement or whole main floor. [EDIT-ME: tie
the opening to the specific room/job.]

1. Plan — fixtures, finishes and layout decided before demo, and a written
scope so ordering material doesn't stall the job. [EDIT-ME: scope of the
actual project.]

2. Permits — electrical, plumbing and structural changes usually need one in
Edmonton. [EDIT-ME: whether the project needed a permit and who pulled it —
do not state permit rules you haven't verified.]

3. Protect — floors, doorways and the path to the dumpster sheeted before the
first swing. Renovation dust travels.

4. Demo — strip to what the plan needs, haul promptly, keep the room
workable. [EDIT-ME: what the demo uncovered — every job finds something.]

5. Rough-in — electrical and plumbing changes inspected before walls close.

6. Drywall — hanging, taping, sanding; light raking across the surface to
check flushness before primer.

7. Paint — walls and ceilings finished before anything that can be damaged by
overspray or ladders goes in.

8. Floors — installed after paint so a brand new surface never meets a drop
cloth or a scaffolding foot.

9. Trim — baseboards, casings and doors last; caulk and final touch-up with
the furniture back in the room.

10. Punch list — walk the room with the client and list every nag: a paint
nib, a scuffed casing, a sticky door. Nothing is finished until the list is
empty. [EDIT-ME: the real punch list from the job and how long it took to
close out.]

Reno order is not glamorous, but it's the difference between a renovation
that wraps and one that drags. If you're planning a room in the Edmonton
area, start from the list and work down.
```

---

## Template 3 — Seasonal

Title: **Best time to paint the exterior of an Edmonton home**

```bash
python3 scripts/add_post.py \
  --title "Best time to paint the exterior of an Edmonton home" \
  --date 2026-06-01 \
  --excerpt "Edmonton's exterior painting season, plainly: why summer through early fall is the window, why interior painting is the natural winter job, and what a cold snap does to fresh paint." \
  --body-file blog-drafts/best-time-to-paint-the-exterior-of-an-edmonton-home.md
```

Body (save as
`blog-drafts/best-time-to-paint-the-exterior-of-an-edmonton-home.md`):

```
The short answer for Edmonton: exterior painting is a summer through early
fall job. Paint needs air and surface temperatures it can cure in, and an
Alberta spring or fall can hand you a morning below curing range and an
afternoon scorching the same wall.

The window, roughly — once overnight lows hold well above the paint's minimum
application temperature and daytime surfaces aren't too hot to touch, the
season is open; it closes when fall nights start flirting with frost.
[EDIT-ME: the season as it actually played out on your jobs this year — first
exterior start date, last exterior finish date.]

Cold snaps are the real risk. A sudden Alberta cold snap on a wall painted
the day before can stop a coat from curing properly — poor adhesion, uneven
sheen, early failure. Watch the forecast backwards and forwards: night lows
matter as much as day highs. [EDIT-ME: confirm the curing requirements on the
current product's label for the paint you're quoting — don't quote numbers
from memory.]

Siding, trim and prep have the same window but prep can start earlier:
scraping loose paint and washing can happen on cool days, which is why early
bookings finish the season well. [EDIT-ME: how your crews sequence prep vs.
paint through the season.]

Interior painting is the flip side: Edmonton homes are closed up from
October to April and inside work doesn't care what the weather does, which
is exactly why interior projects book through winter. [EDIT-ME: your winter
booking pattern and lead times.]

So if the exterior is on your list, you're really deciding between booking
early for a summer slot or joining the queue — and using the off-season to
plan it. [EDIT-ME: quote/booking note — do not invent prices or availability
claims.]
```

---

## Notes

- Bodies use the `--body-file` convention (blank lines split paragraphs), not
  repeated `--body` flags — easier to edit in place.
- Every `[EDIT-ME: ...]` must be gone before publishing. Anything appended to
  `data/posts.json` is live.
- `scripts/test_site_scripts.py` should stay green after publishing
  (`add_post.py` regenerates the sitemap automatically).