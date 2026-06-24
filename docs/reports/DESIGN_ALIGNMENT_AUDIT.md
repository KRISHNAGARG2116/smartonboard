# Design Alignment Audit — Steep Design System Migration

This audit report documents the product-wide review of SmartOnboard's user interface against the **Steep Design System** ("Soft dawn on a marble dashboard") specifications. It identifies visual inconsistencies, legacy styles, and color mismatches, and provides a clear migration matrix to transition the application into a premium daylight SaaS workspace.

---

## 1. Audit Findings & Answers to Specific Questions

### Q1: Identify all locations where legacy styles remain active.
* **`frontend/src/index.css`**: Defines outlined styles for secondary buttons, saturated alert colors (`--success`, `--danger`, `--warning`), and custom helper variables that mask rather than remove the underlying legacy styling.
* **Component Inline Style Blocks**: Extensive `style={{ ... }}` declarations in `AppLayout.tsx`, `CandidateLayout.tsx`, `Landing.tsx`, `CandidateDashboard.tsx`, and `RecruiterDashboard.tsx` that override global CSS variables and hardcode non-standard border-radii, custom backgrounds, and custom paddings.
* **Layout Headers**: The search bar trigger in `AppLayout.tsx` has `borderRadius: '0px'`, creating a completely rectangular input that violates the rounded design language.
* **Alert Banners**: Banners in `index.css` and layout files (like `CandidateLayout.tsx` line 595) that use saturated Tailwind-style red, green, and orange borders/backgrounds.

### Q2: List every component still using legacy colors.
* **Status Badges**: `.badge--interview` in `index.css` uses saturated blue `#3b82f6` for text and border.
* **Notification Indicators**: The activity bell dot in `AppLayout.tsx` uses `var(--danger)` (`#d32f2f` red) with box-shadow offsets.
* **User Monograms & Avatars**: User menu buttons in layouts use Rust (`#5d2a1a`) as a solid background fill for avatars, rather than using pastel mint, sky, or peach washes with Ink text.
* **KPI / Progress Bars**: Progress bars in `CandidateDashboard.tsx` and `CandidateJobFeed.tsx` use `--color-burnt-sienna` (Rust) and `--color-cork-shadow` directly, making indicators look saturated.
* **Alert States**: Success (`#2e7d32`), warning (`#ed6c02`), and danger (`#d32f2f`) colors in `index.css` are standard bright colors instead of desaturated, low-contrast daylight tones.

### Q3: List every component still using legacy button styles.
* **Ghost Outlined Buttons (`.btn--secondary`)**: Styled with `border: 1px solid var(--color-dove)` and a transparent background. This outlined style is used across almost all pages (e.g. `CandidateApplications.tsx`, `CandidateJobFeed.tsx`, `CandidateProfilePage.tsx`, `PipelineBoard.tsx`, recruiter modals) in direct violation of the Steep principle: *"secondary actions are text links, not ghost/outlined buttons"*.
* **Multiple Filled CTAs**: Views such as dashboard cards, onboarding wizards, and profile settings feature multiple filled or outlined buttons in the same viewport, violating: *"one filled button per screen maximum; secondary actions are text links placed immediately to the right"*.
* **Inline Border Radius Overrides**: Navigation links in `AppLayout.tsx` and `CandidateLayout.tsx` use `.btn--ghost` but override the border-radius to `12px` or `999px` inline, creating visual inconsistency.

### Q4: List every component still using legacy card styles.
* **Blocky Radii & Custom Backgrounds**: Workspace selector dropdown card in `AppLayout.tsx` uses `background: var(--bg)` (Fog) instead of Pure White canvas.
* **Ad-Hoc Card Radii**: Floating product preview cards in `Landing.tsx` hardcode `borderRadius: '20px'` instead of using the standard `24px` radius.
* **Flat Card Containers**: Modals, drawers, and resume upload cards lack the three-layer shadow stack (`--shadow-subtle`) and rely on flat borders.

### Q5: List every component still using legacy spacing rules.
* **Base-4px Spacing Scale Violations**: Multiple pages and components hardcode inline spacings (e.g., `padding: '10px 14px'`, `gap: '12px'`, `marginTop: '4px'`, `padding: '12px 16px'`) instead of using the strict base-4px spacing tokens (`--spacing-4` to `--spacing-160`).
* **Section Gap Gaps**: Marketing bands on the landing page use custom pixel heights and vertical padding instead of the standard `--section-gap` (80px).

### Q6: List every page not yet migrated to Steep.
A true visual migration has not been completed on:
1. **Marketing Landing Page (`Landing.tsx`)**: Missing the peach-dawn radial backdrop, and the orbiting product preview cards are statically positioned with inline overrides.
2. **Auth & Registration Pages (`Login.tsx`, `Register.tsx`, `CandidateLogin.tsx`, `CandidateRegister.tsx`, `RecruiterLogin.tsx`, `RecruiterRegister.tsx`)**: Still use rectangular outlined inputs, ghost outlined buttons, and saturated red/green validation warnings.
3. **Verification Pages (`CandidateVerify.tsx`, `RecruiterVerifyEmail.tsx`)**: Missing monospace styled OTP code inputs, and using rectangular verification panels instead of the generous 24px cards.
4. **Candidate Dashboard (`CandidateDashboard.tsx`)**: Driven by inline style blocks, legacy colored progress bars, and multiple primary/secondary buttons.
5. **Recruiter Dashboard (`RecruiterDashboard.tsx`)**: Sidebar has hardcoded borders and widths, search bar is rectangular, and modals contain multiple button CTAs.
6. **Pipeline Board (`PipelineBoard.tsx`)**: Uses old card radii and inline colors for candidate stages; columns do not stack/scroll properly on smaller viewports.
7. **Candidate Directory (`CandidateDirectory.tsx`)** & **Resume Library (`ResumeLibrary.tsx`)**: Outlined textboxes and multiple button CTAs remain dominant.
8. **Interviews & Settings (`CandidateInterviews.tsx`, `RecruiterInterviews.tsx`, `RecruiterSettings.tsx`, `CandidateSettings.tsx`)**: driven by old UI structures, custom padding, and legacy colors.

---

## 2. Migration Matrix

| Current Component / Pattern | Current Style Source | Target Steep Style | Migration Status |
| :--- | :--- | :--- | :--- |
| **Secondary Outlined Button** | `index.css` (`.btn--secondary` with border, transparent bg) | **Text Link style**: No border, no background, Ink color text, underline on hover. Placed right of primary CTA. | **Pending Migration** |
| **Global Alert Banners** | `index.css` (`.banner--*` with saturated green, red, orange) | **Low-contrast desaturated text alerts**: Muted Sage green (success), Muted Terracotta/Rust (error), Muted Charcoal/Ash (warning). | **Pending Migration** |
| **Sidebar Navigation Container** | `AppLayout.tsx` & `CandidateLayout.tsx` inline (width: 260px, border-right, background: var(--bg)) | **Steep Sidebar**: Fog (`#f7f7f8`) background, `width: 240px`, **no border**, active item white card tile with `12px` radius. | **Pending Migration** |
| **Search Bar Input** | `AppLayout.tsx` inline style (`borderRadius: '0px'`) | **Steep Inputs Shape**: `16px` border-radius, Dove hairline border, Graphite placeholder. | **Pending Migration** |
| **Marketing Hero Layout** | `Landing.tsx` (static CTA group, custom gradients, unquoted variables) | **Peach-Dawn Radial Glow**: Centered over a soft radial apricot wash backdrop. Monumental Signifier display serif (`64px` h1), single Ink primary pill CTA paired with text link, and 4 orbiting floating white card tiles with signature three-layer shadows. | **Pending Migration** |
| **Dashboard KPI Cards** | `CandidateDashboard.tsx` & `RecruiterDashboard.tsx` (plain white cards, custom inline padding) | **Warm/Cool Data Cards**: Apricot Wash (`#fbe1d1`) or Sky Wash (`#d3e3fc`) backgrounds, `24px` radius, `20-24px` padding, signature `--shadow-subtle`. | **Pending Migration** |
| **Form Inputs & Textareas** | `index.css` & page files (standard input focus, varying border radius) | **Steep Inputs**: `16px` radius, 1px Dove border, Graphite placeholder, Rust focus shadow. | **Pending Migration** |
| **Status Badges & Monograms** | `index.css` & page-level inline styles (blue badges, Rust solid avatars) | **Pastel Monograms / Restrained Badges**: `9999px` radius, mint, sky, peach pastel backgrounds, Ink monograms. | **Pending Migration** |
| **Modals & Drawers** | `AppLayout.tsx` & page files (custom z-index cards, custom paddings, multiple buttons) | **Steep Modals**: Pure White cards, `24px` radius, single primary Ink CTA, secondary text link cancel. | **Pending Migration** |

---

## 3. Implementation Plan Overview

To address these findings and achieve a true design-system migration:
1. **Refactor Global CSS (`index.css`)**:
   * Re-define `.btn--secondary` globally as a borderless, backgroundless text link button with underline on hover, causing all outline/ghost buttons in the app to instantly migrate.
   * Re-define alert colors (`--success`, `--danger`, `--warning`) and banner classes to use desaturated, low-contrast, elegant daylight tones.
   * Enforce global Sohne text smoothing, `-0.009em` letter-spacing, and clear Signifier display serif rules.
2. **Rebuild Navigation Shells (`AppLayout.tsx` & `CandidateLayout.tsx`)**:
   * Implement a borderless, Fog-background sidebar navigation (`240px` wide).
   * Render the active indicator as a floating Pure White card tile with a `12px` radius.
   * Render the user avatar and monograms using soft pastel washes (mint/sky/peach) and Ink text.
   * Give the command-line search bar a smooth inputs shape (`16px` radius) and Dove hairline border.
3. **Refactor Marketing Hero (`Landing.tsx`)**:
   * Integrate the soft, warm Apricot Wash radial backdrop.
   * Orbit the Signifier headline with 4 fully responsive, absolutely positioned white card tiles featuring the signature three-layer shadow and pastel monograms.
   * Set sections to alternate between Pure White and Fog bands, separated by strict `--section-gap` spacing.
4. **Remove Component-Level Overrides & Apply Warm/Cool Tinting**:
   * Audit dashboards, forms, and tables to strip away custom padding/margin overrides and replace them with standard card paddings.
   * Style widgets using **Warm Data Cards** (Apricot Wash background) and **Cool Data Cards** (Sky Wash background) to bring the data grid to life.
   * Format all OTP text inputs as monospace Sohne characters with clean border-bottom outlines.
   * Wrap all tables in touch-scrollable `.table-wrap` panels to prevent responsive clipping.
