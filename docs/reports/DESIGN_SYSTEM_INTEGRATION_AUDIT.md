# Design System Integration Audit - Phase 13O

This audit identifies the active UI styling files currently in use, evaluates the new design files provided in `frontend/frontend/design-system/`, and details how we will establish the new design system as the single source of truth.

---

## 1. Current Styling Sources

The SmartOnboard frontend UI is controlled by a single CSS file:
- **[index.css](file:///Users/krishnagarg/smartonboard-main/frontend/src/index.css)**: Imported in [main.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/main.tsx). It defines CSS variables, resets, core utility classes, layout structures, and styling overrides.

*Note: There is a [App.css](file:///Users/krishnagarg/smartonboard-main/frontend/src/App.css) file from the default Vite template, but it is not imported or referenced anywhere in the active React source files.*

---

## 2. New Design System Files Audit

The newly supplied design files are located in `frontend/frontend/design-system/` (resolved to `/Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/`):

1. **[DESIGN.md](file:///Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/DESIGN.md)**:
   - **Role**: Brand guidelines and visual style rules for the "Steep" visual identity (editorial display serif, large ceramic radii, light warm-gray surfaces, dual-data charts, single dark CTA).
   - **Status**: **Unused**. It is documentation for developers and does not run in the production build.
2. **[variables.css](file:///Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/variables.css)**:
   - **Role**: Holds the `:root` design token CSS variables (colors, typography scales, spacing units, radii, and surfaces).
   - **Status**: **Unused**. Currently not imported by the build chain or by `index.css`.
3. **[theme.css](file:///Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/theme.css)**:
   - **Role**: Contains a `@theme` CSS block extending Tailwind v4 configuration.
   - **Status**: **Unused**. Since the project uses Vanilla CSS rather than Tailwind CSS, this file is not parsed or referenced in the production bundle.
4. **[tokens.json](file:///Users/krishnagarg/smartonboard-main/frontend/frontend/design-system/tokens.json)**:
   - **Role**: Structured design token specs in JSON format.
   - **Status**: **Unused**. No build tools in the project compile this JSON file.

---

## 3. Integration Plan: single Source of Truth

To make the new design system files the active source of truth and remove duplicate definitions:
1. **Import `variables.css`**: We will import the new `variables.css` file directly at the top of [index.css](file:///Users/krishnagarg/smartonboard-main/frontend/src/index.css):
   ```css
   @import '../frontend/design-system/variables.css';
   ```
2. **Purge Duplicate Variables**: Remove duplicate visual variable declarations (colors, typography, spacing, border-radius) from the `:root` block of [index.css](file:///Users/krishnagarg/smartonboard-main/frontend/src/index.css).
3. **Verify Variable Bindings**: Ensure that all pages and layouts reference the correct visual tokens from the imported stylesheet.
