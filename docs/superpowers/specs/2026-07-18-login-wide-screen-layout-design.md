# Login Wide-Screen Layout Design

## Context

The login experience currently uses a fixed `1360px × 540px` content card. Browser measurements show that the card occupies about 35.4% of a `1920 × 1080` viewport and 19.9% of a `2560 × 1440` viewport. The fixed size leaves 280px side margins and a 176.5px card-to-footer gap at 1920px, increasing to 600px side margins and a 536.5px card-to-footer gap at 2560px.

## Goal

Make the login page feel proportionate and visually full on large desktop displays while preserving the approved 1440px desktop and mobile layouts.

## Approved Direction

Use a large-screen-only responsive enhancement. It activates only when both conditions are true:

- viewport width is at least `1500px`;
- viewport height is at least `900px`.

No authentication behavior, copy, carousel assets, Logo dimensions, form controls, colors, shadows, or mobile breakpoints will change.

## Layout Contract

### Page Grid

At the large-screen breakpoint, the page grid becomes:

```css
grid-template-rows: auto minmax(0, 1fr) auto;
```

The brand remains at the top, the login card is vertically centered in the flexible middle row, and the copyright remains in the bottom row. This distributes the remaining space above and below the card instead of placing nearly all of it between the card and footer.

### Login Card

The large-screen card uses:

```css
width: min(2080px, 100%);
height: clamp(560px, calc(100vh - 360px), 900px);
margin-top: 0;
align-self: center;
grid-template-columns: minmax(0, 1fr) clamp(560px, 34vw, 680px);
```

Expected geometry:

| Viewport | Card width | Card height | Approximate area coverage |
| --- | ---: | ---: | ---: |
| `1920 × 1080` | `1792px` | `720px` | 62% |
| `2560 × 1440` | `2080px` | `900px` | 51% |

The carousel absorbs most width growth. The form panel remains between 560px and 680px so fields stay readable and do not become excessively wide.

### Preserved Layouts

- At `1440 × 1024`, the existing `1360px × 540px` card and `36px` Logo top offset remain unchanged.
- At `390 × 844`, the existing stacked card, `78px` Logo, `20px` top offset, natural footer flow, and horizontal overflow behavior remain unchanged.

## Responsive Safety

- The large-screen rule requires both width and height, preventing short widescreen laptops from receiving a card that exceeds the viewport.
- Card width remains constrained by the page content box and a 2080px maximum.
- The carousel keeps `overflow: hidden`; the login panel keeps vertical scrolling available if browser zoom or translated copy increases content height.
- No fixed positioning is introduced.

## Verification

Automated Playwright coverage will verify:

- `1440 × 1024` and `390 × 844` retain their current geometry;
- `1920 × 1080` produces a `1792px × 720px` card;
- `2560 × 1440` produces a `2080px × 900px` card;
- large-screen card area coverage is at least 50%;
- the form panel remains between 560px and 680px;
- remaining vertical space is balanced above and below the card;
- all checked viewports have no card/footer overlap and no horizontal overflow.

Visual QA will capture the deployed state at `1920 × 1080`, plus regression views at `1440 × 1024` and `390 × 844`, and compare the large-screen before/after screenshots together.

## Out Of Scope

- Changing the Logo size or product title.
- Replacing carousel images or changing carousel timing.
- Redesigning the login form, roles, CAPTCHA, password controls, or footer.
- Changing authenticated student, teacher, or administrator pages.
