# RR3 Debug Overlay

Floating debug overlay for Real Racing 3. Injects as a dylib via Sideloadly, provides an in-game toggle panel for engine debug flags and a live tweakable variable browser with read/write access to ~847 engine variables across 15 categories.

## Features

- Draggable floating "RR3" button (tap to open, drag to reposition)
- 8 BSS debug flag toggles (ImGui, Cheat Menu, Debug Render, etc.) with "ALL ON" quick-enable
- **Live tweakable browser** — reads the runtime BSS vector at startup, dynamically groups entries by `TWEAKABLE_` prefix into 15 categories
- **Smart control selection:**
  - `UISwitch` for type=2 (bool) entries
  - `UISwitch` for type=1 (int) entries detected as bool-like by name heuristic (see below)
  - `UISlider` for all other int/float/double entries, with min/max from entry metadata
- **Real-time value editing** — writes through the entry's live variable pointer (`+0x48`), also updates the value cache at `+0x40`
- **Per-category RESET** — restores all values to their compiled defaults from `+0x60`
- **117 human-readable descriptions** for known tweakables (shown as subtitles)
- **Pretty names** — `MAX_SPEED_KPH` → "Max Speed KPH" (auto-generated for entries without descriptions)
- **Diagnostic dump** — writes `Documents/tweakable_dump.txt` at startup with all entries grouped by category

## Bool-Like Detection (`isBoolLike`)

Many int-typed entries (type=1) are actually on/off toggles stored as 0/1. The overlay detects these by name to show a `UISwitch` instead of a slider with a -100..100 range.

**Positive patterns** (→ toggle):
- Suffix `_ENABLED`, contains `ENABLE_`, `_CAN_`, `_USE_`
- Prefix `TWEAKABLE_SHOW_`, `TWEAKABLE_ALLOW_`, `TWEAKABLE_RENDER_`, `TWEAKABLE_DEBUGRENDER_`, `TWEAKABLE_HUD_`
- 20 specific known names (e.g. `AI_RUBBER_BANDING`, `DRIFT_ENABLED`, `PAUSE_BLUR`)

**Negative patterns** (checked first — override positives → slider):
Names containing `_AMOUNT`, `_SCALE`, `_SIZE`, `_POSITION`, `_ANGLE`, `_FALLOFF`, `_CENTRE`, `_CENTER`, `_RATE`, `_THRESHOLD`, `_DELAY`, `_ZOOM`, `_FOV`, `_TILT`, `_OFFSET_`/`_OFFSET` (suffix), `_WIDTH`, `_HEIGHT`, `_MAX_`, `_MIN_`, `_TO_RENDER`

This prevents numeric RENDER/DEBUGRENDER/HUD sub-entries (e.g. `RENDER_DISTORT_VIGNETTE_FALLOFF`, `RENDER_LENS_FLARE_BLOOM_PEAK_SIZE`, `DEBUGRENDER_CAR_BOUNDS_Z_OFFSET`, `HUD_EXTERNAL_PLANE_OFFSET_HEIGHT`) from getting toggles.

## Tweakable Entry Layout (0x78 = 120 bytes)

Reverse-engineered from the setter at `0x1000314c0` and init at `0x100047458`:

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| +0x00 | 4 | uint32 ID | Sequential, 0-based |
| +0x08 | 24 | SSO name | libc++ SSO: byte[23] high bit clear = inline ≤22 chars, set = heap {ptr, size, cap} |
| +0x20 | 4 | Type tag | 0=string, 1=int, 2=bool, 3=double, 4=float |
| +0x28 | 24 | SSO label | Often empty |
| +0x40 | 8 | Value cache | Current value (written by setter) |
| +0x48 | 8 | void* live ptr | Pointer to actual game variable — write through this to modify state |
| +0x50 | 8 | Min value | INT_MIN for int entries (clamped to -100 in UI) |
| +0x58 | 8 | Max value | INT_MAX for int entries (clamped to 100 in UI) |
| +0x60 | 8 | Default value | Used by per-category RESET |

## Categories (15)

| Category | Description |
|----------|-------------|
| AI | Opponent behavior, rubber banding, difficulty |
| CAMERA | FOV, chase cam, photo mode, free orbit |
| CAR | Override speed/weight, damage, draft |
| DAMAGE | Player/AI damage, visual damage |
| DEBUGRENDER | Collision bounds, splines, suspension, forces |
| DRIFT | Drift mode, scoring, multipliers |
| HUD | Debug planes, safe areas, input overlay |
| INPUT | Vibration, tilt sensitivity |
| NETWORK | Profiling, latency |
| PARTICLE | Scale, FX toggle |
| PHYSICS | Tire grip, suspension, aero |
| PVS | Potentially Visible Set debug, fade test |
| RENDER | 68 entries — wireframe, shadows, lens flare, distortion, sky, post-FX |
| SOUND | Volume, 3D audio |
| (Other) | Uncategorized entries |

## Build

Compiled on jailbroken iPhone SE (iOS 15.5) with clang-16:

```bash
clang-16 -arch arm64 -dynamiclib \
    -framework UIKit -framework Foundation -framework CoreGraphics \
    -isysroot /path/to/iPhoneOS.sdk \
    -o rr3_overlay.dylib rr3_overlay.m \
    -install_name @rpath/rr3_overlay.dylib \
    -fobjc-arc -Os -miphoneos-version-min=15.0
```

## Inject

Use Sideloadly's "Inject dylibs/frameworks" option:
1. Select the target IPA (e.g., `rr3_4k_v3.ipa`)
2. Advanced Options → Inject dylibs
3. Add `rr3_overlay.dylib`
4. Sideload to device
5. Wait ~11s after launch for the overlay button to appear (8s for BSS vector read + 3s for UI init)

## BSS Debug Flag Addresses

| VA | Flag | Description |
|-----|------|-------------|
| 0x10324f910 | ImGui Overlay | Main ImGui render gate (6 check sites) |
| 0x10324f9d0 | Cheat Menu | MainMenuCheats.cpp:1715 context |
| 0x10324f648 | Cheat Screen | MainMenuCheatScreen |
| 0x10324f640 | Debug Render | Primary debug render flag |
| 0x10324f649 | Debug Flag 2 | Secondary cheat flag |
| 0x10324f9b0 | Debug Flag 3 | Tertiary debug flag |
| 0x10324f9f0 | Debug Flag 4 | Quaternary debug flag |
| 0x10324f9e0 | Debug Flag 5 | Quinary debug flag |

## BSS Tweakable Vector

| Address | Field |
|---------|-------|
| 0x10324f478 | std::vector base pointer |
| 0x10324f480 | std::vector end pointer |
| 0x10324f488 | std::vector capacity pointer |

## Key Functions (binary VAs)

| VA | Function |
|-----|----------|
| 0x1000314c0 | Tweakable setter — `(w0=index, w1=value)`, dispatches by type at +0x20, writes through ptr at +0x48 |
| 0x100047458 | Tweakable init — 100KB inlined, builds all ~847 entries on 102KB stack frame |
