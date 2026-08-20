# Internal Developer Systems

The final iOS retail binary retains developer-oriented infrastructure: command names, cheat-screen references, ImGui-related code, debug flags, and a live tweakable registry. RR3 DevOps documents and exposes the registry through an independent UIKit harness.

## Status

| Component | Status |
|---|---|
| Runtime tweakable vector | Confirmed and used by the harness |
| `0x78`-byte entry layout | Confirmed by tracked source and researched setter/init references |
| Live numeric-value writes | Confirmed by harness write/read-back behavior |
| Original developer/cheat UI | Not fully restored; not presented as a working touch UI |
| BSS debug flags | Exposed for research; individual behavior may remain unresolved |

## Count definitions

Several values appear in the source and analysis. They measure different things.

- **895** — `TWEAKABLE_` names/inventory references identified during static analysis in the patch and binary analysis reference.
- **~847** — entries observed in the live runtime vector on the researched final iOS build.
- **887** — authored description mappings in `overlay/rr3_overlay.m`; a mapping can exist for an entry that is absent, conditional, or differently registered in a particular runtime state.

The harness reports the live count it indexes. Do not represent these measurements as a single fixed control count.

## BSS addresses for the researched build

These are unslid virtual addresses for the final iOS binary. The harness first verifies the researched executable's Mach-O UUID, then determines the dyld slide and adjusts them at runtime. It checks the vector header, stride alignment, entry ceiling, and mapped ranges before indexing or writing a value.

| VA | Role |
|---|---|
| `0x10324f478` | Tweakable-vector base pointer |
| `0x10324f480` | Tweakable-vector end pointer |
| `0x10324f488` | Tweakable-vector capacity pointer |
| `0x10324f910` | ImGui-related render gate |
| `0x10324f9d0` | Cheat-menu-related flag |
| `0x10324f648` | Cheat-screen-related flag |
| `0x10324f640` | Debug-render-related flag |

The overlay also presents four nearby researched flags whose exact subsystem role remains unresolved. A flag write is not proof that a complete UI path exists.

## Entry layout

| Offset | Type | Meaning |
|---|---|---|
| `+0x00` | `uint32_t` | Registry ID |
| `+0x08` | libc++ string | Tweakable name, decoded with short-string optimization support |
| `+0x20` | `uint32_t` | Type tag: string/int/bool/double/float |
| `+0x28` | libc++ string | Optional label |
| `+0x40` | value storage | Cached/current value representation |
| `+0x48` | pointer | Live game-variable pointer |
| `+0x50` | numeric | Minimum metadata |
| `+0x58` | numeric | Maximum metadata |
| `+0x60` | numeric | Default metadata |

The entry stride is `0x78` bytes. The source references a setter at `0x1000314c0` and initialization at `0x100047458` for the researched build.

## Original developer UI versus the harness

The binary includes references such as `MainMenuCheatScreen`, `ToggleImGuiToolsMenu`, and `ShowDebugTweakables`. These references establish that parts of the developer system survived. They do not establish that the retail build retains every resource, initializer, input path, and dependency required to render the original UI.

RR3 DevOps does not depend on that UI path. The UIKit harness uses the live registry directly and provides touch-native controls for the researched data model.

## Evidence standard

Document new claims as **Confirmed by source/disassembly**, **Confirmed on device**, **Inferred**, or **Unresolved**. The evidence category is part of the result.

See [Runtime developer harness](../overlay/README.md) for implementation details and [Technical report](TECHNICAL_REPORT.md) for methods and findings.
