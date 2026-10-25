---
name: Obsidian Emerald
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#bacac1'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#85948c'
  outline-variant: '#3c4a43'
  surface-tint: '#2fe0aa'
  primary: '#44edb7'
  on-primary: '#003828'
  primary-container: '#00d09c'
  on-primary-container: '#00533c'
  inverse-primary: '#006c4f'
  secondary: '#43e4b9'
  on-secondary: '#00382a'
  secondary-container: '#00c89e'
  on-secondary-container: '#004d3b'
  tertiary: '#ffc5c2'
  on-tertiary: '#68000f'
  tertiary-container: '#ff9d9a'
  on-tertiary-container: '#8f1721'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#59fdc5'
  primary-fixed-dim: '#2fe0aa'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#00513b'
  secondary-fixed: '#60fcce'
  secondary-fixed-dim: '#3adfb3'
  on-secondary-fixed: '#002117'
  on-secondary-fixed-variant: '#00513e'
  tertiary-fixed: '#ffdad8'
  tertiary-fixed-dim: '#ffb3b0'
  on-tertiary-fixed: '#410006'
  on-tertiary-fixed-variant: '#8c1520'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display:
    fontFamily: Outfit
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.015em
  headline-lg-mobile:
    fontFamily: Outfit
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Outfit
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  title-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-tablet: 1.5rem
  margin-desktop: 2.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
---

## Brand & Style

This design system expresses a high-precision, focused fintech aesthetic tailored for an intelligent mutual fund investment assistant. Built around an ultra-dark canvas and energized by electric emerald accents, the visual style combines modern financial clarity with atmospheric depth.

### Personality & Emotional Resonance
- **Disciplined Precision:** High data legibility, structured hierarchy, and exact numerical alignment instill confidence in automated portfolio management and wealth building.
- **Electric Forward-Momentum:** The signature neon emerald accent punctuates wealth growth, positive delta, and intelligent buy-signals without visual fatigue.
- **Refined Sophistication:** Subtle surface shifts between deep obsidian and sleek slate layers generate an executive, distraction-free environment that feels dependable and cutting-edge.

### Style Directives
- **Subtle Layered Depth:** Rely on disciplined surface steps (from base obsidian to elevated slate) paired with low-contrast structural borders rather than heavy blur artifacts or drop shadows.
- **Data-First Focus:** Information hierarchy relies on high-contrast numeric typography, intentional color zoning (accent green exclusively for actions and gains; alert coral for risks and losses), and uncluttered breathing room.

## Colors

The palette establishes an ultra-dark background infrastructure overlaid with purposeful financial feedback tones. 

### Palette Tokens & Application
- **Base Canvas (`#121212`):** Obsidian foundation for all primary viewport backgrounds.
- **Surface Level 1 (`#1E222B`):** Sleek slate containers, module backgrounds, and base card surfaces.
- **Surface Level 2 (`#262A35`):** Elevated components, hovered rows, active states, and modals.
- **Primary Accent (`#00D09C`):** High-energy emerald dedicated to primary action triggers, positive market shifts, returns, and successful verification states.
- **Interactive State Mint (`#33DAAF`):** Hover, focus highlight, and interactive states for primary active targets.
- **Translucent Emerald (`rgba(0, 208, 156, 0.12)`): Backdrops for interactive badges, positive pill chips, selected segments, and focus halos.
- **Alert Coral (`#FF6B6B`):** Strict semantic token reserved for negative market deltas, high-risk flags, sell actions, and error banners.
- **Structural Borders (`#2E3240`):** Low-contrast dividers and container perimeters ensuring clean delineation in pitch-black viewports.
- **Text & Content Hierarchy:**
  - **High Contrast (`#FFFFFF`):** NAV metrics, major titles, input text, and key financial figures.
  - **Muted Subtext (`#A0A3B1`):** Fund manager labels, timestamps, metadata, and structural micro-copy.

## Typography

The type system balances technical geometric authority with uncompromised data utility. 

- **Display & Headlines (Outfit):** Utilized for portfolio balances, fund category titles, and analytical dashboards. The geometric construction gives modern flair without sacrificing scanability.
- **Body & Data (Inter):** Applied across fund factsheets, SIP tables, assistant conversational dialogues, and settings. Tabular figures (`tnum`) must be enforced for all currency metrics, daily return percentages, and NAV readings to preserve tabular alignment across lists.
- **Hierarchy Rules:** Large balance statements rely on `display` or `headline-lg` with tight negative letter spacing. Metadata labels use uppercase `label-sm` with widened letter tracking (`0.04em`) rendered in `#A0A3B1` for rapid categorization.

## Layout & Spacing

A disciplined 8-point base grid ensures dense financial data remains clean, breathable, and aligned across all devices.

### Grid & Breakpoints
- **Mobile (< 768px):** 4-column layout with a 16px (`1rem`) outer margin and 16px gutter. Bottom navigation bar anchors assistant input and primary actions.
- **Tablet (768px - 1024px):** 8-column layout with 24px (`1.5rem`) margins and 24px gutters. Secondary analytical modules stack responsively.
- **Desktop (> 1024px):** 12-column layout with 40px (`2.5rem`) outer canvas margins and 24px gutters. Fixed 380px contextual drawer for the conversational mutual fund assistant alongside the primary portfolio/fund explorer views.

### Spacing Application
- Use `space-xs` (4px) and `space-sm` (8px) for internal padding within chips, badges, and tightly locked input fields.
- Use `space-md` (16px) for standard card padding and gap separations in list items.
- Use `space-lg` (24px) for card-to-card structural boundaries and section headings.
- Use `space-xl` (32px) and `space-2xl` (48px) exclusively for dashboard section demarcation.

## Elevation & Depth

Visual hierarchy is maintained through structured tonal layering and crisp boundaries rather than heavy diffusion.

### Depth Hierarchy
1. **Base Layer (`#121212`):** Primary window canvas. Recedes backward.
2. **Surface Layer (`#1E222B`):** Fund cards, list wrappers, chart backings, and conversational chat bubbles. Finished with a 1px solid stroke in `#2E3240`.
3. **Elevated Layer (`#262A35`):** Overlays, dropdown menus, autocomplete popovers, and sticky assistant panels. Features a 1px border `#2E3240` combined with an ambient dark shade: `0 8px 24px -4px rgba(0, 0, 0, 0.45)`.
4. **Accent Glow (Focus States):** Primary interactive focus states deploy a targeted outline paired with a neon aura: `0 0 0 1px #00D09C, 0 0 16px 0 rgba(0, 208, 156, 0.20)`. No ambient shadows are applied to standard cards.

## Shapes

The design system employs a structured geometry: consistent 12px card corners paired with complete pill-shaped dynamic tags.

### Geometric Rules
- **Containers & Cards:** Strictly 12px corner radius (`rounded-lg` token scale adaptation). This ensures fund data containers appear modern and structured without appearing soft or playful.
- **Buttons & Interactive Controls:** Standard 8px radius (`rounded-md`) for primary CTA and secondary input buttons to convey firm structural affordance.
- **Chips, Badges & Toggles:** 9999px fully rounded pill geometry. Used for category tags (e.g., "Equity", "Debt", "ELSS"), return indicators, and quick-filter switches.

## Components

### Buttons
- **Primary CTA:** Background `#00D09C`, text `#121212` (bold `Inter`), 8px border radius. Hover transitions to `#33DAAF`. Pressed state subtly compresses down to scale `0.98`.
- **Secondary / Ghost:** Transparent background with 1px border `#2E3240`, text `#FFFFFF`. Hover elevates to background `#262A35` with border `#A0A3B1`.
- **Destructive / Sell:** Background `rgba(255, 107, 107, 0.12)`, border 1px solid `rgba(255, 107, 107, 0.32)`, text `#FF6B6B`. Hover shifts to solid `#FF6B6B` with `#121212` text.

### Chips & Filters
- **Pill Chips:** Full pill radius (`rounded-full`), horizontal padding of 12px, vertical padding of 6px.
- **Selected State:** Background `rgba(0, 208, 156, 0.12)`, border 1px solid `#00D09C`, text `#00D09C`.
- **Default State:** Background `#1E222B`, border 1px solid `#2E3240`, text `#A0A3B1`. Hover triggers text `#FFFFFF` and border `#A0A3B1`.

### Cards & Fund Tiles
- Background `#1E222B`, border 1px solid `#2E3240`, 12px radius, internal padding 16px or 20px.
- **Interactive State:** Border transitions from `#2E3240` to `#00D09C` with background stepping to `#262A35` upon cursor hover. Contains fund logo placeholder, fund title in `#FFFFFF`, expense ratio/CAGR in `#A0A3B1`, and numeric return highlight in `#00D09C`.

### Form Inputs & Search Fields
- Height 44px, background `#121212`, border 1px solid `#2E3240`, 8px radius. Text `#FFFFFF`, placeholder `#A0A3B1`.
- **Focus State:** Border shifts to `#00D09C` with an outer glow: `box-shadow: 0 0 0 3px rgba(0, 208, 156, 0.15)`.

### Lists & Performance Rows
- Alternating subtle rows or continuous rows separated by a 1px horizontal divider in `#2E3240`.
- Padding 14px vertical, 12px horizontal. Hover highlights the row background with `#262A35`. Numerical delta values dynamically format with `#00D09C` (positive) or `#FF6B6B` (negative).

### Checkboxes & Radio Selectors
- **Unchecked:** 18px box/circle, border 1.5px solid `#2E3240`, background `#121212`.
- **Checked:** Background `#00D09C`, border `#00D09C`, checkmark or inner dot rendered in `#121212`.

### Conversational Assistant Drawer (Domain-Specific)
- Background `#1E222B`, left border 1px solid `#2E3240`.
- **User Message Bubbles:** Background `#262A35`, border 1px solid `#2E3240`, text `#FFFFFF`, right-aligned.
- **Assistant Message Bubbles:** Background `#121212`, border 1px solid `rgba(0, 208, 156, 0.3)`, text `#FFFFFF`, left-aligned with a mini 20px neon emerald assistant emblem.
- **Actionable Assistant Prompts:** Pill chips with translucent emerald backdrops `rgba(0, 208, 156, 0.12)` providing quick responses like "Compare 3Y Returns" or "Analyze Risk Level".