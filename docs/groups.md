---
title: Your groups
nav_order: 3
---

# Your groups

A group is an ordinary Indigo device that holds a list of other devices. The [Group Changed trigger](triggers.md) watches a group, so you build the list once and every trigger that uses the group follows it.

## Making and changing a group

Choose **New Device**, set **Type** to **Device Activity Monitor**, and the model to **Device Activity Monitor Group**. To change a group later, double-click it in the device list. It is the same window either way.

| In the window | What it does |
|---|---|
| **Show devices from** | Narrows the **Available devices** list to one folder. **(All folders)** shows every device, and **(Root — no folder)** shows the devices that are not in a folder. It only helps you find devices, and makes no difference to what the group watches. |
| **Available devices** | Every device not already in the group. Select the ones you want, holding the Command key to select more than one. |
| **Add to Group ↓** | Moves the selected devices into the group. |
| **Current group members** | The devices in the group. A device that has since been deleted from Indigo shows as `<missing device id` followed by its number, so you can see it and take it out. |
| **↑ Remove from Group** | Takes the selected members out of the group. |

A change takes effect as soon as you click **Save**, with no need to restart the plugin.

A group can be empty while you set it up. A device can be in as many groups as you like.

To delete a group, delete the device as you would any other. The triggers that used it stop working, and the plugin says so in the Event Log the next time it starts.

## What a group shows in Indigo

| Shown as | What it means |
|---|---|
| **Status** | How many devices are in the group, such as **3 members**. This is what the device list shows. |
| **Members** | The same count, as a number. |
| **Last Firing Device** | The name of the member that last set off one of this group's triggers. |
| **Last Firing Time** | When that happened, such as `2026-09-27 08:59:48`. |
| **Last Direction** | What the member did: **activated** if it turned on, opened or detected something, **deactivated** if it turned off, closed or went clear, or **changed** for any other change. |

The last three only fill in once a trigger that uses the group has run, so a group with no triggers leaves them blank. A test fire from the Plugins menu does not change them.

You can show any of these on a control page, or use them in a trigger's conditions, the same as any other device state.
