# SDK dependency audit

`scripts/audit_sdk_dependencies.py` provides a read-only, offline inventory of
the packaged Mach-O dependency graph. It addresses the framework-removal work
tracked in [issue #5](https://github.com/Indegosblade/RR3-DevOps/issues/5).
It does not strip SDKs, change load commands, disable callbacks or certify a
package for installation.

```text
python scripts/audit_sdk_dependencies.py original.ipa
python scripts/audit_sdk_dependencies.py original.ipa --output sdk-audit.json
python -m unittest discover -s tests -p test_sdk_dependencies.py -v
```

Python 3.12 and its standard library are sufficient. The report defaults to
stdout; an explicit report path must not already exist or resolve to the input
IPA. No archive extraction, credentials, signing operation or device connection
is needed. Input bytes remain unchanged.

## What the audit measures

The audit locates the top-level app, declared bundle executables and `.dylib`
files. It selects the corresponding ARM64 slice, reads load commands and maps
`LC_SYMTAB` undefined-symbol ordinals to their declared libraries. It records
strong/weak/reexport/upward/lazy load kinds, candidate packaged/system
resolution, direct edges and reachability through transitive dependencies.

Segment-backed virtual addresses are mapped to slice-relative file offsets.
Selected SDK classes and initialization-method implementations are recovered
from Objective-C metadata. These are actual class definitions in each image,
not merely occurrences of SDK names in strings. Absolute and relative method
lists are supported; unreadable encoded metadata is counted rather than guessed.

The framework table sums current ZIP entry sizes and records `__text` and
instruction-section sizes. These measurements describe bytes in the package,
not runtime allocation, download traffic or startup time.

## Reproduced v1.1 inventory

Input: `RR3-DevOps-v1.1-Production-Quality.ipa`, SHA-256
`d1ccf110ec538545169d93cdae8a8fd839cb9015d02c0f495570a0f1089c2148`.
These are static measurements, with no new device run.

| Measurement | Result |
|---|---:|
| Framework directories | 46 |
| All framework bytes, uncompressed | 18,453,795 (17.60 MiB) |
| All framework ZIP-compressed bytes | 5,742,291 (5.48 MiB) |
| Frameworks with zero `__text` bytes | 37 |
| Those 37 framework bytes, uncompressed | 1,748,672 (1.67 MiB) |
| Those 37 framework ZIP-compressed bytes | 339,531 (0.32 MiB) |
| Selected packaged ARM64 images | 51 |
| Statically reachable images from main, including weak edges | 13 |

The nine framework bundles with nonzero text are AppLovinSDK, FBAEMKit,
FBSDKCoreKit, FBSDKCoreKit_Basics, FBSDKGamingServicesKit, FBSDKLoginKit,
FBSDKShareKit, HelpshiftX and fuelmetrics. The main executable imports symbols
from several of them: AppLovin 26, Helpshift 26, CoreKit 11, Basics 7,
fuelmetrics 6, Login/Share/Gaming 2 each. Import counts establish linkage, not
execution of every imported function. FBAEM has no main-symbol import but is
a hard dependency of FBSDKCoreKit.

The main executable itself defines `FIRApp`, `FIRAnalytics`, `FIRRemoteConfig`
and `GADMobileAds`. Deleting their small namesake framework bundles does not
remove that embedded SDK implementation. Zero text or no statically resolved
incoming edge does not prove that a bundle's resources are unused.

The current package therefore cannot lose 50 MiB just by deleting its framework
directories. A claim of improved performance needs measurements of actual work
removed, not the number of SDK names present.

## A live initialization boundary

For executable UUID `06ed5b50c44c3b69a5840701b8a88451`, Objective-C metadata
and instruction inspection establish the following unslid addresses. The
portable audit reports the method implementations and type encodings; call
sites below were checked by disassembling this exact executable.

| Boundary | Address | Observed behavior |
|---|---|---|
| `-[RealRacingAppDelegate application:didFinishLaunchingWithOptions:]` | `0x10092c734` | Calls `InitialiseFirebase` at `0x10092cacc`, then returns success after its stack check |
| `-[RealRacingAppDelegate InitialiseFirebase]` | `0x10092d80c` | Selects configuration using the bundle-ID region markers and constructs Firebase options |
| App call to `+[FIRApp configureWithOptions:]` | `0x10092d944` | Reaches implementation `0x101488840`; this method returns `void` |
| `+[FIRApp addAppToAppDictionary:]` | `0x1014892c0` | Calls `configureCore`; a false result reaches the explicit Firebase exception at `0x101489364` |
| `-[RealRacingAppDelegate EnableFirebaseCollection:]` | `0x10092d9d8` | Receives the engine-derived collection flag after initialization |
| App call to `setAnalyticsCollectionEnabled:` | `0x10092d9f0` | Applies that collection flag; initialization has already happened |
| App tail call to `setCrashlyticsCollectionEnabled:` | `0x10092da80` | Applies the same flag to Crashlytics |

A matching startup exception was recorded during the earlier controlled tests.
This is runtime-backed evidence that Firebase initialization is still active,
not a new runtime test or evidence that Firebase causes the reported visual
problem. The existing ad-readiness patches do not bypass this boundary.

Simply NOPing the configuration call is not a justified release change. Its
return value is unused at this caller, but other SDK state is not. Seven direct
main-code calls to the `defaultApp` selector stub remain at `0x1013262dc`,
`0x10148e774`, `0x10148f194`, `0x10169f1f4`, `0x101ed810c`, `0x101ed9514`
and `0x101ed9668`. Their missing-initialization behavior has not been established.
The wrapper also performs collection setup after configuration. An ABI-level
safe return does not prove that the remaining process has valid SDK state.

### Negative result: forced installations-token refresh

`EnableFirebaseCollection:` contains a narrowly scoped
`authTokenForcingRefresh:completion:` call at `0x10092da64`, with callback
implementation `0x10092da84`. The callback logs an error or the returned token;
no gameplay or UI transition was found in that callback body. Token values must
not be copied into public diagnostic output.

However, the call is guarded by the app's `CloudcellEnvironment` being
`development` or `stage`. The unmodified input, v1.0 production and v1.1
production packages all declare **`live`**, which skips this call. Disabling it
would not remove this request from the current release because that branch is
already skipped. It is not a demonstrated fix for startup, Time Trial delays
or black backgrounds. This negative result is retained to avoid promoting an
ineffective patch.

## Boundaries and next experiments

- Static resolution uses an image's own rpaths plus the main executable's
  rpaths, not a complete context-sensitive dyld run-path stack. System resolution
  is a classification, not verification against a particular OS shared cache.
- Undefined symbols come from `LC_SYMTAB`. Bind streams, chained-import tables,
  dynamic `dlopen`/`NSBundle` lookup, constructors and callback lifecycles are not
  exhaustively evaluated. Zero counted imports does not mean unused code.
- The audit selects ARM64 images. Its 51-image count differs from a signature
  audit counting every architecture slice in universal files.
- Selected Objective-C ownership is not a complete inventory of statically
  linked SDKs. Encoded/chained class pointers can remain unreadable.
- Removing `LC_RPATH` search paths is different from removing `LC_LOAD_DYLIB`
  requirements; Apple's [`install_name_tool` implementation](https://github.com/apple-oss-distributions/cctools/blob/main/misc/install_name_tool.c)
  explicitly distinguishes them. Neither operation resolves remaining symbol
  bindings or application-level SDK expectations by itself.

The next useful offline work is to trace the specific operation reported slow
or visually incomplete to its wait/retry and completion/failure paths. Preserve
normal completion semantics if an unnecessary network operation is eventually
suppressed. The collection controls above are narrower policy boundaries than
removing SDKs, but their effect on network work and the reported symptom has
not been measured. No behavioral suppression patch is included in this audit.

Before promoting a future candidate, validate the affected screen or results
transition, main menu/garage, race completion, cold offline restart and save
continuity on a device. Devices were disconnected for this audit; no new claim
of gameplay, image restoration or performance improvement is made.
