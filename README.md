# Ox morgonbrief
Static site (GitHub Pages, main branch root). Public at https://oskarwkarlsson.github.io/ox-brief/

Datacentrrs writes each weekday's Swedish brief to `briefs/YYYY-MM-DD.md` (about 06:50 Berlin time).

## Publish a brief
    python3 render.py briefs/YYYY-MM-DD.md [--headline "Rubrik för kortet"]
    git add index.html briefs/YYYY-MM-DD.html && git commit -m "Ox morgonbrief YYYY-MM-DD" && git push

The script writes `briefs/YYYY-MM-DD.html`, adds or replaces the index card (newest first) and removes the placeholder. Re-running is safe. `--all` renders every `.md`.
Card headline: `--headline`, else a `<!-- rubrik: ... -->` line in the .md, else the first `#` heading, else the first paragraph.

`state.json` (Datacentrrs dedupe state) and `briefs/*.md` are gitignored and never published. No em-dashes.
