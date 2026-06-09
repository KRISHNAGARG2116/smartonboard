# Motion Excellence Report

This report outlines the animation principles, transition durations, and interaction motion targets for **SmartOnboard**, focusing on a premium, Stripe-like feel.

---

## 1. Core Motion Principles
- **Intentionality**: Motion must guide the user's attention, not distract. No heavy spring bounces, wiggles, or playful elastic effects.
- **Duration**: Transitions must fall strictly within the **200ms - 350ms** range.
- **Easing**: Smooth, accelerated starts and decelerated ends using standard cubic-bezier functions (e.g. `cubic-bezier(0.16, 1, 0.3, 1)` or `ease-out`).

---

## 2. Animation Categories & Gap Analysis

### Route Transitions
- **Current State**: Standard pages load immediately or have a simple 250ms opacity fade.
- **Steep Target**: Smooth entry/exit choreography using `<AnimatePresence>` and a combination of `opacity` and a subtle vertical shift (`translateY(12px)` to `0`).
- **Refinement Plan**: Update `<AnimatedPage>` to wrap all page routes with Framer Motion, utilizing:
  - `initial={{ opacity: 0, y: 10 }}`
  - `animate={{ opacity: 1, y: 0 }}`
  - `exit={{ opacity: 0, y: -10 }}`
  - `transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}`

### Hero reveals
- **Current State**: Static headline loading.
- **Steep Target**: Word-by-word staggered reveal and CTA fade-ins.
- **Refinement Plan**: Split the landing page hero text into individual words wrapped in `motion.span`, animate with `staggerChildren: 0.05` delay.

### Dashboard Entrances (KPI Cascade)
- **Current State**: Cards appear simultaneously with the page.
- **Steep Target**: Staggered, cascading card reveals that elevate the perceived performance of the app.
- **Refinement Plan**: Apply container-child staggered transitions to dashboard grid items, giving each card a `100ms` progressive delay.

### Sidebar Active State
- **Current State**: Instant tab highlight on click.
- **Steep Target**: Floating indicator background that slides smoothly from one menu option to another.
- **Refinement Plan**: Implement Framer Motion's `layoutId` on the active sidebar link indicator, enabling smooth morphing between nav clicks.

### Hover States (Micro-interactions)
- **Current State**: Basic CSS hover scale/shadow.
- **Steep Target**: Micro-lift (scale capped at `1.02`), soft shadow extension, and border highlights.
- **Refinement Plan**: Restrict all card hover scale limits to 1.02 with an ease-out transition.
