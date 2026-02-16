# Header Reposition Hover Control Design

Date: 2026-02-16
Project: Reflex AI Lead Enrichment
Scope: Header image reposition UX refinement in desktop view

## Objective

Refine the header image reposition interaction so it behaves predictably and matches expected UX:

- Reposition controls must stay anchored in the top-right corner of the header image.
- Slider visual style must use neutral gray tones.
- `Reposition` button appears only while hovering the header image area.
- `Reposition` button auto-hides when cursor leaves the header image area.
- Reposition controls are not shown on mobile/touch layouts.

## Recommended Approach (Approved)

Use a single anchored control system in the header image container:

1. Keep one relative-positioned image stage (`header_image_stage`).
2. In non-edit mode, show a hover-triggered `Reposition` button at top-right.
3. In edit mode, replace button with a fixed top-right panel containing gray slider + `Done`.
4. Preview image movement live while dragging slider via `temp_header_position`.
5. Save final value into `header_position` on `Done`.

This approach is minimal, predictable, and avoids extra state complexity.

## Component Architecture

Target file: `reflex_app/ui/components/header.py`

- `project_header()` keeps the current header structure and owns the interactive image container.
- `reposition_controls()` renders one of two views:
  - Idle view: hover-only `Reposition` trigger.
  - Active view: anchored control panel with slider + `Done`.
- Header image remains `object_fit="cover"` and uses dynamic `object_position` from state.

Placement rules:

- All reposition UI is absolutely positioned inside the same relative image container.
- Anchor location is always top-right to prevent center drift.

## State and Data Flow

Target file: `reflex_app/state.py`

Existing state is sufficient:

- `header_reposition_mode: bool`
- `header_position: int`
- `temp_header_position: int`

Event flow:

1. Hover header image -> idle `Reposition` trigger becomes visible.
2. Click `Reposition` -> `enter_reposition_mode()`.
3. Drag slider -> `set_temp_header_position()` updates `temp_header_position` (clamped 0..100).
4. Image preview updates in real time using `temp_header_position`.
5. Click `Done` -> `save_reposition()` commits value to `header_position` and exits edit mode.

## Visual Design

Slider and control panel should adopt neutral grays:

- Rail (inactive): light gray
- Rail (active): medium/dark gray
- Thumb: white with subtle gray border
- Panel background: light neutral surface with soft border/shadow

No accent blue is used in reposition controls.

## Interaction Rules

- Desktop:
  - Non-edit mode: control is hover-only and auto-hides on mouse leave.
  - Edit mode: slider panel remains visible until `Done`.
- Mobile/touch:
  - Reposition controls hidden entirely (no hover dependency).

## Error Handling and Edge Cases

- Invalid slider payloads are ignored safely (already handled by parser in `set_temp_header_position`).
- Slider values are clamped to 0..100 to avoid out-of-range object positioning.
- Fast hover changes do not affect active edit session because active panel is not hover-gated.
- No change to dark mode toggle behavior or overlay behavior.

## Testing Plan

Manual acceptance checks:

1. Hover inside header image (desktop) -> `Reposition` appears at top-right.
2. Move cursor out of image (desktop) -> `Reposition` disappears.
3. Click `Reposition` -> slider panel appears at top-right, not center.
4. Drag slider -> image position updates live.
5. Slider visual style appears gray as specified.
6. Click `Done` -> edit mode exits and value persists.
7. On mobile width -> no reposition controls are shown.

## Out of Scope

- Mobile gesture-based reposition.
- Persisting header position outside current session.
- Additional animation layers beyond basic transition.
