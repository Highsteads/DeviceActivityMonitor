---
title: The plugin menu
nav_order: 8
---

# The plugin menu

These are under **Plugins → Device Activity Monitor**.

| Menu item | What it does |
|---|---|
| **Discover All Devices (generate config file)** | Looks at every device in Indigo, finds the door, window and motion sensors, and writes the activity log's settings file with them switched on. It keeps anything you have changed in the file, and starts using the new file straight away. [The activity log](activity-log.md) explains it in full. It also writes a second file, `device_discovery.json`, in the same folder, listing the devices it considered and what it decided about each. |
| **Find Contact & Motion Sensors** | Lists the door, window and motion sensors it can find in the Event Log, each with a line ready to copy into the settings file. It changes nothing. |
| **Reload Config File** | Reads the activity log's settings file again, after you have edited it, checks that every device and variable in it still exists, and says in the Event Log how many it now follows. |
| **Test Fire All Group Triggers** | Runs every enabled Group Changed trigger once, straight away, so you can check what its actions do without setting off a sensor. It names each one in the Event Log. It does not write to a trigger's **Save to variable**, or change a group's last firing details. |
| **Toggle Device Change Log (on/off)** | Stops or starts the activity log. The same as **Device change log** in the [settings](settings.md). |
| **Toggle Group Change Triggers (on/off)** | Stops or starts every Group Changed trigger. The same as **Group change triggers** in the settings. |
| **Toggle Timestamps in Log (on/off)** | Turns off or on the time at the start of most lines the plugin writes. The same as **Timestamps in log** in the settings. |
| **Toggle Activity in Indigo Event Log (on/off)** | Stops or starts the activity log's lines appearing in the Event Log as well as the plugin's own log file. The same as **Activity in the Indigo event log** in the settings. |
| **Show Plugin Info** | Writes the plugin's version, details of your Mac and Indigo, and how the four switches above are set, to the Event Log. It is useful to include if you ask for help on the Indigo forum. |
| **About Device Activity Monitor** | Opens this project's page on GitHub. |

Each of the four switches says in the Event Log whether it is now on or off, and stays as you leave it after a restart.
