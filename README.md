# Device Activity Monitor — Indigo Plugin

**Version**: 1.10.0
**Author**: CliveS
**Platform**: Indigo 2022.1 or later / macOS / Python 3.10+

*Developed and tested on Indigo 2025.2 / Python 3.13. Older Indigo releases that meet the minimum API version above should also work — the API floor is what Indigo's plugin loader actually checks.*
**Plugin ID**: `com.clives.indigoplugin.deviceactivitymonitor`
**GitHub**: <https://github.com/Highsteads/DeviceActivityMonitor>

> v1.9.0 renamed this plugin from **Sensor Monitor** → **Device Activity Monitor**.
> Same lineage — the new name better describes both halves of what it now does:
> per-device change **logging** and group-change custom **triggers**.

## What's new in 1.10.x

1.10.1 (21-Jul-2026) is housekeeping: named log levels now map to the real logging levels — warnings and errors raised through the shared helper had been appearing as plain info lines, so amber and red entries people relied on for diagnosis never showed. Shared-utility refresh: calling the log timestamp filter twice no longer double-stamps every line, and the module imports cleanly outside Indigo.

The 1.9.11 → 1.10.0 releases are the result of a full deep review of the plugin.
The headline fixes: editing a group's members now takes effect immediately (it
used to silently wait for a plugin restart), group triggers no longer double-fire
on Zigbee2MQTT duplicate publishes or radio housekeeping updates, one typo in a
hand-edited config can no longer stop the plugin loading, and re-running
discovery now preserves your variables, custom labels and manually added
entries instead of quietly resetting them. New in 1.10.0: a **Test Fire All
Group Triggers** menu item so you can check your trigger actions without
walking round the house waving at sensors, a Configure dialog for the runtime
toggles, discovery that applies its results immediately, and warnings when a
group still references a deleted device. The test suite has grown from 104 to
143 checks along the way.

---

## Table of contents

- [What it does](#what-it-does)
- [Installation](#installation)
- [Credentials — `IndigoSecrets.py` vs `IndigoSecrets_example.py`](#credentials--indigosecretspy-vs-indigosecrets_examplepy)
- [Quick start in 5 minutes](#quick-start-in-5-minutes)
- [Use cases](#use-cases)
  - [1. Activity logging — passive observer](#1-activity-logging--passive-observer)
  - [2. Single-device direction trigger](#2-single-device-direction-trigger)
  - [3. Multi-sensor "any change" trigger](#3-multi-sensor-any-change-trigger)
  - [4. Multi-sensor "becomes occupied" trigger](#4-multi-sensor-becomes-occupied-trigger)
  - [5. Multi-sensor "becomes empty" trigger](#5-multi-sensor-becomes-empty-trigger)
  - [6. Save which device fired](#6-save-which-device-fired)
  - [7. Combining with conditions and scripts](#7-combining-with-conditions-and-scripts)
  - [8. Variable monitoring](#8-variable-monitoring)
- [Multi-Sensor Trigger — deep dive](#multi-sensor-trigger--deep-dive)
- [Configuration file](#configuration-file)
- [Plugin menu](#plugin-menu)
- [Discovery](#discovery)
- [Log output examples](#log-output-examples)
- [Group device states](#group-device-states)
- [Repository structure](#repository-structure)
- [Migrating from "Sensor Monitor"](#migrating-from-sensor-monitor)
- [Changelog](#changelog)
- [License](#license)

---

## What it does

Device Activity Monitor watches Indigo devices and variables and reacts to their state
changes two complementary ways:

1. **Logs** changes to the Indigo event log with millisecond-precision timestamps and
   custom on/off labels (`Front Door OPEN`, `Lux Level: 450 -> 520`).
2. **Fires custom triggers** when any device in a named **Group** changes state, with
   an optional direction filter (`any change` / `becomes ON/OPEN` / `becomes OFF/CLOSED`).

**The two halves are independent and can each be turned on or off at runtime** from the
**Plugins → Device Activity Monitor** menu — use just the change-logger, just the group
triggers, or both. The `[HH:MM:SS.mmm]` timestamp prefix on the logger's output is also
its own toggle, so you can keep the logging on but rely on Indigo's column timestamp
alone if the inline prefix is noise for you. All three toggles persist across plugin
restarts. See [Plugin menu](#plugin-menu) below.

Groups are first-class Indigo devices managed via a rich two-list Add/Remove ConfigUI —
no JSON editing required. The plugin replaces both:

- A pile of one-trigger-per-device "Device State Changed" triggers
- The older **Group Change Listener** plugin (Morris's) — this plugin is based on
  Group Change Listener and updated to a dual-list Add/Remove ConfigUI

…with one subscription, one config file for logging, and one Indigo Group device per
trigger group.

---

## Installation

1. Download `Device_Activity_Monitor.indigoPlugin.zip` from the
   [latest release](https://github.com/Highsteads/DeviceActivityMonitor/releases)
2. Unzip and double-click `Device_Activity_Monitor.indigoPlugin` — Indigo will
   prompt to install
3. **Plugins → Manage Plugins** → enable **Device Activity Monitor**
4. The plugin auto-creates its config folder at
   `<install>/Preferences/Plugins/com.clives.indigoplugin.deviceactivitymonitor/`
5. Open the Indigo Event Log — you should see a one-line startup summary with
   the loaded device count (the full diagnostic banner is available on demand
   via **Plugins → Device Activity Monitor → Show Plugin Info**)

---

## Credentials — `IndigoSecrets.py` vs `IndigoSecrets_example.py`

This plugin, like every CliveS Indigo plugin, reads sensitive values from one
shared master file:

`/Library/Application Support/Perceptive Automation/IndigoSecrets.py`

| File | Purpose | Real data? | Committed to GitHub? |
|------|---------|------------|----------------------|
| `IndigoSecrets.py` | Working file the plugin reads at runtime. Keep a backup in a password manager. | YES | **NO** — listed in `.gitignore` |
| `IndigoSecrets_example.py` | Template only — empty placeholders. Shipped in the plugin bundle. | NO | YES |

If you don't have `IndigoSecrets.py`, copy `IndigoSecrets_example.py` out of
the plugin bundle into `/Library/Application Support/Perceptive Automation/`,
rename it to `IndigoSecrets.py`, and fill in your values. Or skip the file
altogether and type the values into the plugin's configuration dialog — where
both are set, `IndigoSecrets.py` wins.

If neither source supplies a value the plugin needs, it logs an ERROR naming
the key and telling you to either fill in the matching field or add the key to
`IndigoSecrets.py`.

**Note for this plugin specifically**: Device Activity Monitor reads no external
APIs and needs no credentials in normal use. The `IndigoSecrets_example.py`
file is shipped for ecosystem consistency only — there is nothing to fill in
unless you extend the plugin yourself.

---

## Quick start in 5 minutes

**Goal**: get a Pushover notification when *any* of three motion sensors in
the living room detects movement.

1. **Create the group device**
   - **Devices → New Device**
   - Type = "Device Activity Monitor → Device Activity Monitor Group"
   - Name it "Living Room Presence"
   - **Show devices from**: pick `Living Room` (or `(All folders)`)
   - In **Available devices**: ⌘-click your 3 motion sensors
   - Click **Add to Group ↓**
   - Save

2. **Create the trigger**
   - **New Trigger** → Type = "Device Activity Monitor: Group Changed"
   - **Group**: pick "Living Room Presence  (3 members)"
   - **Fire on**: "Any device becomes ON / OPEN / detected"
   - **Actions tab**: add your Pushover action

3. **Done**. Wave at any of the three sensors — Pushover fires. The trigger
   does NOT re-fire while the sensor stays active, and does NOT fire on the
   off transition (because of the direction filter).

That's the headline workflow. The rest of this README covers the variants.

---

## Use cases

### 1. Activity logging — passive observer

You want a single log line every time a sensor changes state, so the event log
becomes a usable timeline. No triggers, no actions — just clean logging.

1. **Plugins → Device Activity Monitor → Discover All Devices**
2. Open `device_activity_monitor_config.json` and uncomment / add the lines
   you want logged
3. **Plugins → Device Activity Monitor → Reload Config File**

Each configured state gets a log line of the form:

    [14:23:01.452] Front Door Contact OPEN
    [14:25:33.104] Hall PIR Occupancy ON

### 2. Single-device direction trigger

Indigo has a built-in "Device State Changed" trigger for this, but if you'd
rather pick by a friendly name from a list of Group devices:

1. Create a group with one member (the device)
2. Trigger → Fire on = "Any device becomes ON / OPEN / detected" (or the OFF variant)

Useful when you want a consistent "group" mental model across single and
multi-device cases.

### 3. Multi-sensor "any change" trigger

Fire whenever any member of the group changes any state. Equivalent to
Morris's Group Change Listener with no filter.

- Group: any number of devices
- Trigger → Fire on = "Any change (default)"

Use this for log-spam-style "something happened in this area" reactions where
direction doesn't matter.

### 4. Multi-sensor "becomes occupied" trigger

Fire once when the *first* member transitions from off to on. Doesn't re-fire
while any other member is also active.

- Group: 3 presence sensors in a room
- Trigger → Fire on = "Any device becomes ON / OPEN / detected"

Common uses:
- Turn on the lights when *anyone* enters a multi-sensor room
- Pushover "movement in the garage" without 3 separate triggers
- Start a "room occupied" timer

### 5. Multi-sensor "becomes empty" trigger

Fire only on the off transition.

- Group: same room sensors
- Trigger → Fire on = "Any device becomes OFF / CLOSED / clear"

Common uses:
- Start a delay timer to turn lights off when the last sensor clears
- Trigger an "armed away" routine when a contact closes

> Pairing: use one group with two triggers — one direction-filtered to
> "becomes ON" and one to "becomes OFF". Each fires only on the relevant
> edge.

### 6. Save which device fired

If multiple devices in a group could be the source, capture the firing
device's name to an Indigo variable so your actions can use it:

1. Trigger ConfigUI → tick **Save firing device**
2. Pick a variable
3. **Save value**: "Device Name" or "Device ID"
4. In your action, reference the variable with `%%v:NN%%` or read it in a
   Python action script

Examples:
- Pushover body: "Movement detected by %%v:firing_sensor%%"
- Script: branch based on which front-of-house contact was triggered

### 7. Combining with conditions and scripts

The trigger doesn't have to fire blindly. Indigo's standard Conditions and
Actions tabs are fully available:

- **Conditions tab**: "only fire between sunset and sunrise" / "only when
  the alarm is armed" / "only when nobody is home"
- **Actions tab**: chain to action groups, Python scripts, action collections,
  send-to-variables, control pages, etc.

For complex multi-room logic, fire one trigger from each group and have the
target action group read all the various states it cares about.

### 8. Variable monitoring

Add Indigo variables to the `variables[]` section of
`device_activity_monitor_config.json`:

    "variables": [
      {"id": 241032502, "name": "Lux_Level", "label": "Lux Level"}
    ]

Output:

    [14:26:10.512] Lux Level: 450 -> 520

---

## Multi-Sensor Trigger — deep dive

The headline feature. This section walks through every option in detail.

### Step 1: create the Group device

**Devices → New Device** → Type = "Device Activity Monitor → Device Activity
Monitor Group".

You get a dialog with these fields:

| Field | What it does |
|-------|--------------|
| **Show devices from** | Folder filter for the Available list. `(All folders)` shows everything; `(Root)` shows un-foldered devices; named folders narrow to that folder's contents |
| **Available devices** | Multi-select list of devices NOT yet in this group. Cmd-click to select multiple, then click Add. Refreshes as the folder filter changes |
| **Add to Group ↓** | Moves the Available-list selection into the Members list |
| **Current group members** | Multi-select list of devices currently in the group. Devices the bridge has since deleted show as `<missing device id NN>` so you can clean them up |
| **↑ Remove from Group** | Moves the Members-list selection back to "available" |

To **edit** a group later, double-click the Group device — same dialog, same
flow. There is no JSON editing.

To **delete** a group, right-click → Delete (standard Indigo flow). Any
triggers wired to the deleted group will log a warning on next plugin reload
that they reference a now-missing group.

Each Group device shows `N members` as its display state in the Indigo device
list.

### Step 2: create the Trigger

**New Trigger** → Type = "Device Activity Monitor: Group Changed".

| Field | What it does |
|-------|--------------|
| **Group** | Dropdown of all Group devices, each labelled with its name and live member count. This is Indigo's native device picker filtered to `self.damGroup` — folder tree, search, the lot |
| **Fire on** | Direction filter (see next section) |
| **Save firing device** | Tick to capture which member triggered the event into an Indigo variable |
| **Save to variable** | (only when Save firing device is ticked) target variable |
| **Save value** | (only when Save firing device is ticked) "Device Name" or "Device ID" |

### Step 3: pick the direction filter

The **Fire on** menu has three options. They look at the device's `onState`
attribute before and after the change.

| Option | Fires when… |
|--------|-------------|
| **Any change** (default) | Any *meaningful* state on a group member changes. Housekeeping states (`lastSeen`, link quality, battery, RSSI) are ignored as of v1.9.12, so duplicate radio publishes and signal-strength churn no longer fire it |
| **Any device becomes ON / OPEN / detected** | A member's `onState` flips from `False` to `True`. Edge-triggered: doesn't re-fire while it stays on. Use for occupancy, door-opens, alarms |
| **Any device becomes OFF / CLOSED / clear** | A member's `onState` flips from `True` to `False`. Edge-triggered: doesn't re-fire while it stays off. Use for "last sensor cleared" timers, door closes |

The directional options only fire on `onState` transitions, so they ignore
chatty value updates (temperature, illuminance, etc.) entirely.

### Step 4: chain to actions

Standard Indigo Actions tab. The trigger fires the same way as any built-in
Indigo trigger — Pushover, action groups, scripts, control pages all work
identically.

If you ticked **Save firing device**, your variable now contains the name or
ID of the device that triggered the firing — reference it via `%%v:NN%%` in
text fields, or read it directly in Python script actions.

### Diagnostic states on the Group device

Whenever a trigger fires for a Group device, the plugin also writes these
states on the Group device itself (useful for control pages or other
triggers):

- `memberCount` — number of devices in the group
- `lastFiringDevice` — name of the device that triggered the most recent fire
- `lastFiringTime` — `YYYY-MM-DD HH:MM:SS`
- `lastFiringDirection` — `activated` / `deactivated` / `changed`
- `status` — display string, e.g. "3 members"

---

## Configuration file

Lives at:

    <install>/Preferences/Plugins/com.clives.indigoplugin.deviceactivitymonitor/
    ├── device_activity_monitor_config.json   ← edit this
    └── device_discovery.json                 ← generated by Discover Devices

`<install>` resolves via `indigo.server.getInstallFolderPath()` so the path
follows your active Indigo version automatically.

### Format

```json
{
  "_usage": "Lines starting with # are ignored. Reload plugin after changes.",
  "excluded_ids": [],
  "devices": [
    {"id": 123456789, "name": "Front Door",  "state": "onState", "label": "Front Door",  "on_text": "OPEN", "off_text": "CLOSED"},
    {"id": 987654321, "name": "Basin mmWave","state": "pirDetection", "label": "PIR"},
    {"id": 987654321, "name": "Basin mmWave","state": "presence",     "label": "mmWave Presence"}
  ],
  "variables": [
    {"id": 241032502, "name": "Lux_Level", "label": "Lux Level"}
  ]
}
```

### Conventions

- `#` at the start of a line disables that entry. Use this to comment out a
  device without deleting the line
- Trailing commas before `]` or `}` are silently cleaned up
- Multiple rows with the same `id` monitor multiple states on one device
  (e.g. PIR and mmWave on a multi-state sensor)
- After saving, reload via **Plugins → Device Activity Monitor → Reload
  Config File** — no plugin restart required

### Field reference

| Field      | Required | Description                                                                  |
|------------|----------|------------------------------------------------------------------------------|
| `id`       | Yes      | Indigo device or variable ID (integer)                                       |
| `name`     | No       | For your reference only — never used by the code                             |
| `state`    | Yes      | `"onState"` reads `device.onState`; any other name reads from `device.states`|
| `label`    | No       | Log text shown after the device name (defaults to `name`)                    |
| `on_text`  | No       | Log text when state is True (default `ON`)                                   |
| `off_text` | No       | Log text when state is False (default `OFF`)                                 |

### Groups are NOT in this file

As of v1.8.0, groups live as `damGroup` Indigo devices, not in the JSON file.
This file is logging-only.

---

## Plugin menu

Under **Plugins → Device Activity Monitor**:

| Item | What it does |
|------|--------------|
| **Discover All Devices (generate config file)** | Scans every Indigo device, classifies contact / motion / presence candidates using device type, Zigbee2MQTT capability flags, and name keywords. Writes `device_discovery.json` (full inventory) and a fresh `device_activity_monitor_config.json`, then applies it immediately. Preserves `excluded_ids`, your variables section, custom labels and manually added entries across re-runs, and refuses to overwrite a config file it cannot parse |
| **Find Contact & Motion Sensors** | One-shot log dump of all sensor candidates with ready-to-paste config entries — useful for a quick check without regenerating the whole config |
| **Reload Config File** | Re-reads the JSON and re-validates without a full plugin restart. Use after editing the config file by hand |
| **Test Fire All Group Triggers** | Fires every enabled Group Changed trigger once so you can verify the wired-up actions without physically tripping a sensor |
| **Toggle Device Change Log (on/off)** | Flips per-device / per-variable event-log lines on or off. When OFF the plugin still subscribes to changes (group triggers keep working) but writes nothing to the event log |
| **Toggle Group Change Triggers (on/off)** | Flips group-device-driven custom triggers on or off. When OFF, `damGroup` device changes no longer fire `damGroupChange` events even if matching triggers are enabled |
| **Toggle Timestamps in Log (on/off)** | Strips or restores the `[HH:MM:SS.mmm]` prefix on every line the plugin writes to the event log. Indigo's own column timestamp is unaffected |
| **Show Plugin Info** | Prints the startup banner on demand, including current state of the three toggles above |

All three toggles persist across plugin restarts (stored in `pluginPrefs` as
`logEnabled` / `groupEnabled` / `timestampEnabled`) and default ON. As of
v1.10.0 they are also available in the standard Configure dialog
(**Plugins → Device Activity Monitor → Configure**), alongside a debug-logging
checkbox — changes apply immediately on save.

---

## Discovery

Discovery uses a layered classifier that gets the right answer even on
generic Zigbee2MQTT devices that publish stub fields they don't physically
have:

1. **Z2M ownerProps** (authoritative when available): `has_contact`,
   `has_occupancy`, `has_presence`, `has_pir`
2. **deviceTypeId hints**: `z2mContactSensor` → contact, `z2mOccupancySensor`
   → motion
3. **Motion-keyword veto**: if the device name contains `motion`, `pir`,
   `presence`, `occupancy`, `mmwave`, `radar`, it can't be a contact sensor
4. **State-name match**: `contact` / `doorSensor` / `windowSensor` → contact;
   `occupancy` / `pirDetection` / `presence` / `motion` / `motionDetected`
   → motion
5. **Name-keyword match**: `contact`, `door`, `window`, etc. — gated on the
   device's Indigo class, so actuators (relays, dimmers, locks, thermostats)
   are never classified as sensors by name alone. "Front Door Lock" stays a
   lock

To **permanently exclude** a device from discovery output, add its ID to the
`excluded_ids` array in the config file. Subsequent re-discovery runs will
respect the exclusion and leave that device commented out. Discovery also
flags any excluded ids whose devices no longer exist so the list stays clean.

To **add a sensor that discovery missed**, just add a line manually to
`devices[]` — re-discovery keeps it in a dedicated "Manually added entries"
section, along with any custom labels or on/off text you have set on the
generated entries.

---

## Log output examples

```
[14:23:01.452] Hall PIR Occupancy ON
[14:23:01.891] Basin Sensor mmWave Presence ON
[14:25:33.104] Front Door Contact OPEN
[14:25:41.230] Front Door Contact CLOSED
[14:26:10.512] Lux Level: 450 -> 520
[14:30:00.001] [Device Activity Monitor] Device renamed: 'Test Sensor' -> 'Hall PIR' (ID: 99887766)
[14:31:05.774] [Device Activity Monitor] WARNING - Monitored device deleted: 'Hall PIR' (ID: 99887766)
```

---

## Group device states

Each `damGroup` device exposes:

| State                  | Type    | Updated when                                |
|------------------------|---------|---------------------------------------------|
| `memberCount`          | Integer | Group device is saved / reloaded            |
| `status`               | String  | Display state — e.g. `"3 members"`         |
| `lastFiringDevice`     | String  | A trigger wired to this group fires        |
| `lastFiringTime`       | String  | `YYYY-MM-DD HH:MM:SS` of last fire          |
| `lastFiringDirection`  | String  | `activated` / `deactivated` / `changed`     |

Useful for control pages ("Living Room presence last activity: 2 minutes
ago") or for chaining one group's activity into another trigger's condition.

---

## Repository structure

```
README.md                                                  ← this file (GitHub displays this)
Device_Activity_Monitor.indigoPlugin/
├── Contents/
│   ├── Info.plist
│   └── Server Plugin/
│       ├── plugin.py                       ← main plugin code + ConfigUI callbacks
│       ├── Devices.xml                     ← damGroup device type
│       ├── Events.xml                      ← Group Changed trigger
│       ├── MenuItems.xml                   ← Plugins menu
│       ├── PluginConfig.xml                ← runtime toggles + debug logging
│       ├── plugin_utils.py                 ← on-demand info banner helper
│       ├── test_plugin.py                  ← 143 tests, runs without Indigo
│       └── IndigoSecrets_example.py        ← credential template (unused — ecosystem standard)
```

---

## Migrating from "Sensor Monitor"

If you ever installed a pre-v1.9.0 release of this plugin under the old name:

1. Disable **Sensor Monitor** in Indigo Manage Plugins
2. Delete the old bundle at `<install>/Plugins/Sensor_Monitor.indigoPlugin/`
3. Install Device Activity Monitor v1.9.0
4. Move `<install>/Preferences/Plugins/com.clives.indigoplugin.sensormonitor/` →
   `<install>/Preferences/Plugins/com.clives.indigoplugin.deviceactivitymonitor/`
5. Rename `sensor_monitor_config.json` → `device_activity_monitor_config.json`
   inside that folder
6. Old `smGroup` devices are not auto-migrated to `damGroup` — re-create
   groups via Devices → New Device

(For me specifically: that migration was done at the moment of the rename, so
this section exists only for completeness if I ever do a clean reinstall.)

---

## Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.10.0  | 2026-07-17 | Deep-review feature batch — Test Fire All Group Triggers menu item, discovery applies its results immediately and preserves manually added entries, Configure dialog for the runtime toggles, stale group-member and stale-exclusion warnings, fallback config now ships empty |
| 1.9.13  | 2026-07-17 | Deep-review polish — one-line startup validation summary, deletion warnings always shown (and now cover group members), duplicate config entries skipped, triggers can no longer be saved without a group, timestamp toggle honoured on menu output |
| 1.9.12  | 2026-07-17 | Deep-review robustness — group triggers ignore housekeeping-state churn (no more double-fires on Zigbee2MQTT duplicate publishes), one failing trigger no longer blocks the rest, atomic config writes, toggle flips survive a crash, locks/relays no longer offered as sensors by name |
| 1.9.11  | 2026-07-17 | Deep-review fixes — group membership edits apply immediately (previously needed a plugin restart), a config typo can no longer stop the plugin loading, device names with quotes no longer corrupt the generated config, re-discovery preserves your variables and custom labels |
| 1.9.10  | 2026-06-12 | Discovery recognises Matter (indigo-matter) presence and contact sensors |
| 1.9.9   | 2026-06-10 | Fleet audit — lint cleanup and CI gate |
| 1.9.8   | 2026-06-05 | Estate bug-sweep — guarded config id parse, merged duplicate deviceDeleted |
| 1.9.7   | 2026-06-04 | Millisecond-precision timestamps on menu and discovery output |
| 1.9.5   | 2026-05-23 | Three runtime toggle menu items — Device Change Log, Group Change Triggers, Timestamps in Log. Each is independent, persists across restarts, defaults ON |
| 1.9.4   | 2026-05-14 | Discovery correctly classifies multi-capability Aqara presence sensors (PS-S04D, FP1 etc.) using `pirDetection` / `presenceDetectionOptions` state names |
| 1.9.3   | 2026-05-13 | Added `on_value` / `off_value` config keys for explicit value matching on string-typed states (e.g. presenceEvent `enter`/`leave`) |
| 1.9.2   | 2026-05-13 | Trust Z2M `has_*` flags to exclude non-motion devices in discovery |
| 1.9.1   | 2026-05-12 | Minor discovery and config fixes |
| 1.9.0   | 2026-05-12 | **Renamed** Sensor Monitor → Device Activity Monitor (bundle ID, device type id, event id, config filename all changed; legacy migration code stripped) |
| 1.8.1   | 2026-05-12 | Dropped JSON-groups backward-compat path; damGroup devices the sole source of truth |
| 1.8.0   | 2026-05-12 | Groups are now first-class Indigo devices with Add/Remove ConfigUI |
| 1.7.2   | 2026-05-12 | Direction filter (any/activated/deactivated) on group triggers |
| 1.7.1   | 2026-05-11 | Moved config files from `Logs/` to `Preferences/` |
| 1.7.0   | 2026-05-11 | Group-change custom triggers (JSON-defined, since superseded by damGroup devices) |
| 1.6.0   | 2026-05-11 | Z2M-aware sensor classifier (uses ownerProps `has_*` flags) |
| 1.5.9   | 2026-02-27 | Sync live plugin (multiple features since v1.4.0) |
| 1.4.0   | 2026-02-27 | Plugin menu — Discover Devices, Find Contact Sensors, Reload Config File |
| 1.3.0   | 2026-02-27 | JSON config file support |
| 1.2.0   | 2026-02-27 | Variable monitoring |
| 1.1.0   | 2026-02-27 | Startup validation, rename detection, deletion warning |
| 1.0.0   | 2026-02-27 | Initial release |

## Authors & licence

Vibed into existence by **CliveS**, who knew what he wanted, argued until he got it, and tested it on a real house. Typed at inhuman speed by **Claude** (Anthropic), who mostly did as it was told.

© 2026 CliveS · [MIT licence](LICENSE) — copy it, fork it, bend it, break it, fix it, ship it. If it breaks, you get to keep both pieces.
