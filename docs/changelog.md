---
title: Version history
nav_order: 10
---

# Version history

The newest version is at the top.

## 1.11.1 — 7 September 2026

The **Configure** window was wider than it could be shown, so the help text beside some settings was cut off part way through. That help now sits in paragraphs that wrap to fit. No setting or behaviour changed.

## 1.11.0 — 6 September 2026

- **The activity log moved out of the Indigo Event Log** and into the plugin's own log file, complete and timed as before. It had been writing hundreds of lines a day into the Event Log, with no way to stop it.
- **A new setting, Activity in the Indigo event log,** with a menu item beside it, puts the lines back in the Event Log if you want them there.
- Warnings still go to the Event Log — a deleted device, a device in the settings file that Indigo no longer has, a reading that could not be taken, or a trigger that failed — and so do the notes about renamed devices and variables.

## 1.10.2 — 2 August 2026

The **About Device Activity Monitor** item in the Plugins menu opens this project's page. Nothing else changed.

## 1.10.1 — 21 July 2026

A helper file inside the plugin, shared with my other plugins, was brought up to date. Nothing changed in how the plugin behaves.

## 1.10.0 — 17 July 2026

- **New Test Fire All Group Triggers menu item,** which runs every enabled Group Changed trigger once, so you can check its actions without setting off a sensor.
- **Discover All Devices starts using the new settings file straight away,** and keeps any devices you have added to it yourself.
- **The plugin's settings are in the Configure window** as well as the Plugins menu, with a setting for debug logging.
- **A group with a deleted device in it says so** when it starts, and discovery points out excluded devices that no longer exist.
- **A new install starts with nothing in the activity log** until you run discovery or make a settings file.

## 1.9.13 — 17 July 2026

- The check at start-up gives one summary line, with a separate warning only for each device that is missing.
- Warnings about deleted devices always appear, even with the activity log switched off, and deleting a device that is in a group names the group.
- A device and reading listed twice in the settings file is logged once, with a warning.
- A Group Changed trigger cannot be saved without a group, or with **Save firing device** ticked and no variable picked. Before, it saved and then never ran.
- **Toggle Timestamps in Log** also applies to the lines written by the menu items.
- A device deleted while discovery is running no longer stops it writing the settings file.

## 1.9.12 — 17 July 2026

- **Group triggers ignore housekeeping updates** such as signal strength, battery level and the time a sensor was last heard from, so a Zigbee sensor sending the same message twice no longer sets off an **Any change** trigger twice.
- If one trigger has a problem, the others still run.
- The settings files are written in one go, so a crash cannot leave half a file.
- The switches in the Plugins menu are saved the moment you choose them, rather than when the plugin stops.
- Discovery no longer takes a lock, relay, dimmer or thermostat for a sensor because of its name, so Front Door Lock is not treated as a door sensor.
- The start-up warning for a trigger with a problem says what the problem is.

## 1.9.11 — 17 July 2026

- **Changes to a group's members take effect when you click Save.** Before, they waited until the plugin restarted.
- A mistake in one variable's line in the settings file no longer stops the plugin loading.
- A device name with a quote mark in it no longer breaks the settings file that discovery writes.
- Discovery keeps the variables you log and any wording you have changed, and will not overwrite a settings file it cannot read.
- Two old stand-alone scripts that wrote to a place the plugin no longer reads were removed.

## 1.9.10 — 12 June 2026

Discovery recognises motion and door sensors from the Matter plugin.

## 1.9.9 — 10 June 2026

Housekeeping only. Nothing changed in how the plugin behaves.

## 1.9.8 — 5 June 2026

The warning when a monitored device is deleted now appears — before, a mistake in the code meant it never did. A device line in the settings file with a missing or wrong ID number is skipped with a warning.

## 1.9.7 — 4 June 2026

The lines written by the menu items carry the time to the thousandth of a second.

## 1.9.6 — 25 May 2026

Changing the folder picker in a group's window no longer restarts the group.

## 1.9.5 — 23 May 2026

Three new Plugins menu items switch the activity log, the group triggers and the times at the start of each line on and off, without a restart. Each stays as you leave it.

## 1.9.4 — 14 May 2026

Discovery recognises Aqara presence sensors that also measure temperature, humidity or light, and logs their presence and motion readings separately.

## 1.9.3 — 13 May 2026

The settings file can say which word means on and which means off, for sensors that report words such as `enter` and `leave` rather than on and off.

## 1.9.2 — 13 May 2026

Discovery trusts the Zigbee2MQTT Bridge's record of what each device is, so a leak or temperature sensor is no longer taken for a motion sensor.

## 1.9.1 — 13 May 2026

**Find Contact & Motion Sensors** gives motion sensors MOTION and CLEAR, rather than ON and OFF.

## 1.9.0 — 12 May 2026

The plugin was renamed from **Sensor Monitor** to **Device Activity Monitor**. Indigo sees it as a new plugin, so groups made with Sensor Monitor have to be made again. [Getting started](getting-started.md) explains the move.

## 1.8.1 — 12 May 2026

Groups only come from group devices. The old way of listing groups in the settings file no longer works.

## 1.8.0 — 12 May 2026

Groups became Indigo devices, which you build by picking devices from a list, and each shows how many members it has and which one last set off a trigger.

## 1.7.2 — 12 May 2026

The Group Changed trigger gained **Fire on**, to choose between any change, a device turning on, or a device turning off.

## 1.7.1 — 11 May 2026

The settings files moved from Indigo's **Logs** folder to its **Preferences** folder.

## 1.7.0 — 11 May 2026

New Group Changed trigger, which runs when any device in a group changes, and can note which device set it off in a variable. Groups were listed in the settings file at this point.

## 1.6.0 — 11 May 2026

Discovery uses the Zigbee2MQTT Bridge's record of what each device can sense, so motion sensors are no longer taken for door sensors, and it picks one reading per motion sensor so a movement gives one line rather than several.

## 1.5.9 — 24 March 2026

The published copy was brought up to date with changes made since 1.4. They were not recorded one by one.

## 1.4.0 — 27 February 2026

A Plugins menu with **Discover Devices**, **Find Contact Sensors** and **Reload Config File**.

## 1.3.0 — 27 February 2026

The devices to log are chosen in a settings file.

## 1.2.0 — 27 February 2026

Variables can be logged as well as devices.

## 1.1.0 — 27 February 2026

A check at start-up that every device still exists, a note when a device is renamed, and a warning when one is deleted.

## 1.0.0 — 27 February 2026

The first version.
