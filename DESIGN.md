---
name: Folio
description: Quantitative portfolio analysis for self-directed investors.
colors:
  instrument-blue: "#2563eb"
  midnight-slate: "#0f172a"
  cool-mist: "#f1f5f9"
  white-surface: "#ffffff"
  steel-line: "#e2e8f0"
  steel-gray: "#64748b"
  field-green: "#16a34a"
  amber-signal: "#d97706"
  alert-red: "#dc2626"
typography:
  display:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.5px"
  headline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "normal"
  title:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0.5px"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  2xl: "28px"
components:
  button-primary:
    backgroundColor: "{colors.instrument-blue}"
    textColor: "{colors.white-surface}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "#1d4ed8"
    textColor: "{colors.white-surface}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.instrument-blue}"
    rounded: "{rounded.md}"
    padding: "6px 12px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.steel-gray}"
    rounded: "{rounded.sm}"
    padding: "4px 8px"
  input-default:
    backgroundColor: "{colors.white-surface}"
    textColor: "{colors.midnight-slate}"
    rounded: "{rounded.md}"
    padding: "6px 10px"
  tab-active:
    backgroundColor: "transparent"
    textColor: "{colors.instrument-blue}"
    padding: "12px 16px"
  tag-default:
    backgroundColor: "#f8fafc"
    textColor: "{colors.midnight-slate}"
    rounded: "{rounded.sm}"
    padding: "3px 8px"
---

# Design System: Folio

## 1. Overview

**Creative North Star: "The Analyst's Workbench"**

Folio's visual system is a serious instrument. Like a well-maintained workbench where everything has its place and function, nothing exists for decoration — every visual decision earns its presence by serving the analysis. The interface recedes from the data. The user should feel the rigour of the numbers, not the craft of the UI.

The aesthetic draws from Linear's discipline: opinionated, unhurried, and immediately purposeful. White space is structured, not generous for its own sake. The palette is cool and near-neutral, with Instrument Blue reserved for interactive elements and primary data signals. Color is either data-meaningful or absent. Type is a single family at a tight scale — Inter keeps the chrome from competing with the content.

Folio explicitly rejects: the speculative energy of crypto dark mode (neon on black, chart-fetishism); the gamified optimism of retail fintech (Robinhood-style green numbers and confetti); the safe anonymity of generic SaaS blue (an accent that communicates nothing). This is a tool for self-directed investors who want rigorous analysis, not emotional feedback.

**Key Characteristics:**
- Dense, data-forward layouts with deliberate whitespace rhythm
- Restrained palette: cool neutrals + one functional accent (Instrument Blue)
- Monospace for tickers and numeric alignment; Inter for everything else
- Flat surfaces at rest; shadows are structural separators, not expressive
- Every color carries a specific meaning (action, success, warning, danger)
- WCAG AA throughout: color is never the sole carrier of meaning


## 2. Colors: The Workbench Palette

A cool, near-neutral palette that subordinates itself to the data. One accent used with precision.

### Primary
- **Instrument Blue** (#2563eb): The sole accent in the system. Belongs to interactive elements — primary buttons, active tab underlines, focused input borders, ticker symbols in data tables, and primary chart series lines. It marks decisions and direction, not decoration. If it appears on something non-interactive, something is wrong.

### Neutral
- **Midnight Slate** (#0f172a): Default text for all body copy, headings, and data values. Near-black with a perceptible cool blue cast. Never use a pure `#000` — the tint is not accidental.
- **Steel Gray** (#64748b): Secondary text, table column headers, empty states, muted labels, descriptive copy. The voice of context, not content.
- **Cool Mist** (#f1f5f9): Application background. A faint slate-blue tint separates it from the white surface above. Not a neutral gray.
- **White Surface** (#ffffff): Panel and card backgrounds. The primary work surface. Elevation above Cool Mist comes from the border, not shadow.
- **Steel Line** (#e2e8f0): All borders, table dividers, and input strokes. Barely visible but structurally necessary.

### Semantic
- **Field Green** (#16a34a): Positive returns, portfolio gains, pass states. Data signal only.
- **Amber Signal** (#d97706): Warnings, data-freshness notices, non-advice banners. Not an error — a caution.
- **Alert Red** (#dc2626): Negative returns, losses, hard errors, dangerous hover states (destructive buttons). Never used decoratively.

**The Workbench Rule.** Instrument Blue appears on no more than 15% of any given view. Its rarity is what makes it signal. If it spreads across the surface, it signals nothing. Semantic colors follow the same logic: green and red are data, never emphasis.


## 3. Typography

**Body Font:** Inter (with system-ui, sans-serif fallback)
**Monospace:** System monospace stack (tickers, codes, tabular alignment)

**Character:** A single-family system at a deliberately tight scale. Inter's geometric clarity makes the UI recede from the data — the typeface must never attract attention. Monospace is a distinct register: when you see it, you know you're reading a symbol or a code, not prose.

### Hierarchy
- **Display** (700 weight, 18px, -0.5px tracking, 1.2 leading): The logo mark only. Reserved; appears once in the sticky header. The one moment Folio's brand has a voice.
- **Headline** (600 weight, 16px, 1.3 leading): Panel section titles (h2). The primary organizational layer within each tab.
- **Title** (600 weight, 13px, 1.4 leading): Subsection headers within a panel (h3). When used as a category label, uppercase with 0.5px tracking.
- **Body** (400 weight, 14px, 1.5 leading): All prose, error messages, advisory copy, descriptive text. Cap line length at 65–75ch wherever prose paragraphs appear.
- **Label** (500–600 weight, 11px, 0.4–0.5px tracking, uppercase): Table column headers, section meta labels, chip text, status indicators. The system's smallest legible unit.

**The Monospace Signal Rule.** Ticker symbols and tabular numerics are always rendered in a monospace stack. If a number must align to a decimal column, use `font-variant-numeric: tabular-nums` at minimum; a full monospace stack is preferred. Never render a ticker symbol in Inter — the distinction between prose and instrument is the point.


## 4. Elevation

Folio uses a single ambient shadow level. Surfaces convey depth through borders and background tone contrast, not shadow stacking. The goal is to separate surfaces from their background, not to create theatrical depth.

### Shadow Vocabulary
- **Ambient Separator** (`0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.05)`): Applied to panels, the sticky application header, and card containers. A near-invisible layer that lifts the work surface off the background. This is structural, not expressive — it exists so the eye can parse surface hierarchy without effort.

**The Flat-at-Rest Rule.** Surfaces are flat at rest. Shadows do not escalate on hover or focus. The ambient separator is a layout tool, not a state response. Hover states use background tint changes; focus states use the Instrument Blue ring. Nested shadows and shadow amplification are prohibited. If you're reaching for a larger shadow to create emphasis, the design has a different problem.


## 5. Components

### Buttons

Functional and immediate. No gradients, no transforms, no skeuomorphism.

- **Shape:** Gently rounded corners (6px radius)
- **Primary** (Instrument Blue background, white text, `8px 16px` padding, 13px 500 weight): The singular call-to-action per view. Triggers optimizer runs, data fetches, confirmations.
- **Primary Hover:** Background darkens to `#1d4ed8`. No transform. No shadow added.
- **Primary Disabled:** 40% opacity, `cursor: not-allowed`. No trickery.
- **Secondary** (transparent background, Instrument Blue text, 1px Instrument Blue border, `6px 12px` padding): Secondary confirmable actions. Hover tints background `#eff6ff`.
- **Ghost** (no background, no border, Steel Gray text, `4px 8px` padding): Low-priority utility actions. Hover reveals Midnight Slate text. Destructive ghost variants (Clear Portfolio) hover to Alert Red text with a red-tinted border.

### Inputs and Fields

Understated by default. The focus ring is the only expressive moment in the form system.

- **Style:** White Surface background, Steel Line border (1px), 6px radius, `6px 10px` padding, 13px Inter.
- **Focus:** Border shifts to Instrument Blue. Soft `0 0 0 3px rgba(37,99,235,0.1)` halo applied. The one moment of quiet expressiveness in the input system — communicates state without alarm.
- **Ticker Input:** 160px fixed width. `text-transform: uppercase` forced via CSS.
- **Number Inputs:** 80–100px, `font-variant-numeric: tabular-nums`.
- **Error state:** Border Alert Red; error text in Alert Red below the field, 12px.

### Tab Navigation

The primary routing surface of the application shell.

- **Default:** Steel Gray text, no bottom border, `12px 16px` padding, 13px 500 weight.
- **Hover:** Midnight Slate text. No border. Transition 150ms.
- **Active:** Instrument Blue text, 2px solid Instrument Blue bottom border. No filled background. The underline is the sole affordance — no pill, no background fill.
- **Gap:** 2px between tab items.

### Asset Table

The primary data entry and display surface.

- **Header row:** Uppercase label style (11px, 600, 0.5px tracking), Steel Gray text, `#f8fafc` background, 1px bottom border. Column headers describe the column, full stop.
- **Data rows:** 13px body, `8px 10px` cell padding, 1px Steel Line bottom border between rows. Hover tints full row to `#f8fafc`.
- **Ticker column:** Monospace, 600 weight, Instrument Blue. Always visually distinct from the data beside it.
- **Borders:** `border-collapse: collapse`. No outer table border. Rows are separated, not contained.

### Metric Cards

Compact at-a-glance output blocks used in optimizer and simulation results.

- **Container:** `#f8fafc` background, Steel Line border (1px), 6px radius, `12px 16px` padding, minimum 120px width, flex-wrap in a row.
- **Label:** Uppercase label style, Steel Gray. States what follows; never decorates it.
- **Value:** 22px, 700 weight, Midnight Slate. The number always dominates. Small labels never compete with it visually.

### Tags and Chips

Inline constraint tokens and category markers.

- **Default:** `#f8fafc` background, Steel Line border (1px), 4px radius, `3px 8px` padding, 12px text, Midnight Slate color.
- **Ticker selection (unselected):** Same as default.
- **Ticker selection (selected):** Instrument Blue border (1px), `#eff6ff` background, Instrument Blue text.
- **ESG/Alert variant:** `#fff1f2` background, `#fecdd3` border. Alert Red text. The background tint carries the severity; the text confirms it.

### Stress Cards

The most semantically loaded component. Severity expressed through full-surface background tinting.

- **Severe** (`#fff1f2` background, `#fca5a5` border): Return in Alert Red, 800 weight, 28px. Portfolio impact negative and significant.
- **Bad** (`#fff7ed` background, `#fed7aa` border): Return in `#ea580c`. Still a loss, less severe.
- **Mild** (`#fffbeb` background, `#fde68a` border): Return in Amber Signal. Caution range.
- **Positive** (`#f0fdf4` background, `#bbf7d0` border): Return in Field Green.
- **Neutral** (Cool Mist background, Steel Line border): No clear directional signal.

There is no border-left stripe. The full card surface carries the severity signal — a stripe would be insufficient and is prohibited by the system's global ban.

### Tooltip

Dark reversal. Used exclusively for jargon disambiguation inline.

- **Container:** `#1e293b` background (deep slate, not pure black), `#f1f5f9` text, 12px Inter, 7px radius. 9px 12px padding.
- **Trigger:** Small info icon at 70% opacity; hover reveals the bubble. No persistent affordance.
- **Arrow:** Centered below the bubble, matching background color.
- **Behavior:** Appears above the trigger; repositions if there is insufficient space.


## 6. Do's and Don'ts

### Do:
- **Do** render ticker symbols in a monospace stack, always. They are instruments, not prose.
- **Do** pair color with labels, numbers, or icons. Color alone must never be the sole signal — a colorblind user must read the same information you do.
- **Do** use `font-variant-numeric: tabular-nums` for any column of numbers requiring decimal alignment.
- **Do** express severity through full card-surface background tinting. A tinted surface carries more weight than an accent stripe.
- **Do** maintain 4.5:1 contrast for all body text. Test Field Green and Amber Signal on White Surface specifically — both are frequently non-compliant on light backgrounds.
- **Do** respect `prefers-reduced-motion` for all CSS transitions and animations.
- **Do** use Instrument Blue exclusively for interactive, data-meaningful, or selection-state elements. If it appears on something the user cannot act on, remove it.

### Don't:
- **Don't** introduce neon accents, electric gradients, or dark-mode-on-black surfaces. Folio is not a crypto terminal. This is the hardest anti-reference: it applies to any future dark mode proposal.
- **Don't** add celebratory states, confetti, green-number animations, or gamification signals of any kind. Folio doesn't care how the trade went.
- **Don't** use `border-left` greater than 1px as a colored accent stripe on cards, list items, callouts, or alerts. Rewrite with a full background tint, a leading icon, or nothing.
- **Don't** use gradient text (`background-clip: text` with a gradient). Emphasis through weight or size only — never through spectacle.
- **Don't** stack shadows or amplify them on hover. One ambient separator level exists; escalation is prohibited.
- **Don't** use Instrument Blue as a background fill on anything larger than a button. It is an accent on no more than 15% of any view.
- **Don't** introduce a second non-semantic accent color. Field Green, Amber Signal, and Alert Red are data signals, not a color palette. Any new color must justify its existence as a data-meaningful signal with a named role.
- **Don't** use pure `#000000` black or `#ffffff` white. Midnight Slate and White Surface carry a perceptible cool blue cast. Preserve the tint.
- **Don't** use generic SaaS blue as an expressive choice. Instrument Blue is the one blue allowed in this system, and it earns its place by being functional.
