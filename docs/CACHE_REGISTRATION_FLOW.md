# Cache receipts and optional-group admission

Adding the recovered Hybrid Highway files supplies the missing stored content, but does **not** make the normal AssetManager group-completion check accept those paths. That check also requires matching entries in the global cache receipt map. The existing group manifest already supplies the authoritative requested paths, transport hashes and sizes; no new per-group catalog is needed for these six HD resources.

The preserved cache's only receipt file is `asset_list_base.txtCache.txt`. Despite its name, the traced loader and writer use this fixed filename for the shared path-to-hash map that is consulted while processing other asset-list groups. This is a separate layer from direct resource-path resolution. A loader may find an added file while the download service still considers the group incomplete.

```text
bundled optional-group catalog       global on-disk cache receipts
path + transport MD5 + sizes          fixed asset_list_base.txtCache.txt
             |                                  |
             |                         LoadCacheList -> in-memory map
             |                                  |
             +-------- LoadAssetList -----------+
                             |
          runtime agent may filter paths for the selected platform/family
                             |
              each selected path has matching receipt?
                      /                    \
                    yes                    no
                     |                     |
          increment completed count   pending/download accounting
                     |
           all selected entries complete?
                     |
              group downloaded result

stored file on disk -> separate physical-path resolution/load
```

## Verified ledger format and lifecycle

The [read-only registration tracer](../scripts/trace_cache_registration.py) checks the executable UUID and full hashes of nine relevant code regions, plus format strings, imported file-I/O symbols and AssetManager RTTI/vtable identity. Reports remain under ignored research storage. It provides no ledger writer.

`LoadCacheList` at `0x1016c3564` reads two four-byte words, validates magic `0xa4f6f39d` and format version **4**, then scans the following text line and compares it with a decimal value read through the global client context. `SaveCacheList` at `0x1016c70bc` writes those same binary words and formats that context value with `%u\n`. The current file's text value is **7469**; it is **not an entry count**. Its exact source-level property name remains unresolved, so the tracer calls it a client revision token. The observed file actually contains **24,792** path/hash records.

The subsequent format is one path, a tab, a 32-character lowercase transport-MD5 value and a newline per record. Loading inserts these records into the map rooted at AssetManager `+0x198`. Saving iterates that shared map and writes its path/hash pairs to the fixed ledger path. The load function has a byte guard at manager `+0xe0`, so the observed path initializes this map once rather than rereading the file for each group check.

**File records need not be sorted.** The read loop at `0x1016c3920` processes records until EOF and inserts each key through `0x1016cf50c`. Its search at `0x1016cf5a8` compares the incoming key with existing tree keys in both directions and descends left or right; `0x1016cf640` links/rebalances the selected insertion. It neither compares the input row with the preceding file row nor requires monotonic input order. The save routine's tree traversal naturally writes key order, but that is an output property, not a loader precondition. Appending unique authenticated records can therefore preserve the existing header, revision line and original record bytes without sorting or rewriting them. Duplicate/conflicting records still need refusal; their overwrite semantics are not used as a registration mechanism here.

An initial-load flag controls whether each recorded path is passed through the physical-path resolver before insertion. This is a file-presence check, not a reconstructed transport hash calculation over stored atlas XML. The host audit deliberately keeps receipt status and stored-file presence as separate facts; neither one proves rendering.

## The finite admission boundary

| Address | Verified behavior |
|---|---|
| `0x1016c4fc8` | Group loader first ensures the global cache receipt map is initialized. It resolves and reads the requested asset-list file. |
| `0x1016c536c`–`0x1016c5384` | An optional agent callback can filter a manifest path before the map/completion logic. The actual selected runtime filter was not executed here. |
| `0x1016c5388`–`0x1016c53bc` | Look up the manifest path in the global receipt map. |
| `0x1016c53e4`–`0x1016c54c4` | In the observed flag-controlled branch, a physically present path absent from that map is logged as `Untracked asset file in cache`. Finding the file here does not insert a successful receipt. |
| `0x1016c5728`–`0x1016c576c` | Compare the selected path's recorded MD5 with the catalog's MD5. Only a present matching entry increments the completed count and skips the pending path. |
| `0x1016caa10` | Format the four stored MD5 words as `%08x%08x%08x%08x`, then compare that string with the catalog value. This helper does not open or hash the expanded file. |
| `0x1016cac38`–`0x1016caca4` | The downloaded-check wrapper calls the group loader and returns whether the total and completed counts are equal. Its pointer is at AssetManager vtable `0x102c5dc98`, slot `+0xf8`. |
| `0x1016cb9cc`–`0x1016cba94` | Download finalization reads the temporary transport bytes, computes their digest and compares all four words with the expected digest before accepting them. |
| `0x1016cbac8`–`0x1016cbbac` | After successful [transport expansion](ASSET_TRANSPORT_FLOW.md), append the path and transport digest to the open receipt file, flush/fsync it, and insert/update the in-memory map. |

The distinction matters for atlases: the receipt stores the **transport MD5** even though the filesystem ultimately contains expanded XML. Putting the XML's raw MD5 into a registration record would fail the catalog comparison. A receipt is the downloader's retained completion evidence, not a claim that the current expanded file has just been rehashed.

A bounded Unicorn probe executes the actual guarded counting fragment beginning at `0x1016c5728`, with synthetic map/result memory. It supplies only the equality result of the already-traced MD5-comparison helper and stops at the first divergent branch:

| Synthetic map state | Completed-count increment | Stop |
|---|---:|---|
| Path absent | 0 | `0x1016c5770` |
| Path present, catalog transport MD5 matches | 1 | `0x1016c5268` |
| Path present, MD5 differs | 0 | `0x1016c5778` |

This is host execution of a decision fragment with controlled inputs. It does not execute the full AssetManager, the platform filter, a resource loader, game startup or an event on a device.

## The preserved inputs and the recovery candidate

The original Hybrid Highway catalog contains **18** resources across three resolution families. The original cache has **zero** matching receipts and **zero** files for those exact paths. Its six HD entries are the three recovered atlas/page pairs. `flashback_hybrid_highway` is a separate path family; its existing receipts do not register `hybrid_highway` resources.

In contrast, the original ledger already records `SpeedRush_TV_commercial.mp4` and its exact transport MD5, although the original archive lacks the movie file. Restoring that movie addresses a physical-content gap for an already recorded resource. Restoring the six Hybrid Highway files addresses physical content while leaving the separately demonstrated receipt gap.

A candidate that only appends those recovered members is therefore a **payload recovery candidate**. It preserves provenance and is useful for import/path/layout investigation, but should retain an explicit runtime gate. If the runtime selects those HD entries, physical presence alone cannot satisfy the traced completion branch. The complete 18-entry catalog must also not be treated as a requirement to fabricate other resolution families: the runtime agent controls which paths matter on the selected setup.

This trace supports the need for matching global completion receipts when using the normal group-admission path. It found no need to invent another per-group registration filename or replace the original group catalog. It does not authorize arbitrary receipts, prove a complete event restoration, or establish all startup cleanup behavior. Any separately constructed registration candidate must preserve the original ledger and derive its new receipts from independently verified original transport representations; no original ledger, hash or catalog was modified by this investigation.

```text
python scripts/trace_cache_registration.py --ipa original.ipa --cache Caches_ipastore.zip --report investigation/recovered_assets/optional/cache-registration-original.json --probe-branch
python scripts/trace_cache_registration.py --ipa original.ipa --cache recovery.candidate.zip --report investigation/recovered_assets/optional/cache-registration-candidate.json
python -m unittest discover -s tests -p test_cache_registration.py -v
```

The same read-only audit can compare separate candidates. A payload-only candidate retains missing receipts; a registered candidate adds the independently authenticated transport receipts below. Neither projection proves device rendering or runtime event eligibility.

## Guarded registered candidate

`scripts/build_recovered_cache.py` requires the exact Hybrid Highway manifest SHA-256, the known original cache hash, the verified movie and all six authenticated HD GUI resources. Atlas receipts come from their reconstructed original transport MD5, not the expanded XML's raw MD5.

The writer preserves the original ledger bytes, magic, version, revision line and all 24,792 existing records as an exact prefix. It appends six unique records and refuses conflicting hashes, unsafe/control-character paths or a receipt without its verified payload. It does not change the group catalog or any existing receipt hash. The new ledger parses to 24,798 records and retains revision token `7469`.

```text
python scripts/build_recovered_cache.py --ipa original.ipa --cache Caches_ipastore.zip --movie investigation/recovered_assets/SpeedRush_TV_commercial.mp4 --asset-root investigation/recovered_assets/optional --output investigation/recovered_assets/registered.candidate.zip
```

This operation creates a separate archive. Unlike the movie-only append, replacing the existing ledger uses public ZIP rewrite APIs so the output has one unambiguous ledger member rather than duplicate ZIP names. Unchanged file contents/CRCs, timestamps, permissions, compression methods, entry order and archive comment are retained; compression bytes and offsets may be regenerated. Failed new outputs are removed while inputs stay intact.

The full local candidate was built and read back: 59,926 original entries retained, seven original resources added, one additive ledger update. It was 5,529,709,353 bytes with SHA-256 `b6f19e16a1d3b9f1500a16c03a2c96ac02e9ab88b26623932b32ef343c7b6cd8`. That is the fingerprint of this host build, not a published release or a universal cross-version ZIP hash.

| Host check | Original | Registered candidate |
|---|---:|---:|
| HD group stored resources present | 0 / 6 | 6 / 6 |
| HD group authentic matching receipts | 0 / 6 | 6 / 6 |
| Base-ledger paths absent from inventory | 1 | 0 |
| Available atlases | 3,321 | 3,324 |
| Atlas image entries | 107,082 | 107,086 |
| Missing referenced atlas pages / invalid sprite bounds | 0 / 0 | 0 / 0 |

The candidate does not resolve any of the 658 previously unresolved static GUI image names; Hybrid Highway's recovered sprites are a separate content restoration, with runtime associations still to establish. The large archive was deleted after verification, leaving only compact evidence and verified small assets in ignored research storage. No working installation or stable release was replaced.

For a future device check, import into a separate test copy and force-quit/cold-relaunch before checking the group: the traced receipt map has an initial-load guard, so replacing a file underneath an already initialized map is not a refresh mechanism. Verify selected resolution, group admission, actual sprite lookup and event behavior separately.
