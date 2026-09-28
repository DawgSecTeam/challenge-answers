#!/usr/bin/env python3
"""Regenerate index.html for DawgSecTeam/challenge-answers from the huitzilopochtli repo.

Renders every practice box's scenario.yaml (checks, penalty guards, forensics,
authored `solution:` walkthroughs) into a single static, self-contained page:
underline-only search bar, one section per challenge with a claim link (real
pool code pulled from the vms.dawgsec.com portal) and a collapsed spoiler
walkthrough. Deliberately independent of the main site's design system — flat,
minimal, beige(light)/navy(dark), system fonts, zero external references.

Run from the repo root:  python3 tools/generate_challenges.py
Point at a different checkout:  HUITZ_REPO=/path/to/huitzilopochtli python3 ...
"""
import os
import re
import sys

WEBSITE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUITZ_ROOT = os.environ.get(
    "HUITZ_REPO",
    os.path.join(os.path.dirname(WEBSITE_ROOT), "dawgsec", "huitzilopochtli"),
)
sys.path.insert(0, HUITZ_ROOT)

from boxbuilder.answerkey import (  # noqa: E402
    load_scenario,
    goal_line,
    scored_on,
    solution_text,
)
from boxbuilder.mdhtml import markdown_to_html  # noqa: E402

PORTAL_BASE = "https://vms.dawgsec.com/claim?code="

# Real pool codes re-verified against the prod portal's configs.json on
# 2026-09-27 (all eight confirmed unchanged; XPV8Z created 2026-09-25). If a
# pool is retired and re-coded, update the code here and re-run this script.
# `iso` drives the page's default sort (newest run date first); `date` is the
# display string.
BOXES = [
    {"dir": "chocolate-factory", "code": "EUKT7", "os": "Linux", "flavor": "Xubuntu XFCE", "date": "Sept 7, 2026", "iso": "2026-09-07"},
    {"dir": "solar-observatory", "code": "FQP38", "os": "Linux", "flavor": "Xubuntu XFCE", "date": "Sept 10, 2026", "iso": "2026-09-10"},
    {"dir": "coral-reef-station", "code": "REF7M", "os": "Linux", "flavor": "Xubuntu XFCE", "date": "Sept 10, 2026", "iso": "2026-09-10"},
    {"dir": "opochtli-landing", "code": "WP5RC", "os": "Linux", "flavor": "Debian 13 · headless CLI", "date": "Sept 15, 2026", "iso": "2026-09-15"},
    {"dir": "pinecrest-hospital", "code": "3RK37", "os": "Windows", "flavor": "Windows Server", "date": "Sept 17, 2026", "iso": "2026-09-17"},
    {"dir": "static-pine-radio", "code": "SR883", "os": "Linux", "flavor": "Debian 13 · headless CLI", "date": "Sept 22, 2026", "iso": "2026-09-22"},
    {"dir": "meridian-hq", "code": "S6QE5", "os": "Windows", "flavor": "Windows Server · Active Directory", "date": "Sept 23, 2026", "iso": "2026-09-23"},
    {"dir": "vermilion-relay", "code": "XPV8Z", "os": "Linux", "flavor": "Xubuntu XFCE", "date": "Sept 25, 2026", "iso": "2026-09-25"},
]


def inline_md(text):
    """Escape first, then restore the `code` spans the goal lines use."""
    esc = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", esc)


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_box(box):
    path = os.path.join(HUITZ_ROOT, "boxes", box["dir"], "scenario.yaml")
    scenario = load_scenario(path)  # validates exactly as compile would
    meta = scenario.get("scenario") or {}
    checks = scenario.get("checks") or []
    forensics = scenario.get("forensics") or []

    vulns = [c for c in checks if c.get("category") == "vuln"]

    def difficulty_rank(c):
        d = str(c.get("display") or "").strip().upper()
        if d.startswith("EASY"):
            return 0
        if d.startswith("MODERATE"):
            return 1
        if d.startswith("HARD"):
            return 2
        return 3

    # Present the challenges easy -> moderate -> hard, but only for boxes that
    # label every check (chocolate-factory's displays carry no difficulty, and
    # half-sorted reads worse than authored order).
    if vulns and all(difficulty_rank(c) < 3 for c in vulns):
        vulns.sort(key=difficulty_rank)
    penalties = [c for c in checks if c.get("category") != "vuln"]
    vuln_pts = sum(c.get("max_points", 0) for c in vulns)
    for_pts = sum(f.get("points", 0) for f in forensics)

    def anchor(c):
        return "wt-{}-{}".format(box["dir"], c.get("id"))

    def attr_esc(text):
        return esc(text).replace('"', "&quot;")

    def toc_link(c, prefix=""):
        label = "{} {}".format(
            prefix, c.get("display") or c.get("question") or c.get("id")
        ).strip()
        return '      <a href="#{a}" title="{t}">{l}</a>'.format(
            a=anchor(c), t=attr_esc(label), l=esc(label)
        )

    def render_task(c, negative=False):
        pts = abs(c.get("max_points", 0))
        sol = solution_text(c)
        if not sol:
            raise SystemExit(
                f"{box['dir']}: no authored solution for "
                f"{c.get('display') or c.get('id')!r} — backfill it first"
            )
        pts_html = (
            f'<span class="wt-pts">&minus;{pts} pts when triggered</span>'
            if negative
            else f'<span class="wt-pts">{pts} pts</span>'
        )
        return f"""      <section class="wt-item" id="{anchor(c)}">
        <h3>{esc(c.get('display') or c.get('id'))} {pts_html}</h3>
        <p class="wt-meta"><strong>Goal:</strong> {inline_md(goal_line(c))} &nbsp;&middot;&nbsp; <strong>Scored on:</strong> {inline_md(scored_on(c))}</p>
        <div class="wt-body">
{markdown_to_html(sol)}
        </div>
      </section>"""

    def render_fq(i, fq):
        answers = []
        if fq.get("answer"):
            answers.append(fq["answer"])
        answers.extend(fq.get("answers") or [])
        parts = []
        if answers:
            shown = " or ".join("`" + str(a).replace("`", "'") + "`" for a in answers)
            label = "answer" if len(answers) == 1 else "answers"
            parts.append(f"**Accepted {label}:** {shown}")
        sol = solution_text(fq)
        if not sol:
            raise SystemExit(
                f"{box['dir']}: no authored solution for forensic {fq.get('id')!r}"
            )
        parts.append("**How to find it.**\n\n" + sol)
        return f"""      <section class="wt-item" id="{anchor(fq)}">
        <h3>Q{i}. {esc(fq.get('question'))} <span class="wt-pts">{fq.get('points', 0)} pts</span></h3>
        <div class="wt-body">
{markdown_to_html("\n\n".join(parts))}
        </div>
      </section>"""

    sections, toc = [], []
    if vulns:
        sections.append(
            f'      <p class="wt-group">The challenges &middot; {len(vulns)} checks &middot; {vuln_pts} points</p>'
        )
        toc.append('      <p class="wt-toc-group">The challenges</p>')
        sections.extend(render_task(c) for c in vulns)
        toc.extend(toc_link(c) for c in vulns)
    if penalties:
        sections.append(
            f'      <p class="wt-group">Penalties &middot; {len(penalties)} guards &middot; these only subtract</p>'
        )
        toc.append('      <p class="wt-toc-group">Penalties</p>')
        sections.extend(render_task(c, negative=True) for c in penalties)
        toc.extend(toc_link(c) for c in penalties)
    if forensics:
        sections.append(
            f'      <p class="wt-group">Forensics &middot; {len(forensics)} questions &middot; {for_pts} points</p>'
        )
        toc.append('      <p class="wt-toc-group">Forensics</p>')
        sections.extend(render_fq(i, fq) for i, fq in enumerate(forensics, 1))
        toc.extend(
            toc_link(fq, f"Q{i}.") for i, fq in enumerate(forensics, 1)
        )

    total = vuln_pts + for_pts
    card = f"""  <article class="challenge">
    <h2>{esc(meta.get('name'))}</h2>
    <p class="ch-meta">{esc(box['os'])} &middot; {esc(box['flavor'])} &middot; {total} pts &middot; {esc(box['date'])}</p>
    <div class="ch-links">
      <a class="claim" href="{PORTAL_BASE}{box['code']}" rel="noopener">Start challenge VM&nbsp;&rarr;</a>
      <details class="walkthrough">
        <summary>Answer walkthrough</summary>
        <p class="spoiler-note">Spoilers below &mdash; this gives away every point on the box. Try the box first.</p>
        <div class="wt-layout">
          <nav class="wt-toc" aria-label="Answer key contents">
{chr(10).join(toc)}
          </nav>
          <div class="wt-main">
{chr(10).join(sections)}
          </div>
        </div>
      </details>
    </div>
  </article>"""
    return card, {
        "dir": box["dir"],
        "name": meta.get("name"),
        "checks": len(vulns),
        "penalties": len(penalties),
        "forensics": len(forensics),
        "points": total,
    }


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
   <meta charset="UTF-8">
   <meta name="viewport" content="width=device-width, initial-scale=1.0">
   <title>Challenges - DawgSec</title>
   <meta name="description" content="DawgSec hardening practice boxes: claim a VM, lock it down, and check the answer walkthrough when you're stuck.">
   <meta name="theme-color" content="#fcfaf5" media="(prefers-color-scheme: light)">
   <meta name="theme-color" content="#07111f" media="(prefers-color-scheme: dark)">
   <style>
      /* Flat two-tone scheme: near-white with a whisper of warmth in light
         mode, heavy navy in dark. Underlines everywhere a border could go;
         system fonts only. */
      :root {
         --bg: #fcfaf5;
         --ink: #26251f;
         --muted: #7c7666;
         --faint: #c9c0a8;
         --link: #1c3a5e;
         --code-bg: rgba(38, 37, 31, 0.055);
      }
      @media (prefers-color-scheme: dark) {
         :root {
            --bg: #07111f;
            --ink: #ece4d0;
            --muted: #8d9db2;
            --faint: #203050;
            --link: #ece4d0;
            --code-bg: rgba(236, 228, 208, 0.07);
         }
      }
      * { box-sizing: border-box; }
      html { background: var(--bg); scroll-behavior: smooth; }
      body {
         margin: 0;
         background: var(--bg);
         color: var(--ink);
         font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         -webkit-font-smoothing: antialiased;
      }
      main { max-width: 46rem; margin: 0 auto; padding: 5rem 3rem 6rem; }
      ::selection { background: var(--link); color: var(--bg); }
      @media (max-width: 480px) {
         main, footer { padding-left: 1.75rem; padding-right: 1.75rem; }
      }

      a, .claim { color: var(--link); text-decoration: underline; text-underline-offset: 3px; text-decoration-thickness: 1px; }
      a:hover, .claim:hover { text-decoration-thickness: 2px; }
      a:focus-visible, .claim:focus-visible, summary:focus-visible, #search:focus-visible { outline: none; text-decoration-thickness: 2px; color: var(--ink); }
      #search:focus-visible { border-bottom-color: var(--ink); }

      .home { font-size: 0.8rem; color: var(--muted); }
      .home a { color: var(--muted); }
      .home a:hover { color: var(--ink); }

      h1 { font-size: 2rem; font-weight: 700; letter-spacing: -0.01em; margin: 1.5rem 0 0.5rem; }
      .lede { color: var(--muted); margin: 0 0 2.5rem; max-width: 36rem; }

      /* Search — underline only */
      .search-wrap { display: flex; align-items: baseline; gap: 1rem; }
      #search {
         flex: 1; background: transparent; color: var(--ink);
         border: none; border-bottom: 1px solid var(--faint); border-radius: 0;
         padding: 0.5rem 2px; font: inherit;
      }
      #search::placeholder { color: var(--muted); }
      #search:focus { outline: none; border-bottom-color: var(--ink); }
      #count { color: var(--muted); font-size: 0.8rem; white-space: nowrap; }

      #empty { display: none; color: var(--muted); padding: 3rem 0; font-size: 0.9rem; text-align: center; }
      #empty:not([hidden]) { display: block; }

      /* Challenge sections — spacing, not boxes or rules */
      .challenge { margin-top: 3rem; }
      .challenge:first-of-type { margin-top: 3.5rem; }
      .challenge h2 { font-size: 1.3rem; font-weight: 650; margin: 0; letter-spacing: -0.005em; }
      .ch-meta { color: var(--muted); font-size: 0.95rem; margin: 0.25rem 0 0; }
      .ch-links { margin-top: 0.75rem; display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.35rem 1.75rem; }
      .claim { font-weight: 600; }

      details.walkthrough { min-width: 0; }
      details.walkthrough > summary {
         cursor: pointer; user-select: none; color: var(--link); font-weight: 500;
         text-decoration: underline; text-underline-offset: 3px; text-decoration-thickness: 1px; list-style: none;
      }
      details.walkthrough > summary::-webkit-details-marker { display: none; }
      details.walkthrough > summary::before { content: "\\25B8\\2003"; color: var(--muted); }
      details.walkthrough[open] > summary::before { content: "\\25BE\\2003"; }
      details.walkthrough > summary:hover, details.walkthrough[open] > summary { text-decoration-thickness: 2px; }

      /* Answer-key table of contents. On wide screens it hangs off the left
         edge of the column into the page gutter (sticky, scroll-aware) so the
         answer text keeps its full width; where the gutter is too small it's
         simply hidden. */
      .wt-toc { display: none; }
      @media (min-width: 72rem) {
         .wt-toc {
            display: block;
            position: sticky; top: 2.5rem;
            float: left; clear: left;
            width: 13rem; margin-left: -15rem;
            max-height: calc(100vh - 5rem); overflow-y: auto;
            font-size: 0.72rem; line-height: 1.5;
            overscroll-behavior: contain;
         }
      }
      .wt-toc-group { color: var(--muted); font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.09em; margin: 1.4rem 0 0.2rem; }
      .wt-toc a {
         display: block; color: var(--muted); text-decoration: none;
         white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0.16rem 0;
      }
      .wt-toc a:hover { color: var(--ink); text-decoration: underline; text-underline-offset: 3px; }
      .wt-toc a.active { color: var(--ink); text-decoration: underline; text-underline-offset: 3px; }

      .spoiler-note { color: var(--muted); font-style: italic; font-size: 0.85rem; margin: 1.25rem 0 0; }
      .wt-group { color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.09em; margin: 2rem 0 0.25rem; }
      .wt-item { margin-top: 3.25rem; scroll-margin-top: 1.5rem; }
      .wt-item h3 { font-size: 0.98rem; font-weight: 600; line-height: 1.5; margin: 0; }
      .wt-pts { color: var(--muted); font-weight: 400; font-size: 0.78rem; white-space: nowrap; margin-left: 0.4rem; }
      .wt-meta { color: var(--muted); font-size: 0.82rem; margin: 0.2rem 0 0; }
      .wt-meta code { font-size: 0.9em; }

      .wt-body { font-size: 0.92rem; line-height: 1.7; margin-top: 0.5rem; }
      .wt-body p { margin: 0.5rem 0; }
      .wt-body ul, .wt-body ol { margin: 0.5rem 0; padding-left: 1.4rem; }
      .wt-body li { margin: 0.3rem 0; }
      .wt-body h1, .wt-body h2, .wt-body h3, .wt-body h4 { font-size: 0.92rem; margin: 0.9rem 0 0.3rem; }
      .wt-body code { background: var(--code-bg); border-radius: 3px; padding: 0.08rem 0.35rem; font-size: 0.85em; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
      .wt-body pre { background: var(--code-bg); border-radius: 4px; padding: 0.7rem 0.9rem; overflow-x: auto; margin: 0.6rem 0; }
      .wt-body pre code { background: none; border-radius: 0; padding: 0; font-size: 0.8rem; line-height: 1.55; }
      .wt-body a { color: var(--link); }
      .wt-body hr { border: none; border-top: 1px solid var(--faint); margin: 1rem 0; }

      footer { max-width: 46rem; margin: 0 auto; padding: 0 3rem 6rem; color: var(--muted); font-size: 0.8rem; }
      footer a { color: var(--muted); }
      footer a:hover { color: var(--ink); }
   </style>
</head>
<body>

   <main>
      <p class="home"><a href="https://dawgsec.com">&larr; dawgsec.com</a></p>
      <h1>Challenges</h1>
      <p class="lede">Hands-on hardening boxes for DawgSec workshops and CDE prep. Start a challenge VM, lock it down &mdash; the scoring agent re-checks the box while your fixes hold. When you're stuck (or done), the walkthrough gives it away.</p>

      <div class="search-wrap">
         <input id="search" type="search" placeholder="Search challenges&hellip;" autocomplete="off" autofocus>
         <span id="count">@@TOTAL@@ of @@TOTAL@@</span>
      </div>

      <div id="empty" hidden>No challenges match &mdash; clear the search to see all @@TOTAL@@.</div>

@@CARDS@@
   </main>

   <footer>
      <p>Powered by <a href="https://github.com/DawgSecTeam/huitzilopochtli" target="_blank" rel="noopener">huitzilopochtli</a> &middot; starting a challenge provisions a fresh VM from <a href="https://vms.dawgsec.com" rel="noopener">vms.dawgsec.com</a></p>
   </footer>

   <script>
      (function () {
         var input = document.getElementById("search");
         var count = document.getElementById("count");
         var empty = document.getElementById("empty");
         var cards = Array.prototype.slice.call(document.querySelectorAll(".challenge"));
         var haystacks = cards.map(function (card) {
            var clone = card.cloneNode(true);
            var spoilers = clone.querySelector("details.walkthrough");
            if (spoilers) spoilers.remove(); /* walkthrough content is not searchable */
            return clone.textContent.toLowerCase();
         });
         function apply() {
            var q = input.value.trim().toLowerCase();
            var shown = 0;
            cards.forEach(function (card, i) {
               var hit = !q || haystacks[i].indexOf(q) !== -1;
               card.hidden = !hit;
               if (hit) shown++;
            });
            count.textContent = shown + " of " + cards.length;
            empty.hidden = shown !== 0;
         }
         input.addEventListener("input", apply);
         document.addEventListener("keydown", function (e) {
            if (e.key === "/" && document.activeElement !== input && !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) {
               e.preventDefault();
               input.focus();
            }
         });

         /* Walkthrough scrollspy: per open answer key, mark the item nearest
            above the activation line as active in its TOC and keep the TOC
            scrolled so the active entry stays visible. */
         var spyTick = false;
         function spy() {
            spyTick = false;
            var line = window.innerHeight * 0.28;
            document.querySelectorAll("details.walkthrough[open]").forEach(function (d) {
               var active = null;
               d.querySelectorAll(".wt-main .wt-item").forEach(function (item) {
                  if (item.getBoundingClientRect().top <= line) active = item.id;
               });
               if (d.__spyActive === active) return;
               d.__spyActive = active;
               var toc = d.querySelector(".wt-toc");
               toc.querySelectorAll("a").forEach(function (a) {
                  var on = active !== null && a.getAttribute("href") === "#" + active;
                  a.classList.toggle("active", on);
                  if (on) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current");
               });
               if (active !== null && toc) {
                  var a = toc.querySelector('a[href="#' + active + '"]');
                  if (a && (a.offsetTop < toc.scrollTop || a.offsetTop + a.offsetHeight > toc.scrollTop + toc.clientHeight)) {
                     toc.scrollTop = a.offsetTop - toc.clientHeight * 0.35;
                  }
               }
            });
         }
         function spySoon() {
            if (!spyTick) { spyTick = true; requestAnimationFrame(spy); }
         }
         window.addEventListener("scroll", spySoon, { passive: true });
         window.addEventListener("resize", spySoon);
         document.querySelectorAll("details.walkthrough").forEach(function (d) {
            d.addEventListener("toggle", spySoon);
         });
         spy();
      })();
   </script>

</body>
</html>
"""


def main():
    cards, stats = [], []
    for box in sorted(BOXES, key=lambda b: b["iso"], reverse=True):  # newest run date first
        card, stat = build_box(box)
        cards.append(card)
        stats.append(stat)
    html = PAGE.replace("@@CARDS@@", "\n\n".join(cards)).replace(
        "@@TOTAL@@", str(len(cards))
    )
    out = os.path.join(WEBSITE_ROOT, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    for s in stats:
        print(
            f"{s['dir']}: {s['checks']} checks + {s['penalties']} penalty"
            f" + {s['forensics']} forensics = {s['points']} pts ({s['name']})"
        )
    print(f"wrote {out} ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()
