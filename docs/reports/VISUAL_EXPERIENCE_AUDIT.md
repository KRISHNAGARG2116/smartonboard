# Visual Experience Audit

This audit evaluates the visual hierarchy, focal points, layout density, and whitespace composition of **SmartOnboard** compared to Steep-level design benchmarks.

---

## 1. Landing Page Visual Composition
- **Focal Point**: The headline and the call-to-action (CTA) buttons are the primary focal points, but they are nested in a generic layout that lacks product visuals on the homepage.
- **Eye Flow**: The user reads the title, looks at the CTAs, and then immediately scrolls into feature text cards that look like static lists. The eye is not led naturally down a product story.
- **Whitespace**: Spacing is present but feels accidental rather than intentional (loose margins, basic grid columns).
- **Recommendation**: Create a central product showcase below the hero featuring overlapping, interactive mockups of the recruiter candidate board and pipeline.

---

## 2. Authentication Screens (`/login`, `/register`, etc.)
- **Focal Point**: The central login card.
- **Eye Flow**: Simple and direct. Centered input fields draw attention immediately.
- **Whitespace**: Balanced but could be refined by introducing a max-width container and soft backdrop glows (glassmorphism/gradient mesh) to anchor the card.
- **Recommendation**: Add a subtle radial gradient backdrop that transitions smoothly between themes, and replace standard inputs with border-bottom fields mapping strictly to design system variables.

---

## 3. Recruiter Dashboard (`/recruiter/dashboard`)
- **Focal Point**: The top row of numeric KPI metrics.
- **Eye Flow**: Horizontal flow across metrics, then vertical down candidate listings.
- **Whitespace**: Spacing between card groups is slightly irregular. Card margins feel tight in some places and empty in others (especially under list feeds).
- **Recommendation**: Standardize grid gap spacing to exactly `var(--space-6)` (24px). Align cards cleanly and use card borders matching the dark/light design system tokens.

---

## 4. Candidate Dashboard (`/candidate/dashboard`)
- **Focal Point**: Profile completion percentage circle/status block.
- **Eye Flow**: Scanning the checklist on the left, then resumes on the right.
- **Whitespace**: The right column feels detached when there is only one resume. It leaves a large void at the bottom right.
- **Recommendation**: Introduce card-group containers to frame the columns. Add a subtle, styled background wash to separate interactive sections from the page canvas.

---

## 5. Spacing & Margin Consistency Audit
- **Standardized Spacing scale**:
  - Main outer page gutters: `var(--space-6)` (24px) or `var(--space-8)` (32px).
  - Component gaps: `var(--space-4)` (16px) or `var(--space-5)` (20px).
  - Grid structures: `var(--space-6)` (24px).
- **Current Deviations**:
  - Several custom margins in pages (e.g. `29px` headers, `4px` margins) need to be cleaned up or mapped directly to design-system typography variables.
