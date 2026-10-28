# Ordinary Time Trial tasks and result persistence

Tracking: [issue #14](https://github.com/Indegosblade/RR3-DevOps/issues/14).

This extends the [tournament-specific trace](POSTRACE_CONTROL_FLOW.md) into ordinary/local Time Trial result handling. It is a static exact-build trace plus controlled execution of original ARM64 instructions with synthetic records and in-memory file/API hooks. No device, user save, signing material or network service is accessed. No behavioral patch is emitted.

## The ordinary result path is not the tournament timeout

Retained callback RTTI identifies the task-building owner as `TimeTrialMode::EndRace`, beginning at unslid VA `0x1004D7408`. Conditional branches in this function can enqueue `DisplayInterstitialTask`, `RaceStatsTask`, competition signup/upload, leaderboard, tournament aggregate, repair and final upload tasks. Not every branch runs every task.

One branch chooses between `LocalLeaderboardTask` and `LeaderboardTask`:

| Site | Observation |
|---|---|
| `0x1004D7A58` | Calls a configured-bitset lookup with index `0x41` (65) |
| `0x1004D80F0` | Tests the saved result to choose a local or remote constructor |
| `0x1004D811C` | Constructs `LocalLeaderboardTask` via `0x1003D1330` |
| `0x1004D814C` | Constructs `LeaderboardTask` via `0x1003D1614` |
| `0x1004D796C` | Another branch constructs the remote task outside that selection |

The lookup at `0x10016D020` reads a bitset. This call site is not an inline connectivity test, and turning off Wi-Fi does not itself prove that this configured bit changes. The semantic flag name, configuration producer and all update conditions remain unresolved. The existence of a local task is not enough evidence to force all result paths through it.

The local options factory at `0x100153304` creates type **4**; the remote factory at `0x10015329C` creates type **0 or 5**, depending on event data. Both tasks create `LeaderboardScreen` through `0x1003D0058`, derived from `FrontEnd2::EventLeaderboardWithGroups`. They use distinct default layouts, `Leaderboard_Local.xml` and `Leaderboard.xml`.

## Completion is a UI transition, not just a server flag

The shared task predicate at `0x1003D1704` reads the result-screen byte at `+0x471`. Its constructor clears `+0x470` and `+0x471` together.

- `0x1003D03FC` handles pit-lane button events. The retained strings explicitly include `PITLANE_RETRY_BTN`, `PITLANE_NEXT_BTN` and `PITLANE_REPLAY_BTN`. One branch sets `+0x471` at `0x1003D053C`; other branches initiate a result-exit/retry transition through `0x1003D0564`.
- That transition sets `+0x470` at `0x1003D07E4`.
- The update at `0x1003D08AC` waits for exit-started, not-already-done, and a UI-manager state predicate at `0x10081011C` to clear. It then sets `+0x471` at `0x1003D0904`.
- The manager predicate scans state records for enum values 2 or 4. Its exact enum labels are not recovered; calling it an HTTP completion or timeout check would be unsupported.

Consequently, forcing this task predicate true would skip normal result-screen interaction and transitions. It is not a targeted dead-server fix.

## Upload tasks have distinct completion/error behavior

`UploadResultTask` uses a different done byte, `+0x1F`, read at `0x1003EA8D0`. Its constructor initializes done=true. A selected direct-upload path sets it false at `0x1003EA18C`.

The response callback at `0x1003EA5C4` parses two raw response words. A nonempty response can perform acknowledgement/bookkeeping and set done=true. An empty response reaches a retry/cancel UI using:

- `GAMETEXT_RETRY_UPLOAD_HEADER`
- `GAMETEXT_RETRY_UPLOAD_BODY`
- `GAMETEXT_RETRY`
- `GAMETEXT_CANCEL`

The retry callback at `0x1003EA458` reissues submission; cancellation at `0x1003EA584` performs existing cleanup and sets done=true. This is a concrete retry/cancel boundary, but it is not proof of an automatic per-frame retry loop or the measured source of the reported delay.

`DisplayInterstitialTask` is also present in the EndRace task graph. Its predicate at `0x1003CBB9C` considers the ad manager's active-popup state and another game UI-ready byte; its start function remains live even when selected ad SDK readiness stubs are suppressed. This establishes another distinct task to instrument, not a demonstrated ad-related hang.

## Two persistence files with different roles

| File | Observed path | Scope |
|---|---|---|
| `localleaderboard.bin` | Reader `0x1002B3488`, writer `0x1002B3330` | Local ranking structures; the writer traverses nested trees and serializes their records |
| `rres.bin` | Load `0x1003E7F48`, upsert `0x1003E8170`, save `0x1003E8348` | Pending remote-result queue, format version 5 and 68-byte records |

The local leaderboard reader is called while rebuilding the grouped leaderboard table at `0x10025C7DC`. No load-once guard was found in that reader itself. That does not prove it is called every frame or quantify its cost; caller frequency and data sizes still matter.

The read is **once before that rebuild's row/tree loops**, not once per row. No backward branch from the remainder of the analyzed rebuild crosses the read site. Direct rebuild calls were found at `0x100254854`, `0x100254ADC` and local-task setup `0x1003D1594`. The reader itself has direct calls at startup `0x10017588C`, callback `0x100254A44`, and rebuild `0x10025C7DC`. The callback that reads at `0x100254A44` can later invoke the rebuild at `0x100254ADC`, so that path can produce two reads. It is a concrete place to measure duplicate work, not evidence of a per-update disk loop. Dropping the second read still needs invalidation and ordering proof.

The pending-result upsert matches an existing record using the field at record `+4`; it is not simply an unlimited append for every attempt. A type-13 record has an additional value comparison before replacement. The field names and all record semantics are not inferred from these offsets alone.

The queued upload path calls upsert at `0x1003E9FB4`, then save with unload=false at `0x1003E9FCC`. The queue flush routine has one direct caller at `0x10027D9E8`, outside the EndRace task builder. Direct-call counts do not exclude indirect calls, and no per-frame flush loop was established.

None of these queue/ranking findings establishes a `character.2.dat` transaction boundary. The follow-up [primary-save trace](PRIMARY_SAVE_BOUNDARY.md) identifies the selected EndRace task's deferred save request and the distinct serializer/writer path. Its task predicate can report complete before any save dispatch; storage durability and complete main-loop ordering remain unverified. Ranking data, pending upload data and primary career progress must not be treated as interchangeable.

## Queue scheduling is tied to screen entry, not a proven update retry

The direct flush call at `0x10027D9E8` lies inside `FrontEnd2::EventsScreen` method `0x10027D5B4`. Retained RTTI and the vtable identify that method at virtual slot `+0x210`. The common screen-entry dispatcher at `0x10029E490` calls slot `+0x210`, then changes the screen's lifecycle state at `+0x240` to 1.

The EventsScreen per-update slot is a **different** method: virtual `+0xA8`, target `0x10027D424`. Its guarded instruction window contains no direct call to queue load/flush. A flag at screen `+0x2E7` is set after the entry's flush and consumed by a separate screen-readiness method; it is not read by this per-update method as a queue-retry switch.

The empty-reply path in `UploadResultQueue` neither advances a retry/backoff timer nor invokes queue submission again. It calls the save/unload routine and returns. Therefore this traced callback is not evidence of an automatic upload-on-every-update loop. Repeated screen entry or retries below the request-manager interface can still repeat work, and their actual frequency has not been measured.

There **is** a separate update counter in EventsScreen at `+0x2D4`, but its code is a one-shot debounce, not a periodic retry:

1. A value returned by view helper `0x1009DF08C` changes: cache that value at `+0x2D0` and set counter 10.
2. While the value remains unchanged, decrement the counter each update.
3. At zero, call event action `0x1000E95EC` once.
4. Later updates saturate the counter at -1, preventing repeats until the input value changes. Screen entry also resets the cached value.

The action's complete semantics are not recovered here; it must not be labelled a result-upload retry just because it occurs near the flush code.

The flush routine `0x1003E86E0` submits the result vector, then also calls `0x1003EBBFC` to advance separate ghost work. Skipping the entire flush merely because the result vector is empty could suppress that separate work. An empty vector also does not prove the durable file is already empty after a prior save failure.

## The empty-response rewrite is real, but cannot be blindly removed

`UploadResultQueue`'s reply handler at `0x1003E8794` behaves as follows:

1. An empty `BinaryBlobRef` goes directly to the save call at `0x1003E8848`, without changing the queued records.
2. A nonempty response with raw first word 0 similarly retains the records before saving.
3. A nonzero first word takes a processed-response branch, optionally performs existing acknowledgement/bookkeeping, then clears the logical queued record range before saving.
4. The save is requested with unload=true.

The save function rewrites the full queue when opening the output succeeds. Its record loop at `0x1003E83E0` serializes each 68-byte entry. On the successful-open path it closes the file, then clears the loaded flag and logical record range when unload=true. It retains the allocation; this is not a free of the vector buffer.

**If opening the output fails, the original function does not unload.** It returns with the loaded flag and current RAM records intact. This difference is essential for durability.

Every normal enqueue is followed by a save call, but that is not proof the data reached disk. If a new entry was added while an upload was pending and its initial save failed, the later empty-response save may be its first successful persistence. Skipping the rewrite while still unloading could discard the only current in-memory copy of that entry. Leaving the loaded data in memory instead would also change reload/import semantics.

An optimization needs a proven dirty/durable generation or equivalent invariant, plus callback/thread ownership. Neither is established here. There is no safe unconditional skip-write/unload patch in this change.

## Controlled original-instruction probes

```text
python scripts/trace_ordinary_postrace.py --input release-dist/RR3-DevOps-v1.1-Production-Quality.ipa --emulate-queue
python scripts/trace_ordinary_postrace.py --input release-dist/RR3-DevOps-v1.1-Production-Quality.ipa --emulate-events
python -m unittest discover -s tests -p test_ordinary_postrace.py -v
```

The tracer guards the executable UUID, both complete callback/save instruction windows, the shared result predicate and the route branch. The emulator executes the original callback and save routines; file wrappers, record serialization, acknowledgement bookkeeping and binary-blob reads are controlled hooks. It does not run the actual file codec or career-save operations.

For an input with **two RAM entries and one previously durable entry**, the actual instructions produced:

| Controlled input | Written records | Durable count afterward | Loaded / logical RAM count afterward |
|---|---:|---:|---|
| Empty response, output can open | 2 | 2 | 0 / 0 |
| Empty response, output cannot open | 0 | 1 | 1 / 2 |
| Nonempty raw response `(1,1)`, output can open | 0; empty queue persisted | 0 | 0 / 0 |

The last case calls acknowledgement bookkeeping before saving. The mocked subsystem treats a successful close as the commit boundary; real disk flush/finalization failures are outside this probe. These are controlled outcomes, not observations of a user's files or measured write rates.

Eight tests cover the full callback/save guard windows, pending newer entries plus output-open failure, preservation of the later persistence opportunity, empty and zero-status response rewrites, acknowledgement before the processed queue is persisted empty, and the additional cadence invariants below.

The event probe executes the guarded **original activation tail, neutral-state frame update and debounce instructions** with a synthetic UI object and opaque helper hooks. One activation tail invoked flush once; 100 neutral-state updates added no flush; another activation tail invoked it once more. A stable input value generated one debounced action after ten further updates, then no repeat across 100 updates; changing the input generated one further action. These probes do not execute the full application, lower request manager or real screen-entry lifecycle, and do not claim a measured runtime retry rate or callback thread.

## Next bounded work

1. Use the follow-up [request-delivery trace](REQUEST_DELIVERY_FLOW.md), which resolves the concrete manager chain and demonstrates that accepted records can be added while a batch is pending. Callback thread identity, cancellation synchronization and durable queue generations still require stronger evidence before changing rewrite policy.
2. Map successful/failed finalization to a durable queue generation before changing rewrite policy; preserve loaded/logical-range transitions on failure.
3. Measure which EndRace task is slow and the sizes/frequency of the two persistence files when runtime evidence becomes available. Do not infer an infinite retry or quadratic behavior from a single full-file serialization loop.
4. Verify any future candidate through ordinary/local result display, retry/cancel behavior, race completion, offline cold restart and save/cache continuity.

The tournament timeout candidate is separate. No save bypass, forced task completion, broad local-route replacement or ordinary-flow behavioral patch was produced here.
