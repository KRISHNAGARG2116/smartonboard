# Design System Interpretation Report

This report outlines the core visual, layout, and component philosophy defined in the Steep Design System.

---

## 1. Visual DNA & Color Philosophy
The design system operates on an **achromatic daylight canvas** styled with selective spot-color punctuation:
- **Canvas (`--color-pure-white`)**: The primary background for elevated workspace blocks.
- **Fog (`--color-fog`)**: The daylight secondary background canvas. Used on sidebar panels and section backgrounds.
- **Ink (`--color-ink`)**: Primary text, dark buttons, and solid CTA surfaces.
- **Restrained Chromatics**: The only accent color is Rust (`#5d2a1a` / `--color-rust`). Warm Apricot Wash (`#fbe1d1` / `--color-apricot-wash`) and cool Sky Wash (`#d3e3fc` / `--color-sky-wash`) are reserved exclusively for data viz chart cards.

---

## 2. Typography Philosophy
The system defines a dual-font configuration:
- **Serif Display (`--font-signifier`)**: Used only for large titles ($\ge$ 44px) to establish an editorial editorial voice. It must never be used for body, label, or form text.
- **Sans UI (`--font-sohne`)**: The workhorse for all data panels. It utilizes precise micro-weights (430, 450, 480, 500) to create granular data weight distinctions instead of coarse bolding.
- **Tracking & Leading**: Text elements are set with tight letter-spacing (`-0.009em` for Sohne, `-0.025em` for Signifier $\ge$ 64px) to feel crisp and refined.

---

## 3. Shapes, Spacing & Shadows
- **Ceramic Card Radius**: Cards use a `24px` border radius (`--radius-cards`), buttons and pills use a `9999px` radius (`--radius-buttons`), and inputs use `16px` (`--radius-inputs`).
- **Signature Elevation**: The shadow must be structured as a 3-layer shadow: a 1px ink-tinted border outline + a soft 20px/25px drop + a micro 8px/10px drop.
- **Layout Rhythm**: Comfortable spacing using a 4px base unit (standard paddings: 20px and 24px).

---

## 4. Component Rules (Do's & Don'ts)
- **Filled Dark CTA**: Only one filled dark button per screen maximum, paired with a text-link secondary action on its right.
- **Radii Consistency**: No sharp corners below 12px for content structures.
- **Delineation**: Avoid borders heavier than 1px. Delineate sections via surface contrast and spacing.
