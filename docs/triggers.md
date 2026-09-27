---
title: Triggers
nav_order: 4
---

# Triggers

## Group Changed

This trigger runs when a device in a group changes. To use it, create a new trigger, set its type to **Device Activity Monitor → Device Activity Monitor: Group Changed**, and fill in the settings below. Then add whatever you want to happen on the **Actions** tab, and any **Conditions** you want, the same as any other Indigo trigger.

| Setting | What it does |
|---|---|
| **Group** | The group to watch. Each group is listed with how many members it has. If you have not made one yet, the list says so. The trigger cannot be saved without a group. |
| **Fire on** | Which changes set the trigger off. The three choices are below. |
| **Save firing device** | Tick this to have the plugin write which member set the trigger off into an Indigo variable, before the actions run. |
| **Save to variable** | The variable to write to. It only appears when **Save firing device** is ticked, and the trigger cannot be saved without one. |
| **Save value** | Whether to write the device's name or its ID number. |

## The Fire on choices

**Any change** is the one to start with.

| Choice | The trigger runs when... |
|---|---|
| **Any change (default)** | A member turns on or off, or any other reading on it changes, such as a temperature. Updates that do not mean anything happened are ignored — a sensor reporting its signal strength, battery level, voltage or the time it was last heard from, or sending the same message twice. |
| **Any device becomes ON / OPEN / detected** | A member turns on, opens or detects something. It runs once as each member turns on, and not again while that member stays on. |
| **Any device becomes OFF / CLOSED / clear** | A member turns off, closes or goes clear. It runs once as each member turns off, and not again while that member stays off. |

The second and third choices go by the on and off state Indigo shows for each device. A member with no on and off state, such as a plain temperature sensor, can only set off **Any change**.

For a door sensor, check in the device list whether it shows on when the door is open, so you pick the choice you mean.

## Examples

- **Lights on when anyone walks in.** A group of the room's motion sensors, and a trigger on **Any device becomes ON / OPEN / detected** that turns the lights on.
- **Lights off when the room is empty.** The same group, and a second trigger on **Any device becomes OFF / CLOSED / clear**. The trigger runs as each sensor clears, so give it a condition that every sensor in the room is clear, or have it start a timer that the first trigger cancels.
- **One notification for every outside door.** A group of the door sensors, a trigger with **Save firing device** ticked, and a notification that includes the variable, such as `Opened: %%v:123456789%%` with your own variable's ID number.
- **One device by name.** A group can hold a single device, if you would rather pick triggers by a group's name than by the device.

## Pausing every group trigger

**Plugins → Device Activity Monitor → Toggle Group Change Triggers (on/off)** stops every Group Changed trigger running without you having to disable each one, and choosing it again starts them. The same switch is **Group change triggers** in the plugin's [settings](settings.md).
