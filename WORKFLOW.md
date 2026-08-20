# How RR3 DevOps Was Built

## The short version

RR3 DevOps was built by taking the final iOS version of *Real Racing 3*, figuring out what still existed inside it after the game was shut down, and turning the useful parts into a working tool people can actually use.

This was not a one-prompt AI project and it was not a random collection of hex edits. It was a focused three-day reverse-engineering effort: inspect the game, test an idea, watch what happened on a real phone, keep the parts that held up, and throw out the parts that did not.

Claude Code was the main working environment. It was used to run many focused investigations in parallel, inspect code and data, write candidate implementations, and help organize the results. The project lead set the goals, decided what to investigate, supplied the game and devices, challenged bad conclusions, and tested the builds on actual hardware. AI made the loop much faster; it did not replace the loop.

## Where the project began

RR3 DevOps did **not** create offline *Real Racing 3* from nothing. The community package it builds on had already solved the biggest preservation problem: it made the final iOS app accept a local asset cache after EA's servers were shut down. That upstream work is credited in [Provenance](docs/PROVENANCE.md).

The new question was different:

> What else is still inside the final game binary, and can it be made useful without pretending unsupported features work?

The answer was much more interesting than expected. The final build still contains a large amount of developer-facing code: debug references, menu definitions, rendering controls, vehicle controls, and hundreds of live engine settings called tweakables.

## How the investigation worked

The work was divided into small, answerable questions instead of asking one agent to "figure out the game." The Claude Code session dispatched 17 focused investigations covering topics such as:

- what the existing community package already did;
- how the game stored settings and saved data;
- where the hidden developer and cheat systems appeared in the binary;
- whether suspicious debug switches belonged to the game or to bundled ad/analytics software;
- how the game chose graphics settings for different devices;
- how to add an injected iOS overlay; and
- how the runtime settings were structured in memory.

That task split is why the project moved forward quickly without treating every first guess as fact. One investigation could trace a switch through the code while another checked the menu wiring, another examined the crash, and another looked at the graphics profile.

The practical loop was simple:

1. Find a possible route in the binary.
2. Check what that route actually controls.
3. Build the smallest test that answers the question.
4. Run it on a real iPhone.
5. Keep, revise, or discard the idea based on the result.

Some early ideas crashed. Some switches turned out to belong to third-party ad software, not the game. One apparent build-type change turned out to be a label, not the setting that controlled behavior. Those were not wasted attempts; they prevented broken experiments from becoming part of the public release.

## The important discovery

At first, the goal was to restore the game's own hidden developer menu. The code for that system is still there, and the binary contains a surprising amount of its menu text and internal commands.

But code existing in a release build does not mean the whole feature is ready to turn back on. The original interface appears to depend on pieces that are incomplete or missing in the final retail version. Simply forcing its switches did not produce a complete, usable menu.

That led to the real breakthrough:

> Instead of trying to revive a missing interface, use the live settings system directly and build a new interface around it.

The game keeps a live list of tweakable settings while it runs. RR3 DevOps recovered how that list is laid out in memory, how each setting identifies itself, what type of control it needs, and where its current value lives. The custom UIKit overlay uses that information to show toggles, sliders, values, categories, descriptions, resets, and write verification on a touch screen.

That is why the overlay is more than a hidden-menu launcher. It is a general-purpose harness for the game's own runtime settings.

## What the 4K-quality work involved

The graphics profile was another reverse-engineering problem, not just a “max settings” button. RR3 uses encrypted Engine Device Settings (EDS) files to decide which graphics settings belong to a device profile.

The project recovered the file transformation, built a safe encrypt/decrypt round-trip into the builder, and started from a compatible iPad-derived profile rather than inventing an unknown device identity. That produced the elevated “4K” quality profile without claiming that every scene renders at a literal 3840 x 2160.

The technical details are in [EDS Format and Quality Profile](docs/EDS_FORMAT.md).

## What was tested

The project makes a clear distinction between “we found it,” “we wrote to it,” and “we watched it work.”

- The overlay can find the live settings list, change a selected value, and read that same value back to confirm the write reached the expected location.
- Selected tire, vehicle, rendering, and debug controls were tested on device and produced visible live changes. Tire color, dimensions, and stance changes were among the observed results.
- The production builder checks that it is working against the supported final executable before applying its documented changes.
- The original Firemonkeys developer/ImGui interface is **not** claimed to be fully restored.
- The project does **not** claim that every roughly 847 live settings will visibly affect every scene. Some are conditional, unused, or later overridden by other game code.

That honesty matters. The project proves that the runtime system is wired correctly and useful. It does not pad that into a claim that every internal switch has been behavior-tested.

## How AI was used

Claude Code, with Claude Opus 4.6 in the archived primary session, was used as an engineering environment: it analyzed code, organized parallel tasks, generated and revised implementation candidates, searched for references, and helped turn findings into documentation and tooling.

The human part remained essential. The project lead decided what mattered, supplied context the model could not infer, recognized when a result did not match the real device, asked for deeper analysis instead of accepting a shallow answer, and chose the final design. The agents read and compare faster; the binary and the phone decide what is true.

This workflow is included because it says something important about the project: modern AI can dramatically accelerate reverse engineering when it is directed, challenged, and kept inside a real test loop.

## What to take from this repository

If you are here to play the preserved game, start with the [Deployment Guide](docs/INSTALLATION.md).

If you are here to understand the technical work, start with the [Technical Report](docs/TECHNICAL_REPORT.md), then read [Internal Developer Systems](docs/INTERNAL_DEVELOPER_SYSTEMS.md) and [Runtime Harness](overlay/README.md).

If you are here because you want to build on it, treat the source and documentation as the evidence base. Verify your own build, keep experiments separate from production changes, and report what you observed—not only what a model or a string in a binary suggested.
