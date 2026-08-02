# Crash Analysis: ObjC Stub Patching in Release Binaries

**Status: RESOLVED** — god-mode EDS crash root-caused to `PLIST_IDENTIFIER` mismatch. See [EDS Crash Resolution](#eds-crash-resolution) at the end.

This document records the analysis of a post-splash crash in a multi-patch RR3 build and the methodology used to identify the root causes. The findings are broadly applicable to anyone doing ObjC stub patching on stripped arm64 binaries.

## Key Principle: Suppress, Don't Activate

Every safe patch in this project (maxFPS, ad removal, checksum off) *suppresses* behavior — it returns NO/0/nil to skip a code path. Every crasher (BuildType PRIVATE, CBZ NOP, generic `debugMode=YES`) *activates* dormant code paths that were compiled in but never tested in a release binary.

**The pattern:** returning NO/0/nil is safe-direction. Returning YES/1 on generic selectors is dangerous.

## Methodology

The single most important fact: **maxFPS stub alone works.** This proves the stub-replacement mechanism is sound, the binary tolerates patching, and the crash is caused by the *content* of one or more patches, not the technique. With N remaining variables, a bisection (half-build, then narrow) identifies the culprit in log2(N) builds.

The crash timing — after both splash logos, ~1 second of audio, during engine/SDK init — points at initialization-phase code paths, not UI-time selectors.

## Per-Patch Risk Assessment

### LOW RISK (safe-direction patches)

- **`isAdReady` -> NO** — prevents ad display calls rather than triggering them.
- **`isInterstitialReady` -> NO** — same reasoning.
- **`adMobEnabled` -> NO** — disabling ad networks prevents SDK invocation.
- **`checksumEnabled` -> NO** — disabling anti-tamper. Return value 0 means checks skipped.
- **`maxFPS` -> 120** — confirmed working in isolation.

### MODERATE RISK

- **`isDebugModeEnabled` -> YES** — 14 call sites. Enables code paths (cheat screen, ImGui overlay) that may never have shipped enabled. ImGui initialization without bundled resources is a plausible crash, but would likely crash at menu render, not during init.
- **`isRewardedVideoReady` -> NO** — returning 0 is safe-direction, but the selector name is SDK-shaped. Unverified collision risk with UnityAds.
- **`requestReview` -> nil** — bare `ret` without clearing x0 returns the receiver pointer. Always use `mov x0, #0; ret` for void methods.

### HIGH RISK (confirmed crash causes)

- **`debugMode` -> YES** — generic name, 13 call sites across IronSource/AppLovin/MAX/Tapjoy. Returning YES activates ad SDK debug mode during initialization. Confirmed crash.
- **`isDebug` -> YES** — same problem, worse name. Facebook Audience Network selector. Confirmed crash.
- **BuildType "PUBLIC" -> "PRIVATE"** — switches the engine's entire build identity. A PRIVATE build in the original dev pipeline would connect to internal telemetry, initialize developer console sockets, load debug config files not bundled in the shipping IPA. The supporting infrastructure isn't present. Confirmed crash.
- **debugMode CBZ -> NOP** — forces execution of a never-tested debug block. Dead-in-practice code in release binaries routinely contains references to uninitialized globals, debug file I/O to nonexistent paths, socket binds, or calls into subsystems only initialized in debug builds. Confirmed crash.

## Lessons for ObjC Stub Patching

### 1. Global stub patches are GLOBAL

Patching a stub in `__objc_stubs` intercepts ALL calls to that selector from the entire binary, including bundled third-party SDKs. A selector like `isDebug` may be implemented by AppLovin, GoogleUtilities, FBSDKCoreKit, and the game engine simultaneously. One stub, all callers.

**Mitigation:** For generic selector names, patch individual call sites (the instruction after `blr x16` at each site) instead of the global stub.

### 2. Bare `ret` is not the same as returning nil

A bare `ret` instruction returns whatever is in x0 — which is the receiver pointer (self) from the `objc_msgSend` call. If any caller interprets the return value, it gets a wild pointer. Always explicitly set the return register: `mov x0, #0; ret` for nil, `mov w0, #<imm>; ret` for integers.

### 3. URL nulling crashes at NSURL construction

`[NSURL URLWithString:@""]` returns nil. `[NSURLRequest requestWithURL:nil]` raises NSInvalidArgumentException. This is a different, earlier, untested code path from the server-unreachable path the stock app already handles.

**Mitigation:** Rewrite URLs to `127.0.0.1` for fast connection-refused on the tested failure path, rather than emptying the string.

### 4. Consent and tracking selectors are landmines

Ad SDKs (AppLovin, AdMob, Facebook, UnityAds) all query consent/tracking state during init. Short-circuiting these selectors skips initialization of consent singletons that later code assumes exist. Nil dereference on the singleton -> crash.

### 5. String identity patches are dangerous

Changing a string like `"PUBLIC"` to `"PRIVATE"` doesn't just change a label — if any code does `strncmp(s, "PUBLIC", 6)` in multiple places with different branch depths, you get an inconsistent state where half the engine thinks it's in one mode and half in another.

## Recommended Tiered Approach

**Tier 1 — safe (suppress-direction):** ad removal, checksum off, maxFPS, URL rewrites (127.0.0.1)

**Tier 2 — add one at a time after Tier 1 boots:** `isDebugModeEnabled`, `requestReview`, `isRewardedVideoReady`

**Tier 3 — validate individually before shipping:** `isInternalTestMode`, `isAppDebuggable`

**Drop entirely unless the gated code is disassembled first:** BuildType string changes, CBZ NOPs, generic `debugMode`/`isDebug`

## EDS Crash Resolution

The god-mode EDS plist caused a separate crash unrelated to ObjC stub patching.

### Problem

Setting `PLIST_IDENTIFIER` to `iPhone18,1` (a device the game doesn't know about) caused a crash during engine init. The engine uses `PLIST_IDENTIFIER` for internal resource lookups — shader caches, texture atlases, asset bundles — not just labeling. It matches against the `ALL_PLISTS` registry string. An unknown identifier produces a null asset handle, which crashes.

The *filename* (`iPhone18,1.plist`) is what handles device matching. The identifier *inside* the plist must refer to a device the engine's resource tree knows about.

### Additional crash factors identified

- **GUI cluster mismatch**: Using iPad GUI settings (`_1024x768`, `AUTO_SCALE=false`, `HIGH_RES_MENU=true`) with iPhone-class resolution/screen values crashes because the GUI resource set doesn't match.
- **EXPECTED_SCREEN mismatch**: Changing resolution to `2622x1206` while keeping iPad GUI settings creates an inconsistent state.

### Fix

Start from the iPad Pro 12.9" (iPad6,8) plist as-is — all 113 keys preserved, `PLIST_IDENTIFIER` kept as `iPad6,8`, GUI cluster untouched. Apply only safe quality upgrades (anisotropic filtering, streaming shadows, prop detail, cubemap threshold). Device-tested and confirmed working on iPhone 17 Pro (A19, iOS 26.0).

### Test matrix

| Build | PLIST_IDENTIFIER | EXPECTED_SCREEN | GUI cluster | Result |
|-------|-----------------|-----------------|-------------|--------|
| v3 (custom god) | iPhone18,1 | 2622x1206 | _960x640 | CRASH |
| v3 godfix (iPad base + 10 changes) | iPhone18,1 | 2622x1206 | _1024x768 | CRASH |
| iPad Pro re-encrypt (zero changes) | iPad6,8 | 2732x2048 | _1024x768 | OK |
| v3 final (iPad base + 4 safe) | iPad6,8 | 2732x2048 | _1024x768 | OK |
