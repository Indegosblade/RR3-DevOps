# Compile with clang-16 on a jailbroken device or cross-compile environment
# Target: arm64 dylib for injection via Sideloadly

CLANG = clang-16
SDK = /path/to/iPhoneOS.sdk
OUT = rr3_overlay.dylib

$(OUT): rr3_overlay.m
	$(CLANG) -arch arm64 -dynamiclib \
		-framework UIKit -framework Foundation -framework CoreGraphics \
		-isysroot $(SDK) \
		-o $(OUT) $< \
		-install_name @rpath/$(OUT) \
		-fobjc-arc -Os -miphoneos-version-min=15.0

clean:
	rm -f $(OUT)

.PHONY: clean
