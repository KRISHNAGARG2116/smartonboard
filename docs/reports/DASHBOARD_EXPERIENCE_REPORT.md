# Dashboard Experience Report

This report outlines the visual structure, layout density, and interactive improvements planned for the recruiter and candidate dashboards to create a premium command center experience.

---

## 1. Recruiter Command Center (`/recruiter/dashboard`)
The recruiter dashboard should feel like a sophisticated, high-trust command center for managing applications.
- **Metric Cards Grouping**: We will wrap the KPI stats in unified cards with subtle, crisp borders. Font sizes for numbers will be increased to `var(--text-heading-sm)` (26px) with a semi-bold weight.
- **Density & Spacing**: Adjust card padding to exactly `var(--spacing-20)` (20px) and grid gaps to `24px` to improve visual scan speed.
- **Card Hover States**: Cards will gently lift on hover (scale up to `1.015`, translateY by `3px`) and their border will darken slightly.
- **Entry cascade**: KPI cards and candidate feeds will stagger-fade on route entry.

---

## 2. Candidate Workspace (`/candidate/dashboard`)
The candidate workspace should feel simple, high-trust, and clear, helping candidates verify their skills.
- **Profile Completion Visuals**: Emphasize the matching skills / missing skills section with cleaner badge chips.
- **Grid Layout**: Structure the page with a clean, two-column layout that remains solid on all screen sizes.
- **Empty State Polish**: When no interviews or applications exist, display a unified empty-state card with custom SVG brand-aligned icons.
- **Entry cascade**: Slide in the main sections sequentially from `translateY(12px)` to `0`.
