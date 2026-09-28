# challenge-answers

DawgSec's challenge listing with the full answer walkthrough for every
practice box. Served at <https://dawsecteam.github.io/challenge-answers/>.

⚠️ **Everything behind an "Answer walkthrough" toggle is a spoiler** — it gives
away every point on the box. Play the boxes first:
[start a challenge VM](https://vms.dawgsec.com).

## Regenerating

`index.html` is generated — don't edit it by hand. From the repo root:

```bash
python3 tools/generate_challenges.py
```

The generator renders each box's `scenario.yaml` (checks, penalty guards,
forensics, and the authored `solution:` walkthroughs) out of a
[huitzilopochtli](https://github.com/DawgSecTeam/huitzilopochtli) checkout and
fails if any check or forensics question is missing its authored solution. By
default it expects a sibling checkout at `../dawgsec/huitzilopochtli`; point it
elsewhere with `HUITZ_REPO=/path/to/huitzilopochtli`.

Pool claim codes are hardcoded in the `BOXES` list at the top of
`tools/generate_challenges.py` — if a pool is retired and re-coded, update the
code there and re-run.

## Deploying

GitHub Pages: deploy from a branch, `main` / root — `index.html` at the repo
root is the whole site.
