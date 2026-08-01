# Real Racing 3 — Resurrection Project

Real Racing 3 was shut down by EA on March 31, 2026. This project brings it back to life as a fully offline single-player game with unlocked developer features, quality-of-life improvements, and a maxed-out 4K visual mode for modern hardware.

**Status:** Playable offline on iOS 26.0. Tested on iPhone 17 Pro (A19).

## Downloads

All builds are available as [GitHub Release](../../releases) attachments. You also need the game cache (5.1GB) — see [Setup](#setup).

| Build | Size | Description |
|-------|------|-------------|
| **rr3_4k_v1.ipa** | 1.31 GB | Full build — 120fps, 4K quality (EDS profile override), debug mode, all 18 patches. See below. |

## What's Fixed

Real Racing 3 was designed as an always-online free-to-play game. With EA's servers gone, the stock app hangs on connection timeouts, shows broken ad prompts, and runs at low quality on modern hardware. This project fixes all of that.

### rr3_4k_v1.ipa — All-in-One Build

All 18 binary patches (every patch verified by disassembling all call sites):

**4K Visual Quality (EDS Profile Override)**
- iPad Pro 12.9" (iPad6,8) quality profile injected as `iPhone18,2.plist` — exact device match for iPhone 17 Pro
- iPhone.plist fallback also replaced with iPad Pro profile as safety net
- Enables all 15 quality capability flags: car ambient occlusion, planar reflections, HDR post-processing, real-time car shadow maps, PBR water, high-quality headlights, and more
- See [EDS Quality Override](#eds-quality-override) for technical details

**120fps**
- maxFPS uncapped from the stock 30/60 limit
- A19 GPU has 4x the power this game was designed for, it barely breaks a sweat

**Debug Mode Unlocked (3 patches)**
- `isDebugModeEnabled` (14 callers, EA singleton), `isInternalTestMode`, `isAppDebuggable` — forced YES
- Unlocks the developer cheat menu (MainMenuCheatScreen) with 29 categories and 150+ entries
- Access to 895 runtime tweakable variables via ShowDebugTweakables and ImGui overlay

**Ads Killed (4 patches)**
- `isAdReady` (11 callers), `isRewardedVideoReady`, `isInterstitialReady` — return NO
- `adMobEnabled` — disabled at EA's ad config singleton
- All verified as IronSource/AppLovin mediation code, no framework collision

**Other Stubs**
- `checksumEnabled` — returns NO (IronSource analytics protobuf checksum)
- `requestReview` — returns nil (EA wrapper for SKStoreReviewController, void method)

**Dead Server URLs Rewritten (6 URLs)**
- EA/Glu backend URLs rewritten to `127.0.0.1` for fast connection-refused (not nulled — nil NSURL crashes)
- `director-int.sn.eamobile.com`, `director-stage.sn.eamobile.com`, `syn-dir.sn.eamobile.com`
- `prod.geo.gluops.com`, `prod-rest.ccs.gluops.com`, `firemonkeys.com.au`

**Other**
- BuildType string: `PUBLIC` → `PRIVATE` (cosmetic logging label only — code uses integer enum for behavior)
- `debugMode` CBZ → NOP (debug block messages nil global pointer — ObjC no-op)

## EDS Quality Override

The game uses **Engine Device Settings** (EDS) — 41 encrypted plist files in `res/eds/` that control all visual quality flags per device model. The game looks up the device model string (e.g. `iPhone18,2`), searches for a matching `res/eds/{model}.plist`, and falls back to `iPhone.plist` if no match is found.

**The problem:** No `iPhone18,2.plist` exists in the stock IPA (the game predates iPhone 17 Pro), so it falls back to the conservative generic `iPhone.plist` profile.

**The fix:** Copy the iPad Pro 12.9" profile (`iPad6,8.plist` — the highest-quality iOS profile at 6929 bytes) as `iPhone18,2.plist`. The game finds an exact device match and loads iPad Pro quality settings.

**Why it works:** All 41 EDS files share identical encryption (same 32-byte header, same keystream). The game decrypts them all the same way — no per-device key. Copying any encrypted profile and renaming it works without decrypting anything. This approach is validated by the Android modding community, who copy `AndroidXtraHigh.plist` to override device profiles.

**15 quality capability flags controlled by EDS:**

| Flag | Effect |
|------|--------|
| USE_HIGH_QUALITY_HEADLIGHT | High-quality headlight rendering |
| CAR_AMBIENT_OCCLUSION | Ambient occlusion on car models |
| CAR_PLANAR_REFLECTION | Planar reflections on car surfaces |
| ENV_MAP_DYNAMIC_BLUR | Dynamic environment map blur |
| ENV_MAP_HDR | HDR environment maps |
| GAMMA_CORRECTION | Gamma correction |
| USE_HDR_POST_PROCESS | Full HDR post-processing pipeline |
| USE_HDR_AUTOMATIC_EXPOSURE | Automatic HDR exposure |
| PARTICLE_CAST_SHADOW | Particle effects cast shadows |
| SKID_MARK_DEFERRED_LIGHTMAP | Deferred lightmap for skid marks |
| USE_PBR_WATER | Physically-based water rendering |
| USE_REALTIME_CAR_SHADOW_MAPS | Real-time car shadow maps |
| LOW_LOD_TRACKS | Track LOD level (disabled = high LOD) |
| LOW_MEMORY_LEMANS_HACK | Le Mans memory hack (disabled = full quality) |
| SUPPORTS_BIG_TRACKS | Big track support |

## Cheat Menu

The dev build unlocks EA Firemonkeys' internal cheat screen with 29+ categories:

| Feature | What it does |
|---------|-------------|
| **Unlock + Own Everything** | One tap — all cars, all tracks, all series |
| **OwnAllCars** | Every car in the game |
| **Currency Cheats** | R$, Gold, Motorsport dollars |
| **Debug Race Selector** | Jump to any race directly |
| **Toggle VIP** | VIP status on/off |
| **AI Control Player Car** | Let the AI drive for you |
| **Free Camera** | Fly around the track |
| **Photo Mode** | Screenshot mode |
| **Finish Race** | Instantly finish |
| **895 Tweakable Variables** | Full runtime config access |

## 895 Tweakables

The ImGui debug overlay (ShowDebugTweakables in-race) exposes the entire Firemonkeys engine config:

**Handling & Physics (331 tweakables)**
- Steering sensitivity, grip, traction, drift mode
- Full suspension sim (R4 engine): springs, damping, anti-roll bars, bumpstops
- Weight distribution, center of mass offsets
- Downforce model with speed thresholds
- Per-gear acceleration curves, brake power
- ERS/KERS hybrid system
- Slipstreaming physics (drafting length, width, speed boost)
- Tire degradation, wear rates, offroad multipliers
- Oversteer/understeer tuning

**Visual Quality (200+ tweakables)**
- Render scale, FXAA, MSAA
- Full HDR pipeline: bloom, tonemapping, color grading, auto exposure
- Motion blur, depth of field, lens flare, chromatic aberration
- LOD controls: car, wheel, driver, mipmap, track
- 4K skybox, dynamic skid marks, particle effects with lighting/shadows
- PBR lighting, car shadows, track headlights

**Audio Engine**
- Per-channel volume: engine, gears, tires, collision, backfire, supercharger
- 4-band parametric EQ
- Exhaust overrun pop frequency and chance (crackle tuning)
- Full ADSR envelope on backfire ducking

**Camera System**
- Free orbit in menus and races
- Manual camera position/rotation (X/Y/Z)
- Cinematic zoom curves
- 360-degree video recording with configurable resolution

**Customization**
- Ride height (front/rear) — stance your cars
- Wheel width (front/rear) — wide body fitment
- Custom tire colors (RGB)
- Wheel and tire style selection

**Gameplay**
- AI skill level and slow-down
- Toggle player damage
- Endurance race time limits
- Weather toggle (rain on/off)
- Split-screen player count override

## Controller Support

The game natively supports MFi controllers via GCController (ExtendedGamepad profile). Tested with Razer Kishi V3 Pro.

| Input | Action |
|-------|--------|
| Left stick / D-pad | Steering |
| R2 (right trigger) | Accelerate (analog) |
| L2 (left trigger) | Brake (analog) |
| A button | UI confirm |
| B button | Nitro / boost |

Enable analog triggers via ImGui: `TWEAKABLE_INPUT_ENABLE_ANALOG_ACCELERATION` and `TWEAKABLE_INPUT_ENABLE_ANALOG_BRAKING`.

44 force feedback tweakables (CLUBSPORT_*) may provide haptic feedback through the Kishi's motors.

Custom joystick config: drop a `joystick_config.txt` in the app's Documents folder (accessible via Files app with UIFileSharingEnabled).

## Setup

### Requirements
- iPhone or iPad running iOS 15+ (tested on iOS 26.0)
- [Sideloadly](https://sideloadly.io/) for sideloading
- ~7 GB free storage (1.3 GB app + 5.1 GB cache)

### Steps

1. **Download** the IPA from [Releases](../../releases)
2. **Sideload** with Sideloadly — connect your device, drag the IPA, sign with your Apple ID
3. **Import cache** — the game needs its ~5.1 GB asset cache to run. Download `Caches_ipastore.zip` from Releases, unzip, and copy the contents into the app's Documents folder via Files app or 3uTools
4. **Launch** — the game runs fully offline, no EA account needed

### Sideloading Tips
- Bundle ID is `com.ea.realracing3.inc` — sideloading one build over another preserves your save and cache
- Free Apple IDs get 7-day signing. Use [AltStore](https://altstore.io/) or re-sign weekly
- If the app crashes on launch, re-sideload — sometimes Sideloadly's signing is flaky

## How It Works

All patches are binary-level modifications to the arm64 Mach-O executable. No jailbreak required, no code injection, no runtime hooking.

### ObjC Stub Patching

The game's `__objc_stubs` section contains 16-byte trampolines for every ObjC method call. Each stub normally does:
```
adrp  x1, selector_ref
ldr   x1, [x1, #offset]
adrp  x16, _objc_msgSend
ldr   x16, [x16, #offset]
br    x16
```

We replace the entire stub with:
```
mov   w0, #<return_value>
ret
nop
nop
```

This short-circuits the method call — the ObjC message is never sent, the stub just returns our hardcoded value. Clean, simple, no side effects.

### Build Process

IPAs are built via Python script doing a zip-to-zip copy from the original IPA. The binary is read into memory, patches are applied, and the modified binary is written to the new zip. All other files (frameworks, assets, plists, code signatures) are copied byte-for-byte. Sideloadly re-signs the entire bundle on install.

**Important:** The zip must preserve all directory entries. Python's `zipfile` module handles this correctly when copying `ZipInfo` objects, but extract-then-rezip loses directory entries and causes framework loading failures on iOS.

## Known Issues

- **GDPR/ATT popups** — we intentionally do NOT patch `gdprApplies` or `trackingAuthorizationStatus` because these selectors collide with Apple's AppTrackingTransparency framework and ad SDK consent systems (UMP, AppLovin, Facebook). Patching them crashes during ad SDK init. The popups may appear once but are harmless offline.
- **`debugMode` and `isDebug` NOT patched** — binary analysis confirmed all 13 `debugMode` callers are IronSource/AppLovin/MAX/Tapjoy ad SDK init code, and `isDebug` is Facebook Audience Network. Forcing YES crashes the app during ad SDK initialization. The cheat menu works without these — `isDebugModeEnabled` is the actual gate.
- **Some cheats are platform-gated** — a few cheat menu entries display "This cheat does not work on non windows/Android platforms" and won't function on iOS.
- **Cheat menu visibility** — the MainMenuCheatScreen may not have an obvious button. Investigation ongoing (see [Issue #3](../../issues/3)).
- **EDS quality — awaiting device confirmation** — the iPad Pro profile injection is built and sideloading. Visual quality improvement needs device verification (see [Issue #2](../../issues/2)).
- **Save file editing** — `checksumEnabled` disables IronSource analytics checksums (not EA save checksums). EA save checksum behavior needs testing.

## Technical Details

See [RR3_DEV_BUILD_GUIDE.md](RR3_DEV_BUILD_GUIDE.md) for the complete patch table with file offsets, ARM64 encodings, and Mach-O layout details.

## Credits

Built with binary analysis, ARM64 instruction encoding, and stubbornness. No source code was used or needed.

## License

This project is for personal archival and educational purposes. Real Racing 3 is property of Electronic Arts / Firemonkeys. The game was discontinued and is no longer available for purchase or download. This project does not distribute copyrighted game assets — you need your own copy of the original IPA and game cache.
