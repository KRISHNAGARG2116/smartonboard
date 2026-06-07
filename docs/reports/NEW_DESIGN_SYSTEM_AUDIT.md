# New Design System Audit — Steep Style Reference

This report documents the architectural patterns, tokens, and components defined in the new daylight analytics design system **Steep** (`frontend/frontend/design-system/`).

---

## 1. Color Palette (Tokens & CSS Variables)

The Steep design system is light-themed and uses color as punctuation on a cool-tone marble/monochrome canvas.

| Role | CSS Variable | Value | Description |
| :--- | :--- | :--- | :--- |
| **Ink** | `--color-ink` | `#17191c` | Primary text, filled CTA backgrounds, dark surfaces. |
| **Pure White** | `--color-pure-white` | `#ffffff` | Page canvas, elevated card surfaces, CTA text. |
| **Fog** | `--color-fog` | `#f7f7f8` | Secondary canvas, section backdrops, app shell, sidebar. |
| **Ash** | `--color-ash` | `#4c4c4c` | Muted body copy text, secondary borders/strokes. |
| **Graphite** | `--color-graphite` | `#777b86` | Tertiary text, icon outlines, inactive links. |
| **Dove** | `--color-dove` | `#a3a6af` | Hairline dividers, border grids, inputs, placeholders. |
| **Slate** | `--color-slate` | `#8b8c8d` | Low-emphasis context icons/borders. |
| **Obsidian** | `--color-obsidian` | `#000000` | Sharp contrast hairlines and strokes. |
| **Rust** | `--color-rust` | `#5d2a1a` | Signature warm accent for visual highlights and donuts. |
| **Apricot Wash** | `--color-apricot-wash` | `#fbe1d1` | Soft warm card tint, hero background radial glow. |
| **Sky Wash** | `--color-sky-wash` | `#d3e3fc` | Soft cool card tint for charts and chat dialogs. |

---

## 2. Typography & Hierarchy

Typography relies on a clean pairing between **Signifier** (display serif for headlines) and **Söhne** (sans-serif utility workhorse for UI text).

* **Display Serif (`--font-signifier`)**: Signifier, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
* **UI Sans (`--font-sohne`)**: Sohne, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif

### Typographic Scale

| Token | Size | Line Height | Letter Spacing | Font Family |
| :--- | :--- | :--- | :--- | :--- |
| `--text-caption` | `14px` | `1.5` | `-0.13px` | Söhne |
| `--text-body` | `16px` | `1.38` | `-0.14px` | Söhne |
| `--text-body-lg` | `18px` | `1.35` | `-0.16px` | Söhne |
| `--text-subheading` | `22px` | `1.25` | `-0.2px` | Söhne |
| `--text-heading-sm` | `26px` | `1.18` | `-0.23px` | Söhne |
| `--text-heading` | `44px` | `1.1` | `-0.66px` | Signifier |
| `--text-heading-lg` | `64px` | `1.1` | `-1.6px` | Signifier |
| `--text-display` | `90px` | `1.1` | `-2.25px` | Signifier |

---

## 3. Spacing, Shapes & Borders

* **Base Unit**: `4px` grid (increments: 4, 8, 12, 16, 20, 24, 28, 32, 40, 64, 80, 96, 128, 160).
* **Border Radii**:
  * tags / badges / buttons / avatars: `9999px` (fully rounded pill)
  * cards: `24px` (generously rounded tiles)
  * images: `12px`
  * inputs: `16px`
* **Shadows (`--shadow-subtle`)**:
  * 3-layer signature stack: `rgba(4, 23, 43, 0.05) 0px 0px 0px 1px, rgba(0, 0, 0, 0.1) 0px 20px 25px -5px, rgba(0, 0, 0, 0.1) 0px 8px 10px -6px`

---

## 4. Components Layout Rules

1. **Filled Dark CTA**: Pill shape (`9999px`), Ink (`#17191c`) background, white text. Only one filled button per screen.
2. **Text Link Button**: ink-colored text, no borders or background, paired to the right of the filled CTA.
3. **Product Dashboard Card**: White surface, `24px` radius, `20px` internal padding, signature subtle shadow.
4. **Warm / Cool Data Cards**: Apricot Wash (`#fbe1d1`) or Sky Wash (`#d3e3fc`) backgrounds, `24px` radius, containing color-themed charts.
5. **Sidebar Navigation**: Fog (`#f7f7f8`) background, `240px` wide, outline-style icons (`16px`), Ink text. Active items use white background with `12px` radius.
6. **Chat / Search Inputs**: White background, `16px` radius, `12px 20px` padding, 1px Dove border.

---

## 5. Motion and Interactions

* Smooth `cubic-bezier(0.16, 1, 0.3, 1)` page transitions.
* Hover animations on interactive cards (slight lift or border darkening).
* Sidebar collapses smoothly.
* Modals and Drawers enter with fade-in and slide-up dynamics.
