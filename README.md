# RR3 Resurrection

Real Racing 3 was shut down by EA on March 31, 2026. This project brings it back as a fully offline single-player experience with quality-of-life improvements, 4K visuals on modern hardware, and unlocked developer features.

**Status:** Playable offline on iOS 26.0+.

## Downloads

Each component is published as a separate GitHub Release with full install instructions:

| Release | Asset | Size | Description |
|---------|-------|------|-------------|
| [**v1.0-4k**](../../releases/tag/v1.0-4k) | `rr3_4k_v2.ipa` | 1.3 GB | Production build — 120fps, 4K quality, ads removed, dead URLs patched |
| [**v1.0-overlay**](../../releases/tag/v1.0-overlay) | `rr3_overlay.dylib` | 90 KB | Debug overlay — inject via Sideloadly for in-game debug flag toggles |
| [**v1.0-cache**](../../releases/tag/v1.0-cache) | `Caches_ipastore.zip` (3 parts) | 5.1 GB | Game asset cache — required for offline play (tracks, cars, textures) |

## What's Patched

The stock app hangs on connection timeouts, shows broken ad prompts, and runs at low quality on modern hardware. All patches are binary-level modifications to the arm64 Mach-O executable — no jailbreak, no code injection, no runtime hooking.

### 4K Visual Quality (EDS Profile Override)

Real Racing 3 uses **Engine Device Settings** (EDS) — 41 encrypted plists in `res/eds/` that control visual quality per device model. Newer devices have no matching EDS profile and fall back to conservative defaults.

The fix: inject the iPad Pro 12.9" quality profile (the highest-quality iOS profile) as a device-specific match. All 41 EDS files share identical encryption — no per-device key — so copying and renaming works without decryption. This technique is well-established in the Android modding community.

**15 quality flags unlocked:** car ambient occlusion, planar reflections, HDR post-processing, real-time car shadow maps, PBR water, high-quality headlights, dynamic environment map blur, HDR environment maps, gamma correction, automatic HDR exposure, particle shadows, deferred lightmap skid marks, high LOD tracks, full Le Mans rendering, and big track support.

### 120fps

The stock app caps at 30/60fps. Patched to 120fps for ProMotion displays.

### Ads Removed (4 patches)

`isAdReady`, `isRewardedVideoReady`, `isInterstitialReady`, `adMobEnabled` — all forced to return NO. Every call site verified as IronSource/AppLovin mediation code with no framework collisions.

### Dead Server URLs Rewritten (6 URLs)

EA/Glu backend URLs rewritten to `127.0.0.1` for fast connection-refused on the tested failure path. Nulling URLs causes `[NSURLRequest requestWithURL:nil]` crashes — `127.0.0.1` exercises the same network-failure handler the stock app already uses when servers are unreachable.

### Other Patches

- `checksumEnabled` → NO (IronSource analytics protobuf checksum — not EA save anti-tamper)
- `requestReview` → nil (suppresses App Store review prompts)

## Debug Overlay

The overlay dylib (`rr3_overlay.dylib`) is a floating debug panel that writes directly to BSS debug flag addresses at runtime. Inject it via Sideloadly's "Inject dylibs/frameworks" option.

**8 toggleable flags:** ImGui overlay, cheat menu, cheat screen, debug render, and 4 additional debug flags. See [`overlay/README.md`](overlay/README.md) for addresses and build instructions.

## Developer Cheat Menu

The game binary contains EA Firemonkeys' internal developer cheat screen with 29 categories and 150+ entries, plus 895 runtime tweakable variables accessible through an ImGui overlay. Full documentation in [PATCHES.md](PATCHES.md).

**Current status:** Debug mode is confirmed active (debug HUD elements appear), but the cheat menu UI trigger mechanism has not been fully identified. The overlay dylib attempts to force-enable the relevant BSS flags. See [Issue #3](../../issues/3) for ongoing investigation.

### What the cheat menu contains (from binary analysis)

- **Unlock + Own Everything** — all cars, tracks, series
- **Currency cheats** — R$, Gold, Motorsport dollars
- **Debug race selector** — jump to any race directly
- **AI control** — let AI drive your car
- **Free camera** — 6DOF camera in race
- **895 tweakable variables** — full engine config access (physics, rendering, audio, input, camera)

## Setup

### Requirements

- iPhone or iPad running iOS 15+
- [Sideloadly](https://sideloadly.io/) for sideloading
- ~7 GB free storage (1.3 GB app + 5.1 GB cache)

### Steps

1. **Download the IPA** from the [v1.0-4k release](../../releases/tag/v1.0-4k)
2. **Sideload** with [Sideloadly](https://sideloadly.io/) — connect your device, select the IPA, sign with your Apple ID
3. **Download the cache** from the [v1.0-cache release](../../releases/tag/v1.0-cache) — download all 3 `.part` files
4. **Reassemble the cache:**
   - **Windows:** `copy /b Caches_ipastore.zip.part00+Caches_ipastore.zip.part01+Caches_ipastore.zip.part02 Caches_ipastore.zip`
   - **macOS/Linux:** `cat Caches_ipastore.zip.part* > Caches_ipastore.zip`
5. **Import cache** — unzip and copy the contents into the app's Documents folder via the Files app (enable File Sharing in Sideloadly) or 3uTools
6. **Launch** — the game runs fully offline, no EA account required

### Optional: Debug Overlay

1. **Download** `rr3_overlay.dylib` from the [v1.0-overlay release](../../releases/tag/v1.0-overlay)
2. In Sideloadly, go to Advanced Options → Inject dylibs/frameworks → add the dylib
3. Sideload with the dylib injected — a floating "RR3" button appears in-game

### Notes

- Bundle ID is `com.ea.realracing3.inc` — sideloading one build over another preserves saves and cache
- Free Apple IDs have 7-day signing. Use [AltStore](https://altstore.io/) for auto-refresh or re-sign weekly
- The game natively supports MFi controllers (GCController, ExtendedGamepad profile)

## How It Works

### ObjC Stub Patching

The binary's `__objc_stubs` section contains 16-byte trampolines for every ObjC method call. Each stub is replaced with a 16-byte sequence that returns a hardcoded value:

```arm64
mov   w0, #<return_value>
ret
nop
nop
```

The ObjC message is never sent — the stub returns immediately with the desired value.

### Build Process

IPAs are built via a Python script that performs a zip-to-zip copy from the original IPA. The binary is read into memory, patches are applied at known file offsets, and the modified binary is written to the output zip. All other files are copied byte-for-byte. Sideloadly re-signs the bundle on install.

The zip must preserve directory entries — Python's `zipfile` handles this correctly when copying `ZipInfo` objects, but extract-then-rezip drops directory entries and causes framework loading failures on iOS.

## Known Issues

- **GDPR/ATT popups** — `gdprApplies` and `trackingAuthorizationStatus` are intentionally NOT patched. These selectors collide with Apple's AppTrackingTransparency framework and third-party ad SDK consent systems. Patching them crashes the app during ad SDK initialization. The popups are harmless offline.
- **Generic debug selectors NOT patched** — `debugMode` (13 callers, all IronSource/AppLovin/MAX/Tapjoy ad SDK init code) and `isDebug` (Facebook Audience Network) are confirmed SDK selectors. Forcing YES crashes the app during initialization.
- **Some cheats are platform-gated** — a few cheat menu entries display "This cheat does not work on non windows/Android platforms."

## Technical Reference

See [PATCHES.md](PATCHES.md) for the complete patch table with file offsets, ARM64 encodings, and Mach-O layout details.

## License

This project is for personal archival and educational purposes. Real Racing 3 is property of Electronic Arts / Firemonkeys. The game was discontinued on March 31, 2026 and is no longer available for purchase or download. This project does not distribute copyrighted game assets.
