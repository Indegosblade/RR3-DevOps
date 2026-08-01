# RR3 Debug Overlay

Saturn-style floating debug overlay for Real Racing 3. Injects as a dylib, provides in-game toggle panel for all debug flags.

## Features
- Draggable floating "RR3" button
- 8 BSS debug flag toggles (ImGui, Cheat Menu, Debug Render, etc.)
- "ALL ON" quick-enable
- Categorized tweakable browser (Show/HUD, Camera, Render, Car Tuning, AI, Input, etc.)
- Nested navigation (categories -> items)

## Build
Compile on jailbroken SE (iOS 15.5, Dopamine, clang-16):
```bash
scp rr3_overlay.m root@192.168.88.12:/var/root/
ssh root@192.168.88.12 'cd /var/root && make -f /dev/stdin' < Makefile
scp root@192.168.88.12:/var/root/rr3_overlay.dylib .
```

Or directly:
```bash
/var/jb/usr/bin/clang-16 -arch arm64 -dynamiclib \
    -framework UIKit -framework Foundation -framework CoreGraphics \
    -isysroot /var/jb/usr/share/SDKs/iPhoneOS.sdk \
    -o rr3_overlay.dylib rr3_overlay.m \
    -install_name @rpath/rr3_overlay.dylib \
    -fobjc-arc -Os -miphoneos-version-min=15.0
```

## Inject
Use Sideloadly's "Inject dylibs/frameworks" option:
1. Select rr3_4k_v2.ipa (or any patched IPA)
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
