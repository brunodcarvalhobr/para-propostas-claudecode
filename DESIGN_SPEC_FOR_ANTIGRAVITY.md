# PMRA DocGen — Design Specification for AI Agent Implementation
> **Target:** Python desktop application replicating the layout of the PMRA DocGen Electron app.
> **Recommended stack:** `pywebview` (Python) + HTML/CSS/JS (self-contained in a single `.html` file served from memory or a local string). This is the only Python approach that faithfully reproduces glassmorphism, `backdrop-filter`, CSS animations, and variable fonts. Do NOT use Tkinter, PyQt, or PySide — they cannot render this design system.

---

## 1. Python Entry Point

```python
# main.py
import webview
import os

def main():
    html_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    window = webview.create_window(
        title="PMRA · Gerador de Propostas",
        html=html,
        width=1100,
        height=760,
        min_size=(800, 580),
        frameless=False,        # set True on macOS to match 'hiddenInset' titlebar
        background_color="#FAF9F7",
    )
    webview.start(debug=False)

if __name__ == "__main__":
    main()
```

Install: `pip install pywebview`

---

## 2. Design Tokens

All values below must be defined as CSS custom properties in `:root` (light) and `[data-theme="dark"]` (dark). The toggle between themes is done by setting `document.documentElement.setAttribute("data-theme", "dark")`.

### 2.1 Color Palette

| Token | Light mode | Dark mode |
|---|---|---|
| `--color-ink` | `#0a0a0a` | `#f5f5f7` |
| `--color-ink-600` | `#404040` | `#b8b8bc` |
| `--color-ink-400` | `#737373` | `#8a8a90` |
| `--color-ink-200` | `#d4d4d4` | `#3a3a40` |
| `--color-ink-100` | `#e5e5e5` | `#2a2a30` |
| `--color-paper` | `#faf9f7` | `#0a0a0c` |
| `--color-paper-50` | `#fdfcfa` | `#0f0f12` |
| `--color-paper-100` | `#f5f3ee` | `#15151a` |
| `--color-paper-200` | `#ebe7df` | `#1f1f25` |
| `--color-ember-200` | `#fde68a` | `#fde68a` |
| `--color-ember-300` | `#fbbf24` | `#fcd34d` |
| `--color-ember-400` | `#fb923c` | `#fdba74` |
| `--color-ember-500` | `#f97316` | `#fb923c` |
| `--color-ember-600` | `#ea580c` | `#f97316` |
| `--color-ember-700` | `#c2410c` | `#ea580c` |
| `--color-glass-white` | `rgba(255,255,255,0.55)` | `rgba(20,20,24,0.55)` |
| `--color-glass-strong` | `rgba(255,255,255,0.78)` | `rgba(28,28,34,0.78)` |
| `--color-glass-border` | `rgba(255,255,255,0.7)` | `rgba(255,255,255,0.08)` |
| `--color-glass-tint` | `rgba(249,115,22,0.04)` | `rgba(249,115,22,0.06)` |
| `--color-success-500` | `#16a34a` | `#4ade80` |
| `--color-danger-500` | `#ef4444` | `#f87171` |
| `--color-danger-600` | `#dc2626` | `#f87171` |

### 2.2 Typography

```css
/* Load from Google Fonts or bundle locally */
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;1,9..144,400&family=Inter:wght@400;500;600&display=swap');

:root {
  --font-display: 'Fraunces', ui-serif, Georgia, serif;  /* headings, logo tagline */
  --font-sans:    'Inter', ui-sans-serif, system-ui, sans-serif; /* body */
}
```

**Usage rules:**
- `font-family: var(--font-display)` → page titles (H1: 44px, H2: 26px, H3: 18px), footer tagline (11px italic)
- `font-family: var(--font-sans)` → all body text, labels, inputs, buttons
- Font smoothing on all elements: `-webkit-font-smoothing: antialiased`
- Body text feature settings: `font-feature-settings: 'cv11', 'ss01', 'ss03'`

### 2.3 Border Radius

| Token | Value |
|---|---|
| `--radius-glass` | `18px` (cards) |
| `--radius-glass-sm` | `12px` (inputs, buttons, select dropdowns) |
| Radio/checkbox/toggle tiles | `14px` |
| Stepper pills | `999px` |
| Badge/tag pills | `999px` |

### 2.4 Shadows

```css
--shadow-glass:
  0 1px 0 0 rgba(255,255,255,0.9) inset,
  0 0 0 0.5px rgba(0,0,0,0.04),
  0 14px 40px -16px rgba(15,15,20,0.18),
  0 4px 14px -8px rgba(249,115,22,0.08);

--shadow-glass-hover:
  0 1px 0 0 rgba(255,255,255,0.95) inset,
  0 0 0 0.5px rgba(0,0,0,0.06),
  0 22px 60px -18px rgba(15,15,20,0.22),
  0 8px 22px -10px rgba(249,115,22,0.14);

--shadow-input:
  0 1px 0 0 rgba(255,255,255,0.9) inset,
  0 0 0 0.5px rgba(0,0,0,0.06);

--shadow-button:
  0 1px 0 0 rgba(255,255,255,0.4) inset,
  0 6px 18px -6px rgba(249,115,22,0.5),
  0 2px 6px -2px rgba(234,88,12,0.4);
```

**Dark mode overrides:**
```css
[data-theme="dark"] {
  --shadow-glass:
    0 1px 0 0 rgba(255,255,255,0.04) inset,
    0 0 0 0.5px rgba(255,255,255,0.04),
    0 14px 40px -16px rgba(0,0,0,0.5),
    0 4px 14px -8px rgba(249,115,22,0.10);

  --shadow-button:
    0 1px 0 0 rgba(255,255,255,0.18) inset,
    0 6px 18px -6px rgba(249,115,22,0.55),
    0 2px 6px -2px rgba(234,88,12,0.45);
}
```

### 2.5 Easing & Timing

```css
--ease-out-soft: cubic-bezier(0.22, 1, 0.36, 1);
```

| Animation purpose | Duration | Easing |
|---|---|---|
| All interactive transitions (hover, focus) | `220ms` | `var(--ease-out-soft)` |
| Component enter/fade-in | `320ms` | `var(--ease-out-soft)` |
| Stagger children entrance | `360ms` + delay | `var(--ease-out-soft)` |
| Ambient blob drift A | `38s` | `var(--ease-out-soft)` infinite |
| Ambient blob drift B | `56s` | `var(--ease-out-soft)` infinite |
| Theme toggle icon swap | `200ms` | `ease-out` |

**Never use bounce/spring easings.**

---

## 3. Global CSS Classes

### `.glass`
```css
.glass {
  background: var(--color-glass-white);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 0.5px solid var(--color-glass-border);
  box-shadow: var(--shadow-glass);
}
```

### `.glass-strong`
```css
.glass-strong {
  background: var(--color-glass-strong);
  backdrop-filter: blur(28px) saturate(190%);
  -webkit-backdrop-filter: blur(28px) saturate(190%);
  border: 0.5px solid var(--color-glass-border);
  box-shadow: var(--shadow-glass);
}
```

### `.glass-input`
```css
.glass-input {
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(12px) saturate(160%);
  -webkit-backdrop-filter: blur(12px) saturate(160%);
  border: 0.5px solid rgba(0,0,0,0.08);
  box-shadow: var(--shadow-input);
  transition: all 220ms var(--ease-out-soft);
}
.glass-input:hover { border-color: rgba(0,0,0,0.14); }
.glass-input:focus-within {
  border-color: rgba(249,115,22,0.55);
  box-shadow:
    0 1px 0 0 rgba(255,255,255,0.9) inset,
    0 0 0 3px rgba(249,115,22,0.16);
}
[data-theme="dark"] .glass-input {
  background: rgba(28,28,34,0.55);
  border-color: rgba(255,255,255,0.08);
}
[data-theme="dark"] .glass-input:focus-within {
  border-color: rgba(249,115,22,0.6);
  box-shadow:
    0 1px 0 0 rgba(255,255,255,0.04) inset,
    0 0 0 3px rgba(249,115,22,0.22);
}
```

### `.ambient-grain` (SVG noise texture overlay)
```css
.ambient-grain {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 1;
  opacity: 0.035;
  mix-blend-mode: multiply;
  background-image: url("data:image/svg+xml;utf8,<svg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='1.4' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='0.9'/></svg>");
}
[data-theme="dark"] .ambient-grain {
  mix-blend-mode: screen;
  opacity: 0.045;
}
```

---

## 4. Layout Structure

```
┌─────────────────────────────────────────────────────┐
│  HEADER (sticky, 60px tall, frosted glass)          │
│  [Logo + "Gerador de Propostas"] ── [ThemeToggle]   │
├─────────────────────────────────────────────────────┤
│  MAIN (flex-1, overflow-y: auto)                    │
│  ┌───────────────────────────────────────────────┐  │
│  │  max-width: 896px, margin: auto               │  │
│  │  padding: 32px 28px, gap: 32px between blocks │  │
│  │                                               │  │
│  │  [Content: Landing OR Form Steps]             │  │
│  └───────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│  FOOTER (border-top, 11px text, frosted)            │
│  [Tagline italic] ── [PMRA Propostas · v0.1.0]      │
└─────────────────────────────────────────────────────┘
```

**Ambient background (fixed, behind everything, z-index: -1):**
- Blob A: top-right, 640×640px circle, radial gradient amber/orange, opacity 0.55, blur 64px, animation `drift-a` 38s
- Blob B: bottom-left, 520×520px circle, radial gradient yellow/orange, opacity 0.40, blur 64px, animation `drift-b` 56s
- Blob C: center, 420×820px ellipse, `#C7D2FE` lavender, opacity 0.18, blur 64px, static
- Grain overlay on top of blobs

---

## 5. Component Specifications

### 5.1 Header

```
height: 60px
background: rgba(paper-50, 0.80) + backdrop-filter: blur(48px)
border-bottom: 0.5px solid rgba(0,0,0,0.06)  [dark: rgba(255,255,255,0.06)]
padding: 0 28px (right), 0 84px (left on macOS for traffic lights), 0 28px (left on Windows)
position: sticky, top: 0, z-index: 30

Left side:
  - PMRA logo mark (see §5.1a) at 32px
  - Vertical divider: 1px × 24px, rgba(0,0,0,0.08)
  - "Gerador de Propostas" in font-display, 14.5px, letter-spacing -0.005em, color ink-600

Right side:
  - Theme toggle button (see §5.7)
```

#### 5.1a PMRA Logo Mark
Monogram "PM" rendered in Fraunces italic, or use the SVG at `resources/pmra-logo.png` scaled to height 32–40px. In absence of the image, render:
```html
<div style="width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#f97316,#ea580c);display:flex;align-items:center;justify-content:center;">
  <span style="font-family:var(--font-display);font-style:italic;color:white;font-size:14px;font-weight:500;letter-spacing:-0.02em">PM</span>
</div>
```

### 5.2 Footer

```
height: auto (padding top/bottom: 12px)
background: rgba(paper-50, 0.60) + backdrop-filter: blur(16px)
border-top: 0.5px solid rgba(0,0,0,0.05)  [dark: rgba(255,255,255,0.05)]
padding: 0 28px
font-size: 11px
color: ink-400

Left:  font-display, font-style: italic, letter-spacing: 0.005em
       text: "O nosso negócio é fazer direito"
Right: font-variant-numeric: tabular-nums
       text: "PMRA Propostas · v0.1.0"
```

### 5.3 Progress Stepper

Renders as a pill-shaped frosted nav bar (`.glass`, `border-radius: 999px`, `padding: 8px 12px`).

Each step is a button with:
```
padding: 6px 12px
border-radius: 999px
transition: all 220ms ease-out-soft

States:
  ACTIVE:
    background: white  [dark: rgba(255,255,255,0.10)]
    box-shadow: 0 1px 0 0 rgba(255,255,255,0.9) inset, 0 4px 14px -4px rgba(249,115,22,0.25)

  VISITED (not current):
    hover: background rgba(255,255,255,0.55)

  LOCKED:
    opacity: 0.50, cursor: not-allowed

Step number badge (20×20px circle):
  ACTIVE:   gradient from ember-400 to ember-500, text white, 10.5px bold
  DONE:     bg rgba(ember-500,0.15), text ember-700, shows checkmark icon (3px stroke)
  DEFAULT:  bg ink-100, text ink-400

Step label:
  12.5px, font-weight: 500
  ACTIVE: color ink
  DEFAULT: color ink-600
```

### 5.4 GlassCard

```css
.glass-card {
  position: relative;
  border-radius: 18px;
  /* apply .glass or .glass-strong */
}
```

**CardHeader** (inside card, at top):
```
padding: 28px 32px 16px 32px

eyebrow (optional): 10.5px, uppercase, letter-spacing 0.18em, color ember-600, font-weight 500
title: font-display, 26px, line-height 1.1, letter-spacing -0.01em, color ink
description (optional): 13.5px, line-height relaxed (1.625), color ink-600, max-width: 65ch
```

**CardBody**:
```
padding: 8px 32px 32px 32px
Children entrance: stagger animation (see §6.2)
```

### 5.5 GlassInput

```
Structure:
  [label]          ← 11.5px, uppercase, tracking 0.12em, color ink-600, font-weight 500
  [input wrapper]  ← .glass-input, border-radius 12px, height 44px, padding 0 14px
    [affix-left?]  ← ink-400, 14px
    [<input>]      ← bg transparent, 14px, color ink, placeholder color ink-400/70, outline none
    [affix-right?] ← ink-400, 14px
  [hint/error]     ← 11.5px, hint: ink-400, error: danger-600

Error state on wrapper:
  border-color: rgba(danger-400, 0.60)
  focus-within border-color: rgba(danger-500, 0.70)
```

### 5.6 GlassButton

**Variants:**

```css
/* PRIMARY */
.btn-primary {
  color: white;
  background: linear-gradient(to bottom, #fb923c, #ea580c);  /* ember-400 → ember-600 */
  box-shadow: var(--shadow-button);
  border-radius: 12px;
  font-weight: 500;
}
.btn-primary:hover {
  background: linear-gradient(to bottom, #fb923c, #ea580c);
  filter: brightness(1.06);
  box-shadow: 0 1px 0 0 rgba(255,255,255,0.5) inset, 0 8px 22px -6px rgba(249,115,22,0.6), 0 3px 8px -2px rgba(234,88,12,0.45);
}
.btn-primary:active { transform: scale(0.985); }

/* GHOST */
.btn-ghost {
  color: var(--color-ink-600);
  background: transparent;
  backdrop-filter: blur(12px);
  border: 1px solid transparent;
  border-radius: 12px;
}
.btn-ghost:hover {
  color: var(--color-ink);
  background: rgba(255,255,255,0.40);
  border-color: rgba(0,0,0,0.05);
}

/* OUTLINE */
.btn-outline {
  /* apply .glass-input */
  color: var(--color-ink);
  border-radius: 12px;
}
.btn-outline:hover { background: rgba(255,255,255,0.80); }
```

**Sizes:**
```
sm: height 36px, padding 0 14px, font-size 12.5px
md: height 44px, padding 0 20px, font-size 13.5px  (default)
lg: height 48px, padding 0 24px, font-size 14px
```

**Disabled:** `opacity: 0.50`, `cursor: not-allowed`

**Loading state:** Show spinning Loader icon (24px), hide children text.

### 5.7 Theme Toggle

Small ghost-style button (36×36px). Toggles between sun icon (light) and moon icon (dark). On click, sets `data-theme` attribute on `<html>`. Persists in `localStorage`.

### 5.8 GlassToggle (Switch)

```
Outer label: border-radius 14px, padding 14px 16px
  CHECKED:   border rgba(ember-500,0.40), bg rgba(white,0.85), box-shadow 0 0 0 3px rgba(249,115,22,0.08)
  DEFAULT:   border rgba(0,0,0,0.06), bg rgba(white,0.45)
  hover DEFAULT: bg rgba(white,0.65)

Left side: label (13.5px, font-weight 500) + optional description (12px, ink-400)

Right side: switch track (42×24px, border-radius 999px)
  CHECKED:   gradient ember-400 → ember-500, box-shadow ember glow
  DEFAULT:   bg ink-200, inner shadow

Switch thumb: 20×20px white circle, translate-x from 2px (off) to 21px (on), transition 200ms ease-out-soft
```

### 5.9 GlassRadio (Radio Group)

Each option is a card-style button:
```
border-radius: 14px, padding: 14px 16px
border: 1px solid

SELECTED:
  border: rgba(ember-500,0.40)
  bg: rgba(white,0.85)
  box-shadow: 0 0 0 3px rgba(249,115,22,0.10), 0 8px 22px -12px rgba(249,115,22,0.4)
  scale: 1.000

UNSELECTED:
  border: rgba(0,0,0,0.06)
  bg: rgba(white,0.45)
  scale: 0.995
  hover: bg rgba(white,0.65), border rgba(0,0,0,0.12)

Inside each option:
  Row: [optional icon in ink-400/ember-600] + [label 13.5px font-weight 500] + [radio indicator circle]
  Radio indicator: 16×16px circle
    SELECTED: gradient ember-400→ember-500, white dot 6×6px centered
    DEFAULT:  border ink-200, bg rgba(white,0.60)
  Optional description: 11.5px, ink-400, below the row
```

### 5.10 GlassCheckbox

Same visual rules as GlassRadio but the indicator is a 18×18px rounded square (border-radius 4px):
```
CHECKED:   gradient ember-400→ember-500, checkmark icon white 12px strokeWidth 3
UNCHECKED: border ink-200, bg rgba(white,0.70)
```

### 5.11 GlassSelect

Trigger uses `.glass-input` class + border-radius 12px + height 44px.
Shows selected value (14px, ink) or placeholder (ink-400/70).
ChevronDown icon (16px, ink-400) on the right.

Dropdown panel: `.glass-strong`, border-radius 12px, padding 4px, max-height 288px, overflow-y auto.

Each option: padding 8px 12px, border-radius 8px, font-size 13.5px.
Highlighted: `background: rgba(249,115,22,0.10)`.
Selected: color ember-700, checkmark icon on right.

### 5.12 Section Divider

```
Horizontal rule: 1px height, gradient from transparent → rgba(0,0,0,0.10) → transparent
Optional centered label: 10.5px, uppercase, letter-spacing 0.18em, ink-400, font-weight 500
```

### 5.13 SubBlock (Form Section Group)

```
display: flex, flex-direction: column, gap: 16px

Header (optional):
  title: font-display, 18px, line-height tight, letter-spacing -0.005em, color ink
  description: 12.5px, line-height relaxed, color ink-400
```

### 5.14 FieldGrid (Form Field Layout)

```
display: grid, gap: 20px
cols=1: grid-template-columns: 1fr
cols=2: grid-template-columns: 1fr 1fr  (stacks to 1fr on < 640px)
cols=3: grid-template-columns: 1fr 1fr 1fr  (stacks progressively)
```

---

## 6. Animations

### 6.1 Ambient Blobs

```css
@keyframes drift-a {
  0%,100% { transform: translate3d(0,0,0) scale(1); }
  33%      { transform: translate3d(8%,-6%,0) scale(1.04); }
  66%      { transform: translate3d(-4%,4%,0) scale(0.98); }
}

@keyframes drift-b {
  0%,100% { transform: translate3d(0,0,0) scale(1); }
  50%     { transform: translate3d(-10%,8%,0) scale(1.08); }
}
```

### 6.2 Stagger Children Entrance

Applied to CardBody containers. Each direct child receives:
```css
@keyframes stagger-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
/* child delays: 0, 50, 100, 150, 195, 235, 270, 300ms */
```

### 6.3 Page Transition

On route/step change, incoming content:
```css
@keyframes fade-in {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}
/* duration: 320ms, ease-out-soft */
```

### 6.4 PMRA Loading Pulse (initial app load)

```css
@keyframes pmra-fadein {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
/* 200ms ease-out */
```

---

## 7. Typography Scale Reference

| Use | Font | Size | Weight | Color | Extra |
|---|---|---|---|---|---|
| H1 landing | display | 44px | 400 | ink | line-height 1.05, tracking -0.018em |
| H2 card title | display | 26px | 400 | ink | line-height 1.1, tracking -0.01em |
| H3 subblock title | display | 18px | 400 | ink | line-height tight, tracking -0.005em |
| Footer tagline | display | 11px | 400 italic | ink-400 | tracking 0.005em |
| Body / description | sans | 15px | 400 | ink-600 | line-height 1.625 |
| Card description | sans | 13.5px | 400 | ink-600 | line-height 1.625 |
| Input / body small | sans | 14px | 400 | ink | — |
| Label uppercase | sans | 11.5px | 500 | ink-600 | uppercase, tracking 0.12em |
| Eyebrow uppercase | sans | 10.5px | 500 | ember-600 | uppercase, tracking 0.18em |
| Badge/tag | sans | 11px | 500 | ember-700 | uppercase, tracking 0.16em |
| Hint/error | sans | 11.5px | 400 | ink-400 / danger-600 | — |
| Step label | sans | 12.5px | 500 | ink / ink-600 | — |
| Table header | sans | 11px | 500 | ink-400 | uppercase, tracking wide |
| Footer version | sans | 11px | 400 | ink-400 | tabular-nums |

---

## 8. Scrollbar Styling

```css
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(64,64,64,0.18);
  border-radius: 999px;
  border: 2px solid transparent;
  background-clip: content-box;
}
::-webkit-scrollbar-thumb:hover { background: rgba(64,64,64,0.32); background-clip: content-box; }
[data-theme="dark"] ::-webkit-scrollbar-thumb { background: rgba(220,220,224,0.14); background-clip: content-box; }
[data-theme="dark"] ::-webkit-scrollbar-thumb:hover { background: rgba(220,220,224,0.26); background-clip: content-box; }
```

---

## 9. Selection Color

```css
::selection {
  background: rgba(249,115,22,0.18);
  color: var(--color-ink);
}
```

---

## 10. Landing Page Content

The home screen (before any form step is activated) shows:

```
[Badge pill] — bg rgba(white,0.55), border black/5, px-12 py-4, rounded-full
  ✦ PMRA · Gerador de Propostas   ← sparkle icon + uppercase 11px tracking 0.16em ember-700

[H1] "Propostas comerciais bem feitas, na primeira tentativa."
  font-display 44px, tracking -0.018em, line-height 1.05, color ink

[Subtitle] 15px, ink-600, max-width 65ch
  "Preencha um formulário guiado com os dados da contratação e gere o documento Word
   padronizado da PMRA — escopo consultivo, contencioso ou misto, com toda a lógica
   condicional do template oficial aplicada automaticamente."

[Button row, gap 12px, margin-top 8px]
  [Primary btn lg] FileText icon + "Nova Proposta"
  [Outline btn lg]  ScrollText icon + "Conhecer o fluxo"

[Feature cards grid — 3 columns, gap 16px, margin-top 24px]
  Card 1: eyebrow "01 · Identificação"
          desc "Pessoa física ou jurídica, com endereço, contato principal e múltiplos canais..."
  Card 2: eyebrow "02 · Escopo & Honorários"
          desc "Modalidade consultiva, contenciosa ou mista, com seleção múltipla..."
  Card 3: eyebrow "03 · Documento .docx"
          desc "Geração imediata do arquivo padronizado, com formatação preservada..."
```

---

## 11. Form Step Navigation

The stepper component sits in the header `rightSlot`. Steps:

| # | Key | Label | Short label |
|---|---|---|---|
| 1 | contratante | Contratante | Contratante |
| 2 | escopo | Escopo | Escopo |
| 3 | honorarios-consultiva | Honorários Consultiva | Consultiva |
| 4 | honorarios-contenciosa | Honorários Contenciosa | Contenciosa |
| 5 | despesas | Despesas | Despesas |
| 6 | disposicoes | Disposições | Disposições |
| 7 | revisao | Revisão Final | Revisão |

Navigation controls (Previous / Next / Generate) live inside each step card at the bottom, aligned right.

---

## 12. Z-index Stack

| Layer | Value |
|---|---|
| Base (cards, main content) | 10 |
| Sticky header | 30 |
| Overlay / modal backdrop | 40 |
| Modal / dialog | 50 |
| Toast notifications | 60 |

---

## 13. Implementation Checklist for AI Agent

- [ ] Install `pywebview`: `pip install pywebview`
- [ ] Create `ui/index.html` as a single self-contained file with all CSS inlined in `<style>` and JS in `<script>`
- [ ] Embed Google Fonts import or bundle Fraunces + Inter as base64 data URIs for offline use
- [ ] Implement CSS custom properties for all tokens from §2
- [ ] Implement `.glass`, `.glass-strong`, `.glass-input` utility classes from §3
- [ ] Implement ambient blob background with keyframe animations from §6.1
- [ ] Build Shell layout (header + main + footer) from §4
- [ ] Build all components from §5 using plain HTML + CSS (no framework needed)
- [ ] Implement dark/light theme toggle with `localStorage` persistence
- [ ] Implement JS-based stagger entrance animation for card bodies
- [ ] Implement multi-step form with stepper navigation
- [ ] Bridge Python ↔ JS via `window.pywebview.api` for file save operations
- [ ] Respect `prefers-reduced-motion` media query (skip animations if set)
- [ ] Test backdrop-filter rendering — requires Chromium rendering engine (pywebview uses OS WebView: Chromium on Windows, WebKit on macOS; both support `backdrop-filter`)
