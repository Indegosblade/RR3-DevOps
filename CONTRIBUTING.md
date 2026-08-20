# Contributing to RR3 DevOps

RR3 DevOps is provided as-is, with documentation intended to support reproducible community work. Contributions are welcome when they improve evidence, attribution, compatibility knowledge, or implementation quality.

## Issue preparation

Before opening an issue:

1. Read [Troubleshooting](docs/TROUBLESHOOTING.md).
2. Confirm the exact release asset and final iOS build in use.
3. Search existing issues for the same symptom or finding.
4. Collect device model, iOS version, release asset, exact steps, screenshots/logs, and a relevant `tweakable_dump.txt` excerpt when the harness is involved.

## Valuable contributions

- Confirmed compatibility results for another device or iOS version.
- Better provenance, attribution, licensing, or cache-lineage sources.
- Repeatable corrections to a tweakable description.
- Android research that identifies an equivalent registry or entry layout.
- Documentation corrections that distinguish confirmed facts from inference.
- Focused source changes with a clear test result.

## Evidence standard

Use one of these labels in issues, pull requests, and documentation:

- **Confirmed by source/disassembly** — directly supported by tracked source or repeatable binary analysis.
- **Confirmed on device** — observed on a stated device/build with reproducible steps.
- **Inferred** — a reasoned interpretation from a name, call path, or related behavior.
- **Unresolved** — an open question; do not present it as a working feature.

## Pull requests

Keep each pull request narrow and state the target build, exact change, verification method, and remaining uncertainty. Do not add game binaries, caches, extracted resources, credentials, or unrelated generated files to Git history.

## Attribution corrections

Attribution is part of the technical record. If you can improve an upstream name, translation, source, license, or asset lineage, open an issue with the primary evidence. RR3 DevOps will correct the record when better information is available.

## Support model

There is no support SLA and no promise that every issue will receive an individual response. A complete, reproducible report lets other players and researchers validate the result and move the project forward.