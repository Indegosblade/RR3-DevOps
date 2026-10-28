# Interstitial state ownership and normal close

This extends [the SDK lifecycle trace](SDK_LIFECYCLE_FLOW.md) at its two open
boundaries: game byte `+0x141` and the non-null interstitial popup. It identifies
an initializer and the normal GUI close route. It does **not** establish a
post-scheduling provider failure, a stranded modal, a missing background asset,
or a cause of the reported Time Trial delay. No behavioral patch is proposed.

All executable addresses refer to unslid ARM64 UUID
`06ed5b50c44c3b69a5840701b8a88451`. The read-only tracer verifies that UUID and
SHA-256 guards over each researched code/table window. Optional emulation
executes the input's original instructions with explicit external-call mocks.
Input IPA/cache/release artifacts, signing and devices remain untouched.

```text
python scripts/trace_ad_state.py original.ipa --emulate --output new-report.json
python -m unittest discover -s tests -p test_ad_state.py -v
```

Static tracing uses the standard library; emulation requires `unicorn==2.1.4`.
Reports are created exclusively, so an existing output cannot be overwritten.
The tests use synthetic instruction sequences and tables without shipping game
executable bytes. The mocked RTTI cast assumes a valid event object; mocked
modal removal records a request and does not render or destroy real UI.

## The game bit has a demonstrated initializer, not a semantic name

The task predicate remains:

```text
done = !(manager.byte_0x1b4 & 1) && (game.byte_0x141 & 1)
```

The constructor path at `0x100602840` passes the game object in `x19` to
`0x10008ce60`. The same object is published at `0x100602884` to the global at
`0x103251e60`; the page base is established at `0x1006027bc`. The initializer
keeps that object in `x19` and executes:

```text
0x10008d060  MOV  w8, #0x100
0x10008d064  STRH w8, [x19, #0x140]
```

ARM64 little-endian halfword storage puts `0x00` at object `+0x140` and `0x01`
at `+0x141`. Original-instruction emulation confirms those two writes and
preserves the surrounding bytes. The initial producer is game initialization;
it is distinct from the manager's ad-pending latch producer.

Direct unsigned-immediate byte-load references in the game-owned paths include
`0x100077194`, `0x1000a7e98` and task poll `0x1003cbbc4`. The first two inspect
the same state in wider game control flow. No game-owned direct `STRB` to
displacement `0x141` was found by that instruction-form scan. Other objects in
the executable also use displacement `0x141`, so the report lists their accesses
without treating them as game-state writers.

This scan is **not alias analysis**: indexed stores, adjusted base pointers,
wider writes and runtime code can escape that search. The byte must not be
called immutable, fade-complete, foreground-active, provider-ready or ad-close
state from the current evidence. Its exact semantic meaning and all later
producers remain unresolved. Initialization to true does not authorize forcing
it true during a wait.

## Normal close belongs to the GUI/modal lifecycle

```text
GUI event: type 1 + "BTN_CLOSE"
  -> InterstitialAdPopup handler 0x1001dedac
  -> popup vtable slot +0x1e8: 0x1007e1084
  -> stored callable pointer popup +0x298
  -> member-function binder 0x10066fae4
  -> AdvertisingManager callback 0x10066db6c: clear +0x1b4
  -> request removal from modal owner: 0x1007fbb80
```

The handler checks for a non-null GUI event object, event type `1` and the
literal `BTN_CLOSE` at `0x10257b1e5`. A matching event dispatches the popup's
virtual close operation. Its researched vtable at `0x102b74568` resolves slot
`+0x1e8` to `0x1007e1084`.

The modal close operation can invoke an optional animation hook, invokes the
stored callback at `+0x298` when present, obtains the modal owner and requests
removal. The manager's modal-creation code supplies the callback: its callable
stores the manager instance and `0x10066db6c`. The binder uses those captured
values to call the correct instance. The callback clears that manager's latch;
the separate owner operation handles modal removal. Clearing a byte globally
would bypass this instance and UI lifecycle relationship.

Original-byte execution of six cases verifies that a matching close clears the
latch and requests removal; unrelated event types, labels and a null event
leave the latch and modal alone. A deliberately missing-callback fixture still
requests removal but leaves the latch set. That last case identifies callback
ownership; it is **not** evidence that the real constructor loses its callback.
All cases restore the caller stack and checked callee-saved registers.

## The concrete PCSP provider is separate from Objective-C readiness

RTTI identifies `PCSPRealRacingAd` at vtable `0x102bd30e8`:

| Virtual slot | Target | Observed role |
|---|---|---|
| `+0x10` | `0x10067030c` | Builds a GET request and installs a completion callback |
| `+0x18` | `0x100670514` | Show path, including GUI attachment |
| `+0x20` | `0x1006706bc` | Returns whether provider field `+0xc0` is non-null |
| `+0x38` | `0x100670770` | Click handling, including `Ad Clicked` bookkeeping |
| `+0x40` | `0x100670874` | Returns the stored field `+0xc0` |

The request completion at `0x1006708b8` tests the transport result and HTTP
status/content, forwards parsed data through virtual slot `+0x30`, tests the
loaded predicate through `+0x20`, and invokes the saved load-result callback.
This establishes a concrete game/PCSP provider path. It does not establish
equivalence with the four patched Objective-C ad-ready selectors.

The Show method stores a callback and constructs a provider wrapper, then calls
`0x10053b23c` at `0x100670620` to attach it to a `GuiAdvertisement` registered
for the placement. A failed attachment returns false before the viewed callback;
a successful attachment proceeds through `Ad Viewed` bookkeeping and the
supplied callback. The already-traced manager factory converts a false Show
result into GUI-ad deletion and null before modal scheduling.

The wrapper's virtual methods forward clicks and content retrieval back to
the provider. These native creative operations do not themselves prove an
external fullscreen-ad presentation/error contract. In the observed normal
popup, `BTN_CLOSE` and modal ownership provide the close route.

No trace here demonstrates a provider error **after** a non-null popup is
scheduled that prevents `BTN_CLOSE` delivery or its stored close callback. A
load/attachment failure before scheduling remains the no-fill case already
covered by the lifecycle tracer. Inventing a failed callback in an emulator
would only show that a hypothetical missing callback can strand a latch.

## What would make a targeted fix defensible

An affected runtime trace needs to tie the task, provider and popup to the same
operation: task start and placement; provider result; non-null GUI-ad creation;
modal scheduling; both bytes at the actual wait; close-event delivery; stored
callback identity/invocation; and the modal removal request. A provider error
after scheduling must be observed on that same instance before assigning it
ownership of the wait.

Without that transition, an unconditional task-complete, latch-clear, game-bit
override or generic selector patch is unsupported. The normal close and
constructor tests establish local control flow and ownership, not successful
gameplay, rendering, network behavior or a reproduced black-screen fix.
