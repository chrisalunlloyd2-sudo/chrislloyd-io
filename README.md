# chrislloyd-io

Website for **Chris Alun Lloyd Ltd** — painting & home renovation services, an
Amazon affiliate shop, and a compendium of open-source business-automation
tools.

Live: https://chrisalunlloyd2-sudo.github.io/chrislloyd-io/
Custom domain (once DNS is pointed): https://chrislloyd.io (see `CNAME`).

Plain static HTML/CSS/JS. No build step, no frameworks, no dependencies.

## How content works

**You never edit `index.html` to change content.** All page content is loaded
from JSON files in `data/`:

| File | Feeds section |
|---|---|
| `data/site.json` | Hero text, tagline, email, social links, footer name |
| `data/services.json` | Services grid |
| `data/shop.json` | Shop grid (Amazon affiliate cards) |
| `data/opensource.json` | Open-source project cards |

### Add a service / product / project

Use the helper script (works from a phone via Termux/SSH, or any editor):

```sh
python3 scripts/add_item.py services --title "Decking build" --desc "Garden decking and repairs."
python3 scripts/add_item.py shop --title "Trade roller set" --url "https://www.amazon.co.uk/dp/XXXX" --category Paint
python3 scripts/add_item.py opensource --title "my-tool" --desc "Timekeeping CLI" --url "https://github.com/chrisalunlloyd2-sudo/my-tool" --tags cli,timekeeping
```

`id` is auto-generated from the title if omitted. Shop entries without a `url`
are flagged `"placeholder": true` and render with a dashed border. Or edit the
JSON directly — same effect. `site.json` fields:

```sh
python3 scripts/add_item.py site --field tagline --value "New tagline"
```

Commit + push after editing and GitHub Pages redeploys automatically (usually
within a minute or two).

## Custom domain

`CNAME` is pre-set to `chrislloyd.io`. When the domain is registered, add DNS
records at the registrar:

- `A` records for `chrislloyd.io` → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
- `CNAME` record for `www` → `chrisalunlloyd2-sudo.github.io`

Then verify the domain under *Settings → Pages* in this repo.

## Notes

- Social links with empty `url` render as placeholders — fill them in
  `data/site.json` as accounts get set up.
- No credentials, payments, or analytics in this repo. Amazon links are
  affiliate links added via `data/shop.json`.