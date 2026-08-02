# RR3 Debug Overlay

Floating debug overlay for Real Racing 3. Injects as a dylib via Sideloadly, provides an in-game toggle panel for engine debug flags and a tweakable variable browser.

## Features
- Draggable floating "RR3" button
- 8 BSS debug flag toggles (ImGui, Cheat Menu, Debug Render, etc.)
- "ALL ON" quick-enable
- Categorized tweakable browser (Show/HUD, Camera, Render, Car Tuning, AI, Input, etc.)
- Nested navigation (categories -> items)

## Build

Requires clang-16 and an iOS SDK (Xcode or standalone toolchain):

```bash
clang-16 -arch arm64 -dynamiclib \
    -framework UIKit -framework Foundation -framework CoreGraphics \
    -isysroot /path/to/iPhoneOS.sdk \
    -o rr3_overlay.dylib rr3_overlay.m \
    -install_name @rpath/rr3_overlay.dylib \
    -fobjc-arc -Os -miphoneos-version-min=15.0
```

## Inject

Use Sideloadly's "Inject dylibs/frameworks" option:
1. Select the target IPA (e.g., `rr3_4k_v3.ipa`)
2. Click Advanced Options -> Inject dylibs
3. Add `rr3_overlay.dylib`
4. Sideload to device

## BSS Debug Flag Addresses

| Flag | VA | Description |
|------|-----|-------------|
| 0x10324f910 | ImGui Overlay | Main ImGui render gate (6 check sites, up to 512B skip) |
| 0x10324f9d0 | Cheat Menu | MainMenuCheats.cpp:1715 context |
| 0x10324f648 | Cheat Screen | MainMenuCheatScreen |
| 0x10324f640 | Debug Render | Primary debug render flag |
| 0x10324f649 | Debug Flag 2 | Secondary cheat flag |
| 0x10324f9b0 | Debug Flag 3 | Tertiary debug flag |
| 0x10324f9f0 | Debug Flag 4 | Quaternary debug flag |
| 0x10324f9e0 | Debug Flag 5 | Quinary debug flag |
