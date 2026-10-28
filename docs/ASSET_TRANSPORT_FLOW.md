# Asset transport and stored atlas bytes

The three missing Hybrid Highway `sprites.ios.atlas` files have been recovered as exact iOS-manifest representations. The source package labels its stored files `.android.atlas`, but acceptance now rests on the iOS transport length and MD5, followed by lossless expansion to the stored length. No XML, sprite names or manifest hashes were edited.

This closes the metadata gap described in [optional asset recovery](OPTIONAL_ASSET_RECOVERY.md). It does not establish event eligibility, a visible layout, successful device rendering or a black-background fix. Original IPA/cache archives remain unchanged; recovered content and provenance remain in ignored research storage.

## The representation boundary

The asset manifest describes two representations:

```text
logical path -> expected transport MD5, transport byte count, stored byte count

downloaded bytes:  "FMASZ1" + zlib stream
                        |
                        v
asset finalizer:   consume six-byte header -> inflate stream -> write stored file
                        |
                        v
stored atlas:      original expanded XML bytes -> later atlas loading
```

For these atlas records, the manifest MD5 belongs to the transport wrapper. Hashing expanded XML therefore produces a different MD5 even when the stored file is correct. The six-byte header was the missing part in earlier negative experiments with raw zlib and a little-endian size prefix. Those negative results were valid for the representations tested, but did not test the actual wrapper.

The compression level is an empirical encoding result, not a parameter that the decoder imposes. On this host, `b'FMASZ1' + zlib.compress(stored, 6)` with zlib **1.3.1** reproduces the manifest MD5 and both lengths for **all 1,541 compressed iOS atlas paths available in the original local inputs**. No available compressed atlas failed. The scan covers every atlas resolution represented in those manifests; it is not limited to the 909-path missing HD inventory. Another 3,947 compressed atlas paths were absent from these inputs and supplied no known stored bytes for this validation.

Matching a compression level or decompressed appearance alone remains insufficient. The helper requires the exact expected transport length and MD5 for every accepted candidate. A different zlib implementation that emits another valid stream will be rejected if its bytes differ.

## Static executable evidence

The [transport helper](../scripts/trace_asset_transport.py) guards the final iOS executable UUID, resolves virtual addresses through the existing Mach-O segment mapper and checks the full 876-byte finalizer at `0x1016cc0c4`. Its SHA-256 is `009fd7510f0e51ea9db179da0f28a23ab20e4215a60eeba26a83fc818b38b9a8`. It also resolves the imported stubs through the Mach-O indirect-symbol table and checks the `DecompressAsset`, `AssetManager.cpp` and `FinaliseDownloadedAssetFile` diagnostic identities.

| Address | Observed mechanism |
|---|---|
| `0x1016cc13c`–`0x1016cc15c` | Seek input to offset zero, then `fread` six bytes into an allocated header buffer. |
| `0x1016cc160`–`0x1016cc184` | Terminate the buffer and compare overlapping words against the exact six-byte `FMASZ1` magic. |
| `0x1016cc190`–`0x1016cc1d0` | If the header differs, close the input, remove the destination and rename the source to the destination. |
| `0x1016cc218`–`0x1016cc228` | Initialize the zlib stream with imported `_inflateInit_`; the input file remains positioned after the six-byte header. |
| `0x1016cc240`–`0x1016cc2e4` | Read input in 16 KiB blocks, call `_inflate`, and write the expanded output with `_fwrite`. |
| `0x1016cc2e8`–`0x1016cc310` | End the inflate stream, finalize the output and remove the consumed transport input. |
| `0x1016cc388`–`0x1016cc3e8` | End/close the relevant streams and report finalization failure on the observed inflate/read/write failure paths. |

This path contains neither an XOR pass nor an XML parse/serialization step. It is separate from the modified-RC4 transform used for EDS/GUI/NCT files and from the shader/texture de-scrambling path. The host helper adds stricter bounded validation of truncated streams, trailing bytes and excessive output; it does not claim the original decoder has all of these restrictions. The static trace identifies the finalization representation, without claiming to reconstruct the complete downloader or execute the finalizer on a device.

## Exact Hybrid Highway recovery

The matching-version [ADRENO preservation archive](https://archive.org/download/com.ea.games.r3_row_ADRENO_14.0.1/com.ea.games.r3_row_ADRENO.zip), linked by [Project_RR3](https://viduxsh.github.io/Project_RR3/), contains same-logical-path `.android.atlas` members under `com.ea.games.r3_row/files/.depot/`. The source members already contain the expanded XML. Each member was read completely with ZIP CRC validation, then its bytes were wrapped without modification and compared with the original iOS manifest.

All paths below are relative to `gui_assets/2048x1536/quests/hybrid_highway/`:

| iOS atlas | Transport bytes | Stored bytes | Exact iOS transport MD5 |
|---|---:|---:|---|
| `sprites.ios.atlas` | 264 | 418 | `bf2c50954da4f801cbcb1993af931865` |
| `splash/sprites.ios.atlas` | 216 | 259 | `e9ac4ceba855d0b8f0a6409ac4132496` |
| `large/sprites.ios.atlas` | 221 | 266 | `7ccd7225164ed6f80e74351888f9116d` |

The recovered stored metadata totals **943 bytes**. Provenance records both stored SHA-256 and reconstructed transport SHA-256, iOS manifest owner/source archive SHA-256, public archive URL/size/member, ZIP CRC validation and host zlib version. This proves the expanded byte sequences expected by the iOS records despite the source package's Android suffix. It does not establish that arbitrary Android atlases are interchangeable.

The initial bounded discovery pass read **8,404,548 bytes over 13 requests**. A separate reproduction through the finished helper read the same amount, so this investigation consumed **16,809,096 additional range-payload bytes** (about 16.03 MiB). Each run had a hard 16 MiB total/request cap, and no complete source archive was downloaded or hashed. These are additional to the earlier RGB recovery described in the optional recovery document.

```text
python scripts/trace_asset_transport.py --ipa original.ipa --cache Caches_ipastore.zip --report investigation/recovered_assets/optional/atlas-transport-validation.json
python scripts/trace_asset_transport.py --ipa original.ipa --cache Caches_ipastore.zip --recover --output-directory investigation/recovered_assets/optional --report investigation/recovered_assets/optional/atlas-transport-recovery.json
python -m unittest discover -s tests -p test_asset_transport.py -v
```

Recovery first validates the guarded binary and the known local atlas representations. It then checks only these three target paths, refuses conflicting manifests, duplicate/oversized source members and unknown existing outputs, and writes original stored bytes only after exact transport proof. A rerun can recognize an identical file and provenance record. Reports refuse overwrite. Tests use synthetic assets; no game XML or media is embedded in source or tests.

The next boundary is explicit restoration into a separate candidate followed by resource/layout and eventual device verification. These recovery steps neither alter the existing inventory nor import anything into a working cache.
