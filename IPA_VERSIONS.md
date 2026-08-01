# RR3 IPA Versions

| File | Size | Patches | Status |
|------|------|---------|--------|
| `959112d6ace07153840144be3201b00f39ec0e91.ipa` | 1.3 GB | 0 | Original from appdb. **NEVER MODIFY.** |
| `rr3_4k.ipa` | 1.31 GB | 1 | maxFPS=120 only. **WORKING** (2026-08-01, iPhone 17 Pro A19). |
| `rr3_dev.ipa` | 1.31 GB | 20 | Full dev build with K3-informed fixes. **TESTING** (2026-08-01). |

## Bundle ID

All use `com.ea.realracing3.inc` — sideloading any one over another preserves Documents (save + 5.1GB cache).

## rr3_4k.ipa (1 patch)
- maxFPS stub -> 120
- Everything else stock
- Clean zip-to-zip from original (19,251 zip entries preserved)

## rr3_dev.ipa (20 patches, K3-fixed)
**Debug mode (5 stubs -> YES):**
isDebugModeEnabled, debugMode, isInternalTestMode, isAppDebuggable, isDebug

**Ads killed (4 stubs -> NO):**
isAdReady, isRewardedVideoReady, isInterstitialReady, adMobEnabled

**Other stubs:**
- checksumEnabled -> NO (save checksum validation off)
- maxFPS -> 60
- requestReview -> nil (FIXED: returns nil, not garbage receiver pointer)

**Non-stub patches:**
- BuildType string: PUBLIC -> PRIVATE
- debugMode CBZ -> NOP
- 6 dead server URLs first-byte nulled

**DROPPED (crash-causing — K3 analysis 2026-08-01):**
- ~~gdprApplies -> NO~~ — collides with UMP/AppLovin/Facebook consent SDKs. Skips consent init, causes nil dereference in consent singletons during ad SDK bring-up.
- ~~trackingAuthorizationStatus -> 3~~ — collides with ATTrackingManager (Apple framework). Combined with missing consent state, forces ad SDKs down an untested "authorized + no consent" init path.

## Lessons Learned

1. **Zip directory entries matter.** Python zipfile extract-then-rezip drops directory entries. iOS needs them for framework loading. Always do zip-to-zip copy preserving ZipInfo objects.

2. **ObjC stub patches are GLOBAL.** Patching a stub in `__objc_stubs` intercepts ALL calls to that selector from the app binary, not just one class. Selectors shared with Apple frameworks or third-party SDKs (gdprApplies, trackingAuthorizationStatus) will break those frameworks.

3. **Bare `ret` without setting x0 returns the receiver.** `requestReview` with just `ret` returns `self` (the receiver pointer in x0). If any caller interprets the return value, it gets a wild pointer. Always `mov x0, #0; ret` for void methods.

4. **Consent and tracking selectors are landmines.** Ad SDKs (AppLovin, AdMob, Facebook, UnityAds) all query consent/tracking state during init. Short-circuiting these selectors skips initialization of consent singletons that later code assumes exist.
