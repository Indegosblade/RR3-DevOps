# v1.1 compatibility changes and validation

## Choose a build

| Build | Contents | Intended use |
|---|---|---|
| [v1.1 Production Quality](https://github.com/Indegosblade/RR3-DevOps/releases/tag/v1.1-4k) | 18 guarded operations, including corrected URL literal lengths | Default package; retains the existing quality profile |
| [v1.1 SE Compatibility](https://github.com/Indegosblade/RR3-DevOps/releases/tag/v1.1-se) | The same startup correction plus two guarded GUI-filter operations, atlas override and direct SE 2 profile | SE-class small-screen asset-family mismatch; locally validated on SE 2 |

Both use the existing **v1.0 asset cache**. Neither includes the optional developer harness. Both are **ad-hoc/re-sign-required** packages: sign them with your own sideloading account. They contain no development provisioning profiles or CMS signing identities.

## Startup defect

The old builder shortened endpoint text to `http://127.0.0.1/` but left five constant NSString/CFString character counts unchanged. The resulting logical strings included NUL padding. On the tested iOS 15.5 Foundation runtime, the padded geoservice string produced a nil NSURL. The SDK then copied its nil `absoluteString` through `+[NSString stringWithString:]`, raising an uncaught exception.

**Confirmed on device:** a fresh v1.0 production install on an iPhone SE 2 running iOS 15.5 aborted about two seconds after launch in that path. A native Foundation probe reproduced the failure for the padded 57-character form and succeeded for the corrected 17-character form. Correcting the five length fields let the same researched executable survive startup.

## GUI asset-family mismatch

After startup was corrected, the SE 2 still requested data despite a cache import. Scoped checks found all **2,758** high-resolution GUI files and all **four** small-family files from the supplied archive present. The researched runtime asset-limit words were **1334x750**, so the original GUI manifest filter excluded the larger family.

The optional correction, adapted from [hefti's SE 3 work](https://github.com/hefti/RR3-offline-fix-for-iPhone-SE3), changes only GUI manifest admission to a 2048x1536 ceiling and sets `GUI_ATLAS_OVERRIDE=2048x1536`. The original physical framebuffer, global screen-derived values, non-GUI image selection and other 112 EDS settings are preserved. A direct `iPhone12,8.plist` is added while retaining internal resource identity `iPad6,8`.

Hefti and rr3 contributors retain credit and their [MIT license](../third_party/hefti/LICENSE). This release does not include their diagnostic helper or fishhook.

## Evidence and limits

| Result | Evidence category | Boundary |
|---|---|---|
| SE 2 / iOS 15.5 combined candidate loads after cache import | Confirmed on device and by owner observation | Test device was jailbroken; development signing used for the test; optional harness absent |
| 15 Pro / iOS 27.0.1 baseline loads after cache import | Owner-reported device result | Stock device; this was a baseline result, not a separate full test of every v1.1 release artifact |
| SE 3 resource-family fix | Upstream community report | See [hefti's validation record](https://github.com/hefti/RR3-offline-fix-for-iPhone-SE3/blob/main/VALIDATION.md); not an independent test of this release |
| All 50 original/patched ARM64 admission combinations | Emulation | Non-GUI decisions/limits preserved in the tested cases; changed input and occupied cave refused |
| URL literal regression | Synthetic fixture and actual IPA inspection | The v1.0 package fails the literal check; corrected builds pass |
| iPad7,1 / iPadOS 17.7.11, save transfer and Time Trial delays | Unresolved | No such device, original-save migration or performance trace was validated here |

Launch and cache-load success do not establish every race, optional event, car, long session or OS version. The two reported 15 Pro test copies were not separately tracked through full cache-load completion, so this record does not claim universal alternate-bundle-ID compatibility.

Release IPAs are rebuilt from the unmodified community input, not copied from a device. They are re-signed ad-hoc and audited after packaging. Normal code-page hashes are checked; profiles, CMS identities, team fields, private-key blocks, device reports and local-only markers are refused. This is a packaging/privacy audit, not Apple authorization to install without re-signing.

## Reproduce

```text
python build_4k_v3.py original.ipa production.ipa
python build_4k_v3.py original.ipa se.ipa --se-compat
python scripts/validate_url_literals.py production.ipa
python -m pip install unicorn==2.1.4
python -m unittest discover -s tests -v
python scripts/build_releases.py --input original.ipa --zsign /path/to/zsign --output release-dist
```

The synthetic test fixtures contain no game executable or device data. Rebuilding with another tool version or XML/ZIP metadata may produce a different IPA hash; verify downloaded releases with their published hashes rather than assuming cross-tool byte identity.
