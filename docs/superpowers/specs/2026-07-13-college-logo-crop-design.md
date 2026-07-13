# College Logo Crop Design

## Goal

Remove the excessive white margins embedded in `public/college-logo.jpg` so the Hunan University College of Civil Engineering crest appears centered, complete, and visually prominent wherever the shared asset is used.

## Scope

- Crop only the uniform outer white area from the source image.
- Preserve the complete crest, including the top border pattern, side ornaments, English ring text, and the `1903` ribbon.
- Keep approximately 3% white safety space around the visible crest.
- Produce a square image centered on the crest so circular containers crop evenly.
- Remove the login-page CSS compensation that currently enlarges the image with `transform: scale(1.35)`.
- Keep the existing desktop and mobile logo container dimensions unchanged.

## Implementation

1. Create a tightly cropped square replacement for `public/college-logo.jpg` from the current official source image.
2. Render the image with `object-fit: contain` and no transform in the login logo container.
3. Reuse the same asset automatically in the login page, portal shell, and password change gate.

## Verification

- Confirm the cropped image is square and the full crest remains visible.
- Run the login-page component tests and production build.
- Inspect desktop and mobile screenshots for centering, clipping, and visual size.
- Confirm no horizontal overflow or layout shift is introduced.

## Non-goals

- Do not redraw, recolor, sharpen, or otherwise alter the official crest.
- Do not change login-page spacing, typography, carousel, or form layout.
