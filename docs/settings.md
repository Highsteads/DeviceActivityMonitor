---
title: Settings
nav_order: 7
---

# Settings

## The plugin's settings

Open these with **Plugins → Device Activity Monitor → Configure**. A change takes effect as soon as you click **Save**. The first four are also in the Plugins menu, so you can flip them without opening this window, and the menu and this window always agree.

| Setting | What it does |
|---|---|
| **Device change log** | The master switch for the [activity log](activity-log.md). Unticked, nothing is logged anywhere. Ticked, each change goes to the plugin's own log file, and to the Indigo Event Log as well if the fourth setting is ticked. Ticked to start with. |
| **Group change triggers** | Unticked, no Group Changed trigger runs, even if it is enabled. Ticked to start with. |
| **Timestamps in log** | Starts most lines the plugin writes with the time to the thousandth of a second, such as `[14:25:33.104]`. The Event Log's own time column is not affected. Ticked to start with. |
| **Activity in the Indigo event log** | Also writes each activity log line to the Indigo Event Log. It adds a second place for the lines rather than moving them, so it does nothing while **Device change log** is unticked. Unticked to start with, because the lines would fill the Event Log. |
| **Enable debug logging** | Shows the plugin's detailed lines in the Event Log, such as each time a group trigger runs, for when you are chasing a problem. The plugin's own log file always has them. While it is ticked, the activity log also appears in the Event Log whatever **Activity in the Indigo event log** says. Unticked to start with. |

### Passwords and keys

This plugin needs no passwords, keys or network addresses, so there is nothing to fill in. The file `IndigoSecrets_example.py` inside the plugin is the blank template my plugins share for keeping such things in one place, and this plugin does not read it.

## Each group's settings

Open these by double-clicking a group in the device list. [Your groups](groups.md) explains each one.

## Each trigger's settings

Open these by double-clicking a Group Changed trigger. [Triggers](triggers.md) explains each one.

## The activity log's settings file

Which devices and variables the activity log follows, and the words it uses, are in a settings file rather than a window. [The activity log](activity-log.md) explains where it is and what goes in it.
