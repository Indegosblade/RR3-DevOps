# Real Racing 3 — Dev Build Guide

**File:** `C:\Users\Kevin\Downloads\rr3_dev.ipa` (1.34 GB)
**Date:** 2026-07-31
**Target:** iPhone 17 Pro (stock, Sideloadly)

## Quick Start

1. Open Sideloadly, drag `rr3_dev.ipa`, sideload to 17 Pro
2. Re-import your 5.1GB cache into the app's Documents folder
3. Launch — cheat menu should appear on main menu
4. Tap "Character|Unlock + Own Everything" to unlock all careers

## What's Patched (19 binary patches + config mods)

### Debug Mode (5 ObjC stubs → return YES)
| Selector | Stub Offset | Callers | Effect |
|----------|-------------|---------|--------|
| `isDebugModeEnabled` | 0x022CCAA0 | 14 | Main gate — enables debug UI blocks |
| `debugMode` | 0x0229E380 | 13 | Race/gameplay debug features |
| `isInternalTestMode` | 0x022CE3E0 | 5 | Internal test features |
| `isAppDebuggable` | 0x022CB9C0 | 2 | App-level debug flag |
| `isDebug` | 0x022CCA80 | 1 | Debug property |

### Kill Ads (4 stubs → return NO)
| Selector | Stub Offset | Effect |
|----------|-------------|--------|
| `isAdReady` | 0x022CB460 | No ads ever "ready" |
| `isRewardedVideoReady` | 0x022D0120 | No rewarded video ads |
| `isInterstitialReady` | 0x022CE4A0 | No interstitial ads |
| `adMobEnabled` | 0x022812E0 | AdMob disabled entirely |

### Anti-Tamper
| Patch | Offset | Effect |
|-------|--------|--------|
| `checksumEnabled` stub | 0x02292440 | Returns NO — disables save checksum validation |

### Popups & Tracking (3 stubs)
| Selector | Stub Offset | Return | Effect |
|----------|-------------|--------|--------|
| `gdprApplies` | 0x022AE380 | NO | Skip GDPR consent popup |
| `trackingAuthorizationStatus` | 0x023350A0 | 3 (authorized) | Skip ATT tracking popup |
| `requestReview` | 0x022F6560 | ret | Kill "rate this app" popup |

### Other Binary Patches
| Patch | Offset | Effect |
|-------|--------|--------|
| BuildType string | 0x024F6480 | `PUBLIC` → `PRIVATE` |
| debugMode CBZ | 0x01267420 | NOP (removed conditional skip) |
| `maxFPS` stub | 0x022DACE0 | Returns 60 (was dynamic) |
| 6 dead server URLs | various | First byte nulled — instant fail instead of 30s timeout |

Dead servers nulled:
- `director-int.sn.eamobile.com` / `director-stage.sn.eamobile.com`
- `syn-dir.sn.eamobile.com`
- `prod.geo.gluops.com` / `prod-rest.ccs.gluops.com`
- `firemonkeys.com.au/news/embednews`

### Config Changes
- 4x Glu SDK Prod configs replaced with Debug configs (ads/analytics/services all in QA mode)
- NimbleEnvironment: `Development` + `IsDevelopmentBuild=true` + `debugMode=true`
- NimbleLog level: `debug`
- Settings.bundle: Debug Mode / IsDevelopmentBuild / isInternalTestMode toggles
- UIFileSharingEnabled: YES (access save files via Files app)
- GCSupportedGameControllers: added DirectionalGamepad (Kishi V3 Pro dpad support)
- NSAllowsArbitraryLoads: YES (clean network policy)
- UIApplicationSupportsIdleTimerDisabling: YES (no screen dim during races)

## QOL Summary

| Improvement | How |
|-------------|-----|
| **No ads** | 4 ad stubs return NO, AdMob disabled, debug configs |
| **Faster startup** | 6 dead EA server URLs nulled (no 30s timeout) |
| **No popups** | GDPR, ATT tracking, and "rate this app" all killed |
| **60fps** | maxFPS stub hardcoded to 60 |
| **No screen dim** | Idle timer disabling enabled in Info.plist |
| **Controller ready** | ExtendedGamepad + DirectionalGamepad profiles |
| **Save file access** | UIFileSharingEnabled=YES, checksums disabled |
| **Debug logging** | NimbleLog=debug for troubleshooting |

## Sideloading Over Existing Install

**Yes, you can sideload directly over your current install.** Sideloadly preserves the Documents folder (save files + 5.1GB cache) when the bundle ID matches. Bundle ID: `com.ea.realracing3.inc` (unchanged).

1. Connect 17 Pro
2. Sideloadly > drag `rr3_dev.ipa`
3. Sign and install (same Apple ID you used before)
4. Launch — your save + cache will be intact

## Razer Kishi V3 Pro Controller

The game natively supports GCController (ExtendedGamepad profile). The Kishi V3 Pro connects via USB-C passthrough and registers as ExtendedGamepad automatically.

**Controls mapping:**
- Left stick / dpad: steering
- R2 (right trigger): accelerate (analog — pressure-sensitive)
- L2 (left trigger): brake (analog)
- A button: various UI confirm
- B button: nitro / boost

**Analog triggers:** The game has `TWEAKABLE_INPUT_ENABLE_ANALOG_ACCELERATION` and `TWEAKABLE_INPUT_ENABLE_ANALOG_BRAKING`. With debug mode enabled, access these via the in-race ImGui menu (ToggleImGuiToolsMenu > ShowDebugTweakables). Enable both for pressure-sensitive gas/brake on the Kishi triggers.

**Steering sensitivity:** Adjustable via `TWEAKABLE_CAR_STEERING_SENSITIVITY` and the JOYSTICK_WHEEL_STEERING_* tweakables in the debug menu.

**Force feedback tweakables (44 total):** The CLUBSPORT_* tweakables control force feedback — originally for racing wheels but may provide haptic feedback through the Kishi's motors. Worth experimenting with in the tweakables menu.

**Config files:** `joystick_config.txt` is loaded at runtime from Documents if present. The game prints "Successfully loaded joystick settings file: %s" on success. You can create custom configs after seeing what the default looks like in debug logs.

## Cheat Menu (MainMenuCheatScreen)

The cheat screen is created unconditionally — no gate on the constructor. The `isDebugModeEnabled` gate (14 callers) controls whether the cheat entries are built into the UI. Our patch forces all 14 code blocks to execute.

### Career Unlocks
- **"Character|Unlock + Own Everything"** — one tap
- **"Character|Unlock Everything"** — alternative
- **"Character|Unlock Next Series"** — step-by-step
- **"Character|Unlock All Tracks"**
- **"Customisation|Unlock All"**
- Confirmation: *"Do you REALLY want to Unlock and Own Everything?"*

### Currency
- `SetupCurrencyCheats` — 10 lambda functions for R$, Gold, M$

### Categories (29+)
SetupCheats, SetupCurrencyCheats, SetupStoreCheats, SetupChampionshipCheats, SetupSeriesEventCheats, SetupAiCheats, SetupTutorialCheats, SetupMetagameCheats, SetupOmpCheats, SetupLTSCheats, SetupSaleCheats, SetupBalancePassCheats, SetupDailyRewardCheats, SetupCloudcellCheats, SetupCheatCallbacks, LoadRestoreSaveScreen, ReloadMenu, EnterDeepLink, ToggleSeriesLockState, FirebaseRemoteConfigShowInfo, GluRevSDKShowInfo, OnLiveryApprove, OnLiveryBan

### Other Cheat Buttons
- **"Toggle VIP"** — VIP status
- **"Toggle Mtx Purchase Made"** — simulates microtransaction
- **"OwnAllCars"** — unlock every car
- **"Daily Gold Reward (Cheat)"**
- **"HiddenValue|Test Hack"** — modify hidden game values
- **"Debug Race Selector"** — pick any race

## In-Race Debug

| Command | Effect |
|---------|--------|
| FinishRace | Instantly finish |
| TeleportPlayer | Teleport your car |
| PhysicsExplode | Blow up physics |
| AI_CONTROL_PLAYER_CAR | Let AI drive |
| ToggleFreeCamera | Free-roam camera |
| ToggleImGuiToolsMenu | ImGui debug overlay |
| ShowDebugTweakables | 895 tweakable variables |
| ToggleDebugWindow | Debug info window |
| Toggle3DRender | Disable 3D rendering |
| ToggleTVCamera | TV broadcast camera |

## Fun Tweakables (895 total)

| Tweakable | Effect |
|-----------|--------|
| AI_PLAYER_AI_SKILL_LEVEL | Control AI difficulty |
| AI_SLOW_DOWN | Slow down AI |
| CAR_MAX_SPEED | Override max speed |
| DAMAGE_PLAYER_ENABLED | Toggle damage |
| IS_RAINING | Toggle rain |
| SHOW_FPS | FPS counter |
| PHOTO_MODE_ENABLED | Photo mode |
| MENU_SCENE_FREE_ORBIT | Free orbit menus |

## Deep Links

Open in Safari:
- `rr3://RaceTeamsAdmin` — admin panel
- `rr3://RaceTeams` — race teams
- `rr3://STREAM/STREAM_ID` — jump to career stream

## Dev Screens

- `DebugRaceSelectScreen` — direct race picker
- `DebugInfoScreen` — system/build info
- `CarDebugViewer` — inspect car models
- `PhotoModeScreen` — photo mode

## If Cheat Menu Doesn't Appear

1. Check Settings > RealRacing3 > verify debug toggles are ON
2. Try deep links from Safari (`rr3://RaceTeamsAdmin`)
3. The gate fork confirmed the screen is created unconditionally — if stubs work, it works
4. Backup: save file editing with checksums disabled (profile.dat in Documents)
