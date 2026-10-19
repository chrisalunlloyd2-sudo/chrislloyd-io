# Adding job photos to the site (for Alice)

Chris emails you before/after photos and tells you which job they are. You publish them.

1. Get both photos onto disk (the email attachments). A photo is only ever published as a before/after PAIR.
2. Ask Chris for, or take from his message: a title, a one-line caption, and what each photo shows (alt text). Do not invent any of these. Do not make up a location or year.
3. Confirm Chris said the customer is OK with photos of their home being public. No confirmation: stop and ask him.
4. Run from the repo root:

       python3 scripts/add_gallery.py --before b.jpg --after a.jpg \
         --title "Bedroom repaint" --caption "Walls and ceiling, two coats." \
         --alt-before "Bedroom walls before painting" --alt-after "Same bedroom after painting" \
         --client-ok [--location "Edmonton"] [--year 2026]

   It shrinks the photos to 1200px, strips GPS/EXIF data, saves them in `assets/gallery/`, adds the entry to `data/gallery.json`, and shows the Before & After section (nav link "Gallery").
5. `python3 scripts/test_site_scripts.py` must say OK. Then commit the new files and push to `origin main`. GitHub Pages deploys in about a minute.
6. Tell Chris what went live, with the job title.

Notes: needs Pillow (`pip install pillow`). Customer faces, house numbers and licence plates should not be visible; if you can see any, ask Chris first. Pairs only, one script run per pair.
