# Technical Report: Runtime Tweakable System and Production Patch Method

## Scope

This report documents the reverse-engineering method used to characterize the final iOS build's runtime tweakable system and to produce the RR3 DevOps package. It separates production behavior from experimental findings and distinguishes verified observations from inference.

For a plain-English account of the engineering workflow, including task-specialized AI assistance, binary-analysis review, and physical-device validation, see [How RR3 DevOps was built](../WORKFLOW.md).

## Initial conditions

The project began with an existing community-preserved iOS package that already supported local cache import and offline operation. RR3 DevOps therefore focused on two questions:

1. Which modifications could be applied reproducibly to the final iOS executable without destabilizing the shipping binary?
2. Which developer-oriented systems remained live and accessible in the retail binary?

## Method

### Production patch selection

The production builder uses only bounded, exact-build changes: known Objective-C stub returns, known endpoint rewrites, and EDS-file replacement. Activation-style experiments were excluded because a release binary can retain references to developer or third-party SDK paths without retaining a complete initialization environment.

The primary controls were:

- inspect every relevant selector/call site before making a global stub replacement;
- distinguish suppression paths from activation paths;
- preserve the source IPA's zip-entry structure during rebuild;
- use the existing iPad Pro EDS resource family rather than invent an unknown internal identity; and
- verify the EDS transformation with an encrypt/decrypt round trip.

### Runtime registry analysis

The harness resolves the main-image ASLR slide, applies it to researched BSS virtual addresses, and walks the live tweakable vector after game initialization. Entry names, type tags, range metadata, and live pointers are decoded from a fixed `0x78`-byte layout. The implementation then performs a reversible write/read-back check before reporting a successful UI change.

## Validated findings

### Verification boundary

The harness was validated at the data-path level: it indexes the live registry, writes to each selected entry's recovered live pointer, and reads that location back for verification. This establishes that the reverse-engineered entry layout and pointer wiring are correct for the researched process. It is not a claim that all roughly 847 registered entries were individually behavior-tested. A control can be conditional, not consumed in the current scene, superseded by another value, or overridden later by game logic. Selected vehicle, tire, rendering, and debug controls were independently confirmed on device with visible live changes.

| Finding | Evidence |
|---|---|
| EDS uses the modified-RC4 transformation implemented in `build_4k_v3.py` | Source implementation with round-trip assertion |
| The iPad-based EDS profile operates on the stated test device | Device validation: iPhone 17 Pro, iOS 26.0 |
| The runtime registry has a `0x78`-byte entry layout and live-value pointer | Tracked harness implementation and setter/init analysis |
| The harness indexes runtime entries, writes values, reads them back, and resets the captured session baseline | Tracked Objective-C source |
| The original developer/ImGui UI is fully restorable | Not established; not a project claim |
| Every description exactly reflects internal developer intent | Not established for every entry; descriptions may be inferred from names and observed behavior |

## Production versus experimental status

The authoritative production patch set is [Production binary patches](BINARY_PATCHES.md). It excludes debug-gate activation, BuildType changes, and branch-NOP experiments.

Earlier activation experiments established an important negative result: forcing dormant debug gates or patching generic Objective-C selectors can activate unrelated SDK paths and destabilize initialization. Those experiments are retained as local research notes; the public production specification is the complete supported patch reference.

## Research significance

The implementation does not depend on reconstructing a missing developer UI. It treats the live registry as the operational interface: discover the collection, recover the entry schema, validate the data path, and provide a stable touch-native frontend. The same method can be independently applied to another platform or build after its own addresses and layout are established.

See [Internal developer systems](INTERNAL_DEVELOPER_SYSTEMS.md) for the data model and [Android porting notes](ANDROID_PORTING.md) for the platform-transfer plan.
