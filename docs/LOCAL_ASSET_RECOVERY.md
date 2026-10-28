# Exact local content recovery

The original IPA/cache contain **47 additional exact original HD GUI texture
pages under different logical paths**. The content-hash search recovered their
23,073,486 stored bytes into ignored research storage on 28 October 2026. All 47
are `.ptc.pvr.z` pages already present in the original cache, predominantly below
flashback event paths. The source path supplies provenance; the original target
manifest's exact length and MD5 establish identity.

This is additional to the six authenticated Hybrid Highway resources described
in [optional recovery](OPTIONAL_ASSET_RECOVERY.md). Original source inventory
still lacks 909 declared HD paths. Separately stored candidates now cover
**53 / 909**, leaving **856** without authenticated candidates. The helper does
not change that original-source inventory, build a cache, add receipts, install
anything or demonstrate runtime rendering.

## Identity and representation

[The local helper](../scripts/recover_local_assets.py) indexes resource member
sizes from the original IPA's `Payload/RealRacing3.app/res/` and the original
cache's `Caches/`. It excludes AppleDouble metadata, research/report paths,
runtime/private subdirectories, duplicate source names, unsafe paths and oversized members. It searches by size
and content, independently of the source basename or event name.

```text
missing target manifest -> exact transport length/MD5 + stored length
                                      |
original local resource -> ZIP CRC -> candidate stored bytes
                                      |
                   equal lengths: hash bytes directly
                   compressed atlas: FMASZ1 + zlib.compress(bytes, 6)
                                      |
                     exact target transport size and MD5?
                                      |
                    write unchanged stored bytes + provenance
```

The atlas representation follows the independently validated
[transport trace](ASSET_TRANSPORT_FLOW.md). No XML serialization, platform
conversion, pixel resizing, filename-only substitution or manifest-hash edits
are performed. Seven missing non-atlas targets have unequal transport/stored
sizes and remain excluded because this helper does not reconstruct their
transport representation. No compressed atlas candidate matched in this scan.

For example, the cached
`quests/flashback_first_flight/large/sprites_0.ptc.pvr.z` bytes exactly match the
original manifest for
`quests/first_flight/large/sprites_0.ptc.pvr.z`. Both paths are relative to
`gui_assets/2048x1536/`. Similar art or a shared basename would be insufficient;
the hash and length equality are the acceptance evidence.

## Measured bounded pass

| Measurement | Result |
|---|---:|
| Original missing HD target paths | 909 |
| Targets within supported representations | 902 |
| Previously recovered candidates independently authenticated | 6 |
| Size-indexed source members read | 2,277 |
| Source members without an exact target match | 2,230 |
| New exact target matches / files written | 47 / 47 |
| New stored asset bytes | 23,073,486 |
| Distinct original target manifest owners | 24 |
| Manifest bytes read | 3,930,859 |
| Total payload bytes read, including manifests and local deduplication | 34,877,920 |
| Hard total payload cap | 4,294,967,296 |
| Hard per-member expanded/compressed size cap | 16,777,216 |
| Deferred member reads / rejected writes | 0 / 0 |

The helper charges each complete source member's expanded size before reading
it. Failed CRC reads retain their reservation; deferred reads are recorded.
ZIP directory/header I/O is outside this payload measurement. Original archive
files are opened read-only. The scan did not hash either complete archive;
provenance identifies each archive's local path/size, source ZIP member/CRC,
authoritative manifest member SHA-256, and exact stored/transport digests.

All new files and individual provenance sidecars remain below
`investigation/recovered_assets/local/`. The compact evidence report is
`original-local-content-report.json` in that directory. Independent readback
verified all 47 output lengths, MD5s, SHA-256s and sidecars. Unknown existing
payload/provenance files and existing reports are never replaced. An authentic
existing payload can be deduplicated by its exact target representation without
rewriting its provenance. Asset/provenance write or close failure removes only
files exclusively created by that write attempt, preserving occupied unknown
files.

A second full run authenticated all 53 known candidate files, scanned another
2,227 size-relevant members for unresolved targets and found no additional
matches. It wrote zero assets, rejected/deferred zero operations and retained
856 unresolved paths. Its report is `original-local-rerun-report.json`;
34,536,213 payload bytes were read, including local authentication. The two
passes consumed 69,414,133 payload bytes in total.

```text
python scripts/recover_local_assets.py --ipa 959112d6ace07153840144be3201b00f39ec0e91.ipa --cache Caches_ipastore.zip --output-directory investigation/recovered_assets/local --report investigation/recovered_assets/local/original-local-content-report.json --recover
python -m unittest discover -s tests -p test_local_asset_recovery.py -v
```

Omitting `--recover` performs the same bounded content validation without asset
writes. Choose a fresh report filename on a rerun. The CLI also authenticates
earlier Hybrid Highway files under the optional-recovery directory, preserving
the distinction between original inputs and recovered outputs.

Sixteen synthetic tests cover exact bytes under a different name, same-basename
wrong-hash refusal, atlas transport/stored separation, unsupported transports,
CRC failure, payload budget deferral, unknown payload/sidecar refusal,
deduplication without inventory changes, metadata/report exclusions, duplicate
manifest refusal, inventory-only behavior and transactional write-failure
cleanup without deleting an unknown sidecar. No original game assets are
embedded in tests or tracked source.

Physical content remains separate from the global receipt map and runtime
platform filter described in [cache registration](CACHE_REGISTRATION_FLOW.md).
These 47 authenticated candidates do not establish receipt completeness,
companion-atlas availability, event eligibility or a visible layout. Those are
separate validation boundaries.

Follow-up [companion recovery](COMPANION_ATLAS_RECOVERY.md) authenticated 15
atlas targets for these pages from matching-version preservation metadata.
That raises the separate recovered HD candidate inventory to 68 of 909 paths;
the local-only rerun figures above remain its original measured result.
