# Production Binary Patch Specification

This is the authoritative reference for `build_4k_v3.py`, the RR3 DevOps production builder. It targets the researched final iOS binary only.

## Scope

The default build applies **18** binary operations: seven Objective-C stub replacements, six endpoint rewrites, and five URL-literal length corrections. It also encrypts and injects the custom EDS profile. It excludes debug-gate activation and BuildType changes. The explicit `--se-compat` variant adds two guarded GUI-filter operations for **20** total; those are described below.

The production builder accepts re-signed or repackaged copies of the researched final build, but refuses a different executable before it writes. It verifies the final build's Mach-O UUID, checks that every offset is in range, and compares the original bytes at all 18 locations. It does not use an IPA-wide hash or bundle identifier, because those can change during normal re-signing and packaging.

The legacy **v1.0-4k IPA predates the five length corrections**. Both v1.1 IPA variants include them. The v1.0 checksums remain intact for historical verification.

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

## Foundation URL-literal lengths

Five rewritten endpoints are backed by constant `NSString`/CFString records. Their explicit 64-bit character counts must also become **17**, the length of `http://127.0.0.1/`. Updating only the text bytes leaves the NUL padding inside the logical NSString even though a C-string reader would stop at the first NUL.

| Length-field file offset | Endpoint | Original count | Corrected count |
|---|---|---:|---:|
| `0x02D51378` | geoservice | 57 | 17 |
| `0x02D56898` | ccs putData | 47 | 17 |
| `0x02D610F8` | director-int | 36 | 17 |
| `0x02D61118` | director-stage | 38 | 17 |
| `0x02D61138` | syn-dir | 31 | 17 |

**Confirmed on device:** on an iPhone SE 2 running iOS 15.5, the shipped padded geoservice string produced a nil `NSURL`; copying its `absoluteString` through `+[NSString stringWithString:]` raised `NSInvalidArgumentException`. A clean v1.0 production build aborted after about two seconds in that call path. A native Foundation probe reproduced the failure with the old count and succeeded with 17; the five-field correction allowed the game process to survive the previous startup failure, including a subsequent launch after cache import. This does not establish that every older device, game mode, or separately reported crash has the same cause.

The builder checks the original count bytes before writing each correction. `scripts/validate_url_literals.py` independently discovers CFString records in a built IPA and rejects redirected literals whose logical contents still include NUL padding. The published v1.0 IPA is retained as a failing regression control.

## Optional SE GUI compatibility

The SE option is a separate supported compatibility variant, not a debug-activation experiment. It checks the original instruction sequence at `0x00680B24`, zero padding at `0x00003800`, executable UUID and header separation before applying a 40-byte GUI-only detour. It then sets the fallback GUI atlas family to `2048x1536` and adds the direct SE 2 profile. See [hefti attribution](../third_party/hefti/NOTICE.md), `se_compat.py`, and [v1.1 validation](COMPATIBILITY_V1_1.md).

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
