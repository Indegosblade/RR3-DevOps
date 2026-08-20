# Production Binary Patch Specification

This is the authoritative reference for `build_4k_v3.py`, the RR3 DevOps production builder. It targets the researched final iOS binary only.

## Scope

The script applies **13** binary operations: seven Objective-C stub replacements and six endpoint rewrites. It also encrypts and injects the custom EDS profile. It deliberately excludes debug-gate activation, BuildType changes, and conditional-branch changes.

The production builder accepts re-signed or repackaged copies of the researched final build, but refuses a different executable before it writes. It verifies the final build's Mach-O UUID, checks that every offset is in range, and compares the original bytes at all 13 locations. It does not use an IPA-wide hash or bundle identifier, because those can change during normal re-signing and packaging.

## Stub replacements

Each researched Objective-C trampoline is replaced with an ARM64 return sequence. `NO` and numeric returns use `mov w0, #imm; ret`; review suppression explicitly returns `nil` using `mov x0, #0; ret`.

| Offset | Change | Purpose |
|---|---|---|
| `0x022CB460` | `isAdReady → NO` | Suppress ready-ad presentation |
| `0x022D0120` | `isRewardedVideoReady → NO` | Suppress rewarded-ad availability |
| `0x022CE4A0` | `isInterstitialReady → NO` | Suppress interstitial-ad availability |
| `0x022812E0` | `adMobEnabled → NO` | Disable this ad-config path |
| `0x02292440` | `checksumEnabled → NO` | Disable the researched checksum path |
| `0x022F6560` | `requestReview → nil` | Suppress the review request |
| `0x022DACE0` | `maxFPS → 120` | Raise the frame-rate cap |

## Endpoint rewrites

Known retired endpoints are replaced with `http://127.0.0.1/`, padded to the original string length. This preserves a fast connection-failure path. Replacing a URL with an empty value entered an earlier invalid-request path during testing.

| Offset | Original host/path |
|---|---|
| `0x026F5B86` | `director-int.sn.eamobile.com` |
| `0x026F5BAB` | `director-stage.sn.eamobile.com` |
| `0x026F5BD2` | `syn-dir.sn.eamobile.com` |
| `0x026CB1A2` | `prod.geo.gluops.com/geoservice/v2/publishdetailed` |
| `0x026E787D` | `prod-rest.ccs.gluops.com/api/v1/putData` |
| `0x02743860` | `firemonkeys.com.au/news/embednews/index.php?nGameId=` |

This identifies the known rewrites; it does not claim that no other network attempt can occur in every runtime condition.

## Non-production experiments

`scripts/build_debug_v1.py` is retained for technical reference. It contains activation experiments that are excluded from the production builder and will only run when explicitly invoked as `python scripts/build_debug_v1.py --experimental <original.ipa> <output.ipa>`. Before any experimental changes, it reuses the production builder's final-executable UUID and expected-byte validation:

- forcing `isDebugModeEnabled`, `isInternalTestMode`, or `isAppDebuggable`;
- changing `BuildType` to `PRIVATE`; and
- NOPing conditional debug gates.

These changes can activate dormant or shared SDK paths and were associated with instability in the technical record. They are not a release recipe.

## IPA preservation method

`build_4k_v3.py` copies the source IPA zip-to-zip and preserves its `ZipInfo` entries while replacing only researched executable bytes and EDS entries. Extracting and rezipping the app was avoided because directory-entry changes can break iOS framework loading.

## Related references

- [EDS format and quality profile](EDS_FORMAT.md)
- [Technical report](TECHNICAL_REPORT.md)
