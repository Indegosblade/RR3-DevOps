# Remote Config consumers and suppression boundary

Remote Config supplies actual engine decisions. Suppressing the game-owned fetch
at `0x10082010c` cannot currently be justified as an inert SDK cleanup. A bounded
static trace identifies **32 direct calls covering 22 keys**, including frame-rate
configuration, rookie behavior and feature unlock levels. The SDK also retains
local configuration loading and a separate nominal 30-second database wait.
No suppression patch or device-performance claim is made here.

This extends [SDK lifecycle tracing](SDK_LIFECYCLE_FLOW.md) and the
[dependency audit](SDK_DEPENDENCY_AUDIT.md). All addresses are unslid ARM64 VAs
for executable UUID `06ed5b50c44c3b69a5840701b8a88451`.

```text
python scripts/trace_remote_config_consumers.py original.ipa
python scripts/trace_remote_config_consumers.py original.ipa --output new-report.json
python -m unittest discover -s tests -p test_remote_config_consumers.py -v
```

The standard-library script checks the UUID, hashes reviewed instruction windows,
verifies key literals and exact direct callers, resolves selected Objective-C
selectors/imports, and decodes the database-wait constant. The key mappings are
manually traced findings guarded against changed bytes, rather than a general
decompiler. Reports refuse existing output paths and the input IPA. There is no
extraction, executable editing, signing or device access.

The report was run successfully against both the original IPA (SHA-256
`74c8e4c208b0cbcff2d232499f80ab72685a614c1b1c60847338055143c5ff4f`)
and v1.1 production. The latter retains the previously documented package SHA-256
`d1ccf110ec538545169d93cdae8a8fd839cb9015d02c0f495570a0f1089c2148`.
This proves compatibility of these static windows with those packages, not live
configuration contents or safe gameplay under an experimental patch.

## Values reach game-owned state

```text
game fixed key -> typed C++ bridge -> fmRemoteConfig Objective-C getter
  -> FIRRemoteConfig configValueForKey: -> dispatch_sync(SDK serial queue)
    -> activeConfig[namespace][key]
    -> defaultConfig[namespace][key] if absent
    -> static empty-data value if absent
  -> int / std::string / bool -> game state, branch or feature gate
```

The C++ bridges are integer `0x1001e3f40`, string `0x1001e3fe4` and Boolean
`0x1001e4084`. Their `std::string` argument and returned string require normal
libc++ ownership/ABI behavior. The Objective-C wrappers at `0x100820128`,
`0x100820174` and `0x10082024c` convert the SDK value with `numberValue/intValue`,
`stringValue/UTF8String`, and `boolValue`. Removing Firebase initialization or
returning arbitrary pointers from these bridges is outside the researched boundary.

| Keys | Direct consumer call sites | Demonstrated immediate effect |
|---|---|---|
| `enable_mtx_tile` | `0x100079d64`, `0x10073a9f0` | Stores result in object byte `+0x50`; second consumer conditionally calls `0x100b42634` |
| `mtx_offer_tile_target_user_level` | `0x100079dbc` | Stores integer in the same object's `+0x58` |
| `ABTestId`, `CohortId` | `0x100079e04`, `0x100079e78`, `0x10007a2ac`, `0x10007a2f8`, `0x1003c6ef0`, `0x1003c6f28` | Copies/logs cohort values and passes them to a game string-combination helper |
| `enable_optimized_logic`, `enable_experimental_logic` | `0x100079fcc`, `0x10007a028` | Stores Boolean globals `0x1031d6fbc` / `0x1031d6fbd`; ultimate logic consumers not resolved |
| `ios_framerate_cap` | `0x10007a070` | Negative result becomes 30; nonnegative result, including zero, is stored at `0x1031d6fb8`; then enables frame-rate cap through app delegate/GL view |
| `override_client_unlock_levels` | `0x10007a0e0`, `0x100ab05b4` | Gates remote unlock overrides and a local-config fallback |
| `omp_unlock_level_override`, `exclusive_series_unlock_level_override`, `race_teams_unlock_level_override` | `0x10007a158`, `0x10007a1c0`, `0x10007a218` | Override branch writes integers to game-object offsets `+0x574`, `+0x57c`, `+0x570` |
| `wtt_championship_unlock_level_override` | `0x10007a278`, `0x100ab0600` | Read under override policy; helper at `0x100ab056c` returns it when enabled, otherwise reads local `SeasonsUnlockLevel` |
| `activate_rookie_crash_fix` | `0x100139d40`, `0x1003c9420` | Chooses different game call/control-flow branches; descriptive key name alone is not proof of a crash fix |
| `enable_rookie` | `0x1003c6eb0` | Under an earlier condition, stores Boolean into consumer object byte `+8` |
| `enable_dynamic_ads` | `0x1006ce574` | Stores Boolean into game object byte `+0x2f0` |
| `enable_custom_logs_for_events` | `0x100a2432c` | False exits before the longer custom-event logging path |
| `ad_feature_drive_points_cap`, `ad_feature_crew_hire_cap` | `0x100b48270`, `0x100b482dc`, `0x100b4837c`, `0x100b483ec` | Constructor logs caps; per-kind helper returns requested cap |
| `enable_ad_feature_drive_points` | `0x100b4909c` | Returns eligibility for feature kind zero |
| `ad_feature_crew_hire_min_level`, `ad_feature_crew_hire_max_level`, `enable_ad_feature_crew_hire` | `0x100b49114`, `0x100b49174`, `0x100b49228` | Stores level bounds, compares another game-provided integer against them, then reads enable flag; max `-1` bypasses upper comparison |

The large population function at `0x100079d0c` has a direct tail caller at
`0x1006cee1c` after creation of a game-owned singleton. This is an application
configuration boundary, not merely SDK diagnostic logging. These strings identify
feature intent; the table deliberately limits effects to inspected instructions.
For example, forwarding a zero frame-rate value does **not** establish an actual
zero frame rate, a hang or any measured rendering change: its final downstream
interpretation remains unresolved.

The direct-call scan does not identify a script binding to these bridges. An
additional raw-pointer search found no literal 64-bit references to their entry
addresses in readable Mach-O sections. Neither result proves scripts cannot
reach configuration through another engine helper, computed pointers, virtual
dispatch or dynamic Objective-C dispatch. This is complete coverage only of the
observed aligned direct `B`/`BL` calls to these three entry points in `__text`.

## Defaults are SDK data, not a demonstrated complete game default table

The getter's queue block reads active configuration at `0x101edadd0` and falls
back through `defaultValueForFullyQualifiedNamespace:key:` at `0x101edaeb8`.
That helper reads `defaultConfig` at `0x101edab78`. When neither contains the
key, `0x101edabe4` onward constructs a value from empty `NSData`, with source
integer 2. The conversion implementation uses UTF-8 `NSString`, its `doubleValue`
and `boolValue`: this is the static empty-string/zero/false fallback, rather than
a per-key game default. No live database was read to determine which keys
actually take this path.

The direct-selector scan finds:

| Selector | Observed direct callers |
|---|---|
| `setDefaultsFromPlistFileName:` | None |
| `setDefaults:` | Only `0x101edbf50`, inside the SDK's own plist-loading implementation |
| `activateWithCompletion:` | Only `0x101eda180`, inside SDK fetch-and-activate handling |

No direct game default-population call is established by this scan. The
game-owned `fmRemoteConfig Init` sets settings and starts fetch, with no default
dictionary installation in that method. A selector implementation existing in
the binary does not establish that the game invokes it. These are bounded
negative results: dynamic sends, alternate paths or a prior stored default set
remain possible. A local fallback such as `SeasonsUnlockLevel` is owned by the
game consumer; it is distinct from Firebase's default-config table.

## Local cache initialization still has work and a wait

`RCNConfigContent initWithDBManager:` at `0x101edd358` creates its dictionaries
and dispatch group, then calls `loadConfigFromMainTable` at `0x101edd510`.
That method enters a dispatch group and asks the DB manager to load records
for the bundle identifier at `0x101edd5a4`. DB loading runs asynchronously;
the callback at `0x101edd5ec` copies loaded data into the content object's
fetched (`+0x10`), active (`+8`) and default (`+0x18`) dictionaries and leaves
the group at `0x101edd734`.

The corresponding content getters call `checkAndWaitForInitialDatabaseLoad`
before returning their dictionary. At `0x101ede728`, a completed flag at `+0x58`
returns immediately. Otherwise the helper builds `dispatch_time(0,
30_000_000_000)` and calls `dispatch_group_wait` at `0x101ede768`. Success marks
the flag; timeout logs and returns false. The inspected dictionary getters do
not branch on that Boolean before returning their current dictionary.

This is a **nominal 30-second API deadline for local initial database loading**.
It is separate from the network fetch's 60-second timeout. Static instructions
do not measure elapsed time, prove that a database ever times out, identify the
calling UI thread, or connect this wait to the reported symptom. Suppressing
`0x10082010c` retains this database initialization and getter route.

Activation at `0x101eda3e4` checks fetched/apply metadata; the newer-config path
reads fetched configuration at `0x101eda460` and copies it into active source
zero at `0x101eda484`. The default setter separately copies into source one at
`0x101edbaf4`. Therefore active/default state ownership is in the SDK's local
content/DB machinery, not the game's log-only fetch callback.

## Result for a fetch-suppression experiment

Skipping the final game-owned fetch dispatch preserves getters and local cache
loading but removes this path's opportunity to obtain and activate fresh values.
Existing installations can retain different active/default records from a fresh
installation. Even when both launch successfully, they may make different
decisions at the demonstrated feature gates. Cached fetched-but-not-active data
also cannot be assumed equivalent to active data.

There is no justified release patch from this trace. A later separate-copy
experiment needs known cold and preexisting configuration states, recorded key
values/sources without private identifiers, and checks of frame-rate behavior,
rookie paths, unlock rules, ad-feature eligibility and ordinary offline/save
continuity. Timing/network/storage measurements must distinguish the fetch work
from retained local DB initialization. Devices were disconnected; no new UI,
race, backend, cache-content or performance result is claimed.
