# Steep.app Experience Reconstruction & Visual Benchmarking Report

This report compares **SmartOnboard** screens side-by-side against **Steep.app** design principles, answers the 5 visual perception questions for each screen, and outlines our prioritized plan of 25 visual improvements.

---

## 1. Side-by-Side Visual Comparison & Perception Answers

### 1.1 Landing Page
- **Why does Steep feel better?**
  Steep's hero section immediately captures attention using monumental serif text (Signifier) centered over a warm, daylight radial glow. Below the hero is a large, high-fidelity visual preview of the actual dashboard workspace.
- **What is visually missing?**
  A central product showcase anchor. SmartOnboard's landing page uses standard sans-serif titles that do not project the editorial voice of the Signifier serif.
- **What is structurally missing?**
  A logical storytelling sequence that leads the user from problem (applicant noise) to solution (verification & signal matching).
- **What is compositionally missing?**
  Rhythm. The gaps between columns and feature grids are uniform and lack variation in density.
- **What is emotionally missing?**
  A sense of trust and sophistication. It looks like a SaaS template rather than a premium, daylight product workspace.

### 1.2 Recruiter Dashboard
- **Why does Steep feel better?**
  The dashboard feels like an organized command center. Metric cards stand out clearly on an off-white background canvas, and data is grouped in compact widgets with clean hairline borders.
- **What is visually missing?**
  Legibility and contrast. Text in selected queue rows, skill chips, and the AI Copilot title is completely invisible or washed out in light mode.
- **What is structurally missing?**
  A functional form presentation. Input fields in modals are white-on-white, making them look like blank holes.
- **What is compositionally missing?**
  Density. Gaps between metrics and columns are loose, creating dead zones.
- **What is emotionally missing?**
  Authority. The interface feels static and flat due to invisible selected states and text elements.

### 1.3 Candidate Dashboard
- **Why does Steep feel better?**
  It is clear, direct, and has generous rounded corners (`24px`) that make elements feel physical and premium.
- **What is visually missing?**
  Action clarity. The primary buttons (Resolve) are black rectangles with invisible text.
- **What is structurally missing?**
  A clean checklist status presentation. Checklist lines are plain border boxes rather than interactive status modules.
- **What is compositionally missing?**
  Balance. When resumes are absent, the right-side column displays large blank zones.
- **What is emotionally missing?**
  High trust. It lacks the verified, signal-first vibe due to unreadable action items.

---

## 2. Ranked List of 25 Highest-Impact Visual Improvements

Ranked by: **Expected Visual Impact ÷ Implementation Effort**

1. **Fix invisible text on primary buttons** (Change text color of `var(--color-dark-cork)` background buttons to `var(--color-pure-white)`).
   - *Impact*: Extremely High | *Effort*: Low | *Score*: 10.0
2. **Fix white-on-white modal inputs** (Update `.form-input`, `.form-select`, `.form-textarea` in `index.css` to use `var(--text)` for text and `var(--color-dove)` for borders in light mode).
   - *Impact*: Extremely High | *Effort*: Low | *Score*: 10.0
3. **Fix invisible text in selected table rows** (Change text color of selected rows to white or use a soft selection background like `rgba(93, 42, 26, 0.08)`).
   - *Impact*: Extremely High | *Effort*: Low | *Score*: 9.8
4. **Fix invisible AI Copilot Command Hub header** (Set header text to `var(--text)` instead of white).
   - *Impact*: High | *Effort*: Low | *Score*: 9.5
5. **Fix invisible skills chips text** (Change skill chip text color to `var(--text)` or `var(--color-rust)`).
   - *Impact*: High | *Effort*: Low | *Score*: 9.5
6. **Standardize Card Shadows & Hairlines** (Apply 3-layer `var(--shadow-subtle)` and `1px solid var(--border)` to all cards for physical depth).
   - *Impact*: High | *Effort*: Low | *Score*: 9.2
7. **Pill-shaped CTA buttons across all dashboards** (Ensure all dashboard and layout buttons use `var(--radius-buttons)`).
   - *Impact*: High | *Effort*: Low | *Score*: 9.0
8. **Stat Delta Badge polish** (Convert green/red status badges to outline pill shapes with light background and colored labels).
   - *Impact*: Medium | *Effort*: Low | *Score*: 8.8
9. **Dashboard cascade entrance animations** (Stagger metric card and widget reveals on entry with Framer Motion).
   - *Impact*: High | *Effort*: Medium | *Score*: 8.5
10. **Dense table row padding** (Tighten table padding to fit more applicant and job entries on screen).
    - *Impact*: Medium | *Effort*: Low | *Score*: 8.5
11. **MX warning banner redesign** (Make organization MX warnings a low-opacity status block instead of a heavy banner).
    - *Impact*: Medium | *Effort*: Low | *Score*: 8.5
12. **Workspace Switcher Dropdown** (Style company selectors as floating popover cards rather than native select fields).
    - *Impact*: Medium | *Effort*: Low | *Score*: 8.0
13. **Card hover lift transitions** (TranslateY cards by -2px on hover with ease-out transition).
    - *Impact*: Medium | *Effort*: Low | *Score*: 8.0
14. **Clean Outline Sidebar Icons** (Use consistent outline monochrome icons with a 1.5px stroke weight).
    - *Impact*: Medium | *Effort*: Low | *Score*: 8.0
15. **Soft peach radial hero glow** (Refine landing hero background with a soft peach glow gradient).
    - *Impact*: High | *Effort*: Medium | *Score*: 7.8
16. **Input fields corner radii standardization** (Ensure all input fields are standardized to exactly 16px radius).
    - *Impact*: Medium | *Effort*: Low | *Score*: 7.8
17. **Achomatic auth forms** (Ensure login and registration use white cards, light-grey borders, and pill buttons).
    - *Impact*: Medium | *Effort*: Low | *Score*: 7.5
18. **Pipeline column solid borders** (Verify Kanban columns and candidate cards use solid borders rather than dashed lines).
    - *Impact*: Medium | *Effort*: Low | *Score*: 7.5
19. **Avatar initials badge formatting** (Ensure all user monograms are perfectly circular with custom pastel fills).
    - *Impact*: Medium | *Effort*: Low | *Score*: 7.2
20. **Interactive product previews centering** (Center the mockup candidate checklists and kanban boards).
    - *Impact*: Medium | *Effort*: Medium | *Score*: 7.0
21. **Uniform spacing scale usage** (Clean up inline margin/padding overrides to align strictly to the 4px-base scale).
    - *Impact*: Medium | *Effort*: Low | *Score*: 7.0
22. **Empty state vector illustration refinement** (Re-draw/simplify SVG lines in empty states to match outline strokes).
    - *Impact*: Medium | *Effort*: Medium | *Score*: 6.5
23. **Chart tooltip outline borders** (Style Recharts tooltips with 1px solid borders and white background).
    - *Impact*: Low | *Effort*: Low | *Score*: 6.0
24. **Word-by-word Title reveals** (Refine staggered word reveals on landing display headings).
    - *Impact*: Medium | *Effort*: Medium | *Score*: 6.0
25. **Sidebar active-tab indicator transitions** (Animate active indicators using framer-motion layoutId).
    - *Impact*: Medium | *Effort*: Medium | *Score*: 5.5
