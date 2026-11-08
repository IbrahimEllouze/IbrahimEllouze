#!/usr/bin/env python3
"""Generate the animated SVGs used by README.md.

    pip install fonttools
    python tools/build.py

Edit the CONTENT section below, then re-run. Fonts (OFL, from github.com/google/fonts)
are downloaded once into .cache/fonts and embedded as subsetted WOFF, so the SVGs render
with the right typefaces inside GitHub's <img> sandbox.
"""
import base64
import html
import io
import math
import pathlib
import random
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
CACHE = ROOT / ".cache" / "fonts"

# ============================== CONTENT ==============================

NAME = "Ibrahim Ellouze"
TYPED = [
    "DevOps & Cloud Engineer",
    "I run the cloud behind SDRCloud",
    "I ship backend, frontend and AI",
    "280+ pull requests merged",
]
PRS = "280+ pull requests merged"

# (title, light colour, dark colour, light text colour, stack, description, icon path in a 50x50 box)
DISCIPLINES = [
    ("Cloud & Infrastructure", "#7C3AED", "#A78BFA", "#6D28D9", ["GCP", "Terraform", "Cloudflare"],
     "The whole GCP estate as Terraform across dev, staging and prod, with daily drift detection. "
     "Led a zero-downtime move to a new GCP organization. White-label customer domains on Cloudflare for SaaS.",
     "M14 34 a10 10 0 0 1 2-19.8 a13 13 0 0 1 25 3.8 a8 8 0 0 1 -1 16 Z"),
    ("DevSecOps", "#2563EB", "#60A5FA", "#1D4ED8", ["GitHub Actions", "Docker", "Semgrep", "ZAP"],
     "Per-service pipelines, release candidates with smoke tests and one-step rollback, a preview "
     "environment per pull request. Semgrep, Trivy, TruffleHog and ZAP in CI; SOC 2 Type II readiness.",
     "M25 6 L41 12 V24 C41 34 34 40 25 44 C16 40 9 34 9 24 V12 Z M18 25 l5 5 l10 -11"),
    ("Observability & FinOps", "#0891B2", "#22D3EE", "#0E7490", ["GCP Monitoring", "BigQuery", "PostHog"],
     "Alerting, latency dashboards and on-call routing. Per-provider cost tracking in BigQuery, "
     "reconciling modelled AI spend against the cloud invoice, cost centres mapped to credit pricing.",
     "M6 28 H14 L19 14 L27 38 L32 22 L36 28 H44"),
    ("Backend", "#059669", "#34D399", "#047857", ["Convex", "TypeScript", "Python", "FastAPI"],
     "Correctness where money and email are on the line: idempotent sends, credit-ledger conflict fixes, "
     "capacity-aware scheduling. A Python video engine that renders scenes in parallel and survives crashes.",
     "M10 10 H40 V20 H10 Z M10 26 H40 V36 H10 Z M16 15 h2 M16 31 h2"),
    ("Frontend", "#DB2777", "#F472B6", "#BE185D", ["Next.js", "React", "Tailwind"],
     "Cost-centre and AI-spend dashboards, server-rendered public microsite pages with no layout shift, "
     "and per-route error containment reported to PostHog.",
     "M7 10 H43 V40 H7 Z M7 17 H43 M17 17 V40"),
    ("AI engineering", "#D97706", "#FBBF24", "#B45309", ["Gemini", "Vertex AI", "Langfuse", "AI SDK"],
     "An offline eval harness for the autonomous decider agent: golden scenarios, LLM-as-judge, prompt "
     "versioning and a CI gate that blocks regressions. LLM tracing on Langfuse.",
     "M25 6 L29 20 L43 25 L29 30 L25 44 L21 30 L7 25 L21 20 Z"),
]

LOOP_CENTER = ("AI-native SDLC", "self-checking agents · gated releases")
LOOP = [  # (stage, artifact, colour)
    ("Plan", "intent.md", "#0D9488"),
    ("Design", "spec.md", "#0891B2"),
    ("Build", "plan.md → code", "#2563EB"),
    ("Test", "evals gate CI", "#4F46E5"),
    ("Deploy", "review + approval", "#7C3AED"),
    ("Maintain", "monitors → intent", "#DB2777"),
]
INNER_LOOP = (3, "verify → fix → verify")

TOOLBOX = [  # (group, light colour, dark colour, light text colour, items)
    ("Cloud & infra", "#7C3AED", "#A78BFA", "#6D28D9",
     ["GCP", "Cloud Run", "Terraform", "Cloudflare", "Docker", "Kubernetes", "Helm", "Ansible", "AWS"]),
    ("Delivery & security", "#2563EB", "#60A5FA", "#1D4ED8",
     ["GitHub Actions", "Semgrep", "Trivy", "TruffleHog", "OWASP ZAP", "SOC 2"]),
    ("Software", "#059669", "#34D399", "#047857",
     ["TypeScript", "Next.js", "React", "Tailwind", "Convex", "Python", "FastAPI", "Playwright"]),
    ("AI & data", "#D97706", "#FBBF24", "#B45309",
     ["Vertex AI", "Gemini", "AI SDK", "Langfuse", "PostHog", "BigQuery"]),
]

PILLS = [
    ("email", "Email", "M3 6h18v12H3z M3 7l9 6 9-6"),
    ("linkedin", "LinkedIn", "M4 9h3v10H4z M5.5 4.5a1.6 1.6 0 1 1 0 3.2 1.6 1.6 0 0 1 0-3.2 M10 9h3v1.6c.5-1 1.7-1.8 3.3-1.8 "
                             "2.6 0 3.7 1.6 3.7 4.5V19h-3v-5.2c0-1.5-.5-2.3-1.7-2.3-1.3 0-2.3.9-2.3 2.6V19h-3z"),
    ("portfolio", "Portfolio", "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M3 12h18 M12 3c3 3 3 15 0 18 M12 3c-3 3-3 15 0 18"),
]
FOOTER_LINE = "Thanks for stopping by."

THEMES = {
    "light": dict(bg="#ffffff", fg="#1f2328", mut="#59636e", bd="#d1d9e0", tile="#f6f8fa"),
    "dark": dict(bg="#0d1117", fg="#f0f6fc", mut="#9198a1", bd="#3d444d", tile="#151b23"),
}

# ============================== FONTS ==============================

FONT_SRC = {
    "Sora": "ofl/sora/Sora%5Bwght%5D.ttf",
    "Geist": "ofl/geist/Geist%5Bwght%5D.ttf",
    "JetBrains Mono": "ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
}
_faces = {}


def face(family, weight):
    key = (family, weight)
    if key not in _faces:
        CACHE.mkdir(parents=True, exist_ok=True)
        path = CACHE / (family.replace(" ", "") + ".ttf")
        if not path.exists():
            url = "https://github.com/google/fonts/raw/main/" + FONT_SRC[family]
            print("downloading", url)
            path.write_bytes(urllib.request.urlopen(url).read())
        inst = instancer.instantiateVariableFont(TTFont(path), {"wght": weight})
        buf = io.BytesIO()
        inst.save(buf)
        font = TTFont(io.BytesIO(buf.getvalue()))
        _faces[key] = dict(bytes=buf.getvalue(), upm=font["head"].unitsPerEm,
                           cmap=font.getBestCmap(), hmtx=font["hmtx"].metrics)
    return _faces[key]


def text_width(s, family, weight, size, ls=0.0):
    f = face(family, weight)
    units = sum(f["hmtx"][f["cmap"].get(ord(c), ".notdef")][0] for c in s)
    return units * size / f["upm"] + ls * len(s)


def font_face_css(family, weight, chars):
    f = TTFont(io.BytesIO(face(family, weight)["bytes"]))
    opts = subset.Options()
    opts.flavor = "woff"
    opts.layout_features = ["kern", "liga", "calt"]
    opts.name_IDs = []
    opts.drop_tables += ["meta"]
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(chars)) + " ")
    sub.subset(f)
    buf = io.BytesIO()
    f.flavor = "woff"
    f.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return (f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:normal;"
            f"src:url(data:font/woff;base64,{b64}) format('woff')}}")


# ============================== SVG BUILDER ==============================

def esc(s):
    return html.escape(str(s), quote=True)


class Svg:
    def __init__(self, w, h, label):
        self.w, self.h, self.label = w, h, label
        self.parts, self.defs, self.css = [], [], []
        self.used = {}
        self._id = 0

    def uid(self, p):
        self._id += 1
        return f"{p}{self._id}"

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, family="Geist", weight=400, size=14, fill="#000", anchor="start", ls=0, extra=""):
        self.used.setdefault((family, weight), set()).update(s)
        lsa = f' letter-spacing="{ls}"' if ls else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-weight="{weight}" font-size="{size}" '
                f'fill="{fill}" text-anchor="{anchor}"{lsa} {extra}>{esc(s)}</text>')

    def wrap(self, x, y, s, maxw, lh, **kw):
        lines, cur = [], ""
        for word in s.split():
            trial = f"{cur} {word}".strip()
            if cur and text_width(trial, kw.get("family", "Geist"), kw.get("weight", 400), kw.get("size", 14)) > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        lines.append(cur)
        return [self.text(x, y + i * lh, ln, **kw) for i, ln in enumerate(lines)], len(lines)

    def render(self):
        faces = "".join(font_face_css(f, w, chars) for (f, w), chars in sorted(self.used.items()))
        base = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}" role="img" aria-label="{esc(self.label)}">'
                f"<title>{esc(self.label)}</title><style>{faces}{''.join(self.css)}{base}</style>"
                f"<defs>{''.join(self.defs)}</defs>{''.join(self.parts)}</svg>")


def keytimes(pairs):
    """pairs: [(t in 0..1, value)] -> (keyTimes, values) with first t=0 and last t=1."""
    pairs = sorted(pairs, key=lambda p: p[0])
    if pairs[0][0] > 0:
        pairs.insert(0, (0, pairs[0][1]))
    if pairs[-1][0] < 1:
        pairs.append((1, pairs[-1][1]))
    return ";".join(f"{t:.4f}" for t, _ in pairs), ";".join(str(v) for _, v in pairs)


BLOB_CSS = (
    "@keyframes d1{to{transform:translate(90px,40px) scale(1.15)}}"
    "@keyframes d2{to{transform:translate(-110px,50px) scale(.9)}}"
    "@keyframes d3{to{transform:translate(70px,-60px) scale(1.2)}}"
    "@keyframes d4{to{transform:translate(-60px,-30px) scale(1.1)}}"
    ".blob{transform-box:fill-box;transform-origin:center;animation:12s ease-in-out infinite alternate}"
    "@keyframes up{0%{transform:translateY(0);opacity:0}15%{opacity:.9}100%{transform:translateY(-340px);opacity:0}}"
)
LAGOON_BG = "#03161C"
LAGOON_PARTICLE = "#A7F3D0"


def lagoon_field(svg, w, h, blobs, particles, seed, py):
    blur = svg.uid("blur")
    svg.defs.append(f'<filter id="{blur}" x="-50%" y="-50%" width="200%" height="200%">'
                    f'<feGaussianBlur stdDeviation="{40 if h < 200 else 46}"/></filter>')
    svg.css.append(BLOB_CSS)
    out = [f'<rect width="{w}" height="{h}" fill="{LAGOON_BG}"/><g filter="url(#{blur})">']
    for i, (cx, cy, r, c) in enumerate(blobs):
        out.append(f'<circle class="blob" cx="{cx}" cy="{cy}" r="{r}" fill="{c}" '
                   f'style="animation-name:d{i % 4 + 1};animation-duration:{12 + 2 * i}s"/>')
    out.append(f'</g><g fill="{LAGOON_PARTICLE}">')
    rnd = random.Random(seed)
    for _ in range(particles):
        x, y = rnd.uniform(0, w), rnd.uniform(*py)
        sz = rnd.uniform(2, 4.5)
        out.append(f'<g transform="translate({x:.0f},{y:.0f})"><rect width="{sz:.1f}" height="{sz:.1f}" rx="1" '
                   f'style="animation:up {rnd.uniform(6, 13):.1f}s {-rnd.uniform(0, 12):.1f}s linear infinite"/></g>')
    out.append("</g>")
    return "".join(out)


def wave_path(y, flip=False, w=800, h=330):
    if not flip:
        a = f"M0 {y} C 160 {y-30} 300 {y+30} 420 {y+10} C 560 {y-14} 660 {y-30} 800 {y+2} V{h} H0 Z"
        b = f"M0 {y+10} C 140 {y+30} 290 {y-20} 430 {y-2} C 570 {y+16} 690 {y+22} 800 {y-8} V{h} H0 Z"
    else:
        a = f"M0 0 H800 V{y} C 640 {y+30} 520 {y-24} 400 {y-4} C 270 {y+18} 150 {y-20} 0 {y+4} Z"
        b = f"M0 0 H800 V{y-8} C 650 {y-26} 520 {y+20} 400 {y} C 280 {y-18} 140 {y+16} 0 {y-6} Z"
    return a, b


def wave(y, fill, opacity=1, flip=False, h=330):
    a, b = wave_path(y, flip, h=h)
    return (f'<path d="{a}" fill="{fill}" fill-opacity="{opacity}"><animate attributeName="d" dur="9s" '
            f'repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" keySplines=".45 0 .55 1;.45 0 .55 1" '
            f'values="{a};{b};{a}"/></path>')


def round_rect(w, h, r, top=True):
    """Clip path rounded only at the top (hero) or only at the bottom (footer), so the wave edge stays clean."""
    if top:
        return f"M0 {r} Q0 0 {r} 0 H{w - r} Q{w} 0 {w} {r} V{h} H0 Z"
    return f"M0 0 H{w} V{h - r} Q{w} {h} {w - r} {h} H{r} Q0 {h} 0 {h - r} Z"


def section_header(svg, title, th, right=None):
    out = svg.text(0, 34, title, "Sora", 800, 28, th["fg"], ls=-0.8)
    if right:
        out += svg.text(svg.w, 34, right, "Geist", 400, 14, th["mut"], anchor="end")
    return out


# ============================== SECTIONS ==============================

def hero(th):
    svg = Svg(800, 330, f"{NAME} — DevOps & Cloud Engineer")
    clip = svg.uid("c")
    svg.defs.append(f'<clipPath id="{clip}"><path d="{round_rect(800, 330, 12, top=True)}"/></clipPath>')
    body = [lagoon_field(svg, 800, 330, [(150, 90, 150, "#0D9488"), (660, 70, 150, "#0891B2"),
                                         (420, 250, 140, "#059669"), (740, 260, 110, "#1D4ED8")], 34, 11, (300, 360))]
    body.append(svg.text(400, 146, NAME, "Sora", 800, 62, "#ffffff", "middle", ls=-2))
    # typed lines (SMIL so it runs everywhere an SVG <img> animates)
    size, per = 19, 4.0
    total = per * len(TYPED)
    for i, ln in enumerate(TYPED):
        w = text_width(ln, "JetBrains Mono", 500, size)
        x0 = 400 - w / 2
        a, b, c, d, e = [(i * per + o) / total for o in (0, 1.4, 3.2, 3.7, per)]
        cid = svg.uid("t")
        kt, vals = keytimes([(a, 0), (b, f"{w:.1f}"), (c, f"{w:.1f}"), (d, 0)])
        svg.defs.append(f'<clipPath id="{cid}"><rect x="{x0:.1f}" y="178" height="34" width="0">'
                        f'<animate attributeName="width" dur="{total}s" repeatCount="indefinite" keyTimes="{kt}" values="{vals}"/>'
                        f"</rect></clipPath>")
        body.append(svg.text(x0, 203, ln, "JetBrains Mono", 500, size, "#99F6E4", extra=f'clip-path="url(#{cid})"'))
        kt2, v2 = keytimes([(a, f"0 0"), (b, f"{w + 2:.1f} 0"), (c, f"{w + 2:.1f} 0"), (d, "0 0")])
        if a == 0:
            okt, ov = f"0;{e:.4f}", "1;0"
        elif e >= 1:
            okt, ov = f"0;{a:.4f}", "0;1"
        else:
            okt, ov = f"0;{a:.4f};{e:.4f}", "0;1;0"
        body.append(f'<rect x="{x0:.1f}" y="186" width="9.5" height="22" fill="#99F6E4" opacity="0">'
                    f'<animateTransform attributeName="transform" type="translate" dur="{total}s" repeatCount="indefinite" keyTimes="{kt2}" values="{v2}"/>'
                    f'<animate attributeName="opacity" dur="{total}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{okt}" values="{ov}"/></rect>')
    body.append(wave(296, th["bg"], 0.35))
    body.append(wave(302, th["bg"]))
    svg.add(f'<g clip-path="url(#{clip})">{"".join(body)}</g>')
    return svg


def job_status(svg, i, r=12, cyc=10.0, step=1.2):
    t_start = 0.4 + i * step
    t_done = t_start + 0.9
    p = lambda v: f"{v / cyc * 100:.2f}"
    k = svg.uid("j")
    svg.css.append(
        f"@keyframes {k}r{{0%,{p(t_start)}%{{opacity:0}}{p(t_start + .05)}%,{p(t_done)}%{{opacity:1}}{p(t_done + .05)}%,100%{{opacity:0}}}}"
        f"@keyframes {k}o{{0%,{p(t_done)}%{{opacity:0;transform:scale(.5)}}{p(t_done + .3)}%,{p(cyc - .5)}%{{opacity:1;transform:scale(1)}}100%{{opacity:0}}}}"
        f".{k}r{{animation:{k}r {cyc}s linear infinite}}"
        f".{k}o{{transform-box:fill-box;transform-origin:center;animation:{k}o {cyc}s cubic-bezier(.2,.8,.2,1) infinite}}")
    q = r / 18
    return (f'<circle r="{r}" fill="none" stroke="currentColor" stroke-opacity=".35" stroke-width="2.5"/>'
            f'<g class="{k}r" opacity="0"><circle r="{r}" fill="none" stroke="#D29922" stroke-opacity=".3" stroke-width="2.5"/>'
            f'<path d="M0 {-r} A{r} {r} 0 0 1 {r} 0" fill="none" stroke="#D29922" stroke-width="2.5" stroke-linecap="round">'
            f'<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur=".8s" repeatCount="indefinite"/></path></g>'
            f'<g class="{k}o" opacity="0"><circle r="{r}" fill="#2DA44E"/>'
            f'<path d="M{-7 * q:.1f} 0 l{5 * q:.1f} {5 * q:.1f} l{9 * q:.1f} {-10 * q:.1f}" fill="none" stroke="#fff" '
            f'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></g>'), (t_done, cyc)


def what_i_do(th, mode):
    svg = Svg(800, 760, "What I do: " + "; ".join(f"{d[0]} — {d[5]}" for d in DISCIPLINES))
    svg.css.append("@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}"
                   ".tile{opacity:0;animation:rise .9s cubic-bezier(.2,.8,.2,1) forwards}"
                   "@keyframes draw{to{stroke-dashoffset:0}}"
                   ".icon{stroke-dasharray:240;stroke-dashoffset:240;animation:draw 1.8s ease-out forwards}")
    out = [section_header(svg, "What I do", th, PRS)]
    for i, (title, c_l, c_d, t_l, stack, desc, icon) in enumerate(DISCIPLINES):
        col = c_l if mode == "light" else c_d
        tcol = t_l if mode == "light" else c_d
        x, y = (i % 2) * 406, 60 + (i // 2) * 232
        status, (t_done, cyc) = job_status(svg, i)
        hl = svg.uid("h")
        svg.css.append(f"@keyframes {hl}{{0%,{t_done / cyc * 100:.1f}%{{opacity:0}}{(t_done + .3) / cyc * 100:.1f}%,94%{{opacity:1}}100%{{opacity:0}}}}"
                       f".{hl}{{animation:{hl} {cyc}s linear infinite}}")
        g = [f'<g transform="translate({x},{y})"><g class="tile" style="animation-delay:{.12 * i:.2f}s">',
             f'<rect x=".5" y=".5" width="393" height="216" rx="14" fill="{th["tile"]}" stroke="{th["bd"]}"/>',
             f'<rect class="{hl}" x="1" y="1" width="392" height="215" rx="13.5" fill="none" stroke="{col}" stroke-width="2" opacity="0"/>',
             f'<g transform="translate(364,32)" color="{th["mut"]}">{status}</g>',
             f'<g transform="translate(20,18)"><rect width="50" height="50" rx="12" fill="{col}" fill-opacity=".14"/>'
             f'<path class="icon" style="animation-delay:{.3 + .12 * i:.2f}s" d="{icon}" fill="none" stroke="{col}" '
             f'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></g>',
             svg.text(84, 50, title, "Sora", 700, 19, th["fg"])]
        lines, n = svg.wrap(20, 94, desc, 350, 20, family="Geist", weight=400, size=13.5, fill=th["mut"])
        assert n <= 4, f"{title}: description wraps to {n} lines; shorten it"
        g += lines
        cx = 20
        for s in stack:
            w = text_width(s, "Geist", 600, 12) + 20
            g.append(f'<rect x="{cx:.1f}" y="182" width="{w:.1f}" height="24" rx="12" fill="{col}" fill-opacity=".13"/>')
            g.append(svg.text(cx + 10, 198, s, "Geist", 600, 12, tcol))
            cx += w + 6
        g.append("</g></g>")
        out.append("".join(g))
    svg.add("".join(out))
    return svg


def how_i_work(th, mode):
    h = 360
    svg = Svg(800, h, "How I work: an AI-native SDLC loop — " + " → ".join(f"{s} ({a})" for s, a, _ in LOOP)
              + f" → back to Plan; inner loop at Test: {INNER_LOOP[1]}")
    svg.css.append("@keyframes pulse{0%,100%{opacity:.3}50%{opacity:1}}")
    cx, cy, rx, ry = 400, h / 2 + 18, 215, h / 2 - 82
    d = f"M{cx} {cy - ry} a{rx} {ry} 0 1 1 0 {2 * ry} a{rx} {ry} 0 1 1 0 {-2 * ry}"
    gid = svg.uid("g")
    svg.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0D9488"/>'
                    f'<stop offset=".5" stop-color="#0891B2"/><stop offset="1" stop-color="#7C3AED"/></linearGradient>')
    n = len(LOOP)
    period = n * 1.8
    out = [section_header(svg, "How I work", th), f'<path d="{d}" fill="none" stroke="url(#{gid})" stroke-width="3"/>']
    for j in range(3):
        out.append(f'<circle r="6" fill="{th["bg"]}" stroke="#0891B2" stroke-width="3">'
                   f'<animateMotion dur="{period}s" begin="{-j * period / 3:.2f}s" repeatCount="indefinite" path="{d}"/></circle>')
    out.append(svg.text(cx, cy - 4, LOOP_CENTER[0], "Sora", 800, 22, th["fg"], "middle"))
    out.append(svg.text(cx, cy + 20, LOOP_CENTER[1], "Geist", 400, 13.5, th["mut"], "middle"))
    for i, (stage, art, col) in enumerate(LOOP):
        a = -math.pi / 2 + i * 2 * math.pi / n
        X, Y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        out.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="17" fill="{col}" fill-opacity=".2" '
                   f'style="animation:pulse {period}s {i * 1.8 - period:.1f}s ease-in-out infinite"/>')
        out.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="10" fill="{col}"/>')
        side = 1 if X > cx + 30 else -1 if X < cx - 30 else 0
        anchor = {1: "start", -1: "end", 0: "middle"}[side]
        tx = X + side * 24
        ty = Y - 2 if side else (Y - 36 if Y < cy else Y + 34)
        out.append(svg.text(tx, ty, stage, "Geist", 700, 15, th["fg"], anchor))
        out.append(svg.text(tx, ty + 18, art, "Geist", 400, 13, th["mut"], anchor))
    i, label = INNER_LOOP
    a = -math.pi / 2 + i * 2 * math.pi / n
    X, Y, r = cx + (rx - 70) * math.cos(a), cy + (ry - 40) * math.sin(a), 22
    dd = f"M{X:.1f} {Y - r:.1f} a{r} {r} 0 1 1 0 {2 * r} a{r} {r} 0 1 1 0 {-2 * r}"
    amber = "#B45309" if mode == "light" else "#FBBF24"
    out.append(f'<path d="{dd}" fill="none" stroke="{amber}" stroke-width="2" stroke-dasharray="3 4"/>'
               f'<circle r="4.5" fill="{amber}"><animateMotion dur="2.2s" repeatCount="indefinite" path="{dd}"/></circle>')
    out.append(svg.text(X + r + 10, Y + 4, label, "Geist", 600, 12.5, amber))
    svg.add("".join(out))
    return svg


def toolbox(th, mode):
    rows = len(TOOLBOX)
    h = 58 + rows * 56
    svg = Svg(800, h, "Toolbox: " + "; ".join(f"{g}: {', '.join(items)}" for g, _, _, _, items in TOOLBOX))
    x0, span = 176, 800 - 176
    out = [section_header(svg, "Toolbox", th)]
    fade = svg.uid("f")
    svg.defs.append(f'<linearGradient id="{fade}"><stop offset="0" stop-color="{th["bg"]}"/>'
                    f'<stop offset=".07" stop-color="{th["bg"]}" stop-opacity="0"/><stop offset=".93" stop-color="{th["bg"]}" stop-opacity="0"/>'
                    f'<stop offset="1" stop-color="{th["bg"]}"/></linearGradient>')
    for ri, (group, c_l, c_d, t_l, items) in enumerate(TOOLBOX):
        col = c_l if mode == "light" else c_d
        tcol = t_l if mode == "light" else c_d
        y = 58 + ri * 56
        out.append(svg.text(0, y + 22, group, "Sora", 700, 14.5, tcol))
        widths = [text_width(s, "Geist", 600, 14) + 32 for s in items]
        one = sum(widths) + 10 * len(items)
        reps = max(1, math.ceil(span / one))
        unit = one * reps
        chips, cx = [], 0.0
        for _ in range(2 * reps):
            for s, w in zip(items, widths):
                chips.append(f'<rect x="{cx:.1f}" width="{w:.1f}" height="34" rx="17" fill="{col}" fill-opacity=".13"/>')
                chips.append(svg.text(cx + 16, 22, s, "Geist", 600, 14, tcol))
                cx += w + 10
        k = svg.uid("m")
        frm, to = ("0", f"-{unit:.1f}px") if ri % 2 == 0 else (f"-{unit:.1f}px", "0")
        svg.css.append(f"@keyframes {k}{{from{{transform:translateX({frm})}}to{{transform:translateX({to})}}}}"
                       f".{k}{{animation:{k} {unit / 22:.1f}s linear infinite}}")
        cid = svg.uid("c")
        svg.defs.append(f'<clipPath id="{cid}"><rect x="{x0}" y="{y - 4}" width="{span}" height="44"/></clipPath>')
        out.append(f'<g clip-path="url(#{cid})"><g transform="translate({x0},{y})"><g class="{k}">{"".join(chips)}</g></g></g>')
    out.append(f'<rect x="{x0}" y="50" width="{span}" height="{h - 50}" fill="url(#{fade})"/>')
    svg.add("".join(out))
    return svg


def heading(th, title):
    svg = Svg(800, 48, title)
    svg.add(section_header(svg, title, th))
    return svg


def footer(th):
    svg = Svg(800, 130, FOOTER_LINE)
    clip = svg.uid("c")
    svg.defs.append(f'<clipPath id="{clip}"><path d="{round_rect(800, 130, 12, top=False)}"/></clipPath>')
    body = [lagoon_field(svg, 800, 130, [(130, 100, 110, "#0D9488"), (430, 120, 110, "#059669"),
                                         (690, 90, 110, "#0891B2"), (760, 130, 80, "#1D4ED8")], 16, 5, (120, 150))]
    body.append(wave(36, th["bg"], 0.35, flip=True))
    body.append(wave(30, th["bg"], 1, flip=True))
    body.append(svg.text(400, 96, FOOTER_LINE, "Sora", 700, 17, "#ffffff", "middle"))
    svg.add(f'<g clip-path="url(#{clip})">{"".join(body)}</g>')
    return svg


def pill(th, label, icon):
    w = 18 + 16 + 8 + text_width(label, "Geist", 600, 14) + 18
    svg = Svg(math.ceil(w), 40, label)
    svg.add(f'<rect x=".5" y=".5" width="{w - 1:.1f}" height="39" rx="19.5" fill="{th["tile"]}" stroke="{th["bd"]}"/>'
            f'<g transform="translate(18,12) scale(.6667)" fill="none" stroke="{th["fg"]}" stroke-width="2.6" '
            f'stroke-linecap="round" stroke-linejoin="round"><path d="{icon}"/></g>'
            + svg.text(42, 25, label, "Geist", 600, 14, th["fg"]))
    return svg


# ============================== MAIN ==============================

def main():
    OUT.mkdir(exist_ok=True)
    jobs = []
    for mode, th in THEMES.items():
        jobs += [
            (f"hero-{mode}.svg", hero(th)),
            (f"what-i-do-{mode}.svg", what_i_do(th, mode)),
            (f"how-i-work-{mode}.svg", how_i_work(th, mode)),
            (f"toolbox-{mode}.svg", toolbox(th, mode)),
            (f"selected-project-{mode}.svg", heading(th, "Selected project")),
            (f"footer-{mode}.svg", footer(th)),
        ]
        jobs += [(f"pill-{key}-{mode}.svg", pill(th, label, icon)) for key, label, icon in PILLS]
    for name, svg in jobs:
        data = svg.render()
        (OUT / name).write_text(data, encoding="utf-8")
        print(f"{name:32s} {len(data) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
