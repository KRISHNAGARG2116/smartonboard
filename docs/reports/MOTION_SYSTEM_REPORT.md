# Motion System Report

**Audited By:** SmartOnboard Brand Systems Subagent  
**Status:** ✅ IMPLEMENTED  
**Date:** 2026-06-07  

---

## 1. Executive Summary

This report covers the motion system, page transitions, entrance animations, and interactive state triggers configured in the **SmartOnboard** frontend application. Built on top of **Framer Motion**, the motion guidelines focus on subtle, purposeful transitions that guide the user's attention without introducing visual noise or slowing down workflows.

---

## 2. Page Transition Engine

Standard layout routes utilize a dedicated wrapper element to animate page entrances:
* **File Reference:** [AnimatedPage.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/AnimatedPage.tsx)
* **Animation Sequence**:
  * **Initial state**: `opacity: 0`, translated `10px` down along the Y-axis.
  * **Entrance transition**: Smoothly interpolates to `opacity: 1` and `y: 0`.
  * **Exit transition**: Fades out to `opacity: 0` while translating `-10px` up.
  * **Duration & Easing**: `0.25` seconds with `easeOut` curve for a snappy, responsive feel.
  ```typescript
  // AnimatedPage.tsx:L10-15
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -10 }}
    transition={{ duration: 0.25, ease: 'easeOut' }}
  >
  ```

---

## 3. Scroll-Linked Viewport Animations

Marketing sections and data representations on the main landing page load dynamically as the user scrolls:
* **File Reference:** [Landing.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/pages/Landing.tsx)
* **Behavior**: Uses the `whileInView` and `viewport` configurations of Framer Motion.
* **Settings**:
  ```typescript
  initial={{ opacity: 0, y: 30 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true, margin: '-100px 0px' }}
  transition={{ duration: 0.6, ease: 'easeOut' }}
  ```
* **Impact**: Elements fade and slide up into place only when they are at least `100px` within the viewport boundaries, ensuring the initial render is lightweight while scroll interaction feels organic.

---

## 4. Staggered Row Entrances

To make listings feel tactile and responsive, grid rows stagger their entry:
* **File Reference:** [DataTable.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/DataTable.tsx#L4-L15)
* **Animation Pattern**:
  ```typescript
  const rowVariants = {
    hidden: { opacity: 0, y: 5 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: {
        delay: Math.min(i * 0.03, 0.3),
        duration: 0.2,
        ease: 'easeOut'
      }
    })
  }
  ```
* **Impact**: Rows incrementally cascade (staggered by `30ms` per item up to a cap of `300ms`), preventing the layout from flashing all rows at once.

---

## 5. Dynamic Metric Counters

Numerical indicators (e.g. applicability matching scores, pipeline metrics) animate values incrementally upon entering the viewport:
* **File Reference:** [AnimatedCounter.tsx](file:///Users/krishnagarg/smartonboard-main/frontend/src/components/AnimatedCounter.tsx)
* **Mechanism**:
  1. Component receives raw value inputs (e.g. `98.5%` or `14 days`).
  2. Extracts the numeric component and trailing/leading symbols or labels via regex.
  3. Uses `useInView` to detect if the element is visible.
  4. Triggers `animate(0, numericValue)` using a `duration` of `0.8s` and `easeOut` interpolation.
  5. Dynamically updates text nodes to display decimal points or whole numbers.

---

## 6. Micro-Interactions & Hover Feedback

* **Primary CTAs & Ghost Cards**: Use spring scaling for responsive click/tap feedback:
  ```typescript
  whileHover={{ scale: 1.02 }}
  whileTap={{ scale: 0.98 }}
  ```
* **CSS Transitions**: Standard hover effects (color fills, border colors, icons) use utility variables:
  ```css
  /* index.css */
  transition: color var(--duration-fast), border-color var(--duration-fast);
  ```

---

## 7. Accessibility & Reduced Motion

SmartOnboard honors user operating system preferences for reduced motion. Global stylesheets include overrides to bypass layout animations:
* **File Reference:** [index.css](file:///Users/krishnagarg/smartonboard-main/frontend/src/index.css#L165-L173)
* **CSS Definition**:
  ```css
  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }
  ```

---

*End of Report*
