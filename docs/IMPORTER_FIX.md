# Inherited importer: save handoff repair and English interface

RR3 DevOps's contribution here is limited to repairing the inherited importer's
save-application/restart handoff and translating its interface into English.
The original file-assistant UI, ZIP implementation and exporter remain upstream
work. Its iPA Store branding, support links and existing attribution are retained;
see [provenance and credits](PROVENANCE.md).

![Inherited importer with English labels](images/importer-english.png)

## The failure and the repaired boundary

On the tested runtime, the inherited importer replaced the files correctly but
left the old profile loaded in memory. Leaving the game invoked its primary
serializer and opened `character.2.dat` in `wb` mode, overwriting an imported
valid self-export. A later export could consequently contain the old profile
again. ZIP structure and successful extraction alone did not prevent this.

The repair keeps the upstream menu and exporter and changes the save worker:

```text
Import Save & Close -> selected ZIP
  -> main-queue worker; old main-thread game save cannot interleave
  -> validate root save filenames, stream sizes and ZIP CRCs
  -> upstream extractor writes an owned temporary staging folder
  -> verify every staged file's size and CRC
  -> preserve recovery copies of existing destination files
  -> atomically rename each staged file into Documents
  -> verify destination bytes, clean owned staging, _exit(0)
  -> user reopens the game; the new runtime loads the imported files
```

An invalid archive returns to the inherited failure UI in English. Reported
replacement failures trigger rollback rather than successful termination. If
rollback itself fails, its staging/recovery copies are retained. This is atomic
per file with rollback for reported errors; it is not a power-loss-safe
transaction across the entire set of files. Keep an independent original save.

Cache import retains its separate `Library` route and does not acquire the
close-on-success behavior. The exporter and three-finger gesture are retained.
No game executable patch, save-format conversion, account merge or cloud-service
restoration is added by this change.

## Use

1. Keep the original installation and an independent save backup.
2. Use a ZIP with save `.dat` files directly at its root, including the exact
   lowercase filename `character.2.dat`. Use a complete matching export when
   available; mixing files from different profiles is not validated here.
3. Choose **Import Save & Close** and select the ZIP.
4. A successful import closes the game deliberately. Reopen it to load the save.
   An error leaves the game running and displays **Import Failed**.

The worker accepts up to 64 root save files with ASCII filenames of at most
128 bytes, 64 MiB per file and 256 MiB total expanded save data. It rejects
nested/traversal paths, case-colliding duplicates, unsupported compressed input,
missing/empty `character.2.dat`, bad CRCs and failed staged verification.
Known ZIP metadata (`.DS_Store`, `__MACOSX/`) is ignored. A graphics-cache ZIP
belongs in **Import Graphics Cache**, not the save action.

These checks establish archive/file integrity, not that an arbitrary career
format, account state or save version is compatible with the game. A completed
save from another installation remains a separate acceptance case.

## Build and scope

The production source builder applies this repair when the inherited AppData
component is present. Its existing game/quality patches remain the v1.1 baseline;
the importer changes are the v1.2 addition.

```text
python build_4k_v3.py original.ipa RR3-DevOps-v1.2-Production-Quality.ipa
python build_4k_v3.py original.ipa RR3-DevOps-v1.2-SE-Compatibility.ipa --se-compat
```

For an existing v1.1 package, the standalone helper changes only
`Frameworks/AppData.dylib`, preserving every other member's content and ZIP
metadata:

```text
python scripts/fix_importer.py v1.1.ipa importer-fixed.ipa
```

Both commands produce packages that require re-signing. The profile-free
release builder performs ad-hoc signing and the existing privacy/code-page
audit; pass a local zsign executable with ad-hoc support. No private signing
identity or device connection is accepted by these builders.

```text
python scripts/build_releases.py --input original.ipa --zsign path/to/zsign --output release-dist/importer-v1.2
```

The patcher checks the two researched AppData UUIDs, all file-backed section
hashes, the original container configuration and unused executable header
padding before making changes. Changed, unsupported or already-patched inputs
are refused. The native repair source is [native.c](../importer_fix/native.c);
the small generated payload is original repair glue, not copied game code.

The helper uses only scalar AAPCS64/Darwin-compatible arguments, reserves Apple's
platform register x18, and has no variadic, aggregate, ARC or TLS ABI dependency.
Its arm64e dynamic-function calls authenticate pointers; ordinary ARM64 uses
the corresponding plain branch. No Apple SDK or additional runtime library is
bundled. Reproduce the payload with the pinned temporary compiler:

```text
python scripts/build_importer_payload.py --zig path/to/zig-0.14.1 --check
```

The English mapping covers all 149 inherited Chinese constant messages in each
architecture, including the menu, file browser, progress, errors and diagnostics.
It preserves format arguments. CFString encoding flags, character counts and
character-data pointers are updated together; arm64e chained-fixup link bits are
preserved. Original unreferenced string bytes remain in the binary. This is a
translation of runtime messages, not a claim that a raw string scan contains no
Chinese bytes.

## Validation and limits

On our test device running iOS 15.5, both ARM64 and ARM64e versions were loaded
and exercised separately:

- Invalid ZIP: game remained running, all eight save hashes stayed unchanged,
  and the English failure notification appeared.
- Valid self-export: staging ran on the main thread outside `Documents`, exit
  status zero was observed on that thread, and all eight imported files matched
  exactly after the old process had terminated.
- An isolated synthetic eight-file ZIP replaced a 719,928-byte file with
  4,569,856 bytes through the native worker. Real save files were unchanged by
  that size test.
- Cache-marker import reached `Library`, kept the game running and left the
  save hashes unchanged. Export still produced eight root `.dat` files with
  exact original contents and valid ZIP CRCs. The English menu was rendered and
  inspected; all 149 translated constant messages also matched in the loaded
  ARM64e image.

Both v1.2 package variants passed the profile-free audit: 53 verified Mach-O
code directories each, no provisioning profiles, CMS identities or tested
private markers. Independent package readback matched the final native payload
and all English messages in both architectures. Main executable code and EDS
profiles matched the corresponding v1.1 variants.

The tests invoke the inherited delegate with local sandbox URLs. They do not
establish every external Files/iCloud provider interaction or iPadOS 17 behavior.
No completed cross-installation career transfer, Garage availability or universal
save compatibility is claimed. The pre-test save was backed up and restored;
raw backups, device identifiers and diagnostic reports remain outside Git.

Host tests execute the actual C repair core with explicit Foundation/minizip
ports and real temporary files. They cover successful application, corrupt ZIPs,
staged corruption, unsafe paths, duplicates, limits, backup/commit failure,
rollback/recovery retention and termination boundaries. Separate tests check
CFString representations, source guards, ASLR trampoline arguments and bounded
archive differences. Proprietary-input checks skip when the original IPA is
unavailable; host C checks skip if no compiler/test library is provided.
