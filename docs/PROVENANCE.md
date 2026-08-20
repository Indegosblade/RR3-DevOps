# Provenance and Credits

RR3 DevOps is built on community work. This page records what was inherited, what this project contributes, and what still needs better attribution.

## Upstream offline iOS preservation work

The final iOS package used as the starting point already made local play possible by combining an offline-capable IPA, a gesture-accessed local-file importer, and a complete asset cache.

The strongest public attribution currently available is [Bokun_Zhao's community guide](https://www.reddit.com/r/RealRacing3/comments/1u8xtmj/ios_real_racing_3_v1401_ipa_with_local_asset/), which credits:

- **有时会很闲** — the Chinese user credited for the self-contained iOS package.
- **Flickxie** — credited for providing the asset cache.

That guide documents the same basic flow used here: sideload the modified IPA, open the upstream importer with a three-finger double-tap, import `Caches_ipastore.zip`, force-quit, and relaunch. It is the public source for these credits; RR3 DevOps does not claim authorship of that upstream offline workflow.

The RR3 DevOps author encountered the preserved package through AppDB. AppDB is a discovery/source path, not evidence of original authorship.

## RR3 DevOps's original work

This repository adds and documents work performed for RR3 DevOps:

- the production `build_4k_v3.py` patcher and its exact final-build patch table;
- reverse engineering and implementation of the modified-RC4 EDS transformation;
- a modern-device quality profile derived from the existing iPad Pro tier;
- runtime investigation of developer flags and the tweakable registry;
- recovery of the `0x78`-byte registry-entry layout and live-value write path;
- the optional UIKit developer harness, its description dataset, verification behavior, snapshot reset, and diagnostic dump; and
- the research notes that record dead ends as well as working results.

The project is documented so that others can reproduce, verify, correct, and extend the method.

## Scope of redistribution and licensing

The releases distribute a community-preserved game package/cache alongside RR3 DevOps's original tooling. This repository does not claim ownership of the upstream package, the game, its assets, or the upstream import mechanism.

Only the original source and documentation authored for RR3 DevOps are released under this repository's [MIT License](../LICENSE). If the upstream package's original author publishes a source repository, license, or preferred attribution, please open an issue with the primary source so this record can be updated.

## Attribution is a living record

The names above are credited as they appear in the public community source. Transliteration, original links, and lineage may be incomplete. Corrections are welcome and should include a source link, screenshot, archive, or other evidence. See [Contributing](../CONTRIBUTING.md).

## Release integrity

The downloadable [SHA256SUMS.txt](../SHA256SUMS.txt) records GitHub's SHA-256 digest for every current v1.0 release asset. Verify the individual parts before reassembling the cache.
