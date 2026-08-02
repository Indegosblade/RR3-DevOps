# RR3 Resurrection

Real Racing 3 was shut down by EA on March 31, 2026. This project brings it back as a fully offline single-player experience with quality-of-life improvements, 4K visuals on modern hardware, and unlocked developer features.

**Status:** Playable offline on iOS 26.0+.

## Downloads

Each component is published as a separate GitHub Release with full install instructions:

| Release | Asset | Size | Description |
|---------|-------|------|-------------|
| [**v1.0-4k**](../../releases/tag/v1.0-4k) | `rr3_4k_v3.ipa` | 1.3 GB | Production build — 120fps, god-mode EDS quality, ads removed, dead URLs patched |
| [**v1.0-overlay**](../../releases/tag/v1.0-overlay) | `rr3_overlay.dylib` | 286 KB | Debug overlay v5 — 887 described tweakables, snapshot reset, three-finger hide |
| [**v1.0-cache**](../../releases/tag/v1.0-cache) | `Caches_ipastore.zip` (3 parts) | 5.1 GB | Game asset cache — required for offline play (tracks, cars, textures) |

## What's Patched

The stock app hangs on connection timeouts, shows broken ad prompts, and runs at low quality on modern hardware. All patches are binary-level modifications to the arm64 Mach-O executable — no jailbreak, no code injection, no runtime hooking.

### God-Mode Visual Quality (EDS Encryption Cracked)

Real Racing 3 uses **Engine Device Settings** (EDS) — 41 encrypted plists in `res/eds/` that control visual quality per device model. The encryption is a modified RC4 cipher with an 8-byte hardcoded key (`a5 35 b3 b1 e8 43 e7 cf`). We cracked it — full algorithm, key extraction, and Python encrypt/decrypt code are in [PATCHES.md](PATCHES.md).

With all 41 files decrypted, we built a **god-mode quality profile** starting from the iPad Pro 12.9" baseline (the highest stock tier) and pushing 4 additional settings beyond it. The `PLIST_IDENTIFIER` is kept as `iPad6,8` — the engine uses this for internal resource lookups (shader caches, texture atlases, asset bundles), not device matching. The filename (`iPhone18,1.plist`) handles device matching. The custom plist is encrypted with the cracked key and injected into the IPA as both `iPhone18,1.plist` (direct model match) and `iPhone.plist` (universal fallback).

**Key upgrades over iPad Pro 12.9":** anisotropic filtering, streaming shadow maps, finer prop detail (0.001 vs 0.005), and higher cubemap threshold (800 vs 400). All 15 existing iPad Pro quality flags are preserved: car ambient occlusion, planar reflections, HDR post-processing, real-time car shadow maps, PBR water, high-quality headlights, dynamic environment map blur, HDR environment maps, gamma correction, automatic HDR exposure, particle shadows, deferred lightmap skid marks, high LOD tracks, full Le Mans rendering, and big track support.

The build script (`build_4k_v3.py`) and decrypted god plist (`eds_god.plist`) are included in this repo.

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

The overlay dylib (`rr3_overlay.dylib`) provides a floating debug panel and live tweakable variable browser. Inject via Sideloadly's "Inject dylibs/frameworks" option. See [`overlay/README.md`](overlay/README.md) for full documentation.

### What it does

- **8 debug flag toggles** with descriptions — ImGui overlay, Cheat Menu (Unlock All, Free Currency, Max Level, Skip Tutorial), Debug Render (wireframes, collision, physics), and 5 subsystem flags
- **Live tweakable browser** — reads ~847 engine variables from the BSS vector at runtime, groups into 15+ categories (AI, Camera, Car, Suspension, Sound, Render, HDR, PBR, Lighting, NASCAR, Input, Shaders, etc.)
- **887 functional descriptions** — every tweakable has a description explaining what it does, with directional hints for sliders (← less → more) and ON/OFF behavior for toggles. Long-press any entry to see it.
- **Smart controls** — UISwitch for bools and bool-like ints, UISlider for numeric values. 20 negative patterns prevent numeric entries from getting toggles
- **Write verification** — every change is read back through the live pointer and confirmed with a toast notification (green checkmark = verified, red = mismatch)
- **Snapshot-based reset** — RESET restores values to what the game actually loaded, not compiled defaults. Per-category and global RESET ALL button in the main menu header
- **Three-finger tap** — tap with three fingers anywhere to hide/show the entire overlay (button + panel)
- **Diagnostic dump** — writes `Documents/tweakable_dump.txt` at startup with all entries categorized

### Developer Cheat Menu

The game binary contains EA Firemonkeys' internal developer cheat screen with 29 categories and 150+ entries. The overlay force-enables the relevant BSS flags, but the ImGui UI requires keyboard/controller input to navigate — touch input is not wired to ImGui. See [Issue #3](../../issues/3).

**Cheat menu contents (from binary analysis):**

- **Unlock + Own Everything** — all cars, tracks, series
- **Currency cheats** — R$, Gold, Motorsport dollars
- **Debug race selector** — jump to any race directly
- **AI control** — let AI drive your car
- **Free camera** — 6DOF camera in race
- **847 tweakable variables** — full engine config access (physics, rendering, audio, input, camera)

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
3. Sideload with the dylib injected
4. Wait ~11 seconds after launch — a floating "RR3" button appears
5. Tap to open the debug panel; drag to reposition the button
6. Three-finger tap anywhere to hide/show the overlay

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

## Legal

Real Racing 3 is property of Electronic Arts / Firemonkeys. The game was a free-to-play title distributed at no cost on the App Store. EA discontinued the game on March 31, 2026, shut down all backend servers, and removed it from all app stores. It is no longer available through any official channel.

This project preserves the game for offline single-player play. All code in this repository (build scripts, documentation, overlay source) is original work created through reverse engineering for interoperability purposes under 17 U.S.C. § 1201(f). The EDS encryption was reverse-engineered to achieve device compatibility with hardware released after the game's discontinuation.

The game cache is distributed because EA's asset delivery servers are permanently offline — without it, the app cannot function. All server URLs in the binary have been rewritten to localhost; the game makes zero network requests to EA infrastructure.

If you are a rights holder and believe this project infringes your copyright, please open an issue and we will respond promptly.

### License

All original code in this repository is released under the [MIT License](LICENSE).
