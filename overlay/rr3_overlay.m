/*
 * rr3_overlay.m — Saturn-style debug overlay for Real Racing 3
 * Draggable floating button -> navigation menu with debug toggles
 *
 * Compile on SE (clang-16):
 *   /var/jb/usr/bin/clang-16 -arch arm64 -dynamiclib \
 *     -framework UIKit -framework Foundation \
 *     -isysroot /var/jb/usr/share/SDKs/iPhoneOS.sdk \
 *     -o rr3_overlay.dylib rr3_overlay.m \
 *     -install_name @rpath/rr3_overlay.dylib \
 *     -fobjc-arc -Os -miphoneos-version-min=15.0
 */

#import <UIKit/UIKit.h>
#import <mach-o/dyld.h>
#import <objc/runtime.h>

#pragma mark - Data

typedef struct {
    uint64_t va;
    const char *label;
} RR3Var;

static RR3Var g_flags[] = {
    {0x10324f910, "ImGui Overlay"},
    {0x10324f9d0, "Cheat Menu"},
    {0x10324f648, "Cheat Screen"},
    {0x10324f640, "Debug Render"},
    {0x10324f649, "Debug Flag 2"},
    {0x10324f9b0, "Debug Flag 3"},
    {0x10324f9f0, "Debug Flag 4"},
    {0x10324f9e0, "Debug Flag 5"},
};
#define NUM_FLAGS (sizeof(g_flags)/sizeof(g_flags[0]))

static intptr_t g_slide = 0;

static uint8_t *flagPtr(int idx) {
    return (uint8_t *)((uintptr_t)g_flags[idx].va + g_slide);
}

// Tweakable categories: name + item list (string arrays)
typedef struct {
    const char *category;
    const char **items;
    int count;
} RR3TweakCat;

static const char *cat_show[] = {
    "SHOW_FPS", "SHOW_CC_AND_EVENT_IDS", "SHOW_NDT_WORM",
    "HUD_SHOW_DEBUG", "HUD_SHOW_DEBUG_PLANE",
    "HUD_ENABLE_EXTERNAL_PLANE_OFFSETS",
};
static const char *cat_debugrender[] = {
    "DEBUGRENDER_ENABLED", "DEBUGRENDER_ACCFORCE_R4",
    "DEBUGRENDER_AI_SPLINE_LOOK_AHEAD_CAR", "DEBUGRENDER_BULLET",
    "DEBUGRENDER_BULLET_TRACK_COLLISION", "DEBUGRENDER_CAR_SHADOW",
    "DEBUGRENDER_CIRCUIT", "DEBUGRENDER_COLLISION",
    "DEBUGRENDER_CUBEMAP_PROBES", "DEBUGRENDER_ENABLED",
    "DEBUGRENDER_HOTSWAP", "DEBUGRENDER_INCAR",
    "DEBUGRENDER_METRICS", "DEBUGRENDER_NAVMESH",
    "DEBUGRENDER_PARTICLES", "DEBUGRENDER_PVS",
    "DEBUGRENDER_SKID_MARKS", "DEBUGRENDER_SPLINE_POINTS",
    "DEBUGRENDER_SUSPENSION", "DEBUGRENDER_TRACK_DIST",
    "DEBUGRENDER_TRIGGER_AREAS", "DEBUGRENDER_VISUAL_PROFILER",
};
static const char *cat_camera[] = {
    "CAMERA_BANKING_OFFSET", "CAMERA_CHASE_2",
    "CAMERA_FAR_CLIP_OFFSET", "CAMERA_MENU_SCENE_FREE_ORBIT",
    "CAMERA_NEAR_CLIP_OFFSET", "CAMERA_ONBOARD_PITCH",
    "CAMERA_ONBOARD_YAW", "CAMERA_PHOTO_MODE",
    "CAMERA_SHOW_CAR_SHADOW_BASE", "CAMERA_TRACK_FAR_CLIP",
    "CAMERA_TRACK_NEAR_CLIP", "CAMERA_Z_FAR",
    "CAMERA_Z_NEAR",
};
static const char *cat_render[] = {
    "RENDER_BEFORE_UPDATE", "RENDER_CARS", "RENDER_CAR_SHADOWS",
    "RENDER_CAR_SHADOWS_BATCH", "RENDER_COCKPIT",
    "RENDER_CUBEMAPS", "RENDER_DEBUG_INFO",
    "RENDER_ENABLED", "RENDER_ENV_MAP", "RENDER_FLAT_SHADOWS",
    "RENDER_FOG", "RENDER_GLOW", "RENDER_GPU_PROFILING",
    "RENDER_HDR", "RENDER_HUD", "RENDER_INVERTED",
    "RENDER_LENS_FLARE", "RENDER_LIGHT_BEAMS",
    "RENDER_MOTION_BLUR", "RENDER_PARTICLES",
    "RENDER_POST_PROCESS", "RENDER_REFLECTIONS",
    "RENDER_SHADOWS", "RENDER_SKID_MARKS",
    "RENDER_SKY", "RENDER_SSAO", "RENDER_TRACK",
    "RENDER_TRANSPARENT", "RENDER_WEATHER",
    "RENDER_WIREFRAME",
};
static const char *cat_car[] = {
    "CAR_ACC_PERCENT_GEAR_1", "CAR_ACC_PERCENT_GEAR_2",
    "CAR_ACC_PERCENT_GEAR_3", "CAR_ACC_PERCENT_GEAR_4",
    "CAR_ACC_PERCENT_GEAR_5", "CAR_ACC_PERCENT_GEAR_6",
    "CAR_BRAKE_PERCENT", "CAR_FORCE_ENGINE_SOUND_ID",
    "CAR_MAX_RPM", "CAR_MAX_SPEED_KPH",
    "CAR_OVERRIDE_ENABLED", "CAR_STEER_ANGLE",
    "CAR_TRACTION_CONTROL", "CAR_WEIGHT_KG",
};
static const char *cat_ai[] = {
    "AI_CAN_DRIVE", "AI_PLAYER_AI_SKILL_LEVEL",
    "AI_RECALC_OPPONENTS", "AI_1PT5_ERROR_RANGE",
    "AI_CREST_SPEED_LIMIT_R4", "AI_RUBBER_BANDING",
    "AI_STUCK_RESET_TIMER", "AI_USE_GHOST_MODE",
};
static const char *cat_input[] = {
    "INPUT_ACCEL_LOWER_DEADZONE_PERCENT",
    "INPUT_ACCEL_UPPER_DEADZONE_PERCENT",
    "INPUT_BRAKE_LOWER_DEADZONE_PERCENT",
    "INPUT_BRAKE_UPPER_DEADZONE_PERCENT",
    "INPUT_FORCE_CONTROLLER_TYPE",
    "INPUT_GYRO_STEER_SENSITIVITY",
    "INPUT_STEER_LINEARITY", "INPUT_STEER_SENSITIVITY",
    "INPUT_VIBRATION_ENABLED", "INPUT_VIBRATION_STRENGTH",
};
static const char *cat_photo[] = {
    "PHOTO_MODE_ENABLED",
};
static const char *cat_misc[] = {
    "ALLOW_ALPHA_TEST", "ALLOW_BLEND", "ALLOW_DEPTH_TEST",
    "ALLOW_STENCIL_TEST", "CUBEMAP_ENABLED",
    "DAMAGE_PLAYER_ENABLED", "DRIFT_ENABLED",
    "ENABLE_NASCAR_TUTORIAL", "HOTSWAP_ENABLE",
    "NETWORK_PROFILING_ON", "PARTY_PLAY",
    "PAUSE_BLUR", "PVS_DEBUG",
    "CUTSCENE_DISABLE_INTRO_OVERLAY",
    "FEAT_EVENT_DEBUG_INFO",
};

static RR3TweakCat g_cats[] = {
    {"Show / HUD",     cat_show,        sizeof(cat_show)/sizeof(cat_show[0])},
    {"Debug Render",   cat_debugrender,  sizeof(cat_debugrender)/sizeof(cat_debugrender[0])},
    {"Camera",         cat_camera,       sizeof(cat_camera)/sizeof(cat_camera[0])},
    {"Render",         cat_render,       sizeof(cat_render)/sizeof(cat_render[0])},
    {"Car Tuning",     cat_car,          sizeof(cat_car)/sizeof(cat_car[0])},
    {"AI",             cat_ai,           sizeof(cat_ai)/sizeof(cat_ai[0])},
    {"Input",          cat_input,        sizeof(cat_input)/sizeof(cat_input[0])},
    {"Photo",          cat_photo,        sizeof(cat_photo)/sizeof(cat_photo[0])},
    {"Misc Toggles",   cat_misc,         sizeof(cat_misc)/sizeof(cat_misc[0])},
};
#define NUM_CATS (sizeof(g_cats)/sizeof(g_cats[0]))

// Lime green accent (matches Limen's color)
#define ACCENT [UIColor colorWithRed:0.75f green:1.0f blue:0.0f alpha:1.0f]
#define BG_DARK [UIColor colorWithWhite:0.08f alpha:0.95f]
#define BG_CELL [UIColor colorWithWhite:0.14f alpha:1.0f]
#define TXT_DIM [UIColor colorWithWhite:0.5f alpha:1.0f]

#pragma mark - Category Detail VC

@interface RR3CatDetail : UIViewController <UITableViewDelegate, UITableViewDataSource>
@property (nonatomic, assign) int catIndex;
@property (nonatomic, strong) UITableView *table;
@end

@implementation RR3CatDetail

- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = BG_DARK;
    RR3TweakCat *cat = &g_cats[_catIndex];

    UILabel *hdr = [[UILabel alloc] init];
    hdr.text = [NSString stringWithFormat:@"< %s (%d)", cat->category, cat->count];
    hdr.textColor = ACCENT;
    hdr.font = [UIFont boldSystemFontOfSize:16];
    hdr.translatesAutoresizingMaskIntoConstraints = NO;
    hdr.userInteractionEnabled = YES;
    UITapGestureRecognizer *back = [[UITapGestureRecognizer alloc]
        initWithTarget:self action:@selector(goBack)];
    [hdr addGestureRecognizer:back];
    [self.view addSubview:hdr];

    _table = [[UITableView alloc] initWithFrame:CGRectZero style:UITableViewStylePlain];
    _table.delegate = self;
    _table.dataSource = self;
    _table.backgroundColor = [UIColor clearColor];
    _table.separatorColor = [UIColor colorWithWhite:0.25f alpha:1.0f];
    _table.translatesAutoresizingMaskIntoConstraints = NO;
    [_table registerClass:[UITableViewCell class] forCellReuseIdentifier:@"tw"];
    [self.view addSubview:_table];

    [NSLayoutConstraint activateConstraints:@[
        [hdr.topAnchor constraintEqualToAnchor:self.view.topAnchor constant:12],
        [hdr.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor constant:14],
        [hdr.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor constant:-14],
        [_table.topAnchor constraintEqualToAnchor:hdr.bottomAnchor constant:8],
        [_table.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor],
        [_table.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor],
        [_table.bottomAnchor constraintEqualToAnchor:self.view.bottomAnchor],
    ]];
}

- (NSInteger)tableView:(UITableView *)tv numberOfRowsInSection:(NSInteger)s {
    return g_cats[_catIndex].count;
}

- (UITableViewCell *)tableView:(UITableView *)tv cellForRowAtIndexPath:(NSIndexPath *)ip {
    UITableViewCell *cell = [tv dequeueReusableCellWithIdentifier:@"tw" forIndexPath:ip];
    cell.backgroundColor = (ip.row % 2 == 0) ? BG_CELL : [UIColor clearColor];
    cell.selectionStyle = UITableViewCellSelectionStyleNone;
    const char *item = g_cats[_catIndex].items[ip.row];
    cell.textLabel.text = [NSString stringWithUTF8String:item];
    cell.textLabel.textColor = [UIColor whiteColor];
    cell.textLabel.font = [UIFont systemFontOfSize:13];
    cell.textLabel.numberOfLines = 0;
    cell.accessoryView = nil;
    return cell;
}

- (CGFloat)tableView:(UITableView *)tv heightForRowAtIndexPath:(NSIndexPath *)ip {
    return 40;
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

@interface RR3MainMenu : UIViewController <UITableViewDelegate, UITableViewDataSource>
@property (nonatomic, strong) UITableView *table;
@end

@implementation RR3MainMenu

- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = BG_DARK;
    self.view.layer.cornerRadius = 16;
    self.view.clipsToBounds = YES;

    // Header bar
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
    [allOn setTitleColor:[UIColor colorWithRed:0.3f green:0.9f blue:0.4f alpha:1.0f] forState:UIControlStateNormal];
    allOn.titleLabel.font = [UIFont boldSystemFontOfSize:13];
    allOn.translatesAutoresizingMaskIntoConstraints = NO;
    [allOn addTarget:self action:@selector(allOn) forControlEvents:UIControlEventTouchUpInside];
    [hdrBar addSubview:allOn];

    UIButton *closeBtn = [UIButton buttonWithType:UIButtonTypeSystem];
    [closeBtn setTitle:@"X" forState:UIControlStateNormal];
    [closeBtn setTitleColor:[UIColor colorWithWhite:0.6f alpha:1.0f] forState:UIControlStateNormal];
    closeBtn.titleLabel.font = [UIFont boldSystemFontOfSize:16];
    closeBtn.translatesAutoresizingMaskIntoConstraints = NO;
    [closeBtn addTarget:self action:@selector(closeTapped) forControlEvents:UIControlEventTouchUpInside];
    [hdrBar addSubview:closeBtn];

    _table = [[UITableView alloc] initWithFrame:CGRectZero style:UITableViewStylePlain];
    _table.delegate = self;
    _table.dataSource = self;
    _table.backgroundColor = [UIColor clearColor];
    _table.separatorColor = [UIColor colorWithWhite:0.25f alpha:1.0f];
    _table.translatesAutoresizingMaskIntoConstraints = NO;
    [_table registerClass:[UITableViewCell class] forCellReuseIdentifier:@"fl"];
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

// Section 0 = Debug Flags (toggles), Section 1 = Tweakable Categories (nav)
- (NSInteger)numberOfSectionsInTableView:(UITableView *)tv { return 2; }

- (NSInteger)tableView:(UITableView *)tv numberOfRowsInSection:(NSInteger)s {
    return s == 0 ? NUM_FLAGS : NUM_CATS;
}

- (NSString *)tableView:(UITableView *)tv titleForHeaderInSection:(NSInteger)s {
    return s == 0 ? @"Debug Flags" : @"Tweakable Categories";
}

- (void)tableView:(UITableView *)tv willDisplayHeaderView:(UIView *)view forSection:(NSInteger)s {
    UITableViewHeaderFooterView *hdr = (UITableViewHeaderFooterView *)view;
    hdr.textLabel.textColor = ACCENT;
    hdr.textLabel.font = [UIFont boldSystemFontOfSize:13];
    hdr.contentView.backgroundColor = [UIColor colorWithWhite:0.06f alpha:1.0f];
}

- (UITableViewCell *)tableView:(UITableView *)tv cellForRowAtIndexPath:(NSIndexPath *)ip {
    if (ip.section == 0) {
        UITableViewCell *cell = [tv dequeueReusableCellWithIdentifier:@"fl" forIndexPath:ip];
        cell.backgroundColor = BG_CELL;
        cell.selectionStyle = UITableViewCellSelectionStyleNone;
        RR3Var *f = &g_flags[ip.row];
        cell.textLabel.text = [NSString stringWithUTF8String:f->label];
        cell.textLabel.textColor = [UIColor whiteColor];
        cell.textLabel.font = [UIFont systemFontOfSize:15];
        UISwitch *sw = [[UISwitch alloc] init];
        sw.tag = ip.row;
        sw.onTintColor = ACCENT;
        sw.on = (*flagPtr((int)ip.row) != 0);
        [sw addTarget:self action:@selector(flagToggled:) forControlEvents:UIControlEventValueChanged];
        cell.accessoryView = sw;
        return cell;
    } else {
        UITableViewCell *cell = [tv dequeueReusableCellWithIdentifier:@"ct" forIndexPath:ip];
        cell.backgroundColor = BG_CELL;
        cell.selectionStyle = UITableViewCellSelectionStyleDefault;
        RR3TweakCat *cat = &g_cats[ip.row];
        cell.textLabel.text = [NSString stringWithFormat:@"%s  (%d)",
            cat->category, cat->count];
        cell.textLabel.textColor = [UIColor whiteColor];
        cell.textLabel.font = [UIFont systemFontOfSize:15];
        cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
        cell.accessoryView = nil;
        return cell;
    }
}

- (CGFloat)tableView:(UITableView *)tv heightForRowAtIndexPath:(NSIndexPath *)ip {
    return ip.section == 0 ? 50 : 44;
}

- (void)tableView:(UITableView *)tv didSelectRowAtIndexPath:(NSIndexPath *)ip {
    [tv deselectRowAtIndexPath:ip animated:YES];
    if (ip.section == 1) {
        RR3CatDetail *detail = [[RR3CatDetail alloc] init];
        detail.catIndex = (int)ip.row;
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
    // Refresh flag states
    [_table reloadSections:[NSIndexSet indexSetWithIndex:0]
        withRowAnimation:UITableViewRowAnimationNone];
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
        lbl.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        [self addSubview:lbl];

        UIPanGestureRecognizer *pan = [[UIPanGestureRecognizer alloc]
            initWithTarget:self action:@selector(drag:)];
        [self addGestureRecognizer:pan];

        UITapGestureRecognizer *tap = [[UITapGestureRecognizer alloc]
            initWithTarget:self action:@selector(tap:)];
        [self addGestureRecognizer:tap];
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
    if (_menu.view.hidden) {
        [_menu showMenu];
    } else {
        [_menu closeTapped];
    }
}

@end

#pragma mark - Constructor

__attribute__((constructor))
static void rr3_overlay_init(void) {
    g_slide = _dyld_get_image_vmaddr_slide(0);

    // Set all debug flags immediately
    for (int i = 0; i < NUM_FLAGS; i++) *flagPtr(i) = 1;

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

        // Main menu panel
        RR3MainMenu *menu = [[RR3MainMenu alloc] init];
        CGFloat pw = MIN(300, sw - 40);
        CGFloat ph = MIN(500, sh - 80);
        menu.view.frame = CGRectMake((sw - pw) / 2, (sh - ph) / 2, pw, ph);
        menu.view.hidden = YES;
        [window addSubview:menu.view];

        // Floating button
        RR3Btn *btn = [[RR3Btn alloc] initWithFrame:CGRectMake(sw - 60, sh / 3, 44, 44)];
        btn.menu = menu;
        [window addSubview:btn];
    });
}
