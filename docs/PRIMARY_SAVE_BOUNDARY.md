# Primary career-save boundary after Time Trial

Tracking: [issue #14](https://github.com/Indegosblade/RR3-DevOps/issues/14). This extends [the ordinary postrace trace](ORDINARY_POSTRACE_FLOW.md). All addresses are unslid ARM64 virtual addresses for executable UUID `06ed5b50c44c3b69a5840701b8a88451`.

The primary career save has a separate deferred lifecycle. A selected `TimeTrialMode::EndRace` branch queues a task that requests saving, but that task's completion predicate is constant true. Task completion therefore does not establish that `character.2.dat` has been written, closed successfully, or survived restart. The existing `rres.bin` and `localleaderboard.bin` probes cannot supply that missing guarantee.

## The concrete postrace-to-save connection

Retained RTTI identifies vtable `0x102BA9660` as `CarDamageTask`. Its constructor is `0x1003C0D40`, start slot `+0x20` points to `0x1003C0D58`, and completion slot `+0x10` points to `0x1003C13E4`.

| Site | Exact-build observation |
|---|---|
| `0x1004D7994` | `TimeTrialMode::EndRace` calls the `CarDamageTask` constructor |
| `0x1004D79A0` | It passes that task to queue helper `0x1004EFF64` |
| `0x1003C11AC`–`0x1003C11B8` | Task start loads the singleton at `0x103251EA0`, then calls save request `0x100645574` |
| `0x1003C13E4` | Task completion is `mov w0, #1; ret`, with no SaveManager read |
| `0x1004F0280`–`0x1004F0288` | Task scheduler calls the completion slot `+0x10`; false holds the current task |
| `0x1004F0490`–`0x1004F0494` | Scheduler starts a subsequent queued task through slot `+0x20` |

This is a connection for the branch selecting this task. Other branches build different task sequences; the trace does not assert that every Time Trial or every exit executes `CarDamageTask`. The complete task start has not been executed in the synthetic probe below, and its other career/car effects are outside the probe.

```text
selected EndRace branch
    -> CarDamageTask start -> request SaveManager pending=1 -> return
    -> CarDamageTask completion predicate returns true

separate SaveManager update
    -> thread and state gates -> primary serialization -> file writer dispatch
```

## The deferred primary-save owner

Request `0x100645574` sets SaveManager byte `+0x22` to 1. It also reads the byte at the game object `+0x478`; if that byte equals 1, it sets a separate SaveManager flag `+0x23` using `stlrb`. Those are two distinct scheduling flags. Their presence is not a proof of a durable generation counter.

Update `0x10064605C` compares current-thread identity against SaveManager `+0x158`. A mismatch follows the retained diagnostic that SaveManager should only be updated from the main thread, then exits this update path. Byte `+0x1C` also blocks the work. When primary pending `+0x22` equals 1, the update calls serializer `0x1006456D0` at `0x10064614C`, then clears `+0x22` at `0x100646150`.

The update clears that pending byte even when the serializer returns zero. Zero suppresses the secondary-save dispatch during that update; it does not re-arm the primary request. On a later unblocked update with primary pending already zero, the original code can process secondary pending `+0x23` without another primary serializer call. This is scheduling behavior, not a proposal to alter retry policy.

The primary serializer return is **not** a disk-success result:

- Byte `+8` not equal to 1 returns 1 immediately at `0x100645760`, without serializing.
- Several game/configuration gates return zero before serialization. Examples include missing owner state, game-state bytes, configured-bitset index `0x45`, and the condition path through `0x100645AB0`. The complete semantic names of these gates are not recovered.
- On the serialization path, the later file writer's output status is not propagated as a durable-success boolean. The routine ultimately returns 1 on its normal tail, including after calling a writer with its own failure logging.

The direct call at `0x100142494` demonstrates an independent caller of the SaveManager update. Other direct callers exist, including explicit request-then-update sequences. This work does not resolve all frame-loop virtual dispatch or establish the ordering of every SaveManager update against every task scheduler update. The constant task predicate is enough to rule out a save-completion wait in that predicate itself.

## Actual primary serialization and filename evidence

On the admitted serialization path, `0x1006456D0` passes the retained name `character` through name helper `0x100645AEC`. That helper normally preserves the name; an explicit test-name mode can format `%s_test` instead. Save setup at `0x100645810` passes that base name, mode 1, and extension `dat` to `0x100642868`. Its filename helper `0x1006431C8` formats `%s.2.%s`, establishing the normal `character.2.dat` filename. No user's file is read to infer it.

The primary serializer calls the Character serializer `0x10075CA10` at `0x100645854`, using the game object's Character member at `+0x478` and SaveManager's serializer member at `+0x28`. Several other subsystem serializers follow before `0x100645978` calls `0x1006436B0`. That wrapper forwards to writer dispatch `0x100943B60`, which locates the matching serializer record and reaches `0x100943C08`.

The writer has a real file-output path: it opens through `0x100942B64`, serializes through `0x100943DD0`, compares a returned byte count with the calculated size, and calls close helper `0x10094258C`. It has distinct open-failure and size-mismatch logging branches. The surrounding code also handles alternate/secondary file names and calls helper `0x10064356C` after the writer dispatch. This trace does not equate those helpers with atomic replacement or a crash-safe transaction.

The static sequence establishes that the primary-save path exists and is separate from ranking/pending-upload storage. It does not prove that the filesystem accepted all bytes, the file codec finalized correctly, close/flush succeeded, the OS made the data durable, or a later launch can load the result. The complete serializer, codec and storage body have not been emulated here.

## Controlled original-instruction probes

```text
python scripts/trace_primary_save.py --input release-dist/RR3-DevOps-v1.1-Production-Quality.ipa --emulate-dispatch
python -m unittest discover -s tests -p test_primary_save.py -v
```

The tracer checks the executable UUID, complete researched instruction windows, task RTTI/vtable slots and filename literals. The synthetic probe executes the original request, constant task predicate, and SaveManager update instructions. It hooks thread identity, logging, the primary serializer and secondary-save body. It never executes the full `EndRace`, task start, Character serialization, codec or real disk operations.

| Controlled case | Observed original-instruction result |
|---|---|
| Request, then task predicate, before an update | Task returns done=1 while primary pending remains 1 and serializer call count is zero |
| Allowed update, serializer hook returns 1 | Primary serializer called once; primary and secondary pending flags consumed |
| Serializer hook returns 0, followed by another update | First update clears primary pending and retains secondary pending; next update processes secondary work without another primary call |
| Wrong thread | Diagnostic hook called; pending flags retained and primary serializer not dispatched |
| Blocking byte `+0x1C` set | Pending flags retained and primary serializer not dispatched |
| Character byte `+0x478` zero | Primary request still set and dispatched; secondary pending not set |

Six tests passed against the original IPA. Both production and SE-compatible v1.1 IPAs passed the same instruction/RTTI/name guards; the production v1.1 IPA also passed the dispatch probes. The five emulator tests explicitly skip when optional Unicorn is unavailable, while the static guard test remains independent. The mocked return-zero experiment models an opaque call result, not an observed disk error: the actual serializer can return zero before any file work and return one without writing.

## Remaining boundary

This narrows the missing evidence to admission gates, full save-body behavior, and real storage finalization/reload. It supplies no basis for forcing task completion, skipping the primary save, deleting queued results, or automatically re-arming a pending flag. In particular, an unconditional re-arm could introduce repeated work on every update while an admission condition persists. Any later behavioral candidate still needs ordinary/local result interaction, offline cold restart, primary progress continuity and controlled failure validation on a real runtime.
