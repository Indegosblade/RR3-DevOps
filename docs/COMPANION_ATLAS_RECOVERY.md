# Exact companion metadata for recovered original pages

Fifteen of the 47 original HD texture pages found by the
[local content search](LOCAL_ASSET_RECOVERY.md) now have independently
authenticated `sprites.ios.atlas` companions. The recovered stored XML totals
**3,888 bytes**. Each companion matches its original iOS manifest's stored
length and reconstructed transport length/MD5. Assets and provenance remain
under ignored `investigation/recovered_assets/companions/ios/`.

The source metadata came from the pinned matching-version public Android
preservation archives already used for [optional recovery](OPTIONAL_ASSET_RECOVERY.md).
The Android XML **was changed**: exactly one observed texture-format descriptor
was replaced. No image name, position, dimension, hash, whitespace or line
ending was edited. This differs from the unchanged Hybrid Highway XML recovery
described in [asset transport](ASSET_TRANSPORT_FLOW.md).

## Representation and acceptance

```text
exact local texture-page target + original source-page provenance
                      |
            select two possible atlas collections:
            original target and source flashback collection
                      |
    public .android.atlas member -> complete read with ZIP CRC
                      |
          unchanged bytes, or one exact descriptor replacement
                      |
    FMASZ1 + zlib.compress(candidate stored XML, 6)
                      |
    original iOS manifest stored length + transport length + MD5
                      |
         accept exact iOS stored bytes and provenance
```

The observed replacement was precisely:

```text
texture_formats=".ptc.pvr .atc.dds .dxt.dds .etc.dds"
                          ->
texture_formats=".ptc.pvr"
```

Before target promotion, replay applied this replacement to **73 available
source iOS atlas controls**: 42 ADRENO members and 31 Mali members. Every accepted
control reproduced its original local iOS stored bytes byte-for-byte and its
manifest transport representation. These controls overlap between archives:
73 source-member checks cover all **47 distinct source atlas paths** selected
by the original local-page provenance.

[The predicate](../scripts/recover_companion_atlases.py) permits unchanged bytes
or one exact known descriptor replacement. It also recognizes the single values
`.atc.dds`, `.etc.dds` and `.etc.pvr` as candidate descriptors. Only the full list
above has real source-control and target evidence from this experiment. The
single-value cases have synthetic coverage; they are not claimed as observed
recovery results. Unknown or reordered lists are excluded. Matching the
descriptor never establishes compatibility by itself: the original iOS manifest
remains the acceptance authority for every target.

All 15 accepted companions in this pass came from their exact original target
collections. The source flashback collections supplied controls and additional
candidates, but their metadata was not assumed to match a target merely because
a texture page did. Shared texture bytes do not establish shared atlas bytes.
No pixel conversion or arbitrary XML reconstruction was attempted.

## Accepted companions

Paths below are relative to `gui_assets/2048x1536/quests/`; each row identifies
the folders whose `sprites.ios.atlas` representation was authenticated.

| Quest | Accepted atlas folders | Companions |
|---|---|---:|
| `absolut_speed` | `splash/` | 1 |
| `interlagos_interlude` | root, `card/`, `splash/` | 3 |
| `rd_mclaren_artura` | `card/`, `large/`, `splash/` | 3 |
| `track_day_2022_radical_sr10` | `splash/` | 1 |
| `track_day_arx_06` | `card/`, `large/`, `splash/` | 3 |
| `track_day_nissan_nismo_r33` | `card/`, `splash/` | 2 |
| `visions_of_utopia` | `large/`, `splash/` | 2 |

Each output sidecar records the source URL/member/CRC, raw Android stored
digests, edited stored-iOS digests, reconstructed transport digests, exact
transformation, original manifest record/member SHA-256 and zlib runtime
version. The original local archives were opened read-only. Output creation
refused existing payloads or sidecars; a failed write removed only files
exclusively created by that write attempt. Independent readback checked all
15 written assets against the original manifest and checked their sidecars.

## Bounded scan and remaining gaps

The selected set was 94 distinct candidate logical atlas paths per archive:
one original-target collection and one source collection for each of the 47
pages. This experiment did not scan arbitrary other event metadata.

| This pass | ADRENO | Mali |
|---|---:|---:|
| Candidate outcomes persisted | 94 | 47 |
| Complete CRC-validated candidates | 57 | 31 |
| Selected paths absent from archive directory | 32 | 12 |
| Candidates with HTTP 500 read failures | 5 | 4 |
| Validated range payload bytes | 8,424,448 | 8,115,664 |
| Successful range requests | 181 | 100 |
| Per-archive payload cap | 33,554,432 | 33,554,432 |

There were **16,540,112 validated range payload bytes** over 281 successful
requests, plus nine persisted HTTP failures. The maximum individual request was
bounded at 16 MiB and the combined payload cap at 64 MiB. HTTP error bodies were
not read or included in the validated range-payload counter; network headers
and transport overhead are also outside that measurement. No complete archive
was downloaded or hashed.

The scan stopped after three consecutive HTTP 500 failures in Mali. There was
no subsequent network retry. Therefore the selected-set search is **incomplete**,
and the remaining **32 companions are unresolved**. The 44 observed absent-path
outcomes apply only to those exact archive/path combinations. They do not prove
that an atlas is irrecoverable. The earlier interrupted exploratory pass did not
persist its byte count or partial outcomes, so this pass's measurement cannot
be used as a total for the earlier investigation.

The durable research evidence is:

- `investigation/recovered_assets/companions/companion-probe-progress.json`:
  per-candidate extraction outcomes, raw-source digests, HTTP errors, budgets
  and progress at the stop boundary.
- `investigation/recovered_assets/companions/companion-recovery-report.json`:
  replayed source controls, exact target proofs, rejected candidates, unresolved
  targets and output readback evidence.
- `investigation/recovered_assets/companions/raw/`: unchanged Android XML used
  for replay, retained separately from the transformed exact-iOS outputs.

The reusable predicate performs no network or file writes. Its synthetic suite
checks exact unchanged input, all narrowly allowed descriptors, rejection of
wrong content/hashes/names, unknown or reordered descriptors, duplicate fields,
each manifest measurement and preservation of line endings:

```text
python -m unittest discover -s tests -p test_companion_atlases.py -v
```

These 15 atlas/page pairs establish physical content identity within the
original manifests. They do not establish complete event art, receipt
registration, event eligibility, runtime layout or device rendering. No cache,
IPA, signature or device was changed by this recovery.

Together with the six earlier Hybrid Highway resources and 47 local pages,
the separate authenticated inventory covers **68 of the original 909 absent
HD declarations**, leaving **841 unresolved**. A read-only manifest-group join
found that **only Hybrid Highway has a complete HD catalog**. The new partial
collections therefore remain outside the existing seven-resource registered
cache candidate; another large cache build would not establish completeness.
