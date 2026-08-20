# RR3 Developer Harness

`RR3-DevOps-v1.0-Developer-Harness.dylib` is RR3 DevOps's native UIKit frontend for the final iOS build's runtime tweakable registry. It is not a recreation of Firemonkeys' original developer UI. The retail binary retains pieces of that infrastructure, but the original presentation path has not been fully restored; this harness talks to the live registry directly.

## What it does

- Adds a draggable `RR3` button after the game finishes initializing.
- Displays eight researched BSS debug flags for experimentation.
- Reads the runtime tweakable vector and groups the entries by `TWEAKABLE_` prefix.
- Uses switches for booleans and likely boolean-like integers; uses sliders for other numeric types.
- Writes through the entry's live-value pointer, then reads the value back to report whether the write verified.
- Captures each value when the harness indexes the runtime registry. Category reset and **RESET ALL** restore that captured state; they do not reconstruct a factory/default configuration.
- Provides long-press metadata, a startup diagnostic dump at `Documents/tweakable_dump.txt`, and a one-tap three-finger gesture to hide or show the harness.

Press and hold a slider or its list row for about half a second to open its short information panel: description, raw runtime name, type, current value, launch snapshot, range, and pointer address. The complete generated reference is [All Runtime Tweakables and Research Flags](../docs/ALL_FLAGS.md).

### Gesture coexistence

The upstream preserved iOS package retains its own local cache importer. With the harness injected, use **one three-finger tap** for the RR3 DevOps overlay and **one three-finger double-tap** for the upstream cache importer. The importer belongs to the upstream package; RR3 DevOps does not claim authorship of it.

The current source contains **887 authored description mappings**. The number of registered runtime entries is measured from the live vector at launch; the tested final iOS build has been observed at roughly **847** entries. Those are different measurements, not competing claims. See [Internal developer systems](../docs/INTERNAL_DEVELOPER_SYSTEMS.md#counts-and-what-they-mean).

## What write verification proves

The harness writes a selected value through the recovered live pointer and reads the same location back. That proves the registry entry and write path are wired correctly for the current process. It does **not** prove that every entry visibly changes the current scene or race: a value may be conditional, unused by the final build, cached elsewhere, or later overridden by another game system. Selected vehicle, tire, rendering, and debug controls were confirmed on device; the complete registry was not individually behavior-tested.

## Build and injection

The release dylib was compiled with an iOS 15.0 deployment target. A representative build command is in the [Makefile](Makefile).

To use the release asset:

1. Download `RR3-DevOps-v1.0-Developer-Harness.dylib` from [v1.0-overlay](https://github.com/Indegosblade/RR3-DevOps/releases/tag/v1.0-overlay).
2. In Sideloadly, select the target IPA and open **Advanced Options**.
3. Add the dylib under **Inject dylibs/frameworks**, then sideload the IPA.
4. Launch the game and wait for it to finish initializing. The floating button normally appears after roughly 11 seconds; the registry then retries initialization for up to 16 seconds if the game is still starting.

The overlay is optional. The current source validates the researched final executable's Mach-O UUID, vector structure, and mapped read/write ranges before it exposes controls. This is a build identity check, not a bundle-ID or signing check: normally re-signed/repackaged copies of that same executable remain usable. Do not use the harness with an arbitrary RR3 IPA.

## Runtime model

The harness determines the main-image ASLR slide with dyld and adds it to the researched virtual addresses. It then walks a `std::vector` whose entries are `0x78` bytes each.

| Offset | Field | Notes |
|---|---|---|
| `+0x00` | `uint32_t` ID | Sequential registry identifier |
| `+0x08` | 24-byte libc++ string | Tweakable name; short-string optimization is decoded by the harness |
| `+0x20` | type tag | `0` string, `1` int, `2` bool, `3` double, `4` float |
| `+0x28` | 24-byte libc++ string | Optional label |
| `+0x40` | value cache | Value stored with the entry |
| `+0x48` | live-value pointer | The harness writes through this pointer |
| `+0x50` / `+0x58` | min / max | Range metadata for numeric UI controls |
| `+0x60` | default metadata | Present in the entry; the current UI resets to its launch snapshot instead |

The BSS vector and flag virtual addresses, plus the relevant setter and initializer, are recorded in [Internal developer systems](../docs/INTERNAL_DEVELOPER_SYSTEMS.md).

## Original developer UI: current status

The retail binary retains names, commands, flags, ImGui code, and the tweakable registry associated with internal developer tooling. It does **not** follow that toggling a flag restores a complete retail-ready menu. The original UI's resources and initialization path are incomplete or inactive in this build.

The harness deliberately does not depend on that path. Treat the BSS flag toggles as research controls, not as a guarantee that every original panel will appear or work.

## Limits and safe reporting

- The runtime layout and addresses are build-specific.
- Some descriptions are inferred from names and observed behavior; they are not official game documentation.
- A verified write only means the harness read back the requested value. It does not guarantee every system will consume that value in the current race or menu state.
- Do not report a generic “overlay broken.” Include the device, iOS version, IPA/release used, whether the `RR3` button appears, and the relevant `tweakable_dump.txt` excerpt. See [Troubleshooting](../docs/TROUBLESHOOTING.md).

For an implementation-oriented handoff to Android developers, see [Android porting notes](../docs/ANDROID_PORTING.md).
