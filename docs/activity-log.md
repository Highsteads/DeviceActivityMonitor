---
title: The activity log
nav_order: 5
---

# The activity log

Separately from the groups and triggers, the plugin can write a line every time a device or variable you choose changes, in words you choose. It turns a pile of sensors into a timeline you can read:

```
[14:23:01.452] Hall PIR MOTION
[14:25:33.104] Front Door OPEN
[14:25:41.230] Front Door CLOSED
[14:26:10.512] Lux Level: 450 -> 520
```

Each line starts with the time to the thousandth of a second, which helps when lining events up, unless you switch **Timestamps in log** off. A device line gives the device's name as it is in Indigo now, so renaming a device changes the log straight away. A variable line gives its old and new value.

The activity log and the group triggers are independent. A device can be in a group without being logged, and logged without being in a group.

## Where the lines go

The lines go to the plugin's own log file. It is in your Indigo folder, under **Logs**, in a folder named `com.clives.indigoplugin.deviceactivitymonitor`, and the current file is `plugin.log`.

They do not go in the Indigo Event Log unless you ask for them, because a house full of sensors writes hundreds of lines a day and would crowd out everything else. To have them there as well, tick **Activity in the Indigo event log** in the plugin's [settings](settings.md), or choose **Plugins → Device Activity Monitor → Toggle Activity in Indigo Event Log (on/off)**.

Warnings always go to the Event Log, whatever you choose — a watched device or variable being deleted, a device in the list that Indigo no longer has, a reading that could not be taken, or a trigger that failed. So does a note when a watched device or variable is renamed.

## Choosing what to log

The list of what to log is a settings file, which you can have the plugin write for you.

A new install has no settings file, so it logs nothing until you make one.

### Let the plugin find your sensors

Choose **Plugins → Device Activity Monitor → Discover All Devices (generate config file)**.

The plugin looks at every device in Indigo, picks out the door, window and motion sensors, and writes the settings file with those switched on and everything else listed but switched off. It starts using the new file straight away, and says in the Event Log how many sensors of each kind it found, with their names.

- **Door and window sensors** log as **OPEN** and **CLOSED**.
- **Motion and presence sensors** log as **MOTION** and **CLEAR**.
- Sensors that report motion several ways at once get one line per movement, not three or four. Aqara presence sensors that have both a presence reading and a separate motion detector get a line for each, because they report different things.

It leaves out Indigo's own virtual devices and the devices the Alexa plugin makes, because they copy other devices and would give false readings. It also leaves out devices whose names say they are something else, such as a temperature sensor, a power monitor, a plug or a light, unless the device itself reports as a door or motion sensor.

You can run it again whenever you add sensors. It keeps everything you have done to the file — the devices you have excluded, the variables you log, any wording you have changed, and any devices you have added yourself.

If it finds the existing file cannot be read, it does not overwrite it, and says so in the Event Log.

### Change what is logged

Open the settings file in any text editor. It is in your Indigo folder, under **Preferences → Plugins**, in a folder named `com.clives.indigoplugin.deviceactivitymonitor`, and it is called `device_activity_monitor_config.json`.

After saving your changes, choose **Plugins → Device Activity Monitor → Reload Config File** and the plugin uses them straight away.

A shortened example:

```
{
  "excluded_ids": [],

  "devices": [

    # --- Contact / Door / Window sensors (active) ---
    {"id": 123456789, "name": "Front Door", "state": "onState", "label": "Front Door", "on_text": "OPEN", "off_text": "CLOSED"},

    # --- Motion / Occupancy / Presence sensors (active) ---
    {"id": 234567890, "name": "Hall Sensor", "state": "occupancy", "label": "PIR", "on_text": "MOTION", "off_text": "CLEAR"},

    # --- Other devices (not contact/motion - remove # to enable) ---
#     {"id": 345678901, "name": "Kitchen Light", "state": "onState", "label": "Kitchen Light", "on_text": "ON", "off_text": "OFF"},

  ],

  "variables": [
    {"id": 456789012, "name": "Lux_Level", "label": "Lux Level"},
  ]
}
```

- **A line starting with `#` is switched off.** Delete the `#` to switch it on, or add one to switch a line off without losing it.
- **A comma after the last line in a list does no harm**, so you do not need to tidy them.
- **Each line is one reading on one device.** A sensor with two readings, such as presence and motion, can have two lines.

What each part of a line does:

| Part | What it does |
|---|---|
| `id` | The device's ID number in Indigo. Right-click the device and copy its ID if you add one yourself. |
| `name` | For your own reference. The plugin does not use it. |
| `state` | Which reading to log. `onState` is the on and off state Indigo shows for the device, and any other name is one of the device's own states, such as `occupancy` or `contact`. |
| `label` | The word or words that follow the device's name in the log. If it matches the device's name, it is left out so the name does not appear twice. |
| `on_text` | What to write when the reading turns on. `ON` if you leave it out. |
| `off_text` | What to write when it turns off. `OFF` if you leave it out. |
| `on_value` | For a sensor that reports words rather than on and off, the word that means on, such as `"enter"`. It can be a list of words. |
| `off_value` | The word that means off, such as `"leave"`. When either of these is set, a change to any other word is not logged. |

A Zigbee door sensor's `contact` reading is on when the door is closed, so the plugin writes those the other way round, with `"on_text": "CLOSED", "off_text": "OPEN"`.

### Leave a device out for good

Put its ID number in the `excluded_ids` list at the top, such as `"excluded_ids": [123456789, 234567890],`, then run **Discover All Devices** again. That switches the device's line off, and every later run keeps it off. **Reload Config File** on its own does not, because only discovery reads this list. If an excluded device has since been deleted from Indigo, discovery says so, so you can take it off the list.

### Log a variable

Add a line to the `variables` list with the variable's ID number and the label to show, as in the example. Right-click the variable in Indigo and copy its ID. Each change is logged as the label, then the old value and the new one.

## Pausing the activity log

**Plugins → Device Activity Monitor → Toggle Device Change Log (on/off)** stops the activity log completely, including the notes about renamed devices and variables, and choosing it again starts it. Group triggers and warnings carry on either way. The same switch is **Device change log** in the plugin's [settings](settings.md).
