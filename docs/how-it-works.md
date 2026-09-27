---
title: How it works
nav_order: 6
---

# How it works

You do not need to know any of this to use the plugin. It is here for anyone who likes to know what is going on.

## Watching Indigo, not the devices

The plugin never talks to a device. It asks Indigo to tell it about every change to every device and variable, and Indigo does, the moment each change happens. That is why it works with any device, whether it comes from Z-Wave, Zigbee, Matter or another plugin, and why it adds no traffic to your network.

For each change, the plugin asks two questions.

1. **Is this device in a group?** If it is, the plugin checks each Group Changed trigger that watches one of that device's groups, and runs the ones whose **Fire on** choice matches the change.
2. **Is this device in the activity log's settings file?** If it is, the plugin writes a line for each reading in the file that changed.

The two are separate, so turning one off never affects the other.

## Telling a real change from a check-in

Wireless sensors send updates all the time that do not mean anything happened — the time they were last heard from, their signal strength, their battery level and voltage. A sensor can also send the same message twice. If the plugin counted those, a trigger set to **Any change** would run over and over with nobody in the room.

So when a group member updates, the plugin compares everything the device reports, leaving out that housekeeping, and only counts it as a change if something else is different. A device turning on or off always counts.

For **Any device becomes ON / OPEN / detected** and **Any device becomes OFF / CLOSED / clear**, the plugin only looks at the device's on and off state, and only when it has just flipped. A device that stays on, and keeps sending new readings, does not set the trigger off again.

## When a trigger runs

For each trigger that matches, in this order, the plugin:

1. writes the member's name or ID number to the chosen variable, if **Save firing device** is ticked,
2. fills in the group's **Last Firing Device**, **Last Firing Time** and **Last Direction**,
3. asks Indigo to run the trigger, which checks its conditions and runs its actions.

If something goes wrong with one trigger, the plugin logs an error and carries on with the rest.

## How discovery tells sensors apart

**Discover All Devices** has to decide, for every device in Indigo, whether it is a door or window sensor, a motion sensor, or something else. It works through these, and the first that gives an answer wins:

1. **What the Zigbee2MQTT Bridge plugin knows.** For a Zigbee device from my Zigbee2MQTT Bridge plugin, the plugin uses the bridge's own record of what the device can sense. Some Zigbee devices report stand-in door and motion readings they do not really have, so this is the most reliable answer when the bridge has one.
2. **The kind of device.** Zigbee door and motion sensor devices, and the motion and door sensors from the Matter plugin, are taken at their word.
3. **The name.** A device with motion, PIR, presence, occupancy, mmWave or radar in its name is never taken for a door sensor.
4. **The device's readings.** A reading called contact, door sensor or window sensor means a door or window sensor, and one called occupancy, presence, motion, motion detected or PIR detection means a motion sensor.
5. **The name again.** Words such as door, window, contact, gate, garage or patio suggest a door sensor, and the motion words above suggest a motion sensor. This only applies to devices that have an on and off state, and never to lights, dimmers, relays, locks, thermostats or sprinklers, so a device called Front Door Lock is not mistaken for a door sensor.

Anything it gets wrong, you can correct in the settings file, and the correction stays when you run discovery again.

## Keeping your settings safe

The plugin writes its settings file in one go, so a crash or power cut part way through cannot leave half a file behind. It never overwrites a settings file it cannot read, and if one entry has a missing or wrong ID number, it skips that entry, says which in the Event Log, and uses the rest. The same goes for an entry that repeats another. If the file cannot be read at all, the plugin says so and logs nothing until it is fixed.

The switches in the Plugins menu are saved the moment you choose them, so they stay as you left them after a restart.
