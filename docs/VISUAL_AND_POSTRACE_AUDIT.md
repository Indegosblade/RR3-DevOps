# Offline visual and post-race investigation

Initial static audit performed 28 October 2026. No device was connected and no original game/cache input was modified. Follow-up work prepared isolated experimental helpers and recovered a manifest-matching original media asset. These experiments are not enabled in the production builder or included in a new release.

## Tracking and follow-up work

- [Black backgrounds #13](https://github.com/Indegosblade/RR3-DevOps/issues/13) and [optional assets #15](https://github.com/Indegosblade/RR3-DevOps/issues/15): [full texture-stream and decoded-layout findings](VISUAL_ASSET_FINDINGS.md), the [normal background control/resource trace](BACKGROUND_RESOURCE_FLOW.md), and [six exact-match optional GUI recoveries](OPTIONAL_ASSET_RECOVERY.md). The [transport](ASSET_TRANSPORT_FLOW.md) and [receipt-registration](CACHE_REGISTRATION_FLOW.md) traces support a separate seven-resource cache candidate; runtime event behavior remains unverified.
- [Malformed event styles #17](https://github.com/Indegosblade/RR3-DevOps/issues/17): exact-resource-guarded experimental XML repair, now verified through the [original engine parser and encrypted loader](STYLE_PARSER_FLOW.md). The original skips 12 local overrides, seven differing from globals; rendered event behavior remains unverified.
- [Time Trial delays #14](https://github.com/Indegosblade/RR3-DevOps/issues/14): [tournament request/completion trace and experimental timeout plan](POSTRACE_CONTROL_FLOW.md), [ordinary routing and persistence probes](ORDINARY_POSTRACE_FLOW.md), [deferred primary career-save boundary](PRIMARY_SAVE_BOUNDARY.md), and [request delivery/ownership](REQUEST_DELIVERY_FLOW.md).
- [SDK dependencies #5](https://github.com/Indegosblade/RR3-DevOps/issues/5): [reproducible dependency audit](SDK_DEPENDENCY_AUDIT.md), [live SDK lifecycle](SDK_LIFECYCLE_FLOW.md), [actual Remote Config consumers and local DB wait](REMOTE_CONFIG_CONSUMERS.md), and [ad-state initialization and close ownership](AD_STATE_OWNERSHIP.md).
- [Missing promotional video #16](https://github.com/Indegosblade/RR3-DevOps/issues/16): [verified original-content recovery and separate cache restoration](MISSING_CONTENT_RECOVERY.md).

The [local content-hash recovery pass](LOCAL_ASSET_RECOVERY.md) recovered 47 additional texture pages under their original target paths, independently of source filenames. A [bounded companion-metadata search](COMPANION_ATLAS_RECOVERY.md) authenticated another 15 atlas targets. Together with Hybrid Highway, separate authenticated candidates cover 68 of the 909 absent HD declarations; 841 remain unresolved. Only Hybrid Highway has a complete recovered HD catalog. This does not alter the preserved-input inventory or establish complete event rendering.

The [end-to-end inline rejection probe](INLINE_REJECTION_FLOW.md) also demonstrates a conditional post-deletion ID store and a narrowly scoped fresh-ID experimental guard. It does not resolve the helper's lost early-error state, reused-request cases or real server rejection reachability.

A separate [two-phase helper candidate](HELPER_DELIVERY_REPAIR.md) preserves responses arriving during launch and defers their completion to the ordinary update. Controlled-Start tests demonstrate the state change without invoking completion during construction. Combined patch regions are reversible, but the combined candidate has not been executed through the concrete manager and complete UI body. Runtime relevance and platform execution remain open.

## Reported symptoms

- [Hefti's compatibility report](https://github.com/Indegosblade/RR3-DevOps/discussions/9#discussioncomment-18920203) describes perhaps one or two black backgrounds, without identifying the screens. [Upstream issue #2](https://github.com/hefti/RR3-offline-fix-for-iPhone-SE3/issues/2) leaves the cause unresolved.
- [Ray's original report](https://github.com/Indegosblade/RR3-DevOps/discussions/9#discussioncomment-19201223) describes slow startup and results, particularly Time Trials, persisting without connectivity. His follow-up reports a separate launch abort. Neither post identifies a black background or its asset.
- A dead-service wait, incomplete optional content and a rendering/resource-selection problem remain separate hypotheses. They need not share a fix.

## Reproducible asset checks

```text
python scripts/audit_visual_assets.py --ipa original.ipa --cache Caches_ipastore.zip --output inventory.json
python -m unittest discover -s tests -v
```

The scanner reads ZIPs without extracting or changing them. It joins bundled `res/` and cache resources into a logical inventory, excludes AppleDouble metadata, parses manifests and the base ledger, and follows available atlas pages. This is an availability inventory, not proof of the engine's runtime lookup order or selected event/family.

Input identities, rehashed during this audit:

| Input | SHA-256 |
|---|---|
| Unmodified preserved IPA | `74c8e4c208b0cbcff2d232499f80ab72685a614c1b1c60847338055143c5ff4f` |
| Existing cache ZIP | `96aeb92f1bb6c5ddee73e1a5fb2f4b33ef2e5a5e03fd86380b847cd771a7fc8e` |

| Check | Result |
|---|---:|
| Unique available logical resource paths | 41,182 |
| Parsed manifest files / unique declared paths | 1,179 / 32,763 |
| Malformed manifest records | 0 |
| Base-ledger entries / absent paths | 24,792 / 1 |
| Available atlases / image entries inspected | 3,321 / 107,082 |
| Referenced texture-page headers inspected | 6,220 |
| Missing pages referenced by available atlases | 0 |
| Invalid inspected PVR v2 headers | 0 |
| Sprite rectangles outside inspected page dimensions | 0 |
| Available malformed atlas XML files | 0 |
| Weekly Time Trial high-resolution manifest paths present | 6 / 6 |
| Quest-stage background high-resolution manifest paths present | 101 / 101 |

The only absent base-ledger resource in the unchanged source cache is `SpeedRush_TV_commercial.mp4`. Its manifest records transport/stored sizes of 6,925,760 bytes and hash `7f9560c4abf3665fd4bd62e01aa9f689`. The later recovery work found an exact match, verified a full host decode and built/read back a separate cache candidate adding only that file. See the recovery record above. [Hefti's missing-video issue](https://github.com/hefti/RR3-offline-fix-for-iPhone-SE3/issues/1) does not establish a link to the black backgrounds.

The union of all optional manifests declares **909 absent `2048x1536` GUI paths**, including **70** paths in older Time Trial competition/event groups. These are not the normal six-file weekly Time Trial group. An inventory across all historical events and device families is not a list of mandatory startup resources. An entirely absent atlas is also outside the available-atlas page check above.

Important limits:

- The page check inspects PVR headers and sprite bounds. It does not decode pixels, validate whole texture streams, execute shaders or establish that an image is visually correct.
- The game can request dynamically composed resources outside a particular manifest or choose an unexpected family. Static presence cannot prove runtime use.
- Stored file bytes must not be compared blindly with transport hashes: expanded files can legitimately differ. The audit intentionally does not rewrite or interpret those hashes as corruption checks.
- GUI layout files are encoded rather than plain XML in this package. Follow-up work decoded them with the existing resource cipher and mapped static image references; a filename alone is not proof of runtime layout-to-image binding. See the linked visual findings for the malformed style resource and remaining unresolved references.

## Post-race code located

These are unslid virtual addresses for the researched main executable UUID `06ed5b50c44c3b69a5840701b8a88451`. Class identities were resolved through retained C++ RTTI and vtables, then relevant ARM64 instructions were disassembled.

| Component | Concrete observation | Interpretation boundary |
|---|---|---|
| `LeaderboardTask` | Vtable at `0x102BAB628`; candidate setup at `0x1003D1718`; shared poll at `0x1003D1704` reads the pointed object's byte at `+0x471` | Task completion depends on another object's state; it does not establish which result or network callback changes it |
| `LocalLeaderboardTask` | Separate vtable at `0x102BAB5C0`; candidate setup at `0x1003D1420`; same poll function | A local path exists; its name alone does not prove it can replace a remote result path safely |
| `TTCPostRaceTask` | Vtable at `0x102BAE4C8`; setup at `0x1003E709C`; poll at `0x1003E7088` reads the pointed object's byte at `+0x264` | A precise wait/completion point to investigate, not proof of an infinite wait |
| `TimeTrialTournamentAggregateScreen` | Constructor `0x1003E4F5C`, vtable `0x102BAE1E0`, initializes state at `+0x264`; nearby write candidates at `0x1003E6EE0` and `0x1003E7058` | Those writes still require caller/event analysis and runtime correlation; the field may represent normal UI completion |

The initial poll-function inspection did not establish a timeout, save effect or stuck state. Follow-up tracing found a 30,000-update-tick timeout in the tournament helper. It uses the existing error callback and Continue UI; it does not directly force the task complete. A one-instruction experimental timeout plan preserves those transitions. See the post-race trace for the request producers, cleanup and emulation results. Runtime duration, relevance to the reported delay and local-save ordering remain unverified.

## Initial review of the SDK-removal issue

[Issue #5: Strip dead ad SDK frameworks from binary](https://github.com/Indegosblade/RR3-DevOps/issues/5) was open with zero comments when reviewed. Its assumptions do not justify broad deletion:

- The published v1.1 production IPA has **46 framework bundles totaling 18,453,795 uncompressed bytes / 5,742,291 compressed bytes** (about 17.60 / 5.48 MiB). Removing frameworks cannot save the issue's claimed 50+ MB in this package.
- **37** framework bundles have no `__text` code, together totaling 1,748,672 uncompressed bytes. Resources and dynamic bundle lookup can still matter; code-empty does not automatically mean removable.
- Main defines classes such as `FIRApp`, `FIRAnalytics`, `FIRRemoteConfig` and `GADMobileAds` itself. Removing their namesake framework bundles would not remove that embedded implementation or its initialization.
- Main has hard loads and undefined-symbol imports from several code-bearing SDKs. Dependencies also exist between frameworks: FBAEM is loaded by FBSDKCoreKit despite having no direct main-symbol imports.
- The production ad patches suppress selected readiness/config paths. They do not establish that all SDK initialization, timers, callbacks or networking are inactive.
- `install_name_tool -delete_rpath` removes an `LC_RPATH` search path, not an `LC_LOAD_DYLIB` requirement. [Apple's implementation distinguishes them](https://github.com/apple-oss-distributions/cctools/blob/main/misc/install_name_tool.c).

The issue has no demonstrated causal link to the reported backgrounds or Time Trial delays. After the user requested public tracking, its title/body were corrected around measured dependencies and lifecycle behavior, and the other investigations received their own open issues. No issue was closed by the static audit.

## Acceptance of a future behavioral patch

Identify the exact affected screen/transition, establish the failing resource or completion path, and make one bounded change. Before release, check that screen, result completion, a race, offline cold restart, and save/cache continuity on the relevant setup. Offline analysis can prepare that candidate; it cannot supply the missing runtime result.
