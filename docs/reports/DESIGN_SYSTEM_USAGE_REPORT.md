# Design System Usage Report - Phase 13O.1

This report documents the adoption of the newly uploaded design system files as the single source of visual authority for the SmartOnboard application. It includes a catalog of imported tokens, the components actively consuming them, and the details of legacy variable removal.

---

## 1. Imported Tokens

The master values are imported from the design system directory:
* CSS Variables: [variables.css](file:///Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/variables.css) (imported in [index.css](file:///Users/krishnagarg/smartonboard-main/frontend/src/index.css))
* Tailwind Reference: [theme.css](file:///Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/theme.css) (reserved for theme structures)
* Data Tokens: [tokens.json](file:///Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/tokens.json) (token manifest reference)

### Token Categories Imported:

1. **Colors**:
   - `--color-ink` (`#17191c`): Deep ink primary text/fill.
   - `--color-pure-white` (`#ffffff`): Pure background.
   - `--color-fog` (`#f7f7f8`): Cool wash tint.
   - `--color-ash` (`#4c4c4c`): Slate ash for secondary text.
   - `--color-graphite` (`#777b86`): Muted graphite.
   - `--color-dove` (`#a3a6af`): Subtle borders.
   - `--color-slate` (`#8b8c8d`): Medium gray.
   - `--color-obsidian` (`#000000`): Pure black.
   - `--color-rust` (`#5d2a1a`): Warm rust brand color.
   - `--color-apricot-wash` (`#fbe1d1`): Apricot tint for alert highlights.
   - `--color-sky-wash` (`#d3e3fc`): Sky blue tint.

2. **Typography Families**:
   - `--font-signifier`: Headline typeface.
   - `--font-sohne`: Body and UI control typeface.

3. **Typography Scale**:
   - `--text-caption` (`14px`), `--text-body` (`16px`), `--text-body-lg` (`18px`)
   - `--text-subheading` (`22px`), `--text-heading-sm` (`26px`), `--text-heading` (`44px`)
   - `--text-heading-lg` (`64px`), `--text-display` (`90px`)

4. **Typography Weights**:
   - `--font-weight-regular` (`400`), `--font-weight-medium` (`500`)
   - Custom weights: `--font-weight-w430`, `--font-weight-w450`, `--font-weight-w480`

5. **Spacing Scale**:
   - Standard 4px-based spacing: `--spacing-4`, `--spacing-8`, `--spacing-12`, `--spacing-16`, `--spacing-20`, `--spacing-24`, `--spacing-28`, `--spacing-32`, `--spacing-40`, `--spacing-64`, `--spacing-80`, `--spacing-96`, `--spacing-124`, `--spacing-128`, `--spacing-160`.

6. **Layout**:
   - `--page-max-width` (`1200px`), `--section-gap` (`80px`), `--card-padding` (`24px`), `--element-gap` (`8px`).

7. **Radii**:
   - Named and geometric curves: `--radius-sm`, `--radius-xl`, `--radius-2xl`, `--radius-3xl`, `--radius-tags`, `--radius-cards`, `--radius-images`, `--radius-inputs`, `--radius-avatars`, `--radius-buttons`.

8. **Shadows**:
   - `--shadow-subtle` (`rgba(4, 23, 43, 0.05) 0px 0px 0px 1px...`).

9. **Surfaces**:
   - `--surface-canvas` (`#ffffff`), `--surface-fog` (`#f7f7f8`), `--surface-card` (`#ffffff`), `--surface-warm-tint`, `--surface-cool-tint`, `--surface-ink`.

---

## 2. Consuming Components

All components in the React frontend application consume these master variables. Major views and components include:

* **Landing Page**: [Landing.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/Landing.tsx) (uses typography scales, display fonts, rust accents, and page max widths).
* **Authentication**: [Login.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/Login.tsx), [Register.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/Register.tsx) (uses card padding, input radii, and ink borders).
* **Recruiter & Candidate Dashboards**: [AppLayout.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/AppLayout.tsx), [CandidateLayout.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/CandidateLayout.tsx) (uses system backgrounds, canvas surfaces, header heights, and shadows).
* **Jobs & Pipeline**: [Jobs.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/Jobs.tsx), [PipelineBoard.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/PipelineBoard.tsx) (uses tag radii, button styling, card padding, and element gaps).
* **Applications**: [Applications.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/Applications.tsx) (uses data tables and status badge themes).
* **Analytics & Settings**: [Analytics.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/Analytics.tsx) (uses layout spacing, card boundaries, and graphic borders).

---

## 3. Removed Tokens from `index.css`

Duplicated token definitions inside `:root` selector were completely purged from `index.css`. Below is the before/after breakdown of the changes made:

### Before
```css
/* SmartOnboard — Steep Design System */

:root {
  /* Colors from Steep Design System */
  --color-ink: #17191c;
  --color-pure-white: #ffffff;
  --color-fog: #f7f7f8;
  --color-ash: #4c4c4c;
  --color-graphite: #777b86;
  --color-dove: #a3a6af;
  --color-slate: #8b8c8d;
  --color-obsidian: #000000;
  --color-rust: #5d2a1a;
  --color-apricot-wash: #fbe1d1;
  --color-sky-wash: #d3e3fc;

  /* Typography — Font Families */
  --font-signifier: 'Signifier', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-sohne: 'Sohne', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;

  /* Typography — Scale */
  --text-caption: 14px;
  --leading-caption: 1.5;
  --tracking-caption: -0.13px;
  --text-body: 16px;
  --leading-body: 1.38;
  --tracking-body: -0.14px;
  --text-body-lg: 18px;
  --leading-body-lg: 1.35;
  --tracking-body-lg: -0.16px;
  --text-subheading: 22px;
  --leading-subheading: 1.25;
  --tracking-subheading: -0.2px;
  --text-heading-sm: 26px;
  --leading-heading-sm: 1.18;
  --tracking-heading-sm: -0.23px;
  --text-heading: 44px;
  --leading-heading: 1.1;
  --tracking-heading: -0.66px;
  --text-heading-lg: 64px;
  --leading-heading-lg: 1.1;
  --tracking-heading-lg: -1.6px;
  --text-display: 90px;
  --leading-display: 1.1;
  --tracking-display: -2.25px;

  /* Typography — Weights */
  --font-weight-regular: 400;
  --font-weight-w430: 430;
  --font-weight-w450: 450;
  --font-weight-w480: 480;
  --font-weight-medium: 500;

  /* Spacing Scale */
  --spacing-unit: 4px;
  --spacing-4: 4px;
  --spacing-8: 8px;
  --spacing-12: 12px;
  --spacing-16: 16px;
  --spacing-20: 20px;
  --spacing-24: 24px;
  --spacing-28: 28px;
  --spacing-32: 32px;
  --spacing-40: 40px;
  --spacing-64: 64px;
  --spacing-80: 80px;
  --spacing-96: 96px;
  --spacing-124: 124px;
  --spacing-128: 128px;
  --spacing-160: 160px;

  /* Layout */
  --page-max-width: 1200px;
  --section-gap: 80px;
  --card-padding: 24px;
  --element-gap: 8px;

  /* Border Radius */
  --radius-sm: 0.01px;
  --radius-xl: 12px;
  --radius-2xl: 16px;
  --radius-2xl-2: 20px;
  --radius-3xl: 24px;

  /* Named Radii */
  --radius-tags: 9999px;
  --radius-cards: 24px;
  --radius-images: 12px;
  --radius-inputs: 16px;
  --radius-avatars: 9999px;
  --radius-buttons: 9999px;

  /* Shadows */
  --shadow-subtle: rgba(4, 23, 43, 0.05) 0px 0px 0px 1px, rgba(0, 0, 0, 0.1) 0px 20px 25px -5px, rgba(0, 0, 0, 0.1) 0px 8px 10px -6px;

  /* Surfaces */
  --surface-canvas: #ffffff;
  --surface-fog: #f7f7f8;
  --surface-card: #ffffff;
  --surface-warm-tint: #fbe1d1;
  --surface-cool-tint: #d3e3fc;
  --surface-ink: #17191c;

  /* Old Layout Variables mapping to Steep Design System */
```

### After
```css
/* SmartOnboard — Steep Design System */
@import '../frontend/design-system/variables.css';

:root {
  /* Old Layout Variables mapping to Steep Design System */
```

With this update, any changes to typography, color definitions, scale ratios, spacing offsets, or named borders in `/frontend/frontend/design-system/variables.css` will immediately cascade across the entire platform, establishing it as the single, master visual authority.
