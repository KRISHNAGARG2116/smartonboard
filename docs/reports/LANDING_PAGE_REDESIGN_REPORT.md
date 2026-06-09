# Landing Page Redesign Report

This report outlines the structural, storytelling, and visual modifications to transform the **SmartOnboard Landing Page** from a simple template into a premium product showcase.

---

## 1. Storytelling Flow
The landing page will be restructured into a chronological product story:
1. **Hero**: Word-by-word headline reveal, staggered CTA buttons, and subtle animated background blobs.
2. **Product Previews (Recruiter & Candidate Dashboards)**: Overlapping visual showcases of the recruiter dashboard and the candidate dashboard.
3. **Verified Hiring Loop (How it works)**: A step-by-step interactive workflow visualization explaining the verified loop (Verification -> Match -> AI Queue -> Hired).
4. **Features Grid**: A premium grid with card hover micro-lifts mapping to design system metrics.
5. **Candidate Journey**: Highlight of verified credentials, matching percentage, and resume library.
6. **Recruiter Journey**: Highlight of risk scores, authenticity metrics, and executive analytics.
7. **Final Call-to-Action**: Generous spacing, high-contrast CTA card.

---

## 2. Interactive Product Previews
Since the recruiter and candidate portals are protected by authentication, we will build **interactive CSS/React mockups** directly on the landing page so unregistered guests can visually explore the product surfaces.
- **Recruiter Mockup**: Displays a simulated candidate pipeline board, an AI Queue risk summary widget, and a small key metrics panel (Open Jobs: 12, Matches: 85%).
- **Candidate Mockup**: Displays a profile completion checklist, verified credentials badges, and a resume match rate indicator (e.g., "React Developer Match: 94%").

---

## 3. Motion & Micro-interactions
- **Headline Stagger**: Words fade in from `y: 20px` to `y: 0` with a 50ms stagger.
- **CTA Reveal**: Delay of 400ms before CTAs fade in smoothly.
- **Background Blobs**: Floating, blurred gradient meshes animating slowly in the background to create depth.
- **Mockup Entrances**: Previews slide up on scroll using scroll-reveal transitions.
