# Motion Visual Evidence — Experience Polish Report

This report documents the motion design system of **SmartOnboard**, verifying that visual interactions feel premium, responsive, and editorial. We avoid bouncy animations, opting instead for Steep's signature transition curve (`cubic-bezier(0.16, 1, 0.3, 1)`) and precise cascade reveals.

---

## 1. Verified Motion Categories & Implementation Evidence

### 1.1 Route Transitions
- **Implementation**: Managed globally in [App.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/App.tsx) and layouts using `<AnimatePresence mode="wait">` and wrapping elements with the [AnimatedPage](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/AnimatedPage.tsx) component.
- **Visual Behavior**: When navigating, the active page exits by fading and shifting `8px` upwards. The new page enters from `y: 8` to `0` with a soft opacity fade over `300ms` using the custom easing curve.
- **Evidence**: Captured across all page transitions during the automated screenshot audit.

### 1.2 Dashboard Loading
- **Implementation**: Utilizes custom [Skeletons.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/Skeletons.tsx) (e.g. `KpiCardSkeleton`, `ListRowSkeleton`).
- **Visual Behavior**: Elements feature a soft, continuous opacity pulse animation (`@keyframes pulse` from 60% to 30% opacity) that settles immediately when real data hooks resolve, preventing sudden layout shifts.
- **Evidence**: Observed during API fetch delays in Recruiter and Candidate dashboard loads.

### 1.3 Landing Page Scrolling
- **Implementation**: Reconstructed in [Landing.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/Landing.tsx) using Framer Motion's `whileInView` and `viewport={{ once: true }}` triggers.
- **Visual Behavior**: 
  - Hero Display Title: Staggered word-by-word reveal (each word has a `40ms` offset delay).
  - Workflow steps and showcase cards slide up by `15px` and fade in as they cross the viewport threshold (margin `-50px`), creating a natural storytelling flow.
- **Evidence**: Visible in [public_landing_after.png](file:///Users/krishnagarg/smartonboard-main/docs/reports/ui-after/public_landing.png) where parallax mesh gradient blobs float behind sections.

### 1.4 Sidebar Navigation Changes
- **Implementation**: Configured in sidebar layouts using CSS transitions for active state classes.
- **Visual Behavior**: Clicking nav tabs triggers a smooth transition (`transition: background var(--duration-fast), color var(--duration-fast)`) that shifts the active indicator background subtly without harsh flashing or jumping.
- **Evidence**: Observed in Recruiter and Candidate layout navigations.

### 1.5 KPI Card Entrances
- **Implementation**: Wrapped in staggered Framer Motion containers in [RecruiterDashboard.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/recruiter/RecruiterDashboard.tsx) and [CandidateDashboard.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/candidate/CandidateDashboard.tsx).
- **Visual Behavior**: KPI blocks do not render simultaneously; they cascade sequentially with a `50ms` progressive delay per card, sliding up from `y: 10` to `0`.
- **Evidence**: Dashboard KPI panels render with a visible sequential fade-in waterfall.

### 1.6 Table Row Entrances & Hovers
- **Implementation**: Implemented via CSS transition classes on tables in [index.css](file:///Users/krishnagarg/smartonboard-main/frontend/src/index.css) (`.data-table tbody tr`).
- **Visual Behavior**: 
  - Hovering a candidate row applies a soft grey-blue highlight (`background: var(--accent-subtle)`) with a `150ms` ease-out transition.
  - Selecting a row transitions the background highlight smoothly.
- **Evidence**: Checked inside the Recruiter Candidate list and Job openings lists.

### 1.7 Empty-State Transitions
- **Implementation**: Structured inside the [EmptyState.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/EmptyState.tsx) component.
- **Visual Behavior**: Vector graphics and action prompts fade in gently when collections are empty, ensuring a soft reveal rather than a harsh layout snap.
- **Evidence**: Visible when loading an empty jobs list or interviews queue.
