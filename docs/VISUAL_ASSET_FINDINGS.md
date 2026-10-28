# Visual resource findings and experimental XML repair

This follows [black-background issue #13](https://github.com/Indegosblade/RR3-DevOps/issues/13) and [optional asset coverage issue #15](https://github.com/Indegosblade/RR3-DevOps/issues/15). The audit was run offline against the preserved inputs on 28 October 2026. No device connection, installation, cache mutation or release was performed.

## Complete available GUI texture streams

The [asset auditor](../scripts/audit_visual_assets.py) now offers bounded full GUI-stream checks:

```text
python scripts/audit_visual_assets.py --ipa original.ipa --cache Caches_ipastore.zip --verify-gui-streams --map-layouts --output audit.json
```

`--verify-gui-streams` reads each referenced available GUI texture member to completion, validating its ZIP CRC. It then checks the game's four-byte expanded-size prefix, complete zlib stream and PVR v2 texture-data extent. The default stored/expanded limit is 64 MiB per texture; exceeded limits are reported as skipped, not silently treated as successful checks. A complete zlib stream's trailing bytes are reported separately rather than assumed corrupt. Pixel decoding and rendered appearance remain outside this check.

Results on the same input hashes documented in [the initial audit](VISUAL_AND_POSTRACE_AUDIT.md):

| Check | Result |
|---|---:|
| Complete GUI texture streams verified | 3,605 |
| Stored bytes checked | 1,899,574,105 |
| Expanded bytes checked | 7,193,398,006 |
| Invalid streams / ZIP CRCs / PVR payload lengths | 0 |
| Skipped streams / trailing zlib bytes | 0 / 0 |

This reduces the likelihood of simple stored-texture corruption among the available referenced GUI pages. It does not establish that every requested optional atlas exists, the engine selects the intended family, or shaders and image contents render correctly.

## GUI layouts are decodable with existing tooling

The existing `build_4k_v3.eds_crypt()` transform also decodes the encrypted `.gui` resources. Some resources concatenate a layout document and separate animation documents. The auditor removes XML declarations and wraps those fragments **in memory for analysis**; treating every file as one standalone XML document would falsely reject valid multi-document resources.

After normalizing image-reference backslashes and excluding nodes explicitly marked `editor_only_image=true`:

| Check | Result |
|---|---:|
| Layout files parsed | 2,382 of 2,383 |
| Layout/animation documents parsed | 2,546 |
| Unique static image references | 1,800 |
| Image references with an available high-resolution atlas sprite | 1,142 |
| Unresolved static image references | 658 |
| Unresolved references sharing a path prefix with an absent declared HD atlas | 351, used by 371 layouts |

The last association is a **candidate mapping by collection prefix**, not proof of the contents of an absent atlas. Static references also include historical events and prototype screens. Runtime image replacement, current event eligibility and resource lookup rules are not established by an XML attribute alone. Do not turn the 658 count into a count of broken visible screens.

Useful screen-level candidates include:

| Layout | Static image | Absent atlas group |
|---|---|---|
| `Eagle_LoadingScreen_PostRace.gui` and Eagle intro/outro layouts | `quests/eagle/main_menu_splash/eagle_full_bg.png` | `asset_list_quest_eagle_assets.txt` |
| `EventMapScreen_TimeTrialTournament_lmp1.gui` and Le Mans POV layouts | `quests/lemans_pov/lemans_welcome_bg.png` | No matching absent declaration was established by the collection-prefix check |
| `limited_time_series/formulae_tt/ltd_timed_series_card_background.gui` | `ltd_timed_series/formulae_tt/formulae_tt_bg.png` | `asset_list_lts_formulae_tt_assets.txt` |

These are reproduction targets for future screen-specific checks, not confirmed descriptions of Hefti's accepted black backgrounds.

### Normal post-race and SpeedRush backgrounds

`PostRaceBackground.gui` references `rewards/post_race_sky_burn.png`, available in all three GUI families. Its blend mode is `Translucent Color Multiply`. Changing that mode without a rendering trace would alter presentation rather than establish a missing-resource fix.

The SpeedRush loading/post-race layouts use `quests/speedrush/loading/load_screen_speedrush.png`, which is available in the high-resolution family. No decoded GUI file contains a literal `.mp4` filename or `SpeedRush_TV_commercial.mp4`. `IntroScreen_ItemVideo.gui` has generic `BTN_WATCH_YES`, `BTN_WATCH_NO` and `BTN_CONTINUE` controls; it does not identify the playback target. The missing movie's consuming runtime code still needs tracing in [issue #16](https://github.com/Indegosblade/RR3-DevOps/issues/16).

## One real XML syntax defect

Tracked separately in [experimental style-repair issue #17](https://github.com/Indegosblade/RR3-DevOps/issues/17); runtime acceptance remains pending.

The remaining parse failure is:

```text
res/gui/processed/limited_time_series/gameonix_2020_mazda_mx5/LocalStyles.gui
```

After decryption, its final `Colour` element is missing `/>` before the closing `Colours` element. An exact two-byte insertion repairs strict XML syntax while retaining the same color values.

| Resource | SHA-256 | Size |
|---|---|---:|
| Original encrypted resource | `3af680491c7073f47271a4ed2efe1d23117d7b67bf2e4b205322cde4537c549a` | 1,073 bytes |
| Experimental repaired resource | `cd69b876f3d5e353426486913b367a02a79264e8a1793a99bf5912be6f5f94e4` | 1,075 bytes |

The actual preserved resource was passed through the guarded repair and decrypted again; strict XML parsing succeeded. Both published v1.1 IPA variants contain this same guarded resource and produce the same repaired hash. This is a demonstrated **syntax repair**, not a demonstrated black-background or gameplay fix. Whether the engine tolerates the original syntax, loads this historical event's style file, or presents a visible defect is unknown.

The initial comparison found the same final `lts_popup_backing_color` value in GlobalStyles, but that was insufficient to infer whole-file neutrality. A subsequent [original-engine parser/loader probe](STYLE_PARSER_FLOW.md) proved that the original file is rejected and all 12 local color overrides are skipped; seven differ from GlobalStyles. The repaired file is accepted and reaches style ingestion. Rendered event behavior and a connection to the reported black backgrounds remain unverified.

### Isolated experimental candidate

The [standalone repair helper](../scripts/repair_gui_layout.py) is excluded from the default production builder:

```text
python scripts/repair_gui_layout.py --experimental v1.1.ipa visual-candidate.ipa
```

The helper requires the exact original resource SHA-256, refuses changed/already-repaired input and existing/same-as-input output, preserves ZIP entry metadata and changes only this encrypted resource. It does not patch executable code or accept signing credentials. **The new IPA's resource seal is stale and it must be re-signed before installation.** Use a current v1.1 input to retain its existing startup fixes; this helper does not add them to older inputs.

Synthetic archive tests cover the resource change and metadata preservation; real-resource checks prove the source hash, two-byte insertion and XML/encryption round trip. Devices are needed to establish any visible effect before promotion.

The actual experimental CLI was also run against the published v1.1 Production Quality IPA. Readback confirmed the same entry list, preserved ZIP entry metadata, exactly one changed resource, an unchanged main executable and valid repaired XML. The large generated test IPA was removed after validation; a compact local result record was retained. It was not signed, installed, uploaded or treated as a release.
