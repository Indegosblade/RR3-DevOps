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
