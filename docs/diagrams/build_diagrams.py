"""Build the SVG diagrams in this folder, and docs/WHAT-AI-GAINS.md, from threads/threads.json.

    python docs/diagrams/build_diagrams.py          # write the files
    python docs/diagrams/build_diagrams.py --check  # fail if any file is out of date

Standard library only. Every diagram that lists lessons reads them from the threads, so a
change to the data changes the pictures. Each SVG paints its own light background, so it reads
the same on a light or a dark page. This script is Apache-2.0; its outputs are CC-BY-SA-4.0.
"""

from __future__ import annotations

import io
import json
import os
import sys
from typing import Dict, List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
THREADS = os.path.join(ROOT, "threads", "threads.json")

FONT = "Helvetica, Arial, sans-serif"
INK, MUTED, LINE, PAPER = "#1f2328", "#57606a", "#8c959f", "#ffffff"
BLUE_FILL, BLUE = "#eaf1fd", "#3567c8"
ORANGE_FILL, ORANGE = "#fff3df", "#b86e00"
DARK = "#24292f"
RED, RED_FILL = "#b42318", "#fdecea"
GREEN, GREEN_FILL = "#1a7f37", "#e8f5ec"
AMBER, AMBER_FILL = "#9a6700", "#fff8e1"
VIOLET, VIOLET_FILL = "#6639ba", "#f3eefc"
GREY_FILL = "#f6f8fa"
MARKS = {MUTED: "a-muted", RED: "a-red", GREEN: "a-green", AMBER: "a-amber", BLUE: "a-blue",
         ORANGE: "a-orange", VIOLET: "a-violet"}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def text_width(s: str, size: float, bold: bool = False) -> float:
    return len(s) * size * (0.58 if bold else 0.52)


def wrap(s: str, size: float, width: float, bold: bool = False) -> List[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if cur and text_width(trial, size, bold) > width:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines or [""]


class SVG(object):
    def __init__(self, w: int, h: int, title: str, desc: str):
        self.w, self.h, self.title, self.desc = w, h, title, desc
        self.parts: List[str] = []

    def rect(self, x, y, w, h, fill=GREY_FILL, stroke=LINE, rx=6, sw=1.2, dash: Optional[str] = None):
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        self.parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%d" fill="%s" stroke="%s" '
                          'stroke-width="%.1f"%s/>' % (x, y, w, h, rx, fill, stroke, sw, d))

    def text(self, x, y, s, size=13, fill=INK, bold=False, anchor="start"):
        extra = ' font-weight="700"' if bold else ""
        self.parts.append('<text x="%.1f" y="%.1f" font-size="%.1f" fill="%s" text-anchor="%s"%s>%s</text>'
                          % (x, y, size, fill, anchor, extra, esc(s)))

    def lines(self, x, y, lines: Sequence[str], size=13, fill=INK, bold=False, anchor="start", lead=1.3):
        for i, ln in enumerate(lines):
            self.text(x, y + i * size * lead, ln, size, fill, bold, anchor)
        return y + len(lines) * size * lead

    def para(self, x, y, s, width, size=13, fill=INK, bold=False, anchor="start", lead=1.3):
        return self.lines(x, y, wrap(s, size, width, bold), size, fill, bold, anchor, lead)

    def arrow(self, x1, y1, x2, y2, color=MUTED, sw=1.6, dash: Optional[str] = None, label: str = "",
              lx=None, ly=None, lsize=11.5):
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        self.parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f"%s '
                          'marker-end="url(#%s)"/>' % (x1, y1, x2, y2, color, sw, d, MARKS[color]))
        if label:
            self.text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2 - 6,
                      label, lsize, color, anchor="middle")

    def path(self, d, color=MUTED, sw=1.6, dash: Optional[str] = None, arrow=True):
        dd = ' stroke-dasharray="%s"' % dash if dash else ""
        self.parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="%.1f"%s%s/>'
                          % (d, color, sw, dd, ' marker-end="url(#%s)"' % MARKS[color] if arrow else ""))

    def box(self, x, y, w, h, head, body="", fill=GREY_FILL, stroke=LINE, size=13, head_fill=INK, dash=None,
            body_fill=MUTED, body_size=None):
        self.rect(x, y, w, h, fill, stroke, dash=dash)
        yy = self.para(x + 12, y + 22, head, w - 24, size, head_fill, bold=True)
        if body:
            self.para(x + 12, yy + 2, body, w - 24, body_size or size - 1.5, body_fill)

    def render(self) -> str:
        marks = []
        for color, name in MARKS.items():
            marks.append('<marker id="%s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                         'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="%s"/></marker>' % (name, color))
        head = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
                'font-family="%s" role="img" aria-labelledby="t d">\n<title id="t">%s</title>\n<desc id="d">%s</desc>\n'
                '<defs>%s</defs>\n<rect x="0" y="0" width="%d" height="%d" fill="%s"/>\n'
                % (self.w, self.h, self.w, self.h, FONT, esc(self.title), esc(self.desc), "".join(marks),
                   self.w, self.h, PAPER))
        return head + "\n".join(self.parts) + "\n</svg>\n"


def load() -> Dict:
    with io.open(THREADS, encoding="utf-8") as fh:
        return json.load(fh)


def ascii_name(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s) if ord(c) < 128)


def header(svg: SVG, title: str, sub: str):
    svg.text(28, 40, title, 22, INK, bold=True)
    svg.para(28, 64, sub, svg.w - 56, 13.5, MUTED)


def chip_style(lesson):
    return (ORANGE_FILL, ORANGE) if lesson["derivation"] == "derived" else (BLUE_FILL, BLUE)


def chips(svg: SVG, x, y, width, lessons, size=12.0, show_ctx=True) -> float:
    cx, cy, row_h = x, y, 28
    for l in lessons:
        name = ascii_name(l["name"])
        w = text_width("%s  %s" % (l["id"], name), size) + 30
        if cx + w > x + width and cx > x:
            cx, cy = x, cy + row_h + 6
        fill, stroke = chip_style(l)
        svg.rect(cx, cy, w, row_h, fill, stroke, rx=14)
        svg.text(cx + 11, cy + 18.5, l["id"], size, stroke, bold=True)
        svg.text(cx + 13 + text_width(l["id"], size, True) + 4, cy + 18.5, name, size, INK)
        if show_ctx and "context" in l["enforcement_layers"]:
            svg.parts.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (cx + w - 10, cy + 14, GREEN))
        cx += w + 8
    return cy + row_h


def legend(svg: SVG, x, y, ctx=True):
    svg.rect(x, y, 26, 18, BLUE_FILL, BLUE, rx=9)
    svg.text(x + 34, y + 14, "the book states the rule for AI", 12, MUTED)
    svg.rect(x + 250, y, 26, 18, ORANGE_FILL, ORANGE, rx=9)
    svg.text(x + 284, y + 14, "this lab derived the rule from the chapter's argument", 12, MUTED)
    if ctx:
        svg.parts.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (x + 13, y + 36, GREEN))
        svg.text(x + 34, y + 40, "can also be carried in context (a prompt); the rest need code, architecture or people", 12, MUTED)


# ---------------------------------------------------------------- 1. the map
def d_map(t) -> SVG:
    order = ["P", "F", "A", "D", "K", "S", "R", "M"]
    W, chip_x, chip_w = 1200, 300, 860
    heights = []
    for s in order:
        tmp = SVG(10, 10, "", "")
        heights.append(max(70, chips(tmp, chip_x, 0, chip_w, [l for l in t["lessons"] if l["strand"] == s]) + 24))
    H = 120 + sum(heights) + 4 * len(order) + 70
    svg = SVG(W, H, "The threads: fifty-eight lessons in eight strands",
              "The book's method at the bottom, then the strands that follow its parts: reality and explanation, self "
              "and cognition, cooperation and political economy, discourse and morals, artificial intelligence, the four "
              "moves and institutions, and practice.")
    header(svg, "The threads: fifty-eight lessons in eight strands",
           "Read from the bottom. The method strand is what every other lesson assumes: mark the standing of a claim, count "
           "agreement only across independent routes, agree on shape and keep content plural, keep open what is open.")
    y = 120
    for s, h in zip(order, heights):
        meta = t["strands"][s]
        is_method = s == "M"
        svg.rect(28, y, W - 56, h - 6, DARK if is_method else GREY_FILL, DARK if is_method else LINE)
        yy = svg.lines(44, y + 26, wrap("%s  %s" % (s, meta["title"]), 15, 240, True), 15, PAPER if is_method else INK, bold=True)
        chaps = sorted({c for l in t["lessons"] if l["strand"] == s for c in l["chapters"]})
        svg.para(44, yy + 2, "chapters " + ", ".join(str(c) for c in chaps), 240, 11.5, "#d0d7de" if is_method else MUTED)
        chips(svg, chip_x, y + 12, chip_w, [l for l in t["lessons"] if l["strand"] == s])
        y += h + 4
    legend(svg, 28, H - 54)
    return svg


# ---------------------------------------------------------------- 2. the register
def d_register(t) -> SVG:
    W, H = 1200, 640
    svg = SVG(W, H, "The epistemic register",
              "Six standings a claim can have, from settled to method note, each with the wording it may be asserted in, "
              "and how the answer governor holds wording to standing.")
    header(svg, "How much weight can this claim bear? The six registers (M1)",
           "The book opens many paragraphs with a glyph that records the standing of its claim. The threads make that a field "
           "on every claim; the wording must fit it.")
    styles = {"settled": (GREEN_FILL, GREEN), "established": (BLUE_FILL, BLUE), "contested": (AMBER_FILL, AMBER),
              "limit": (RED_FILL, RED), "bridge": (VIOLET_FILL, VIOLET), "method": (GREY_FILL, LINE)}
    examples = {"settled": "Water boils at 100 C at sea level.",
                "established": "Within structural causal models, rung-2 claims need a graph.",
                "contested": "Compatibilists hold that free will survives determinism; hard incompatibilists deny it.",
                "limit": "No randomised trial long enough to settle this exists.",
                "bridge": "On this view, relation comes before substance.",
                "method": "This overview draws mainly on English-language sources."}
    w, h, gx, gy = 362, 190, 28, 112
    for i, r in enumerate(t["registers"]):
        x = gx + (i % 3) * (w + 15)
        y = gy + (i // 3) * (h + 16)
        fill, stroke = styles[r["id"]]
        svg.rect(x, y, w, h, fill, stroke)
        svg.text(x + 16, y + 30, r["ascii"], 17, stroke, bold=True)
        svg.para(x + 16, y + 54, r["name"], w - 32, 12.5, INK, bold=True)
        yy = svg.para(x + 16, y + 92, "Assert as: " + r["assert_as"], w - 32, 12, MUTED)
        svg.para(x + 16, max(yy + 6, y + 140), '"' + examples[r["id"]] + '"', w - 32, 12, INK)
    y = gy + 2 * (h + 16) + 8
    svg.rect(28, y, W - 56, 86, RED_FILL, RED)
    svg.text(44, y + 26, "What the governor refuses", 14, RED, bold=True)
    svg.para(44, y + 48, "proof language (proves, certainly, beyond doubt) on a contested, bridge, limit or method claim (REG-001); "
             "a settled claim resting on an own thesis (REG-002) or on a convergence graded only partial (REG-003); a self-report "
             "asserted as fact with no outside check (REG-006); a foundational claim asserted as settled (REG-009).", W - 100, 12.5, INK)
    return svg


# ---------------------------------------------------------------- 3. independent routes
def d_routes(t) -> SVG:
    W, H = 1200, 820
    svg = SVG(W, H, "Independent routes as evidence",
              "Orthogonality-as-evidence: routes are recorded with their methods; routes joined by a shared upstream source "
              "collapse into one witness; the number of independent witnesses sets the ceiling on the grade.")
    header(svg, "Counting agreement: independent routes as evidence (M2, CV1-CV12)",
           "Agreement raises confidence in a shared shape only to the extent that the routes could not have passed doctrine to "
           "one another. Correlated routes count as one witness.")
    routes = [("Relational physics", "method: mathematical physics", "problem: measurement"),
              ("Madhyamaka", "method: dialectical refutation", "problem: suffering"),
              ("Systems biology", "method: biological modelling", "problem: what is alive"),
              ("Process metaphysics", "method: speculative metaphysics", "problem: bifurcation of nature")]
    bx, by, bw, bh = 40, 130, 250, 96
    for i, (n, m, p) in enumerate(routes):
        y = by + i * 120
        svg.box(bx, y, bw, bh, n, m + "; " + p, BLUE_FILL, BLUE)
    svg.path("M%.1f,%.1f C%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (bx + bw, by + 3 * 120 + 40, bx + bw + 70, by + 3 * 120 + 40,
                                                       bx + bw + 70, by + 40, bx + bw + 4, by + 40), RED, 1.8, dash="6 4")
    svg.para(bx + bw + 78, by + 190, "upstream link: the process philosopher had read the physicists", 170, 12, RED, bold=True)
    cx = 560
    svg.text(cx, 140, "Clusters after the links", 15, INK, bold=True)
    svg.rect(cx, 156, 280, 70, AMBER_FILL, AMBER)
    svg.para(cx + 14, 180, "Relational physics + process metaphysics: one witness", 252, 12.5, INK)
    svg.rect(cx, 238, 280, 46, GREEN_FILL, GREEN)
    svg.text(cx + 14, 266, "Madhyamaka: one witness", 12.5, INK)
    svg.rect(cx, 296, 280, 46, GREEN_FILL, GREEN)
    svg.text(cx + 14, 324, "Systems biology: one witness", 12.5, INK)
    svg.text(cx, 372, "= 3 independent routes", 16, GREEN, bold=True)
    svg.arrow(bx + bw + 180, 300, cx - 6, 260, MUTED, 1.4)
    gx = 900
    svg.text(gx, 140, "Grade ceiling", 15, INK, bold=True)
    grades = [("3 or more", "strong", GREEN_FILL, GREEN), ("2", "partial", AMBER_FILL, AMBER),
              ("1", "withdrawn", RED_FILL, RED), ("a selection", "author's thesis", VIOLET_FILL, VIOLET)]
    for i, (n, g, f, s) in enumerate(grades):
        y = 156 + i * 58
        svg.rect(gx, y, 260, 48, f, s)
        svg.text(gx + 14, y + 20, n, 12, MUTED)
        svg.text(gx + 14, y + 38, g, 14, s, bold=True)
    svg.rect(40, 610, 1120, 196, GREY_FILL, LINE)
    svg.text(56, 636, "What counts as a shared upstream source", 14, INK, bold=True)
    kinds = ["a shared translation vocabulary", "a shared lineage or scripture", "a comparative project that shaped both",
             "active dialogue between the routes", "a shared forum or debate", "the synthesist's own frame",
             "direct influence", "a citation artefact (dropped, not counted)"]
    for i, k in enumerate(kinds):
        x = 56 + (i % 2) * 540
        y = 664 + (i // 2) * 24
        svg.text(x, y, "- " + k, 12.5, INK)
    svg.para(56, 664 + 4 * 24 + 8, "Routes that share a method, a validation procedure or a cosmology are also counted as one. "
             "The computed grade is a ceiling; a declared grade above it is a finding (CON-001).", 1090, 12, MUTED)
    return svg


# ---------------------------------------------------------------- 4. shape not content
def d_shape(t) -> SVG:
    W, H = 1200, 640
    svg = SVG(W, H, "Shape, not content",
              "The anti-Capra discipline: a convergence claims only a shared shape; each tradition keeps its own content and "
              "vocabulary; flattening the contents into one gloss withdraws the claim.")
    header(svg, "Agree on shape, keep content plural: the anti-Capra discipline (M3, D5)",
           "The agreement carries weight because the contents cannot be reduced to one another. Flatten them and the agreement "
           "has been written into the translation.")
    svg.rect(430, 250, 340, 110, DARK, DARK)
    svg.text(600, 290, "Shared shape", 16, PAPER, bold=True, anchor="middle")
    svg.para(450, 316, "relation comes before substance", 300, 13.5, "#d0d7de", anchor="start")
    routes = [(60, 120, "Relational quantum mechanics", "properties exist only relative to interacting systems; says nothing about liberation"),
              (820, 120, "Madhyamaka", "phenomena are empty of inherent existence; a path out of suffering, not a physical theory"),
              (60, 400, "Hua-yen Indra's Net", "phenomena interpenetrate without obstruction; a Tang synthesis, not generic connectedness"),
              (820, 400, "Anishinaabe kinship", "the river is a relative within a moral community grounded in place")]
    for x, y, n, c in routes:
        svg.box(x, y, 320, 110, n, c, BLUE_FILL, BLUE)
    svg.arrow(380, 175, 480, 252, BLUE, 1.4)
    svg.arrow(820, 175, 720, 252, BLUE, 1.4)
    svg.arrow(380, 455, 480, 358, BLUE, 1.4)
    svg.arrow(820, 455, 720, 358, BLUE, 1.4)
    svg.text(600, 210, "each route arrives by its own method", 12, BLUE, anchor="middle")
    svg.text(600, 400, "the contents stay where they are", 12, BLUE, anchor="middle")
    svg.rect(60, 548, 1080, 70, RED_FILL, RED, dash="6 4")
    svg.text(76, 572, "Flattened (withdrawn): \"physics and mysticism are the same: all is one\"", 13.5, RED, bold=True)
    svg.para(76, 594, "identity phrasing (CON-003) and duplicated content (CON-002) withdraw the claim until each route's own content is restored.",
             1040, 12, INK)
    return svg


# ---------------------------------------------------------------- 5. causal ladder
def d_ladder(t) -> SVG:
    W, H = 1200, 650
    svg = SVG(W, H, "The ladder of causation",
              "Three rungs of causal claim: association, intervention, counterfactual, with what licenses each and the "
              "characteristic AI failure at each.")
    header(svg, "Climbing the causal ladder only with declared structure (R4, CV10)",
           "Data alone cannot deliver a cause; structural assumptions can. Most machine learning lives on the first rung, so its "
           "recommendations are correlations unless assumptions license them.")
    rungs = [
        (3, "Imagining: had X not happened, would Y?", "P(y_x | x', y')", "a structural causal model plus the assumptions behind it",
         "explaining a decision as if one cause at one scale settled it", VIOLET_FILL, VIOLET),
        (2, "Doing: what happens to Y if we set X?", "P(Y | do(X))", "explicit causal assumptions (a graph) or an experiment",
         "a correlation dressed as a recommendation: 'people who do X live longer, so do X'", BLUE_FILL, BLUE),
        (1, "Seeing: does X go with Y?", "P(Y | X)", "data", "fine, as long as it is labelled as association", GREEN_FILL, GREEN),
    ]
    for i, (n, q, f, lic, fail, fill, stroke) in enumerate(rungs):
        y = 118 + i * 150
        x = 60 + i * 40
        svg.rect(x, y, 700 - i * 40, 130, fill, stroke)
        svg.text(x + 18, y + 32, "Rung %d" % n, 18, stroke, bold=True)
        svg.text(x + 120, y + 32, q, 14, INK, bold=True)
        svg.text(x + 120, y + 56, f, 13, MUTED)
        svg.para(x + 120, y + 82, "Licensed by: " + lic, 540 - i * 40, 12.5, INK)
        svg.rect(800, y, 360, 130, RED_FILL, RED)
        svg.text(816, y + 28, "Failure at this rung", 12.5, RED, bold=True)
        svg.para(816, y + 50, fail, 330, 12.5, INK)
    svg.rect(60, 572, 1100, 56, GREY_FILL, LINE)
    svg.para(76, 594, "The governor reads each claim's rung, declared or from its phrasing: rung 2 without assumptions (CAU-001), rung 3 "
             "without a model (CAU-002), a rung-1 tag on interventional wording (CAU-003), a non-identifiable effect asserted (CAU-005).",
             1070, 11.5, MUTED)
    return svg


# ---------------------------------------------------------------- 6. four moves
def d_moves(t) -> SVG:
    W, H = 1200, 700
    svg = SVG(W, H, "The four-move framework",
              "Two truths, action without attachment, Indra's Net and political economy, each from its own tradition and mapped to "
              "a pressure, held together; any one alone fails in a characteristic way.")
    header(svg, "The four moves, held together (F1-F5; the author's own thesis, CV9)",
           "Habits of thought to inhabit, not a checklist. Each is grounded in a separate tradition and can be used without its "
           "metaphysics; the claim is about integration.")
    moves = t["frameworks"]["four_moves"]
    pos = [(60, 120), (640, 120), (640, 400), (60, 400)]
    for (x, y), m in zip(pos, moves):
        svg.rect(x, y, 500, 200, VIOLET_FILL, VIOLET)
        svg.text(x + 18, y + 32, ascii_name(m["name"]), 18, VIOLET, bold=True)
        svg.para(x + 18, y + 58, "From: " + ascii_name(m["source"]), 464, 12, MUTED)
        svg.para(x + 18, y + 108, ascii_name(m["stance"]), 464, 13, INK)
        svg.text(x + 18, y + 184, "answers the pressure of " + m["pressure"], 12, VIOLET)
    svg.rect(470, 315, 260, 80, DARK, DARK)
    svg.text(600, 348, "one stance", 15, PAPER, bold=True, anchor="middle")
    svg.text(600, 372, "inhabited, not scored", 12.5, "#d0d7de", anchor="middle")
    svg.rect(60, 616, 1080, 70, RED_FILL, RED)
    svg.text(76, 640, "Each move alone fails", 13.5, RED, bold=True)
    fails = t["frameworks"]["integration_failures"]
    svg.para(76, 662, "; ".join(ascii_name(f) for f in fails) + ".", 1040, 11.5, INK)
    return svg


# ---------------------------------------------------------------- 7. governed answer
def d_governed(t) -> SVG:
    W, H = 1200, 700
    svg = SVG(W, H, "The governed answer",
              "How threadkit's AnswerGovernor sits between a model and a user: the model drafts a structured answer; the governor "
              "checks it against the answer-level lessons; only a healthy record is rendered, with each claim's standing visible.")
    header(svg, "The governed answer: the lessons around any model",
           "The model drafts; the governor checks; findings go back as revision notes; only a healthy record reaches the user, and "
           "it reaches them with its standings showing.")
    svg.box(40, 120, 230, 110, "Model drafts an answer record", "mode, claims with standing and rung, deliberation, disagreements, moral block",
            GREY_FILL, LINE)
    steps = [("Schema", "the answer contract (GOV-000)"), ("Claim register", "standing vs wording, basis, sources (REG)"),
             ("Causal ladder", "rung and assumptions (CAU)"), ("Deliberation", "checked only if a check ran (GOV-001, GOV-004)"),
             ("Self-status", "no flat claim about own consciousness (GOV-003)"), ("Mode", "inquiry or advocacy; purpose (ARG)"),
             ("Moral pluralism", "C1-C7 firm; D1-D5 plural, no default (MOR)"), ("Disagreements", "presented, never settled by fiat (DIS)")]
    x0, y0, w, h = 330, 120, 200, 76
    for i, (a, b) in enumerate(steps):
        x = x0 + (i % 4) * (w + 14)
        y = y0 + (i // 4) * (h + 40)
        svg.box(x, y, w, h, a, b, BLUE_FILL, BLUE, size=12.5)
        if i % 4 < 3:
            svg.arrow(x + w, y + h / 2, x + w + 12, y + h / 2, MUTED, 1.2)
    svg.arrow(270, 175, 326, 158, MUTED, 1.4)
    svg.path("M%.1f,%.1f L%.1f,%.1f L%.1f,%.1f" % (x0 + 3 * (w + 14) + w / 2, y0 + h, x0 + 3 * (w + 14) + w / 2, y0 + h + 20,
                                               x0 + w / 2, y0 + h + 20), MUTED, 1.2, arrow=False)
    svg.arrow(x0 + w / 2, y0 + h + 20, x0 + w / 2, y0 + h + 36, MUTED, 1.2)
    vy = 380
    svg.box(330, vy, 300, 96, "Healthy", "render with each claim's standing ([settled], [contested]...), open questions, attributed moral positions, coverage",
            GREEN_FILL, GREEN)
    svg.box(660, vy, 300, 96, "Needs attention or unhealthy", "findings, each naming its lesson, go back to the model as revision notes",
            AMBER_FILL, AMBER)
    svg.arrow(600, y0 + 2 * (h + 40) - 30, 480, vy - 4, GREEN, 1.6)
    svg.arrow(650, y0 + 2 * (h + 40) - 30, 810, vy - 4, AMBER, 1.6)
    svg.path("M%.1f,%.1f L%.1f,%.1f L%.1f,%.1f L%.1f,%.1f L%.1f,%.1f" % (660, vy + 70, 645, vy + 70, 645, 606, 155, 606, 155, 234), AMBER, 1.6, dash="6 4")
    svg.text(170, 598, "revise: findings go back to the model (bounded rounds)", 12, AMBER, bold=True)
    svg.box(660, vy + 120, 300, 70, "Still unhealthy after N rounds", "not shown to the user as if it were fine", RED_FILL, RED)
    svg.arrow(810, vy + 96, 810, vy + 116, RED, 1.4)
    svg.rect(40, 626, 1120, 60, GREY_FILL, LINE)
    svg.para(56, 650, "The governor reads structure, not minds: a model can mislabel consistently. Pair it with an independent critic (R3) "
             "and keep the architecture-level lessons (shared medium, diversity, freedoms) where they belong.", 1090, 12, MUTED)
    return svg


# ---------------------------------------------------------------- 8. cooperation
def d_cooperation(t) -> SVG:
    W, H = 1200, 700
    svg = SVG(W, H, "Cooperation's infrastructure",
              "The three layers cooperation runs on, the eight capacities an AI deployment can support or erode, the reciprocity "
              "policy for agents, and the freedoms a deployment must keep.")
    header(svg, "What a deployment touches: cooperation's infrastructure (K1-K8, D7, A10)",
           "Judge a deployment less by whether its output is correct than by whether it strengthens or erodes what people need "
           "to cooperate, and whether they can still leave, contest and reshape it.")
    layers = [("narrative", "shared stories that motivate taking part"), ("institutional", "rules with legitimacy, enforcement, competence and responsiveness"),
              ("cognitive", "shared concepts, standards and reference points")]
    for i, (n, d) in enumerate(layers):
        y = 120 + i * 78
        svg.rect(40, y, 520, 68, BLUE_FILL, BLUE)
        svg.text(58, y + 28, n + " layer", 15, BLUE, bold=True)
        svg.para(58, y + 50, d, 480, 12.5, INK)
    svg.text(600, 136, "The eight capacities (D7)", 15, INK, bold=True)
    for i, c in enumerate(t["frameworks"]["eight_capacities"]):
        x = 600 + (i % 2) * 280
        y = 150 + (i // 2) * 44
        svg.rect(x, y, 266, 36, GREEN_FILL, GREEN, rx=18)
        svg.text(x + 16, y + 23, c, 12.5, INK)
    svg.text(40, 390, "A legible reciprocity policy for agents (K1)", 15, INK, bold=True)
    props = [("nice", "cooperate on first contact"), ("forgiving", "restore trust after one response"),
             ("provokable", "answer every violation"), ("clear", "publish the policy; log violations")]
    for i, (n, d) in enumerate(props):
        x = 40 + i * 280
        svg.box(x, 404, 266, 76, n, d, AMBER_FILL, AMBER)
    svg.text(40, 520, "The three freedoms (A10)", 15, INK, bold=True)
    for i, f in enumerate(t["frameworks"]["three_freedoms"]):
        x = 40 + i * 374
        svg.box(x, 534, 360, 90, f["name"], f["for_ai"], VIOLET_FILL, VIOLET)
    svg.para(40, 660, "threadkit review scores each section (supports / neutral / erodes / unknown) and flags erosion, closed freedoms, "
             "unaudited shared media and an empty political economy. A review is a prompt for judgement, never a score.", 1120, 12, MUTED)
    return svg


# ---------------------------------------------------------------- 9. gains
GAINS = [
    ("Every sentence in one confident register", "M1", "each claim's standing is visible; proof language is refused on contested claims"),
    ("Many sources repeating one, counted as consensus", "M2, A5", "agreement is counted by independent routes; copies of one model are one witness"),
    ("'All traditions teach the same thing'", "M3, D5", "the shared shape is stated and each tradition keeps its own terms and content"),
    ("Live disputes settled by fiat or averaged away", "M4", "both sides are attributed and held open; closing one needs new evidence"),
    ("Correlations dressed as recommendations", "R4", "the rung is labelled; interventional claims declare their assumptions; non-identifiable effects are reported as such"),
    ("Fluent explanations that would fit anything", "R2, R3", "explanations commit to counterfactuals; unverified output is treated as conjecture"),
    ("'I checked' with no check behind it", "S3, S1", "the checked label requires a recorded check; self-reports are verified from outside"),
    ("Inquiry in form, persuasion in purpose", "D1, K4", "the mode is declared and a persuasive purpose is disclosed"),
    ("Evasion in dialogue", "D2, D3", "unanswered questions, repetition, quiet thesis shifts and refutation without a position are flagged"),
    ("One culture's moral answer as the default", "D4, D6", "convergent ground is held firmly; foundational questions get attributed, plural answers and no default"),
    ("Sycophancy learned from approval", "S5, F2", "process is rewarded over approval; bad news is reported as readily as good"),
    ("Swarm groupthink and coordination nobody sees", "A4, A5", "writes to the shared medium are logged; consensus is weighted by lineage"),
    ("Forecasts of destiny; risk read off a vivid story", "K6, A6", "windows and scopes, not dates; frame, record and probability kept apart"),
    ("Flat claims about its own consciousness", "A8, S2", "the question is held open while precaution proceeds in practice"),
    ("Deployments that erode the people using them", "D7, K5, A10", "capacities, infrastructure and freedoms are reviewed before shipping"),
]


def d_gains(t) -> SVG:
    ids = {l["id"] for l in t["lessons"]}
    for _, refs, _ in GAINS:
        for r in refs.split(", "):
            assert r in ids, r
    W, row_h = 1200, 54
    H = 150 + len(GAINS) * (row_h + 8) + 70
    svg = SVG(W, H, "What an AI system gains",
              "Fifteen failure modes of AI reasoning, the lessons that address each, and what changes when they are implemented.")
    header(svg, "What an AI system gains: failure mode, lesson, what changes",
           "Each gain is a bet with a test in threads.json, not a guarantee. If the test fails, the lesson is revised or retired (P2).")
    cx = [28, 470, 600]
    for x, label in zip(cx, ("Failure mode", "Lessons", "What changes")):
        svg.text(x, 128, label, 13, MUTED, bold=True)
    y = 140
    for fail, refs, gain in GAINS:
        svg.rect(cx[0], y, 420, row_h, RED_FILL, RED)
        svg.para(cx[0] + 12, y + 22, fail, 396, 13, INK, bold=True)
        svg.rect(cx[1], y + 10, 110, 34, BLUE_FILL, BLUE, rx=17)
        svg.text(cx[1] + 55, y + 32, refs, 12.5, BLUE, bold=True, anchor="middle")
        svg.arrow(cx[0] + 420, y + row_h / 2, cx[1] - 4, y + row_h / 2, MUTED, 1.2)
        svg.arrow(cx[1] + 110, y + row_h / 2, cx[2] - 4, y + row_h / 2, MUTED, 1.2)
        svg.rect(cx[2], y, 572, row_h, GREEN_FILL, GREEN)
        svg.para(cx[2] + 12, y + 22, gain, 548, 12.5, INK)
        y += row_h + 8
    svg.para(28, y + 26, "Read docs/WHAT-AI-GAINS.md for each lesson's test and caution, and docs/LESSONS.md for the full rule, rationale and sketch.",
             W - 56, 12.5, MUTED)
    return svg


# ---------------------------------------------------------------- 10. layers
def d_layers(t) -> SVG:
    rows = [("context", "a prompt or system instructions", "the model applies the rule in its own reasoning and wording"),
            ("middleware", "code around the model", "the governor, the assessor, the linter, the decision records"),
            ("architecture", "what channels, logs and agents exist", "shared-medium logs, diversity of agents, opt-out routes"),
            ("governance", "named people and records", "design reviews, consultation, institutional moves, tests and review dates")]
    W = 1200
    heights = []
    for layer, _, _ in rows:
        tmp = SVG(10, 10, "", "")
        heights.append(max(92, chips(tmp, 330, 0, 820, [l for l in t["lessons"] if layer in l["enforcement_layers"]], show_ctx=False) + 30))
    H = 130 + sum(heights) + 12 * 4 + 110
    ctx = [l for l in t["lessons"] if "context" in l["enforcement_layers"]]
    svg = SVG(W, H, "Where each lesson can be enforced",
              "Four enforcement layers from a prompt to governance, with the lessons each can carry.")
    header(svg, "A prompt is the shallowest layer: where each lesson can be enforced",
           "%d of %d lessons can be carried in context. The rest need code, architecture or people. A lesson may appear in more than "
           "one layer; this placement is the lab's engineering judgement." % (len(ctx), len(t["lessons"])))
    y = 120
    for (layer, what, how), h in zip(rows, heights):
        svg.rect(28, y, W - 56, h, GREY_FILL, LINE)
        svg.text(44, y + 28, layer, 16, INK, bold=True)
        svg.text(44, y + 48, what, 12.5, MUTED)
        svg.para(44, y + 66, how, 260, 11.5, MUTED)
        chips(svg, 330, y + 14, 820, [l for l in t["lessons"] if layer in l["enforcement_layers"]], show_ctx=False)
        y += h + 12
    svg.arrow(W - 14, 124, W - 14, y - 16, MUTED, 1.4)
    svg.rect(28, y + 4, W - 56, 56, AMBER_FILL, AMBER)
    svg.para(44, y + 28, "A model can be asked to mark its claims' standing; only middleware can check the marks, and only people can "
             "decide who is consulted. threadkit audit reports THR-003 when a lesson is claimed at a layer that cannot enforce it.",
             W - 100, 12.5, AMBER, bold=True)
    legend(svg, 28, H - 36, ctx=False)
    return svg


GAINS_INTRO = """# What an AI system gains

Each row below pairs a failure that AI systems show in their reasoning with the lessons that
address it and what changes when they are implemented at a layer that can enforce them. Every
gain is a **bet**: each lesson in `threads/threads.json` carries a test that would show it is
not working, quoted here with it. Adopt a lesson as a bet you can lose, and measure.

![What a system gains](diagrams/09-what-ai-gains.svg)

This page is generated from `threads/threads.json` by `docs/diagrams/build_diagrams.py`.
CC-BY-SA-4.0.
"""

GAINS_OUTRO = """
## What it costs

- **More words, sometimes.** Marked standings, attributed positions and stated assumptions make
  some answers longer. The register's own test (M1) asks whether readers calibrate better; if
  they do not, simplify.
- **Fewer confident answers.** A system held to its standings asserts less. That is the point,
  and users who wanted certainty will notice.
- **Structured output.** The governor, linter and assessor read records, not prose. A model has
  to emit the structure beside its text, and someone has to keep the schemas current.
- **People's time.** Design reviews, consultation and diversity attestations need named people.

## What it does not buy

- Wisdom, fairness or safety as a certified property. A healthy check means a record is
  consistent with the lessons.
- An answer to whether any AI system is conscious or a moral patient. Several lessons exist to
  keep that question open.
- Protection at a layer a lesson does not reach. A prompt carries dispositions; the shared
  medium, diversity among agents and the freedoms need architecture and people.
"""


def gains_markdown(t) -> str:
    L = {l["id"]: l for l in t["lessons"]}
    out = [GAINS_INTRO]
    for i, (fail, refs, gain) in enumerate(GAINS, 1):
        out.append("\n## %d. %s\n" % (i, fail))
        out.append("**Lessons:** %s  " % ", ".join("%s %s" % (r, L[r]["name"]) for r in refs.split(", ")))
        out.append("**What changes:** %s%s.\n" % (gain[0].upper(), gain[1:]))
        for r in refs.split(", "):
            l = L[r]
            chs = l["chapters"]
            out.append("- **%s** (standing: %s; %s; chapter%s %s). Failure it addresses: %s" % (
                r, l["standing"], l["derivation"], "s" if len(chs) > 1 else "", ", ".join(str(c) for c in chs), l["failure_mode"]))
            out.append("  - Example: %s" % l["example"])
            out.append("  - Test: %s" % l["test"])
            if l["cautions"]:
                out.append("  - Caution: %s" % l["cautions"])
        out.append("")
    out.append(GAINS_OUTRO)
    text = "\n".join(out).replace("\n\n\n", "\n\n")
    return text.rstrip("\n") + "\n"


DIAGRAMS = [
    ("01-the-threads.svg", d_map),
    ("02-epistemic-register.svg", d_register),
    ("03-independent-routes.svg", d_routes),
    ("04-shape-not-content.svg", d_shape),
    ("05-causal-ladder.svg", d_ladder),
    ("06-four-moves.svg", d_moves),
    ("07-governed-answer.svg", d_governed),
    ("08-cooperation-infrastructure.svg", d_cooperation),
    ("09-what-ai-gains.svg", d_gains),
    ("10-enforcement-layers.svg", d_layers),
]


def build() -> Dict[str, str]:
    """Every generated file, keyed by its path relative to this folder."""
    t = load()
    out = {name: fn(t).render() for name, fn in DIAGRAMS}
    out[os.path.join("..", "WHAT-AI-GAINS.md")] = gains_markdown(t)
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = build()
    stale = []
    for name, body in out.items():
        assert name.endswith(".md") or all(ord(ch) < 128 for ch in body), name
        path = os.path.join(HERE, name)
        if "--check" in argv:
            try:
                with io.open(path, encoding="utf-8") as fh:
                    if fh.read().replace("\r\n", "\n") != body:
                        stale.append(name)
            except OSError:
                stale.append(name)
        else:
            with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(body)
    if stale:
        sys.stderr.write("out of date: %s\nrun: python docs/diagrams/build_diagrams.py\n" % ", ".join(stale))
        return 1
    sys.stderr.write("%s %d file(s)\n" % ("checked" if "--check" in argv else "wrote", len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
