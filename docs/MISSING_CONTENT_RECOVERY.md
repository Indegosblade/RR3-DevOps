# Missing-content recovery

Tracking: [optional-event inventory #15](https://github.com/Indegosblade/RR3-DevOps/issues/15) and [SpeedRush video #16](https://github.com/Indegosblade/RR3-DevOps/issues/16).

## Original SpeedRush video recovered

The base ledger and `asset_list_quest_speedrush_assets.txt` refer to:

```text
/SpeedRush_TV_commercial.mp4 7f9560c4abf3665fd4bd62e01aa9f689 6925760 6925760
```

The original video has now been recovered from a matching 14.0.1 Android preservation archive. Its byte count and MD5 exactly match this iOS manifest entry. The recovered file's SHA-256 is `68047ad8e7fa50601aec1787117699d71b85e9673f03060a043c827a70c5a4da`. Raw media remains outside Git; no substitute or re-encoded video was used.

### Verified source and recovery

[Project_RR3's preservation page](https://viduxsh.github.io/Project_RR3/) links the public [14.0.1 Adreno archive](https://archive.org/details/com.ea.games.r3_row_ADRENO_14.0.1). Its ZIP contains:

```text
com.ea.games.r3_row/files/.depot/SpeedRush_TV_commercial.mp4
```

The [recovery tool](../scripts/recover_speedrush_video.py) reads bounded HTTPS ranges rather than downloading the entire 6,164,903,864-byte ZIP. The actual recovery read 15,205,629 bytes over seven requests, including the ZIP directory and selected member. It checks exact Content-Range responses, transfer budgets, member size, ZIP CRC and the manifest MD5 before creating an output file. It refuses existing output files.

The matching content hash establishes byte identity with the resource expected by the iOS manifest, despite the source archive being an Android preservation set. A full host decode with PyAV also succeeded: the MP4 is 25.566667 seconds, with 1280x720 H.264 Baseline video and 48 kHz stereo AAC-LC audio. All 767 video frames and 1,199 audio frames decoded without an error. This does not establish playback on a particular iOS setup or a relationship to black backgrounds.

### Separate cache candidate

The [cache-restoration tool](../scripts/restore_speedrush_cache.py) requires the known original cache SHA-256 and verified movie bytes. It copies the original ZIP and appends only `Caches/SpeedRush_TV_commercial.mp4`. Existing compressed member data, entry offsets, sizes, CRCs, timestamps and permissions are retained; archive directory/ZIP64 encoding can be regenerated. No manifest or ledger entry is edited, because the existing ledger already names this resource.

```text
python -c "from pathlib import Path; Path('investigation/recovered_assets').mkdir(parents=True, exist_ok=True)"
python scripts/recover_speedrush_video.py investigation/recovered_assets/SpeedRush_TV_commercial.mp4
python scripts/restore_speedrush_cache.py Caches_ipastore.zip investigation/recovered_assets/SpeedRush_TV_commercial.mp4 investigation/recovered_assets/Caches_recovered.candidate.zip
```

A full local candidate build retained all **59,926** original archive entries and added one verified movie. Readback verified the new member and the retained entry metadata. The resulting archive was 5,525,649,097 bytes, SHA-256 `85998d670b041a00c311149dbcd149616e2603a2b474b3683a58033ebaaae597`. This identifies that local build, not a newly published release; ZIP/compression tool versions may change a rebuild's archive hash.

The multi-gigabyte candidate was deleted after verification. Only the small recovered movie and compact provenance remain under ignored local research storage. The original cache, release assets and device installations were not changed. Import/playback and the consuming event still need verification before release.

A later [combined registered candidate](CACHE_REGISTRATION_FLOW.md) also adds six independently verified Hybrid Highway GUI files and their missing authentic receipts. The movie itself already has a valid receipt in the original ledger. These two writer modes are intentionally distinct: movie-only restoration can append a file without changing the ledger; optional content requires both payload and catalog-completion evidence.

### Static consuming-event association

The movie filename occurs once in the decrypted `res/data/jobs.bin.nct`, at decoded offset `0x34A7F3`, preceded by its 27-byte string length. The encrypted table's SHA-256 is `2c0e5403d0be4a3baa3b89585ff43ea2a034b0e6d9cbb2bb8735f46034a5fc84`.

The same local configuration span contains `Speedrush`, `Career`, `speedrush`, `SpeedrushQuestLandingPage.xml`, `LoadingScreen_Speedrush.xml`, `SpeedrushQuestIntro.xml` and `SpeedrushOfferPopup.xml`. This associates the file with the Speedrush career configuration rather than a generic post-race background. The table can be inspected with the existing `eds_crypt()` transform, as with the GUI layouts.

This is a static association from serialized strings and their positions, not a fully reconstructed table schema or a runtime playback trace. The current event eligibility, job selection, watch/skip behavior and playback return transition still need checking.

### Earlier negative searches, retained for provenance

- Filename and video-extension searches across the original local workspace found no candidate.
- The original preserved IPA, historical production IPA and supplied cache ZIP contain no `.mp4`, `.mov` or `.m4v` file outside AppleDouble metadata.
- Exact filename/hash web and GitHub searches returned no candidate.
- The executable contains the asset path fragments `/gameasset/direct/realracing3/`, `/rr3/live/` and host `firemonkeys.akamaized.net`. A filename-form candidate returned HTTP 403.
- Three further bounded HEAD requests using the manifest-group/hash form returned HTTP 403, 403 and 503 respectively. These were candidate paths, not verified historical download URLs:

```text
https://firemonkeys.akamaized.net/gameasset/direct/realracing3/asset_list_quest_speedrush_assets/7f9560c4abf3665fd4bd62e01aa9f689.bin
https://firemonkeys.akamaized.net/rr3/live/asset_list_quest_speedrush_assets/7f9560c4abf3665fd4bd62e01aa9f689.bin
https://cdn.adc.eamobile.com/gameasset/direct/realracing3/asset_list_quest_speedrush_assets/7f9560c4abf3665fd4bd62e01aa9f689.bin
```

Those searches did not recover content; the later matching preservation archive did. These responses do not prove that every original copy is gone, that those paths are correct, or that a transient endpoint will remain unavailable. No access controls were bypassed.

### Remaining verification

1. Preserve the recorded archive source, package/cache version, filename and verified hashes.
2. Retain the host media/container/decode result; do not substitute a re-encoded copy for the exact original match.
3. Identify the consuming screen/event and test import/playback on the relevant platform in a separate candidate before release.

Do not remove the manifest entry or overwrite its hash to make a resource count appear complete. A substitute video needs separate provenance and explicit labeling.

## Limits

The available reports do not link the missing video to the accepted black backgrounds. Exact original-content recovery is now complete, while event association and device playback remain open. The software investigations in #13 and #14 can advance independently.
