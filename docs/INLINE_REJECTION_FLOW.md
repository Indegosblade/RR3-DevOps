# Conditional synchronous rejection: request lifetime and helper state

Tracking: [issue #14](https://github.com/Indegosblade/RR3-DevOps/issues/14). This extends [request delivery](REQUEST_DELIVERY_FLOW.md) with the concrete tournament request lifetime. All addresses are unslid VAs for executable UUID `06ed5b50c44c3b69a5840701b8a88451`.

**If the sync manager rejects tournament operation `0x28F4` or `0x28ED` inline, the concrete request is deleted before the shared submission bridge writes the returned ID to that request.** The helper also loses the early error state when its post-launch initialization runs. Both effects occur in controlled execution of the original launch, Start, bridge, manager, response, helper callback and deleting-destructor instructions. The server-derived rejection-set membership is synthetic; no observation establishes this path causes a reported device failure.

## The concrete ownership path

```text
helper allocates request and stores pointer in helper +0 / +8
  -> request Start serializes operation
  -> bridge creates closure holding raw request pointer
  -> SyncManager wrapper forwards to ManagerV34
  -> manager finds operation in rejection set (conditional)
  -> manager invokes empty response closure while holding sync lock
       -> bridge closure invokes concrete request response virtual +0x18
          -> empty-response branch invokes helper callback
             -> helper clears its request pointer and records error
       -> bridge closure invokes concrete deleting destructor virtual +8
          -> destroys vector and callback closure, calls operator delete(request)
  -> manager returns ID 0 and releases sync lock
  -> bridge stores ID 0 to former request +0x10
  -> Start returns; helper caller does not reassign a request handle
  -> helper starts the other request, then resets flags/error and sets pending
```

The request is not a reference-counted owner in this traced path. Its callback closure holds a raw object pointer at closure `+0x18`; the closure invoker `0x1001656A4` forwards it to `0x1001655D0`. That trampoline invokes response virtual `+0x18` at `0x100165604`, then deleting virtual `+8` at `0x100165620`.

| Concrete request | Vtable | Start | Response | Deleting destructor |
|---|---|---|---|---|
| `CC_Helpers::LeaderBoardGroupSync` | `0x102B60970` | `0x100154DA8` | `0x100154F5C` | `0x1001575AC` |
| `CC_Helpers::LeaderBoardSync` | `0x102B60900` | `0x100153724` | `0x100153A6C` | `0x10015742C` |

Each deleting destructor destroys its optional vector and callback closure, then tail-calls `0x102270F08`. The Mach-O indirect-symbol table resolves that import stub to `__ZdlPv`, the Mach-O spelling of C++ `operator delete(void*)`. There is no retain/release test or reference-count condition between response delivery and that destructor call. This establishes an ended object lifetime even though the probe's allocator deliberately leaves the memory mapped.

The bridge preserves the request pointer in `x21` across manager submission and unconditionally executes `str w0, [x21, #0x10]` at `0x100165574` after the manager returns. In the rejection path `w0` is zero and the request has already passed through its concrete deleting destructor and operator-delete call. The probe records this actual memory-write instruction after the delete hook, rather than assuming a delete hook would have been called.

The manager returns a numeric request ID to the bridge. That does not make the request's `Start` a handle-returning API: the observed Start routines call the bridge, destroy their local serialization blob, restore registers and return without constructing a request-handle return value. The helper ignores the return register. It stores group and entries object pointers **before** Start at `0x1001563B8` and `0x1001564C0`. Their callbacks clear those same fields at `0x100156570` and `0x100156670`; no caller-side assignment restores either pointer after Start. Thus this trace demonstrates a write through an ended request lifetime, not a helper resurrecting a stale returned handle.

## Guards and the helper consequence

The helper's original launch `0x1001561FC` has pending/relaunch guards, abandons existing handles when present, and clears pending before creating the new pair. The probe enters with pending zero, no old handles and one synthetic leaderboard ID, so it exercises the ordinary creation path rather than bypassing a guard or directly injecting helper responses.

`LeaderBoardSync::Start` has a separate cached synchronous response path. The actual helper launch writes cache key `-1` at request `+0x68`, making Start take the non-cache serialization path; the probe observes that value at entry. Both response methods also check a global local-response override through `0x1003C752C`. The probe supplies false for that opaque predicate, then executes each original empty-blob branch and helper-closure invoker. It does not establish the predicate's value in a live process.

Each inline empty response reaches its helper callback with pending zero. The callback clears its handle, sets the corresponding received flag and sets error, but does not invoke helper completion. After the two Start calls return, the original block `0x1001564E0..0x10015650C` sets pending and clears both received flags and error. Original instructions therefore erase the responses in the same launch that received them.

| Synthetic manager policy | Pending records after launch | Live helper handles | Post-delete bridge writes | Final helper pending / received / error |
|---|---:|---|---:|---|
| Accept both | 2 | Group and entries | 0 | `1 / 0,0 / 0` |
| Reject group | 1 | Entries only | 1 | `1 / 0,0 / 0` |
| Reject entries | 1 | Group only | 1 | `1 / 0,0 / 0` |
| Reject both | 0 | Neither | 2 | `1 / 0,0 / 0` |

The accepted baseline assigns IDs 1 and 2, keeps the objects alive and invokes no inline response. Every rejection case deletes only the rejected request(s), records the corresponding zero-ID store at former-object offset `+0x10`, leaves the rejected helper handles null, releases the manager lock, and makes zero helper-completion calls. The early received/error flags are observed before the arm block and cleared afterward. With no later response, the existing timer remains the helper's fallback; no real elapsed-time measurement follows.

## Reproduction and limits

```text
python scripts/probe_inline_rejection.py --input release-dist/RR3-DevOps-v1.1-Production-Quality.ipa
python scripts/probe_inline_rejection.py --input release-dist/RR3-DevOps-v1.1-Production-Quality.ipa --experimental-fresh-id-store-guard
python -m unittest discover -s tests -p test_inline_rejection.py -v
```

The script checks the existing delivery tracer's UUID, 21 instruction windows and interface vtables, plus 13 additional bounded windows and five request/closure vtables. Its optional `--output` JSON refuses overwrite. The nine tests use the delivery tests' existing 6,408-byte fixture and only 1,592 additional original instruction bytes with synthetic Mach-O metadata. They cover the accepted baseline, all three rejection combinations, deleted-object write ordering, lost early state, unchanged negative cache guard, changed-window/vtable refusal and rejection-input bounds, plus the candidate checks below. No IPA or private asset is required by the tests.

Allocation, delete, blob serialization/cleanup, lookup policy, time, local-response predicate and Cloudcell getter are controlled hooks. The original wrapper, manager submission, closures, concrete response branches and concrete deleting destructors execute. The delete hook records the call without unmapping or reusing the allocation, allowing the subsequent original write to be observed. This demonstrates the conditional lifetime error; it does not demonstrate allocator corruption, a crash, exploitable behavior, threading properties or save effects in a real process.

The manager's rejection set starts empty and is populated by successful server-response parsing. No captured server response establishes membership for either tournament operation, and an offline connection is not the membership condition. The remaining external invariant is whether the live game/server contract excludes these operations from synchronous rejection (and whether its local-response override changes delivery). This result must not be described as the cause of the community report.

## Experimental guard for the fresh-request lifetime write

`patch_fresh_zero_store(binary)` returns an experimental candidate in memory and a reversible three-region plan. The CLI's experimental flag emulates that candidate and emits the plan; it does not write an executable or IPA. The production builder and releases are unchanged. This candidate only removes the demonstrated post-delete ID write for requests whose ID was zero when submission began. It does not fix helper early-state loss or establish any improvement in a reported delay.

A returned ID of zero is not enough to characterize every path. The wrapper also returns zero without a callback when its concrete manager member is null. The accepted SubSync ID counter increments in 32 bits without an overflow guard, so a synthetic counter at `0xFFFFFFFF` accepts a record with ID zero. Moreover, the shared bridge has 22 direct callers: this analysis does not assume every possible caller submits a new object with ID zero. An unconditional skip of every returned-zero store could preserve an old nonzero ID on a null-wrapper path that originally cleared it.

The candidate therefore latches the **pre-call ID** while the request is alive. It skips the late store only when **both** that initial ID and the returned ID are zero. A fresh request surviving the call retains its original zero value; an inline-deleted fresh request receives no late write. A nonzero returned ID takes the exact original store. An initially nonzero request also takes the original store, including the intentionally unrepaired reused-request rejection case.

The latch uses `w26`. The exact original bridge already saves `x26/x25` at `0x1001654F0` and restores them at `0x1001655C0`; there are no other original reads or writes of `x26` in the bridge. It is a callee-saved register across the manager/response calls. The detour does not grow the frame, change the returned ID, inspect request memory after a zero return, or alter callback/destructor order.

| Changed location | Original instruction / bytes | Experimental behavior |
|---|---|---|
| `0x10016556C` | `mov x3, x23` | Branch to pre-call latch; perform displaced move; return to original `blr` |
| `0x100165574` | `str w0, [x21, #0x10]` | Branch to conditional store; skip only for initial zero and returned zero |
| `0x100003900..0x10000391F` | 32 zero padding bytes | Eight ARM64 instructions for the two leaf detours |

```asm
; Pre-call detour at 0x100003900
ldr  w26, [x21, #0x10]
mov  x3, x23
b    0x100165570
; Post-call detour at 0x10000390C
cbnz w0,  0x100003918
cbnz w26, 0x100003918
b    0x100165578
str  w0, [x21, #0x10]
b    0x100165578
```

None of these instructions writes NZCV. The 32-byte cave is separate from the reserved SE area beginning at `0x3800`. On the read-only v1.1 input, load commands end at file offset `0x33D8`, the first file-backed section starts at `0x4000`, and executable `__TEXT` maps file offset zero at VA `0x100000000`. The patch function validates those relationships, executable permission, zero cave contents, the complete original bridge window, and the original Start/helper caller windows. It refuses an already patched or changed input. Only two four-byte branch sites and the 32-byte cave may change; restoring the plan's original bytes recovers the input exactly.

The full original launch probes compare the candidate against baseline for accepted IDs 1/2 and each rejection combination. Accepted object IDs, pending-vector counts, helper state, callback/delete order and live handles remain identical. Fresh rejected requests retain their callback and deletion, but all writes after their deletion disappear. Helper pending/error state remains identical, including the known loss of early errors. Additional probes cover null-wrapper returns with initial IDs zero and 77, the accepted zero-ID counter wrap, and rejected objects with synthetic initial ID 77. The latter still produce two post-delete writes at the relocated original `str`; the candidate explicitly does **not** fix that condition. The probes compare caller `x19..x29`, ABI-preserved `d8..d15`, SP, final NZCV and NZCV across each conditional-store boundary.

This is a narrow experimental memory-lifetime guard, not a complete request-contract or tournament-flow repair. The cave requires executable header-padding behavior on the actual platform, and any packaged artifact would require proper signing. No device execution has validated it. Fixing helper early-state loss remains separate: moving pending initialization before Start would allow completion to reenter partially constructed state. A complete helper repair would need to preserve accepted asynchronous ownership, consume failure callbacks once, defer user-facing completion until construction is ready, and avoid recursively abandoning requests while the sync rejection lock is held.
