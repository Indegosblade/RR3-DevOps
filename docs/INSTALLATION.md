# Deployment Guide

This guide describes the community-preserved iOS workflow used by the RR3 DevOps release assets. Read [Provenance and credits](PROVENANCE.md) first: the offline importer/cache workflow predates RR3 DevOps.

## Requirements

- An iPhone or iPad with sufficient free storage for the IPA and imported cache.
- A macOS or Windows computer for sideloading. [Sideloadly](https://sideloadly.io/) is the documented tool used by the upstream public guide.
- The [v1.0-4k](https://github.com/Indegosblade/RR3-DevOps/releases/tag/v1.0-4k) IPA and every part from [v1.0-cache](https://github.com/Indegosblade/RR3-DevOps/releases/tag/v1.0-cache).
- Optionally, `RR3-DevOps-v1.0-Developer-Harness.dylib` from [v1.0-overlay](https://github.com/Indegosblade/RR3-DevOps/releases/tag/v1.0-overlay).

The confirmed RR3 DevOps device test is an iPhone 17 Pro on iOS 26.0. The upstream public guide identifies iPad and iPhone 12-or-newer as its documented target class. This is not a guarantee for every device; report compatibility results with details.

## Gesture reference

When the RR3 DevOps harness is injected:

- **One three-finger tap** shows or hides the RR3 DevOps overlay.
- **One three-finger double-tap** opens the upstream community package's local cache importer, allowing `Caches_ipastore.zip` to be selected directly from on-device storage.

The cache importer is part of the upstream preserved iOS package, not the RR3 DevOps harness. See [Provenance and credits](PROVENANCE.md).

## 1. Reassemble the cache

Download every `RR3-DevOps-v1.0-Asset-Cache.zip.partXX` asset into one folder.

**Windows**

```text
copy /b RR3-DevOps-v1.0-Asset-Cache.zip.part00+RR3-DevOps-v1.0-Asset-Cache.zip.part01+RR3-DevOps-v1.0-Asset-Cache.zip.part02 Caches_ipastore.zip
```

**macOS / Linux**

```text
cat RR3-DevOps-v1.0-Asset-Cache.zip.part* > Caches_ipastore.zip
```

Keep the finished `Caches_ipastore.zip` accessible in the Files app. Do not extract it before the in-app importer accepts it.

## 2. Sideload the IPA

1. Open Sideloadly and connect the target device.
2. Select `RR3-DevOps-v1.0-Production-Quality.ipa` from [v1.0-4k](https://github.com/Indegosblade/RR3-DevOps/releases/tag/v1.0-4k).
3. Sign and sideload using the normal account workflow.
4. Launch the installed app once.

The package uses bundle identifier `com.ea.realracing3.inc`. Replacing a build with another build using the same identifier can preserve Documents data, but back up data before testing a different IPA.

## 3. Import the cache

The upstream community package includes a local-file cache importer. Open it with one three-finger double-tap, then:

1. Select the first import function and choose `Caches_ipastore.zip`.
3. Wait for import to complete.
4. Force-quit the app and relaunch it.

If the game still requests data after a completed import, use [Troubleshooting](TROUBLESHOOTING.md) and provide the exact request size, device, iOS version, IPA/cache release names, and observed importer behavior.

## Optional: inject the runtime harness

1. Download `RR3-DevOps-v1.0-Developer-Harness.dylib` from [v1.0-overlay](https://github.com/Indegosblade/RR3-DevOps/releases/tag/v1.0-overlay).
2. In Sideloadly, open **Advanced Options** and add the dylib under **Inject dylibs/frameworks**.
3. Sideload the IPA with the dylib selected.
4. Wait for initialization. A floating `RR3` button normally appears after approximately 11 seconds; the runtime registry retries initialization for up to 16 seconds if the game is still starting.

The harness is optional and build-specific. See [Runtime developer harness](../overlay/README.md) for architecture and limits.

## Re-signing and backup

Re-signing requirements depend on the Apple account and sideloading method. Back up Documents/save data before re-signing, reinstalling, or replacing an IPA.
