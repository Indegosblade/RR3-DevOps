# Exact optional GUI asset recovery

Tracking: [optional asset coverage #15](https://github.com/Indegosblade/RR3-DevOps/issues/15). This follows the [visual inventory](VISUAL_ASSET_FINDINGS.md) and [background/resource-flow trace](BACKGROUND_RESOURCE_FLOW.md).

Three original texture-page byte sequences and their three companion iOS atlas metadata files were recovered on 28 October 2026. They came from matching-version public preservation archives linked by [Project_RR3](https://viduxsh.github.io/Project_RR3/). Texture bytes match the exact iOS filename, length and MD5; the later atlas recovery reproduces the original compressed transport hashes. This is content recovery, not a demonstrated black-background fix or a complete runtime event restoration.

## Verification rule

The source archives are Android preservation packages. Platform origin and a similar filename are not compatibility evidence by themselves. The [recovery helper](../scripts/recover_optional_assets.py) therefore:

1. Reconstructs the 909 absent high-resolution paths from the local iOS manifests and existing IPA/cache inventory.
2. Restricts this pass to the same logical `.rgb.pvr.z` path under the source archive's `com.ea.games.r3_row/files/.depot/` prefix.
3. Requires a single unambiguous iOS manifest representation, equal transport/stored lengths and a matching archive-member length.
4. Reads the complete member, checking its ZIP CRC, exact byte count and the iOS manifest MD5 before writing anything.
5. Records source URL, archive size, member, iOS manifest source SHA-256, manifest owners, MD5 and SHA-256 provenance alongside verified bytes.

The helper does not convert a codec, rename an Android atlas to an iOS atlas, edit a manifest hash, touch a working cache or accept signing/device credentials. Similar content and same-basename art are not substitutes for the hash check. Existing verified local files can be deduplicated by size/hash; unknown existing files and provenance records are never overwritten.

## Two bounded source checks

Both pinned archives were checked using the existing `BoundedRangeReader`, which requires exact HTTPS `206` ranges and enforces request/total byte limits. The full archives were not downloaded or hashed.

| Source archive | Pinned archive bytes | Exact-name/size RGB candidates | Newly verified files | Range-payload bytes read |
|---|---:|---:|---:|---:|
| [ADRENO 14.0.1](https://archive.org/download/com.ea.games.r3_row_ADRENO_14.0.1/com.ea.games.r3_row_ADRENO.zip) | 6,164,903,864 | 3 | 3 | 13,706,311 |
| [MALI 14.0.1](https://archive.org/download/com.ea.games.r3_row_MALI_14.0.1/com.ea.games.r3_row_MALI.zip) | 5,808,584,640 | 0 | 0 | 8,104,193 |
| MALI prefix-confirmation pass | 5,808,584,640 | — | 0 | 8,104,193 |
| **Combined, including mapping confirmation** | — | — | **3** | **29,914,697** |

The combined actual payload is about 28.53 MiB, below the 128 MiB task budget; each request was capped at 16 MiB. ADRENO central-directory reads used 8,403,489 bytes. Each MALI pass used only 8,104,193 directory bytes; no MALI member payload was downloaded.

The MALI zero result was checked against the real member layout: 44,750 archive entries, with 43,168 under the same `com.ea.games.r3_row/files/.depot/` prefix. Actual HD GUI members include achievements, agreement and `apple_tv/loading_tips/sprites_0.rgb.pvr.z`; that last canonical path also exists in the current iOS cache at 81,739 bytes. This is prefix/path mapping evidence, not an unperformed MALI content-hash comparison. The recovery helper now includes this mapping check in its normal metadata phase and refuses an archive with the wrong root instead of reporting a misleading zero.

The iOS manifest source archive SHA-256 is `74c8e4c208b0cbcff2d232499f80ab72685a614c1b1c60847338055143c5ff4f`.

### Recovered bytes

All three belong to `asset_list_quest_hybrid_highway_assets.txt`, below logical prefix `gui_assets/2048x1536/quests/hybrid_highway/`:

| Relative page | Bytes | Exact iOS manifest MD5 |
|---|---:|---|
| `sprites_0.rgb.pvr.z` | 88,092 | `3ad657379554a497ded6c5110c310c6d` |
| `splash/sprites_0.rgb.pvr.z` | 1,892,876 | `4b0802a6b43bbbe1c155924554069bd4` |
| `large/sprites_0.rgb.pvr.z` | 3,321,466 | `475de3b2e17cdd2d108024213e789c42` |

Total recovered stored bytes: **5,302,434**. Subsequent local wrapper/zlib/PVR-payload validation passed. Their texture dimensions are respectively 818x215, 1080x766 and 2000x1000. Image pixels were not rendered or compared on a device.

Verified bytes, per-file provenance and compact source reports remain only under ignored `investigation/recovered_assets/optional/`. No raw asset is added to Git. Recovery tooling does not relicense the game's original content.

### What was excluded

| Disposition | ADRENO paths | MALI paths |
|---|---:|---:|
| Outside this exact RGB-texture pass | 546 | 546 |
| Same logical member name absent | 358 | 361 |
| iOS transport and stored sizes differ | 2 | 2 |
| Eligible and verified | 3 | 0 |

No eligible candidate failed its hash or ZIP CRC, and no eligible candidate was deferred by the remaining budget. The exclusions are measured scope limits, not proof that all other assets are irrecoverable.

## Companion atlas recovery and the six-member HD GUI candidate

The original working inputs still lack the root, `splash/` and `large/` companion `sprites.ios.atlas` files. A follow-up [transport trace](ASSET_TRANSPORT_FLOW.md) established the actual representation: `FMASZ1` followed by a zlib stream. Reconstructing this representation with level 6 matched all 1,541 existing compressed iOS atlas members. The three recovered metadata candidates then reproduced the exact iOS transport sizes/hashes without editing their XML. This is hash-based identity proof, not filename-only renaming.

Together with the pages, the six recovered resources cover the declared high-resolution GUI subset. A [separate registered cache candidate](CACHE_REGISTRATION_FLOW.md) now contains those files and six authentic transport-MD5 receipts, plus the recovered SpeedRush video. Host inventory and receipt comparison pass. The lower-resolution catalog entries, event eligibility, other required content, layout/touch behavior and rendering are not established by this subset. Original inputs, current releases and devices remain unchanged.

A subsequent [content-hash scan of the original local archives](LOCAL_ASSET_RECOVERY.md) recovered 47 further pages from differently named source members. That produces authenticated candidates for 53 of the original 909 missing HD paths. No further compressed atlas matched locally, so receipt registration, companion metadata and complete event validation for those additional pages remain separate work. The seven-resource registered candidate above has not silently expanded to include these partial collections.

## Reproduce within a combined budget

The following pair uses hard caps summing to 128 MiB. Inventory is performed before member recovery in each run. Omitting `--recover` performs only the inventory phase.

```text
python scripts/recover_optional_assets.py --ipa original.ipa --cache Caches_ipastore.zip --archive-source adreno --max-total-mib 14 --output-directory investigation/recovered_assets/optional --report investigation/recovered_assets/optional/adreno-report.json --recover
python scripts/recover_optional_assets.py --ipa original.ipa --cache Caches_ipastore.zip --archive-source mali --max-total-mib 114 --output-directory investigation/recovered_assets/optional --report investigation/recovered_assets/optional/mali-report.json --recover
python -m unittest discover -s tests -p test_optional_recovery.py -v
```

The measured initial ADRENO run had a 128 MiB cap but consumed only 13,706,311 bytes. The subsequent MALI cap was reduced to 114 MiB, keeping its maximum permitted payload plus ADRENO's already measured usage below the combined limit. After both had completed, a separately bounded 16 MiB metadata pass confirmed the MALI root. Its cap plus the preceding actual usage also fit within the remaining combined budget. The repeat commands above reserve 14 MiB for ADRENO from the outset; the current helper records member-root evidence during its initial inventory, so a separate mapping pass is unnecessary.

CLI output/report paths must remain under the ignored recovery directory. Reports and candidate files refuse overwrite. Tests use synthetic archives to cover exact hash acceptance, wrong hash/size refusal, transport-representation separation, unsafe paths, conflicting manifests, CRC failures, local deduplication, wrong archive-root refusal and exhaustion of the remaining range budget.
