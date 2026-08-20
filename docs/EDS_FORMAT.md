# EDS Format and Quality Profile

Real Racing 3's Engine Device Settings (EDS) are encrypted plist files under `res/eds/`. They select quality and platform settings for known device profiles.

## Modified RC4 transformation

The researched EDS function is a symmetric modified-RC4 transformation. The implementation in `build_4k_v3.py` is the source of truth.

- **Function VA:** `0x100726200`
- **Key bytes:** `a5 35 b3 b1 e8 43 e7 cf`
- **Base algorithm:** RC4 key-scheduling and PRGA
- **Post-KSA operation:** an additional swap pass over S-box indices `1..133` begins with its own `j = 0`.
- **PRGA start:** `i = 133`, carrying the post-scramble state.

The script encrypts and decrypts with the same `eds_crypt()` function and asserts a round trip before producing output.

## Profile selection

The RR3 DevOps profile starts from the existing iPad Pro 12.9-inch profile (`iPad6,8`) rather than inventing a new internal device identity. All 113 keys and the iPad resource/GUI family are retained.

Filename selection is handled through:

- `iPhone18,1.plist` — direct filename match for the tested iPhone 17 Pro;
- `iPhone.plist` — fallback filename.

The internal `PLIST_IDENTIFIER` remains `iPad6,8`. Testing found that an unknown internal identifier could break resource lookup during engine initialization.

## Intentional quality changes

| Setting | iPad Pro baseline | RR3 DevOps profile |
|---|---:|---:|
| `USE_ANISOTROPIC_FILTERING` | `false` | `true` |
| `STREAMING_CAR_SHADOW_MAPS` | `false` | `true` |
| `PROP_MIN_COVERAGE` | `0.005` | `0.001` |
| `PIXEL_THRESHOLD_CUBEMAP_LOW_DETAIL` | `400` | `800` |

## Meaning of the 4K label

“4K” identifies the elevated device profile. The profile retains `EXPECTED_SCREEN = 2732×2048`, the iPad GUI cluster, and 512-pixel cubemaps. It is not a claim that every rendering path uses a literal 3840×2160 framebuffer.

## Configuration constraints

- `PLIST_IDENTIFIER`, expected screen, and GUI-resource cluster must remain consistent.
- A filename can add a model match without changing the internal resource identity.
- Larger settings are not automatically safer: 1024-pixel cubemaps and other untested extremes were intentionally excluded from the mobile profile.

The binary contains a separate XOR-plus-decompression path associated with some shader/texture data. It is not the EDS transformation and is not used by `build_4k_v3.py`.

For the implementation and supported patch context, see [`build_4k_v3.py`](../build_4k_v3.py) and the [Production binary patch specification](BINARY_PATCHES.md).
