# UI/UX & Responsive Audit Report — Phase 15A

This report presents the findings of the comprehensive product-wide UI/UX audit of SmartOnboard. It identifies visual inconsistencies, UX friction points, responsiveness issues, and accessibility gaps across the entire candidate and recruiter journeys, ranking them by severity and detailing the planned remedies.

---

## 1. Executive Summary

The objective of Phase 15A is to elevate SmartOnboard from a functioning utility into a polished, premium daylight SaaS workspace. While the underlying authentication, Twilio verification, and recruiter/candidate APIs are robust and functionally complete, the presentation layer exhibits minor visual inconsistencies, ad-hoc CSS mappings, and minor layout glitches on smaller screens. 

By systematically auditing all 20+ screens against the **Steep Design System**, we ensure a unified product that is visually stunning, fully responsive, and accessible.

---

## 2. Audit Findings & Severity Rankings

### A. Visual Consistency & Typography Mismatches
- **Issue**: Standard text elements and page headings across dashboards are using browser-default sans-serif fallbacks without consistent letter-spacing and weight hierarchy.
- **Severity**: **Medium**
- **Details**:
  - `Landing.tsx` headline uses serif italic tags inline rather than the global `Signifier` class.
  - Form labels and KPI captions on candidate and recruiter dashboards lack standard `uppercase` transformations and consistent sub-weights (Sohne `430`/`450`/`480`).
  - Dividers and borders are thicker than 1px in some modal and settings layouts, violating the hairline principle.
- **Recommended Remedy**:
  - Implement strict global rules in `index.css` forcing `-webkit-font-smoothing` and the exact `-0.009em` letter-spacing on all `Sohne` body and UI texts.
  - Define utility classes for Signifier (display serifs at line-height `1.1` and tracking `-0.025em`) and Sohne micro-weights.
  - Standardise all borders to `1px solid var(--color-cork-shadow)` or `1px solid var(--border)`.

### B. Spacing & Card Radius Inconsistencies
- **Issue**: Content cards and form boxes use varying corner radii (some `12px`, some `16px`, some `24px`), making the interface feel disjointed.
- **Severity**: **Medium**
- **Details**:
  - Dashboard widgets, resumes panels, and profile edit forms use rectangular styling with standard shadow spreads instead of the signature `24px` radius tile look.
  - Spacing gaps between cards and grids fluctuate between custom pixel values instead of aligning with the base-4px spacing units (e.g. `--spacing-16`, `--spacing-24`).
- **Recommended Remedy**:
  - Set all content card components to use a strict `border-radius: var(--radius-cards)` (24px) and the three-layer `--shadow-subtle` shadow.
  - Apply standard inputs radius of `16px` (`--radius-inputs`) and button radius of `9999px` (`--radius-buttons`).
  - Standardise layout margins and padding to use the custom spacing custom properties.

### C. UX & Interaction Gaps
- **Issue**: Interactive controls lack clear focus indicators, loading states, or empty states in some candidate/recruiter workflows.
- **Severity**: **High**
- **Details**:
  - Recruiter setup company wizard and settings forms do not display custom skeleton states or loading button states during submission.
  - Some list views (like upcoming interviews or applications) lack premium empty states, displaying basic text strings instead of illustrated widgets.
  - Success and error alerts are styled as basic colored banners rather than elegant, low-contrast styled text alerts matching the Steep palette.
- **Recommended Remedy**:
  - Create standard animated skeleton skeletons (`.skeleton--card`, `.skeleton--row`) in `index.css`.
  - Add inline spinner loading indicators to primary filled buttons during submission.
  - Standardise all empty states to use the structured `.empty-state` styling with outline icons.

### D. Responsive Overflow & Layout Clipping
- **Issue**: Multi-column grids and data tables cause horizontal overflows or alignment breaks on tablet and mobile viewports.
- **Severity**: **High**
- **Details**:
  - The Candidate and Recruiter Dashboards use a 2-column sidebar grid that squashes on tablets, causing text clipping in statistics widgets.
  - Data tables in the Recruiter Pipeline and Candidate Directory lack responsive horizontal scroll wrappers, resulting in layout overflows.
  - Form cards on mobile have excessively large padding that reduces the usable screen width for input elements.
- **Recommended Remedy**:
  - Use fluid media queries (`@media (max-width: 900px)`) to stack the dashboard grid into a single column.
  - Wrap all data tables in a `.table-wrap` and `.table-scroll` horizontal wrapper with `-webkit-overflow-scrolling: touch`.
  - Dynamically reduce card padding from `24px` to `16px` on screens below `600px`.

### E. Accessibility Barriers (A11y)
- **Issue**: Low contrast ratios on secondary text labels and missing outline indicators for keyboard navigation.
- **Severity**: **Medium**
- **Details**:
  - Inactive tabs, captions, and form hints are styled in light grey that does not satisfy WCAG AA contrast ratios against white surfaces.
  - Focused interactive elements rely on browser-default blue outlines which are often hidden or clipped by card containers.
- **Recommended Remedy**:
  - Enforce Sohne body text in primary Ink (`#17191c`) and secondary text in Ash (`#4c4c4c`) or Graphite (`#777b86`), which satisfy high-contrast ratios.
  - Add a global `:focus-visible` rule in `index.css` supplying a `2px solid var(--accent)` outline with a `2px` offset.

---

## 3. Screen-by-Screen Audit Matrix

| Screen | Target Experience | Discovered Issue | Severity | Recommended Fix |
|---|---|---|---|---|
| **Landing** | Marketing | No radial hero glow or orbiting cards; static CTA button. | **Medium** | Implement Peach Dawn radial glow behind Signifier headline. Render four floating product cards. |
| **Auth Pages** | Guest Entry | Inconsistent input borders, mixed button shapes, missing skeletons. | **Medium** | Apply achromatic Fog layout. Standardise inputs (`16px` radius) and filled Ink CTA pill buttons. |
| **Verification** | Onboarding Gate | Verification cards use rectangular margins; no smooth transition indicators. | **High** | Implement standard `24px` cards and `9999px` badges. Add subtle micro-animations during transitions. |
| **Recruiter Setup**| Workspace Init | Outdated form styling; domain warning is not styled. | **Medium** | Standardise text fields, locks, and submit buttons. |
| **Dashboards** | Workspaces | Flat card layouts; missing Warm and Cool data visualization tints. | **High** | Style widgets using **Warm Data Card** (Apricot Wash `#fbe1d1` background) and **Cool Data Card** (Sky Wash `#d3e3fc`). |
| **Job Feed** | Candidate Job | Match scores and job cards use varying border styles. | **Medium** | Standardise match score circular rings to Steep custom colors. |
| **Pipeline Board** | Recruiter Pipeline| Kanban columns do not fit on tablet/mobile screens. | **High** | Implement column wrapping and horizontal scrolling on mobile viewports. |
| **Data Tables** | Directories | Row hover states and borders are inconsistent. | **Medium** | Style table rows with Fog (`#f7f7f8`) background on hover. Enforce hairlines. |
