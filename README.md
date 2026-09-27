# Device Activity Monitor for Indigo

**Run one Indigo trigger when any device in a group changes, and keep a readable log of your sensors.**

**Version:** 1.11.1 | **Author:** CliveS & Claude | **Needs:** Indigo 2022.1 or later

**[Read the full guide](https://highsteads.github.io/DeviceActivityMonitor/)** — setting up, what everything means, and what to do when something goes wrong.

---

## What it does

This plugin lets [Indigo](https://www.indigodomo.com) watch a group of devices as one. It works with any device Indigo knows about, because it watches Indigo itself rather than the devices, so it adds no traffic to your network and needs no account or password.

- **Runs one trigger for a whole group,** so three motion sensors in a room need one trigger rather than three.
- **Lets you choose which change counts** — any change, a device turning on, opening or detecting something, or a device turning off, closing or going clear.
- **Notes which device set it off** in an Indigo variable, so your actions can say which door opened.
- **Ignores the housekeeping updates** wireless sensors send all the time, such as signal strength and battery level, so a trigger runs when something happens and not when a sensor checks in.
- **Keeps an activity log** of the devices and variables you pick, such as `Front Door OPEN`, in the plugin's own log file, and in the Indigo Event Log as well if you want it there.
- **Finds your door, window and motion sensors for you,** including Zigbee sensors from my Zigbee2MQTT Bridge plugin and sensors from the Matter plugin, and writes the list of what to log.
- **Tells you when something it watches is deleted,** so a group or the log is never left pointing at a device that has gone.

The group trigger is based on Morris's Group Change Listener plugin, with thanks to him for the idea. The plugin was called Sensor Monitor until version 1.9.

## What it works with

| Part of the plugin | Works with |
|---|---|
| **Groups and the Group Changed trigger** | Any Indigo device. The ON and OFF choices need a device with an on and off state, such as a motion sensor, door sensor, switch or light. |
| **The activity log** | Any Indigo device or variable. |
| **Finding sensors for you** | Door, window and motion sensors, including Zigbee sensors from my [Zigbee2MQTT Bridge](https://github.com/Highsteads/Zigbee2MQTTBridge) plugin, Aqara presence sensors and motion and door sensors from the Matter plugin. It leaves out Indigo's virtual devices and the copies the Alexa plugin makes. |

## Installing

1. Go to the [Releases page](https://github.com/Highsteads/DeviceActivityMonitor/releases/latest) and download `Device_Activity_Monitor.indigoPlugin.zip`
2. Unzip the downloaded file — you will get `Device_Activity_Monitor.indigoPlugin`
3. Double-click `Device_Activity_Monitor.indigoPlugin` — Indigo will install it automatically

## Setting it up

1. Create a **New Device**, choose **Device Activity Monitor** and the model **Device Activity Monitor Group**, select the devices you want in **Available devices**, click **Add to Group ↓**, and click **Save**.
2. Create a new trigger of type **Device Activity Monitor: Group Changed**, pick the group, choose what to **Fire on**, and add your actions.
3. Choose **Plugins → Device Activity Monitor → Test Fire All Group Triggers** to check the actions work.
4. If you want the activity log, choose **Plugins → Device Activity Monitor → Discover All Devices (generate config file)**, and the plugin finds your sensors and starts logging them.

The [full guide](https://highsteads.github.io/DeviceActivityMonitor/) goes through each step, explains every setting, and covers what to do if something does not work.

## What's new

**v1.11.1** — The **Configure** window no longer cuts off the help text beside some settings. No setting or behaviour changed.

**v1.11.0** — The activity log goes to the plugin's own log file rather than the Indigo Event Log, which it had been filling with hundreds of lines a day. A new setting, **Activity in the Indigo event log**, with a menu item beside it, puts the lines back there if you want them. Warnings still go to the Event Log.

Every version is listed in the [version history](https://highsteads.github.io/DeviceActivityMonitor/changelog.html).

## Authors & licence

Vibed into existence by **CliveS**, who knew what he wanted, argued until he got it, and tested it on a real house. Typed at inhuman speed by **Claude** (Anthropic), who mostly did as it was told.

© 2026 CliveS · [MIT licence](LICENSE) — copy it, fork it, bend it, break it, fix it, ship it. If it breaks, you get to keep both pieces.
