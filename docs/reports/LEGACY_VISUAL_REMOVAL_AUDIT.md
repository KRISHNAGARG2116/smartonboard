# Legacy Visual Removal Audit

This audit identifies all hardcoded design system overrides, legacy layout choices, and incorrect styling tokens embedded in **SmartOnboard**'s components that prevent the visual design system from fully controlling the user experience.

---

## 1. Hardcoded Border Radii Overrides (Legacy Card & Button Styles)
Steep defines a strict hierarchy of radii: `24px` for cards, `9999px` for buttons and tags, and `16px` for inputs. 
We identified multiple instances of legacy hardcoded overrides:
- **Recruiter App Shell (`AppLayout.tsx`)**:
  - Filled buttons hardcoded to `borderRadius: '36px'` or `22.5px'` instead of `var(--radius-buttons)`.
  - Top header elements and sub-cards using `borderRadius: '12px'` or `8px'` instead of `var(--radius-cards)`.
- **Candidate App Shell (`CandidateLayout.tsx`)**:
  - Sidebar profile marks using `borderRadius: '0px'`.
  - Navigation buttons using custom radii overrides.
- **Candidate Profile (`CandidateProfilePage.tsx`)**:
  - Action buttons set to `borderRadius: '36px'` and `borderRadius: '22.5px'`.
- **Pipeline Board (`PipelineBoard.tsx`)**:
  - Kanban columns and candidate cards hardcoded to `12px` or `8px` corners.

---

## 2. Legacy Spacing, Gaps & Spacing Overrides
- Multiple components utilize arbitrary margins (e.g. `marginBottom: '4px'`, `marginTop: '6px'`) rather than aligning strictly to the 4px-base spacing scale (`var(--space-1)` through `var(--space-20)`).
- We must replace these hardcoded values with spacing tokens to create a balanced layout hierarchy.

---

## 3. Legacy Shadows & Flat Indicators
- Several cards use `boxShadow: 'none'` inline overrides, which makes them feel like flat gray wireframes. They should use the design system's signature 3-layer shadow (`var(--shadow-subtle)`).

---

## 4. Execution Plan
1. **Remove hardcoded `borderRadius` values** for all buttons, changing them to `var(--radius-buttons)` or deleting them so the base `.btn` CSS style takes over.
2. **Remove hardcoded `borderRadius` values** for cards, aligning them to `var(--radius-cards)` or letting `.card` style them.
3. **Restore default shadows** by removing `boxShadow: 'none'` from cards, letting the design system's `.card` shadow take effect.
