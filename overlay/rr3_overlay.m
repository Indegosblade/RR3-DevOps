/*
 * rr3_overlay.m — Saturn-style debug overlay for Real Racing 3
 * Live tweakable browser: reads 847 engine variables from BSS vector,
 * groups by category, provides sliders/toggles for real-time editing.
 *
 * Entry layout (0x78 bytes, confirmed via setter at 0x1000314c0):
 *   +0x00  uint32  ID
 *   +0x08  24-byte SSO name ("TWEAKABLE_CAMERA_Z_FAR")
 *   +0x20  uint32  type (0=string, 1=int, 2=bool, 3=double, 4=float)
 *   +0x28  24-byte SSO label (often empty)
 *   +0x40  8-byte  value cache
 *   +0x48  void*   pointer to live game variable
 *   +0x50  8-byte  min value
 *   +0x58  8-byte  max value
 *   +0x60  8-byte  default value
 */

#import <UIKit/UIKit.h>
#import <mach-o/dyld.h>
#import <objc/runtime.h>
#import <math.h>

#pragma mark - Debug Flags

typedef struct { uint64_t va; const char *label; const char *desc; } RR3Var;

static RR3Var g_flags[] = {
    {0x10324f910, "ImGui Overlay",
     "Engine's ImGui debug UI renderer. Enables developer panels, perf graphs, memory stats. Touch input is NOT wired to ImGui — needs Bluetooth keyboard or controller to navigate menus."},
    {0x10324f9d0, "Cheat Menu",
     "Developer cheat system (MainMenuCheats). Contains: Unlock All Cars, Unlock All Tracks, Free Currency, Max Level, Skip Tutorial, Full Upgrade, Reset progress, Firebase debug. Displayed through ImGui panels."},
    {0x10324f648, "Cheat Screen",
     "Cheat screen display panel (MainMenuCheatScreen). Separate UI surface for cheat options. Requires ImGui to render."},
    {0x10324f640, "Debug Render",
     "Master debug visualization. Enables wireframe overlays, collision mesh display, physics debug (Bullet), AI path visualization, PVS boundaries, spline points. Most visual of all debug flags — look for colored wireframes on track and cars."},
    {0x10324f649, "Cheat Flag B",
     "Secondary cheat subsystem flag (1 byte after Cheat Screen in BSS). Likely enables a sub-feature of the cheat system. Toggle and observe."},
    {0x10324f9b0, "Profiler Gate",
     "Debug subsystem flag in the ImGui/Cheat BSS region. May gate ProfilingHarness and performance measurement code paths. Toggle and check for profiling overlays."},
    {0x10324f9f0, "Debug System A",
     "Debug subsystem flag. Purpose not fully identified from binary — toggle during gameplay and observe for visual or behavioral changes."},
    {0x10324f9e0, "Debug System B",
     "Debug subsystem flag. Purpose not fully identified from binary — toggle during gameplay and observe for visual or behavioral changes."},
};
#define NUM_FLAGS (sizeof(g_flags)/sizeof(g_flags[0]))

static intptr_t g_slide = 0;

static uint8_t *flagPtr(int idx) {
    return (uint8_t *)((uintptr_t)g_flags[idx].va + g_slide);
}

#pragma mark - Tweakable System

#define TWEAK_VEC_BASE  0x10324f478
#define TWEAK_VEC_END   0x10324f480
#define TWEAK_STRIDE    0x78
#define TW_OFF_NAME     0x08
#define TW_OFF_TYPE     0x20
#define TW_OFF_VAL      0x40
#define TW_OFF_PTR      0x48
#define TW_OFF_MIN      0x50
#define TW_OFF_MAX      0x58
#define TW_OFF_DEF      0x60

enum { TW_STRING=0, TW_INT=1, TW_BOOL=2, TW_DOUBLE=3, TW_FLOAT=4 };

static NSMutableArray *g_categories = nil;
static NSMutableDictionary *g_catEntries = nil;
static int g_tweakCount = 0;
static NSDictionary *g_catLabels = nil;
static NSDictionary *g_tweakDescs = nil;

static NSString *prettyName(NSString *raw) {
    NSArray *parts = [raw componentsSeparatedByString:@"_"];
    NSMutableArray *out = [NSMutableArray array];
    for (NSString *p in parts) {
        if (p.length == 0) continue;
        if (p.length <= 3 && [p isEqualToString:[p uppercaseString]])
            [out addObject:p];
        else
            [out addObject:[[[p substringToIndex:1] uppercaseString]
                stringByAppendingString:[[p substringFromIndex:1] lowercaseString]]];
    }
    return [out componentsJoinedByString:@" "];
}

static BOOL isBoolLike(NSString *name) {
    if ([name containsString:@"_AMOUNT"] ||
        [name containsString:@"_SCALE"] ||
        [name containsString:@"_SIZE"] ||
        [name containsString:@"_POSITION"] ||
        [name containsString:@"_ANGLE"] ||
        [name containsString:@"_FALLOFF"] ||
        [name containsString:@"_CENTRE"] ||
        [name containsString:@"_CENTER"] ||
        [name containsString:@"_RATE"] ||
        [name containsString:@"_THRESHOLD"] ||
        [name containsString:@"_DELAY"] ||
        [name containsString:@"_ZOOM"] ||
        [name containsString:@"_FOV"] ||
        [name containsString:@"_TILT"] ||
        ([name containsString:@"_OFFSET_"] || [name hasSuffix:@"_OFFSET"]) ||
        [name containsString:@"_WIDTH"] ||
        [name containsString:@"_HEIGHT"] ||
        [name containsString:@"_MAX_"] ||
        [name containsString:@"_MIN_"] ||
        [name containsString:@"_TO_RENDER"])
        return NO;
    if ([name hasSuffix:@"_ENABLED"]) return YES;
    if ([name containsString:@"ENABLE_"]) return YES;
    if ([name containsString:@"_CAN_"]) return YES;
    if ([name containsString:@"_USE_"]) return YES;
    if ([name hasPrefix:@"TWEAKABLE_SHOW_"]) return YES;
    if ([name hasPrefix:@"TWEAKABLE_ALLOW_"]) return YES;
    if ([name hasPrefix:@"TWEAKABLE_RENDER_"]) return YES;
    if ([name hasPrefix:@"TWEAKABLE_DEBUGRENDER_"]) return YES;
    if ([name hasPrefix:@"TWEAKABLE_HUD_"]) return YES;
    static NSSet *known = nil;
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        known = [NSSet setWithArray:@[
            @"TWEAKABLE_AI_RUBBER_BANDING",
            @"TWEAKABLE_AI_RECALC_OPPONENTS",
            @"TWEAKABLE_DAMAGE_PLAYER_ENABLED",
            @"TWEAKABLE_DRIFT_ENABLED",
            @"TWEAKABLE_PARTY_PLAY",
            @"TWEAKABLE_PAUSE_BLUR",
            @"TWEAKABLE_HOTSWAP_ENABLE",
            @"TWEAKABLE_NETWORK_PROFILING_ON",
            @"TWEAKABLE_PVS_DEBUG",
            @"TWEAKABLE_CUBEMAP_ENABLED",
            @"TWEAKABLE_PHOTO_MODE_ENABLED",
            @"TWEAKABLE_CAMERA_PHOTO_MODE",
            @"TWEAKABLE_CAMERA_MENU_SCENE_FREE_ORBIT",
            @"TWEAKABLE_CAMERA_CHASE_2",
            @"TWEAKABLE_CAMERA_SHOW_CAR_SHADOW_BASE",
            @"TWEAKABLE_CAR_OVERRIDE_ENABLED",
            @"TWEAKABLE_INPUT_VIBRATION_ENABLED",
            @"TWEAKABLE_CUTSCENE_DISABLE_INTRO_OVERLAY",
            @"TWEAKABLE_FEAT_EVENT_DEBUG_INFO",
            @"TWEAKABLE_ENABLE_NASCAR_TUTORIAL",
        ]];
    });
    return [known containsObject:name];
}

static void initLabels(void) {
    g_catLabels = @{
        @"AI": @"AI Opponents",
        @"CAMERA": @"Camera",
        @"CAR": @"Car Tuning",
        @"DEBUGRENDER": @"Debug Render",
        @"HUD": @"HUD",
        @"INPUT": @"Input & Controls",
        @"RENDER": @"Rendering",
        @"SHOW": @"Display",
        @"PHOTO": @"Photo Mode",
        @"FEAT": @"Features",
        @"NETWORK": @"Network",
        @"DAMAGE": @"Damage",
        @"ALLOW": @"Render Pipeline",
        @"CUTSCENE": @"Cutscenes",
        @"OTHER": @"Other",
    };
    g_tweakDescs = @{
        @"CAR_MAX_SPEED_KPH": @"Top speed in km/h",
        @"CAR_WEIGHT_KG": @"Car mass in kilograms",
        @"CAR_BRAKE_PERCENT": @"Brake force multiplier",
        @"CAR_STEER_ANGLE": @"Maximum steering angle",
        @"CAR_TRACTION_CONTROL": @"Traction control level",
        @"CAR_MAX_RPM": @"Engine rev limiter",
        @"CAR_OVERRIDE_ENABLED": @"Master toggle for car tuning",
        @"CAR_ACC_PERCENT_GEAR_1": @"Throttle power — 1st gear",
        @"CAR_ACC_PERCENT_GEAR_2": @"Throttle power — 2nd gear",
        @"CAR_ACC_PERCENT_GEAR_3": @"Throttle power — 3rd gear",
        @"CAR_ACC_PERCENT_GEAR_4": @"Throttle power — 4th gear",
        @"CAR_ACC_PERCENT_GEAR_5": @"Throttle power — 5th gear",
        @"CAR_ACC_PERCENT_GEAR_6": @"Throttle power — 6th gear",
        @"CAR_FORCE_ENGINE_SOUND_ID": @"Override engine sound",
        @"AI_CAN_DRIVE": @"Let AI cars drive",
        @"AI_PLAYER_AI_SKILL_LEVEL": @"Opponent difficulty",
        @"AI_RUBBER_BANDING": @"AI catch-up mechanic",
        @"AI_USE_GHOST_MODE": @"AI cars pass through each other",
        @"AI_STUCK_RESET_TIMER": @"Seconds before stuck AI resets",
        @"AI_RECALC_OPPONENTS": @"Recalculate opponent lineup",
        @"AI_1PT5_ERROR_RANGE": @"AI driving error margin",
        @"AI_CREST_SPEED_LIMIT_R4": @"AI speed limit over crests",
        @"CAMERA_Z_FAR": @"Far draw distance",
        @"CAMERA_Z_NEAR": @"Near clipping plane",
        @"CAMERA_PHOTO_MODE": @"Free camera for screenshots",
        @"CAMERA_MENU_SCENE_FREE_ORBIT": @"Free orbit camera in menus",
        @"CAMERA_CHASE_2": @"Alternate chase camera",
        @"CAMERA_ONBOARD_PITCH": @"Cockpit camera pitch angle",
        @"CAMERA_ONBOARD_YAW": @"Cockpit camera yaw angle",
        @"CAMERA_FAR_CLIP_OFFSET": @"Far clip distance offset",
        @"CAMERA_NEAR_CLIP_OFFSET": @"Near clip distance offset",
        @"CAMERA_BANKING_OFFSET": @"Camera banking angle",
        @"CAMERA_TRACK_FAR_CLIP": @"Track far clipping",
        @"CAMERA_TRACK_NEAR_CLIP": @"Track near clipping",
        @"CAMERA_SHOW_CAR_SHADOW_BASE": @"Show shadow origin point",
        @"RENDER_WIREFRAME": @"Wireframe render mode",
        @"RENDER_ENABLED": @"Master render on/off",
        @"RENDER_HDR": @"High dynamic range",
        @"RENDER_SSAO": @"Screen-space ambient occlusion",
        @"RENDER_MOTION_BLUR": @"Motion blur effect",
        @"RENDER_SHADOWS": @"Shadow rendering",
        @"RENDER_REFLECTIONS": @"Reflections",
        @"RENDER_FOG": @"Fog effect",
        @"RENDER_WEATHER": @"Weather effects (rain, etc.)",
        @"RENDER_LENS_FLARE": @"Lens flare effect",
        @"RENDER_GLOW": @"Bloom / glow effect",
        @"RENDER_LIGHT_BEAMS": @"Volumetric light beams",
        @"RENDER_CARS": @"Show car models",
        @"RENDER_CAR_SHADOWS": @"Car shadow rendering",
        @"RENDER_COCKPIT": @"Cockpit interior",
        @"RENDER_HUD": @"Heads-up display",
        @"RENDER_SKY": @"Sky rendering",
        @"RENDER_TRACK": @"Track surface",
        @"RENDER_PARTICLES": @"Particle effects (sparks, dust)",
        @"RENDER_POST_PROCESS": @"Post-processing pipeline",
        @"RENDER_SKID_MARKS": @"Tire skid marks",
        @"RENDER_CUBEMAPS": @"Environment cubemaps",
        @"RENDER_ENV_MAP": @"Environment map reflections",
        @"RENDER_FLAT_SHADOWS": @"Flat shadow mode",
        @"RENDER_INVERTED": @"Inverted colors",
        @"RENDER_TRANSPARENT": @"Transparent objects",
        @"RENDER_BEFORE_UPDATE": @"Render before game update",
        @"RENDER_GPU_PROFILING": @"GPU performance profiler",
        @"RENDER_DEBUG_INFO": @"Render debug info overlay",
        @"INPUT_GYRO_STEER_SENSITIVITY": @"Tilt steering sensitivity",
        @"INPUT_STEER_SENSITIVITY": @"Steering sensitivity",
        @"INPUT_STEER_LINEARITY": @"Steering response curve",
        @"INPUT_VIBRATION_ENABLED": @"Haptic feedback on/off",
        @"INPUT_VIBRATION_STRENGTH": @"Haptic intensity",
        @"INPUT_ACCEL_LOWER_DEADZONE_PERCENT": @"Throttle lower deadzone",
        @"INPUT_ACCEL_UPPER_DEADZONE_PERCENT": @"Throttle upper deadzone",
        @"INPUT_BRAKE_LOWER_DEADZONE_PERCENT": @"Brake lower deadzone",
        @"INPUT_BRAKE_UPPER_DEADZONE_PERCENT": @"Brake upper deadzone",
        @"INPUT_FORCE_CONTROLLER_TYPE": @"Force specific controller type",
        @"SHOW_FPS": @"Framerate counter",
        @"SHOW_CC_AND_EVENT_IDS": @"Show challenge & event IDs",
        @"SHOW_NDT_WORM": @"Network debug timeline",
        @"HUD_SHOW_DEBUG": @"Debug HUD overlay",
        @"HUD_SHOW_DEBUG_PLANE": @"Debug plane visualizer",
        @"HUD_ENABLE_EXTERNAL_PLANE_OFFSETS": @"External plane offset debug",
        @"DEBUGRENDER_ENABLED": @"Master debug render toggle",
        @"DEBUGRENDER_COLLISION": @"Show collision meshes",
        @"DEBUGRENDER_BULLET": @"Physics engine debug",
        @"DEBUGRENDER_BULLET_TRACK_COLLISION": @"Track collision debug",
        @"DEBUGRENDER_CIRCUIT": @"Show circuit path",
        @"DEBUGRENDER_SUSPENSION": @"Show suspension geometry",
        @"DEBUGRENDER_TRIGGER_AREAS": @"Show trigger zones",
        @"DEBUGRENDER_VISUAL_PROFILER": @"Visual performance profiler",
        @"DEBUGRENDER_METRICS": @"Performance metrics overlay",
        @"DEBUGRENDER_NAVMESH": @"Show navigation mesh",
        @"DEBUGRENDER_PARTICLES": @"Particle debug view",
        @"DEBUGRENDER_CUBEMAP_PROBES": @"Show cubemap probe locations",
        @"DEBUGRENDER_SPLINE_POINTS": @"Show racing line spline",
        @"DEBUGRENDER_TRACK_DIST": @"Show track distance markers",
        @"DEBUGRENDER_AI_SPLINE_LOOK_AHEAD_CAR": @"AI path prediction lines",
        @"DEBUGRENDER_HOTSWAP": @"Asset hot-reload debug",
        @"DEBUGRENDER_INCAR": @"Interior debug view",
        @"DEBUGRENDER_PVS": @"Visibility set debug",
        @"DEBUGRENDER_SKID_MARKS": @"Skid mark debug view",
        @"DEBUGRENDER_CAR_SHADOW": @"Car shadow debug",
        @"DEBUGRENDER_ACCFORCE_R4": @"Acceleration force vectors",
        @"DAMAGE_PLAYER_ENABLED": @"Crash damage on/off",
        @"DRIFT_ENABLED": @"Drift mode",
        @"PAUSE_BLUR": @"Blur effect when paused",
        @"PARTY_PLAY": @"Party play mode",
        @"CUBEMAP_ENABLED": @"Cubemap rendering",
        @"HOTSWAP_ENABLE": @"Asset hot-reload",
        @"NETWORK_PROFILING_ON": @"Network profiler",
        @"PVS_DEBUG": @"Visibility debug",
        @"ALLOW_ALPHA_TEST": @"Alpha test pipeline",
        @"ALLOW_BLEND": @"Alpha blend pipeline",
        @"ALLOW_DEPTH_TEST": @"Depth test pipeline",
        @"ALLOW_STENCIL_TEST": @"Stencil test pipeline",
        @"ENABLE_NASCAR_TUTORIAL": @"NASCAR tutorial sequence",
        @"CUTSCENE_DISABLE_INTRO_OVERLAY": @"Skip intro overlay",
        @"FEAT_EVENT_DEBUG_INFO": @"Event debug info display",
        @"PHOTO_MODE_ENABLED": @"Enable photo mode",
    };
}

static NSString *readSSO(uint8_t *base) {
    uint8_t flag = base[23];
    if ((flag & 0x80) == 0) {
        int len = flag;
        if (len > 22) len = 22;
        return [[NSString alloc] initWithBytes:base length:len
                    encoding:NSUTF8StringEncoding] ?: @"??";
    }
    char *ptr = *(char **)base;
    uint64_t sz = *(uint64_t *)(base + 8);
    if ((uintptr_t)ptr > 0x100000000ULL && sz < 256)
        return [[NSString alloc] initWithBytes:ptr length:sz
                    encoding:NSUTF8StringEncoding] ?: @"??";
    return @"??";
}

static float readTweakFloat(uint8_t *entry) {
    uint32_t type = *(uint32_t *)(entry + TW_OFF_TYPE);
    void *vp = *(void **)(entry + TW_OFF_PTR);
    if (!vp) return 0;
    switch (type) {
        case TW_BOOL:   return (float)*(uint8_t *)vp;
        case TW_INT:    return (float)*(int32_t *)vp;
        case TW_FLOAT:  return *(float *)vp;
        case TW_DOUBLE: return (float)*(double *)vp;
        default: return 0;
    }
}

static void writeTweak(uint8_t *entry, float val) {
    uint32_t type = *(uint32_t *)(entry + TW_OFF_TYPE);
    void *vp = *(void **)(entry + TW_OFF_PTR);
    if (!vp) return;
    switch (type) {
        case TW_BOOL:
            *(uint8_t *)vp = val > 0.5f ? 1 : 0;
            *(uint8_t *)(entry + TW_OFF_VAL) = val > 0.5f ? 1 : 0;
            break;
        case TW_INT:
            *(int32_t *)vp = (int32_t)roundf(val);
            *(int32_t *)(entry + TW_OFF_VAL) = (int32_t)roundf(val);
            break;
        case TW_FLOAT:
            *(float *)vp = val;
            *(float *)(entry + TW_OFF_VAL) = val;
            break;
        case TW_DOUBLE:
            *(double *)vp = (double)val;
            *(double *)(entry + TW_OFF_VAL) = (double)val;
            break;
    }
}

static UIWindow *rr3KeyWindow(void) {
    for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) {
        if ([scene isKindOfClass:[UIWindowScene class]]) {
            for (UIWindow *w in ((UIWindowScene *)scene).windows) {
                if (w.isKeyWindow) return w;
            }
        }
    }
    return nil;
}

static void showToast(NSString *msg, BOOL ok) {
    dispatch_async(dispatch_get_main_queue(), ^{
        UIWindow *win = rr3KeyWindow();
        if (!win) return;
        UILabel *t = [[UILabel alloc] init];
        t.text = [NSString stringWithFormat:@"  %@  ", msg];
        t.textColor = ok ? [UIColor colorWithRed:0.75f green:1.0f blue:0.0f alpha:1.0f]
                         : [UIColor colorWithRed:1 green:0.4f blue:0.4f alpha:1];
        t.backgroundColor = [UIColor colorWithWhite:0.1f alpha:0.95f];
        t.font = [UIFont boldSystemFontOfSize:11];
        t.textAlignment = NSTextAlignmentCenter;
        t.layer.cornerRadius = 12;
        t.clipsToBounds = YES;
        [t sizeToFit];
        CGFloat w = t.frame.size.width + 24;
        if (w > win.bounds.size.width - 20) w = win.bounds.size.width - 20;
        t.frame = CGRectMake((win.bounds.size.width - w) / 2, -32, w, 26);
        [win addSubview:t];
        [UIView animateWithDuration:0.2 animations:^{
            t.frame = CGRectMake(t.frame.origin.x, 52, w, 26);
        } completion:^(BOOL done) {
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(1.3 * NSEC_PER_SEC)),
                dispatch_get_main_queue(), ^{
                [UIView animateWithDuration:0.25 animations:^{
                    t.alpha = 0;
                } completion:^(BOOL d) { [t removeFromSuperview]; }];
            });
        }];
    });
}

static BOOL writeTweakVerified(uint8_t *entry, float val) {
    writeTweak(entry, val);
    float rb = readTweakFloat(entry);
    uint32_t type = *(uint32_t *)(entry + TW_OFF_TYPE);
    if (type == TW_BOOL || type == TW_INT)
        return (int32_t)roundf(rb) == (int32_t)roundf(val);
    return fabsf(rb - val) < 0.01f;
}

static void tweakRange(uint8_t *entry, float *mn, float *mx) {
    uint32_t type = *(uint32_t *)(entry + TW_OFF_TYPE);
    if (type == TW_FLOAT) {
        *mn = *(float *)(entry + TW_OFF_MIN);
        *mx = *(float *)(entry + TW_OFF_MAX);
        if (*mn >= *mx || isnan(*mn) || isnan(*mx)) { *mn = -1; *mx = 1; }
    } else if (type == TW_INT) {
        int32_t imn = *(int32_t *)(entry + TW_OFF_MIN);
        int32_t imx = *(int32_t *)(entry + TW_OFF_MAX);
        if (imn <= -10000) imn = -100;
        if (imx >= 10000) imx = 100;
        if (imn >= imx) { imn = 0; imx = 100; }
        *mn = (float)imn; *mx = (float)imx;
    } else if (type == TW_DOUBLE) {
        double dmn = *(double *)(entry + TW_OFF_MIN);
        double dmx = *(double *)(entry + TW_OFF_MAX);
        if (dmn >= dmx || isnan(dmn) || isnan(dmx)) { dmn = -1; dmx = 1; }
        *mn = (float)dmn; *mx = (float)dmx;
    } else {
        *mn = 0; *mx = 1;
    }
}

static void buildTweakIndex(void) {
    uint8_t **bs = (uint8_t **)((uintptr_t)TWEAK_VEC_BASE + g_slide);
    uint8_t **es = (uint8_t **)((uintptr_t)TWEAK_VEC_END + g_slide);
    uint8_t *base = *bs, *end = *es;
    if (!base || !end || end <= base) {
        NSLog(@"[RR3] Tweak vector not ready (base=%p end=%p)", base, end);
        return;
    }
    g_tweakCount = (int)(end - base) / TWEAK_STRIDE;
    g_catEntries = [NSMutableDictionary dictionary];

    for (int i = 0; i < g_tweakCount; i++) {
        uint8_t *entry = base + i * TWEAK_STRIDE;
        NSString *name = readSSO(entry + TW_OFF_NAME);
        uint32_t type = *(uint32_t *)(entry + TW_OFF_TYPE);

        NSString *cat = @"OTHER";
        NSString *shortName = name;
        if ([name hasPrefix:@"TWEAKABLE_"]) {
            NSString *rest = [name substringFromIndex:10];
            NSRange r = [rest rangeOfString:@"_"];
            if (r.location != NSNotFound) {
                cat = [rest substringToIndex:r.location];
                shortName = [rest substringFromIndex:r.location + 1];
            } else {
                cat = rest; shortName = rest;
            }
        }

        NSString *fullKey = [NSString stringWithFormat:@"%@_%@", cat, shortName];
        NSString *desc = g_tweakDescs[fullKey];
        NSString *pretty = prettyName(shortName);

        NSDictionary *info = @{
            @"i": @(i), @"name": name, @"short": pretty,
            @"cat": cat, @"type": @(type),
            @"desc": desc ?: @"",
            @"entry": [NSValue valueWithPointer:entry],
        };
        NSMutableArray *arr = g_catEntries[cat];
        if (!arr) { arr = [NSMutableArray array]; g_catEntries[cat] = arr; }
        [arr addObject:info];
    }

    g_categories = [[g_catEntries allKeys]
        sortedArrayUsingSelector:@selector(compare:)].mutableCopy;
    NSLog(@"[RR3] Tweak index: %d entries, %lu categories",
        g_tweakCount, (unsigned long)g_categories.count);
}

static void dumpTweakables(void) {
    if (!g_catEntries) return;
    NSMutableString *log = [NSMutableString stringWithFormat:
        @"Tweakable Dump — %d entries, %lu categories\n\n",
        g_tweakCount, (unsigned long)g_categories.count];

    for (NSString *cat in g_categories) {
        NSArray *items = g_catEntries[cat];
        [log appendFormat:@"=== %@ (%d) ===\n", cat, (int)items.count];
        for (NSDictionary *info in items) {
            uint8_t *entry = (uint8_t *)[(NSValue *)info[@"entry"] pointerValue];
            uint32_t type = *(uint32_t *)(entry + TW_OFF_TYPE);
            float val = readTweakFloat(entry);
            void *vp = *(void **)(entry + TW_OFF_PTR);
            static const char *tn[] = {"str","int","bool","dbl","flt"};
            [log appendFormat:@"  %@ [%s] = %.4g (ptr=%p)\n",
                info[@"short"], type<=4 ? tn[type] : "?", val, vp];
        }
        [log appendString:@"\n"];
    }

    NSArray *paths = NSSearchPathForDirectoriesInDomains(
        NSDocumentDirectory, NSUserDomainMask, YES);
    NSString *fp = [[paths firstObject]
        stringByAppendingPathComponent:@"tweakable_dump.txt"];
    [log writeToFile:fp atomically:YES encoding:NSUTF8StringEncoding error:nil];
    NSLog(@"[RR3] Dump written to %@", fp);
}

#pragma mark - Colors

#define ACCENT [UIColor colorWithRed:0.75f green:1.0f blue:0.0f alpha:1.0f]
#define BG_DARK [UIColor colorWithWhite:0.08f alpha:0.95f]
#define BG_CELL [UIColor colorWithWhite:0.14f alpha:1.0f]
#define BG_ALT  [UIColor colorWithWhite:0.11f alpha:1.0f]
#define TXT_DIM [UIColor colorWithWhite:0.5f alpha:1.0f]

#pragma mark - Category Detail VC

@interface RR3CatDetail : UIViewController <UITableViewDelegate, UITableViewDataSource>
@property (nonatomic, strong) NSString *catKey;
@property (nonatomic, strong) NSArray *items;
@property (nonatomic, strong) UITableView *table;
@end

@implementation RR3CatDetail

- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = BG_DARK;
    _items = g_catEntries[_catKey] ?: @[];

    UIView *hdrBar = [[UIView alloc] init];
    hdrBar.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:hdrBar];

    UILabel *hdr = [[UILabel alloc] init];
    NSString *catLabel = g_catLabels[_catKey] ?: prettyName(_catKey);
    hdr.text = [NSString stringWithFormat:@"< %@ (%d)", catLabel, (int)_items.count];
    hdr.textColor = ACCENT;
    hdr.font = [UIFont boldSystemFontOfSize:16];
    hdr.translatesAutoresizingMaskIntoConstraints = NO;
    hdr.userInteractionEnabled = YES;
    [hdr addGestureRecognizer:[[UITapGestureRecognizer alloc]
        initWithTarget:self action:@selector(goBack)]];
    [hdrBar addSubview:hdr];

    UIButton *resetBtn = [UIButton buttonWithType:UIButtonTypeSystem];
    [resetBtn setTitle:@"RESET" forState:UIControlStateNormal];
    [resetBtn setTitleColor:[UIColor colorWithRed:1 green:0.4f blue:0.4f alpha:1]
        forState:UIControlStateNormal];
    resetBtn.titleLabel.font = [UIFont boldSystemFontOfSize:12];
    resetBtn.translatesAutoresizingMaskIntoConstraints = NO;
    [resetBtn addTarget:self action:@selector(resetAll)
        forControlEvents:UIControlEventTouchUpInside];
    [hdrBar addSubview:resetBtn];

    _table = [[UITableView alloc] initWithFrame:CGRectZero style:UITableViewStylePlain];
    _table.delegate = self;
    _table.dataSource = self;
    _table.backgroundColor = [UIColor clearColor];
    _table.separatorColor = [UIColor colorWithWhite:0.25f alpha:1.0f];
    _table.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:_table];

    UILongPressGestureRecognizer *lp = [[UILongPressGestureRecognizer alloc]
        initWithTarget:self action:@selector(longPressed:)];
    lp.minimumPressDuration = 0.5;
    [_table addGestureRecognizer:lp];

    [NSLayoutConstraint activateConstraints:@[
        [hdrBar.topAnchor constraintEqualToAnchor:self.view.topAnchor],
        [hdrBar.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor],
        [hdrBar.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor],
        [hdrBar.heightAnchor constraintEqualToConstant:40],
        [hdr.centerYAnchor constraintEqualToAnchor:hdrBar.centerYAnchor],
        [hdr.leadingAnchor constraintEqualToAnchor:hdrBar.leadingAnchor constant:14],
        [resetBtn.centerYAnchor constraintEqualToAnchor:hdrBar.centerYAnchor],
        [resetBtn.trailingAnchor constraintEqualToAnchor:hdrBar.trailingAnchor constant:-10],
        [_table.topAnchor constraintEqualToAnchor:hdrBar.bottomAnchor],
        [_table.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor],
        [_table.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor],
        [_table.bottomAnchor constraintEqualToAnchor:self.view.bottomAnchor],
    ]];
}

- (NSInteger)tableView:(UITableView *)tv numberOfRowsInSection:(NSInteger)s {
    return _items.count;
}

- (UITableViewCell *)tableView:(UITableView *)tv cellForRowAtIndexPath:(NSIndexPath *)ip {
    NSDictionary *info = _items[ip.row];
    uint8_t *entry = (uint8_t *)[(NSValue *)info[@"entry"] pointerValue];
    uint32_t type = [info[@"type"] unsignedIntValue];
    float val = readTweakFloat(entry);

    UITableViewCell *cell = [tv dequeueReusableCellWithIdentifier:@"tw"];
    if (!cell) {
        cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleSubtitle
            reuseIdentifier:@"tw"];
    }
    cell.backgroundColor = (ip.row % 2) ? BG_CELL : BG_ALT;
    cell.selectionStyle = UITableViewCellSelectionStyleNone;
    cell.textLabel.text = info[@"short"];
    cell.textLabel.textColor = [UIColor whiteColor];
    cell.textLabel.font = [UIFont systemFontOfSize:13];

    NSString *desc = info[@"desc"];
    BOOL hasDesc = desc && desc.length > 0;

    BOOL useToggle = (type == TW_BOOL) ||
        (type == TW_INT && isBoolLike(info[@"name"]));

    if (useToggle) {
        UISwitch *sw = [[UISwitch alloc] init];
        sw.onTintColor = ACCENT;
        sw.on = val > 0.5f;
        sw.transform = CGAffineTransformMakeScale(0.7f, 0.7f);
        sw.tag = ip.row;
        [sw addTarget:self action:@selector(boolToggled:)
            forControlEvents:UIControlEventValueChanged];
        cell.accessoryView = sw;
        if (hasDesc) {
            cell.detailTextLabel.text = desc;
            cell.detailTextLabel.textColor = TXT_DIM;
        } else {
            cell.detailTextLabel.text = val > 0.5f ? @"ON" : @"OFF";
            cell.detailTextLabel.textColor = val > 0.5f ? ACCENT : TXT_DIM;
        }
        cell.detailTextLabel.font = [UIFont systemFontOfSize:10];
    } else if (type == TW_STRING) {
        cell.accessoryView = nil;
        cell.detailTextLabel.text = hasDesc ? desc : @"(string)";
        cell.detailTextLabel.textColor = TXT_DIM;
        cell.detailTextLabel.font = [UIFont systemFontOfSize:10];
    } else {
        NSString *valStr;
        if (type == TW_INT)
            valStr = [NSString stringWithFormat:@"%d", (int)val];
        else
            valStr = [NSString stringWithFormat:@"%.4g", val];

        if (hasDesc)
            cell.detailTextLabel.text = [NSString stringWithFormat:@"%@ — %@",
                valStr, desc];
        else
            cell.detailTextLabel.text = valStr;
        cell.detailTextLabel.textColor = ACCENT;
        cell.detailTextLabel.font = [UIFont monospacedSystemFontOfSize:10
            weight:UIFontWeightRegular];

        float mn, mx;
        tweakRange(entry, &mn, &mx);
        UISlider *sl = [[UISlider alloc] initWithFrame:CGRectMake(0, 0, 110, 30)];
        sl.minimumValue = mn;
        sl.maximumValue = mx;
        sl.value = fminf(fmaxf(val, mn), mx);
        sl.minimumTrackTintColor = ACCENT;
        sl.tag = ip.row;
        [sl addTarget:self action:@selector(sliderChanged:)
            forControlEvents:UIControlEventValueChanged];
        [sl addTarget:self action:@selector(sliderFinished:)
            forControlEvents:UIControlEventTouchUpInside|UIControlEventTouchUpOutside];
        cell.accessoryView = sl;
    }
    return cell;
}

- (CGFloat)tableView:(UITableView *)tv heightForRowAtIndexPath:(NSIndexPath *)ip {
    return 52;
}

- (void)boolToggled:(UISwitch *)sw {
    if (sw.tag >= (NSInteger)_items.count) return;
    NSDictionary *info = _items[sw.tag];
    uint8_t *entry = (uint8_t *)[(NSValue *)info[@"entry"] pointerValue];
    BOOL ok = writeTweakVerified(entry, sw.on ? 1.0f : 0.0f);
    showToast([NSString stringWithFormat:@"%@ → %@%@",
        info[@"short"], sw.on ? @"ON" : @"OFF",
        ok ? @" ✓" : @" (unverified)"], ok);

    UIView *v = sw.superview;
    while (v && ![v isKindOfClass:[UITableViewCell class]]) v = v.superview;
    UITableViewCell *cell = (UITableViewCell *)v;
    if (cell) {
        NSString *desc = info[@"desc"];
        if (desc && desc.length > 0) {
            cell.detailTextLabel.text = desc;
            cell.detailTextLabel.textColor = TXT_DIM;
        } else {
            cell.detailTextLabel.text = sw.on ? @"ON" : @"OFF";
            cell.detailTextLabel.textColor = sw.on ? ACCENT : TXT_DIM;
        }
    }
}

- (void)sliderChanged:(UISlider *)sl {
    if (sl.tag >= (NSInteger)_items.count) return;
    NSDictionary *info = _items[sl.tag];
    uint8_t *entry = (uint8_t *)[(NSValue *)info[@"entry"] pointerValue];
    uint32_t type = [info[@"type"] unsignedIntValue];

    float val = sl.value;
    if (type == TW_INT) val = roundf(val);
    writeTweak(entry, val);

    UIView *v = sl.superview;
    while (v && ![v isKindOfClass:[UITableViewCell class]]) v = v.superview;
    UITableViewCell *cell = (UITableViewCell *)v;
    if (cell) {
        NSString *valStr;
        if (type == TW_INT)
            valStr = [NSString stringWithFormat:@"%d", (int)val];
        else
            valStr = [NSString stringWithFormat:@"%.4g", val];
        NSString *desc = info[@"desc"];
        if (desc && desc.length > 0)
            cell.detailTextLabel.text = [NSString stringWithFormat:@"%@ — %@",
                valStr, desc];
        else
            cell.detailTextLabel.text = valStr;
    }
}

- (void)sliderFinished:(UISlider *)sl {
    if (sl.tag >= (NSInteger)_items.count) return;
    NSDictionary *info = _items[sl.tag];
    uint8_t *entry = (uint8_t *)[(NSValue *)info[@"entry"] pointerValue];
    uint32_t type = [info[@"type"] unsignedIntValue];
    float val = sl.value;
    if (type == TW_INT) val = roundf(val);
    BOOL ok = writeTweakVerified(entry, val);
    NSString *valStr = (type == TW_INT) ?
        [NSString stringWithFormat:@"%d", (int)val] :
        [NSString stringWithFormat:@"%.4g", val];
    showToast([NSString stringWithFormat:@"%@ → %@%@",
        info[@"short"], valStr, ok ? @" ✓" : @" (unverified)"], ok);
}

- (void)resetAll {
    for (NSDictionary *info in _items) {
        uint8_t *entry = (uint8_t *)[(NSValue *)info[@"entry"] pointerValue];
        uint32_t type = [info[@"type"] unsignedIntValue];
        if (type == TW_STRING) continue;
        float def;
        switch (type) {
            case TW_BOOL:   def = (float)*(uint8_t *)(entry + TW_OFF_DEF); break;
            case TW_INT:    def = (float)*(int32_t *)(entry + TW_OFF_DEF); break;
            case TW_FLOAT:  def = *(float *)(entry + TW_OFF_DEF); break;
            case TW_DOUBLE: def = (float)*(double *)(entry + TW_OFF_DEF); break;
            default: continue;
        }
        writeTweak(entry, def);
    }
    [_table reloadData];
}

- (void)longPressed:(UILongPressGestureRecognizer *)gr {
    if (gr.state != UIGestureRecognizerStateBegan) return;
    CGPoint pt = [gr locationInView:_table];
    NSIndexPath *ip = [_table indexPathForRowAtPoint:pt];
    if (!ip || ip.row >= (NSInteger)_items.count) return;

    NSDictionary *info = _items[ip.row];
    uint8_t *entry = (uint8_t *)[(NSValue *)info[@"entry"] pointerValue];
    uint32_t type = [info[@"type"] unsignedIntValue];
    float val = readTweakFloat(entry);
    void *vp = *(void **)(entry + TW_OFF_PTR);

    static const char *tn[] = {"String","Int","Bool","Double","Float"};
    float mn = 0, mx = 0;
    tweakRange(entry, &mn, &mx);

    float def;
    switch (type) {
        case TW_BOOL:   def = (float)*(uint8_t *)(entry + TW_OFF_DEF); break;
        case TW_INT:    def = (float)*(int32_t *)(entry + TW_OFF_DEF); break;
        case TW_FLOAT:  def = *(float *)(entry + TW_OFF_DEF); break;
        case TW_DOUBLE: def = (float)*(double *)(entry + TW_OFF_DEF); break;
        default: def = 0;
    }

    NSString *desc = info[@"desc"];
    NSMutableString *msg = [NSMutableString string];
    if (desc.length > 0)
        [msg appendFormat:@"%@\n\n", desc];
    [msg appendFormat:@"Name: %@\n", info[@"name"]];
    [msg appendFormat:@"Type: %s\n", type <= 4 ? tn[type] : "?"];
    if (type == TW_INT)
        [msg appendFormat:@"Value: %d\nDefault: %d\nRange: %d – %d",
            (int)val, (int)def, (int)mn, (int)mx];
    else if (type == TW_BOOL)
        [msg appendFormat:@"Value: %@\nDefault: %@",
            val > 0.5f ? @"ON" : @"OFF", def > 0.5f ? @"ON" : @"OFF"];
    else
        [msg appendFormat:@"Value: %.4g\nDefault: %.4g\nRange: %.4g – %.4g",
            val, def, mn, mx];
    [msg appendFormat:@"\nPtr: %p", vp];

    UIAlertController *ac = [UIAlertController alertControllerWithTitle:info[@"short"]
        message:msg preferredStyle:UIAlertControllerStyleAlert];
    [ac addAction:[UIAlertAction actionWithTitle:@"OK"
        style:UIAlertActionStyleDefault handler:nil]];
    UIViewController *root = rr3KeyWindow().rootViewController;
    while (root.presentedViewController) root = root.presentedViewController;
    [root presentViewController:ac animated:YES completion:nil];
}

- (void)goBack {
    [UIView transitionWithView:self.view.superview duration:0.2
        options:UIViewAnimationOptionTransitionCrossDissolve animations:^{
        [self.view removeFromSuperview];
    } completion:nil];
    [self removeFromParentViewController];
}

@end

#pragma mark - Main Menu VC

@class RR3MainMenu;
static RR3MainMenu *g_mainMenu = nil;

@interface RR3MainMenu : UIViewController <UITableViewDelegate, UITableViewDataSource>
@property (nonatomic, strong) UITableView *table;
@end

@implementation RR3MainMenu

- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = BG_DARK;
    self.view.layer.cornerRadius = 16;
    self.view.clipsToBounds = YES;

    UIView *hdrBar = [[UIView alloc] init];
    hdrBar.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:hdrBar];

    UILabel *title = [[UILabel alloc] init];
    title.text = @"RR3 Debug";
    title.textColor = ACCENT;
    title.font = [UIFont boldSystemFontOfSize:18];
    title.translatesAutoresizingMaskIntoConstraints = NO;
    [hdrBar addSubview:title];

    UIButton *allOn = [UIButton buttonWithType:UIButtonTypeSystem];
    [allOn setTitle:@"ALL ON" forState:UIControlStateNormal];
    [allOn setTitleColor:[UIColor colorWithRed:0.3f green:0.9f blue:0.4f alpha:1]
        forState:UIControlStateNormal];
    allOn.titleLabel.font = [UIFont boldSystemFontOfSize:13];
    allOn.translatesAutoresizingMaskIntoConstraints = NO;
    [allOn addTarget:self action:@selector(allOn)
        forControlEvents:UIControlEventTouchUpInside];
    [hdrBar addSubview:allOn];

    UIButton *closeBtn = [UIButton buttonWithType:UIButtonTypeSystem];
    [closeBtn setTitle:@"X" forState:UIControlStateNormal];
    [closeBtn setTitleColor:[UIColor colorWithWhite:0.6f alpha:1]
        forState:UIControlStateNormal];
    closeBtn.titleLabel.font = [UIFont boldSystemFontOfSize:16];
    closeBtn.translatesAutoresizingMaskIntoConstraints = NO;
    [closeBtn addTarget:self action:@selector(closeTapped)
        forControlEvents:UIControlEventTouchUpInside];
    [hdrBar addSubview:closeBtn];

    _table = [[UITableView alloc] initWithFrame:CGRectZero style:UITableViewStylePlain];
    _table.delegate = self;
    _table.dataSource = self;
    _table.backgroundColor = [UIColor clearColor];
    _table.separatorColor = [UIColor colorWithWhite:0.25f alpha:1.0f];
    _table.translatesAutoresizingMaskIntoConstraints = NO;
    [_table registerClass:[UITableViewCell class] forCellReuseIdentifier:@"ct"];
    [self.view addSubview:_table];

    [NSLayoutConstraint activateConstraints:@[
        [hdrBar.topAnchor constraintEqualToAnchor:self.view.topAnchor],
        [hdrBar.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor],
        [hdrBar.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor],
        [hdrBar.heightAnchor constraintEqualToConstant:44],
        [title.centerYAnchor constraintEqualToAnchor:hdrBar.centerYAnchor],
        [title.leadingAnchor constraintEqualToAnchor:hdrBar.leadingAnchor constant:14],
        [allOn.centerYAnchor constraintEqualToAnchor:hdrBar.centerYAnchor],
        [allOn.centerXAnchor constraintEqualToAnchor:hdrBar.centerXAnchor],
        [closeBtn.centerYAnchor constraintEqualToAnchor:hdrBar.centerYAnchor],
        [closeBtn.trailingAnchor constraintEqualToAnchor:hdrBar.trailingAnchor constant:-10],
        [closeBtn.widthAnchor constraintEqualToConstant:30],
        [_table.topAnchor constraintEqualToAnchor:hdrBar.bottomAnchor],
        [_table.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor],
        [_table.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor],
        [_table.bottomAnchor constraintEqualToAnchor:self.view.bottomAnchor],
    ]];
}

- (NSInteger)numberOfSectionsInTableView:(UITableView *)tv { return 2; }

- (NSInteger)tableView:(UITableView *)tv numberOfRowsInSection:(NSInteger)s {
    if (s == 0) return NUM_FLAGS;
    return g_categories ? g_categories.count : 0;
}

- (NSString *)tableView:(UITableView *)tv titleForHeaderInSection:(NSInteger)s {
    if (s == 0) return @"Debug Flags";
    return [NSString stringWithFormat:@"Tweakables (%d)", g_tweakCount];
}

- (void)tableView:(UITableView *)tv willDisplayHeaderView:(UIView *)view
    forSection:(NSInteger)s {
    UITableViewHeaderFooterView *hdr = (UITableViewHeaderFooterView *)view;
    hdr.textLabel.textColor = ACCENT;
    hdr.textLabel.font = [UIFont boldSystemFontOfSize:13];
    hdr.contentView.backgroundColor = [UIColor colorWithWhite:0.06f alpha:1.0f];
}

- (UITableViewCell *)tableView:(UITableView *)tv cellForRowAtIndexPath:(NSIndexPath *)ip {
    if (ip.section == 0) {
        UITableViewCell *cell = [tv dequeueReusableCellWithIdentifier:@"fl"];
        if (!cell) {
            cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleSubtitle
                reuseIdentifier:@"fl"];
        }
        cell.backgroundColor = BG_CELL;
        cell.selectionStyle = UITableViewCellSelectionStyleNone;
        cell.textLabel.text = [NSString stringWithUTF8String:g_flags[ip.row].label];
        cell.textLabel.textColor = [UIColor whiteColor];
        cell.textLabel.font = [UIFont systemFontOfSize:14];
        cell.detailTextLabel.text = [NSString stringWithUTF8String:g_flags[ip.row].desc];
        cell.detailTextLabel.textColor = TXT_DIM;
        cell.detailTextLabel.font = [UIFont systemFontOfSize:9];
        cell.detailTextLabel.numberOfLines = 2;
        UISwitch *sw = [[UISwitch alloc] init];
        sw.tag = ip.row;
        sw.onTintColor = ACCENT;
        sw.on = (*flagPtr((int)ip.row) != 0);
        [sw addTarget:self action:@selector(flagToggled:)
            forControlEvents:UIControlEventValueChanged];
        cell.accessoryView = sw;
        return cell;
    }

    UITableViewCell *cell = [tv dequeueReusableCellWithIdentifier:@"ct"
        forIndexPath:ip];
    cell.backgroundColor = BG_CELL;
    cell.selectionStyle = UITableViewCellSelectionStyleDefault;
    NSString *cat = g_categories[ip.row];
    NSArray *items = g_catEntries[cat];
    NSString *label = g_catLabels[cat] ?: prettyName(cat);
    cell.textLabel.text = [NSString stringWithFormat:@"%@  (%d)",
        label, (int)items.count];
    cell.textLabel.textColor = [UIColor whiteColor];
    cell.textLabel.font = [UIFont systemFontOfSize:15];
    cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
    cell.accessoryView = nil;
    return cell;
}

- (CGFloat)tableView:(UITableView *)tv heightForRowAtIndexPath:(NSIndexPath *)ip {
    return ip.section == 0 ? 64 : 44;
}

- (void)tableView:(UITableView *)tv didSelectRowAtIndexPath:(NSIndexPath *)ip {
    [tv deselectRowAtIndexPath:ip animated:YES];
    if (ip.section == 0) {
        NSString *name = [NSString stringWithUTF8String:g_flags[ip.row].label];
        NSString *desc = [NSString stringWithUTF8String:g_flags[ip.row].desc];
        uint8_t val = *flagPtr((int)ip.row);
        NSString *msg = [NSString stringWithFormat:
            @"%@\n\nState: %@\nBSS address: 0x%llx",
            desc, val ? @"ON" : @"OFF", g_flags[ip.row].va];
        UIAlertController *ac = [UIAlertController alertControllerWithTitle:name
            message:msg preferredStyle:UIAlertControllerStyleAlert];
        [ac addAction:[UIAlertAction actionWithTitle:@"OK"
            style:UIAlertActionStyleDefault handler:nil]];
        UIViewController *root = rr3KeyWindow().rootViewController;
        while (root.presentedViewController) root = root.presentedViewController;
        [root presentViewController:ac animated:YES completion:nil];
        return;
    }
    if (ip.section == 1 && g_categories) {
        RR3CatDetail *detail = [[RR3CatDetail alloc] init];
        detail.catKey = g_categories[ip.row];
        detail.view.frame = self.view.bounds;
        [self addChildViewController:detail];
        [UIView transitionWithView:self.view duration:0.2
            options:UIViewAnimationOptionTransitionCrossDissolve animations:^{
            [self.view addSubview:detail.view];
        } completion:^(BOOL done) {
            [detail didMoveToParentViewController:self];
        }];
    }
}

- (void)flagToggled:(UISwitch *)sw {
    *flagPtr((int)sw.tag) = sw.on ? 1 : 0;
    uint8_t rb = *flagPtr((int)sw.tag);
    BOOL ok = (rb != 0) == sw.on;
    showToast([NSString stringWithFormat:@"%s → %@%@",
        g_flags[sw.tag].label, sw.on ? @"ON" : @"OFF",
        ok ? @" ✓" : @" (failed)"], ok);
}

- (void)allOn {
    for (int i = 0; i < NUM_FLAGS; i++) *flagPtr(i) = 1;
    [_table reloadSections:[NSIndexSet indexSetWithIndex:0]
        withRowAnimation:UITableViewRowAnimationNone];
}

- (void)closeTapped {
    [UIView animateWithDuration:0.2 animations:^{
        self.view.alpha = 0;
        self.view.transform = CGAffineTransformMakeScale(0.85f, 0.85f);
    } completion:^(BOOL done) {
        self.view.hidden = YES;
        self.view.transform = CGAffineTransformIdentity;
    }];
}

- (void)showMenu {
    self.view.hidden = NO;
    self.view.alpha = 0;
    self.view.transform = CGAffineTransformMakeScale(0.85f, 0.85f);
    [_table reloadData];
    [UIView animateWithDuration:0.2 animations:^{
        self.view.alpha = 1;
        self.view.transform = CGAffineTransformIdentity;
    }];
}

@end

#pragma mark - Floating Button

@interface RR3Btn : UIView
@property (nonatomic, strong) RR3MainMenu *menu;
@end

@implementation RR3Btn

- (instancetype)initWithFrame:(CGRect)frame {
    self = [super initWithFrame:frame];
    if (self) {
        self.backgroundColor = [UIColor colorWithWhite:0.15f alpha:0.9f];
        self.layer.cornerRadius = frame.size.width / 2;
        self.layer.borderColor = [ACCENT CGColor];
        self.layer.borderWidth = 2;
        self.layer.shadowColor = [UIColor blackColor].CGColor;
        self.layer.shadowOpacity = 0.5f;
        self.layer.shadowRadius = 4;
        self.layer.shadowOffset = CGSizeMake(0, 2);

        UILabel *lbl = [[UILabel alloc] initWithFrame:self.bounds];
        lbl.text = @"RR3";
        lbl.textColor = ACCENT;
        lbl.font = [UIFont boldSystemFontOfSize:12];
        lbl.textAlignment = NSTextAlignmentCenter;
        lbl.autoresizingMask = UIViewAutoresizingFlexibleWidth |
            UIViewAutoresizingFlexibleHeight;
        [self addSubview:lbl];

        [self addGestureRecognizer:[[UIPanGestureRecognizer alloc]
            initWithTarget:self action:@selector(drag:)]];
        [self addGestureRecognizer:[[UITapGestureRecognizer alloc]
            initWithTarget:self action:@selector(tap:)]];
    }
    return self;
}

- (void)drag:(UIPanGestureRecognizer *)pan {
    UIView *sv = self.superview;
    if (!sv) return;
    CGPoint t = [pan translationInView:sv];
    CGFloat nx = self.center.x + t.x;
    CGFloat ny = self.center.y + t.y;
    CGFloat r = self.bounds.size.width / 2;
    nx = MAX(r, MIN(sv.bounds.size.width - r, nx));
    ny = MAX(r, MIN(sv.bounds.size.height - r, ny));
    self.center = CGPointMake(nx, ny);
    [pan setTranslation:CGPointZero inView:sv];
}

- (void)tap:(UITapGestureRecognizer *)t {
    if (_menu.view.hidden) [_menu showMenu];
    else [_menu closeTapped];
}

@end

#pragma mark - Constructor

__attribute__((constructor))
static void rr3_overlay_init(void) {
    g_slide = _dyld_get_image_vmaddr_slide(0);
    initLabels();
    for (int i = 0; i < NUM_FLAGS; i++) *flagPtr(i) = 1;

    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(8.0 * NSEC_PER_SEC)),
                   dispatch_get_main_queue(), ^{
        buildTweakIndex();
        dumpTweakables();
        if (g_mainMenu) {
            [g_mainMenu.table reloadSections:[NSIndexSet indexSetWithIndex:1]
                withRowAnimation:UITableViewRowAnimationFade];
        }
    });

    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(3.0 * NSEC_PER_SEC)),
                   dispatch_get_main_queue(), ^{
        UIWindow *window = nil;
        for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) {
            if ([scene isKindOfClass:[UIWindowScene class]]) {
                UIWindowScene *ws = (UIWindowScene *)scene;
                for (UIWindow *w in ws.windows) {
                    if (w.isKeyWindow) { window = w; break; }
                }
                if (window) break;
            }
        }
        if (!window) window = UIApplication.sharedApplication.windows.firstObject;
        if (!window) return;

        CGFloat sw = window.bounds.size.width;
        CGFloat sh = window.bounds.size.height;

        RR3MainMenu *menu = [[RR3MainMenu alloc] init];
        g_mainMenu = menu;
        CGFloat pw = MIN(320, sw - 40);
        CGFloat ph = MIN(560, sh - 80);
        menu.view.frame = CGRectMake((sw - pw) / 2, (sh - ph) / 2, pw, ph);
        menu.view.hidden = YES;
        [window addSubview:menu.view];

        RR3Btn *btn = [[RR3Btn alloc]
            initWithFrame:CGRectMake(sw - 60, sh / 3, 44, 44)];
        btn.menu = menu;
        [window addSubview:btn];
    });
}
