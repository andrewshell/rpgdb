# RPG Shelf

A catalogue of the tabletop RPG books I own, published as a phone-friendly "Do I own…?" page so I
can check before buying at conventions.

- `books.py`: a CLI that keeps the catalogue in `books.db` (SQLite) and covers in `covers/`. Book
  details and cover art come from DriveThruRPG; anything it doesn't carry is entered by hand with a
  cover cropped from a photo.
- `site/`: an 11ty project that builds the static search page.

## Setup

Requires macOS (cover thumbnails use `sips`), Python 3 and Node.js.

    cd site && npm install

## Adding books

The easy way: lay books out on a table, take a photo, and give it to Claude Code in this folder.
`CLAUDE.md` tells it how to identify, look up and add every book in the photo.

By hand:

    python3 books.py owned "precipice"          # do I already have it?
    python3 books.py search "precipice of corruption"
    python3 books.py add 343571                 # DriveThruRPG productId from the search
    python3 books.py add 343571 --another-copy  # I own a second physical copy

    # not on DriveThruRPG
    python3 books.py add-manual "Isle of Hex" --author "Diogo Barros" --cover cover.jpg --notes "DCC RPG compatible"

## Fixing entries

    python3 books.py list                        # shows each book's #id
    python3 books.py edit 88 --notes "Legendary Kingdoms Book Two"   # notes are searchable
    python3 books.py edit 88 --title "..." --publisher "..."
    python3 books.py set-cover 66 my-cover.jpg   # use my copy's cover (special editions)
    python3 books.py remove 13

## Publishing

    python3 books.py export && (cd site && npm run build)
    rsync -av --delete site/_site/ <server>:<path>/

Preview locally with `cd site && npm run serve`.

The page has a `noindex` tag but no password, so anyone with the URL can see it.

## Caveat

DriveThruRPG lookups use its undocumented storefront API (`api.drivethrurpg.com/api/vBeta`). If it
stops working, `add-manual` still does.
