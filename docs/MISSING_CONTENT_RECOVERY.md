# Missing-content recovery

Tracking: [optional-event inventory #15](https://github.com/Indegosblade/RR3-DevOps/issues/15) and [SpeedRush video #16](https://github.com/Indegosblade/RR3-DevOps/issues/16).

## Original SpeedRush video

The base ledger and `asset_list_quest_speedrush_assets.txt` refer to:

```text
/SpeedRush_TV_commercial.mp4 7f9560c4abf3665fd4bd62e01aa9f689 6925760 6925760
```

The filename, 6,925,760-byte size and recorded MD5 are lookup/verification references. They do not establish that an arbitrary video with a similar title is the original asset. No recovered candidate is included in this work.

### Search results, 28 October 2026

- Filename and video-extension searches across the local workspace found no candidate.
- The original preserved IPA, historical production IPA and supplied cache ZIP contain no `.mp4`, `.mov` or `.m4v` file outside AppleDouble metadata.
- Exact filename/hash web and GitHub searches returned no candidate.
- The executable contains the asset path fragments `/gameasset/direct/realracing3/`, `/rr3/live/` and host `firemonkeys.akamaized.net`. A filename-form candidate returned HTTP 403.
- Three further bounded HEAD requests using the manifest-group/hash form returned HTTP 403, 403 and 503 respectively. These were candidate paths, not verified historical download URLs:

```text
https://firemonkeys.akamaized.net/gameasset/direct/realracing3/asset_list_quest_speedrush_assets/7f9560c4abf3665fd4bd62e01aa9f689.bin
https://firemonkeys.akamaized.net/rr3/live/asset_list_quest_speedrush_assets/7f9560c4abf3665fd4bd62e01aa9f689.bin
https://cdn.adc.eamobile.com/gameasset/direct/realracing3/asset_list_quest_speedrush_assets/7f9560c4abf3665fd4bd62e01aa9f689.bin
```

No content was recovered. These responses do not prove that every original copy is gone, that those paths are correct, or that a transient endpoint will remain unavailable. No access controls were bypassed.

### Verification when a candidate becomes available

1. Record the original source, package/cache version and filename. Keep the candidate separate from the working cache.
2. Check its byte count and MD5 against the manifest in the expected representation. This entry records equal transport/stored sizes; still establish whether a recovered object is the video or a container/wrapper.
3. Inspect the media container and codec without substituting a re-encoded copy for an exact original match.
4. Identify the consuming screen/event and test its behavior in a separate candidate before release.

Do not remove the manifest entry or overwrite its hash to make a resource count appear complete. A substitute video needs separate provenance and explicit labeling.

## Limits and next source

The available reports do not link the missing video to the accepted black backgrounds. The next recovery source is a matching historical package/cache or a documented original download, not a code change that fabricates missing content. The software investigations in #13 and #14 can advance independently.
