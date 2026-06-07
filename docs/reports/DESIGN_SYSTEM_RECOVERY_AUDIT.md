# Design System Recovery Audit - Phase 13O.1

This audit identifies which visual files currently control the SmartOnboard UI, evaluates the integration status of the newly uploaded design system files, and maps out the transition to the design system as the single visual authority.

---

## 1. Current UI Styling Sources (Imported vs Unused)

To determine which stylesheets actively drive the UI, a search of the codebase was conducted:
- **Active / Imported Stylesheet**: 
  - [index.css](file:///Users/krishnagarg/smartonboard-main/frontend/src/index.css): Imported in [main.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/main.tsx). This is the **only** stylesheet currently loaded in the production bundle.
- **Inactive / Unused Stylesheets**:
  - [App.css](file:///Users/krishnagarg/smartonboard-main/frontend/src/App.css): Legacy stylesheet from the default Vite template. It is **not imported** or referenced anywhere in the source code.

---

## 2. New Design-System Files Audit

The newly supplied design system files are located in `/Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/`:

| File Name | Role | Import Status | Consumption Status |
|---|---|---|---|
| **[DESIGN.md](file:///Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/DESIGN.md)** | Style rules & guidelines | ❌ Unused | ❌ Ignored |
| **[variables.css](file:///Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/variables.css)** | CSS custom variables (:root) | ❌ Unused | ❌ Ignored |
| **[theme.css](file:///Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/theme.css)** | Tailwind v4 @theme blocks | ❌ Unused | ❌ Ignored |
| **[tokens.json](file:///Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/tokens.json)** | Design Token schema specifications | ❌ Unused | ❌ Ignored |

None of the newly supplied design system files are currently imported in the frontend build chain. All variables defined in them are currently ignored by the running application.

---

## 3. Legacy and Hardcoded Styling References

### 3.1 Legacy Variable Mapping in `index.css`
The [index.css](file:///Users/krishnagarg/smartonboard-main/frontend/src/index.css) file currently defines a duplicate copy of visual variables in its `:root` selector. It also contains several legacy custom maps supporting the transition:
- `--color-cork-shadow`
- `--color-burnt-sienna`
- `--color-dark-cork`
- `--color-warm-cream`
- `--color-grey-brown`

These mapping hooks are used throughout the UI to adapt older components to the Steep color scheme.

### 3.2 Components Relying on Hardcoded Colors
Several components utilize inline hardcoded styles or fallback colors instead of strictly referencing CSS custom variables:
- **[AppLayout.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/AppLayout.tsx)**: Hardcoded padding, colors, and border inline styles in popups, command bar overlays, and sidebar nodes.
- **[CandidateLayout.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/CandidateLayout.tsx)**: Hardcoded inline text sizes, colors, and layout widths.
- **[Landing.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/Landing.tsx)**: Hardcoded background radial gradients, glow hex codes, and border colors.
- **Dashboards**: Inline margins, paddings, and background overrides.

---

## 4. Integration Blueprint

To enforce the new design system files as the single visual authority:
1. **Connect Variables**: Add an `@import` statement in `index.css` to load `variables.css`.
2. **Purge Variable Duplication**: Delete duplicate visual variable definitions from `index.css`, keeping only mapping aliases and utility rules.
3. **Align Theme Overrides**: Update the `[data-theme="dark"]` block in `index.css` to override variables from the new `variables.css` source.
