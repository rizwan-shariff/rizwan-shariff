#!/usr/bin/env python3
"""Generate an animated LeetCode "snake eats your submissions" SVG (dark + light)."""
import json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone

USERNAME = os.environ.get("LEETCODE_USER", "3GasfAhrSD")
OUT_DIR = os.environ.get("OUT_DIR", "dist")
WEEKS, CELL, GAP, PAD, TOP = 53, 11, 3, 16, 34
STEP = CELL + GAP          # distance between cell centres
SPEED = 0.045              # seconds per cell
SNAKE_LEN = 6

THEMES = {
    "leetcode-snake-dark.svg": dict(bg="#0f0c29", empty="#2a2a3d", text="#a78bfa",
        levels=["#5c3d00", "#a86b00", "#e08a00", "#ffa116"], head="#a78bfa", body="#7c3aed"),
    "leetcode-snake.svg": dict(bg="#ffffff", empty="#ebedf0", text="#5b21b6",
        levels=["#ffe2ae", "#ffc766", "#ffa116", "#c47800"], head="#7c3aed", body="#a78bfa"),
}

def fetch_calendar():
    if os.environ.get("LOCAL_JSON"):                      # for offline testing
        return json.load(open(os.environ["LOCAL_JSON"]))
    query = """query($u:String!){matchedUser(username:$u){userCalendar{submissionCalendar}}}"""
    req = urllib.request.Request(
        "https://leetcode.com/graphql",
        data=json.dumps({"query": query, "variables": {"u": USERNAME}}).encode(),
        headers={"Content-Type": "application/json", "Referer": "https://leetcode.com",
                 "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    user = (data.get("data") or {}).get("matchedUser")
    if not user:
        sys.exit(f"LeetCode user '{USERNAME}' not found or profile is private")
    return json.loads(user["userCalendar"]["submissionCalendar"])

def build_cells(cal):
    counts = {}
    for ts, n in cal.items():
        d = datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
        counts[d] = counts.get(d, 0) + int(n)
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=(today.weekday() + 1) % 7) - timedelta(weeks=WEEKS - 1)
    cells = []
    for w in range(WEEKS):
        rows = range(7) if w % 2 == 0 else range(6, -1, -1)   # zig-zag path
        for r in rows:
            d = start + timedelta(days=w * 7 + r)
            if d <= today:
                cells.append(dict(w=w, r=r, n=counts.get(d, 0), d=d))
    return cells

def level(n, mx):
    if n <= 0: return -1
    q = n / mx
    return 0 if q <= .25 else 1 if q <= .5 else 2 if q <= .75 else 3

def render(cells, t):
    mx = max([c["n"] for c in cells] + [1])
    total = len(cells)
    dur = total * SPEED
    width = PAD * 2 + WEEKS * STEP
    height = TOP + 7 * STEP + PAD + 10
    cx = lambda c: PAD + c["w"] * STEP + CELL / 2
    cy = lambda c: TOP + c["r"] * STEP + CELL / 2
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
         f'<rect width="100%" height="100%" rx="12" fill="{t["bg"]}"/>',
         f'<text x="{PAD}" y="22" font-family="monospace" font-size="12" fill="{t["text"]}">'
         f'LeetCode submissions · {sum(c["n"] for c in cells)} in the last year</text>']
    for i, c in enumerate(cells):
        lv = level(c["n"], mx)
        x, y = cx(c) - CELL / 2, cy(c) - CELL / 2
        if lv < 0:
            o.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{t["empty"]}"/>')
        else:
            col = t["levels"][lv]
            kt = min(i / total, 0.97)
            o.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{col}">'
                     f'<animate attributeName="fill" dur="{dur:.2f}s" repeatCount="indefinite" '
                     f'calcMode="discrete" values="{col};{t["empty"]};{col}" keyTimes="0;{kt:.4f};0.985"/></rect>')
    path = "M" + " L".join(f"{cx(c):.1f} {cy(c):.1f}" for c in cells)
    for k in range(SNAKE_LEN, -1, -1):             # tail first so head draws on top
        size = CELL - (0 if k == 0 else 1)
        fill = t["head"] if k == 0 else t["body"]
        begin = k * SPEED * 1.6
        o.append(f'<rect x="{-size/2}" y="{-size/2}" width="{size}" height="{size}" rx="3" fill="{fill}" opacity="0">'
                 f'<set attributeName="opacity" to="{1 if k == 0 else 1 - k*0.08:.2f}" begin="{begin:.2f}s" fill="freeze"/>'
                 f'<animateMotion dur="{dur:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite" path="{path}"/></rect>')
    o.append("</svg>")
    return "\n".join(o)

if __name__ == "__main__":
    cells = build_cells(fetch_calendar())
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, theme in THEMES.items():
        open(os.path.join(OUT_DIR, name), "w").write(render(cells, theme))
        print("wrote", os.path.join(OUT_DIR, name))
