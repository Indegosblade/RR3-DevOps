# All Runtime Tweakables and Research Flags

This reference is generated from the **887 authored description mappings** in `overlay/rr3_overlay.m`. It is the complete description dataset shipped with the RR3 DevOps harness, grouped by the category menu shown in the overlay.

A listed mapping is not a guarantee that the entry is registered or consumed in every game state. The tested final iOS runtime has exposed roughly 847 entries; some controls are conditional, scene-specific, unused in the final build, or overridden later by higher-priority game logic.

RR3 DevOps verifies the recovered data path by writing through the live pointer and reading that location back. This confirms registry wiring, not that every entry was individually behavior-tested or will create a visible effect in the current scene.

## Using descriptions in the overlay

Press and hold a slider or its list row for about half a second to open the short information panel. It shows the control description, raw runtime name, type, current value, launch snapshot, range, and live-pointer address.

## Debug Flags menu

These eight BSS flags are separate research controls in the overlay’s **Debug Flags** menu. They are not part of the 887 tweakable-description mappings. Their descriptions are research interpretations of surviving symbols and behavior, not a guarantee that an individual flag restores a complete original developer panel.

| Control | What it does |
|---|---|
| ImGui Overlay | Engine's ImGui debug UI renderer. Enables developer panels, perf graphs, memory stats. Touch input is NOT wired to ImGui — needs Bluetooth keyboard or controller to navigate menus. |
| Cheat Menu | Developer cheat system (MainMenuCheats). Contains: Unlock All Cars, Unlock All Tracks, Free Currency, Max Level, Skip Tutorial, Full Upgrade, Reset progress, Firebase debug. Displayed through ImGui panels. |
| Cheat Screen | Cheat screen display panel (MainMenuCheatScreen). Separate UI surface for cheat options. Requires ImGui to render. |
| Debug Render | Master debug visualization. Enables wireframe overlays, collision mesh display, physics debug (Bullet), AI path visualization, PVS boundaries, spline points. Most visual of all debug flags — look for colored wireframes on track and cars. |
| Cheat Flag B | Secondary cheat subsystem flag (1 byte after Cheat Screen in BSS). Likely enables a sub-feature of the cheat system. Toggle and observe. |
| Profiler Gate | Debug subsystem flag in the ImGui/Cheat BSS region. May gate ProfilingHarness and performance measurement code paths. Toggle and check for profiling overlays. |
| Debug System A | Debug subsystem flag. Purpose not fully identified from binary — toggle during gameplay and observe for visual or behavioral changes. |
| Debug System B | Debug subsystem flag. Purpose not fully identified from binary — toggle during gameplay and observe for visual or behavioral changes. |

## AI Opponents menu (`AI`)

| Runtime control | What it does |
|---|---|
| `AI_1PT5_ERROR_RANGE` | AI driving mistakes. ← robotic precision → more swerving and braking errors. |
| `AI_CAN_DRIVE` | ON = AI opponents drive normally. OFF = AI cars sit still on the grid. |
| `AI_CREST_SPEED_LIMIT_R4` | AI speed over hills. ← crawls over crests → sends it full speed. |
| `AI_PLAYER_AI_SKILL_LEVEL` | How good the AI drives. ← braindead opponents → near-perfect drivers. |
| `AI_RECALC_OPPONENTS` | ON = regenerate the AI lineup. OFF = keep current opponents. |
| `AI_RUBBER_BANDING` | ON = AI speeds up when you're ahead (catch-up). OFF = honest racing. |
| `AI_SKILL_ARRANGEMENT` | How AI skill is distributed across the grid. Changes opponent spread. |
| `AI_SLOW_DOWN` | ON = AI cars slow down near you. OFF = AI drives at full pace. |
| `AI_SPEED_LIMIT` | Maximum AI speed. ← slower AI cap → faster AI cap. |
| `AI_SPEED_LIMITER_ENABLED` | ON = AI speed cap active. OFF = AI drives unrestricted. |
| `AI_STUCK_RESET_TIMER` | How long before a stuck AI gets teleported back on track. ← instant reset → long wait. |
| `AI_USE_GHOST_MODE` | ON = AI cars clip through each other (no AI-AI crashes). OFF = they collide. |

## Render Pipeline menu (`ALLOW`)

| Runtime control | What it does |
|---|---|
| `ALLOW_ALPHA_TEST` | ON = alpha-tested materials render (fences, foliage, trees). OFF = invisible. |
| `ALLOW_ALPHA_TO_COVERAGE` | ON = anti-aliased alpha edges (smoother trees/fences). OFF = hard edges. |
| `ALLOW_BLEND` | ON = transparent/blended materials render (glass, particles). OFF = invisible. |
| `ALLOW_DEPTH_TEST` | ON = depth testing active (proper occlusion). OFF = Z-fighting chaos. |
| `ALLOW_DEPTH_WRITE_DISABLE` | ON = allows depth write disabling for special effects. OFF = always writes depth. |
| `ALLOW_FOG` | ON = fog renders. OFF = no distance fog anywhere. |
| `ALLOW_LIGHTING` | ON = lighting calculations active. OFF = everything unlit (flat colors). |
| `ALLOW_STENCIL_TEST` | ON = stencil buffer active (shadows, mirrors, masks). OFF = broken shadows. |

## ALT menu (`ALT`)

| Runtime control | What it does |
|---|---|
| `ALT_RENDER_ORDER` | ON = alternate draw order for render passes. OFF = default order. |

## Antialised menu (`ANTIALISED`)

| Runtime control | What it does |
|---|---|
| `ANTIALISED_LINES_ENABLE` | ON = anti-aliased debug lines. OFF = jagged debug lines. |
| `ANTIALISED_LINES_RADIUS` | Debug line thickness. ← thin lines → thick lines. |

## Bullet menu (`BULLET`)

| Runtime control | What it does |
|---|---|
| `BULLET_PROP_CULLING` | ON = cull physics props beyond distance. OFF = simulate all props. |
| `BULLET_PROP_CULL_DIST` | Physics prop culling distance. ← cull close → simulate further out. |
| `BULLET_PROP_CULL_MARGIN` | Physics culling buffer zone. ← tight margin → wide margin. |
| `BULLET_PROP_STATS` | ON = show physics prop statistics overlay. OFF = hidden. |

## Camera menu (`CAMERA`)

| Runtime control | What it does |
|---|---|
| `CAMERA_BANKING_OFFSET` | Camera tilt into corners. ← no lean → heavy lean into turns. |
| `CAMERA_CHASE_2` | ON = alternate chase camera (wider, different follow). OFF = default chase. |
| `CAMERA_FAR_CLIP_OFFSET` | Adjusts far draw distance. ← less visibility → more visibility. |
| `CAMERA_FOV` | Field of view. ← narrow/zoomed in → wide-angle/fish-eye. |
| `CAMERA_MENU_SCENE_FREE_ORBIT` | ON = freely orbit car in menus. OFF = fixed menu camera angles. |
| `CAMERA_NEAR_CLIP_OFFSET` | Adjusts near clip. ← clips more → clips less. |
| `CAMERA_ONBOARD_PITCH` | Cockpit view tilt. ← look down at dash → look up at sky. |
| `CAMERA_ONBOARD_YAW` | Cockpit view rotation. ← look left → look right. |
| `CAMERA_ORBIT_CAM_COLLIDES` | ON = orbit camera collides with geometry. OFF = clips through walls. |
| `CAMERA_ORBIT_CAM_FOV` | Orbit camera field of view. ← narrow/zoomed → wide angle. |
| `CAMERA_ORBIT_MODE` | ON = orbit camera mode active. OFF = default camera. |
| `CAMERA_PHOTO_MODE` | ON = free-roam camera for screenshots. OFF = normal chase cam. |
| `CAMERA_POSITION_X` | Camera X position offset. ← move left → move right. |
| `CAMERA_POSITION_Y` | Camera Y position offset. ← move down → move up. |
| `CAMERA_POSITION_Z` | Camera Z position offset. ← move back → move forward. |
| `CAMERA_ROTATION_X` | Camera pitch rotation. ← tilt down → tilt up. |
| `CAMERA_ROTATION_Y` | Camera yaw rotation. ← rotate left → rotate right. |
| `CAMERA_ROTATION_Z` | Camera roll rotation. ← roll left → roll right. |
| `CAMERA_SHOW_CAR_SHADOW_BASE` | ON = shows the shadow anchor point under the car. Debug visual. |
| `CAMERA_TRACK_FAR_CLIP` | Track geometry draw distance. ← track pops in close → full track visible. |
| `CAMERA_TRACK_NEAR_CLIP` | Track near clip. ← see road right under you → clips near geometry. |
| `CAMERA_ZOOM_END` | End zoom distance. ← closer end zoom → further end zoom. |
| `CAMERA_ZOOM_END_FOV` | FOV at end of zoom. ← narrow → wide. |
| `CAMERA_ZOOM_END_OFFSET` | Camera offset at end of zoom. ← close → far. |
| `CAMERA_ZOOM_START` | Start zoom distance. ← closer start → further start. |
| `CAMERA_ZOOM_START_FOV` | FOV at start of zoom. ← narrow → wide. |
| `CAMERA_ZOOM_START_OFFSET` | Camera offset at start of zoom. ← close → far. |
| `CAMERA_Z_FAR` | How far you can see. ← objects pop in close → see the whole track ahead. |
| `CAMERA_Z_NEAR` | Near clip plane. ← see things very close to camera → clips nearby objects. |

## Car Tuning menu (`CAR`)

| Runtime control | What it does |
|---|---|
| `CAR_ACC_PERCENT_GEAR_1` | 1st gear throttle. ← sluggish launch → rocket launch off the line. |
| `CAR_ACC_PERCENT_GEAR_2` | 2nd gear throttle. ← weak mid-range → strong pull through 2nd. |
| `CAR_ACC_PERCENT_GEAR_3` | 3rd gear throttle. ← weak mid-range → strong pull through 3rd. |
| `CAR_ACC_PERCENT_GEAR_4` | 4th gear throttle. ← weak high speed → strong pull through 4th. |
| `CAR_ACC_PERCENT_GEAR_5` | 5th gear throttle. ← weak top speed → strong pull in 5th. |
| `CAR_BANKING_PERCENTAGE` | Car body banking in turns. ← no lean → heavy body roll. |
| `CAR_BRAKE_LOOK_AHEAD_MULT` | AI/assist brake look-ahead. ← brakes late → brakes early. |
| `CAR_BRAKE_PERCENT` | Brake force multiplier. ← weak brakes (long stops) → strong brakes (instant lock-up). |
| `CAR_BRAKE_POWER` | Brake force. ← weak brakes (long stops) → strong brakes (instant lock-up). |
| `CAR_BRAKE_SENSITIVITY` | Brake input sensitivity. ← needs hard press → light tap = full brakes. |
| `CAR_DEGRADATION_BRAKES_MAX_STOPPING_DIST_GAIN` | Max extra stopping distance from worn brakes. ← small penalty → huge penalty. |
| `CAR_DEGRADATION_BRAKES_REGEN_RATE` | How fast brakes recover. ← slow regen → fast regen. |
| `CAR_DEGRADATION_BRAKES_WEAR_RATE` | How fast brakes wear out. ← slow wear → fast wear. |
| `CAR_DEGRADATION_BRAKES_WEAR_SPEED_MPH_MAX` | Top speed for brake wear. Braking above this = max wear rate. |
| `CAR_DEGRADATION_BRAKES_WEAR_SPEED_MPH_MIN` | Min speed for brake wear. Braking below this = no wear. |
| `CAR_DEGRADATION_BRAKES_WEAR_SPEED_MULTIPLIER` | Speed-based brake wear scaling. ← speed barely matters → speed = major wear factor. |
| `CAR_DEGRADATION_INVERSE_TYRE_IDLE_WEAR_RATE` | Tire idle wear (inverse — higher = slower wear). ← tires degrade standing still → no idle wear. |
| `CAR_DEGRADATION_INVERSE_TYRE_OFFROAD_WEAR_RATE` | Tire offroad wear (inverse — higher = slower). ← shreds tires offroad → durable offroad. |
| `CAR_DEGRADATION_INVERSE_TYRE_REGEN_RATE` | Tire recovery rate (inverse — higher = slower regen). ← fast tire recovery → slow recovery. |
| `CAR_DEGRADATION_INVERSE_TYRE_SKID_MULTIPLIER` | Tire skid wear (inverse — higher = less skid wear). ← skidding shreds tires → skidding is gentle. |
| `CAR_DEGRADATION_OVERRIDE` | ON = use custom degradation values below. OFF = use default wear rates. |
| `CAR_DEGRADATION_TYRE_MAX_GRIP_LOSS` | Max grip loss from tire wear. ← small penalty → huge grip loss when worn. |
| `CAR_DEGRADATION_TYRE_WEAR_OFFROAD_MULTIPLIER` | Offroad tire wear multiplier. ← gentle offroad → destroys tires offroad. |
| `CAR_DEGRADATION_TYRE_WEAR_RATE` | Tire wear speed. ← tires last forever → tires wear fast. |
| `CAR_DEGRADATION_TYRE_WEAR_SKID_MULTIPLIER` | Skid tire wear multiplier. ← gentle skid wear → shreds tires when sliding. |
| `CAR_DIRT_MASK_OVERRIDE` | ON = override dirt texture on car body. OFF = default dirt build-up. |
| `CAR_DOWNFORCE_BOOST_MAX` | Max downforce boost. ← small aero effect → massive downforce at speed. |
| `CAR_DOWNFORCE_BOOST_MIN` | Min downforce boost. ← no low-speed downforce → some even at low speed. |
| `CAR_DOWNFORCE_DECELERATION_FACTOR` | How fast downforce drops when slowing. ← instant drop → gradual fade. |
| `CAR_DOWNFORCE_OVERRIDE` | ON = use custom downforce values. OFF = default aero profile. |
| `CAR_DOWNFORCE_SPEED_THRESHOLD_MAX` | Speed for max downforce. ← full effect at low speed → needs high speed. |
| `CAR_DOWNFORCE_SPEED_THRESHOLD_MIN` | Speed where downforce starts. ← starts immediately → needs speed to activate. |
| `CAR_DRAW_RENDERING_INFO` | ON = show car rendering debug info. OFF = hidden. |
| `CAR_ENABLE_EXPERIMENTAL_DOWNFORCE` | ON = experimental downforce model. OFF = standard aero. |
| `CAR_ERS_ACC_MULTIPLIER` | ERS acceleration boost. ← weak boost → strong acceleration when ERS active. |
| `CAR_ERS_BRAKING_CHARGE_RATE` | ERS charge from braking. ← slow charge → fast charge under braking. |
| `CAR_ERS_BRAKING_CHARGE_SPEED_THRESHOLD` | Min speed for ERS brake charging. ← charges at any speed → needs high speed. |
| `CAR_ERS_CHARGE_DRAIN_RATE` | ERS battery drain when deployed. ← lasts long → drains fast. |
| `CAR_ERS_ENABLED` | ON = Energy Recovery System active (hybrid power boost). OFF = no ERS. |
| `CAR_ERS_EXHAUST_CHARGE_RATE` | ERS charge from exhaust heat. ← slow charge → fast passive charge. |
| `CAR_ERS_EXHAUST_CHARGE_RPM_THRESHOLD` | Min RPM for exhaust ERS charging. ← charges at low RPM → needs high revs. |
| `CAR_ERS_MIN_CHARGE_TO_ACTIVATE` | Min ERS charge to deploy. ← deploys with tiny charge → needs significant charge. |
| `CAR_FORCE_ENGINE_SOUND_ID` | Force a different engine sound. Changes exhaust note to another car's. |
| `CAR_GRAVITY` | Gravity strength on car. ← light gravity (moon driving) → heavy gravity (planted). |
| `CAR_HDL_PERCENT` | Handling percentage. ← loose/slippery → tight/responsive. |
| `CAR_LOD_ENABLE_OCCLUSION` | ON = cull car parts hidden by other geometry. OFF = draw everything. |
| `CAR_LOD_FORCE_CAR_LEVEL` | Force car LOD level. Higher = lower detail model. |
| `CAR_LOD_FORCE_DRIVER_LEVEL` | Force driver model LOD. Higher = less driver detail. |
| `CAR_LOD_FORCE_MIPMAP_LEVEL` | Force car texture mipmap. Higher = blurrier textures. |
| `CAR_LOD_FORCE_WHEEL_LEVEL` | Force wheel model LOD. Higher = less wheel detail. |
| `CAR_LOD_FREEZE` | ON = freeze car LOD at current level (won't change with distance). OFF = normal LOD. |
| `CAR_LOD_SHOW_LOD_COVERAGE` | ON = show LOD coverage debug overlay. OFF = hidden. |
| `CAR_LOD_SHOW_LOD_NAME` | ON = show LOD level name on cars. OFF = hidden. |
| `CAR_MAX_RPM` | Rev limiter. ← engine cuts early (slow) → revs higher (more top-end power). |
| `CAR_MAX_SPEED_KPH` | Car top speed. ← slower → faster. Crank right for absurd straights. |
| `CAR_OVERRIDE_ENABLED` | ON = car tuning sliders below take effect. OFF = stock car stats. |
| `CAR_PHYSICALLY_BASED_DRIVING` | ON = physics-based driving model. OFF = arcade driving model. |
| `CAR_SHADOW_ANIMATED` | ON = car shadow animates with suspension. OFF = static shadow. |
| `CAR_SHOW_DEBUG_TELEMETRY` | ON = show speed/RPM/gear telemetry overlay. OFF = hidden. |
| `CAR_SLIDE_OUT_PLAYER` | ON = player car slides out (snap oversteer). OFF = stable rear end. |
| `CAR_SLIPSTREAMING` | ON = drafting/slipstream effect active. OFF = no slipstream. |
| `CAR_SLIPSTREAMING_ACCELERATION_CHANGE` | Speed boost when drafting. ← small boost → big acceleration in slipstream. |
| `CAR_SLIPSTREAMING_AI_BETTERSLIPDISTANCE` | AI drafting detection range. ← short range → AI drafts from further back. |
| `CAR_SLIPSTREAMING_AI_FOLLOWWIDTH` | AI drafting follow width. ← tight behind → wider drafting zone. |
| `CAR_SLIPSTREAMING_AI_OVERTAKEDISTANCE` | Distance AI uses slipstream to overtake. ← close only → starts overtake from far. |
| `CAR_SLIPSTREAMING_ALL_MODES` | ON = slipstream in all race modes. OFF = only in certain modes. |
| `CAR_SLIPSTREAMING_CAMERA_DISTANCE_DELAY` | Camera pull-back delay in slipstream. ← instant → gradual. |
| `CAR_SLIPSTREAMING_CAMERA_DISTANCE_MULTIPLIER` | Camera pull-back amount in slipstream. ← subtle → dramatic zoom out. |
| `CAR_SLIPSTREAMING_CAMERA_FOV_DELAY` | FOV change delay in slipstream. ← instant → gradual. |
| `CAR_SLIPSTREAMING_CAMERA_FOV_MULTIPLIER` | FOV widening in slipstream. ← subtle → dramatic fish-eye effect. |
| `CAR_SLIPSTREAMING_EFFECT_LENGTH` | Slipstream cone length behind car. ← short draft zone → long draft zone. |
| `CAR_SLIPSTREAMING_EFFECT_WIDTH` | Slipstream cone width. ← narrow (must be directly behind) → wide draft zone. |
| `CAR_SLIPSTREAMING_MINIMUM_SPEED` | Min speed for slipstream to activate. ← drafts at low speed → needs high speed. |
| `CAR_SLIP_BURNOUT` | Slip angle for burnout. ← easy burnouts → needs extreme wheel spin. |
| `CAR_SLIP_FORCE_GRASS` | Tire slip force on grass. ← no grass grip → some grass traction. |
| `CAR_SLIP_FORCE_GRAVEL` | Tire slip force on gravel. ← no gravel grip → some gravel traction. |
| `CAR_SLIP_FORCE_TRACK` | Tire slip force on track. ← no track grip → maximum track traction. |
| `CAR_SLIP_NORMAL` | Normal tire slip threshold. ← slides easily → high grip before sliding. |
| `CAR_SPD_PERCENT` | Speed percentage override. ← slower than stock → faster than stock. |
| `CAR_STATS` | ON = show car stats debug info. OFF = hidden. |
| `CAR_STATS_ACCELERATION` | Acceleration stat override. ← sluggish → rocket acceleration. |
| `CAR_STATS_BRAKE_POWER` | Brake power stat. ← weak brakes → monster brakes. |
| `CAR_STATS_DRIVE` | Drive type override (FWD/RWD/AWD). Changes power delivery. |
| `CAR_STATS_ENGINE_MOUNT` | Engine mount position. Changes weight distribution. |
| `CAR_STATS_HANDLING` | Handling stat override. ← loose → sharp handling. |
| `CAR_STATS_KEEP_CAR_UPGRADED_TO_MATCH_RECOMMENDED_PR` | ON = auto-match car PR to event recommendation. OFF = use actual upgrades. |
| `CAR_STATS_OVERSTEER` | Oversteer tendency. ← understeers (pushes wide) → oversteers (rear slides out). |
| `CAR_STATS_OVERSTEER_BRAKING` | Oversteer under braking. ← stable braking → rear swings out under brakes. |
| `CAR_STATS_OVERSTEER_BRAKING_OVERRIDE` | ON = use custom braking oversteer. OFF = default. |
| `CAR_STATS_OVERSTEER_OVERRIDE` | ON = use custom oversteer value. OFF = default. |
| `CAR_STATS_SIDE_FORCE` | Lateral grip force. ← slides easily in corners → massive cornering grip. |
| `CAR_STATS_SIDE_FORCE_OVERRIDE` | ON = use custom side force. OFF = default. |
| `CAR_STATS_TOP_SPEED` | Top speed stat override. ← slow top end → blistering top speed. |
| `CAR_STATS_UNDERSTEER_MAX_FACTOR` | Max understeer at high speed. ← precise at speed → pushes wide at speed. |
| `CAR_STATS_UNDERSTEER_MAX_SPEED` | Speed where max understeer kicks in. ← understeer at low speed → only at high speed. |
| `CAR_STATS_UNDERSTEER_MIN_FACTOR` | Min understeer at low speed. ← no low-speed push → some push even slow. |
| `CAR_STATS_UNDERSTEER_MIN_SPEED` | Speed where understeer begins. ← starts immediately → only above this speed. |
| `CAR_STEERING_JITTER_ENABLED` | ON = steering wheel jitter effect (vibration). OFF = smooth steering. |
| `CAR_STEERING_JITTER_MAX_INTENSITY` | Max steering jitter. ← barely noticeable → violent shaking. |
| `CAR_STEERING_JITTER_RANDOM_TIME` | Jitter timing randomness. ← steady jitter → random bursts. |
| `CAR_STEERING_JITTER_RANDOM_TOLERANCE` | Jitter timing tolerance. ← precise timing → variable timing. |
| `CAR_STEERING_SENSITIVITY` | How fast the car responds to steering input. ← sluggish → twitchy. |
| `CAR_STEER_ANGLE` | Max wheel turn. ← tiny turns (highway feel) → sharp turns (go-kart feel). |
| `CAR_TRACTION_CONTROL` | Traction limit. ← no TC (wheelspin, drifty) → max TC (no slip at all). |
| `CAR_TURN_ANGLE_ACTUAL_SPEED_BIAS` | Speed influence on turn angle. ← speed doesn't affect steering → heavy speed reduction. |
| `CAR_TURN_ANGLE_TOP_SPEED_BIAS` | Top speed turn angle reduction. ← full steering at top speed → restricted at speed. |
| `CAR_WEIGHT_KG` | Car mass. ← lighter (floaty, fast accel) → heavier (planted, slow accel). |
| `CAR_WHEEL_BLUR_ENABLED` | ON = wheels blur at speed (motion blur on rims). OFF = wheels always sharp. |

## Carsfx menu (`CARSFX`)

| Runtime control | What it does |
|---|---|
| `CARSFX_LONG_SLIP_ANGLE_FOR_BURNOUT` | Slip angle to trigger burnout smoke. ← triggers easily → needs big slides. |
| `CARSFX_MPH_FOR_PUDDLE_SPLASH` | Speed for puddle splash effect. ← splashes at low speed → needs high speed. |
| `CARSFX_MPH_FOR_WATER_RIPPLE` | Speed for water ripple effect. ← ripples at low speed → needs high speed. |
| `CARSFX_SLIP_ANGLE_FOR_SLIDE` | Slip angle to trigger tire slide FX. ← triggers easily → needs big angle. |
| `CARSFX_UNDERBODY_SCRAPE` | ON = underbody scrape sparks effect. OFF = no scrape FX. |
| `CARSFX_UNDERBODY_SCRAPE_TEST` | ON = test mode for underbody scrape (always active). OFF = normal trigger. |

## Collision menu (`COLLISION`)

| Runtime control | What it does |
|---|---|
| `COLLISION_CAR_VS_CAR_R3` | Car-to-car collision force. ← soft bumps → violent crashes. |
| `COLLISION_CAR_VS_WALLS_R3` | Car-to-wall collision force. ← soft wall hits → violent wall impacts. |

## Cubemap menu (`CUBEMAP`)

| Runtime control | What it does |
|---|---|
| `CUBEMAP_DIMENSIONS` | Cubemap resolution. ← low-res reflections → high-res reflections (slower). |
| `CUBEMAP_ENABLED` | ON = real-time cubemap reflections. OFF = no environment reflections. |
| `CUBEMAP_ENABLE_DYNAMIC_BLUR` | ON = blur cubemap reflections dynamically. OFF = sharp reflections. |
| `CUBEMAP_FOLLOW_FREE_CAM` | ON = cubemap follows free camera. OFF = stays at car position. |
| `CUBEMAP_FOR_ALL_CARS` | ON = every car gets cubemap reflections. OFF = only player car. |
| `CUBEMAP_MIPMAP_ENABLED` | ON = mipmapped cubemaps (smooth distant reflections). OFF = sharp at all distances. |
| `CUBEMAP_PIXEL_THRESHOLD_OVERRIDE` | Cubemap pixel quality threshold. ← lower quality → higher quality. |
| `CUBEMAP_RENDER_CARS_IN_CUBEMAPS` | ON = cars appear in reflections. OFF = no car reflections. |
| `CUBEMAP_RENDER_CORONAS_IN_CUBEMAPS` | ON = light coronas in reflections. OFF = no corona reflections. |
| `CUBEMAP_RENDER_ENTIRE_TRACK_INTO_REFLECTIONS` | ON = full track in reflections. OFF = simplified track reflections. |
| `CUBEMAP_RENDER_PARTICLES_IN_CUBEMAPS` | ON = particles in reflections. OFF = no particle reflections. |

## Customisation menu (`CUSTOMISATION`)

| Runtime control | What it does |
|---|---|
| `CUSTOMISATION_FRONT_RIDE_HEIGHT` | Front ride height. ← slammed low → raised high. |
| `CUSTOMISATION_PAINT_SCREEN_USES_GARAGE` | ON = paint screen uses garage background. OFF = default background. |
| `CUSTOMISATION_REAR_RIDE_HEIGHT` | Rear ride height. ← slammed low → raised high. |
| `CUSTOMISATION_TYRE_COLOUR_B` | Tire blue channel. ← no blue → full blue. Combine R/G/B for any color. |
| `CUSTOMISATION_TYRE_COLOUR_G` | Tire green channel. ← no green → full green. Combine R/G/B for any color. |
| `CUSTOMISATION_TYRE_COLOUR_PREVIEW` | ON = preview tire color changes live. OFF = apply on exit. |
| `CUSTOMISATION_TYRE_COLOUR_R` | Tire red channel. ← no red → full red. Combine R/G/B for any color. |
| `CUSTOMISATION_TYRE_STYLE` | Tire style index. Changes tire tread/sidewall appearance. |
| `CUSTOMISATION_WHEEL_FRONT_WIDTH` | Front wheel width. ← narrow → wide. |
| `CUSTOMISATION_WHEEL_PREVIEW` | ON = preview wheel changes live. OFF = apply on exit. |
| `CUSTOMISATION_WHEEL_REAR_WIDTH` | Rear wheel width. ← narrow → wide. |
| `CUSTOMISATION_WHEEL_STYLE` | Wheel design index. Changes rim appearance. |
| `CUSTOMISATION_WHEEL_TYRE_RATIO` | Tire profile (sidewall height). ← low-profile → balloon tires. |

## Cutscenes menu (`CUTSCENE`)

| Runtime control | What it does |
|---|---|
| `CUTSCENE_DISABLE_CAR_CULLING` | ON = show all cars in cutscenes (no LOD culling). OFF = normal culling. |
| `CUTSCENE_DISABLE_INTRO_OVERLAY` | ON = skips the intro overlay in cutscenes. OFF = shows it. |
| `CUTSCENE_ENABLE_ANIMATED_REVS` | ON = engine revs animate in cutscenes. OFF = static engine. |
| `CUTSCENE_HEADLIGHT_CAR_INDEX` | Which car has headlights in cutscene. 0 = player, 1+ = opponents. |
| `CUTSCENE_LOAD_CUSTOM_CAR_CONFIGS` | ON = load custom car configs for cutscenes. OFF = default configs. |
| `CUTSCENE_LOOP_FOREVER` | ON = cutscene loops endlessly. OFF = plays once. |
| `CUTSCENE_OVERRIDE_OPPONENT_LOD_OFFSET` | Override opponent LOD in cutscenes. ← lower detail → higher detail. |
| `CUTSCENE_PLAY_INTRO_CUTSCENE_ON_RESTART` | ON = replay intro cutscene on race restart. OFF = skip to grid. |

## Damage menu (`DAMAGE`)

| Runtime control | What it does |
|---|---|
| `DAMAGE_AI_ENABLED` | ON = AI cars take crash damage. OFF = AI cars are invincible. |
| `DAMAGE_FORCE_PART` | Force damage on specific car part index. Changes which part breaks. |
| `DAMAGE_FORCE_STATE` | Force damage state (0=none, 1=light, 2=heavy, 3=destroyed). |
| `DAMAGE_PLAYER_ENABLED` | ON = your car takes crash damage (visual + mechanical). OFF = invincible. |

## Debug Render menu (`DEBUGRENDER`)

| Runtime control | What it does |
|---|---|
| `DEBUGRENDER_ACCFORCE_R4` | ON = draws acceleration force vectors on cars. OFF = hidden. |
| `DEBUGRENDER_AI_SPLINE_LOOK_AHEAD_CAR` | ON = lines showing where AI is looking ahead. OFF = hidden. |
| `DEBUGRENDER_BULLET` | ON = Bullet physics engine debug (contact points, forces). OFF = hidden. |
| `DEBUGRENDER_BULLET_TRACK_COLLISION` | ON = track collision mesh overlay. OFF = hidden. |
| `DEBUGRENDER_BUMPSTOPS_R4` | ON = show suspension bumpstop markers. OFF = hidden. |
| `DEBUGRENDER_CAR_BOUNDS` | ON = show car bounding boxes. OFF = hidden. |
| `DEBUGRENDER_CAR_BOUNDS_Z_OFFSET` | Car bounding box height offset. ← lower bounds → higher bounds. |
| `DEBUGRENDER_CAR_CRASH` | ON = show crash detection volumes. OFF = hidden. |
| `DEBUGRENDER_CAR_CRASH_CAR1` | ON = show crash debug for car 1. OFF = hidden. |
| `DEBUGRENDER_CAR_CRASH_CAR2` | ON = show crash debug for car 2. OFF = hidden. |
| `DEBUGRENDER_CAR_G_FORCES` | ON = show G-force vectors on car. OFF = hidden. |
| `DEBUGRENDER_CAR_VS_CAR` | ON = show car-to-car collision debug. OFF = hidden. |
| `DEBUGRENDER_CAR_VS_TRACK` | ON = show car-to-track collision debug. OFF = hidden. |
| `DEBUGRENDER_CGROUNDCOLLISION` | ON = show ground collision contact points. OFF = hidden. |
| `DEBUGRENDER_ENABLED` | ON = master switch for all debug visuals. OFF = no debug rendering. |
| `DEBUGRENDER_SIDEFORCE_R4` | ON = show lateral force vectors on tires. OFF = hidden. |
| `DEBUGRENDER_SPLINE` | ON = show racing spline path. OFF = hidden. |
| `DEBUGRENDER_SPLINE_TO_RENDER` | Which spline index to visualize. Higher = different spline variant. |
| `DEBUGRENDER_SUSPENSION_ROLL` | ON = show suspension roll visualization. OFF = hidden. |
| `DEBUGRENDER_SUSPENSION_SPRINGS_R4` | ON = show suspension spring compression/extension. OFF = hidden. |
| `DEBUGRENDER_UNDERBODY_DAMAGE` | ON = show underbody damage contact points. OFF = hidden. |

## Debugview menu (`DEBUGVIEW`)

| Runtime control | What it does |
|---|---|
| `DEBUGVIEW_CHANNEL` | Debug view channel to display. Changes which render buffer is shown. |
| `DEBUGVIEW_MODE` | Debug view mode (depth, normals, lighting, etc.). Changes visualization. |
| `DEBUGVIEW_TEXEL_DENSITY` | ON = show texel density heatmap. OFF = normal view. |
| `DEBUGVIEW_TEXEL_DENSITY_OPACITY` | Texel density overlay opacity. ← transparent → opaque. |
| `DEBUGVIEW_TEXEL_DENSITY_SCALE` | Texel density reference scale. ← red at low density → red at high density. |

## Dragrace menu (`DRAGRACE`)

| Runtime control | What it does |
|---|---|
| `DRAGRACE_CAMVIEW_BONNET_RENDERINSCENE` | ON = render scene in bonnet cam during drag race. OFF = hidden. |
| `DRAGRACE_CAMVIEW_BUMPER_RENDERINSCENE` | ON = render scene in bumper cam during drag race. OFF = hidden. |
| `DRAGRACE_CAMVIEW_INCAR_RENDERINSCENE` | ON = render scene in cockpit cam during drag race. OFF = hidden. |
| `DRAGRACE_GOOD_SHIFT_ZONE` | Size of the 'good shift' timing window. ← tiny (hard) → large (easy). |

## Drift menu (`DRIFT`)

| Runtime control | What it does |
|---|---|
| `DRIFT_ENABLED` | ON = drift mode active (looser rear grip, drift scoring). OFF = normal grip. |
| `DRIFT_GRIP_PERCENT` | Rear grip in drift mode. ← no rear grip (wild slides) → some grip (controlled drifts). |
| `DRIFT_SCORE_MULTIPLIER` | Drift score multiplier. ← low scores → massive drift points. |
| `DRIFT_TURNING_POINT_PERCENT` | Steering angle for drift initiation. ← drifts with small input → needs big steering angle. |

## Enable menu (`ENABLE`)

| Runtime control | What it does |
|---|---|
| `ENABLE_NASCAR_TUTORIAL` | ON = forces NASCAR tutorial sequence on next race. OFF = normal. |

## Endurance menu (`ENDURANCE`)

| Runtime control | What it does |
|---|---|
| `ENDURANCE_TIME_LIMIT` | Time limit for endurance races. ← short race → long race. |

## Features menu (`FEAT`)

| Runtime control | What it does |
|---|---|
| `FEAT_EVENT_DEBUG_INFO` | ON = shows event system debug info (IDs, states). OFF = hidden. |
| `FEAT_HIDE_COMMON` | ON = hide common/easy feats from display. OFF = show all feats. |
| `FEAT_KEEP_CAR_IN_SIGHT` | ON = keeps target car visible for feat tracking. OFF = normal view. |
| `FEAT_KEEP_CAR_IN_SIGHT_OPPONENT_ID` | Which opponent to track for 'keep in sight' feat. |
| `FEAT_OFF_TRACK` | Off-track detection distance. ← strict (small deviation = off-track) → lenient. |
| `FEAT_OVERTAKE_FEAT_COOLDOWN` | Cooldown between overtake feats. ← rapid scoring → needs time between overtakes. |
| `FEAT_PERFECT_RACING_LINE` | Racing line tolerance. ← tight (must be perfect) → wide (forgiving). |
| `FEAT_PLAYER_DAMAGE_INFO` | ON = show damage info during feats. OFF = hidden. |
| `FEAT_SKID_DISTANCE` | Skid feat minimum distance. ← short skids count → needs long skids. |
| `FEAT_STAY_IN_LEAD` | Lead time for 'stay in lead' feat. ← brief lead counts → must hold lead longer. |
| `FEAT_TAILGATE` | Tailgate distance for drafting feat. ← far following counts → must be very close. |
| `FEAT_TIME_WITHOUT_BRAKING` | Time without braking for feat. ← short time → long time needed. |
| `FEAT_TIME_WITHOUT_TURNING` | Time without steering for feat. ← short time → long time needed. |

## Force menu (`FORCE`)

| Runtime control | What it does |
|---|---|
| `FORCE_ALPHA_ADD_ON_ALPHA_TEST` | ON = add alpha on alpha-tested materials. OFF = normal alpha test. |
| `FORCE_ALPHA_ADD_ON_BLEND` | ON = additive alpha on blended materials. OFF = normal blending. |
| `FORCE_NUMBER_OF_SPLIT_SCREENS` | Force split-screen count. Changes local multiplayer layout. |
| `FORCE_RACE_METRICS_EXTERNAL` | ON = send race metrics to external tools. OFF = internal only. |

## Frame menu (`FRAME`)

| Runtime control | What it does |
|---|---|
| `FRAME_RECORD_360` | ON = enable 360° frame recording. OFF = normal recording. |
| `FRAME_RECORD_360_CUBE_SIZE` | 360° capture cube face size. ← low quality → high quality (slow). |
| `FRAME_RECORD_360_PREVIEW` | ON = show 360° preview while recording. OFF = blind recording. |
| `FRAME_RECORD_360_PROJECTION_HEIGHT` | 360° output image height. ← low res → high res. |
| `FRAME_RECORD_360_PROJECTION_WIDTH` | 360° output image width. ← low res → high res. |
| `FRAME_RECORD_FPS` | Recording frame rate. ← low FPS (smaller file) → high FPS (smoother). |

## Frustum menu (`FRUSTUM`)

| Runtime control | What it does |
|---|---|
| `FRUSTUM_CULL_TRACK_OVERRIDE` | ON = override track frustum culling. OFF = default culling. |

## Global menu (`GLOBAL`)

| Runtime control | What it does |
|---|---|
| `GLOBAL_CAR_MAX_ACC` | Global max acceleration for all cars. ← sluggish → rocket. |
| `GLOBAL_CAR_MAX_FRONT_WHEEL_TURN_ANGLE` | Global max steering angle. ← tiny turns → extreme lock. |
| `GLOBAL_CAR_MAX_HANDL` | Global max handling. ← loose → razor-sharp. |
| `GLOBAL_CAR_MAX_SPEED` | Global max speed cap for all cars. ← slow → unlimited. |
| `GLOBAL_CAR_WALL_FRICTION_COEFFICIENT` | Wall scraping friction. ← slides along walls → sticks to walls. |
| `GLOBAL_CAR_WALL_FRICTION_MODE` | Wall friction calculation mode. Changes wall contact behavior. |

## HDR menu (`HDR`)

| Runtime control | What it does |
|---|---|
| `HDR_AUTOMATIC_EXPOSURE_MAX` | Auto-exposure max brightness. ← capped dark → allows very bright. |
| `HDR_AUTOMATIC_EXPOSURE_MIN` | Auto-exposure min brightness. ← allows very dark → keeps bright. |
| `HDR_AUTOMATIC_MIDDLE_GRAY` | Middle gray target for auto-exposure. ← darker overall → brighter overall. |
| `HDR_AUTOMATIC_MIDDLE_GRAY_COCKPIT` | Middle gray in cockpit view. ← darker cockpit → brighter cockpit. |
| `HDR_BLOOM_BLUR_FB_0` | Bloom blur framebuffer 0. Technical: blur sample buffer. |
| `HDR_BLOOM_BLUR_FB_1` | Bloom blur framebuffer 1. Technical: blur sample buffer. |
| `HDR_BLOOM_BLUR_FB_2` | Bloom blur framebuffer 2. Technical: blur sample buffer. |
| `HDR_BLOOM_BLUR_RADIUS_0` | Bloom blur radius (large). ← tight bloom → wide glow spread. |
| `HDR_BLOOM_BLUR_RADIUS_1` | Bloom blur radius (medium). ← tight bloom → wide glow spread. |
| `HDR_BLOOM_BLUR_RADIUS_2` | Bloom blur radius (small). ← tight bloom → wide glow spread. |
| `HDR_BLOOM_CUTOFF` | Bloom brightness threshold. ← everything blooms → only bright highlights bloom. |
| `HDR_BLOOM_DOWNSAMPLE_FB_0` | Bloom downsample buffer 0. Technical: resolution tier. |
| `HDR_BLOOM_DOWNSAMPLE_FB_1` | Bloom downsample buffer 1. Technical: resolution tier. |
| `HDR_BLOOM_DOWNSAMPLE_FB_2` | Bloom downsample buffer 2. Technical: resolution tier. |
| `HDR_BLOOM_DOWNSAMPLE_FB_3` | Bloom downsample buffer 3. Technical: resolution tier. |
| `HDR_BLOOM_DOWNSAMPLE_FB_4` | Bloom downsample buffer 4. Technical: resolution tier. |
| `HDR_BLOOM_INTENSITY` | Bloom glow strength. ← no bloom → intense glowing highlights. |
| `HDR_BLOOM_LEVELS_0` | Bloom level 0 contribution. ← less → more bloom at this scale. |
| `HDR_BLOOM_LEVELS_1` | Bloom level 1 contribution. ← less → more bloom at this scale. |
| `HDR_BLOOM_LEVELS_2` | Bloom level 2 contribution. ← less → more bloom at this scale. |
| `HDR_BLOOM_LEVELS_3` | Bloom level 3 contribution. ← less → more bloom at this scale. |
| `HDR_BLOOM_LEVELS_4` | Bloom level 4 contribution. ← less → more bloom at this scale. |
| `HDR_CUBEMAP_MODE` | HDR cubemap rendering mode. Changes reflection quality/method. |
| `HDR_DEBUG_BLOOM` | ON = show bloom debug visualization. OFF = normal bloom. |
| `HDR_DEBUG_BLOOM_LEVEL` | Which bloom mip level to debug. Shows individual bloom layers. |
| `HDR_DEBUG_LUMINANCE` | ON = show luminance debug heatmap. OFF = normal view. |
| `HDR_DEBUG_LUMINANCE_MAX` | Luminance debug max value. ← low ceiling → high ceiling. |
| `HDR_DEBUG_LUMINANCE_MAX_LOCK` | ON = lock luminance max to current value. OFF = dynamic. |
| `HDR_DEBUG_TEST` | ON = HDR test pattern. OFF = normal rendering. |
| `HDR_ENABLE_ALL` | ON = enable all HDR effects. OFF = disable all HDR. |
| `HDR_ENABLE_AUTOMATIC_EXPOSURE` | ON = auto-exposure (eyes adjust to brightness). OFF = fixed exposure. |
| `HDR_ENABLE_AUTOMATIC_EXPOSURE_IN_FREE_CAM` | ON = auto-exposure in free camera. OFF = locked exposure in free cam. |
| `HDR_ENABLE_BLOOM` | ON = bloom/glow effect on bright surfaces. OFF = no bloom. |
| `HDR_ENABLE_COLOUR_GRADE` | ON = color grading LUT active. OFF = ungraded colors. |
| `HDR_ENABLE_TONEMAP` | ON = tone mapping (HDR to display range). OFF = raw HDR values (washed out). |
| `HDR_FIXED_EXPOSURE` | Manual exposure value when auto-exposure is off. ← dark → bright. |
| `HDR_SHOW_BALANCE_TOOLS` | ON = show HDR balance/histogram tools. OFF = hidden. |
| `HDR_TONEMAP_A` | Filmic tonemap parameter A (shoulder strength). Shapes highlight rolloff. |
| `HDR_TONEMAP_B` | Filmic tonemap parameter B (linear strength). Shapes midtone response. |
| `HDR_TONEMAP_C` | Filmic tonemap parameter C (linear angle). Shapes midtone curve. |
| `HDR_TONEMAP_D` | Filmic tonemap parameter D (toe strength). Shapes shadow response. |
| `HDR_TONEMAP_E` | Filmic tonemap parameter E (toe numerator). Shapes deep shadow curve. |
| `HDR_TONEMAP_EDIT` | ON = enable live tonemap editing. OFF = locked values. |
| `HDR_TONEMAP_F` | Filmic tonemap parameter F (toe denominator). Shapes deep shadow curve. |
| `HDR_TONEMAP_RESET` | ON = reset tonemap to defaults. Self-clearing. |
| `HDR_USE_POST_SHADER` | ON = use post-processing shader for HDR. OFF = raw HDR output. |
| `HDR_WHITEPOINT` | HDR white point. ← darker whites → brighter whites. |

## Headlight menu (`HEADLIGHT`)

| Runtime control | What it does |
|---|---|
| `HEADLIGHT_FALLOFF_ANGLE_END` | Headlight cone edge angle. ← tight spot → wide flood. |
| `HEADLIGHT_FALLOFF_ANGLE_START` | Headlight hotspot angle. ← narrow bright center → wide bright center. |
| `HEADLIGHT_FALLOFF_ASPECT` | Headlight cone aspect ratio. ← round beam → wide beam. |
| `HEADLIGHT_ID` | Which headlight model to use. Changes beam pattern. |
| `HEADLIGHT_OFFSET_Y` | Headlight vertical position. ← lower → higher. |
| `HEADLIGHT_OFFSET_Z` | Headlight forward position. ← recessed → protruding. |
| `HEADLIGHT_RANGE` | Headlight throw distance. ← short range → long range. |
| `HEADLIGHT_SCALE` | Headlight brightness. ← dim → blinding. |
| `HEADLIGHT_VERTICAL_ANGLE` | Headlight aim angle. ← aimed down → aimed up. |

## Hide menu (`HIDE`)

| Runtime control | What it does |
|---|---|
| `HIDE_ES1_TRACK_MESHES` | ON = hide OpenGL ES1 fallback track meshes. OFF = show them. |

## Hotswap menu (`HOTSWAP`)

| Runtime control | What it does |
|---|---|
| `HOTSWAP_DASH_INSTRUMENTS` | ON = hot-reload dashboard instruments. OFF = static instruments. |
| `HOTSWAP_ENABLE` | ON = live asset hot-reload (dev tool). OFF = normal asset loading. |
| `HOTSWAP_HUD` | ON = hot-reload HUD elements. OFF = static HUD. |

## HUD menu (`HUD`)

| Runtime control | What it does |
|---|---|
| `HUD_ENABLE_EXTERNAL_PLANE_OFFSETS` | ON = external plane offset markers for safe area. OFF = hidden. |
| `HUD_EXTERNAL_PLANE_OFFSET_HEIGHT` | HUD vertical position offset. ← lower on screen → higher on screen. |
| `HUD_EXTERNAL_PLANE_OFFSET_WIDTH` | HUD horizontal position offset. ← further left → further right. |
| `HUD_SHOW_DEBUG` | ON = debug info overlay on the HUD. OFF = clean HUD. |
| `HUD_SHOW_DEBUG_PLANE` | ON = debug plane visualizer on screen. OFF = hidden. |

## Hunter menu (`HUNTER`)

| Runtime control | What it does |
|---|---|
| `HUNTER_DELAY_END_SHOW_TIME` | End delay display time. ← short → long. |
| `HUNTER_DELAY_START_SHOW_TIME` | Start delay display time. ← short → long. |
| `HUNTER_FADE_TO_BLACK_TIME` | Fade to black duration. ← instant → slow fade. |
| `HUNTER_MIN_BLACK_TIME` | Minimum black screen time. ← instant → holds black. |
| `HUNTER_OPPONENT_SKILL` | Hunter mode opponent AI skill. ← easy target → hard target. |
| `HUNTER_OPPONENT_SKILL_OVERRIDE` | ON = use custom hunter opponent skill. OFF = default. |
| `HUNTER_PLAYER_DELAY` | Player start delay in hunter mode. ← no head start → big head start for target. |

## Input & Controls menu (`INPUT`)

| Runtime control | What it does |
|---|---|
| `INPUT_ACCEL_LOWER_DEADZONE_PERCENT` | Throttle dead zone bottom. ← responds to lightest touch → needs harder press. |
| `INPUT_ACCEL_UPPER_DEADZONE_PERCENT` | Throttle dead zone top. ← full throttle earlier → need to mash harder. |
| `INPUT_BRAKE_LOWER_DEADZONE_PERCENT` | Brake dead zone bottom. ← responds to lightest tap → needs harder press. |
| `INPUT_BRAKE_UPPER_DEADZONE_PERCENT` | Brake dead zone top. ← full brake easier → need to press harder. |
| `INPUT_CLUBSPORT_ACCEL_LOWER_DEADZONE_PERCENT` | ClubSport wheel throttle pedal lower deadzone. ← sensitive → needs deeper press. |
| `INPUT_CLUBSPORT_ACCEL_UPPER_DEADZONE_PERCENT` | ClubSport wheel throttle pedal upper deadzone. ← full early → full late. |
| `INPUT_CLUBSPORT_BRAKE_LOWER_DEADZONE_PERCENT` | ClubSport wheel brake pedal lower deadzone. ← sensitive → needs deeper press. |
| `INPUT_CLUBSPORT_BRAKE_UPPER_DEADZONE_PERCENT` | ClubSport wheel brake pedal upper deadzone. ← full early → full late. |
| `INPUT_CLUBSPORT_DAMPER_COEFFICIENT_MULTIPLIER` | ClubSport force feedback damping. ← light resistance → heavy resistance. |
| `INPUT_CLUBSPORT_FORCE_FRONT_WHEEL_MULTIPLIER` | ClubSport front wheel force feedback strength. ← light → heavy. |
| `INPUT_CLUBSPORT_FORCE_WHEEL_OPPONENT_COLLISION_MAX_STRENGTH` | ClubSport max force on opponent collision. ← soft bump → violent jerk. |
| `INPUT_CLUBSPORT_FORCE_WHEEL_OPPONENT_COLLISION_MIN_STRENGTH` | ClubSport min force on opponent collision. ← no feedback → some feedback. |
| `INPUT_CLUBSPORT_FORCE_WHEEL_WALL_COLLISION_MAX_STRENGTH` | ClubSport max force on wall hit. ← soft → violent. |
| `INPUT_CLUBSPORT_FORCE_WHEEL_WALL_COLLISION_MIN_STRENGTH` | ClubSport min force on wall hit. ← no feedback → some feedback. |
| `INPUT_CLUBSPORT_FRICTION_COEFFICIENT_MULTIPLIER` | ClubSport wheel friction force. ← free spinning → heavy center. |
| `INPUT_CLUBSPORT_FRICTION_END_SPEED` | ClubSport friction fadeout speed. ← fades early → friction at higher speeds. |
| `INPUT_CLUBSPORT_INFO_X` | ClubSport debug info X position on screen. |
| `INPUT_CLUBSPORT_INFO_Y` | ClubSport debug info Y position on screen. |
| `INPUT_CLUBSPORT_JITTER_MULTIPLIER` | ClubSport wheel vibration on rough surfaces. ← smooth → rough feedback. |
| `INPUT_CLUBSPORT_OVERSTEER_SPRING_MULTIPLIER` | ClubSport countersteer spring force. ← no assist → strong self-centering on oversteer. |
| `INPUT_CLUBSPORT_PEDAL_PRIORITY` | ON = pedal priority (brake overrides throttle). OFF = simultaneous input allowed. |
| `INPUT_CLUBSPORT_PEDAL_RUMBLE_ACCEL_SCALE` | ClubSport throttle pedal rumble. ← no vibration → strong engine vibration in pedal. |
| `INPUT_CLUBSPORT_PEDAL_RUMBLE_BRAKE_MAX_PRESSURE` | ClubSport brake rumble max pressure. ← rumbles light → rumbles at full brake. |
| `INPUT_CLUBSPORT_PEDAL_RUMBLE_BRAKE_MIN_PRESSURE` | ClubSport brake rumble start pressure. ← rumbles immediately → only heavy braking. |
| `INPUT_CLUBSPORT_PEDAL_RUMBLE_BRAKE_MIN_SCALE` | ClubSport brake rumble minimum intensity. ← no min → some baseline rumble. |
| `INPUT_CLUBSPORT_PEDAL_RUMBLE_MAX_SPEED` | Speed for max pedal rumble. ← max rumble at low speed → only at high speed. |
| `INPUT_CLUBSPORT_PEDAL_RUMBLE_MAX_STRENGTH` | ClubSport max pedal rumble strength. ← subtle → violent. |
| `INPUT_CLUBSPORT_PEDAL_RUMBLE_MIN_SPEED` | Speed for min pedal rumble. ← rumble at standstill → only when moving. |
| `INPUT_CLUBSPORT_PEDAL_RUMBLE_MIN_STRENGTH` | ClubSport min pedal rumble strength. ← none → some baseline. |
| `INPUT_CLUBSPORT_PEDAL_RUMBLE_NOISE_RATE` | ClubSport pedal rumble noise frequency. ← slow rumble → fast vibration. |
| `INPUT_CLUBSPORT_PEDAL_RUMBLE_NOISE_RATIO` | ClubSport pedal rumble noise mix. ← smooth → noisy/rough. |
| `INPUT_CLUBSPORT_SELF_ALIGNING_TORQUE_DIRECTION` | ClubSport self-aligning torque direction. Changes centering behavior. |
| `INPUT_CLUBSPORT_SHOW_INFO` | ON = show ClubSport wheel debug info. OFF = hidden. |
| `INPUT_CLUBSPORT_SHOW_INFO_ESPORTS` | ON = show esport-specific ClubSport info. OFF = hidden. |
| `INPUT_CLUBSPORT_SPRING_COEFFICIENT_MULTIPLIER` | ClubSport center spring strength. ← floppy center → strong centering. |
| `INPUT_CLUBSPORT_SPRING_MAX_SPEED` | ClubSport spring force max speed. ← effect ends early → effect at high speed. |
| `INPUT_CLUBSPORT_SPRING_SATURATION_MULTIPLIER` | ClubSport spring saturation. ← soft limit → hard limit at lock. |
| `INPUT_ENABLE_ANALOG_ACCELERATION` | ON = analog throttle input (pressure sensitive). OFF = digital on/off. |
| `INPUT_ENABLE_ANALOG_BRAKING` | ON = analog brake input (pressure sensitive). OFF = digital on/off. |
| `INPUT_FORCE_CONTROLLER_TYPE` | Force controller type ID. Changes how input is mapped. |
| `INPUT_GYRO_STEER_SENSITIVITY` | Tilt steering. ← barely responds to tilt → tiny tilt = full lock. |
| `INPUT_JOYSTICK_WHEEL_STEERING_AXIS_ROTATION` | Joystick/wheel steering axis rotation offset. Calibration value. |
| `INPUT_JOYSTICK_WHEEL_STEERING_CLAMP_MULITPLIER` | Joystick/wheel steering clamp. ← reduced range → full range. |
| `INPUT_JOYSTICK_WHEEL_STEERING_OVERRIDE` | ON = override joystick steering with custom values. OFF = default mapping. |
| `INPUT_JOYSTICK_WHEEL_STEERING_SENSITVITY` | Joystick/wheel steering sensitivity. ← sluggish → twitchy. |
| `INPUT_MAXIMUM_ANALOG_BRAKING_INPUT_THRESHOLD` | Max analog brake input threshold. ← full brake easier → needs harder press. |
| `INPUT_SHOW_BUTTON_REGIONS` | ON = show touch button regions on screen. OFF = hidden. |
| `INPUT_SHOW_PRESSED_REGIONS` | ON = highlight touched regions on screen. OFF = hidden. |
| `INPUT_SHOW_TOUCH_INFO` | ON = show touch coordinate debug info. OFF = hidden. |
| `INPUT_STEER_LINEARITY` | Steering curve. ← linear (1:1) → exponential (gentle center, snappy edges). |
| `INPUT_STEER_SENSITIVITY` | Touch steering. ← sluggish response → twitchy instant response. |
| `INPUT_VERBOSE_TOUCH_LOGGING` | ON = log all touch events to console. OFF = quiet. |
| `INPUT_VIBRATION_ENABLED` | ON = phone vibrates on collisions/curbs. OFF = no haptics. |
| `INPUT_VIBRATION_STRENGTH` | Vibration power. ← barely feel it → strong buzz on every bump. |

## Lighting menu (`LIGHTING`)

| Runtime control | What it does |
|---|---|
| `LIGHTING_AMBIENT_B` | Ambient light blue channel. ← no blue → blue ambient tint. |
| `LIGHTING_AMBIENT_G` | Ambient light green channel. ← no green → green ambient tint. |
| `LIGHTING_AMBIENT_ID` | Ambient lighting preset ID. Changes time-of-day/mood. |
| `LIGHTING_AMBIENT_INTERIOR_B` | Interior ambient blue. ← no blue → blue cockpit ambient. |
| `LIGHTING_AMBIENT_INTERIOR_G` | Interior ambient green. ← no green → green cockpit ambient. |
| `LIGHTING_AMBIENT_INTERIOR_R` | Interior ambient red. ← no red → red cockpit ambient. |
| `LIGHTING_AMBIENT_R` | Ambient light red channel. ← no red → red ambient tint. |
| `LIGHTING_CAR_LIGHT_INTENSITY` | Car headlight/taillight brightness. ← dim → blinding. |
| `LIGHTING_CAR_SHADOW_B` | Car shadow blue tint. ← neutral → blue-tinted shadows. |
| `LIGHTING_CAR_SHADOW_G` | Car shadow green tint. ← neutral → green-tinted shadows. |
| `LIGHTING_CAR_SHADOW_R` | Car shadow red tint. ← neutral → red-tinted shadows. |
| `LIGHTING_DIFFUSE_B` | Diffuse light blue. Changes overall scene blue balance. |
| `LIGHTING_DIFFUSE_G` | Diffuse light green. Changes overall scene green balance. |
| `LIGHTING_DIFFUSE_R` | Diffuse light red. Changes overall scene red balance. |
| `LIGHTING_DIRECT_B` | Direct sunlight blue. ← warm light → cool/blue sunlight. |
| `LIGHTING_DIRECT_G` | Direct sunlight green. ← magenta tint → green tint. |
| `LIGHTING_DIRECT_INTENSITY` | Sunlight brightness. ← dim/overcast → harsh sunlight. |
| `LIGHTING_DIRECT_R` | Direct sunlight red. ← cool light → warm/orange sunlight. |
| `LIGHTING_FLAG_TRANSLUCENCY_MULTIPLIER` | Flag see-through amount. ← opaque flags → translucent flags. |
| `LIGHTING_FOG` | ON = scene fog enabled. OFF = no fog. |
| `LIGHTING_FOG_COLOUR_B` | Fog blue color. Changes fog tint. |
| `LIGHTING_FOG_COLOUR_G` | Fog green color. Changes fog tint. |
| `LIGHTING_FOG_COLOUR_R` | Fog red color. Changes fog tint. |
| `LIGHTING_FOG_END` | Fog end distance. ← fog close → fog far away (clearer view). |
| `LIGHTING_FOG_SATURATION` | Fog color saturation. ← gray fog → vivid colored fog. |
| `LIGHTING_FOG_START` | Fog start distance. ← fog starts at camera → fog starts far away. |
| `LIGHTING_FOG_SUN_COLOUR_B` | Sun-facing fog blue. Changes fog color looking toward sun. |
| `LIGHTING_FOG_SUN_COLOUR_G` | Sun-facing fog green. Changes fog color looking toward sun. |
| `LIGHTING_FOG_SUN_COLOUR_R` | Sun-facing fog red. Changes fog color looking toward sun. |
| `LIGHTING_FOG_SUN_END` | Sun fog end angle. ← narrow sun glow → wide sun glow in fog. |
| `LIGHTING_FOG_SUN_POWER` | Sun fog glow intensity. ← subtle → blinding sun through fog. |
| `LIGHTING_FOG_SUN_SATURATION` | Sun fog saturation. ← gray → vivid sun glow. |
| `LIGHTING_FOG_SUN_START` | Sun fog start angle. ← glow everywhere → only looking directly at sun. |
| `LIGHTING_IS_RAINING` | ON = rain lighting active (wet surfaces, dark sky). OFF = dry conditions. |
| `LIGHTING_LIGHTMAP_BRIGHT_POINT` | Lightmap bright threshold. ← more areas lit → only brightest areas lit. |
| `LIGHTING_LIGHTMAP_BRIGHT_TINT_B` | Lightmap bright area blue tint. |
| `LIGHTING_LIGHTMAP_BRIGHT_TINT_G` | Lightmap bright area green tint. |
| `LIGHTING_LIGHTMAP_BRIGHT_TINT_R` | Lightmap bright area red tint. |
| `LIGHTING_LIGHTMAP_DARK_POINT` | Lightmap dark threshold. ← more shadow → less shadow. |
| `LIGHTING_LIGHTMAP_DARK_TINT_B` | Lightmap shadow blue tint. |
| `LIGHTING_LIGHTMAP_DARK_TINT_G` | Lightmap shadow green tint. |
| `LIGHTING_LIGHTMAP_DARK_TINT_R` | Lightmap shadow red tint. |
| `LIGHTING_LIGHTMAP_INTENSITY` | Baked lightmap intensity. ← dim lightmaps → bright lightmaps. |
| `LIGHTING_SKY_MULTIPLIER` | Sky brightness multiplier. ← dark sky → bright sky. |
| `LIGHTING_SPECULAR_B` | Specular highlight blue. Changes shiny surface tint. |
| `LIGHTING_SPECULAR_G` | Specular highlight green. Changes shiny surface tint. |
| `LIGHTING_SPECULAR_R` | Specular highlight red. Changes shiny surface tint. |
| `LIGHTING_SPEC_EXPONENT_MODIFIER` | Specular sharpness. ← soft/spread highlights → sharp/tight highlights. |
| `LIGHTING_SPEC_SHADOW_CUTOFF` | Specular in shadow cutoff. ← specular in shadows → no specular in shadows. |
| `LIGHTING_SUN_ASIMUTH` | Sun horizontal angle (compass direction). Rotates the sun position. |
| `LIGHTING_SUN_ELEVATION` | Sun vertical angle. ← sunrise/sunset → noon (directly overhead). |
| `LIGHTING_TREE_AMBIENT_B` | Tree ambient blue. ← neutral → blue-tinted tree shadows. |
| `LIGHTING_TREE_AMBIENT_G` | Tree ambient green. ← neutral → green-tinted trees. |
| `LIGHTING_TREE_AMBIENT_R` | Tree ambient red. ← neutral → red-tinted trees. |
| `LIGHTING_TREE_BRIGHT_POINT` | Tree lightmap bright point. Changes tree lighting balance. |
| `LIGHTING_TREE_BRIGHT_TINT_B` | Tree bright area blue tint. |
| `LIGHTING_TREE_BRIGHT_TINT_G` | Tree bright area green tint. |
| `LIGHTING_TREE_BRIGHT_TINT_R` | Tree bright area red tint. |
| `LIGHTING_TREE_DARK_POINT` | Tree shadow threshold. Changes tree shadow depth. |
| `LIGHTING_TREE_DARK_TINT_B` | Tree shadow blue tint. |
| `LIGHTING_TREE_DARK_TINT_G` | Tree shadow green tint. |
| `LIGHTING_TREE_DARK_TINT_R` | Tree shadow red tint. |
| `LIGHTING_TREE_DIFFUSE_B` | Tree diffuse blue. Changes tree color balance. |
| `LIGHTING_TREE_DIFFUSE_G` | Tree diffuse green. Changes tree color balance. |
| `LIGHTING_TREE_DIFFUSE_R` | Tree diffuse red. Changes tree color balance. |
| `LIGHTING_WETNESS` | Surface wetness. ← bone dry → fully wet (shiny, dark surfaces). |

## Listener menu (`LISTENER`)

| Runtime control | What it does |
|---|---|
| `LISTENER_DSP_ENABLED` | ON = audio DSP effects active. OFF = raw audio. |
| `LISTENER_DSP_TRANSFER_TWEAKS_ON_TARGET_SWITCH` | ON = carry DSP settings when switching audio target. OFF = reset. |
| `LISTENER_DSP_TWEAKING` | ON = enable live DSP parameter editing. OFF = locked. |
| `LISTENER_DSP_TWEAKING_TARGET` | Which audio bus to apply DSP tweaks to. |
| `LISTENER_EQ1_BANDWIDTH` | EQ band 1 width. ← narrow (surgical) → wide (broad). |
| `LISTENER_EQ1_CENTRE_FREQ` | EQ band 1 center frequency. ← low bass → high frequency. |
| `LISTENER_EQ1_GAIN` | EQ band 1 boost/cut. ← cut (quieter) → boost (louder). |
| `LISTENER_EQ2_BANDWIDTH` | EQ band 2 width. ← narrow → wide. |
| `LISTENER_EQ2_CENTRE_FREQ` | EQ band 2 center frequency. ← low → high. |
| `LISTENER_EQ2_GAIN` | EQ band 2 boost/cut. ← cut → boost. |
| `LISTENER_EQ3_BANDWIDTH` | EQ band 3 width. ← narrow → wide. |
| `LISTENER_EQ3_CENTRE_FREQ` | EQ band 3 center frequency. ← low → high. |
| `LISTENER_EQ3_GAIN` | EQ band 3 boost/cut. ← cut → boost. |
| `LISTENER_EQ4_BANDWIDTH` | EQ band 4 width. ← narrow → wide. |
| `LISTENER_EQ4_CENTRE_FREQ` | EQ band 4 center frequency. ← low → high. |
| `LISTENER_EQ4_GAIN` | EQ band 4 boost/cut. ← cut → boost. |
| `LISTENER_SHOW_SETTINGS` | ON = show DSP/EQ settings on screen. OFF = hidden. |

## Lower menu (`LOWER`)

| Runtime control | What it does |
|---|---|
| `LOWER_CAR_LODS` | ON = force lower LOD on all car models. OFF = normal quality. |

## Menu menu (`MENU`)

| Runtime control | What it does |
|---|---|
| `MENU_WIDTH` | Debug menu width. ← narrow → wide menu panel. |

## Multiplayer menu (`MULTIPLAYER`)

| Runtime control | What it does |
|---|---|
| `MULTIPLAYER_COLLISION_DAMPENING` | Multiplayer collision smoothing. ← raw physics → smoothed contacts. |
| `MULTIPLAYER_COLLISION_DAMPENING_ENABLED` | ON = smooth multiplayer collisions. OFF = raw physics. |
| `MULTIPLAYER_ERRATIC_UPDATES` | ON = simulate erratic network updates (test tool). OFF = normal. |
| `MULTIPLAYER_NEW_INTERPOLATION_LOGIC` | ON = new position interpolation. OFF = legacy interpolation. |
| `MULTIPLAYER_PACKET_LERP_FACTOR_LAN` | LAN position smoothing. ← snappy/jittery → smooth/laggy. |
| `MULTIPLAYER_PACKET_LERP_FACTOR_SERVER` | Server position smoothing. ← snappy/jittery → smooth/laggy. |
| `MULTIPLAYER_PHYSICS_TEST` | ON = multiplayer physics test mode. OFF = normal. |
| `MULTIPLAYER_SHOW_P2P_PACKET_DEBUG` | ON = show peer-to-peer packet debug. OFF = hidden. |
| `MULTIPLAYER_SHOW_PING` | ON = show ping/latency on screen. OFF = hidden. |
| `MULTIPLAYER_SMOOTHING_FACTOR` | Position smoothing amount. ← raw positions → heavily smoothed. |
| `MULTIPLAYER_SMOOTHING_FACTOR_MAX` | Max smoothing cap. ← light max → heavy max smoothing. |
| `MULTIPLAYER_TARGET_TIME_MULTIPLIER` | Network time prediction multiplier. Affects sync timing. |
| `MULTIPLAYER_TOGGLE_AI_CONTROL` | ON = AI takes over in multiplayer. OFF = player control. |

## Nascar menu (`NASCAR`)

| Runtime control | What it does |
|---|---|
| `NASCAR_AIRBRAKE_ANIMATIONS` | ON = air brake flap animations. OFF = static bodywork. |
| `NASCAR_AISKILL_ARRANGEMENT` | NASCAR AI skill distribution. Changes opponent spread. |
| `NASCAR_BREAKDOWN_HEALTH_BAR` | ON = show breakdown health bar. OFF = hidden. |
| `NASCAR_BREAKDOWN_MAX_PERCENT` | Max breakdown damage percentage. ← small damage cap → full breakdown. |
| `NASCAR_BREAKDOWN_MIN_OPPONENTS` | Min opponents needed for breakdowns. ← happens in small fields → needs big fields. |
| `NASCAR_BREAKDOWN_OPPONENTS` | ON = AI opponents can break down. OFF = indestructible AI. |
| `NASCAR_BREAKDOWN_OPPONENT_THRESHOLD` | AI breakdown damage threshold. ← breaks easily → takes heavy damage to break. |
| `NASCAR_BREAKDOWN_PLAYER` | ON = player car can break down. OFF = player is indestructible. |
| `NASCAR_BREAKDOWN_PLAYER_THRESHOLD` | Player breakdown damage threshold. ← breaks easily → tough. |
| `NASCAR_COLLISION_AILOSS_STEERING` | AI steering loss after collision. ← no effect → heavy steering loss. |
| `NASCAR_COLLISION_AILOSS_THINKING` | AI thinking delay after collision. ← instant recovery → dazed after hit. |
| `NASCAR_COLLISION_ASSISTSLOSS_PERCENT_BRAKING` | Brake assist loss on collision. ← keeps assists → loses brake assist. |
| `NASCAR_COLLISION_ASSISTSLOSS_PERCENT_STEERING` | Steering assist loss on collision. ← keeps assists → loses steering assist. |
| `NASCAR_COLLISION_ASSISTSLOSS_PERCENT_TRACTION` | Traction assist loss on collision. ← keeps TC → loses traction control. |
| `NASCAR_COLLISION_ASSISTSLOSS_TIME` | How long assists stay degraded after hit. ← instant recovery → long penalty. |
| `NASCAR_COLLISION_MAXIMPACT` | Max collision force. ← soft contacts → devastating impacts. |
| `NASCAR_COLLISION_MINIMPACT` | Min collision threshold. ← every tap registers → only hard hits count. |
| `NASCAR_COLLISION_MININTENSITY` | Min collision intensity for damage. ← gentle bumps damage → only big hits. |
| `NASCAR_COLLISION_PUSHOUTMULTIPLIER_ANGULAR` | Spin force on collision. ← no spin → heavy spin. |
| `NASCAR_COLLISION_PUSHOUTMULTIPLIER_LINEAR` | Push force on collision. ← no push → heavy push. |
| `NASCAR_COLLISION_STEERINGLOSS` | Steering loss on collision. ← no effect → can't steer after hit. |
| `NASCAR_DISABLE_PACING_CAR` | ON = no pace car. OFF = pace car active. |
| `NASCAR_FULL_ASSISTS_TARGET_SKILL` | AI skill target with full assists. Changes difficulty scaling. |
| `NASCAR_NET_ANIMATION` | ON = network-synced animations. OFF = local-only animations. |
| `NASCAR_NIGHT_TRACK_SHADOWS` | ON = shadows on night tracks. OFF = no night shadows. |
| `NASCAR_SKILL_VARIANCE` | AI skill variation. ← all same skill → wide skill spread. |
| `NASCAR_SKILL_VARIANCE_FALLOFF_MAX` | Max skill variance falloff. Changes how skill spreads over race. |
| `NASCAR_SKILL_VARIANCE_FALLOFF_MIN` | Min skill variance falloff. Changes how skill spreads over race. |
| `NASCAR_SKILL_VARIANCE_INTERVAL` | How often AI skill variance changes. ← constant → periodic shifts. |
| `NASCAR_SLIPSTREAMING_ACCELERATION_CHANGE` | NASCAR draft speed boost. ← small boost → big draft boost. |
| `NASCAR_SLIPSTREAMING_AUDIO_ENGINE_RPM_INCREASE_MAX` | Max engine RPM increase sound in draft. ← subtle → dramatic. |
| `NASCAR_SLIPSTREAMING_AUDIO_ENGINE_RPM_INCREASE_MIN` | Min engine RPM increase sound in draft. ← none → some baseline. |
| `NASCAR_SLIPSTREAMING_AUDIO_ENGINE_VOLUME_MAX` | Max engine volume in draft. ← quiet → loud. |
| `NASCAR_SLIPSTREAMING_AUDIO_ENGINE_VOLUME_MIN` | Min engine volume in draft. ← silent → audible. |
| `NASCAR_SLIPSTREAMING_AUDIO_LOW_PASS_FILTER` | Draft audio low-pass filter. ← unfiltered → muffled in draft. |
| `NASCAR_SLIPSTREAMING_CAMERA_DISTANCE_DELAY` | Camera pull-back delay in NASCAR draft. ← instant → gradual. |
| `NASCAR_SLIPSTREAMING_CAMERA_DISTANCE_MULTIPLIER` | Camera pull-back in NASCAR draft. ← subtle → dramatic zoom out. |
| `NASCAR_SLIPSTREAMING_CAMERA_FOV_DELAY` | FOV change delay in NASCAR draft. ← instant → gradual. |
| `NASCAR_SLIPSTREAMING_CAMERA_FOV_MULTIPLIER` | FOV widening in NASCAR draft. ← subtle → dramatic fish-eye. |
| `NASCAR_SLIPSTREAMING_DEBUG_RENDER_EFFECT_VALUES` | ON = show draft effect debug values. OFF = hidden. |
| `NASCAR_SLIPSTREAMING_DEBUG_RENDER_VOLUME` | ON = show draft volume debug. OFF = hidden. |
| `NASCAR_SLIPSTREAMING_DELAY_BETWEEN_SWITCHING` | Delay between draft target switches. ← instant → slow switching. |
| `NASCAR_SLIPSTREAMING_EFFECT_LENGTH` | NASCAR draft cone length. ← short zone → long zone. |
| `NASCAR_SLIPSTREAMING_EFFECT_WIDTH` | NASCAR draft cone width. ← narrow → wide. |
| `NASCAR_SLIPSTREAMING_EFFECT_WIDTH_CENTRE` | NASCAR draft center width. ← narrow core → wide core. |
| `NASCAR_SLIPSTREAMING_ENABLED` | ON = NASCAR drafting active. OFF = no draft. |
| `NASCAR_SLIPSTREAMING_ENABLE_BLUE_HUD_SPEED` | ON = blue speed indicator when in draft. OFF = normal HUD. |
| `NASCAR_SLIPSTREAMING_MAXIMUM_SPEED` | Max speed for draft effect. ← caps early → works at high speed. |
| `NASCAR_SLIPSTREAMING_MINIMUM_SPEED` | Min speed for draft. ← drafts at low speed → needs high speed. |
| `NASCAR_SLIPSTREAMING_PUSH_BOOST_EFFECT` | Push draft boost amount. ← small → big boost when pushing car ahead. |
| `NASCAR_SLIPSTREAMING_SMOOTHING_DELAY` | Draft effect smoothing. ← instant on/off → gradual fade in/out. |
| `NASCAR_SLIPSTREAMING_STACK_EFFECT_ENABLED` | ON = stacked drafting (multi-car trains). OFF = single-car draft only. |
| `NASCAR_SLIPSTREAMING_TOP_SPEED_CHANGE` | Top speed change while drafting. ← small increase → big speed boost. |
| `NASCAR_TUTORIAL_CAMERA_SPLINE` | ON = tutorial camera follows spline path. OFF = default camera. |
| `NASCAR_USESTARTSPLINE` | ON = use race start spline for grid. OFF = default grid positions. |

## Network menu (`NETWORK`)

| Runtime control | What it does |
|---|---|
| `NETWORK_PROFILING_ON` | ON = network latency/bandwidth monitoring. OFF = hidden. |

## Particle menu (`PARTICLE`)

| Runtime control | What it does |
|---|---|
| `PARTICLE_CAST_SHADOW` | ON = particles cast shadows. OFF = shadowless particles. |
| `PARTICLE_CAST_SHADOW_PREVIEW` | ON = preview particle shadow settings. OFF = normal. |
| `PARTICLE_CAST_SHADOW_TEX_SIZE` | Particle shadow map size. ← low quality → high quality (slower). |
| `PARTICLE_DEPTH` | ON = particles use depth buffer (proper occlusion). OFF = always on top. |
| `PARTICLE_LIGHTING` | ON = particles receive scene lighting. OFF = self-lit particles. |
| `PARTICLE_NORMAL_MAP` | ON = normal-mapped particles (3D look). OFF = flat particles. |
| `PARTICLE_SCALE` | Particle effect size. ← tiny/invisible → huge exaggerated sparks and dust. |
| `PARTICLE_SHADOW_MAP_VERTEX_PIXEL` | Particle shadow precision. ← vertex-level → pixel-level. |
| `PARTICLE_SOFT_FADE` | ON = particles soft-fade at edges (no hard clipping). OFF = hard edges. |
| `PARTICLE_SPHERICAL` | ON = spherical particle billboarding. OFF = camera-facing only. |
| `PARTICLE_SYSTEM_ENABLED` | ON = particle system active. OFF = no particles anywhere. |
| `PARTICLE_SYSTEM_ENABLE_EMITTERS` | ON = particle emitters active. OFF = no new particles spawn. |
| `PARTICLE_SYSTEM_FRUSTUM_CULL_EMITTERS` | ON = cull off-screen particle emitters. OFF = simulate all. |
| `PARTICLE_SYSTEM_OPTIMIZE` | ON = particle system optimizations. OFF = unoptimized (debug). |
| `PARTICLE_SYSTEM_TEST` | ON = particle test mode. OFF = normal. |

## Party menu (`PARTY`)

| Runtime control | What it does |
|---|---|
| `PARTY_PLAY` | ON = party play mode (local multiplayer features). OFF = solo mode. |

## Partyplay menu (`PARTYPLAY`)

| Runtime control | What it does |
|---|---|
| `PARTYPLAY_FORCE_PLAYERS` | Force party play player count. Overrides detected players. |

## Pause menu (`PAUSE`)

| Runtime control | What it does |
|---|---|
| `PAUSE_BLUR` | ON = blurs the game behind the pause menu. OFF = clear view when paused. |

## PBR menu (`PBR`)

| Runtime control | What it does |
|---|---|
| `PBR_AMBIENT_LIGHTING` | ON = PBR ambient lighting. OFF = no ambient in PBR. |
| `PBR_AMBIENT_OCCLUSION` | ON = PBR ambient occlusion (shadows in crevices). OFF = flat. |
| `PBR_AMBIENT_OCCLUSION_VERTEX` | ON = vertex-level AO. OFF = per-pixel AO only. |
| `PBR_DIFFUSE_LIGHTING` | ON = PBR diffuse lighting (surface color response). OFF = no diffuse. |
| `PBR_DIRECT_LIGHTING` | ON = PBR direct lighting (sunlight). OFF = no direct light. |
| `PBR_ENV_MAP_DYNAMIC` | ON = dynamic environment maps (live reflections). OFF = static. |
| `PBR_ENV_MAP_DYNAMIC_BLUR` | ON = blur dynamic env maps. OFF = sharp dynamic reflections. |
| `PBR_ENV_MAP_DYNAMIC_MENU` | ON = dynamic env maps in menus. OFF = static menu reflections. |
| `PBR_ENV_MAP_HIGH_DETAIL` | ON = high-detail environment maps. OFF = low-detail (faster). |
| `PBR_ENV_MAP_MIX` | Environment map blend factor. ← more static → more dynamic reflections. |
| `PBR_ENV_MAP_MONTE_CARLO` | ON = Monte Carlo env map sampling (accurate, slow). OFF = fast approximation. |
| `PBR_FORCE_EVERYTHING` | ON = force PBR on all materials. OFF = only PBR-flagged materials. |
| `PBR_NORMAL_MAP` | ON = normal maps active (surface detail). OFF = flat surfaces. |
| `PBR_PLANAR_REFLECTIONS` | ON = planar reflections (wet road, glass). OFF = no planar reflections. |
| `PBR_PREVIEW_FINAL_ENV_MAP` | ON = preview final environment map. OFF = normal view. |
| `PBR_PREVIEW_MIP_LEVEL` | Env map mip level to preview. ← sharp → blurry (rougher surface). |
| `PBR_PREVIEW_MIX_ENV_MAP` | Preview env map blend. ← static → dynamic. |
| `PBR_PREVIEW_WATER_REFLECTION` | ON = preview water reflection settings. OFF = normal. |
| `PBR_REALTIME_CAR_SHADOW_MAPS` | ON = real-time car shadow maps (accurate shadows). OFF = baked/blob shadows. |
| `PBR_REFLECTION_PROBES` | ON = reflection probe system active. OFF = no localized reflections. |
| `PBR_SHADOW_DEBUG_PREVIEW` | ON = shadow map debug view. OFF = normal shadows. |
| `PBR_SHADOW_NEAREST_LINEAR_VSM` | ON = variance shadow maps (soft edges). OFF = hard shadow edges. |
| `PBR_SHADOW_PCF_DITHER` | ON = dithered PCF shadows (softer). OFF = clean shadow edges. |
| `PBR_SHADOW_SIZE` | Shadow map resolution. ← low quality (blocky) → high quality (sharp). |
| `PBR_SPECULAR_LIGHTING` | ON = PBR specular highlights (shiny spots). OFF = no specular. |

## Photo Mode menu (`PHOTO`)

| Runtime control | What it does |
|---|---|
| `PHOTO_MODE_ENABLED` | ON = enables photo mode button in pause menu. OFF = hidden. |

## Physics menu (`PHYSICS`)

| Runtime control | What it does |
|---|---|
| `PHYSICS_AERO_SCALE` | Downforce. ← no aero (floaty at speed) → massive downforce (planted at speed). |
| `PHYSICS_SUSPENSION_SCALE` | Suspension stiffness. ← soft (body roll, bouncy) → stiff (flat, responsive). |
| `PHYSICS_TYRE_GRIP_SCALE` | Tire grip. ← ice rink (no grip, slide everywhere) → glue (infinite grip, never slide). |

## Player menu (`PLAYER`)

| Runtime control | What it does |
|---|---|
| `PLAYER_TO_FOLLOW` | Which player index the camera follows. 0 = you. |

## Post menu (`POST`)

| Runtime control | What it does |
|---|---|
| `POST_BRIGHTNESS_B` | Blue brightness. ← darker blues → brighter blues. |
| `POST_BRIGHTNESS_G` | Green brightness. ← darker greens → brighter greens. |
| `POST_BRIGHTNESS_R` | Red brightness. ← darker reds → brighter reds. |
| `POST_CONTRAST_B` | Blue contrast. ← flat blues → punchy blues. |
| `POST_CONTRAST_G` | Green contrast. ← flat greens → punchy greens. |
| `POST_CONTRAST_R` | Red contrast. ← flat reds → punchy reds. |
| `POST_SUN_BRIGHTNESS_B` | Sun-facing blue brightness. Changes warm/cool balance toward sun. |
| `POST_SUN_BRIGHTNESS_G` | Sun-facing green brightness. Changes warm/cool balance toward sun. |
| `POST_SUN_BRIGHTNESS_R` | Sun-facing red brightness. Changes warm/cool balance toward sun. |
| `POST_SUN_CONTRAST_B` | Sun-facing blue contrast. Changes punch toward sun. |
| `POST_SUN_CONTRAST_G` | Sun-facing green contrast. Changes punch toward sun. |
| `POST_SUN_CONTRAST_R` | Sun-facing red contrast. Changes punch toward sun. |

## Projection menu (`PROJECTION`)

| Runtime control | What it does |
|---|---|
| `PROJECTION_MODE` | Rendering projection mode. Changes perspective/orthographic. |

## PVS menu (`PVS`)

| Runtime control | What it does |
|---|---|
| `PVS_DEBUG` | ON = shows visibility culling debug (what's rendered vs hidden). OFF = hidden. |
| `PVS_DEBUGRENDER` | ON = PVS debug rendering overlay. OFF = hidden. |
| `PVS_FADE_TEST` | Fade distance test. ← objects fade close → objects stay visible far away. |

## Quests menu (`QUESTS`)

| Runtime control | What it does |
|---|---|
| `QUESTS_ENABLE_BROKEN_STEERING` | ON = quest 'broken steering' challenge active. OFF = normal steering. |
| `QUESTS_STEERING_OFFSET` | Broken steering offset amount. ← small drift → heavy pull to one side. |
| `QUESTS_STEERING_RANDOM_TIME_MAX` | Max time between steering glitches. ← frequent → rare. |
| `QUESTS_STEERING_RANDOM_TIME_MIN` | Min time between steering glitches. ← constant → occasional. |

## Race menu (`RACE`)

| Runtime control | What it does |
|---|---|
| `RACE_METRICS_EXTERNAL` | ON = send race metrics externally. OFF = internal only. |

## Reduce menu (`REDUCE`)

| Runtime control | What it does |
|---|---|
| `REDUCE_BUFFER_BINDS` | ON = optimize buffer binding calls. OFF = unoptimized (debug). |

## Rendering menu (`RENDER`)

| Runtime control | What it does |
|---|---|
| `RENDER_BEFORE_UPDATE` | ON = render frame before physics update (can cause 1-frame lag). OFF = normal. |
| `RENDER_CARS` | ON = car models visible. OFF = invisible cars (still have physics). |
| `RENDER_CAR_SHADOWS` | ON = cars cast shadows on track. OFF = no car shadows. |
| `RENDER_CAR_SHADOWS_BATCH` | ON = batch car shadow rendering (faster). OFF = individual shadow passes. |
| `RENDER_CAR_WHEELS` | ON = wheel models visible. OFF = invisible wheels. |
| `RENDER_CLOUDS` | ON = cloud rendering. OFF = clear sky (no clouds). |
| `RENDER_COCKPIT` | ON = cockpit interior visible in first-person. OFF = no interior geometry. |
| `RENDER_COMBINE_RENDER_CALLS` | ON = combine draw calls (faster). OFF = individual calls (debug). |
| `RENDER_CUBEMAPS` | ON = environment cubemaps. OFF = no cubemap reflections. |
| `RENDER_DEBUG_INFO` | ON = debug text overlay (FPS, memory, render stats). OFF = hidden. |
| `RENDER_DISABLE_PVS` | ON = disable visibility culling (draw everything). OFF = normal culling. |
| `RENDER_DISABLE_PVS_FADE` | ON = disable PVS fade transitions. OFF = normal fade in/out. |
| `RENDER_DISABLE_PVS_FADE_IN_CUBEMAP` | ON = disable PVS fade in cubemap renders. OFF = normal. |
| `RENDER_DISTORT_CHROMATIC_ABERRATION` | ON = chromatic aberration effect (RGB edge split). OFF = clean image. |
| `RENDER_DISTORT_C_ABERATION_AMOUNT` | Chromatic aberration strength. ← subtle → heavy RGB split at edges. |
| `RENDER_DISTORT_FISHEYE_AMOUNT_X` | Fisheye horizontal distortion. ← none → heavy barrel distortion. |
| `RENDER_DISTORT_FISHEYE_AMOUNT_Y` | Fisheye vertical distortion. ← none → heavy barrel distortion. |
| `RENDER_DISTORT_FISHEYE_CENTRE_X` | Fisheye center X position. ← left → right. |
| `RENDER_DISTORT_FISHEYE_CENTRE_Y` | Fisheye center Y position. ← bottom → top. |
| `RENDER_DISTORT_VIGNETTE_FALLOFF` | Vignette darkness at edges. ← no vignette → heavy dark edges. |
| `RENDER_DISTORT_VIGNETTE_SIZE` | Vignette size. ← small bright center → large bright center. |
| `RENDER_DISTORT_ZOOM` | Post-process zoom. ← zoomed out → zoomed in. |
| `RENDER_DYNAMIC_SKIDS` | ON = dynamic skid marks generated in real time. OFF = static/none. |
| `RENDER_ENABLED` | Master render switch. OFF = nothing renders at all (black screen). |
| `RENDER_ENABLE_FISHEYE` | ON = fisheye lens distortion effect. OFF = normal perspective. |
| `RENDER_ENABLE_FISHEYE_SHADER` | ON = use GPU shader for fisheye. OFF = CPU distortion. |
| `RENDER_ENV_MAP` | ON = environment map reflections. OFF = flat paint. |
| `RENDER_FLAT_SHADOWS` | ON = simple blob shadows. OFF = normal shadow maps. |
| `RENDER_FOG` | ON = distance fog. OFF = no fog (clear to horizon). |
| `RENDER_FRUSTRUM_CULL_IN_CUBEMAP` | ON = frustum cull during cubemap render. OFF = draw all. |
| `RENDER_FULL_SCREEN_FX` | ON = full-screen post effects active. OFF = no post-FX. |
| `RENDER_GAMEMODE_HELPER` | ON = gamemode helper overlay. OFF = hidden. |
| `RENDER_GLOW` | ON = bloom/glow on bright surfaces. OFF = no bloom. |
| `RENDER_GPU_PROFILING` | ON = GPU performance overlay (draw call counts, frame time). OFF = hidden. |
| `RENDER_HDR` | ON = high dynamic range lighting (brighter brights, darker darks). OFF = flat. |
| `RENDER_HUD` | ON = speedometer, position, lap display. OFF = clean screen, no UI. |
| `RENDER_HUD_BATCH_DYNAMIC_TEXT` | ON = batch HUD text rendering (faster). OFF = individual draws. |
| `RENDER_HUD_INGAME_INPUT` | ON = show input overlay on HUD (steering/throttle bars). OFF = hidden. |
| `RENDER_INFO_ENABLED` | ON = render info debug overlay (draw calls, triangles). OFF = hidden. |
| `RENDER_INFO_MAX_RENDER_CALLS` | Max render calls to display in info. Limits debug output. |
| `RENDER_INVERTED` | ON = inverts all colors (negative image). OFF = normal colors. |
| `RENDER_LENS_FLARE` | ON = sun lens flare effect. OFF = clean image facing sun. |
| `RENDER_LENS_FLARE_BLOOM_FALLOFF_ANGLE` | Lens flare bloom falloff. ← tight angle → wide angle bloom. |
| `RENDER_LENS_FLARE_BLOOM_MINIMUM_SIZE` | Min lens flare bloom size. ← invisible → always visible. |
| `RENDER_LENS_FLARE_BLOOM_PEAK_ANGLE` | Lens flare peak angle from sun. ← tight → wide peak zone. |
| `RENDER_LENS_FLARE_BLOOM_PEAK_SIZE` | Lens flare size. ← small subtle flare → huge blinding flare. |
| `RENDER_LENS_FLARE_LENS_FOV_ANGLE` | Lens flare FOV response. ← narrow → wide FOV. |
| `RENDER_LENS_FLARE_OCCLUSION_QUERY` | ON = flare occluded by geometry. OFF = flare always visible. |
| `RENDER_LENS_FLARE_OQ_MIN_FRAME_DELAY` | Occlusion query min delay frames. ← fast response → delayed response. |
| `RENDER_LENS_FLARE_PRIMARY_FLARE_EFFECT_RATE` | Primary flare animation speed. ← slow → fast shimmer. |
| `RENDER_LENS_FLARE_PRIMARY_FLARE_EFFECT_RATE_ROLL` | Primary flare roll rate. ← slow rotation → fast rotation. |
| `RENDER_LENS_FLARE_PRIMARY_OVERRIDE_SCALE` | Primary flare size override. ← small → large. |
| `RENDER_LENS_FLARE_PRIMARY_SCALE` | Primary flare scale. ← small → large. |
| `RENDER_LENS_FLARE_PRIMARY_TILT_AMOUNT` | Primary flare tilt. ← no tilt → heavy tilt with camera. |
| `RENDER_LENS_FLARE_RELOAD` | ON = reload lens flare assets. Self-clearing trigger. |
| `RENDER_LENS_FLARE_SECONDARY_OVERRIDE_SCALE` | Secondary flare size override. ← small → large. |
| `RENDER_LENS_FLARE_SECONDARY_SCALE` | Secondary flare scale. ← small ghosts → large ghosts. |
| `RENDER_LENS_FLARE_SUN_POSITION_X` | Override sun X for lens flare. Moves flare source. |
| `RENDER_LENS_FLARE_SUN_POSITION_Y` | Override sun Y for lens flare. Moves flare source. |
| `RENDER_LENS_FLARE_SUN_POSITION_Z` | Override sun Z for lens flare. Moves flare source. |
| `RENDER_LIGHT_BEAMS` | ON = volumetric light shafts (god rays). OFF = no light beams. |
| `RENDER_MATERIAL_DEBUG_COLOUR` | ON = replace material with debug color. OFF = normal materials. |
| `RENDER_MAX_SORTED_OBJECTS_TO_RENDER` | Max sorted transparent objects. ← fewer → more (slower). |
| `RENDER_MOTION_BLUR` | ON = blur when moving fast. OFF = sharp image at all speeds. |
| `RENDER_PARTICLES` | ON = sparks, dust, tire smoke. OFF = no particle effects. |
| `RENDER_PARTICLE_FX` | ON = particle effects visible. OFF = no particle rendering. |
| `RENDER_PARTICLE_SCALE` | Particle size. ← tiny sparks/dust → huge exaggerated effects. |
| `RENDER_PAUSE_MENU` | ON = render pause menu overlay. OFF = no pause UI. |
| `RENDER_PIXEL_THRESHOLD_OVERRIDE` | Pixel threshold for detail rendering. ← render everything → skip small objects. |
| `RENDER_POST_CARS` | ON = post-process effects on cars. OFF = raw car rendering. |
| `RENDER_POST_PROCESS` | ON = color grading, vignette, post-FX. OFF = raw unprocessed image. |
| `RENDER_POST_TRACK` | ON = post-process effects on track. OFF = raw track rendering. |
| `RENDER_PREVIEW_DEFERRED_LIGHTMAP` | ON = preview deferred lightmap. OFF = normal rendering. |
| `RENDER_PVS_FADE_TEST` | ON = PVS fade distance test mode. OFF = normal. |
| `RENDER_RACE_UI` | ON = race UI elements visible. OFF = no race UI. |
| `RENDER_REFLECTIONS` | ON = reflective surfaces (car paint, wet track). OFF = matte everything. |
| `RENDER_SHADOWS` | ON = shadows render. OFF = no shadows (everything uniformly lit). |
| `RENDER_SKID_MARKS` | ON = tire marks on track from braking/drifting. OFF = clean track. |
| `RENDER_SKID_MARK_DEFERRED_LIGHTMAP` | ON = deferred lightmap on skid marks. OFF = unlit skids. |
| `RENDER_SKY` | ON = skybox renders. OFF = no sky (void behind track). |
| `RENDER_SSAO` | ON = ambient occlusion (shadows in crevices/corners). OFF = flatter lighting. |
| `RENDER_SYSTEM_SAFE_AREA` | ON = show system safe area overlay (notch/home bar). OFF = hidden. |
| `RENDER_TRACK` | ON = track surface visible. OFF = invisible track (cars float in void). |
| `RENDER_TRACK_PROPS` | ON = track-side objects visible (fences, signs, stands). OFF = empty trackside. |
| `RENDER_TRANSPARENT` | ON = transparent objects (glass, etc.) render. OFF = invisible. |
| `RENDER_USE_4K_SKY` | ON = 4K sky textures. OFF = standard resolution sky. |
| `RENDER_WEATHER` | ON = rain, spray, wet track effects. OFF = always dry conditions. |
| `RENDER_WIREFRAME` | ON = everything draws as wireframe triangles (no textures). OFF = normal. |

## Result menu (`RESULT`)

| Runtime control | What it does |
|---|---|
| `RESULT_UPLOAD_DIAGNOSTICS` | ON = upload race result diagnostics. OFF = local only. |

## Road menu (`ROAD`)

| Runtime control | What it does |
|---|---|
| `ROAD_IN_GAME_DETAIL_FREQ` | Road surface detail frequency. ← less detail → more surface variation. |

## Rolling menu (`ROLLING`)

| Runtime control | What it does |
|---|---|
| `ROLLING_START_FRONT_CAR_NODE_OFFSET` | Front car position offset in rolling start. Adjusts grid spacing. |
| `ROLLING_START_LATERAL_OFFSET` | Side-to-side offset in rolling start. ← left → right. |
| `ROLLING_START_NODES_BETWEEN_CARS` | Gap between cars in rolling start. ← tight pack → wide spacing. |
| `ROLLING_START_OVERRIDE` | ON = use custom rolling start settings. OFF = default. |
| `ROLLING_START_WARMUP_TOPSPEED` | Rolling start pace speed. ← slow parade → fast rolling start. |

## Shaders menu (`SHADERS`)

| Runtime control | What it does |
|---|---|
| `SHADERS_1_LUMA_BIAS` | Speed-based luminance bias. ← dark at speed → bright at speed. |
| `SHADERS_1_LUMA_SCALE` | Speed-based luminance scale. ← subtle effect → dramatic effect. |
| `SHADERS_1_RADIAL_SPEED_FACTOR` | Radial speed blur factor. ← no radial blur → heavy tunnel effect. |
| `SHADERS_2_DOF_CAM_APERTURE` | Depth of field aperture. ← everything sharp → shallow focus (blurry background). |
| `SHADERS_2_DOF_DEBUG` | ON = show DOF debug regions. OFF = normal. |
| `SHADERS_2_DOF_EIGHTH_BLUR_PART` | DOF 1/8 resolution blur weight. Technical: blur quality layer. |
| `SHADERS_2_DOF_HALF_BLUR_PART` | DOF 1/2 resolution blur weight. Technical: blur quality layer. |
| `SHADERS_2_DOF_QUARTER_BLUR_PART` | DOF 1/4 resolution blur weight. Technical: blur quality layer. |
| `SHADERS_3_MOTION_BLUR_ACCUMULATION` | Motion blur frame accumulation. ← subtle blur → heavy motion smear. |
| `SHADERS_4_BLOOM_EIGHTH_PART` | Bloom 1/8 resolution weight. ← less → more wide bloom. |
| `SHADERS_4_BLOOM_HALF_PART` | Bloom 1/2 resolution weight. ← less → more fine bloom. |
| `SHADERS_4_BLOOM_MULTIPLIER` | Bloom intensity multiplier. ← no bloom → intense glow. |
| `SHADERS_4_BLOOM_QUARTER_PART` | Bloom 1/4 resolution weight. ← less → more medium bloom. |
| `SHADERS_4_BLOOM_TINT_B` | Bloom blue tint. ← neutral → blue-tinted glow. |
| `SHADERS_4_BLOOM_TINT_G` | Bloom green tint. ← neutral → green-tinted glow. |
| `SHADERS_4_BLOOM_TINT_R` | Bloom red tint. ← neutral → red/warm glow. |
| `SHADERS_ALPHA_DITHER_ENABLED` | ON = dithered alpha (screen-door transparency). OFF = standard alpha. |
| `SHADERS_CAMERA_MOTION_BLUR` | ON = camera motion blur effect. OFF = sharp camera movement. |
| `SHADERS_CAMERA_MOTION_BLUR_STRENGTH` | Camera blur strength. ← subtle → heavy blur on camera pan. |
| `SHADERS_CAMERA_MOTION_BLUR_Z_DISCARD` | Depth threshold for camera blur. ← blur everything → only blur far objects. |
| `SHADERS_CAR_SH_DIFFUSE_ONLY` | ON = car uses only spherical harmonics diffuse. OFF = full lighting. |
| `SHADERS_CAR_SH_LIGHTING` | ON = spherical harmonics lighting on cars. OFF = standard lighting. |
| `SHADERS_DOF_BLUR_TYPE` | Depth of field blur algorithm. Changes blur quality/style. |
| `SHADERS_DOF_DEBUG` | ON = show DOF zones (near/focus/far). OFF = normal. |
| `SHADERS_DOF_FAR_BLUR_OFFSET` | DOF far blur start offset. ← blur close behind focus → blur only far background. |
| `SHADERS_DOF_FAR_FOCUS_OFFSET` | DOF far focus end. ← tight focus → deep focus range. |
| `SHADERS_DOF_NEAR_BLUR_OFFSET` | DOF near blur start. ← blur right in front → blur only very close objects. |
| `SHADERS_DOF_NEAR_FOCUS_OFFSET` | DOF near focus start. ← tight focus → wide focus range. |
| `SHADERS_FORCE_DOF_BUTTON_ON` | ON = force DOF always active. OFF = triggered by game events. |
| `SHADERS_FORCE_MATERIAL` | Force material ID. Overrides all materials with one debug material. |
| `SHADERS_FULL_SCREEN_EFFECT` | Full screen shader effect ID. Changes post-process look. |
| `SHADERS_FXAA_ENABLED` | ON = FXAA anti-aliasing (smooth edges). OFF = aliased/jagged edges. |
| `SHADERS_FXAA_QUALITY` | FXAA quality level. ← fast/rough → slow/smooth. |
| `SHADERS_MIPMAP_BIAS` | Texture mipmap bias. ← sharper (shimmer risk) → blurrier (stable). |
| `SHADERS_MSAA_ENABLED` | ON = MSAA anti-aliasing (hardware). OFF = no MSAA. |
| `SHADERS_MSAA_RESOLVE_DIRECTLY` | ON = resolve MSAA directly to backbuffer. OFF = intermediate buffer. |
| `SHADERS_SCREEN_SCALE` | Render resolution scale. ← lower resolution → higher resolution (slower). |
| `SHADERS_TRACK_HEADLIGHT` | ON = track headlight shader effect. OFF = no track illumination from headlights. |
| `SHADERS_VARIABLE_MIPMAP_BIAS` | ON = variable mipmap bias per material. OFF = global bias only. |

## Display menu (`SHOW`)

| Runtime control | What it does |
|---|---|
| `SHOW_CC_AND_EVENT_IDS` | ON = shows internal event/challenge IDs on screen. OFF = hidden. |
| `SHOW_FPS` | ON = framerate counter on screen. OFF = hidden. |
| `SHOW_NDT_WORM` | ON = network timing waveform on screen. OFF = hidden. |

## Skids menu (`SKIDS`)

| Runtime control | What it does |
|---|---|
| `SKIDS_ENABLE_FADING` | ON = skid marks fade over time. OFF = permanent skids. |
| `SKIDS_VISIBILE_FADE_SPEED` | Skid mark visual fade speed. ← slow fade → fast fade. |
| `SKIDS_WET_FADE_SPEED` | Wet skid mark fade speed. ← slow dry → fast dry. |

## Sound menu (`SOUND`)

| Runtime control | What it does |
|---|---|
| `SOUND_3D_ENABLED` | ON = 3D positional audio (hear cars pass L/R). OFF = flat stereo. |
| `SOUND_AMBIENCE_VOLUME` | Ambient sounds (crowd, wind, birds). ← silent → loud. |
| `SOUND_BACKFIRE_DUCKING` | Engine ducking on backfire. ← no duck → engine drops volume on backfire. |
| `SOUND_BACKFIRE_DUCKING_ATTACK_MS` | Backfire duck attack time. ← instant → gradual. |
| `SOUND_BACKFIRE_DUCKING_DECAY_MS` | Backfire duck decay time. ← instant recovery → gradual. |
| `SOUND_BACKFIRE_DUCKING_RELEASE_MS` | Backfire duck release time. ← instant → gradual fade back. |
| `SOUND_BACKFIRE_DUCKING_SUSTAIN_PERCENTAGE` | Backfire duck sustain level. ← full duck → partial duck. |
| `SOUND_BACKFIRE_VOLUME` | Backfire pop volume. ← quiet → loud pops. |
| `SOUND_BACKFIRE_VOLUME_OPPONENT` | Opponent backfire volume. ← quiet → loud. |
| `SOUND_COLLISION_VOLUME` | Crash sound volume. ← quiet impacts → loud crashes. |
| `SOUND_CUSTOMISATION_VOLUME` | Customization menu sounds. ← quiet → loud. |
| `SOUND_CUTSCENE_VOLUME` | Cutscene volume. ← quiet → loud. |
| `SOUND_DAMAGE_VOLUME` | Damage crunch volume. ← quiet → loud. |
| `SOUND_DRAFT_ENGINE_DUCKING` | Engine volume drop in slipstream. ← no change → engine gets quiet in draft. |
| `SOUND_DRAFT_ENGINE_DUCK_IN_TIME` | Draft engine duck fade-in time. ← instant → gradual. |
| `SOUND_DRAFT_ENGINE_DUCK_OUT_TIME` | Draft engine duck fade-out time. ← instant → gradual. |
| `SOUND_DRAFT_SLIPSTREAM_FADE_TIME` | Slipstream whoosh fade time. ← instant → gradual. |
| `SOUND_EFFECTS_VOLUME` | Sound effects master volume. ← quiet → loud. |
| `SOUND_ENGINE_PITCH_VAR_MAX` | Max engine pitch variation. ← consistent → varied pitch. |
| `SOUND_ENGINE_PITCH_VAR_MIN` | Min engine pitch variation. ← no variation → some baseline variation. |
| `SOUND_ENGINE_VOLUME` | Your engine volume. ← quiet → roaring. |
| `SOUND_ENGINE_VOLUME_OPPONENT` | Opponent engine volume. ← quiet → loud opponents. |
| `SOUND_GEARS_VOLUME` | Gear shift sound volume. ← silent shifts → loud clunks. |
| `SOUND_GLOBAL_VOLUME` | Master volume for everything. ← silent → max volume. |
| `SOUND_MASTER_VOLUME` | Master volume. ← silent → full volume. |
| `SOUND_MIX_TYPE` | Audio mix preset. Changes overall balance between engines, effects, ambient. |
| `SOUND_OVERRUN_POP_CHANCE` | Exhaust overrun pop probability. ← rare → constant popping on decel. |
| `SOUND_OVERRUN_POP_INTERVAL` | Time between overrun pops. ← rapid-fire → spaced out. |
| `SOUND_OVERRUN_RPM_THRESHOLD` | RPM for overrun pops. ← pops at low RPM → only at high RPM. |
| `SOUND_RACEUI_VOLUME` | Race UI sound effects volume. ← quiet → loud. |
| `SOUND_RAMP_ACCEL_BLEND_TIME` | Throttle-on sound blend time. ← instant → gradual engine rise. |
| `SOUND_RAMP_DECEL_BLEND_TIME` | Throttle-off sound blend time. ← instant → gradual engine fall. |
| `SOUND_RAMP_IDLE_BLEND_TIME` | Engine idle blend time. ← instant → gradual to idle. |
| `SOUND_SUPERCHARGER_VOLUME` | Supercharger whine volume. ← quiet → screaming supercharger. |
| `SOUND_SUPERCHARGER_VOLUME_OPPONENT` | Opponent supercharger volume. ← quiet → loud. |
| `SOUND_TRACTION_CUE` | ON = traction loss audio cue. OFF = no tire squeal warning. |
| `SOUND_TRACTION_CUE_MAX_PITCH` | Traction cue max pitch. ← low squeal → high-pitched screech. |
| `SOUND_TRACTION_CUE_MAX_VOLUME` | Traction cue max volume. ← quiet → loud screech. |
| `SOUND_TRACTION_CUE_MIN_PITCH` | Traction cue min pitch. ← rumble → higher start pitch. |
| `SOUND_TRACTION_CUE_MIN_VOLUME` | Traction cue min volume. ← silent → some baseline squeal. |
| `SOUND_TRACTION_CUE_TRIGGER_PERCENTAGE` | Traction loss % to trigger squeal. ← squeals easily → only heavy slides. |
| `SOUND_TRANSMISSION_VOLUME` | Gearbox whine volume. ← quiet → loud transmission. |
| `SOUND_TYRES_VOLUME` | Tire sound volume. ← quiet → loud tire roar. |
| `SOUND_UI_VOLUME` | Menu UI sound effects volume. ← quiet → loud. |

## Steering menu (`STEERING`)

| Runtime control | What it does |
|---|---|
| `STEERING_ATTENUATION_FREQ` | Steering attenuation frequency. Changes how steering input is filtered. |

## Suspension menu (`SUSPENSION`)

| Runtime control | What it does |
|---|---|
| `SUSPENSION_CENTRE_OF_MASS_OFFSET_FWD` | Center of mass front/back. ← rearward (oversteer) → forward (understeer). |
| `SUSPENSION_CENTRE_OF_MASS_OFFSET_RIGHT` | Center of mass left/right. ← left bias → right bias. |
| `SUSPENSION_CENTRE_OF_MASS_OFFSET_UP` | Center of mass height. ← low (stable, less roll) → high (more roll, tippy). |
| `SUSPENSION_DAMPING_PITCH` | Pitch damping (nose dive/lift). ← soft (nose dives under braking) → stiff (flat). |
| `SUSPENSION_DAMPING_ROLL` | Roll damping. ← soft (heavy body roll) → stiff (flat in corners). |
| `SUSPENSION_ESPORT` | ON = esport suspension model. OFF = standard. |
| `SUSPENSION_LOGGING` | ON = log suspension data to console. OFF = quiet. |
| `SUSPENSION_PITCH_BCK` | Rear pitch amount under acceleration. ← no squat → heavy rear squat. |
| `SUSPENSION_PITCH_FWD` | Front pitch amount under braking. ← no dive → heavy nose dive. |
| `SUSPENSION_PREVIEW_EXTREME` | ON = preview extreme suspension settings. OFF = normal preview. |
| `SUSPENSION_R3` | ON = R3-era suspension model. OFF = newer model. |
| `SUSPENSION_R4_ACCFORCE` | R4 acceleration force on suspension. ← no effect → heavy squat. |
| `SUSPENSION_R4_ANGULAR_DAMPING` | R4 angular damping. ← rotates freely → resists rotation. |
| `SUSPENSION_R4_ANTIROLLBARS` | R4 anti-roll bar stiffness. ← no roll bars → stiff bars (flat cornering). |
| `SUSPENSION_R4_ANTIROLLBARS_LOGGING` | ON = log anti-roll bar data. OFF = quiet. |
| `SUSPENSION_R4_BUMPSTOPS` | R4 bump stop stiffness. ← soft bottoming → hard stops. |
| `SUSPENSION_R4_BUMPSTOP_RESTITUTION` | R4 bump stop rebound. ← absorbs energy → bounces back. |
| `SUSPENSION_R4_COMPRESSION_DAMPING` | R4 compression damping. ← soft → stiff on compression. |
| `SUSPENSION_R4_INTERPOLATE_NORMALS` | ON = smooth surface normals for suspension. OFF = raw geometry. |
| `SUSPENSION_R4_SIDEFORCE` | R4 lateral force on suspension. ← no effect → heavy cornering load. |
| `SUSPENSION_R4_SPRINGS` | R4 spring rate. ← soft ride → stiff ride. |
| `SUSPENSION_R4_TORQUES_AFFECT_YAW` | ON = suspension torques affect car rotation. OFF = isolated. |
| `SUSPENSION_ROLL_MAX` | Max body roll angle. ← minimal roll → extreme body roll. |
| `SUSPENSION_SPRING_DAMPED` | Spring damping coefficient. ← bouncy → well-damped. |
| `SUSPENSION_SPRING_DAMPED_BUMP_STOP` | Bump stop damping. ← hard bottoming → cushioned stop. |
| `SUSPENSION_STIFFNESS_PITCH` | Pitch spring stiffness. ← soft (nose dives) → stiff (stays level). |
| `SUSPENSION_STIFFNESS_ROLL` | Roll spring stiffness. ← soft (body roll) → stiff (flat cornering). |
| `SUSPENSION_TWEAK_MODE` | ON = suspension tweak mode (live editing). OFF = locked. |
| `SUSPENSION_UPGRADED_DAMPING_PITCH` | Upgraded parts pitch damping. ← soft → stiff. |
| `SUSPENSION_UPGRADED_DAMPING_ROLL` | Upgraded parts roll damping. ← soft → stiff. |
| `SUSPENSION_UPGRADED_STIFFNESS_PITCH` | Upgraded parts pitch stiffness. ← soft → stiff. |
| `SUSPENSION_UPGRADED_STIFFNESS_ROLL` | Upgraded parts roll stiffness. ← soft → stiff. |
| `SUSPENSION_UPGRADE_RATIO` | Suspension upgrade effect ratio. ← small upgrade effect → big upgrade effect. |
| `SUSPENSION_VISUAL_WHEEL_TRAVEL_AMOUNT` | Visual wheel travel range. ← subtle movement → dramatic suspension travel. |
| `SUSPENSION_WEIGHT_SHIFT_BCK` | Weight shift rearward under acceleration. ← none → heavy transfer. |
| `SUSPENSION_WEIGHT_SHIFT_FWD` | Weight shift forward under braking. ← none → heavy transfer. |
| `SUSPENSION_WEIGHT_SHIFT_LR` | Lateral weight shift in corners. ← none → heavy transfer. |

## Texture menu (`TEXTURE`)

| Runtime control | What it does |
|---|---|
| `TEXTURE_TYPE_COLORIZATION` | ON = texture colorization override. OFF = default textures. |

## Timetrial menu (`TIMETRIAL`)

| Runtime control | What it does |
|---|---|
| `TIMETRIAL_MAXDAMAGE` | Max damage in time trial. ← low cap → heavy damage allowed. |
| `TIMETRIAL_PENALTY_MAXDAMAGE` | Time penalty for max damage in time trial. ← small penalty → huge penalty. |

## Track menu (`TRACK`)

| Runtime control | What it does |
|---|---|
| `TRACK_FORCE_LOD_0DEVICEDEFAULT_1LOW_2HIGH` | Force track LOD. 0=device default, 1=low, 2=high. |

## Transmission menu (`TRANSMISSION`)

| Runtime control | What it does |
|---|---|
| `TRANSMISSION_MANUAL_REVERSAL_SPEED_LIMIT_KPH` | Speed limit for manual reverse. ← slow reverse → fast reverse. |
| `TRANSMISSION_REPORTING` | ON = log transmission data to console. OFF = quiet. |
| `TRANSMISSION_STANDARD_RACE_GEAR_SELECTION` | Standard race gear selection mode. Changes auto-shift behavior. |
| `TRANSMISSION_TORSIONAL_VIBRATION` | ON = drivetrain torsional vibration effect. OFF = smooth. |
| `TRANSMISSION_TORVIB_CYCLE_COUNT` | Torsional vibration cycles. ← few oscillations → many oscillations. |
| `TRANSMISSION_TORVIB_DECEL_ENGINE_PITCH_AMPLITUDE` | Engine pitch wobble on decel. ← subtle → heavy pitch variation. |
| `TRANSMISSION_TORVIB_DECEL_ENGINE_VOLUME_AMPLITUDE` | Engine volume wobble on decel. ← subtle → heavy volume variation. |
| `TRANSMISSION_TORVIB_DECEL_PITCH_AMPLITUDE` | Overall pitch wobble on decel. ← subtle → heavy. |
| `TRANSMISSION_TORVIB_DECEL_VOLUME_AMPLITUDE` | Overall volume wobble on decel. ← subtle → heavy. |
| `TRANSMISSION_TORVIB_ENGINE_CYCLE_COUNT` | Engine vibration cycles. ← few → many. |
| `TRANSMISSION_TORVIB_ENGINE_PITCH_AMPLITUDE` | Engine pitch vibration amount. ← smooth → wobbly pitch. |
| `TRANSMISSION_TORVIB_ENGINE_VOLUME_AMPLITUDE` | Engine volume vibration amount. ← smooth → pulsing volume. |
| `TRANSMISSION_TORVIB_MAX_FREQ` | Max torsional vibration frequency. ← slow wobble → fast vibration. |
| `TRANSMISSION_TORVIB_MIN_FREQ` | Min torsional vibration frequency. ← very slow → moderate wobble. |
| `TRANSMISSION_TORVIB_PITCH_AMPLITUDE` | Overall torsional pitch wobble. ← subtle → heavy. |
| `TRANSMISSION_TORVIB_VOLUME_AMPLITUDE` | Overall torsional volume wobble. ← subtle → heavy. |

## Visual menu (`VISUAL`)

| Runtime control | What it does |
|---|---|
| `VISUAL_PROFILER_BREAKDOWN` | ON = show per-pass profiler breakdown. OFF = summary only. |
| `VISUAL_PROFILER_FIXED_FRAMES` | ON = fixed frame count for profiler. OFF = rolling average. |
| `VISUAL_PROFILER_G` | Visual profiler GPU time graph. Technical display. |
| `VISUAL_PROFILER_G_B` | Visual profiler GPU batch graph. Technical display. |
| `VISUAL_PROFILER_G_P` | Visual profiler GPU pass graph. Technical display. |
| `VISUAL_PROFILER_HITCOUNT` | ON = show profiler hit counts. OFF = hidden. |
| `VISUAL_PROFILER_MAX_FRAMES` | Max frames in profiler history. ← short history → long history. |
| `VISUAL_PROFILER_MODE` | Profiler display mode. Changes what metrics are shown. |
| `VISUAL_PROFILER_OPACITY` | Profiler overlay opacity. ← transparent → opaque. |
| `VISUAL_PROFILER_R` | Visual profiler render time graph. Technical display. |
| `VISUAL_PROFILER_R_C` | Visual profiler render calls graph. Technical display. |
| `VISUAL_PROFILER_R_D` | Visual profiler render draw graph. Technical display. |
| `VISUAL_PROFILER_R_G` | Visual profiler render GPU graph. Technical display. |
| `VISUAL_PROFILER_R_HDR_P` | Visual profiler HDR pass graph. Technical display. |
| `VISUAL_PROFILER_R_M` | Visual profiler render memory graph. Technical display. |
| `VISUAL_PROFILER_R_O` | Visual profiler render objects graph. Technical display. |
| `VISUAL_PROFILER_R_P` | Visual profiler render pass graph. Technical display. |
| `VISUAL_PROFILER_R_R` | Visual profiler render resolution graph. Technical display. |
| `VISUAL_PROFILER_R_S` | Visual profiler render state graph. Technical display. |
| `VISUAL_PROFILER_R_T` | Visual profiler render triangles graph. Technical display. |
| `VISUAL_PROFILER_TARGET_FRAMERATE` | Profiler target framerate line. ← low target → high target. |
