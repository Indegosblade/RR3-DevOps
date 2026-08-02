# Patch Reference

Complete technical reference for all binary patches applied to Real Racing 3.

Every patch was verified by disassembling all call sites in the binary. Selectors with confirmed ad SDK collisions (`debugMode`, `isDebug`, `gdprApplies`, `trackingAuthorizationStatus`) were identified and excluded.

## Patch Table

### Debug Gates (3 stubs -> YES)

| Selector | Offset | Callers | Owner | Effect |
|----------|--------|---------|-------|--------|
| `isDebugModeEnabled` | 0x022CCAA0 | 14 | EA singleton (`[monitor isDebugModeEnabled]`) | Main gate — enables cheat menu entries, debug UI |
| `isInternalTestMode` | 0x022CE3E0 | 5 | Ad mediation feature gate | Bypasses secondary checks |
| `isAppDebuggable` | 0x022CB9C0 | 2 | Ad telemetry (dead servers) | Reports debuggable=YES to dead analytics |

### Ad Removal (4 stubs -> NO)

| Selector | Offset | Callers | Owner | Effect |
|----------|--------|---------|-------|--------|
| `isAdReady` | 0x022CB460 | 11 | IronSource/AppLovin mediation | No ads ever "ready" |
| `isRewardedVideoReady` | 0x022D0120 | 2 | IronSource | No rewarded video |
| `isInterstitialReady` | 0x022CE4A0 | 2 | IronSource | No interstitial |
| `adMobEnabled` | 0x022812E0 | 1 | EA ad config singleton | AdMob disabled |

### Other Stubs

| Selector | Offset | Return | Callers | Owner | Effect |
|----------|--------|--------|---------|-------|--------|
| `checksumEnabled` | 0x02292440 | NO | 1 | IronSource analytics | Skips protobuf checksum (NOT EA save anti-tamper) |
| `maxFPS` | 0x022DACE0 | 120 | — | EA engine | Uncaps framerate to 120fps |
| `requestReview` | 0x022F6560 | nil | 1 | EA (void method, wraps SKStoreReviewController) | Suppresses rate popup |

### Non-Stub Patches

| Patch | Offset | Effect |
|-------|--------|--------|
| debugMode CBZ -> NOP | 0x01267420 | Debug block sends `colorWithRed:green:blue:alpha:` to nil global — ObjC no-op |
| BuildType "PRIVATE" | 0x024F6480 | Cosmetic logging label (integer enum drives actual code paths) |

### URL Rewrites (127.0.0.1)

| Offset | Original URL |
|--------|-------------|
| 0x026F5B86 | `director-int.sn.eamobile.com` |
| 0x026F5BAB | `director-stage.sn.eamobile.com` |
| 0x026F5BD2 | `syn-dir.sn.eamobile.com` |
| 0x026CB1A2 | `prod.geo.gluops.com/geoservice/v2/publishdetailed` |
| 0x026E787D | `prod-rest.ccs.gluops.com/api/v1/putData` |
| 0x02743860 | `firemonkeys.com.au/news/embednews/index.php?nGameId=` |

### Excluded Patches (confirmed crash causes)

| Selector | Reason |
|----------|--------|
| `debugMode` -> YES | All 13 callers are IronSource/AppLovin/MAX/Tapjoy ad SDK init code. Forces ad SDKs into debug mode -> crash. |
| `isDebug` -> YES | Facebook Audience Network selector. Forces FB ad debug mode. |
| `gdprApplies` -> NO | Collides with UMP/AppLovin/Facebook consent SDKs. Skips consent singleton init -> nil dereference. |
| `trackingAuthorizationStatus` -> 3 | Collides with Apple's ATTrackingManager framework. Untested init path. |

## Cheat Menu (29 categories, 150+ entries)

The binary contains EA Firemonkeys' complete internal developer cheat screen. Below is the full inventory extracted from binary analysis.

### Character
- **Unlock + Own Everything** — one tap, confirmation dialog
- OwnAllCars, Unlock Everything, Lock All Streams, Unlock Next Series, Unlock All Tracks
- Give XP / Give driver levels / Almost level
- Give money / Give gold / Clear money & gold / Spend Money & Wrenches
- Save game / Clear local save / Graceful Resume / Gradual Resume
- Toggle Mtx Purchase Made / Validate user data / Check for update
- View Server Popups / Export Save Size Breakdown
- Early Access (Reset/Enable/Disable) / Clear purchased packs

### Career
- Reload event data / Win all events / Win tapped event
- Bypass Locked Series / Show Events Completed / Force new series names
- Tutorial: Skip Tutorial, Skip Persistent Content FTUE, Skip Seasons FTUE, Reset FTUE, Skip Servicing+Upgrades FTUE

### Car
- ALL ONE CAR / RANDOM OPPONENT CARS / ALL HIGH LOD
- Upgrade all cars / Damage / Degrade / Repair / Disable Damage
- Remove Upgrades / Remove Car / Remove All Cars
- Toggle VIP / Lend Car / Return All Cars / Set Rental Time Remaining
- Play Animation / Show damage data postrace / +/- Upgrade PR Weight

### Camera
- Toggle Free Orbit Cam / Dump Orbit Cam Pos / +/- Orbit FOV / Elongated Orbit Type

### Customisation
- Enable Interface / Use Garage Scene / Show Paint Test UI
- Unlock All / Lock All / Force Upload
- Enable Tyres / Enable Ride Height / Enable Profiles
- Toggle Disk Cache / Add/Clear Decals / Opponents Max Decals

### Other Categories
- **Time** — Override Server Time, Add/Remove Days/Hours/Minutes/Seconds
- **Sales** — Debug sales, sale variants, targeted sales
- **Cloudcell** — IAP, sandbox, dev/stage servers, customer support
- **OMP** — Online multiplayer, tournaments, dedicated servers, matchmaking
- **LTS** — Live time series, schedules, community events
- **Time Trials** — WTT/TTC, Formula E
- **Gamepads** — Print inputs, find controllers, reload joystick config
- **Replay** — Hide UI, allow cams in race, purge cache
- **RaceTeams** — Member ID, rewards, notifications
- **Uncommon** — AttractMode, experiments, NFC debug, mail toaster, auto play, PVP ping test

### In-Race Debug Commands

| Command | Effect |
|---------|--------|
| FinishRace | Instantly finish the race |
| TeleportPlayer | Teleport car position |
| AI_CONTROL_PLAYER_CAR | Let AI drive |
| ToggleFreeCamera | Free-roam 6DOF camera |
| ToggleImGuiToolsMenu | ImGui debug overlay |
| ShowDebugTweakables | 895 tweakable variables |
| ToggleDebugWindow | Debug info window |
| Toggle3DRender | Disable 3D rendering |
| ToggleTVCamera | TV broadcast camera |

## Tweakable Variables (895 across 39 categories)

The ImGui debug overlay exposes the entire Firemonkeys engine configuration at runtime.

### Physics & Handling (331 tweakables)
- Steering sensitivity, grip, traction, drift mode
- Full suspension simulation: springs, damping, anti-roll bars, bumpstops
- Weight distribution, center of mass offsets, downforce model
- Per-gear acceleration curves, brake power, ERS/KERS hybrid system
- Slipstreaming physics, tire degradation, oversteer/understeer tuning

### Visual Quality (200+ tweakables)
- Render scale, FXAA, MSAA, full HDR pipeline (bloom, tonemapping, color grading)
- Motion blur, depth of field, lens flare, chromatic aberration
- LOD controls (car, wheel, driver, mipmap, track)
- PBR lighting, car shadows, skybox, dynamic skid marks, particles

### Audio
- Per-channel volume (engine, gears, tires, collision, backfire, supercharger)
- 4-band parametric EQ, exhaust crackle tuning (ADSR envelope)

### Camera
- Free orbit in menus and races, manual position/rotation
- Cinematic zoom curves, 360-degree video recording

### Gameplay
- AI skill level and slow-down, player damage toggle
- Endurance time limits, weather toggle, split-screen count override

## Hidden Modes

| Mode | Activation |
|------|-----------|
| **Photo Mode** | `TWEAKABLE_PHOTO_MODE_ENABLED` — full UI with brightness, contrast, exposure, filters |
| **eSports Demo** | Broadcast cameras (Pedestal, Track, Heli, Blimp, Roof, Dash) |
| **Machine Learning** | Launch arg `-demo_mode=MachineLearning` — agent-driven mode |
| **Attract Mode** | Cheat menu: Uncommon > AttractMode > Force |
| **Auto Play** | AI drives with ad overlay system |

## Controller Support

Native MFi controller support via GCController (ExtendedGamepad profile).

| Input | Action |
|-------|--------|
| Left stick / D-pad | Steering |
| R2 (right trigger) | Accelerate (analog) |
| L2 (left trigger) | Brake (analog) |
| A button | UI confirm |
| B button | Nitro / boost |

Enable analog triggers via ImGui tweakables: `TWEAKABLE_INPUT_ENABLE_ANALOG_ACCELERATION` and `TWEAKABLE_INPUT_ENABLE_ANALOG_BRAKING`.

44 force feedback tweakables (CLUBSPORT_*) may provide haptic feedback through compatible controllers.

Custom mapping: drop `joystick_config.txt` in the app's Documents folder.

## Droppable Config Files

These files are loaded from the app's Documents folder at runtime:

| File | Purpose |
|------|---------|
| `joystick_config.txt` | Custom controller button/axis mapping |
| `cheat_macro.bin` | Cheat macro recording/playback |
| `settings.json` | Game settings override |
| `DebugRaceSelect.2.cfg` | Debug race selector config |
| `track_sponsor_overrides.txt` | Track sponsor customization |

## Deep Links (Safari)

| URL | Destination |
|-----|------------|
| `rr3://RaceTeamsAdmin` | Race teams admin panel |
| `rr3://RaceTeams` | Race teams menu |
| `rr3://STREAM/<id>` | Jump to career stream |

## EDS Encryption (Engine Device Settings)

41 encrypted XML plists in `res/eds/`, one per device model. Each contains 113 quality settings (AA, shadows, reflections, HDR, LODs, cubemap resolution, particle effects, PBR water, etc.).

### Algorithm: Modified RC4

Function at VA `0x100726200`. Standard RC4 with two modifications.

### Key

```
a5 35 b3 b1 e8 43 e7 cf
```

8 bytes, hardcoded via MOV/MOVK at `0x1007262a8`:
```arm64
mov  x8, #0x35a5
movk x8, #0xb1b3, lsl #16
movk x8, #0x43e8, lsl #32
movk x8, #0xcfe7, lsl #48
stur x8, [x29, #-0x80]
```

### RC4 Modifications

1. **Post-KSA scramble** — after the standard 256-iteration KSA, a second swap pass runs over S-box indices 1–133 with `j` reset to 0. No key material, just `j += S[i]` and swap.
2. **PRGA starts at i=133** (`0x85`) instead of 0. `j` carries from the post-KSA scramble. Skips the weak early RC4 keystream bytes.

Initial S-box is the standard identity permutation `{0, 1, ..., 255}` (loaded from `__DATA_CONST` at `0x102342df0`).

### Python (encrypt = decrypt, RC4 is symmetric)

```python
EDS_KEY = bytes([0xa5, 0x35, 0xb3, 0xb1, 0xe8, 0x43, 0xe7, 0xcf])

def eds_crypt(data):
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + EDS_KEY[i % 8]) & 0xFF
        S[i], S[j] = S[j], S[i]
    j2 = 0
    for buf_idx in range(3, 0x88):
        si = buf_idx - 2
        j2 = (j2 + S[si]) & 0xFF
        S[si], S[j2] = S[j2], S[si]
    i = 0x85; j3 = j2
    out = bytearray(len(data))
    for n in range(len(data)):
        i = (i + 1) & 0xFF
        j3 = (j3 + S[i]) & 0xFF
        S[i], S[j3] = S[j3], S[i]
        out[n] = data[n] ^ S[(S[i] + S[j3]) & 0xFF]
    return bytes(out)
```

### Separate XOR system (shaders/textures)

`deScrambleData_XOR` at `0x100912a68` uses a different scheme: repeating 64-byte ASCII hex key followed by zlib decompression. Key: `B91BBEDDCE710201C5F1FF672AA71CF0399B43E6F6A62761DDBD0A7C8FBE71F2`. NOT used for EDS files.

### God-mode quality profile

The v3 4K build starts from the iPad Pro 12.9" (iPad6,8) baseline — the highest stock quality tier — and applies 4 safe upgrades on top. The `PLIST_IDENTIFIER` is kept as `iPad6,8` because the engine uses it for internal resource lookups (shader caches, texture atlases, asset bundles), not device matching. The filename (`iPhone18,1.plist`) handles device matching. GUI settings (layout extension, auto-scale, font page size, high-res menu) are kept at iPad values to match the resource set referenced by the identifier.

Key settings beyond the iPad Pro 12.9" baseline:

| Setting | iPad Pro | God Mode | Notes |
|---------|----------|----------|-------|
| `USE_ANISOTROPIC_FILTERING` | false | true | Lightweight, big visual impact |
| `STREAMING_CAR_SHADOW_MAPS` | false | true | Progressive shadow loading |
| `PROP_MIN_COVERAGE` | 0.005 | 0.001 | Finer prop detail at distance |
| `PIXEL_THRESHOLD_CUBEMAP_LOW_DETAIL` | 400 | 800 | Higher threshold for cubemap LOD |

Settings kept at iPad Pro baseline (not maxed) to avoid crashes and thermal throttling:

| Setting | Value | Reason |
|---------|-------|--------|
| `PLIST_IDENTIFIER` | iPad6,8 | Engine uses for resource lookups. Unknown identifiers crash (null asset handle). |
| `EXPECTED_SCREEN` | 2732x2048 | Must match GUI cluster. Mismatched resolution + GUI settings = layout crash. |
| `GUI_LAYOUT_EXTENSION` | _1024x768 | iPad resource set. Mixing iPhone GUI with iPad identifier crashes. |
| `CUBE_MAP_DIMENSIONS` | 512 | 1024 only on SimRigTV (active cooling). No mobile device uses it. |
| `CREATE_FULL_SCREEN_BUFFERS` | false | Zero of 41 device profiles use true. Allocates unused framebuffers. |
| `HAS_PHOTO_MODE` | false | Untested on phone — may require iPad-class resources. |
| `SPLIT_SCREEN_DYNAMIC_REFLECTIONS` | false | Split-screen feature, not needed for single-screen play. |

The encrypted god plist is injected as both `iPhone18,1.plist` (direct model match for iPhone 17 Pro) and `iPhone.plist` (fallback for unknown devices).

## ObjC Stub Encoding

Each `__objc_stubs` trampoline is 16 bytes. Stock:
```
adrp  x1, selector_ref
ldr   x1, [x1, #offset]
adrp  x16, _objc_msgSend
ldr   x16, [x16, #offset]
br    x16
```

Patched (return constant):
```
mov   w0, #<value>    ; 0x52800000 | (imm << 5)
ret                   ; 0xD65F03C0
nop                   ; 0xD503201F
nop                   ; 0xD503201F
```

Patched (return nil):
```
mov   x0, #0          ; 0xD2800000
ret                   ; 0xD65F03C0
nop                   ; 0xD503201F
nop                   ; 0xD503201F
```
