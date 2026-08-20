# Android Porting Notes

RR3 DevOps is an iOS implementation, not an Android port. These notes are a handoff for Android developers who want to investigate whether an equivalent final Android build exposes the same kind of runtime registry.

## What should transfer conceptually

The useful idea is independent of UIKit and iOS injection:

1. Locate the game's live tweakable registry after initialization.
2. Prove the vector/list bounds before walking it.
3. Recover one entry layout from a setter or initializer.
4. Decode names and types.
5. Read a value, write one reversible numeric value, and read it back.
6. Build a frontend only after the data path is proven.

The iOS reference layout is documented in [Internal developer systems](INTERNAL_DEVELOPER_SYSTEMS.md). Use it as a hypothesis, not a binary-compatible contract.

## What is iOS-specific

- dyld ASLR-slide calculation;
- the researched iOS virtual addresses;
- the Objective-C/UIKit overlay;
- dylib injection and Sideloadly installation flow; and
- the exact final iOS Mach-O build.

Do not copy an iOS address into an Android build. Find the equivalent data and code independently.

## Suggested Android workflow

| Stage | Goal | Evidence to save |
|---|---|---|
| Static inventory | Search for `TWEAKABLE_`, debug commands, and developer strings | Build version, string references, candidate functions |
| Runtime location | Break/trace near a candidate initializer or setter | Pointer chain, collection bounds, timing |
| Entry validation | Decode several names/types and compare with expected behavior | Raw entry bytes, field offsets, screenshots/logs |
| Safe write | Change a benign, reversible value and verify read-back | Before/after values and reproduction steps |
| UI | Present categories and controls once the data model is stable | Build identifier and limitations |

## Design suggestions

- Keep a launch-time snapshot so reset means “restore what this session loaded,” not “guess a default.”
- Preserve raw names even when you display prettier labels; raw names are the bridge between researchers.
- Separate confirmed descriptions from inferred descriptions.
- Log the runtime count and unrecognized types instead of silently skipping them.
- Start with a small read-only viewer, then add write controls one category at a time.

## What RR3 DevOps can provide

The project provides a working iOS example of category grouping, type handling, live write/read-back verification, description mapping, reset behavior, and diagnostic output. The source is available under the repository's MIT license. Game assets and the iOS binary are not a substitute for independently researching the Android build.

If you find a matching Android registry, open an issue with the build identifier, evidence, and uncertainty level. A clean write-up is more valuable than a bare address dump.
