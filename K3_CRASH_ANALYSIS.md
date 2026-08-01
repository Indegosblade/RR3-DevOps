# K3 Crash Analysis (2026-08-01)

# Analysis: Post-Splash Crash in Multi-Patch RR3 Build

## Methodology Note First

The single most important fact in your data: **maxFPS stub alone works**. This proves (a) the stub-replacement mechanism is sound, (b) the binary tolerates patching, (c) the crash is caused by *content* of one or more of the remaining 19 patches, not by the patching technique. Given 19 remaining variables, a bisection (10-patch half-build, then narrow) would identify the culprit in ~5 builds. But here's the static analysis.

The crash timing — after both splash logos, ~1s of audio, during engine/SDK init — points at **initialization-phase code paths**, not UI-time selectors. That timing matters for ranking suspects.

---

## 1. Per-Patch Risk Assessment

### LOW RISK (verified reasoning)

**#6 isAdReady → 0** — EA-internal ad abstraction. Forcing "no ad ready" is the safe direction: it prevents ad display calls rather than triggering them. Low risk.

**#8 isInterstitialReady → 0** — Same reasoning. Low risk.

**#9 adMobEnabled → 0** — Config gate; disabling ad networks prevents SDK invocation. Low risk. *Caveat:* if init code does `if (adMobEnabled) initAdMob(); else ...` and the else-branch is never exercised, there's theoretical risk, but "disabled" branches are the shipping default for non-ad builds. Low.

**#10 checksumEnabled → 0** — Disabling anti-tamper. Return value 0 means checks skipped. Low risk — and arguably *necessary* since you've modified the binary.

**#11 maxFPS** — Confirmed working in isolation. Keep.

**#15–20 URL nulling (partial)** — See section 3; risk is real but *selective*. The Nimble/director URLs are fetched asynchronously after init typically; the news embed URL is UI-time. Moderate-to-low individually, but see failure modes below.

### MODERATE RISK

**#1 isDebugModeEnabled → 1** — 14 call sites, EA-internal. This *enables* code paths (cheat screen, ImGui overlay) that may never have shipped-enabled in a release binary. ImGui initialization on a build where ImGui resources/fonts weren't bundled is a plausible crash — **but** it would likely crash at menu render, not during init. Moderate.

**#3 isInternalTestMode → 1**, **#4 isAppDebuggable → 1** — Same class of risk: enabling dormant branches. 5 and 2 call sites. Moderate.

**#7 isRewardedVideoReady → 0** — Returning 0 is safe-direction, **but** the selector name is suspiciously SDK-shaped. I cannot verify whether UnityAds' bundled version exposes `isRewardedVideoReady`; older UnityAds used `+isReady:`, IronSource uses `hasRewardedVideo`/`isRewardedVideoAvailable`. State: **unverified collision risk**. If a collision exists, forcing "not ready" is still the benign direction. Low-moderate.

**#12 requestReview → nil** — `+[SKStoreReviewController requestReview]` is a class method; if app code calls it through this stub, returning nil where void was expected is harmless (caller ignores x0). Collision with EA-internal rating flow returning an object the caller retains/uses would matter — an EA-internal `requestReview` returning an object that's then messaged would crash on nil. **Unverified.** Moderate. Also: bare-ret was a real bug you correctly fixed.

### HIGH RISK — top crash suspects

**#2 debugMode → 1** — Generic name + 13 call sites + you return YES. I cannot verify whether any bundled SDK (AppLovin, GoogleUtilities, FBSDKCoreKit) has a `debugMode` accessor — I don't have confirmed knowledge of that selector in those frameworks' public APIs. But returning **YES** to a debug query is the dangerous direction: it *activates* code rather than suppressing it. If any of those 13 call sites gate logging-to-file, verbose networking, assertion handlers, or debug endpoints, YES on iOS 26 with dead servers is a live crash candidate. High.

**#5 isDebug → 1** — Same problem, worse name. `isDebug` is generic enough that collision is plausible, and again you're returning YES. High.

**#13 BuildType "PUBLIC"→"PRIVATE"** — This is my **#1 suspect**. Here's the specific failure mode: the C++ engine's build-type string is checked at *core initialization* (exactly your crash window). A PRIVATE build in Firemonkeys' pipeline plausibly: connects to internal telemetry/director endpoints, initializes developer console/debug server sockets, loads debug config files that don't exist in the shipping IPA, or asserts on missing internal provisioning. You're not just flipping a boolean — you're switching the engine's entire build identity into a configuration whose supporting infrastructure isn't bundled. High risk of init-time crash. And critically, I cannot verify what the PRIVATE branch does — neither can you without reading that code.

**#14 debugMode CBZ→NOP** — **#2 suspect**, and arguably worse than the stub patches because it's unconditional. The stub patches make debugMode *return* YES; this NOP makes *one specific site* execute its debug block regardless. That block was compiled in but (presumably) never executed in release. Dead-in-practice code in release binaries routinely contains: references to never-initialized globals, debug file I/O to paths that don't exist in the sandbox, socket binds, or calls into subsystems initialized only in debug builds. Executing it during init = crash during init. High.

---

## 2. Most Likely Crash Cause

Given the timing (init-phase, before menu), ranked:

1. **BuildType PRIVATE (#13)** — changes core init behavior at exactly the crash window.
2. **CBZ NOP (#14)** — forces never-tested debug code to run.
3. **debugMode=1 / isDebug=1 (#2, #5)** — YES-return on generic selectors activating unknown branches across 26 combined call sites.
4. **isDebugModeEnabled=1 (#1)** — ImGui/debug overlay init without bundled resources.

Note the pattern: **every high-risk patch returns YES/enables rather than disables.** Your working build (maxFPS) and your safe patches (ad removal, checksum off) all *suppress* behavior. The crashers all *activate* dormant release-binary code paths.

---

## 3. Non-Stub Patch Failure Modes

**BuildType string:** As above. Additional hazard: if the code does `strncmp(s, "PUBLIC", 6)` style checks in *multiple* places with different branch depths, you may get an inconsistent state — half the engine thinking it's PUBLIC, half PRIVATE. Also verify no length-prefixed or hashed usage of the string exists (anti-tamper checksums over `__cstring` would be defeated by checksumEnabled=0 only if that selector actually gates string-region checks — unverified).

**CBZ NOP:** The failure mode is executing the taken-path with uninitialized state. To evaluate properly you'd need to disassemble the block after 0x01267420 — if it references a global pointer that's only set inside a debug-init function, that's your crash. I can't see that code; you can. Check what's in the 10–20 instructions after the NOP'd branch.

**URL nulling:** Your stated mechanism is correct: `[NSURL URLWithString:@""]` returns nil. Then:
- If the code builds `NSURLRequest` with nil URL → `initWithURL:` with nil raises or returns nil depending on API; `+[NSURLRequest requestWithURL:nil]` **raises an exception** (NSInvalidArgumentException) — that *is* a crash.
- If the code passes the empty *NSString* itself somewhere expecting length>0, less dangerous.
- **However:** EA Nimble code's nil-checking habits are unverifiable by me. Counter-consideration: the stock binary already handles *unreachable* servers gracefully (it runs offline on your device), which means the network-failure path is exercised and safe. Nulling the URL changes a "connection fails" path into a "URL is nil at construction" path — a **different, earlier, untested** code path. That distinction is the risk. If any of these URL strings is consumed synchronously during init (director-int is the config/bootstrap endpoint — most likely candidate), nil-URL crash lands exactly in your crash window.

Safer alternative: replace the hostname with `127.0.0.1` (fast connection-refused, exercises the tested failure path) rather than emptying the string.

---

## 4. Recommended Minimal Patch Set

**Tier 1 — near-certain safe (keep):**
- maxFPS (#11)
- isAdReady=0 (#6)
- isInterstitialReady=0 (#8)
- adMobEnabled=0 (#9)
- checksumEnabled=0 (#10)

**Tier 2 — add only after Tier 1 confirmed booting, one at a time:**
- isDebugModeEnabled=1 (#1) — needed for cheat menu; watch for ImGui-init crash at menu
- isRewardedVideoReady=0 (#7)
- requestReview=nil (#12)
- URL patches — as `127.0.0.1` rewrites, not null-prefix

**Tier 3 — do not ship until individually validated:**
- debugMode=1, isDebug=1 — if needed at all, patch **call sites**, not the stub (see §5)
- isInternalTestMode, isAppDebuggable

**Drop entirely unless you disassemble the gated code first:**
- BuildType PRIVATE (#13)
- CBZ NOP (#14)

Note: #1 alone may give you the cheat menu without #2/#5/#13/#14. Test that hypothesis before adding any other debug enabler.

---

## 5. Selectors That Should Never Be Global Stub Patches

Any selector whose name is short/generic English should be treated as call-site-only:

- **isDebug** — too generic; unverifiable across GoogleUtilities/GAI/AppLovin internals.
- **debugMode** — same.
- **requestReview** — Apple-owned namespace adjacency (SKStoreReviewController).
- **isRewardedVideoReady / isInterstitialReady** — ad-SDK-shaped names; even though returning 0 is benign-direction, a colliding SDK call site receiving a hardcoded 0 where it expects a live query is fine, but you lose the ability to ever enable ads per-network. Acceptable here, but note it.

For call-site patching of #2/#5: instead of rewriting the stub, go to each of the 13/14 call sites and patch the instruction after `blr x16` (the stub call) — e.g., force `w0=1` with a `mov w0, #1` over the next instruction, only at sites you've disassembled and confirmed are EA engine code. That gives you debug-on for EA and untouched behavior for SDKs.

---

## Explicit Uncertainties

- I cannot confirm whether AppLovin, GoogleUtilities, GoogleAppMeasurement, FBSDKCoreKit, or UnityAds actually implement `debugMode` or `isDebug` in the bundled versions. Treat as plausible, not verified.
- I cannot know what the PRIVATE build-type branch or the NOP'd debug block contain without disassembly — that's on your end.
- EA Nimble's nil-checking around NSURL construction is unknown to me.
- The definitive answer is one bisection away: build with Tier 1 + half the debug patches. The crash timing you described (init-phase) already tells you it's almost certainly one of #13, #14, #2, #5, #1.