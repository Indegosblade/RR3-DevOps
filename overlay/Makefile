# Compile on jailbroken SE (clang-16, Dopamine)
# Target: arm64 dylib for injection via Sideloadly

CLANG = /var/jb/usr/bin/clang-16
SDK = /var/jb/usr/share/SDKs/iPhoneOS.sdk
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
