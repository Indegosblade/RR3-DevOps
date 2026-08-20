# Troubleshooting

This project is provided as-is, but most useful failures can be narrowed down with a little information. Start here before opening an issue.

## The game asks to download assets after import

1. Confirm that every cache part was downloaded and reassembled without an error.
2. Open the upstream importer with one three-finger double-tap, then import the finished `Caches_ipastore.zip`; do not point it at an already-extracted folder.
3. Wait for import to finish, force-quit the app, then reopen it.
4. Confirm the device is within the asset family's practical target range. The upstream guide reports 2048×1536 assets intended for iPhone 12-and-newer/iPad-class devices; older devices can require a different GUI/asset-resolution family.

If it still requests data, report the exact request size, device model, iOS version, IPA/cache release names, and whether the import showed completion.

## The game crashes on launch

- Verify that the IPA was sideloaded cleanly and has not expired.
- Retry once without the optional overlay. This separates base-package issues from harness-injection issues.
- Do not substitute an older or unrelated RR3 IPA for the researched release.
- Back up existing Documents/save data before reinstalling or replacing an IPA.

## The `RR3` overlay button never appears

- Confirm `RR3-DevOps-v1.0-Developer-Harness.dylib` was selected under Sideloadly's **Inject dylibs/frameworks** option.
- Wait for the game to initialize; the button normally appears after roughly 11 seconds, while the runtime registry can retry for up to 16 seconds.
- Test the base IPA without the overlay first.
- Record the device, iOS version, exact IPA, and overlay release. If available, include whether `Documents/tweakable_dump.txt` was created.

## A tweakable change appears to do nothing

The overlay's checkmark means the value was written and read back through the researched live pointer. It does not prove the current race/menu state will consume that value immediately. Try a new race/menu transition, reset the value afterward, and report the raw tweakable name plus the before/after value.

## The original cheat/ImGui UI does not appear

That is expected. RR3 DevOps does not claim to have fully restored the original retail developer UI. Use the UIKit harness as the working interface to the runtime registry; treat the BSS debug flags as research controls.

## I need to re-sign the app

Re-signing requirements depend on the Apple account and sideloading method. Back up data first, then use your normal Sideloadly/AltStore-style refresh workflow. This repository does not provide account-signing support.

## What to include in an issue

Use this compact template:

```text
Device model:
iOS version:
IPA release/file:
Cache release/file:
Overlay injected: yes/no
Exact steps:
Expected result:
Actual result:
Screenshots/logs/dump excerpt:
```

Clear reports help the community reproduce a problem even when the original author is unavailable.
