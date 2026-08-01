# RR3 IPA Versions

| File | Size | Patches | Status |
|------|------|---------|--------|
| `959112d6ace07153840144be3201b00f39ec0e91.ipa` | 1.3 GB | 0 | Original from appdb. **NEVER MODIFY.** |
| `rr3_4k.ipa` | 1.31 GB | 1 | maxFPS=120 only. **WORKING** (2026-08-01, iPhone 17 Pro A19). |
| `rr3_dev.ipa` | 1.31 GB | 14 | Dev v2 — K3 tiered approach. **TESTING** (2026-08-01). |

## Bundle ID

All use `com.ea.realracing3.inc` — sideloading any one over another preserves Documents (save + 5.1GB cache).

## rr3_4k.ipa (1 patch)
- maxFPS stub -> 120
- Everything else stock
- Clean zip-to-zip from original (19,251 zip entries preserved)

## rr3_dev.ipa — Dev v2 (14 patches, K3 tiered approach)

**Tier 1 — safe (K3 verified):**
- isAdReady -> NO, isRewardedVideoReady -> NO, isInterstitialReady -> NO, adMobEnabled -> NO
- checksumEnabled -> NO, maxFPS -> 60

**Tier 2 — cheat menu + QOL:**
- isDebugModeEnabled -> YES (sole debug gate — K3 says this alone may give cheat menu)
- requestReview -> nil

**URL rewrites (K3 fix — 127.0.0.1, NOT null):**
- 6x dead server URLs rewritten to `http://127.0.0.1/` + null padding
- Previous approach (null first byte) caused `[NSURLRequest requestWithURL:nil]` → NSInvalidArgumentException crash
- 127.0.0.1 gives fast connection-refused on the tested failure path

**DROPPED (K3 round 2 crash suspects — 2026-08-01):**
- ~~BuildType PRIVATE~~ — **K3 #1 suspect.** Switches engine identity; PRIVATE branch initializes debug infrastructure not bundled in release IPA
- ~~CBZ NOP~~ — **K3 #2 suspect.** Forces never-tested dead code execution (uninitialized globals, debug file I/O)
- ~~debugMode -> YES~~ — generic selector, 13 call sites, SDK collision risk (AppLovin/Google/Facebook)
- ~~isDebug -> YES~~ — very generic selector, SDK collision risk
- ~~isInternalTestMode -> YES~~ — dormant branch risk
- ~~isAppDebuggable -> YES~~ — dormant branch risk
- ~~gdprApplies -> NO~~ — consent singleton collision (K3 round 1)
- ~~trackingAuthorizationStatus -> 3~~ — ATTrackingManager collision (K3 round 1)

## Lessons Learned

1. **Zip directory entries matter.** Python zipfile extract-then-rezip drops directory entries. iOS needs them for framework loading. Always do zip-to-zip copy preserving ZipInfo objects.

2. **ObjC stub patches are GLOBAL.** Patching a stub in `__objc_stubs` intercepts ALL calls to that selector from the app binary, not just one class. Selectors shared with Apple frameworks or third-party SDKs (gdprApplies, trackingAuthorizationStatus) will break those frameworks.

3. **Bare `ret` without setting x0 returns the receiver.** `requestReview` with just `ret` returns `self` (the receiver pointer in x0). If any caller interprets the return value, it gets a wild pointer. Always `mov x0, #0; ret` for void methods.

4. **Consent and tracking selectors are landmines.** Ad SDKs (AppLovin, AdMob, Facebook, UnityAds) all query consent/tracking state during init. Short-circuiting these selectors skips initialization of consent singletons that later code assumes exist.

5. **Suppress, don't activate.** Every safe patch (maxFPS, ad removal, checksum off) *suppresses* behavior. Every crasher (BuildType PRIVATE, CBZ NOP, debugMode=YES, isDebug=YES) *activates* dormant code paths that were compiled in but never tested in release. The pattern: return NO/0/nil is safe-direction; return YES/1 on generic selectors is dangerous.

6. **URL nulling crashes at NSURL construction.** `[NSURL URLWithString:@""]` returns nil. `[NSURLRequest requestWithURL:nil]` raises NSInvalidArgumentException. This is a *different, earlier, untested* code path vs. the server-unreachable path that the stock app already handles. Rewrite to `127.0.0.1` for fast connection-refused on the tested failure path.

7. **Generic selector names = SDK collision risk.** `debugMode`, `isDebug` — any selector that's short generic English could be implemented by bundled SDKs (AppLovin, GoogleUtilities, FBSDKCoreKit, UnityAds). If you must patch these, do call-site patching (patch the instruction after `blr x16` at individual call sites) instead of global stub replacement.
