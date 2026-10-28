# Experimental two-phase tournament-helper delivery

The existing [inline-rejection probe](INLINE_REJECTION_FLOW.md) demonstrates two different conditional defects: the bridge can store a request ID after deletion, and the helper can erase a response that arrived inside `Start`. Its fresh-ID guard addresses only the first. `scripts/probe_helper_delivery.py` prepares a separate in-memory candidate for the helper state machine. It emits a reversible plan, never an executable or IPA, and changes no production builder or release.

All addresses are unslid for UUID `06ed5b50c44c3b69a5840701b8a88451`. ManagerV34's real rejection-set membership remains unknown. Synthetic synchronous success also tests the helper's contract; it is not evidence that ManagerV34 synchronously returns successful payloads in the live game.

## Ownership and the deferred boundary

The original helper constructor `0x100155EF4..0x10015601C` initializes the request pointers, owned vectors, completion closure, result/rank fields, pending, both response bytes, error and elapsed. In particular `0x100155FF4` clears bytes `+0x103..+0x106`, rather than relying on a zero-filled allocator. The harness fills every allocation with `0xA5` before executing this constructor.

The aggregate-screen constructor initializes its completion byte `+0x264` at `0x1003E4FAC`, constructs the helper through `0x10015601C`, installs its pointer at screen `+0x298` at `0x1003E50B8`, and launches it at `0x1003E50F8`. It returns at `0x1003E5148`. The existing screen-update call at `0x1003E5EF4` enters the helper timer. This is the deferred completion boundary used by the candidate. The screen/update system still requires its existing serialized object-lifecycle rule; this analysis does not establish safety for an arbitrary thread calling update during construction or destruction.

```text
constructor / relaunch
  initialize response/error/elapsed and rank state; pending remains zero
  start group -> early response can latch state, cannot call completion
  start entries -> early response can latch state, cannot call completion
  arm pending without erasing latched responses
  return from launch and screen construction
ordinary update
  pending and (error OR both received) -> clear pending -> existing closure
  otherwise -> existing elapsed accumulation and 30,000-unit timeout
```

The earlier idea of setting pending before `Start` would let a synchronous callback invoke the screen closure under ManagerV34's lock during partial construction. This candidate retains pending zero through both starts. No callback is moved, no request is abandoned from the new detours, and no new helper field or persistent register latch is introduced.

Preserving only the response flags is insufficient: the original timer returns immediately when error is already set. The new timer preflight must consume that state through the existing `0x1001567E8` pending-clear/closure tail. It also recognizes two successful early responses without turning success into timeout/error. Normal post-arm responses continue through the original callback methods and completion path.

## Exact changes and register ownership

| Region | Candidate behavior |
|---|---|
| `0x1001562BC` | Detour the existing pending-clear instruction; clear pending, response/error/elapsed and rank fields before either Start |
| `0x1001564EC..0x100156507` | Replace seven post-start reset instructions with NOPs; retain pending arm, launch timestamp and dirty-configuration reset |
| `0x1001567C4` | Detour the original error test to preflight error/both-received; resume original timer or its existing closure tail |
| `0x100003A00..0x100003A4F` | 80 bytes of guarded leaf code in executable header padding |

Rank resets `+0xE8..+0xF8` move too: the successful entries callback writes these fields, so moving only the Boolean resets would still erase early successful data. The earlier rank reset uses `w8 = -1`, since the original `w27 = -1` has not yet been assigned at that point. It does not borrow an uninitialized register value.

The launch detour uses volatile `x8` and `q0`, then returns to the original `ADRP x8`. The following original launch code assigns `q0` before reading it. The timer detour uses only volatile `w8` and flags; its incomplete path resumes before the original elapsed load/threshold comparison. The detours neither call another function nor change SP or the callee-saved registers. The tests check caller `x19..x29`, ABI-preserved `d8..d15`, and SP. They do not require identical final NZCV, which is caller-clobbered and can differ when the candidate takes its intended new completion path.

Validation checks the original UUID, delivery/lifetime windows and vtables, the complete timer and its known caller, and six additional bounded constructor/configuration/cleanup/closure windows. The 80-byte helper cave must be zero, inside load-command/first-section padding, and entirely within file-backed executable `__TEXT`. It is separate from SE padding at `0x3800` and the fresh-ID guard at `0x3900..0x391F`. Changed or already-patched inputs are refused. Restoring each plan region recovers the original bytes exactly.

`include_fresh_id_guard=True` first validates the unmodified input and prepares both plans from that original. It combines their disjoint changes only after those checks. The helper candidate alone does not repair the deleted-request ID write; the combined plan retains the fresh-ID guard's restriction to an initially zero ID and zero returned ID.

## What executes and what is controlled

The helper harness executes the full original aggregate-screen constructor, helper constructor/configuration/launch, helper success/error callbacks, helper cleanup, original/candidate timer, and screen-completion closure invoker. It observes the aggregate callback at `0x1003E6F78` and records its screen argument, helper state, construction readiness and synthetic lock state. It does **not** execute that callback's UI-building body. The existing [post-race trace](POSTRACE_CONTROL_FLOW.md) owns the static error/results/Continue routing evidence.

Start is a controlled timing boundary in this harness. It either leaves the request outstanding or dispatches the original helper callback with a synthetic success/error payload while a synthetic manager-lock flag is set. Blob parsing, vector copying, allocation/deallocation, base-screen/UI APIs and closure cloning are hooks. The success payload has empty copied vectors plus a synthetic rank record; original entries arithmetic writes distinctive rank data. No full parser, asset or game binary is embedded in tests. The tests add only 1,392 original instruction bytes to the existing small delivery/lifetime fixture.

The concrete Start/bridge/manager/empty-response/deleting-destructor chain remains demonstrated by `probe_inline_rejection.py`. The helper harness tests the new state machine at its callback boundary; it is not a single end-to-end emulation of the combined candidate through ManagerV34 and the UI body. Neither harness establishes actual OS thread identity, cross-thread cancellation synchronization, allocator reuse, platform header-padding execution or device behavior.

## Reproduction and results

```text
python scripts/probe_helper_delivery.py --input release-dist/RR3-DevOps-v1.1-Production-Quality.ipa
python scripts/probe_helper_delivery.py --input release-dist/RR3-DevOps-v1.1-Production-Quality.ipa --experimental-helper-delivery --include-fresh-id-guard
python -m unittest discover -s tests -p test_helper_delivery.py -v
```

Nine tests cover original early-error erasure; early group/entries/both errors; early success for either/both requests; mixed early/late success/error; both normal late-response orders; neither response; unchanged timeout accumulation/expiry; repeated callbacks; cancellation before update; actual sentinel-filled constructor initialization; register/SP preservation; changed-window and occupied-cave refusal; exact bounded differences; and reversible separate/combined plans.

An early error remains pending after construction and invokes the existing closure once on the first normal update, with pending already cleared and error still set. Both early successes invoke that closure once without setting error and preserve the entries-derived rank bytes. The harness records every completion after screen construction and with the synthetic manager lock released; screen completion byte `+0x264` remains zero at callback entry. An accepted late-response schedule produces identical original/candidate helper states and completion records. Cancellation clears pending and prevents the later update from delivering latched completion; this is a sequential lifecycle check, not a cross-thread guarantee.

No wait reduction, offline repair, crash fix, save-safety result or production recommendation follows from these controlled results. The candidate is reviewable for a later explicitly authorized platform experiment; releases and default builds retain their existing behavior.
