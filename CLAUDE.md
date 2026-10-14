# TTRPG collection

A catalogue of the owner's physical RPG books, built so they can check "do I already own this?" on
their phone at conventions. `books.py` (stdlib Python, macOS `sips` for images) keeps the catalogue in
`books.db` and covers in `covers/`. `site/` is an 11ty project that renders a searchable static
page from `site/src/_data/books.json`; `site/_site/` is what gets uploaded.

## Commands

    python3 books.py search "<query>"          # DriveThruRPG lookup → productId, title, authors
    python3 books.py owned "<query>"           # check the local catalogue (title + notes)
    python3 books.py add <productId> [--notes ...] [--another-copy]
    python3 books.py add-manual "<title>" --author A --author B --publisher P --cover crop.jpg --notes ...
    python3 books.py set-cover <id> <image>    # replace a cover with the owned copy's
    python3 books.py edit <id> [--title] [--publisher] [--notes]
    python3 books.py remove <id>
    python3 books.py list
    python3 books.py export                    # writes site/src/_data/books.json + site/src/covers/

## Cataloguing a batch photo

The user lays books out on a table and sends a photo. Process every book in it:

1. If it's HEIC, convert it first: `sips -s format jpeg IMG.heic --out full.jpg`. Pasted images land
   in `~/.claude/uploads/...`; work on copies in the scratchpad, never next to the original.
2. Read every title off the covers, row by row. Note duplicates in the photo (it has happened).
3. For each title run `owned` first, then `search`. If the top hit isn't clearly the same book, retry
   with the author, publisher or system (e.g. "DCC") added. When several hits are plausible
   (editions, volume 1 vs 2, DCC vs 5E vs Roll20/Foundry VTT versions, language editions), compare
   the cover: `thumbnail` from `api.drivethrurpg.com/api/vBeta/products/<id>?siteId=10`, served from
   `https://d1vzi28wh99zvq.cloudfront.net/images/<thumbnail>`. Skip `[BUNDLE]`, VTT and PDF-only extras.
4. `add <productId>`. It prints `ALREADY OWNED` instead of duplicating; use `--another-copy` only
   when a second physical copy is actually in the photo.
5. Not on DriveThruRPG: crop the cover from the full-resolution photo and look at the crop before
   adding it. Then `add-manual` with everything readable on the cover.
   - `sips -c <h> <w> --cropOffset <y> <x> photo.jpg --out crop.jpg`. Coordinates are in the
     photo's real pixels (`sips -g pixelWidth`), not the downscaled view you see; scale them.
   - Make previews with `sips -Z 260 crop.jpg --out crop_s.jpg`. `sips -Z` without a distinct
     `--out` filename overwrites the full-size crop.
6. Special or limited edition with a different cover than DriveThruRPG's: `add` the product, then
   `set-cover <id> crop.jpg` and say so in notes.
7. If the series name, edition or cover subtitle isn't in the title, put it in notes with `edit`
   (e.g. "Legendary Kingdoms Book Two", "Solo RPG Guide", "2024 revision; 5.5e"). Notes are
   searchable, and this is the only way a series search finds the book.
8. No readable title (cipher or art-only covers, spine-only titles): ask the user rather than guess.
9. `export`, then `cd site && npm run build`. Report what was added, what was entered by hand,
   which edition you chose when there was a choice, and anything uncertain.

## Known gaps on DriveThruRPG

- Wizards of the Coast print books (D&D core books, adventures): only Roll20 VTT listings exist.
  Add by hand and put the year in the title, e.g. "Player's Handbook (2024)".
- Goodman Games' DCC Lankhmar line, Kickstarter add-ons, stretch-goal booklets, preview booklets.
- Many indie zines are itch.io-only. itch.io answered scripted search with HTTP 429; don't work
  around that, crop the cover instead.
- Comics occasionally show up in batches; add them with notes "Comic".

## Publishing

    python3 books.py export && (cd site && npm run build)   # local build only
    cd site && npm run sync                                  # export + build + rsync to the live site

The build wipes `site/_site` first so removed or replaced covers don't linger. `sync` publishes
to the live site (target in `SYNC_TARGET` or `.sync-target`); only run it when the user asks.
DriveThruRPG's `api/vBeta` is undocumented; if it stops working, `add-manual` still works.
