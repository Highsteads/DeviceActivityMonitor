---
title: Home
nav_order: 1
---

# Device Activity Monitor for Indigo

This plugin lets [Indigo](https://www.indigodomo.com) watch a group of devices as one, and run a trigger the moment any of them changes — a door opens, a room with three motion sensors sees movement, or the last of them goes quiet. It can also keep a running log of the sensors and variables you choose, in your own words, such as `Front Door OPEN`.

It works with any device Indigo knows about, whichever plugin or radio it comes from, because it watches Indigo itself rather than the devices.

The group trigger is based on Morris's Group Change Listener plugin, with thanks to him for the idea. The plugin was called Sensor Monitor until version 1.9.

## What it does for you

- **Runs one trigger for a whole group of devices,** so three motion sensors in a room need one trigger rather than three.
- **Lets you choose which change counts** — any change at all, a device turning on, opening or detecting something, or a device turning off, closing or going clear.
- **Notes which device set it off** in an Indigo variable, so your actions can say which door opened.
- **Ignores the housekeeping updates** that wireless sensors send all the time, such as signal strength and battery level, so a trigger runs when something happens and not when a sensor checks in.
- **Keeps an activity log** of the devices and variables you pick, with your own words for on and off, in the plugin's own log file, and in the Indigo Event Log as well if you want it there.
- **Finds your door, window and motion sensors for you** and writes the list of what to log, so you do not have to look up any device numbers.
- **Tells you when something it watches is deleted,** so a group or the activity log is never left pointing at a device that has gone.

## Where to go next

| If you want to... | Read |
|---|---|
| Install the plugin and make your first group and trigger | [Getting started](getting-started.md) |
| Know what a group shows in Indigo | [Your groups](groups.md) |
| Set up the Group Changed trigger | [Triggers](triggers.md) |
| Keep a log of your sensors and variables | [The activity log](activity-log.md) |
| Understand what the plugin is doing behind the scenes | [How it works](how-it-works.md) |
| Know what every setting does | [Settings](settings.md) |
| Know what each item in the Plugins menu does | [The plugin menu](plugin-menu.md) |
| Sort out a problem | [When something goes wrong](troubleshooting.md) |
| See what changed in each version | [Version history](changelog.md) |

## Download

The latest version is always on the [Releases page](https://github.com/Highsteads/DeviceActivityMonitor/releases/latest).
