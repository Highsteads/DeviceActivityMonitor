---
title: Getting started
nav_order: 2
---

# Getting started

This takes about five minutes. The example sends you a notification when any of three motion sensors in the living room sees movement, and you can use the same steps for any group of devices.

## What you need

- Indigo 2022.1 or later.
- The devices you want to watch, already working in Indigo.

The plugin needs no account, password or network address.

## 1. Install the plugin

1. Go to the [Releases page](https://github.com/Highsteads/DeviceActivityMonitor/releases/latest) and download `Device_Activity_Monitor.indigoPlugin.zip`
2. Unzip the downloaded file — you will get `Device_Activity_Monitor.indigoPlugin`
3. Double-click `Device_Activity_Monitor.indigoPlugin` — Indigo will install it automatically

Indigo asks whether to enable the plugin. Say yes.

The Event Log then shows a line saying the plugin has started and how many devices and variables it is logging, which is none at first, and a second line listing its settings.

The settings start as most people want them, so you do not need to open **Configure** yet. Every setting is explained on the [Settings](settings.md) page.

## 2. Make a group

1. In Indigo, choose **New Device**.
2. Name it, such as **Living Room Presence**, set **Type** to **Device Activity Monitor**, and the model to **Device Activity Monitor Group**. The group's settings open.
3. In **Show devices from**, pick the folder that holds your devices, such as **Living Room**, or leave it on **(All folders)**.
4. In **Available devices**, select the three motion sensors. Hold the Command key to select more than one.
5. Click **Add to Group ↓**. The sensors move down into **Current group members**.
6. Click **Save**.

The group shows **3 members** in Indigo's device list.

## 3. Make a trigger

1. Create a new trigger, and set its type to **Device Activity Monitor → Device Activity Monitor: Group Changed**.
2. In **Group**, pick **Living Room Presence**. Each group is listed with how many members it has.
3. In **Fire on**, pick **Any device becomes ON / OPEN / detected**.
4. On the **Actions** tab, add the notification you want.
5. Click **OK**.

## 4. Check it works

Choose **Plugins → Device Activity Monitor → Test Fire All Group Triggers**. This runs every enabled Group Changed trigger once, straight away, so your notification should arrive without you having to walk past a sensor.

Then walk into the room. The trigger runs when a sensor that was clear sees you, and not again while that sensor still sees you. If a second sensor then sees you as well, the trigger runs again for that one. Walk out, and nothing happens, because this trigger only runs when a sensor turns on.

If nothing happens, the [When something goes wrong](troubleshooting.md) page goes through the usual causes.

## 5. Next steps

- [Triggers](triggers.md) covers the other **Fire on** choices, and how to note which device set the trigger off.
- [The activity log](activity-log.md) explains how to have the plugin log your door, window and motion sensors, which it can find for you.

## If you used this plugin when it was called Sensor Monitor

Version 1.9 changed the plugin's name and its identity in Indigo, so Indigo sees it as a new plugin.

1. Disable **Sensor Monitor** in **Plugins → Manage Plugins**, and remove it.
2. Install Device Activity Monitor as above.
3. If you had a settings file for the activity log, move it from the Sensor Monitor folder in your Indigo **Preferences → Plugins** folder (named `com.clives.indigoplugin.sensormonitor`) into this plugin's folder (named `com.clives.indigoplugin.deviceactivitymonitor`), and rename it from `sensor_monitor_config.json` to `device_activity_monitor_config.json`.
4. Make your groups again with **New Device**, because the old groups are not carried over, and point your triggers at them.
