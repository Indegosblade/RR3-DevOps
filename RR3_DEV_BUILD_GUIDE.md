# Real Racing 3 — Dev Build Guide

**Build:** rr3_dev.ipa (1.31 GB, 18 binary patches, code-verified)
**Date:** 2026-08-01
**Target:** iPhone 17 Pro (A19, iOS 26.0, stock, Sideloadly)

## Quick Start

1. Sideloadly > drag `rr3_dev.ipa` > sideload to 17 Pro
2. Import 5.1GB cache into Documents folder (Files app or 3uTools)
3. Launch — cheat menu should appear on main menu
4. Tap "Character > Unlock + Own Everything" to unlock all content

## What's Patched (18 binary patches, all code-verified)

Every patch was verified by disassembling all call sites in the binary. Two selectors (`debugMode`, `isDebug`) were confirmed as ad SDK collisions and killed.

### Debug Gates (3 stubs → YES)
| Selector | Offset | Callers | Owner | Effect |
|----------|--------|---------|-------|--------|
| `isDebugModeEnabled` | 0x022CCAA0 | 14 | EA singleton (`[monitor isDebugModeEnabled]`) | Main gate — enables cheat menu entries, debug UI |
| `isInternalTestMode` | 0x022CE3E0 | 5 | Ad mediation feature gate | Bypasses secondary checks, adds features to list |
| `isAppDebuggable` | 0x022CB9C0 | 2 | Ad telemetry (dead servers) | Reports debuggable=YES to dead analytics |

### Kill Ads (4 stubs → NO)
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
| `maxFPS` | 0x022DACE0 | 60 | — | EA engine | 60fps cap (use 4K build for 120) |
| `requestReview` | 0x022F6560 | nil | 1 | EA (void method, wraps SKStoreReviewController) | Kills rate popup |

### Non-Stub Patches
| Patch | Offset | Effect | Verified |
|-------|--------|--------|----------|
| debugMode CBZ → NOP | 0x01267420 | Debug block sends `colorWithRed:green:blue:alpha:` to nil global → ObjC no-op | Safe |
| BuildType "PRIVATE" | 0x024F6480 | Cosmetic logging label (enum-to-string table, 1 of 5 copies). Does NOT change engine behavior — integer enum drives code paths | Safe but useless |
| 6x URL → 127.0.0.1 | various | Fast connection-refused on tested failure path. NOT null (nil NSURL = NSInvalidArgumentException crash) | Safe |

### URL Rewrites (127.0.0.1, not null)
| Offset | Original URL |
|--------|-------------|
| 0x026F5B86 | `director-int.sn.eamobile.com` |
| 0x026F5BAB | `director-stage.sn.eamobile.com` |
| 0x026F5BD2 | `syn-dir.sn.eamobile.com` |
| 0x026CB1A2 | `prod.geo.gluops.com/geoservice/v2/publishdetailed` |
| 0x026E787D | `prod-rest.ccs.gluops.com/api/v1/putData` |
| 0x02743860 | `firemonkeys.com.au/news/embednews/index.php?nGameId=` |

### Killed Patches (confirmed crash causes)
| Selector | Why killed |
|----------|-----------|
| `debugMode` → YES | ALL 13 callers are IronSource/AppLovin/MAX/Tapjoy ad SDK init code. Forces all ad SDKs into debug mode during init → crash |
| `isDebug` → YES | 1 caller in Facebook Audience Network. Forces FB ad debug mode |
| `gdprApplies` → NO | Collides with UMP/AppLovin/Facebook consent SDKs. Skips consent singleton init |
| `trackingAuthorizationStatus` → 3 | Collides with ATTrackingManager (Apple framework). Untested init path |

---

## Cheat Menu (29 categories, 150+ entries)

### Character
- **Unlock + Own Everything** — one tap, confirmation dialog: "Do you REALLY want to Unlock and Own Everything?"
- OwnAllCars — every car (needs cache downloaded)
- Unlock Everything / Lock All Streams / Unlock Next Series / Unlock All Tracks
- Give XP / Give driver levels / Almost level
- Give money / Give gold / Clear money & gold / Spend Money & Wrenches
- Save game / Clear local save / Graceful Resume / Gradual Resume
- Simulate failed VIP purchase / Toggle Mtx Purchase Made / Validate user data
- Check for update / View Server Popups / Export Save Size Breakdown
- Early Access (Reset/Enable/Disable)
- Clear purchased packs

### Career
- Reload event data / Win all events / Win tapped event
- Bypass Locked Series / Show Events Completed / Force new series names
- **Tutorial submenu:** Skip Tutorial, Skip Persistent Content FTUE, Skip Seasons FTUE, Reset FTUE, Skip Servicing+Upgrades FTUE

### Car
- ALL ONE CAR / RANDOM OPPONENT CARS / ALL HIGH LOD
- Upgrade all cars / Damage / Degrade / Repair / Disable Damage
- Remove Upgrades (all or current) / Remove Car / Remove All Cars
- Toggle VIP / Lend Car / Return All Cars / Set Rental Time Remaining
- Play Animation / Show damage data postrace / +/- Upgrade PR Weight

### Camera
- Toggle Free Orbit Cam / Dump Orbit Cam Pos / +/- Orbit FOV / Elongated Orbit Type

### Customisation
- Enable Interface / Use Garage Scene / Show Paint Test UI
- Unlock All / Lock All / Force Upload
- Enable Tyres / Enable Ride Height / Enable Profiles
- Toggle Disk Cache / Decals Use Step Func
- Add/Clear Decals (current or all cars) / Opponents Max Decals

### HiddenValue
- Test Hack / Stress Test

### Time
- Override Server Time / Force Unreliable
- Reset / Add/Remove Days/Hours/Minutes/Seconds

### Sales
- Clear/Sync sales / Add debug sales / Create sale
- Show Accelerator Packs / Show CRI Packs
- Sale Debugging toggle / Reset Racers Choice Popup
- **TargetedSales submenu:** Show Info, Debug Pending Sales Popup, Check triggers, Add sale variants (single item, compare, pack, car pack, car with popup, post purchase fame bonus)

### Cloudcell
- IAP Purchase $100k / Advertising Forget Ads / Resynch
- Connect Dev/Stage/Sandbox / Change sandbox host name
- Show/Request Rate App / Purchase Validation
- Download/Reload Live Save / Customer Support
- Log Authentication Ids / Force EU Region / FB share AI as friends
- Country Code Info / Modify Track Id On Upload

### OMP (Online Multiplayer)
- End Tournament / Set/Clear/Force Last Played Schedule
- Display connectivity/p2p timing / Disable Idle Disq
- Dedicated Servers / MP Server / Matchmaking settings

### LTS (Live Time Series)
- Default Schedule / Reload UI Descriptions / Community submenu

### Time Trials
- EnableLiveDON / Force Version/Season Reset / Clear Formula E Signup
- WTT/TTC submenus

### Gamepads
- Print inputs / Find Controllers / Reload Joystick Config

### Replay
- Hide UI / Allow Cams In Race / Purge replays from cache

### RaceTeams
- Member Id / Reset Member Id / Reset Rewards / Test Reward / Test Notification

### Uncommon
- AttractMode Force / Collections Reset/Complete/ToggleTutorialType
- Experiments (Tango Create/Start/Stop/Destroy, NFC Open debug screen)
- Mail toaster test / Toggle Auto Play / Delete TTK File / Toggle Pre Race Freeze
- PVP Ping Test / Tier Unlock adjustments (RDtoGOLD/BASEWeight/TotalGold)

### Other Categories
- Metagame Debugging / UI (View Landing Page) / Multi-Car / Quests / Profile
- RemoteGarage / Time Penalty / Rendering (Label Test)

### Deep Link Entry
The cheat menu has a text field that prepends `rr3://` to any input. Type a path and go.

### Platform Warning
Some cheats display: "This cheat does not work on non windows/Android platforms" — a few menu items are platform-gated and won't work on iOS.

---

## In-Race Debug Commands

| Command | Effect |
|---------|--------|
| FinishRace | Instantly finish |
| TeleportPlayer | Teleport your car |
| PhysicsExplode | Blow up physics |
| AI_CONTROL_PLAYER_CAR | Let AI drive |
| ToggleFreeCamera | Free-roam camera (6DOF) |
| ToggleImGuiToolsMenu | ImGui debug overlay |
| ShowDebugTweakables | 895 tweakable variables |
| ToggleDebugWindow | Debug info window |
| Toggle3DRender | Disable 3D rendering |
| ToggleTVCamera | TV broadcast camera |

---

## Hidden Modes

### Photo Mode
- `TWEAKABLE_PHOTO_MODE_ENABLED` — master toggle
- Full UI: brightness, contrast, exposure, saturation, hue, temperature, FOV
- Filter system with purchasable packs
- AR photo mode (`GAMETEXT_PHOTO_MODE_PLUS_*`)
- Screenshot watermark toggle (`PhotoMode_CanShowCarNameWaterMark`)

### eSports Demo Mode
- Broadcast cameras: Pedestal, Track, Heli, Blimp, Roof, Dash
- Config: `demo_modes/esports_demo`

### Machine Learning Mode
- Launch arg: `-demo_mode=MachineLearning`
- Human Performance Recording / Agent Driven mode

### Attract Mode (Idle Demo)
- Force via cheat menu: Uncommon > AttractMode > Force

### Auto Play
- AI drives while recording, with ad overlay system
- `TWEAKABLE_MULTIPLAYER_TOGGLE_AI_CONTROL`

---

## Droppable Config Files

These files are loaded from the app's Documents folder at runtime (accessible via Files app with UIFileSharingEnabled=YES):

| File | Purpose |
|------|---------|
| `joystick_config.txt` | Custom controller button/axis mapping |
| `joystick_config_esports.txt` | eSports controller preset |
| `joystick_config_manufacturer_demo.txt` | Demo mode controller preset |
| `cheat_macro.bin` | Cheat macro recording/playback |
| `settings.json` | Game settings override |
| `DebugRaceSelect.2.cfg` | Debug race selector config |
| `track_sponsor_overrides.txt` | Track sponsor customization |
| `esports_configuration.txt` | eSports mode configuration |
| `demo_settings_ea_play.xml` | EA Play demo settings |
| `demo_settings_porsche.xml` | Porsche demo settings |
| `demo_settings_mclaren_shadow_project.xml` | McLaren Shadow Project demo |

---

## Deep Links (Safari)

| URL | What it opens |
|-----|---------------|
| `rr3://RaceTeamsAdmin` | Race teams admin panel |
| `rr3://RaceTeams` | Race teams menu |
| `rr3://MULTIPLAYERINVITE/server:port:room:key` | MP invite handler |
| `rr3://STREAM/<id>` | Jump to career stream |

---

## Controller Support (Razer Kishi V3 Pro)

The game natively supports GCController (ExtendedGamepad profile). Kishi V3 Pro connects via USB-C passthrough.

### Default Controls
| Input | Action |
|-------|--------|
| Left stick / dpad | Steering |
| R2 (right trigger) | Accelerate (analog) |
| L2 (left trigger) | Brake (analog) |
| A button | UI confirm |
| B button | Nitro / boost |

### Enable Analog Triggers
Via ImGui in-race (ShowDebugTweakables):
- `TWEAKABLE_INPUT_ENABLE_ANALOG_ACCELERATION`
- `TWEAKABLE_INPUT_ENABLE_ANALOG_BRAKING`

### Steering Wheel Mode
- `TWEAKABLE_INPUT_JOYSTICK_WHEEL_STEERING_OVERRIDE` — wheel steering mode
- `TWEAKABLE_INPUT_JOYSTICK_WHEEL_STEERING_SENSITVITY` — sensitivity (typo is EA's)
- `TWEAKABLE_INPUT_JOYSTICK_WHEEL_STEERING_CLAMP_MULITPLIER` — clamp multiplier
- `TWEAKABLE_INPUT_JOYSTICK_WHEEL_STEERING_AXIS_ROTATION` — axis rotation

### Force Feedback (44 CLUBSPORT_* tweakables)
Originally for racing wheels, may provide haptic feedback through Kishi motors:
- Pedal rumble, brake pressure, acceleration scale
- Min/max speed thresholds, noise rate
- `TWEAKABLE_TRANSMISSION_TORSIONAL_VIBRATION`

### Config Files
Drop `joystick_config.txt` in Documents for custom mapping. Game logs "Successfully loaded joystick settings file: %s" on success. Use `Gamepads > Reload Joystick Config` in cheat menu to reload without restarting.

---

## Tweakable Categories (39 categories, ~895 variables)

AI, ALLOW, ALT_RENDER, BULLET, CAMERA, CARSFX, CAR, COLLISION, CUBEMAP, CUSTOMISATION, CUTSCENE, DAMAGE, DEBUGRENDER, DEBUGVIEW, DRAGRACE, DRIFT, ENABLE_NASCAR, ENDURANCE, FEAT, FORCE, FRAME_RECORD, FRUSTUM, GLOBAL, HDR, HEADLIGHT, HIDE, HOTSWAP, HUD, HUNTER, INPUT, LIGHTING, LISTENER, LOWER, MENU, MISC, MULTIPLAYER, NASCAR, NETWORK, PARTICLE, PARTYPLAY, PARTY, PAUSE, PBR, PHOTO, PLAYER, POST, PROJECTION, PVS, QUESTS, RACE, REDUCE, RENDER, RESULT, ROAD, ROLLING, SHADERS, SHOW, SKIDS, SOUND, STEERING, SUSPENSION, TEXTURE, TIMETRIAL, TRACK, TRANSMISSION, VISUAL

### Fun Tweakables
| Tweakable | Effect |
|-----------|--------|
| `AI_PLAYER_AI_SKILL_LEVEL` | Control AI difficulty |
| `AI_SLOW_DOWN` | Slow down AI |
| `CAR_MAX_SPEED` | Override max speed |
| `DAMAGE_PLAYER_ENABLED` | Toggle player damage |
| `IS_RAINING` | Toggle rain |
| `SHOW_FPS` | FPS counter |
| `PHOTO_MODE_ENABLED` | Photo mode |
| `MENU_SCENE_FREE_ORBIT` | Free orbit in menus |
| `CAR_STEERING_SENSITIVITY` | Steering feel |
| `ENDURANCE_TIME_LIMIT` | Endurance race time |
| `MULTIPLAYER_TOGGLE_AI_CONTROL` | AI drives for you |

### Visual Quality
| Tweakable | Effect |
|-----------|--------|
| `RENDER_SCALE` | Resolution multiplier |
| `HDR_BLOOM_*` | Bloom intensity/threshold |
| `HDR_TONEMAPPING_*` | Tonemapping curve |
| `POST_MOTIONBLUR_*` | Motion blur |
| `POST_DOF_*` | Depth of field |
| `POST_LENSFLARE_*` | Lens flare |
| `POST_CHROMATICABERRATION_*` | Chromatic aberration |
| `PBR_*` | PBR lighting params |
| `LIGHTING_*` | Scene lighting |
| `CUBEMAP_*` | Environment reflections |
| `SKIDS_*` | Tire mark visuals |
| `PARTICLE_*` | Particle effects |

### Audio
| Tweakable | Effect |
|-----------|--------|
| `SOUND_ENGINE_*` | Engine volume/EQ |
| `SOUND_GEAR_*` | Gear change sounds |
| `SOUND_TIRE_*` | Tire squeal |
| `SOUND_COLLISION_*` | Impact sounds |
| `CARSFX_BACKFIRE_*` | Exhaust pop frequency/chance (crackle tuning) |
| `CARSFX_SUPERCHARGER_*` | Supercharger whine |

---

## Firebase Kill Switches (Remote Config — dead servers)
- `Maintenance_KillSwitch` — game maintenance mode
- `QuestUnlockSystem_KillSwitch` — quest system
- `HelpShift_KillSwitch` — customer support
- Remote config for: LevelGating, MTXTile, AdFeature, Rookie Championship

These are Firebase Remote Config keys. With dead servers they return defaults.

---

## Jailbreak Detection
- `isDeviceJailbroken` (NimbleApplicationEnvironmentImpl) — checks Cydia, MobileSubstrate, `/private/jailbreak.txt`
- `isRooted` — generic root check
- `JailbrokenMTX` — separate handling for jailbroken IAP
- Not relevant on stock iOS 26.0

---

## Dev Screens
| Screen | Purpose |
|--------|---------|
| `DebugRaceSelectScreen` | Direct race picker |
| `DebugInfoScreen` | System/build info |
| `CarDebugViewer` | Inspect car models |
| `PhotoModeScreen` | Photo mode UI |
| `OrbitModeScreen` | Orbit camera mode |

---

## Build Info (leaked from source paths)
- Build system: `/opt/scm/builds/R3_iOS_UpdateBranchA/src/...`
- Build types: PUBLIC (release), PRIVATE (dev), USER_DEF (custom)
- The binary is on the UpdateBranchA release train

---

## Sideloading

Bundle ID: `com.ea.realracing3.inc` (unchanged). Sideloading one build over another preserves Documents (save + 5.1GB cache).

1. Connect 17 Pro
2. Sideloadly > drag IPA > sign with Apple ID
3. Launch — save + cache intact

## If Cheat Menu Doesn't Appear

1. Try deep links from Safari (`rr3://RaceTeamsAdmin`)
2. The cheat screen constructor is unconditional — isDebugModeEnabled gates the entries being added
3. Look for ImGui overlay in-race (tap screen corners)
4. Backup: save file editing with Documents access (checksums are off for IronSource analytics, but EA save checksums may still be active — test this)
