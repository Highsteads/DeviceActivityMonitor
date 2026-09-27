---
title: When something goes wrong
nav_order: 9
---

# When something goes wrong

Each section starts with what you see, then what it means and what to do.

## A Group Changed trigger never runs

- Choose **Plugins → Device Activity Monitor → Test Fire All Group Triggers**. If the trigger's actions work then, the trigger itself is fine, and the question is which changes set it off.
- Check **Group change triggers** is ticked in **Plugins → Device Activity Monitor → Configure**.
- Look in the Event Log, from when the plugin last started, for a line naming the trigger. It says whether the trigger has no group picked, whether its group has no members yet, or whether the group has been deleted or disabled. Open the trigger and pick the group again, or add members to the group.
- If **Fire on** is one of the ON or OFF choices, check the members have an on and off state in Indigo. A member without one can only set off **Any change**.

## A trigger runs more often than I expected

- With **Any change**, every real change to a member sets it off, including readings such as temperature or brightness. Pick **Any device becomes ON / OPEN / detected** or **Any device becomes OFF / CLOSED / clear** to go by on and off only.
- The directional choices run once for each member that changes, so three sensors in a room clearing one after another set off an OFF trigger three times. Give the trigger a condition, such as every sensor in the room being clear.

## The log says a trigger "points at group device id ... which is not loaded"

The trigger's group has been deleted or disabled. Enable the group again, or open the trigger and pick another group.

## The log says a group "has member id(s) not found in Indigo"

A device in the group has been deleted from Indigo. Double-click the group, select the entry that shows as `<missing device id` and its number, click **↑ Remove from Group**, and click **Save**.

## The log says "Deleted device was a member of group(s)"

You deleted a device that was in the groups the line names. Open each of them and take it out, as above.

## Nothing appears in the activity log

- A new install logs nothing until it has a settings file. Choose **Plugins → Device Activity Monitor → Discover All Devices (generate config file)** to make one.
- The lines go to the plugin's own log file, not the Event Log. [The activity log](activity-log.md) explains where it is, and how to have the lines in the Event Log as well.
- Check **Device change log** is ticked in **Configure**.
- Check the device is switched on in the settings file, with no `#` at the start of its line, and choose **Reload Config File** after any change.

## The log says a monitored device is "not found in Indigo"

The activity log's settings file has a device that Indigo no longer has. Open the file, delete that device's line, and choose **Reload Config File**. Running **Discover All Devices** again does not remove it, because discovery keeps lines you have added yourself.

## The log says "Monitored device deleted" or "Monitored variable deleted"

You deleted a device or variable the activity log was following. Take its line out of the settings file, as above.

## The log says "Could not read config file"

The activity log's settings file has a mistake in it that stops it being read, such as a missing bracket or quote mark, and the plugin is logging nothing until it is fixed. Open the file, correct it, and choose **Reload Config File**. If you would rather start again, delete the file and run **Discover All Devices**.

## Discovery says the existing config file "could not be parsed"

The same mistake stops discovery reading your settings file, so it leaves the file alone rather than losing your changes. Correct the file, or delete it, and run discovery again.

## Discovery picked up the wrong device, or missed one

- To leave a device out for good, add its ID number to the `excluded_ids` list at the top of the settings file and run discovery again.
- To add one it missed, add a line for it yourself. [The activity log](activity-log.md) explains how, and discovery keeps it when you run it again.

## The log says "duplicate config entry ... skipped"

The settings file has the same device and reading on two lines. The plugin uses the first and skips the second, so each change is only logged once. Delete one of them to clear the warning.

## Still stuck?

Choose **Plugins → Device Activity Monitor → Show Plugin Info**, copy the lines it writes to the Event Log, and post them on the [Indigo forum](https://forums.indigodomo.com) with a description of what you see. You can also [raise an issue on GitHub](https://github.com/Highsteads/DeviceActivityMonitor/issues).
