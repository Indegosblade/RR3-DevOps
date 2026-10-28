# Hefti GUI asset-family compatibility work

`se_compat.py` and the ARM64 admission tests in `tests/test_se_gui.py` are adapted from [hefti/RR3-offline-fix-for-iPhone-SE3](https://github.com/hefti/RR3-offline-fix-for-iPhone-SE3), revision `6ace28dc541674ac52af074a20116db69bcdfb59`.

Copyright (c) 2026 hefti and rr3 contributors. The upstream [MIT license](LICENSE) is retained here and included inside the SE release IPA.

Hefti's contribution coordinates the GUI atlas override with a GUI-only manifest-filter detour. RR3 DevOps adapted the device profile to the SE 2 (`iPhone12,8`) and combined it with the independently diagnosed URL-literal length correction. No upstream diagnostic logger or fishhook component is included in these release IPAs.

The upstream SE 3 result is community-reported. The combined SE 2 candidate was tested locally as described in [v1.1 validation](../../docs/COMPATIBILITY_V1_1.md).
