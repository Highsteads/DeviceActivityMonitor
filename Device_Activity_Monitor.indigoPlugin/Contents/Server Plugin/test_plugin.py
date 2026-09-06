#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    test_plugin.py
# Description: Mock test harness for Device Activity Monitor plugin - no Indigo runtime needed
# Author:      CliveS & Claude Fable 5
# Date:        17-07-2026
# Version:     1.13
#
# Run from Terminal (path follows the installed Indigo version):
#   cd "/Library/Application Support/Perceptive Automation/Indigo "*/Plugins
#   cd "Device_Activity_Monitor.indigoPlugin/Contents/Server Plugin"
#   python3 test_plugin.py -v

import sys
import os
import logging
import tempfile
import unittest
import importlib.util
from unittest.mock import MagicMock

# ======================================
# MOCK INDIGO MODULE
# Must be injected into sys.modules BEFORE plugin.py is imported
# ======================================

class MockDevice:
    """Simulates an Indigo device object."""
    def __init__(self, dev_id, name, on_state=False, states=None, enabled=True,
                 plugin_id="", device_type_id=""):
        self.id           = dev_id
        self.name         = name
        self.onState      = on_state
        self.states       = states or {}
        self.enabled      = enabled
        self.folderId     = None  # no folder by default
        self.pluginId     = plugin_id
        # deviceDeleted() reads dev.deviceTypeId to spot damGroup devices; a real
        # Indigo device always has one, so the mock must too (default "" = an
        # ordinary monitored device, not a damGroup).
        self.deviceTypeId = device_type_id

    def __repr__(self):
        return f"MockDevice(id={self.id}, name='{self.name}', onState={self.onState})"


class MockThermostatDevice:
    """Simulates an Indigo ThermostatDevice - intentionally has NO onState attribute.

    Used to verify that discovery helpers correctly exclude non-binary device
    types (thermostats, plain button devices) from contact sensor candidates,
    even when their names contain keywords like 'door' or 'garage'.
    """
    def __init__(self, dev_id, name, states=None, enabled=True, plugin_id="",
                 device_type_id=""):
        self.id           = dev_id
        self.name         = name
        self.states       = states or {}
        self.enabled      = enabled
        self.folderId     = None
        self.pluginId     = plugin_id
        self.deviceTypeId = device_type_id
        # Note: intentionally no self.onState attribute

    def __repr__(self):
        return f"MockThermostatDevice(id={self.id}, name='{self.name}')"


class MockDevices(dict):
    """Dict-like mock for indigo.devices - adds subscribeToChanges().

    __iter__ yields device objects (values) so that discovery methods that
    do 'for dev in indigo.devices:' receive MockDevice instances, matching
    the behaviour of the real Indigo API.
    """
    def subscribeToChanges(self):
        pass  # No-op in tests

    def __iter__(self):
        return iter(self.values())


class MockVariable:
    """Simulates an Indigo variable object."""
    def __init__(self, var_id, name, value=""):
        self.id    = var_id
        self.name  = name
        self.value = value

    def __repr__(self):
        return f"MockVariable(id={self.id}, name='{self.name}', value='{self.value}')"


class MockVariables(dict):
    """Dict-like mock for indigo.variables - adds subscribeToChanges()."""
    def subscribeToChanges(self):
        pass  # No-op in tests


class MockPluginBase:
    """Minimal stand-in for indigo.PluginBase."""
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        self.pluginId          = pluginId
        self.pluginDisplayName = pluginDisplayName
        self.pluginVersion     = pluginVersion
        self.pluginPrefs       = pluginPrefs
        self.logger            = MagicMock()
        # Real PluginBase makes debug a property whose setter lowers the
        # EVENT-LOG handler, so assigning it is not the inert attribute write
        # a plain mock would give. Set the handler before _debug so the
        # setter below always has something to talk to.
        self.indigo_log_handler = MagicMock()
        self._debug             = False

    # Mirrors indigo PluginBase.debug (plugin_base.py:332-353) verbatim,
    # including the bare "if value:" truthiness test. That test is the whole
    # reason showDebugInfo has to be coerced with as_bool: a stored string
    # "false" is truthy, the handler drops to DEBUG, and every activity line
    # the quiet default keeps out of the shared event log goes straight back
    # into it. A test asserting only "plugin.debug is False" would be
    # checking the symptom; asserting the handler level checks the damage.
    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value):
        self._debug = value
        if not hasattr(self, "indigo_log_handler"):
            return
        if value:
            self.indigo_log_handler.setLevel(logging.DEBUG)
        else:
            self.indigo_log_handler.setLevel(logging.INFO)

    def deviceUpdated(self, origDev, newDev):
        pass  # super() in plugin lands here

    def deviceDeleted(self, dev):
        pass  # super() in plugin lands here

    def variableUpdated(self, origVar, newVar):
        pass  # super() in plugin lands here

    def variableDeleted(self, var):
        pass  # super() in plugin lands here


# Build and inject the mock indigo module
mock_indigo            = MagicMock()
mock_indigo.PluginBase = MockPluginBase
mock_indigo.devices    = MockDevices()
mock_indigo.variables  = MockVariables()
mock_indigo.server     = MagicMock()
sys.modules['indigo']  = mock_indigo


# ======================================
# LOAD plugin.py FROM SAME DIRECTORY
# ======================================

_plugin_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin.py")
_spec        = importlib.util.spec_from_file_location("sensor_monitor_plugin", _plugin_path)
_mod         = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

Plugin      = _mod.Plugin
CONFIG_PATH = _mod.CONFIG_PATH

# ======================================
# TEST FIXTURE MONITOR DICTS
#
# As of v1.10.0 the plugin's module-level fallback dicts ship EMPTY (a
# published plugin must not carry the author's personal device ids), so the
# standard test fixtures live HERE and make_plugin() injects deep copies
# after construction. The ids/states match the pre-v1.10.0 shipped dicts so
# every existing test keeps its device vocabulary.
# ======================================

DEVICE_MONITOR = {
    # --- Bathroom Basin ---
    812537401:  [{"state": "onState",       "label": "Occupancy"}],
    1976004986: [{"state": "pirDetection",  "label": "PIR"},
                 {"state": "presence",      "label": "mmWave Presence"}],
    # --- Bathroom Door ---
    1184619127: [{"state": "onState",       "label": "Occupancy"}],
    415253439:  [{"state": "onState",       "label": "Contact",
                  "on_text": "OPEN",        "off_text": "CLOSED"}],
    # --- Kitchen ---
    1649680462: [{"state": "presence",      "label": "mmWave Presence"}],
    1440351705: [{"state": "onState",       "label": "mmWave Presence"}],
    467551931:  [{"state": "onState",       "label": "Occupancy"}],
    # --- Living Room ---
    408117572:  [{"state": "onState",       "label": "mmWave Presence"}],
    1256890181: [{"state": "onState",       "label": "mmWave Presence"}],
    1807623843: [{"state": "onState",       "label": "mmWave Presence"}],
}

VARIABLE_MONITOR = {
    241032502: {"label": "Lux Level"},
}

# Redirect file paths to non-existent locations so tests never touch real
# config/discovery files that may be present on the system.
# Tests that exercise file I/O (TestConfigLoading, TestMenuCallbacks) pass
# their own explicit temp-file paths to _load_config() or patch these vars.
_mod.CONFIG_PATH           = "/nonexistent/test/path/sm_config.json"
_mod.DISCOVERY_OUTPUT_PATH = "/nonexistent/test/path/sm_discovery.json"


# ======================================
# SHARED HELPERS
# ======================================

# Human-readable names for the 10 monitored device IDs
_DEVICE_NAMES = {
    812537401:  "Basin Occupancy Sensor",
    1976004986: "Basin mmWave Sensor",
    1184619127: "Door Occupancy Sensor",
    415253439:  "Bathroom Door Contact",
    1649680462: "Kitchen Left mmWave",
    1440351705: "Kitchen FP2",
    467551931:  "Utility Room Occupancy",
    408117572:  "Living Room FP2 Zone 1",
    1256890181: "Living Room FP2 Zone 2",
    1807623843: "Living Room Moes",
}


_VARIABLE_NAMES = {
    241032502: "Lux_Level",
}


def make_device_registry(missing_ids=None):
    """Return a MockDevices dict populated with all DEVICE_MONITOR entries."""
    missing_ids = set(missing_ids or [])
    registry    = MockDevices()
    for dev_id in DEVICE_MONITOR:
        if dev_id not in missing_ids:
            registry[dev_id] = MockDevice(dev_id, _DEVICE_NAMES.get(dev_id, f"Device {dev_id}"))
    return registry


def make_variable_registry(missing_ids=None):
    """Return a MockVariables dict populated with all VARIABLE_MONITOR entries."""
    missing_ids = set(missing_ids or [])
    registry    = MockVariables()
    for var_id in VARIABLE_MONITOR:
        if var_id not in missing_ids:
            registry[var_id] = MockVariable(var_id, _VARIABLE_NAMES.get(var_id, f"Variable {var_id}"), "0")
    return registry


def make_plugin(prefs=None):
    """Instantiate the Plugin class with minimal prefs and inject the test
    fixture monitor dicts.

    The plugin's module-level fallback dicts are EMPTY as of v1.10.0, so
    the fixtures defined above are copied onto the instance here.
    Call plugin._load_config(path) afterwards to test file-based loading
    (it fully replaces the injected fixtures).
    """
    plugin = Plugin(
        "com.clives.indigoplugin.deviceactivitymonitor",
        "Device Activity Monitor",
        "1.10.0",
        prefs or {}
    )
    plugin.device_monitor   = {k: [dict(s) for s in v]
                               for k, v in DEVICE_MONITOR.items()}
    plugin.variable_monitor = {k: dict(v)
                               for k, v in VARIABLE_MONITOR.items()}
    return plugin


def server_log_messages():
    """Return list of strings passed to indigo.server.log() since last reset."""
    return [c.args[0] for c in mock_indigo.server.log.call_args_list]


def io_open_plugin_source():
    """The plugin source, for the structural guards below."""
    with open(_plugin_path, encoding="utf-8") as fh:
        return fh.read()


def _logger_messages(plugin, *levels):
    """Messages the plugin passed to the named self.logger levels."""
    out = []
    for level in levels:
        for call in getattr(plugin.logger, level).call_args_list:
            if call.args:
                out.append(str(call.args[0]))
    return out


def activity_messages(plugin):
    """The activity narration the plugin produced, whichever route it took.

    _log_activity() sends a line to logger.debug (quiet, the default) or to
    logger.info (when the user has opted the narration back into the event
    log), so a test that cares only THAT the line was produced - and what it
    says - looks at both. Use event_log_messages() to assert about WHERE it
    went.
    """
    return _logger_messages(plugin, "debug", "info")


def plugin_file_messages(plugin):
    """Everything that reaches the plugin's own log file.

    Indigo attaches a file handler to self.logger at THREADDEBUG, so every
    level lands in the file. indigo.server.log() bypasses the logger and so
    never reaches it.
    """
    return _logger_messages(plugin, "debug", "info", "warning", "error")


def event_log_messages(plugin):
    """Everything that reaches the SHARED Indigo event log.

    Two routes get there: a direct indigo.server.log() call, and any
    self.logger call at INFO or above - Indigo sets indigo_log_handler to
    INFO, which is precisely why logger.debug() is the quiet route and why
    warnings and errors still reach Log_Error_Watch.py.
    """
    return server_log_messages() + _logger_messages(
        plugin, "info", "warning", "error")


# ======================================
# TEST: STARTUP VALIDATION
# ======================================

class TestStartupValidation(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices   = make_device_registry()
        mock_indigo.variables = make_variable_registry()

    def test_all_devices_found_logs_summary_not_per_device(self):
        """CONTRACT FLIP (v1.9.13): startup validation logs ONE summary line,
        not a per-device [OK] line. Rationale: trimmed-boot convention (Jay,
        25-May-2026) — dozens of [OK] lines buried the stale-id warnings
        that are the whole point of validation."""
        plugin = make_plugin()
        plugin.startup()

        info_calls = [str(c) for c in plugin.logger.info.call_args_list]
        ok_count   = sum(1 for c in info_calls if "[OK]" in c)

        self.assertEqual(ok_count, 0,
            msg=f"Per-device [OK] boot lines should be gone.\nInfo calls: {info_calls}")

    def test_all_devices_found_logs_final_ok(self):
        """startup() logs 'All monitored devices validated OK' when nothing missing."""
        plugin = make_plugin()
        plugin.startup()

        info_text = " ".join(str(c) for c in plugin.logger.info.call_args_list)
        self.assertIn("All monitored devices validated OK", info_text)

    def test_all_devices_found_no_warnings(self):
        """startup() produces no warnings when all devices are present."""
        plugin = make_plugin()
        plugin.startup()
        plugin.logger.warning.assert_not_called()

    def test_missing_devices_log_bang_per_missing(self):
        """startup() logs [!] for each missing device ID."""
        missing = [812537401, 1976004986]
        mock_indigo.devices = make_device_registry(missing_ids=missing)

        plugin = make_plugin()
        plugin.startup()

        warn_calls   = [str(c) for c in plugin.logger.warning.call_args_list]
        bang_count   = sum(1 for c in warn_calls if "[!]" in c)

        self.assertEqual(bang_count, len(missing),
            msg=f"Expected {len(missing)} [!] entries, got {bang_count}.\n"
                f"Warnings: {warn_calls}")

    def test_missing_devices_summary_warning(self):
        """startup() warns with a count of missing devices."""
        missing = [812537401, 1976004986]
        mock_indigo.devices = make_device_registry(missing_ids=missing)

        plugin = make_plugin()
        plugin.startup()

        warn_text = " ".join(str(c) for c in plugin.logger.warning.call_args_list)
        self.assertIn("2 monitored device(s) not found", warn_text)

    def test_subscribetochanges_called_on_startup(self):
        """startup() calls indigo.devices.subscribeToChanges()."""
        called = []
        mock_indigo.devices = make_device_registry()
        mock_indigo.devices.subscribeToChanges = lambda: called.append(True)

        plugin = make_plugin()
        plugin.startup()

        self.assertEqual(len(called), 1, "subscribeToChanges() should be called once")


# ======================================
# TEST: DEVICE UPDATED - onState
# ======================================

class TestDeviceUpdatedOnState(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices = make_device_registry()
        self.plugin = make_plugin()

    def test_false_to_true_logs_on(self):
        """onState False -> True logs 'ON' for the device."""
        orig = MockDevice(812537401, "Basin Occupancy Sensor", on_state=False)
        new  = MockDevice(812537401, "Basin Occupancy Sensor", on_state=True)
        self.plugin.deviceUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        self.assertTrue(
            any("Basin Occupancy Sensor" in m and "Occupancy" in m and m.endswith("ON")
                for m in msgs),
            msg=f"Expected ON log. Got: {msgs}"
        )

    def test_true_to_false_logs_off(self):
        """onState True -> False logs 'OFF' for the device."""
        orig = MockDevice(812537401, "Basin Occupancy Sensor", on_state=True)
        new  = MockDevice(812537401, "Basin Occupancy Sensor", on_state=False)
        self.plugin.deviceUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        self.assertTrue(
            any("Basin Occupancy Sensor" in m and "Occupancy" in m and m.endswith("OFF")
                for m in msgs),
            msg=f"Expected OFF log. Got: {msgs}"
        )

    def test_no_change_no_log(self):
        """Unchanged onState (False -> False) produces no log output at all."""
        orig = MockDevice(812537401, "Basin Occupancy Sensor", on_state=False)
        new  = MockDevice(812537401, "Basin Occupancy Sensor", on_state=False)
        self.plugin.deviceUpdated(orig, new)

        mock_indigo.server.log.assert_not_called()
        self.assertEqual(activity_messages(self.plugin), [],
            msg="Unchanged state must narrate nothing on either route.")

    def test_label_same_as_device_name_not_duplicated(self):
        """When label equals device name, name is printed once, not twice.

        Discovery-generated configs set label to the device name, so
        'Side Passage Motion' should log as '[ts] Side Passage Motion OFF',
        not '[ts] Side Passage Motion Side Passage Motion OFF'.
        """
        self.plugin.device_monitor[333333] = [{"state": "onState", "label": "My Test Sensor"}]
        orig = MockDevice(333333, "My Test Sensor", on_state=True)
        new  = MockDevice(333333, "My Test Sensor", on_state=False)
        self.plugin.deviceUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        self.assertFalse(
            any("My Test Sensor My Test Sensor" in m for m in msgs),
            msg=f"Device name should not appear twice. Got: {msgs}"
        )
        self.assertTrue(
            any("My Test Sensor" in m and m.endswith("OFF") for m in msgs),
            msg=f"Expected single name + state. Got: {msgs}"
        )

    def test_label_different_from_device_name_both_shown(self):
        """When label differs from device name, both are included in the log."""
        orig = MockDevice(812537401, "Basin Occupancy Sensor", on_state=False)
        new  = MockDevice(812537401, "Basin Occupancy Sensor", on_state=True)
        self.plugin.deviceUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        self.assertTrue(
            any("Basin Occupancy Sensor" in m and "Occupancy" in m for m in msgs),
            msg=f"Expected device name + label. Got: {msgs}"
        )

    def test_unmonitored_device_produces_no_log(self):
        """Device ID not in device_monitor is silently ignored."""
        orig = MockDevice(999999999, "Some Unrelated Device", on_state=False)
        new  = MockDevice(999999999, "Some Unrelated Device", on_state=True)
        self.plugin.deviceUpdated(orig, new)

        mock_indigo.server.log.assert_not_called()
        self.assertEqual(activity_messages(self.plugin), [],
            msg="An unmonitored device must narrate nothing on either route.")

    def test_device_without_onstate_produces_no_error(self):
        """deviceUpdated with state='onState' but device lacking onState does not log
        an error.  getattr(dev, 'onState', None) returns None for both old and new,
        they are equal, so nothing is logged (no error, no state log)."""
        # Manually inject a ThermostatDevice into device_monitor
        self.plugin.device_monitor[555003] = [{"state": "onState", "label": "TRV"}]
        trv = MockThermostatDevice(555003, "Living Room Door TRV")
        self.plugin.deviceUpdated(trv, trv)

        self.plugin.logger.error.assert_not_called()
        mock_indigo.server.log.assert_not_called()
        self.assertEqual(activity_messages(self.plugin), [],
            msg="A device with no onState must narrate nothing on either route.")


# ======================================
# TEST: DEVICE UPDATED - custom states
# ======================================

class TestDeviceUpdatedCustomStates(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices = make_device_registry()
        self.plugin = make_plugin()

    def test_only_changed_state_is_logged(self):
        """When pirDetection unchanged and presence changes, only presence is logged."""
        orig = MockDevice(1976004986, "Basin mmWave Sensor",
                          states={"pirDetection": False, "presence": False})
        new  = MockDevice(1976004986, "Basin mmWave Sensor",
                          states={"pirDetection": False, "presence": True})
        self.plugin.deviceUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        self.assertFalse(any("PIR" in m for m in msgs),
            msg=f"PIR unchanged - should not log. Got: {msgs}")
        self.assertTrue(any("mmWave Presence" in m and "ON" in m for m in msgs),
            msg=f"presence changed - should log. Got: {msgs}")

    def test_both_states_logged_when_both_change(self):
        """Both PIR and presence logged when both change simultaneously."""
        orig = MockDevice(1976004986, "Basin mmWave Sensor",
                          states={"pirDetection": False, "presence": False})
        new  = MockDevice(1976004986, "Basin mmWave Sensor",
                          states={"pirDetection": True,  "presence": True})
        self.plugin.deviceUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        self.assertTrue(any("PIR" in m and m.endswith("ON") for m in msgs),
            msg=f"Expected PIR ON. Got: {msgs}")
        self.assertTrue(any("mmWave Presence" in m and m.endswith("ON") for m in msgs),
            msg=f"Expected mmWave Presence ON. Got: {msgs}")

    def test_custom_state_off_logs_off(self):
        """presence True -> False logs OFF."""
        orig = MockDevice(1976004986, "Basin mmWave Sensor",
                          states={"pirDetection": False, "presence": True})
        new  = MockDevice(1976004986, "Basin mmWave Sensor",
                          states={"pirDetection": False, "presence": False})
        self.plugin.deviceUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        self.assertTrue(any("mmWave Presence" in m and m.endswith("OFF") for m in msgs),
            msg=f"Expected mmWave Presence OFF. Got: {msgs}")


# ======================================
# TEST: DEVICE UPDATED - on_text / off_text
# ======================================

class TestDeviceUpdatedCustomText(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices = make_device_registry()
        self.plugin = make_plugin()

    def test_contact_open_text(self):
        """Door contact onState True logs OPEN (not ON)."""
        orig = MockDevice(415253439, "Bathroom Door Contact", on_state=False)
        new  = MockDevice(415253439, "Bathroom Door Contact", on_state=True)
        self.plugin.deviceUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        self.assertTrue(any(m.endswith("OPEN") for m in msgs),
            msg=f"Expected message ending with OPEN. Got: {msgs}")
        self.assertFalse(any(m.endswith("ON") for m in msgs),
            msg=f"Should not end with ON (should be OPEN). Got: {msgs}")

    def test_contact_close_text(self):
        """Door contact onState False logs CLOSED (not OFF)."""
        orig = MockDevice(415253439, "Bathroom Door Contact", on_state=True)
        new  = MockDevice(415253439, "Bathroom Door Contact", on_state=False)
        self.plugin.deviceUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        self.assertTrue(any(m.endswith("CLOSED") for m in msgs),
            msg=f"Expected message ending with CLOSED. Got: {msgs}")
        self.assertFalse(any(m.endswith("OFF") for m in msgs),
            msg=f"Should not end with OFF (should be CLOSED). Got: {msgs}")


# ======================================
# TEST: DEVICE UPDATED - rename detection
# ======================================

class TestDeviceUpdatedRename(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices = make_device_registry()
        self.plugin = make_plugin()

    def test_rename_on_monitored_device_logs_both_names(self):
        """Name change on a monitored device logs old and new names."""
        orig = MockDevice(812537401, "Old Basin Name", on_state=False)
        new  = MockDevice(812537401, "New Basin Name", on_state=False)
        self.plugin.deviceUpdated(orig, new)

        msgs = server_log_messages()
        self.assertTrue(
            any("Old Basin Name" in m and "New Basin Name" in m for m in msgs),
            msg=f"Expected rename message with both names. Got: {msgs}"
        )

    def test_no_rename_log_when_name_unchanged(self):
        """No rename log when device name is the same."""
        orig = MockDevice(812537401, "Basin Occupancy Sensor", on_state=False)
        new  = MockDevice(812537401, "Basin Occupancy Sensor", on_state=False)
        self.plugin.deviceUpdated(orig, new)

        mock_indigo.server.log.assert_not_called()
        self.assertEqual(activity_messages(self.plugin), [],
            msg="An unchanged name must narrate nothing on either route.")

    def test_rename_on_unmonitored_device_not_logged(self):
        """Rename of an unmonitored device is silently ignored."""
        orig = MockDevice(999999999, "Unrelated Old Name", on_state=False)
        new  = MockDevice(999999999, "Unrelated New Name", on_state=True)
        self.plugin.deviceUpdated(orig, new)

        mock_indigo.server.log.assert_not_called()
        self.assertEqual(activity_messages(self.plugin), [],
            msg="An unmonitored rename must narrate nothing on either route.")


# ======================================
# TEST: DEVICE DELETED
# ======================================

class TestDeviceDeleted(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices = make_device_registry()
        self.plugin = make_plugin()

    def test_monitored_device_deleted_warns(self):
        """Deleting a monitored device triggers a warning containing the device name."""
        dev = MockDevice(812537401, "Basin Occupancy Sensor")
        self.plugin.deviceDeleted(dev)

        self.plugin.logger.warning.assert_called()
        warn_text = " ".join(str(c) for c in self.plugin.logger.warning.call_args_list)
        self.assertIn("Basin Occupancy Sensor", warn_text)

    def test_monitored_device_deleted_includes_id(self):
        """Warning for deleted device includes the device ID."""
        dev = MockDevice(812537401, "Basin Occupancy Sensor")
        self.plugin.deviceDeleted(dev)

        warn_text = " ".join(str(c) for c in self.plugin.logger.warning.call_args_list)
        self.assertIn("812537401", warn_text)

    def test_unmonitored_device_deleted_no_warning(self):
        """Deleting an unmonitored device produces no warning."""
        dev = MockDevice(999999999, "Irrelevant Device")
        self.plugin.deviceDeleted(dev)

        self.plugin.logger.warning.assert_not_called()


# ======================================
# TEST: LOG FORMAT
# ======================================

class TestLogFormat(unittest.TestCase):
    """Verify the millisecond timestamp prefix appears in log messages."""

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices = make_device_registry()
        self.plugin = make_plugin()

    def test_log_contains_millisecond_timestamp(self):
        """Log message starts with [HH:MM:SS.mmm] format."""
        import re
        orig = MockDevice(812537401, "Basin Occupancy Sensor", on_state=False)
        new  = MockDevice(812537401, "Basin Occupancy Sensor", on_state=True)
        self.plugin.deviceUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        ts_pattern = re.compile(r"^\[\d{2}:\d{2}:\d{2}\.\d{3}\]")
        self.assertTrue(
            any(ts_pattern.match(m) for m in msgs),
            msg=f"Expected [HH:MM:SS.mmm] prefix. Got: {msgs}"
        )


# ======================================
# TEST: VARIABLE STARTUP VALIDATION
# ======================================

class TestVariableStartupValidation(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices   = make_device_registry()
        mock_indigo.variables = make_variable_registry()

    def test_all_variables_found_logs_summary_not_per_variable(self):
        """CONTRACT FLIP (v1.9.13): variable validation logs one summary line,
        no per-variable [OK] lines (trimmed-boot convention — see the device
        validation test of the same name for the rationale)."""
        plugin = make_plugin()
        plugin.startup()

        info_calls = [str(c) for c in plugin.logger.info.call_args_list]
        ok_count   = sum(1 for c in info_calls if "[OK]" in c)

        self.assertEqual(ok_count, 0,
            msg=f"Per-entry [OK] boot lines should be gone.\nInfo: {info_calls}")

    def test_all_variables_found_logs_final_ok(self):
        """startup() logs 'All monitored variables validated OK' when none missing."""
        plugin = make_plugin()
        plugin.startup()

        info_text = " ".join(str(c) for c in plugin.logger.info.call_args_list)
        self.assertIn("All monitored variables validated OK", info_text)

    def test_missing_variable_logs_bang(self):
        """startup() logs [!] for a missing variable ID."""
        mock_indigo.variables = make_variable_registry(missing_ids=[241032502])

        plugin = make_plugin()
        plugin.startup()

        warn_calls = [str(c) for c in plugin.logger.warning.call_args_list]
        self.assertTrue(any("[!]" in c and "241032502" in c for c in warn_calls),
            msg=f"Expected [!] for missing variable. Got: {warn_calls}")

    def test_variable_subscribetochanges_called(self):
        """startup() calls indigo.variables.subscribeToChanges()."""
        called = []
        mock_indigo.variables = make_variable_registry()
        mock_indigo.variables.subscribeToChanges = lambda: called.append(True)

        plugin = make_plugin()
        plugin.startup()

        self.assertEqual(len(called), 1, "variables.subscribeToChanges() should be called once")


# ======================================
# TEST: VARIABLE UPDATED
# ======================================

class TestVariableUpdated(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices   = make_device_registry()
        mock_indigo.variables = make_variable_registry()
        self.plugin = make_plugin()

    def test_value_change_logged_with_arrow(self):
        """Variable value change logs 'old -> new' format."""
        orig = MockVariable(241032502, "Lux_Level", "450")
        new  = MockVariable(241032502, "Lux_Level", "520")
        self.plugin.variableUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        self.assertTrue(any("450" in m and "520" in m and "->" in m for m in msgs),
            msg=f"Expected '450 -> 520' in log. Got: {msgs}")

    def test_custom_label_used_in_log(self):
        """Label from variable_monitor config appears in log instead of raw variable name."""
        orig = MockVariable(241032502, "Lux_Level", "100")
        new  = MockVariable(241032502, "Lux_Level", "200")
        self.plugin.variableUpdated(orig, new)

        msgs = activity_messages(self.plugin)
        self.assertTrue(any("Lux Level" in m for m in msgs),
            msg=f"Expected label 'Lux Level' in log. Got: {msgs}")

    def test_no_change_no_log(self):
        """Unchanged variable value produces no log output."""
        orig = MockVariable(241032502, "Lux_Level", "450")
        new  = MockVariable(241032502, "Lux_Level", "450")
        self.plugin.variableUpdated(orig, new)

        mock_indigo.server.log.assert_not_called()
        self.assertEqual(activity_messages(self.plugin), [],
            msg="An unchanged variable must narrate nothing on either route.")

    def test_unmonitored_variable_ignored(self):
        """Variable not in variable_monitor is silently ignored."""
        orig = MockVariable(999999999, "Some_Other_Var", "a")
        new  = MockVariable(999999999, "Some_Other_Var", "b")
        self.plugin.variableUpdated(orig, new)

        mock_indigo.server.log.assert_not_called()
        self.assertEqual(activity_messages(self.plugin), [],
            msg="An unmonitored variable must narrate nothing on either route.")

    def test_rename_detection_logged(self):
        """Variable rename on a monitored variable is logged."""
        orig = MockVariable(241032502, "Old_Lux_Name", "100")
        new  = MockVariable(241032502, "New_Lux_Name", "100")
        self.plugin.variableUpdated(orig, new)

        msgs = server_log_messages()
        self.assertTrue(any("Old_Lux_Name" in m and "New_Lux_Name" in m for m in msgs),
            msg=f"Expected rename log. Got: {msgs}")


# ======================================
# TEST: VARIABLE DELETED
# ======================================

class TestVariableDeleted(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices   = make_device_registry()
        mock_indigo.variables = make_variable_registry()
        self.plugin = make_plugin()

    def test_monitored_variable_deleted_warns(self):
        """Deleting a monitored variable triggers a warning with name and ID."""
        var = MockVariable(241032502, "Lux_Level", "0")
        self.plugin.variableDeleted(var)

        self.plugin.logger.warning.assert_called()
        warn_text = " ".join(str(c) for c in self.plugin.logger.warning.call_args_list)
        self.assertIn("Lux_Level", warn_text)
        self.assertIn("241032502", warn_text)

    def test_unmonitored_variable_deleted_silent(self):
        """Deleting an unmonitored variable produces no warning."""
        var = MockVariable(999999999, "Irrelevant_Var", "0")
        self.plugin.variableDeleted(var)

        self.plugin.logger.warning.assert_not_called()


# ======================================
# TEST: JSON CONFIG LOADING
# ======================================

class TestConfigLoading(unittest.TestCase):
    """Verify _load_config() correctly reads sensor_monitor_config.json."""

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices   = make_device_registry()
        mock_indigo.variables = make_variable_registry()
        self._tmp_files = []

    def tearDown(self):
        for path in self._tmp_files:
            try:
                os.unlink(path)
            except Exception:
                pass

    def _write_config(self, content):
        """Write content to a temp file and return the path."""
        fd, path = tempfile.mkstemp(suffix=".json", prefix="sm_test_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        self._tmp_files.append(path)
        return path

    # --- Fallback behaviour ---

    def test_fallback_when_no_file(self):
        """CONTRACT (v1.10.0): with no config file the module-level fallback
        dicts apply, and they now ship EMPTY — a published plugin must not
        carry the author's personal device ids. (Tests get their fixtures
        injected by make_plugin instead.)"""
        plugin = Plugin("com.clives.indigoplugin.deviceactivitymonitor",
                        "Device Activity Monitor", "1.10.0", {})
        self.assertEqual(plugin.device_monitor, {},
            msg="shipped fallback DEVICE_MONITOR must be empty")
        self.assertEqual(plugin.variable_monitor, {},
            msg="shipped fallback VARIABLE_MONITOR must be empty")
        self.assertEqual(_mod.DEVICE_MONITOR, {})
        self.assertEqual(_mod.VARIABLE_MONITOR, {})

    def test_fallback_is_deep_copy(self):
        """Fallback dicts are independent copies - mutating the instance dict
        does not affect the module-level dict."""
        plugin = Plugin("com.clives.indigoplugin.deviceactivitymonitor",
                        "Device Activity Monitor", "1.10.0", {})
        plugin.device_monitor[999999999] = [{"state": "onState", "label": "Test"}]
        self.assertNotIn(999999999, _mod.DEVICE_MONITOR,
            msg="Mutating device_monitor should not alter module-level DEVICE_MONITOR")

    # --- Device loading ---

    def test_devices_loaded_from_json(self):
        """Devices section of JSON is loaded into self.device_monitor."""
        config = '''{
  "devices": [
    {"id": 111111, "state": "onState", "label": "Test Device"}
  ],
  "variables": []
}'''
        path   = self._write_config(config)
        plugin = make_plugin()
        plugin._load_config(path)

        self.assertIn(111111, plugin.device_monitor,
            msg="Device ID 111111 should be in device_monitor")
        self.assertEqual(plugin.device_monitor[111111][0]["label"], "Test Device")

    def test_variables_loaded_from_json(self):
        """Variables section of JSON is loaded into self.variable_monitor."""
        config = '''{
  "devices": [],
  "variables": [
    {"id": 222222, "label": "Test Var"}
  ]
}'''
        path   = self._write_config(config)
        plugin = make_plugin()
        plugin._load_config(path)

        self.assertIn(222222, plugin.variable_monitor,
            msg="Variable ID 222222 should be in variable_monitor")
        self.assertEqual(plugin.variable_monitor[222222]["label"], "Test Var")

    # --- Comment stripping ---

    def test_comment_lines_ignored(self):
        """Lines starting with # are stripped before JSON parsing."""
        config = '''{
  "devices": [
    {"id": 111111, "state": "onState", "label": "Active Device"},
# {"id": 222222, "state": "onState", "label": "Disabled Device"}
  ],
  "variables": []
}'''
        path   = self._write_config(config)
        plugin = make_plugin()
        plugin._load_config(path)

        self.assertIn(111111, plugin.device_monitor,
            msg="Active device should be present")
        self.assertNotIn(222222, plugin.device_monitor,
            msg="Commented-out device should be absent")

    def test_indented_comment_lines_ignored(self):
        """Lines with leading whitespace before # are also treated as comments."""
        config = '''{
  "devices": [
    {"id": 111111, "state": "onState", "label": "Active"},
    # {"id": 333333, "state": "onState", "label": "Indented Comment"}
  ],
  "variables": []
}'''
        path   = self._write_config(config)
        plugin = make_plugin()
        plugin._load_config(path)

        self.assertIn(111111, plugin.device_monitor)
        self.assertNotIn(333333, plugin.device_monitor)

    # --- Trailing comma handling ---

    def test_trailing_comma_in_devices_handled(self):
        """Trailing comma after last device entry does not cause parse error."""
        config = '''{
  "devices": [
    {"id": 111111, "state": "onState", "label": "Test"},
  ],
  "variables": []
}'''
        path   = self._write_config(config)
        plugin = make_plugin()
        plugin._load_config(path)  # Should not raise

        self.assertIn(111111, plugin.device_monitor)

    def test_trailing_comma_in_variables_handled(self):
        """Trailing comma after last variable entry does not cause parse error."""
        config = '''{
  "devices": [],
  "variables": [
    {"id": 222222, "label": "Var"},
  ]
}'''
        path   = self._write_config(config)
        plugin = make_plugin()
        plugin._load_config(path)  # Should not raise

        self.assertIn(222222, plugin.variable_monitor)

    # --- Multi-state devices ---

    def test_multi_state_device_grouped_by_id(self):
        """Multiple entries with the same device ID are grouped into a list."""
        config = '''{
  "devices": [
    {"id": 111111, "state": "pirDetection", "label": "PIR"},
    {"id": 111111, "state": "presence",     "label": "mmWave Presence"}
  ],
  "variables": []
}'''
        path   = self._write_config(config)
        plugin = make_plugin()
        plugin._load_config(path)

        self.assertIn(111111, plugin.device_monitor)
        self.assertEqual(len(plugin.device_monitor[111111]), 2,
            msg="Two entries for same ID should produce a list of 2 configs")
        labels = [c["label"] for c in plugin.device_monitor[111111]]
        self.assertIn("PIR", labels)
        self.assertIn("mmWave Presence", labels)

    # --- on_text / off_text ---

    def test_custom_on_off_text_preserved(self):
        """on_text and off_text from JSON are preserved in state config."""
        config = '''{
  "devices": [
    {"id": 111111, "state": "onState", "label": "Door",
     "on_text": "OPEN", "off_text": "CLOSED"}
  ],
  "variables": []
}'''
        path   = self._write_config(config)
        plugin = make_plugin()
        plugin._load_config(path)

        cfg = plugin.device_monitor[111111][0]
        self.assertEqual(cfg.get("on_text"),  "OPEN")
        self.assertEqual(cfg.get("off_text"), "CLOSED")

    # --- name as label fallback ---

    def test_name_used_as_label_fallback(self):
        """If label is absent, the name field is used as the label."""
        config = '''{
  "devices": [
    {"id": 111111, "name": "My Sensor Name", "state": "onState"}
  ],
  "variables": []
}'''
        path   = self._write_config(config)
        plugin = make_plugin()
        plugin._load_config(path)

        label = plugin.device_monitor[111111][0]["label"]
        self.assertEqual(label, "My Sensor Name",
            msg="name should be used when label is absent")

    # --- Integration: loaded config works in callbacks ---

    def test_json_loaded_config_works_in_deviceupdated(self):
        """deviceUpdated() correctly uses config loaded from JSON file."""
        config = '''{
  "devices": [
    {"id": 333333, "state": "onState", "label": "JSON Label"}
  ],
  "variables": []
}'''
        path   = self._write_config(config)
        plugin = make_plugin()
        plugin._load_config(path)

        mock_indigo.server.log.reset_mock()
        orig = MockDevice(333333, "JSON Test Device", on_state=False)
        new  = MockDevice(333333, "JSON Test Device", on_state=True)
        plugin.deviceUpdated(orig, new)

        msgs = activity_messages(plugin)
        self.assertTrue(
            any("JSON Test Device" in m and "JSON Label" in m for m in msgs),
            msg=f"Expected JSON-configured label in log. Got: {msgs}"
        )

    def test_json_loaded_config_works_in_variableupdated(self):
        """variableUpdated() correctly uses config loaded from JSON file."""
        config = '''{
  "devices": [],
  "variables": [
    {"id": 444444, "label": "JSON Var Label"}
  ]
}'''
        path   = self._write_config(config)
        plugin = make_plugin()
        plugin._load_config(path)

        mock_indigo.server.log.reset_mock()
        orig = MockVariable(444444, "some_var", "10")
        new  = MockVariable(444444, "some_var", "20")
        plugin.variableUpdated(orig, new)

        msgs = activity_messages(plugin)
        self.assertTrue(
            any("JSON Var Label" in m and "10" in m and "20" in m for m in msgs),
            msg=f"Expected JSON-configured variable label in log. Got: {msgs}"
        )

    # --- Error resilience ---

    def test_invalid_json_falls_back_to_defaults(self):
        """Malformed JSON falls back to the module-level dicts (empty as of
        v1.10.0) with a warning — it must not keep the previous config or
        raise."""
        path   = self._write_config("{ this is not valid json }")
        plugin = make_plugin()
        plugin._load_config(path)

        self.assertEqual(
            set(plugin.device_monitor.keys()),
            set(_mod.DEVICE_MONITOR.keys()),
            msg="Invalid JSON should fall back to the module-level dicts"
        )


# ======================================
# TEST: DISCOVERY FILTER (_disc_is_contact)
# ======================================

class TestDiscoveryFilter(unittest.TestCase):
    """Verify _disc_is_contact() correctly excludes non-binary device types.

    The fix requires devices to have onState before name-keyword matching
    applies.  Contact state names (contact, doorSensor, windowSensor) always
    qualify regardless of device type.
    """

    def setUp(self):
        mock_indigo.devices   = make_device_registry()
        mock_indigo.variables = make_variable_registry()
        self.plugin = make_plugin()

    def test_sensor_with_door_keyword_and_onstate_is_candidate(self):
        """Device with onState + 'door' keyword IS a contact candidate."""
        dev    = MockDevice(111, "Front Door Sensor", on_state=False)
        states = {}
        self.assertTrue(self.plugin._disc_is_contact(dev, states))

    def test_thermostat_with_door_keyword_is_not_candidate(self):
        """ThermostatDevice (no onState) with 'door' keyword is NOT a candidate."""
        dev    = MockThermostatDevice(222, "Living Room Door Radiator")
        states = {"setpointCool": 20, "setpointHeat": 18}
        self.assertFalse(self.plugin._disc_is_contact(dev, states))

    def test_plain_device_with_garage_keyword_is_not_candidate(self):
        """Plain Device (no onState) with 'garage' keyword is NOT a candidate."""
        dev    = MockThermostatDevice(333, "Z Garage Freezer Light Switch Button")
        states = {"buttonGroupCount": 1}
        self.assertFalse(self.plugin._disc_is_contact(dev, states))

    def test_device_with_contact_state_is_candidate_regardless_of_type(self):
        """Device with 'contact' state name IS a candidate even without onState."""
        dev    = MockThermostatDevice(444, "Some Weird Device")
        states = {"contact": True, "battery": 80}
        self.assertTrue(self.plugin._disc_is_contact(dev, states))

    def test_device_with_doorSensor_state_is_candidate(self):
        """Device with 'doorSensor' state name IS a candidate."""
        dev    = MockThermostatDevice(445, "Unlabelled Sensor")
        states = {"doorSensor": False}
        self.assertTrue(self.plugin._disc_is_contact(dev, states))

    def test_non_contact_name_without_onstate_is_not_candidate(self):
        """Device with no contact keywords and no onState is not flagged."""
        dev    = MockThermostatDevice(555, "Utility Room Radiator")
        states = {"setpointHeat": 18}
        self.assertFalse(self.plugin._disc_is_contact(dev, states))

    def test_lounge_motion_with_onstate_is_not_candidate(self):
        """'Lounge Motion' has onState but no contact keywords - not a candidate."""
        dev    = MockDevice(556, "Lounge Motion", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states))

    def test_window_keyword_with_onstate_is_candidate(self):
        """Device with onState + 'window' keyword IS a contact candidate."""
        dev    = MockDevice(557, "Kitchen Window Sensor", on_state=False)
        states = {}
        self.assertTrue(self.plugin._disc_is_contact(dev, states))

    def test_door_and_motion_name_is_not_contact(self):
        """Device named 'Front Door Motion' has 'door' AND 'motion' - NOT a contact candidate.

        Motion keywords beat contact keywords in name-only matching.
        'Front Door Motion' should fall through to _disc_is_motion() and be
        logged as ON/OFF, not OPEN/CLOSED.
        """
        dev    = MockDevice(558, "Front Door Motion", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states))

    def test_garage_door_motion_name_is_not_contact(self):
        """Device named 'Garage Door Motion' has both keywords - NOT a contact candidate."""
        dev    = MockDevice(559, "Garage Door Motion", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states))

    def test_door_sensor_no_motion_keyword_remains_contact(self):
        """Device named 'Front Door Sensor' has 'door' but no motion keyword - still contact."""
        dev    = MockDevice(560, "Front Door Sensor", on_state=False)
        states = {}
        self.assertTrue(self.plugin._disc_is_contact(dev, states))


# ======================================
# TEST: DISCOVERY FILTER (_disc_is_motion / _disc_motion_states)
# ======================================

class TestDiscoveryMotion(unittest.TestCase):
    """Verify _disc_is_motion() correctly identifies motion/occupancy sensors
    and _disc_motion_states() returns the right state names."""

    def setUp(self):
        mock_indigo.devices   = make_device_registry()
        mock_indigo.variables = make_variable_registry()
        self.plugin = make_plugin()

    def test_device_with_occupancy_state_is_motion_candidate(self):
        """Device with 'occupancy' state IS a motion candidate."""
        dev    = MockDevice(100, "Some Sensor", on_state=False)
        states = {"occupancy": True, "battery": 90}
        self.assertTrue(self.plugin._disc_is_motion(dev, states))

    def test_device_with_pirDetection_state_is_motion_candidate(self):
        """Device with 'pirDetection' state IS a motion candidate."""
        dev    = MockDevice(101, "Basin mmWave Sensor", on_state=False)
        states = {"pirDetection": False, "presence": True}
        self.assertTrue(self.plugin._disc_is_motion(dev, states))

    def test_device_with_presence_state_is_motion_candidate(self):
        """Device with 'presence' state IS a motion candidate."""
        dev    = MockDevice(102, "Kitchen FP2", on_state=False)
        states = {"presence": True}
        self.assertTrue(self.plugin._disc_is_motion(dev, states))

    def test_device_with_motion_keyword_and_onstate_is_candidate(self):
        """Device with onState + 'motion' keyword IS a motion candidate."""
        dev    = MockDevice(103, "Lounge Motion Sensor", on_state=False)
        states = {}
        self.assertTrue(self.plugin._disc_is_motion(dev, states))

    def test_device_with_mmwave_keyword_and_onstate_is_candidate(self):
        """Device with onState + 'mmwave' keyword IS a motion candidate."""
        dev    = MockDevice(104, "Kitchen mmWave FP2", on_state=False)
        states = {}
        self.assertTrue(self.plugin._disc_is_motion(dev, states))

    def test_thermostat_with_motion_keyword_is_not_motion_candidate(self):
        """ThermostatDevice (no onState) with 'motion' keyword is NOT a candidate."""
        dev    = MockThermostatDevice(105, "Zone Motion Valve")
        states = {}
        self.assertFalse(self.plugin._disc_is_motion(dev, states))

    def test_light_switch_is_not_motion_candidate(self):
        """Device with onState but no motion keywords/states is NOT a motion candidate."""
        dev    = MockDevice(106, "Kitchen Light Switch", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_motion(dev, states))

    def test_contact_sensor_not_also_motion_candidate(self):
        """A contact sensor (contact state) is NOT additionally a motion candidate.
        In practice callers use elif, but the method itself should return False here."""
        dev    = MockDevice(107, "Front Door Sensor", on_state=False)
        states = {"contact": True}
        # contact state is not in _MOTION_STATE_NAMES, 'door' not in _MOTION_NAME_KEYWORDS
        self.assertFalse(self.plugin._disc_is_motion(dev, states))

    def test_disc_motion_states_returns_found_motion_states(self):
        """_disc_motion_states returns all matching motion state names, sorted."""
        states = {"pirDetection": False, "presence": True, "battery": 80}
        result = self.plugin._disc_motion_states(states)
        self.assertIn("pirDetection", result)
        self.assertIn("presence",     result)
        self.assertNotIn("battery",   result)

    def test_disc_motion_states_fallback_to_onstate(self):
        """_disc_motion_states returns ['onState'] when no known motion states found."""
        states = {"onState": False}
        result = self.plugin._disc_motion_states(states)
        self.assertEqual(result, ["onState"])

    def test_disc_motion_states_empty_states_fallback(self):
        """_disc_motion_states returns ['onState'] for empty states dict."""
        result = self.plugin._disc_motion_states({})
        self.assertEqual(result, ["onState"])

    def test_front_door_motion_is_motion_candidate(self):
        """Device named 'Front Door Motion' IS a motion candidate.

        Because _disc_is_contact now returns False when both a contact keyword
        ('door') and a motion keyword ('motion') appear in the name, the device
        falls through to _disc_is_motion() which returns True.  This ensures
        the device is logged as ON/OFF, not OPEN/CLOSED.
        """
        dev    = MockDevice(558, "Front Door Motion", on_state=False)
        states = {}
        self.assertTrue(self.plugin._disc_is_motion(dev, states))


# ======================================
# TEST: NAME EXCLUSION KEYWORDS
# ======================================

class TestNameExclusionFilter(unittest.TestCase):
    """Verify _NAME_EXCLUSION_KEYWORDS veto name-based classification.

    Devices with sensor keywords in their name (door, garage, motion, etc.)
    must NOT be classified as contact or motion sensors if their name also
    contains an exclusion keyword (temperature, luminance, power, etc.).

    State-name matching (contact, doorSensor, occupancy, etc.) is never
    affected by exclusion keywords.
    """

    def setUp(self):
        mock_indigo.devices   = make_device_registry()
        mock_indigo.variables = make_variable_registry()
        self.plugin = make_plugin()

    # --- contact exclusions ---

    def test_luminance_device_with_door_keyword_not_contact(self):
        """'Front Door Luminance' has 'door' but 'luminance' vetoes it - NOT contact."""
        dev    = MockDevice(700, "Front Door Luminance", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states),
            msg="'luminance' in name must veto contact classification")

    def test_temperature_device_with_door_keyword_not_contact(self):
        """'Front Door Temperature' has 'door' but 'temperature' vetoes it - NOT contact."""
        dev    = MockDevice(701, "Front Door Temperature", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states),
            msg="'temperature' in name must veto contact classification")

    def test_power_device_with_garage_keyword_not_contact(self):
        """'HA Garage Freezer Power' has 'garage' but 'power' vetoes it - NOT contact."""
        dev    = MockDevice(702, "HA Garage Freezer Power", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states),
            msg="'power' in name must veto contact classification")

    def test_repeater_with_garage_keyword_not_contact(self):
        """'Garage Loft Repeater Smart Plug' - 'repeater' vetoes it - NOT contact."""
        dev    = MockDevice(703, "Garage Loft Repeater Smart Plug", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states),
            msg="'repeater' in name must veto contact classification")

    def test_control_device_with_door_keyword_not_contact(self):
        """'HA Garage Door Control' has 'door'+'garage' but 'control' vetoes - NOT contact."""
        dev    = MockDevice(704, "HA Garage Door Control", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states),
            msg="'control' in name must veto contact classification")

    def test_virtual_device_with_door_keyword_not_contact(self):
        """'Garage Door Virtual' has 'door'+'garage' but 'virtual' vetoes - NOT contact."""
        dev    = MockDevice(705, "Garage Door Virtual", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states),
            msg="'virtual' in name must veto contact classification")

    def test_voltage_device_with_garage_keyword_not_contact(self):
        """'HA Garage Freezer Voltage' has 'garage' but 'voltage' vetoes - NOT contact."""
        dev    = MockDevice(706, "HA Garage Freezer Voltage", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states),
            msg="'voltage' in name must veto contact classification")

    def test_current_device_with_garage_keyword_not_contact(self):
        """'HA Garage Freezer Current' has 'garage' but 'current' vetoes - NOT contact."""
        dev    = MockDevice(707, "HA Garage Freezer Current", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states),
            msg="'current' in name must veto contact classification")

    def test_lights_device_with_garage_keyword_not_contact(self):
        """'HA Garage Strip Lights' has 'garage' but 'lights' vetoes it - NOT contact."""
        dev    = MockDevice(708, "HA Garage Strip Lights", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states),
            msg="'lights' in name must veto contact classification")

    def test_light_device_with_door_keyword_not_contact(self):
        """'Back Door Light' has 'door' but 'light' vetoes it - NOT contact."""
        dev    = MockDevice(709, "Back Door Light", on_state=False)
        states = {}
        self.assertFalse(self.plugin._disc_is_contact(dev, states),
            msg="'light' in name must veto contact classification")

    # --- state-name matching beats exclusion keywords ---

    def test_contact_state_beats_luminance_exclusion(self):
        """Device with 'contact' state IS a contact sensor even if name has 'luminance'."""
        dev    = MockDevice(710, "Front Door Luminance Contact", on_state=False)
        states = {"contact": True}
        self.assertTrue(self.plugin._disc_is_contact(dev, states),
            msg="State-name match ('contact') must win over exclusion keyword")

    def test_doorSensor_state_beats_temperature_exclusion(self):
        """Device with 'doorSensor' state IS a contact sensor even if name has 'temp'."""
        dev    = MockDevice(711, "Entry Temp Sensor", on_state=False)
        states = {"doorSensor": False}
        self.assertTrue(self.plugin._disc_is_contact(dev, states),
            msg="State-name match ('doorSensor') must win over exclusion keyword")

    def test_occupancy_state_beats_power_exclusion(self):
        """Device with 'occupancy' state IS a motion sensor even if name has 'power'."""
        dev    = MockDevice(712, "Power Presence Sensor", on_state=False)
        states = {"occupancy": False}
        self.assertTrue(self.plugin._disc_is_motion(dev, states),
            msg="State-name match ('occupancy') must win over exclusion keyword")

    # --- real sensors still detected (no false negatives) ---

    def test_front_door_sensor_still_contact(self):
        """'Front Door Sensor' has no exclusion keywords - still a contact candidate."""
        dev    = MockDevice(720, "Front Door Sensor", on_state=False)
        states = {}
        self.assertTrue(self.plugin._disc_is_contact(dev, states),
            msg="Valid contact sensor must not be blocked by exclusion filter")

    def test_lounge_motion_sensor_still_motion(self):
        """'Lounge Motion Sensor' has no exclusion keywords - still a motion candidate."""
        dev    = MockDevice(721, "Lounge Motion Sensor", on_state=False)
        states = {}
        self.assertTrue(self.plugin._disc_is_motion(dev, states),
            msg="Valid motion sensor must not be blocked by exclusion filter")


# ======================================
# TEST: MENU CALLBACKS
# ======================================

def make_contact_device_registry():
    """Return a MockDevices registry with contact/motion candidates and known
    false-positives.

    Includes:
      555001 - Front Door Sensor      : onState + 'door' keyword  -> CONTACT candidate
      555002 - Lounge Motion Sensor   : onState + 'motion' keyword -> MOTION candidate
      555003 - Living Room Door TRV   : MockThermostatDevice (no onState) + 'door'
                                        -> NOT a candidate (no onState)
      555004 - Kitchen Light Switch   : onState but no contact/motion keywords
                                        -> NOT a candidate (no keywords)
      555005 - Virtual Door Switch    : onState + 'door' keyword BUT virtual pluginId
                                        -> NOT a candidate (excluded plugin)
      555006 - HA Garage Door Gen1    : onState + 'garage' keyword BUT Alexa pluginId
                                        -> NOT a candidate (excluded plugin)
      555007 - Front Door Luminance   : onState + 'door' keyword BUT 'luminance' exclusion
                                        -> NOT a candidate (name exclusion keyword)
      555008 - Front Door Temperature : onState + 'door' keyword BUT 'temperature' exclusion
                                        -> NOT a candidate (name exclusion keyword)
      555009 - HA Garage Freezer Power: onState + 'garage' keyword BUT 'power' exclusion
                                        -> NOT a candidate (name exclusion keyword)
      555010 - Garage Loft Repeater   : onState + 'garage' keyword BUT 'repeater' exclusion
                                        -> NOT a candidate (name exclusion keyword)
      555011 - HA Garage Door Control : onState + 'door'/'garage' BUT 'control' exclusion
                                        -> NOT a candidate (name exclusion keyword)
      555012 - Garage Door Virtual    : onState + 'door'/'garage' BUT 'virtual' exclusion
                                        -> NOT a candidate (name exclusion keyword)
      555013 - HA Garage Strip Lights : onState + 'garage' keyword BUT 'lights' exclusion
                                        -> NOT a candidate (name exclusion keyword)
    """
    registry = make_device_registry()
    registry[555001] = MockDevice(555001, "Front Door Sensor",
                                  on_state=False, states={"onState": False})
    registry[555002] = MockDevice(555002, "Lounge Motion Sensor",
                                  on_state=False, states={"onState": False})
    registry[555003] = MockThermostatDevice(555003, "Living Room Door TRV",
                                            states={"setpointHeat": 18})
    registry[555004] = MockDevice(555004, "Kitchen Light Switch",
                                  on_state=False, states={"onState": False})
    registry[555005] = MockDevice(555005, "Virtual Door Switch",
                                  on_state=False, states={"onState": False},
                                  plugin_id="com.perceptiveautomation.indigoplugin.virtualdevices")
    registry[555006] = MockDevice(555006, "HA Garage Door Gen1",
                                  on_state=False, states={"onState": False},
                                  plugin_id="com.indigodomo.indigoplugin.alexa")
    registry[555007] = MockDevice(555007, "Front Door Luminance",
                                  on_state=False, states={"onState": False})
    registry[555008] = MockDevice(555008, "Front Door Temperature",
                                  on_state=False, states={"onState": False})
    registry[555009] = MockDevice(555009, "HA Garage Freezer Power",
                                  on_state=False, states={"onState": False})
    registry[555010] = MockDevice(555010, "Garage Loft Repeater Smart Plug",
                                  on_state=False, states={"onState": False})
    registry[555011] = MockDevice(555011, "HA Garage Door Control",
                                  on_state=False, states={"onState": False})
    registry[555012] = MockDevice(555012, "Garage Door Virtual",
                                  on_state=False, states={"onState": False})
    registry[555013] = MockDevice(555013, "HA Garage Strip Lights",
                                  on_state=False, states={"onState": False})
    return registry


class TestMenuCallbacks(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices   = make_contact_device_registry()
        mock_indigo.variables = make_variable_registry()

    # --- menuReloadConfig ---

    def test_menu_reload_config_resets_to_defaults(self):
        """menuReloadConfig reloads the config (falls back to defaults when no file)."""
        plugin = make_plugin()
        # Inject a spurious entry not in DEVICE_MONITOR
        plugin.device_monitor[999999999] = [{"state": "onState", "label": "Ghost"}]
        plugin.menuReloadConfig()
        # After reload with no config file, extra key should be gone
        self.assertNotIn(999999999, plugin.device_monitor,
            msg="Reload should have reset device_monitor to DEVICE_MONITOR defaults")

    def test_menu_reload_config_logs_counts(self):
        """menuReloadConfig logs a summary showing old -> new device/variable counts."""
        plugin = make_plugin()
        plugin.menuReloadConfig()

        info_text = " ".join(str(c) for c in plugin.logger.info.call_args_list)
        self.assertIn("->", info_text,
            msg="Reload log should contain 'old -> new' counts")

    def test_menu_reload_config_reruns_validation(self):
        """menuReloadConfig re-validates devices (summary line as of the
        v1.9.13 trimmed-boot contract — per-device [OK] lines are gone)."""
        plugin = make_plugin()
        plugin.logger.info.reset_mock()
        plugin.menuReloadConfig()

        info_text = " ".join(str(c) for c in plugin.logger.info.call_args_list)
        self.assertIn("validated OK", info_text,
            msg="menuReloadConfig should re-run device validation")

    # --- menuFindContactSensors ---

    def test_menu_find_contact_sensors_logs_header(self):
        """menuFindContactSensors logs the discovery header."""
        plugin = make_plugin()
        plugin.menuFindContactSensors()

        info_text = " ".join(str(c) for c in plugin.logger.info.call_args_list)
        self.assertIn("Contact", info_text,
            msg="Discovery header should mention 'Contact'")

    def test_menu_find_contact_sensors_logs_candidate(self):
        """menuFindContactSensors logs devices whose name contains a contact keyword."""
        plugin = make_plugin()
        plugin.menuFindContactSensors()

        info_text = " ".join(str(c) for c in plugin.logger.info.call_args_list)
        self.assertIn("Front Door Sensor", info_text,
            msg="Device with 'door' in name should be logged as a candidate")

    def test_menu_find_contact_sensors_finds_motion_sensor(self):
        """menuFindContactSensors now also logs motion sensor candidates."""
        plugin = make_plugin()
        plugin.menuFindContactSensors()

        info_text = " ".join(str(c) for c in plugin.logger.info.call_args_list)
        self.assertIn("Lounge Motion Sensor", info_text,
            msg="Motion sensor 'Lounge Motion Sensor' should appear as a motion candidate")

    def test_menu_find_contact_sensors_skips_non_sensor(self):
        """menuFindContactSensors excludes devices that are neither contact nor motion."""
        plugin = make_plugin()
        plugin.menuFindContactSensors()

        info_text = " ".join(str(c) for c in plugin.logger.info.call_args_list)
        self.assertNotIn("Kitchen Light Switch", info_text,
            msg="'Kitchen Light Switch' has no sensor keywords - should not appear")

    def test_menu_find_contact_sensors_skips_thermostat_with_door_keyword(self):
        """menuFindContactSensors excludes ThermostatDevice even if name has 'door'."""
        plugin = make_plugin()
        plugin.menuFindContactSensors()

        info_text = " ".join(str(c) for c in plugin.logger.info.call_args_list)
        self.assertNotIn("Living Room Door TRV", info_text,
            msg="ThermostatDevice 'Living Room Door TRV' must not appear - no onState")

    # --- menuDiscoverDevices ---

    def test_menu_discover_devices_logs_summary(self):
        """menuDiscoverDevices logs a 'Discovery complete' summary line."""
        plugin = make_plugin()
        plugin.menuDiscoverDevices()

        info_text = " ".join(str(c) for c in plugin.logger.info.call_args_list)
        self.assertIn("Discovery complete", info_text,
            msg="menuDiscoverDevices should log a summary line")

    def test_menu_discover_devices_writes_config_file(self):
        """menuDiscoverDevices writes sensor_monitor_config.json."""
        import shutil
        tmpdir = tempfile.mkdtemp()
        disc_path   = os.path.join(tmpdir, "device_discovery.json")
        config_path = os.path.join(tmpdir, "sensor_monitor_config.json")

        orig_disc   = _mod.DISCOVERY_OUTPUT_PATH
        orig_config = _mod.CONFIG_PATH
        _mod.DISCOVERY_OUTPUT_PATH = disc_path
        _mod.CONFIG_PATH           = config_path

        try:
            plugin = make_plugin()
            plugin.menuDiscoverDevices()

            self.assertTrue(os.path.exists(disc_path),
                msg="device_discovery.json should have been written")
            self.assertTrue(os.path.exists(config_path),
                msg="sensor_monitor_config.json should have been written")
        finally:
            _mod.DISCOVERY_OUTPUT_PATH = orig_disc
            _mod.CONFIG_PATH           = orig_config
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_menu_discover_devices_config_contains_contact_candidate(self):
        """The generated config file includes the contact sensor candidate as an active entry."""
        import shutil
        tmpdir      = tempfile.mkdtemp()
        config_path = os.path.join(tmpdir, "sensor_monitor_config.json")

        orig_disc   = _mod.DISCOVERY_OUTPUT_PATH
        orig_config = _mod.CONFIG_PATH
        _mod.DISCOVERY_OUTPUT_PATH = os.path.join(tmpdir, "device_discovery.json")
        _mod.CONFIG_PATH           = config_path

        try:
            plugin = make_plugin()
            plugin.menuDiscoverDevices()

            with open(config_path, encoding="utf-8") as f:
                content = f.read()

            # Front Door Sensor (ID 555001) should be an active (uncommented) entry
            active_lines = [
                l for l in content.splitlines()
                if "555001" in l and not l.lstrip().startswith("#")
            ]
            self.assertTrue(len(active_lines) > 0,
                msg=f"Contact candidate 555001 should appear as an active (uncommented) entry.\n"
                    f"Config content:\n{content}")
        finally:
            _mod.DISCOVERY_OUTPUT_PATH = orig_disc
            _mod.CONFIG_PATH           = orig_config
            shutil.rmtree(tmpdir, ignore_errors=True)


    def test_menu_discover_devices_excluded_id_stays_commented_out(self):
        """Device IDs listed in config's excluded_ids are written as commented-out entries.

        When the user adds a device ID to "excluded_ids" in sensor_monitor_config.json
        and re-runs discovery, that device must NOT appear as an active entry —
        even if it would normally be classified as a contact or motion sensor.
        """
        import shutil
        tmpdir      = tempfile.mkdtemp()
        config_path = os.path.join(tmpdir, "sensor_monitor_config.json")

        # Pre-populate config with excluded_ids containing device 555001 (Front Door Sensor)
        existing_config = ('{\n'
                           '  "excluded_ids": [555001],\n'
                           '  "devices": [],\n'
                           '  "variables": []\n'
                           '}\n')
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(existing_config)

        orig_disc   = _mod.DISCOVERY_OUTPUT_PATH
        orig_config = _mod.CONFIG_PATH
        _mod.DISCOVERY_OUTPUT_PATH = os.path.join(tmpdir, "device_discovery.json")
        _mod.CONFIG_PATH           = config_path

        try:
            plugin = make_plugin()
            plugin.menuDiscoverDevices()

            with open(config_path, encoding="utf-8") as f:
                content = f.read()

            # 555001 must not appear as an active (uncommented) device entry line
            # Use '"id": 555001' to avoid matching the "excluded_ids" metadata line
            active_lines = [
                l for l in content.splitlines()
                if '"id": 555001' in l and not l.lstrip().startswith("#")
            ]
            # 555001 must appear as a commented-out device entry
            commented_lines = [
                l for l in content.splitlines()
                if '"id": 555001' in l and l.lstrip().startswith("#")
            ]

            self.assertEqual(len(active_lines), 0,
                msg=f"Excluded device 555001 must NOT appear as active entry.\n"
                    f"Config content:\n{content}")
            self.assertGreater(len(commented_lines), 0,
                msg=f"Excluded device 555001 must appear as a commented-out entry.\n"
                    f"Config content:\n{content}")
        finally:
            _mod.DISCOVERY_OUTPUT_PATH = orig_disc
            _mod.CONFIG_PATH           = orig_config
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_menu_discover_devices_excluded_ids_preserved_in_output(self):
        """The excluded_ids list is written into the regenerated config file.

        After re-discovery, the new config must still contain the excluded_ids
        field with the original device ID so that subsequent discovery runs
        continue to respect the exclusion without further user action.
        """
        import shutil
        tmpdir      = tempfile.mkdtemp()
        config_path = os.path.join(tmpdir, "sensor_monitor_config.json")

        existing_config = ('{\n'
                           '  "excluded_ids": [555001],\n'
                           '  "devices": [],\n'
                           '  "variables": []\n'
                           '}\n')
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(existing_config)

        orig_disc   = _mod.DISCOVERY_OUTPUT_PATH
        orig_config = _mod.CONFIG_PATH
        _mod.DISCOVERY_OUTPUT_PATH = os.path.join(tmpdir, "device_discovery.json")
        _mod.CONFIG_PATH           = config_path

        try:
            plugin = make_plugin()
            plugin.menuDiscoverDevices()

            with open(config_path, encoding="utf-8") as f:
                content = f.read()

            self.assertIn('"excluded_ids"', content,
                msg="Regenerated config must contain the 'excluded_ids' field")
            # The ID 555001 must appear in the excluded_ids value (as an integer)
            # Find the excluded_ids line and confirm 555001 is in it
            excl_lines = [l for l in content.splitlines() if '"excluded_ids"' in l]
            self.assertTrue(any("555001" in l for l in excl_lines),
                msg=f"555001 must be present in excluded_ids in the regenerated config.\n"
                    f"excluded_ids lines: {excl_lines}\n"
                    f"Config content:\n{content}")
        finally:
            _mod.DISCOVERY_OUTPUT_PATH = orig_disc
            _mod.CONFIG_PATH           = orig_config
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_menu_discover_devices_skips_virtual_plugin_devices(self):
        """Devices from excluded plugin IDs are completely absent from discovery output.

        Device 555005 'Virtual Door Switch' has onState, 'door' in its name, and
        would normally be classified as a contact sensor — but its pluginId marks
        it as a Virtual Device.  It must not appear anywhere in the config file,
        not even as a commented-out entry.
        """
        import shutil
        tmpdir      = tempfile.mkdtemp()
        config_path = os.path.join(tmpdir, "sensor_monitor_config.json")

        orig_disc   = _mod.DISCOVERY_OUTPUT_PATH
        orig_config = _mod.CONFIG_PATH
        _mod.DISCOVERY_OUTPUT_PATH = os.path.join(tmpdir, "device_discovery.json")
        _mod.CONFIG_PATH           = config_path

        try:
            plugin = make_plugin()
            plugin.menuDiscoverDevices()

            with open(config_path, encoding="utf-8") as f:
                content = f.read()

            self.assertNotIn('"id": 555005', content,
                msg=f"Virtual device 555005 must not appear in config at all.\n"
                    f"Config content:\n{content}")
        finally:
            _mod.DISCOVERY_OUTPUT_PATH = orig_disc
            _mod.CONFIG_PATH           = orig_config
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_menu_discover_devices_skips_alexa_plugin_devices(self):
        """Devices from the Alexa plugin are completely absent from discovery output.

        Device 555006 'HA Garage Door Gen1' has onState, 'garage' in its name,
        and would normally be classified as a contact sensor — but its pluginId
        marks it as an Alexa mirror device.  It must not appear anywhere in the
        config file, not even as a commented-out entry.

        The Alexa plugin creates a named mirror for every exposed Indigo device,
        so real switches exposed to Alexa appear as sensor candidates unless
        the plugin ID is excluded.
        """
        import shutil
        tmpdir      = tempfile.mkdtemp()
        config_path = os.path.join(tmpdir, "sensor_monitor_config.json")

        orig_disc   = _mod.DISCOVERY_OUTPUT_PATH
        orig_config = _mod.CONFIG_PATH
        _mod.DISCOVERY_OUTPUT_PATH = os.path.join(tmpdir, "device_discovery.json")
        _mod.CONFIG_PATH           = config_path

        try:
            plugin = make_plugin()
            plugin.menuDiscoverDevices()

            with open(config_path, encoding="utf-8") as f:
                content = f.read()

            self.assertNotIn('"id": 555006', content,
                msg=f"Alexa device 555006 must not appear in config at all.\n"
                    f"Config content:\n{content}")
        finally:
            _mod.DISCOVERY_OUTPUT_PATH = orig_disc
            _mod.CONFIG_PATH           = orig_config
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_menu_discover_devices_skips_name_excluded_devices(self):
        """Devices with name exclusion keywords do not appear in config at all.

        Devices 555007-555013 all have contact keywords (door/garage) in their
        names AND onState, but also have exclusion keywords that veto name-based
        classification:
          555007 - Front Door Luminance    (luminance)
          555008 - Front Door Temperature  (temperature)
          555009 - HA Garage Freezer Power (power)
          555010 - Garage Loft Repeater    (repeater + plug)
          555011 - HA Garage Door Control  (control)
          555012 - Garage Door Virtual     (virtual)
          555013 - HA Garage Strip Lights  (lights)

        None must appear anywhere in the generated config file.
        """
        import shutil
        tmpdir      = tempfile.mkdtemp()
        config_path = os.path.join(tmpdir, "sensor_monitor_config.json")

        orig_disc   = _mod.DISCOVERY_OUTPUT_PATH
        orig_config = _mod.CONFIG_PATH
        _mod.DISCOVERY_OUTPUT_PATH = os.path.join(tmpdir, "device_discovery.json")
        _mod.CONFIG_PATH           = config_path

        try:
            plugin = make_plugin()
            plugin.menuDiscoverDevices()

            with open(config_path, encoding="utf-8") as f:
                content = f.read()

            excluded = {
                555007: "Front Door Luminance",
                555008: "Front Door Temperature",
                555009: "HA Garage Freezer Power",
                555010: "Garage Loft Repeater Smart Plug",
                555011: "HA Garage Door Control",
                555012: "Garage Door Virtual",
                555013: "HA Garage Strip Lights",
            }
            for dev_id, dev_name in excluded.items():
                self.assertNotIn(f'"id": {dev_id}', content,
                    msg=f"Name-excluded device {dev_id} '{dev_name}' must not "
                        f"appear in config at all.\nConfig content:\n{content}")
        finally:
            _mod.DISCOVERY_OUTPUT_PATH = orig_disc
            _mod.CONFIG_PATH           = orig_config
            shutil.rmtree(tmpdir, ignore_errors=True)


# ======================================
# v1.9.11 DEEP-REVIEW REGRESSION TESTS
# ======================================

import json as _json


class TestGroupCommRestart(unittest.TestCase):
    """v1.9.11 regression: didDeviceCommPropertyChange must watch memberIds.

    The pre-fix code compared memberList — the transient Members-list
    SELECTION widget — so membership edits saved via the ConfigUI never
    restarted comm and the in-memory group stayed stale until plugin restart.
    memberIds (hidden textfield) is the persistent membership store that
    deviceStartComm parses.
    """

    class _Dev:
        def __init__(self, props):
            self.pluginProps = props

    def test_memberids_change_restarts_comm(self):
        old = self._Dev({"memberIds": "1,2",   "memberList": [], "availableList": []})
        new = self._Dev({"memberIds": "1,2,3", "memberList": [], "availableList": []})
        self.assertTrue(Plugin.didDeviceCommPropertyChange(old, new))

    def test_ui_only_changes_do_not_restart_comm(self):
        old = self._Dev({"memberIds": "1,2", "memberList": [],    "folderFilter": "__all__"})
        new = self._Dev({"memberIds": "1,2", "memberList": ["1"], "folderFilter": "12345"})
        self.assertFalse(Plugin.didDeviceCommPropertyChange(old, new))


class TestConfigVariablesGuard(unittest.TestCase):
    """v1.9.11 regression: a malformed variables entry is skipped with a
    warning — it must NOT raise out of _load_config (and hence __init__),
    which previously killed the whole plugin at startup."""

    def test_malformed_variable_entries_skipped_good_ones_kept(self):
        plugin = make_plugin()
        cfg = {
            "devices": [],
            "variables": [
                {"id": "not-a-number", "name": "Bad Id"},
                {"name": "Missing Id"},
                {"id": None, "name": "Null Id"},
                {"id": 241032502, "label": "Lux"},
            ],
        }
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(cfg, f)
            plugin._load_config(path)   # must not raise
        finally:
            os.unlink(path)
        self.assertEqual(list(plugin.variable_monitor.keys()), [241032502])
        self.assertEqual(plugin.variable_monitor[241032502]["label"], "Lux")


class TestEntryEscaping(unittest.TestCase):
    """v1.9.11 regression: generated config entries are emitted via
    json.dumps, so a device name containing quotes/backslashes can no
    longer corrupt the generated config file."""

    def test_quoted_name_round_trips(self):
        plugin = make_plugin()
        dev  = MockDevice(999, 'Back "Patio" Door', states={"contact": True})
        line = plugin._disc_config_entry(dev, {"contact": True})
        parsed = _json.loads(line)
        self.assertEqual(parsed["name"],  'Back "Patio" Door')
        self.assertEqual(parsed["state"], "contact")
        self.assertEqual(parsed["on_text"], "CLOSED")

    def test_user_overrides_carried_on_rediscovery(self):
        plugin = make_plugin()
        dev = MockDevice(42, "Some Door", states={"contact": True})
        overrides = {(42, "contact"): {"id": 42, "state": "contact",
                                       "label": "My Door", "on_text": "SHUT"}}
        line = plugin._disc_config_entry(dev, {"contact": True},
                                         overrides_map=overrides)
        parsed = _json.loads(line)
        self.assertEqual(parsed["label"],   "My Door")
        self.assertEqual(parsed["on_text"], "SHUT")
        self.assertEqual(parsed["off_text"], "OPEN")  # non-overridden default kept


class TestReadExistingConfig(unittest.TestCase):
    """v1.9.11 regression: re-discovery preserves the user's variables
    section, excluded_ids and per-entry customisations — and refuses to
    rewrite a config file it cannot parse."""

    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_missing_file_is_ok_and_empty(self):
        plugin = make_plugin()
        ok, excl, var_entries, overrides = plugin._read_existing_config(
            "/nonexistent/dam/config.json")
        self.assertTrue(ok)
        self.assertEqual(excl, set())
        self.assertEqual(var_entries, [])
        self.assertEqual(overrides, {})

    def test_valid_file_extracts_all_sections(self):
        plugin = make_plugin()
        path = self._write(
            '{\n'
            '  "excluded_ids": [111, 222],\n'
            '  "devices": [\n'
            '    # comment line to strip\n'
            '    {"id": 42, "state": "contact", "label": "My Door", "on_text": "SHUT"},\n'
            '  ],\n'
            '  "variables": [\n'
            '    {"id": 241032502, "label": "Lux"},\n'
            '  ]\n'
            '}\n'
        )
        try:
            ok, excl, var_entries, overrides = plugin._read_existing_config(path)
        finally:
            os.unlink(path)
        self.assertTrue(ok)
        self.assertEqual(excl, {111, 222})
        self.assertEqual(var_entries, [{"id": 241032502, "label": "Lux"}])
        self.assertIn((42, "contact"), overrides)
        self.assertEqual(overrides[(42, "contact")]["label"], "My Door")

    def test_corrupt_file_flags_not_ok(self):
        plugin = make_plugin()
        path = self._write("{ this is not json at all")
        try:
            ok, excl, var_entries, overrides = plugin._read_existing_config(path)
        finally:
            os.unlink(path)
        self.assertFalse(ok)

    def test_discovery_preserves_variables_and_aborts_on_corrupt(self):
        import shutil
        tmpdir      = tempfile.mkdtemp()
        config_path = os.path.join(tmpdir, "dam_config.json")
        orig_disc   = _mod.DISCOVERY_OUTPUT_PATH
        orig_config = _mod.CONFIG_PATH
        _mod.DISCOVERY_OUTPUT_PATH = os.path.join(tmpdir, "device_discovery.json")
        _mod.CONFIG_PATH           = config_path
        try:
            plugin = make_plugin()

            # 1. Existing config with a variables entry + an exclusion survives re-discovery.
            with open(config_path, "w", encoding="utf-8") as f:
                f.write('{"excluded_ids": [777], "devices": [],\n'
                        ' "variables": [{"id": 241032502, "label": "Lux"}]}\n')
            plugin.menuDiscoverDevices()
            with open(config_path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn('"id": 241032502', content,
                          msg=f"variables section lost on re-discovery:\n{content}")
            self.assertIn("777", content.split('"excluded_ids"')[1].split("]")[0],
                          msg="excluded_ids lost on re-discovery")

            # 2. Corrupt existing config must NOT be overwritten.
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("{ definitely broken json")
            plugin.menuDiscoverDevices()
            with open(config_path, encoding="utf-8") as f:
                after = f.read()
            self.assertEqual(after, "{ definitely broken json",
                             msg="discovery clobbered an unreadable config file")
        finally:
            _mod.DISCOVERY_OUTPUT_PATH = orig_disc
            _mod.CONFIG_PATH           = orig_config
            shutil.rmtree(tmpdir, ignore_errors=True)


# ======================================
# v1.9.12 DEEP-REVIEW REGRESSION TESTS
# ======================================


class _MockRelayDevice(MockDevice):
    """Class name ends with 'RelayDevice' so the actuator-class veto sees it
    exactly as it sees a real indigo.RelayDevice (locks, relays, openers)."""
    pass


class TestSignificantStates(unittest.TestCase):
    """v1.9.12 regression: bookkeeping-state churn (lastSeen, linkQuality,
    battery...) must not count as a significant change — zigbee2mqtt
    duplicate publishes bump lastSeen and used to double-fire fireOn='any'
    group triggers."""

    def test_bookkeeping_only_change_is_not_significant(self):
        old = MockDevice(1, "S", states={"contact": True, "lastSeen": 100, "linkquality": 50})
        new = MockDevice(1, "S", states={"contact": True, "lastSeen": 200, "linkquality": 60})
        self.assertFalse(Plugin._significant_states_changed(old, new))

    def test_real_state_change_is_significant(self):
        old = MockDevice(1, "S", states={"contact": True,  "lastSeen": 100})
        new = MockDevice(1, "S", states={"contact": False, "lastSeen": 200})
        self.assertTrue(Plugin._significant_states_changed(old, new))

    def test_added_state_key_is_significant(self):
        old = MockDevice(1, "S", states={"contact": True})
        new = MockDevice(1, "S", states={"contact": True, "tamper": True})
        self.assertTrue(Plugin._significant_states_changed(old, new))


class TestGroupTriggerFiring(unittest.TestCase):
    """v1.9.12: first direct tests of the group-trigger firing path (the
    plugin's core feature — previously untested), including the fireOn
    direction filter, bookkeeping-churn suppression and per-trigger
    failure isolation."""

    GROUP_ID  = 5555
    MEMBER_ID = 101

    def setUp(self):
        self.plugin = make_plugin()
        self.plugin.device_groups[self.GROUP_ID] = {
            "name": "Test Group", "members": {self.MEMBER_ID}}
        self.plugin._rebuild_group_index()
        mock_indigo.trigger.execute.reset_mock()

    def _trigger(self, trig_id=1, fire_on="any"):
        trigger = MagicMock()
        trigger.id           = trig_id
        trigger.pluginTypeId = "damGroupChange"
        trigger.name         = f"Test Trigger {trig_id}"
        trigger.pluginProps  = {"groupDevice": str(self.GROUP_ID),
                                "fireOn": fire_on, "saveBool": False}
        self.plugin.event_triggers[trig_id] = trigger
        return trigger

    def _update(self, old_on, new_on, old_states=None, new_states=None):
        old = MockDevice(self.MEMBER_ID, "Member", on_state=old_on,
                         states=old_states or {})
        new = MockDevice(self.MEMBER_ID, "Member", on_state=new_on,
                         states=new_states or {})
        self.plugin.deviceUpdated(old, new)

    def test_any_fires_on_onstate_flip(self):
        self._trigger(fire_on="any")
        self._update(False, True)
        mock_indigo.trigger.execute.assert_called_once()

    def test_any_does_not_fire_on_bookkeeping_churn(self):
        self._trigger(fire_on="any")
        self._update(False, False,
                     old_states={"lastSeen": 1, "occupancy": False},
                     new_states={"lastSeen": 2, "occupancy": False})
        mock_indigo.trigger.execute.assert_not_called()

    def test_activated_fires_only_on_rising_edge(self):
        self._trigger(fire_on="activated")
        self._update(True, False)   # falling edge — no fire
        mock_indigo.trigger.execute.assert_not_called()
        self._update(False, True)   # rising edge — fires
        mock_indigo.trigger.execute.assert_called_once()

    def test_deactivated_fires_only_on_falling_edge(self):
        self._trigger(fire_on="deactivated")
        self._update(False, True)   # rising edge — no fire
        mock_indigo.trigger.execute.assert_not_called()
        self._update(True, False)   # falling edge — fires
        mock_indigo.trigger.execute.assert_called_once()

    def test_non_member_device_does_not_fire(self):
        self._trigger(fire_on="any")
        old = MockDevice(999, "Stranger", on_state=False)
        new = MockDevice(999, "Stranger", on_state=True)
        self.plugin.deviceUpdated(old, new)
        mock_indigo.trigger.execute.assert_not_called()

    def test_group_toggle_off_suppresses_firing(self):
        self._trigger(fire_on="any")
        self.plugin.group_enabled = False
        self._update(False, True)
        mock_indigo.trigger.execute.assert_not_called()

    def test_one_broken_trigger_does_not_block_the_rest(self):
        broken = self._trigger(trig_id=1)
        broken.pluginProps = None   # .get on None raises inside the loop
        self._trigger(trig_id=2)
        self._update(False, True)
        mock_indigo.trigger.execute.assert_called_once()
        # And the failure was logged, not swallowed.
        self.assertTrue(self.plugin.logger.error.called)


class TestActuatorClassVeto(unittest.TestCase):
    """v1.9.12 regression: actuator device classes (RelayDevice etc.) must
    never be classified as sensors by NAME keywords — 'Front Door Lock' and
    'Hall Garage Door Opener' are actuators. State-name matching still wins."""

    def test_relay_with_door_name_is_not_contact(self):
        plugin = make_plugin()
        dev = _MockRelayDevice(1, "Front Door Lock", on_state=False)
        self.assertFalse(plugin._disc_is_contact(dev, {}))

    def test_relay_with_motion_name_is_not_motion(self):
        plugin = make_plugin()
        dev = _MockRelayDevice(2, "Drive Motion Floodlight Relay", on_state=False)
        self.assertFalse(plugin._disc_is_motion(dev, {}))

    def test_relay_with_real_contact_state_still_classifies(self):
        plugin = make_plugin()
        dev = _MockRelayDevice(3, "Odd Relay", on_state=False,
                               states={"contact": True})
        self.assertTrue(plugin._disc_is_contact(dev, {"contact": True}))

    def test_plain_sensor_by_name_still_classifies(self):
        plugin = make_plugin()
        dev = MockDevice(4, "Shed Door Sensor", on_state=False)
        self.assertTrue(plugin._disc_is_contact(dev, {}))


class TestToggleFlush(unittest.TestCase):
    """v1.9.12: _set_flag flips the attribute and the pref, and survives the
    harness having no savePluginPrefs (the flush is best-effort)."""

    def test_set_flag_flips_and_persists_pref(self):
        plugin = make_plugin(prefs={"logEnabled": True})
        plugin._set_flag("logEnabled", "log_enabled", "Device Change Log")
        self.assertFalse(plugin.log_enabled)
        self.assertFalse(plugin.pluginPrefs["logEnabled"])
        plugin._set_flag("logEnabled", "log_enabled", "Device Change Log")
        self.assertTrue(plugin.log_enabled)


# ======================================
# v1.9.13 DEEP-REVIEW REGRESSION TESTS
# ======================================


class TestConfigDedupe(unittest.TestCase):
    """v1.9.13 regression: duplicate (device, state) config entries are
    skipped with a warning — duplicates used to double-log every change."""

    def test_duplicate_pair_skipped(self):
        plugin = make_plugin()
        cfg = {"devices": [
            {"id": 42, "state": "contact", "label": "First"},
            {"id": 42, "state": "contact", "label": "Second (dupe)"},
            {"id": 42, "state": "onState", "label": "Different state - kept"},
        ], "variables": []}
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(cfg, f)
            plugin._load_config(path)
        finally:
            os.unlink(path)
        self.assertEqual(len(plugin.device_monitor[42]), 2)
        labels = [c["label"] for c in plugin.device_monitor[42]]
        self.assertIn("First", labels)
        self.assertNotIn("Second (dupe)", labels)


class TestValidateEventConfigUi(unittest.TestCase):
    """v1.9.13: a damGroupChange trigger can no longer be saved without a
    group selected (it used to save fine and silently never fire)."""

    def test_unset_group_rejected(self):
        plugin = make_plugin()
        ok, values, errors = plugin.validateEventConfigUi(
            {"groupDevice": ""}, "damGroupChange", 1)
        self.assertFalse(ok)

    def test_none_placeholder_rejected(self):
        plugin = make_plugin()
        ok, values, errors = plugin.validateEventConfigUi(
            {"groupDevice": "none"}, "damGroupChange", 1)
        self.assertFalse(ok)

    def test_valid_group_accepted(self):
        plugin = make_plugin()
        result = plugin.validateEventConfigUi(
            {"groupDevice": "12345", "saveBool": False}, "damGroupChange", 1)
        self.assertTrue(result[0])

    def test_savebool_without_savevar_rejected(self):
        plugin = make_plugin()
        ok, values, errors = plugin.validateEventConfigUi(
            {"groupDevice": "12345", "saveBool": True, "saveVar": ""},
            "damGroupChange", 1)
        self.assertFalse(ok)


class TestDeletionWarnings(unittest.TestCase):
    """v1.9.13: deletion warnings are configuration diagnostics — no longer
    gated by the Device Change Log toggle, and deleting a device that is a
    member of a damGroup now warns naming the group."""

    def test_monitored_deletion_warns_even_with_log_toggle_off(self):
        plugin = make_plugin()
        plugin.log_enabled = False
        dev = MockDevice(812537401, "Basin Occupancy Sensor")
        plugin.deviceDeleted(dev)
        warn_text = " ".join(str(c) for c in plugin.logger.warning.call_args_list)
        self.assertIn("Monitored device deleted", warn_text)

    def test_group_member_deletion_warns_with_group_name(self):
        plugin = make_plugin()
        plugin.device_groups[5555] = {"name": "Bathroom Sensors", "members": {777}}
        plugin._rebuild_group_index()
        dev = MockDevice(777, "Some Bathroom Sensor")
        plugin.deviceDeleted(dev)
        warn_text = " ".join(str(c) for c in plugin.logger.warning.call_args_list)
        self.assertIn("Bathroom Sensors", warn_text)
        self.assertIn("777", warn_text)


# ======================================
# v1.10.0 FEATURE TESTS
# ======================================


class TestTestFireMenu(unittest.TestCase):
    """v1.10.0: Test Fire All Group Triggers menu item fires every registered
    damGroupChange trigger once, isolating per-trigger failures."""

    def test_fires_each_registered_trigger(self):
        plugin = make_plugin()
        mock_indigo.trigger.execute.reset_mock()
        for trig_id in (1, 2):
            trigger = MagicMock()
            trigger.id           = trig_id
            trigger.pluginTypeId = "damGroupChange"
            trigger.name         = f"T{trig_id}"
            trigger.pluginProps  = {"groupDevice": "1", "fireOn": "any"}
            plugin.event_triggers[trig_id] = trigger
        plugin.menuTestFireGroupTriggers()
        self.assertEqual(mock_indigo.trigger.execute.call_count, 2)

    def test_no_triggers_logs_not_errors(self):
        plugin = make_plugin()
        mock_indigo.trigger.execute.reset_mock()
        plugin.menuTestFireGroupTriggers()
        mock_indigo.trigger.execute.assert_not_called()
        plugin.logger.error.assert_not_called()


class TestClosedPrefsConfigUi(unittest.TestCase):
    """v1.10.0: PluginConfig saves apply immediately, mirroring __init__."""

    def test_applies_new_values(self):
        plugin = make_plugin(prefs={"logEnabled": True, "groupEnabled": True,
                                    "timestampEnabled": True})
        plugin.closedPrefsConfigUi(
            {"logEnabled": False, "groupEnabled": False,
             "timestampEnabled": False, "showDebugInfo": True}, False)
        self.assertFalse(plugin.log_enabled)
        self.assertFalse(plugin.group_enabled)
        self.assertFalse(plugin.timestamp_enabled)
        self.assertTrue(plugin.debug)

    def test_cancel_changes_nothing(self):
        plugin = make_plugin(prefs={"logEnabled": True})
        plugin.closedPrefsConfigUi({"logEnabled": False}, True)
        self.assertTrue(plugin.log_enabled)


class TestGroupMemberValidation(unittest.TestCase):
    """v1.10.0: deviceStartComm warns when a group's memberIds contains ids
    that no longer exist in Indigo."""

    def test_missing_member_warns(self):
        plugin = make_plugin()
        mock_indigo.devices = make_device_registry()   # fixture devices only
        grp = MockDevice(4242, "My Group", device_type_id="damGroup")
        grp.pluginProps = {"memberIds": "812537401,999999999"}
        grp.updateStatesOnServer = MagicMock()
        plugin.deviceStartComm(grp)
        warn_text = " ".join(str(c) for c in plugin.logger.warning.call_args_list)
        self.assertIn("999999999", warn_text)
        self.assertNotIn("812537401", warn_text)

    def test_all_members_present_no_warning(self):
        plugin = make_plugin()
        mock_indigo.devices = make_device_registry()
        grp = MockDevice(4242, "My Group", device_type_id="damGroup")
        grp.pluginProps = {"memberIds": "812537401"}
        grp.updateStatesOnServer = MagicMock()
        plugin.deviceStartComm(grp)
        plugin.logger.warning.assert_not_called()


class TestDiscoveryAutoReload(unittest.TestCase):
    """v1.10.0: Discover Devices applies the freshly-written config
    immediately instead of requiring a manual Reload Config File."""

    def test_discovery_reloads_written_config(self):
        import shutil
        tmpdir      = tempfile.mkdtemp()
        orig_disc   = _mod.DISCOVERY_OUTPUT_PATH
        orig_config = _mod.CONFIG_PATH
        _mod.DISCOVERY_OUTPUT_PATH = os.path.join(tmpdir, "device_discovery.json")
        _mod.CONFIG_PATH           = os.path.join(tmpdir, "dam_config.json")
        try:
            mock_indigo.devices = MockDevices()
            sensor = MockDevice(31337, "Porch Door Sensor", on_state=False)
            mock_indigo.devices[31337] = sensor
            plugin = make_plugin()
            plugin.menuDiscoverDevices()
            self.assertIn(31337, plugin.device_monitor,
                msg="discovered sensor should be live immediately after discovery")
        finally:
            _mod.DISCOVERY_OUTPUT_PATH = orig_disc
            _mod.CONFIG_PATH           = orig_config
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestManualEntryPreservation(unittest.TestCase):
    """v1.10.0: a hand-added ACTIVE config entry for a device discovery does
    NOT classify (neither contact nor motion) survives re-discovery in the
    'Manually added entries' section — previously it was silently dropped."""

    def test_manual_entry_survives_rediscovery(self):
        import shutil
        tmpdir      = tempfile.mkdtemp()
        config_path = os.path.join(tmpdir, "dam_config.json")
        orig_disc   = _mod.DISCOVERY_OUTPUT_PATH
        orig_config = _mod.CONFIG_PATH
        _mod.DISCOVERY_OUTPUT_PATH = os.path.join(tmpdir, "device_discovery.json")
        _mod.CONFIG_PATH           = config_path
        try:
            # A thermostat-ish device discovery won't classify, plus a manual
            # entry for it in the existing config.
            mock_indigo.devices = MockDevices()
            odd = MockDevice(88888, "Boiler Flow Meter", on_state=False,
                             states={"sensorValue": 1.5})
            mock_indigo.devices[88888] = odd
            with open(config_path, "w", encoding="utf-8") as f:
                f.write('{"excluded_ids": [], "devices": [\n'
                        ' {"id": 88888, "state": "sensorValue", "label": "Boiler Flow"}\n'
                        '], "variables": []}\n')
            plugin = make_plugin()
            plugin.menuDiscoverDevices()
            with open(config_path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Manually added entries", content,
                          msg=f"manual section missing:\n{content}")
            self.assertIn('"id": 88888', content)
            # And it is live after the auto-reload.
            self.assertIn(88888, plugin.device_monitor)
        finally:
            _mod.DISCOVERY_OUTPUT_PATH = orig_disc
            _mod.CONFIG_PATH           = orig_config
            shutil.rmtree(tmpdir, ignore_errors=True)


# ======================================
# TEST: WHERE THE ACTIVITY NARRATION GOES
#
# The plugin used to push one line straight into the shared Indigo event log
# for every monitored change, with no way to stop it. Measured on the author's
# estate over the 7 days to 06-09-2026 that was 5,529 lines, 790 a day, about a
# third of every line in the log. It now goes to the plugin's own log unless
# the user opts back in with logActivityToEventLog.
#
# The routing model these tests assert against, taken from Indigo's
# plugin_base.py: self.logger carries a file handler at THREADDEBUG and an
# event-log handler at INFO. So .debug() reaches the plugin's file only, and
# .info() and above reach both.
# ======================================

class TestActivityRouting(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices   = make_device_registry()
        mock_indigo.variables = make_variable_registry()

    @staticmethod
    def _trip_sensor(plugin):
        """Drive one monitored device change - the 790-a-day line."""
        orig = MockDevice(812537401, "Basin Occupancy Sensor", on_state=False)
        new  = MockDevice(812537401, "Basin Occupancy Sensor", on_state=True)
        plugin.deviceUpdated(orig, new)

    # --- default: quiet ---

    def test_default_is_quiet_on_a_fresh_install(self):
        """No pref at all means the narration stays out of the event log.

        A fresh install has never opened the dialog, so the key is absent
        entirely. That path has to default to quiet or the upgrade changes
        nothing for anybody.
        """
        plugin = make_plugin()
        self.assertFalse(plugin.activity_to_event_log)

    def test_state_change_does_not_reach_the_event_log_by_default(self):
        """THE headline: a sensor trip leaves the shared event log alone."""
        plugin = make_plugin()
        self._trip_sensor(plugin)

        self.assertEqual(event_log_messages(plugin), [],
            msg=f"Event log should be untouched. Got: {event_log_messages(plugin)}")

    def test_state_change_still_reaches_the_plugins_own_log_by_default(self):
        """Nothing is lost - the line still exists, and reads the same."""
        plugin = make_plugin()
        self._trip_sensor(plugin)

        msgs = plugin_file_messages(plugin)
        self.assertTrue(
            any("Basin Occupancy Sensor" in m and m.endswith("ON") for m in msgs),
            msg=f"Expected the narration in the plugin log. Got: {msgs}")

    def test_variable_change_does_not_reach_the_event_log_by_default(self):
        """A chatty variable follows the same route as a chatty sensor."""
        plugin = make_plugin()
        orig = MockVariable(241032502, "Lux_Level", "450")
        new  = MockVariable(241032502, "Lux_Level", "520")
        plugin.variableUpdated(orig, new)

        self.assertEqual(event_log_messages(plugin), [],
            msg=f"Event log should be untouched. Got: {event_log_messages(plugin)}")
        self.assertTrue(
            any("450" in m and "520" in m for m in plugin_file_messages(plugin)),
            msg="The variable line must still reach the plugin's own log.")

    # --- opted back in ---

    def test_opting_in_puts_the_narration_back_in_the_event_log(self):
        """A user who reads the event log as an activity feed gets it back."""
        plugin = make_plugin({"logActivityToEventLog": True})
        self.assertTrue(plugin.activity_to_event_log)
        self._trip_sensor(plugin)

        msgs = event_log_messages(plugin)
        self.assertTrue(
            any("Basin Occupancy Sensor" in m and m.endswith("ON") for m in msgs),
            msg=f"Expected the narration in the event log. Got: {msgs}")

    def test_opting_in_still_writes_to_the_plugins_own_log(self):
        """Opting in adds a destination, it does not move the line."""
        plugin = make_plugin({"logActivityToEventLog": True})
        self._trip_sensor(plugin)

        self.assertTrue(
            any("Basin Occupancy Sensor" in m for m in plugin_file_messages(plugin)),
            msg="logger.info reaches the file handler too - nothing is lost.")

    def test_the_line_reads_identically_on_both_routes(self):
        """Only the destination changes, never the wording."""
        quiet = make_plugin()
        loud  = make_plugin({"logActivityToEventLog": True})
        self._trip_sensor(quiet)
        self._trip_sensor(loud)

        def narration(msgs):
            return [m for m in msgs if "Basin Occupancy Sensor" in m]

        self.assertEqual(
            [m[m.index("]") + 1:] for m in narration(activity_messages(quiet))],
            [m[m.index("]") + 1:] for m in narration(activity_messages(loud))],
            msg="Same message, different destination.")

    def test_a_string_false_pref_is_still_quiet(self):
        """bool("false") is True, and here that would re-flood the event log.

        Indigo re-serialises saved textfield and menu values as strings. A
        checkbox normally round-trips as a real bool, but this pref defaults to
        quiet, so the wrong coercion fails in the expensive direction - hence
        as_bool() rather than bool().
        """
        for junk in ("false", "0", "no", "off", "f", ""):
            with self.subTest(pref=junk):
                plugin = make_plugin({"logActivityToEventLog": junk})
                self.assertFalse(plugin.activity_to_event_log,
                    msg=f"pref {junk!r} must not turn the event log back on")

    def test_a_string_true_pref_opts_in(self):
        """The mirror case, so the coercion is not simply always-False."""
        for truthy in ("true", "1", "yes", "on", "t", True):
            with self.subTest(pref=truthy):
                plugin = make_plugin({"logActivityToEventLog": truthy})
                self.assertTrue(plugin.activity_to_event_log)

    # --- faults must never take the quiet route ---

    def test_a_deleted_monitored_device_still_warns_in_the_event_log(self):
        """Log_Error_Watch.py reads the EVENT log and nothing else.

        A fault that only lands in a plugin's own file is a fault nobody is
        watching, so every warning and error has to keep reaching the shared
        log even when the narration has gone quiet.
        """
        plugin = make_plugin()
        self.assertFalse(plugin.activity_to_event_log)
        plugin.deviceDeleted(MockDevice(812537401, "Basin Occupancy Sensor"))

        plugin.logger.warning.assert_called()
        msgs = event_log_messages(plugin)
        self.assertTrue(
            any("Monitored device deleted" in m for m in msgs),
            msg=f"Deletion warning must reach the event log. Got: {msgs}")

    def test_a_deleted_monitored_variable_still_warns_in_the_event_log(self):
        plugin = make_plugin()
        plugin.variableDeleted(MockVariable(241032502, "Lux_Level"))

        msgs = event_log_messages(plugin)
        self.assertTrue(
            any("Monitored variable deleted" in m for m in msgs),
            msg=f"Deletion warning must reach the event log. Got: {msgs}")

    def test_a_state_read_error_still_reaches_the_event_log(self):
        """An unreadable state is a fault, not narration."""
        class ExplodingStates(dict):
            def get(self, *a, **k):
                raise RuntimeError("states unavailable")

        plugin = make_plugin()
        plugin.device_monitor[777001] = [{"state": "presence", "label": "Presence"}]
        orig = MockDevice(777001, "Broken Sensor")
        new  = MockDevice(777001, "Broken Sensor")
        orig.states = ExplodingStates()
        new.states  = ExplodingStates()
        plugin.deviceUpdated(orig, new)

        plugin.logger.error.assert_called()
        self.assertTrue(
            any("Broken Sensor" in m for m in event_log_messages(plugin)),
            msg="A state-read error must reach the event log.")

    def test_a_group_trigger_failure_still_reaches_the_event_log(self):
        """Found by mutation sweep: demoting this error to debug left the whole
        suite green, so nothing was guarding the one handler that catches a
        failure in the plugin's actual product - the group triggers."""
        class ExplodingOnState(MockDevice):
            @property
            def onState(self):
                raise RuntimeError("device object unusable")

            @onState.setter
            def onState(self, value):
                pass

        plugin = make_plugin()
        plugin.group_members = {777002}
        orig = ExplodingOnState(777002, "Group Member")
        new  = ExplodingOnState(777002, "Group Member")
        plugin.deviceUpdated(orig, new)

        plugin.logger.error.assert_called()
        self.assertTrue(
            any("group-trigger error" in m for m in event_log_messages(plugin)),
            msg=f"Group-trigger failure must reach the event log. "
                f"Got: {event_log_messages(plugin)}")

    def test_a_missing_device_at_startup_still_warns_in_the_event_log(self):
        """The one fault this plugin actually raises in normal service -
        6 occurrences in the 7 days measured, all of them stale config ids."""
        mock_indigo.devices = make_device_registry(missing_ids=[812537401])
        plugin = make_plugin()
        plugin.startup()

        msgs = event_log_messages(plugin)
        self.assertTrue(
            any("not found" in m for m in msgs),
            msg=f"Stale-id warning must reach the event log. Got: {msgs}")

    def test_no_narration_call_writes_straight_to_the_event_log(self):
        """Structural guard: _log_activity is the ONLY route for narration.

        Written against the parsed tree rather than the file text so a
        changelog entry describing the old behaviour cannot satisfy it. The
        two deviceUpdated/variableUpdated indigo.server.log() calls that
        remain are the rename notices, which are deliberate keeps - rare
        configuration events, none at all in the 7 days measured.
        """
        import ast
        tree = ast.parse(io_open_plugin_source())
        offenders = []
        for func in ast.walk(tree):
            if not isinstance(func, ast.FunctionDef):
                continue
            if func.name not in ("deviceUpdated", "variableUpdated"):
                continue
            for node in ast.walk(func):
                if not isinstance(node, ast.Call):
                    continue
                target = ast.unparse(node.func)
                if target != "indigo.server.log":
                    continue
                text = " ".join(
                    n.value for n in ast.walk(node)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str))
                if "renamed" not in text:
                    offenders.append(f"{func.name}: {ast.unparse(node)[:90]}")
        self.assertEqual(offenders, [],
            msg="Narration must go through _log_activity, not indigo.server.log.")

    def test_the_guard_above_can_actually_see_a_violation(self):
        """A structural guard that matches nothing passes vacuously."""
        import ast
        tree = ast.parse(io_open_plugin_source())
        found = [
            n for func in ast.walk(tree)
            if isinstance(func, ast.FunctionDef) and func.name == "deviceUpdated"
            for n in ast.walk(func)
            if isinstance(n, ast.Call) and ast.unparse(n.func) == "indigo.server.log"
        ]
        self.assertEqual(len(found), 1,
            msg="Expected exactly the rename notice to remain in deviceUpdated.")


# ======================================
# TEST: THE NEW PREF IS WIRED UP EVERYWHERE
# ======================================

class TestActivityPrefPlumbing(unittest.TestCase):
    """The pref has four touch points and every one of them has been
    forgotten at least once in this plugin's history: __init__, the config
    dialog, the menu toggle and the PluginConfig.xml field itself."""

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices   = make_device_registry()
        mock_indigo.variables = make_variable_registry()

    def test_closed_prefs_config_ui_applies_it_immediately(self):
        plugin = make_plugin()
        plugin.closedPrefsConfigUi(
            {"logActivityToEventLog": True, "logEnabled": True,
             "groupEnabled": True, "timestampEnabled": True}, False)
        self.assertTrue(plugin.activity_to_event_log)

        plugin.closedPrefsConfigUi(
            {"logActivityToEventLog": False, "logEnabled": True,
             "groupEnabled": True, "timestampEnabled": True}, False)
        self.assertFalse(plugin.activity_to_event_log)

    def test_closed_prefs_config_ui_defaults_a_missing_key_to_quiet(self):
        """An older saved dialog has no such key; it must not read as on."""
        plugin = make_plugin({"logActivityToEventLog": True})
        plugin.closedPrefsConfigUi({"logEnabled": True}, False)
        self.assertFalse(plugin.activity_to_event_log)

    def test_menu_toggle_flips_and_persists_it(self):
        plugin = make_plugin()
        plugin.savePluginPrefs = MagicMock()
        plugin.menuToggleActivityInEventLog()

        self.assertTrue(plugin.activity_to_event_log)
        self.assertTrue(plugin.pluginPrefs["logActivityToEventLog"])
        plugin.savePluginPrefs.assert_called()

        plugin.menuToggleActivityInEventLog()
        self.assertFalse(plugin.activity_to_event_log)
        self.assertFalse(plugin.pluginPrefs["logActivityToEventLog"])

    def test_show_plugin_info_reports_it(self):
        plugin = make_plugin()
        mock_indigo.server.log.reset_mock()
        plugin.showPluginInfo()

        text = " ".join(server_log_messages())
        self.assertIn("Activity in Event Log", text)

    def test_startup_line_reports_it(self):
        plugin = make_plugin()
        plugin.startup()

        text = " ".join(_logger_messages(plugin, "info"))
        self.assertIn("ActivityInEventLog", text)

    def test_plugin_config_xml_offers_the_field_defaulting_to_quiet(self):
        """The checkbox has to exist, default false, and not collide."""
        import collections
        import xml.etree.ElementTree as ET
        path = os.path.join(os.path.dirname(_plugin_path), "PluginConfig.xml")
        root = ET.parse(path).getroot()
        fields = {f.get("id"): f for f in root.iter("Field")}

        self.assertIn("logActivityToEventLog", fields)
        self.assertEqual(
            fields["logActivityToEventLog"].get("type"), "checkbox")
        self.assertEqual(
            (fields["logActivityToEventLog"].get("defaultValue") or "").lower(),
            "false",
            msg="The quiet behaviour is the default - that is the whole point.")

        ids = [f.get("id") for f in root.iter("Field")]
        dupes = [i for i, n in collections.Counter(ids).items() if n > 1]
        self.assertEqual(dupes, [],
            msg="A duplicate Field id stops the whole dialog opening.")

    def test_menu_item_callback_exists(self):
        """A MenuItems.xml callback that names no method is a dead menu item."""
        import xml.etree.ElementTree as ET
        path = os.path.join(os.path.dirname(_plugin_path), "MenuItems.xml")
        root = ET.parse(path).getroot()
        callbacks = [m.findtext("CallbackMethod") for m in root.iter("MenuItem")]

        self.assertIn("menuToggleActivityInEventLog", callbacks)
        for name in [c for c in callbacks if c]:
            self.assertTrue(hasattr(Plugin, name),
                msg=f"MenuItems.xml calls {name}, which Plugin does not define.")



# ======================================
# TEST: THE DEBUG PREF CANNOT SILENTLY UNDO THE QUIET DEFAULT
#
# Every other route into the shared event log is now a deliberate choice.
# showDebugInfo is not: Indigo's PluginBase turns self.debug into a property
# whose setter reads "if value:" and lowers indigo_log_handler to DEBUG on
# anything truthy. bool("false") is True, so a pref holding a string - which
# is how Indigo re-serialises a saved textfield or menu value - would put the
# full narration back into the log this change exists to keep clean, with the
# checkbox in the dialog still showing unticked.
# ======================================

class TestDebugPrefCoercion(unittest.TestCase):

    def setUp(self):
        mock_indigo.server.log.reset_mock()
        mock_indigo.devices   = make_device_registry()
        mock_indigo.variables = make_variable_registry()

    def test_a_string_false_does_not_turn_debug_on(self):
        for junk in ("false", "0", "no", "off", "f", ""):
            with self.subTest(pref=junk):
                plugin = make_plugin({"showDebugInfo": junk})
                self.assertIs(plugin.debug, False,
                    msg=f"pref {junk!r} must not read as debug on")

    def test_a_string_false_leaves_the_event_log_handler_at_info(self):
        """The consequence, not the symptom.

        The handler level is what actually decides whether the narration
        reaches the shared event log, so that is what this asserts. A
        mutation that swaps as_bool back for bool() turns this red.
        """
        plugin = make_plugin({"showDebugInfo": "false"})
        plugin.indigo_log_handler.setLevel.assert_called_with(logging.INFO)

    def test_an_unrecognised_string_falls_back_to_quiet(self):
        """as_bool returns the DEFAULT for junk, and the default here is off.

        Guessing True would be the expensive direction: it re-floods a log
        the whole estate shares, and nothing would say why.
        """
        plugin = make_plugin({"showDebugInfo": "maybe"})
        self.assertIs(plugin.debug, False)

    def test_an_absent_pref_is_quiet(self):
        plugin = make_plugin()
        self.assertIs(plugin.debug, False)
        plugin.indigo_log_handler.setLevel.assert_called_with(logging.INFO)

    def test_a_genuine_request_for_debug_is_still_honoured(self):
        """The mirror case, so the coercion is not simply always-False."""
        for truthy in (True, "true", "1", "yes", "on", "t"):
            with self.subTest(pref=truthy):
                plugin = make_plugin({"showDebugInfo": truthy})
                self.assertIs(plugin.debug, True)
                plugin.indigo_log_handler.setLevel.assert_called_with(
                    logging.DEBUG)

    def test_the_config_dialog_path_coerces_it_too(self):
        """closedPrefsConfigUi is a second, separate read of the same pref."""
        plugin = make_plugin({"showDebugInfo": True})
        plugin.closedPrefsConfigUi({"showDebugInfo": "false"}, False)
        self.assertIs(plugin.debug, False)
        plugin.indigo_log_handler.setLevel.assert_called_with(logging.INFO)

    def test_the_other_toggles_are_coerced_the_same_way(self):
        """Same hazard, opposite default: these three default ON, so a junk
        string read through bool() would report a toggle the user switched
        off as still on."""
        plugin = make_plugin({"logEnabled": "false",
                              "groupEnabled": "false",
                              "timestampEnabled": "false"})
        self.assertIs(plugin.log_enabled, False)
        self.assertIs(plugin.group_enabled, False)
        self.assertIs(plugin.timestamp_enabled, False)

    def test_no_pref_is_read_with_a_bare_bool(self):
        """Structural guard: bool() on a pref read is the bug this fixes.

        Parsed, not grepped, so a comment or changelog line mentioning
        bool() cannot satisfy or break it.
        """
        import ast
        tree = ast.parse(io_open_plugin_source())
        offenders = []
        for func in ast.walk(tree):
            if not isinstance(func, ast.FunctionDef):
                continue
            if func.name not in ("__init__", "closedPrefsConfigUi"):
                continue
            for node in ast.walk(func):
                if not (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == "bool"):
                    continue
                inner = ast.unparse(node)
                if "pluginPrefs" in inner or "valuesDict" in inner:
                    offenders.append(f"{func.name}: {inner[:80]}")
        self.assertEqual(offenders, [],
            msg="Prefs must be read through as_bool - bool('false') is True.")

    def test_the_guard_above_can_actually_see_a_violation(self):
        """A structural guard that can never match passes vacuously.

        Feeds it the exact shape it is meant to catch and requires a hit, so
        the guard is proved able to fail before its silence is believed.
        """
        import ast
        sample = ast.parse(
            "class P:\n"
            "    def __init__(self, pluginPrefs):\n"
            "        self.debug = bool(pluginPrefs.get('showDebugInfo', False))\n"
        )
        found = [
            n for func in ast.walk(sample)
            if isinstance(func, ast.FunctionDef) and func.name == "__init__"
            for n in ast.walk(func)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "bool" and "pluginPrefs" in ast.unparse(n)
        ]
        self.assertEqual(len(found), 1,
            msg="The guard cannot see the very shape it exists to reject.")


# ======================================
# TEST: THE DIALOG DESCRIBES WHAT THE PLUGIN ACTUALLY DOES
#
# The dialog is the only explanation most users will ever read, and it went
# stale the moment the destination changed: it still counted three toggles
# beside a fourth, and the master switch still promised the event log. None
# of it is caught by running the plugin, because a plugin never reads its
# own ConfigUI XML - the Indigo client does, once, when the user opens it.
# ======================================

class TestPluginConfigDescriptions(unittest.TestCase):

    NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four",
                    5: "five", 6: "six", 7: "seven", 8: "eight"}

    @staticmethod
    def _config_root():
        import xml.etree.ElementTree as ET
        path = os.path.join(os.path.dirname(_plugin_path), "PluginConfig.xml")
        return ET.parse(path).getroot()

    @staticmethod
    def _menu_toggle_callbacks():
        import xml.etree.ElementTree as ET
        path = os.path.join(os.path.dirname(_plugin_path), "MenuItems.xml")
        root = ET.parse(path).getroot()
        return [c for c in (m.findtext("CallbackMethod")
                            for m in root.iter("MenuItem"))
                if c and c.startswith("menuToggle")]

    def _description(self, field_id):
        for field in self._config_root().iter("Field"):
            if field.get("id") == field_id:
                return (field.findtext("Description") or "")
        self.fail(f"PluginConfig.xml has no field {field_id}")

    def test_the_intro_counts_the_toggles_correctly(self):
        """The count in the intro is prose, so nothing else can check it.

        It said "three" for a week after the fourth toggle arrived directly
        beneath it, which is how a reader learns to distrust the dialog.
        """
        toggles = self._menu_toggle_callbacks()
        intro = ""
        for field in self._config_root().iter("Field"):
            if field.get("id") == "infoLabel":
                intro = (field.findtext("Label") or "").lower()
        self.assertTrue(intro, "PluginConfig.xml has no infoLabel")

        word = self.NUMBER_WORDS[len(toggles)]
        self.assertIn(f"{word} toggles", intro,
            msg=f"The intro must say '{word} toggles' - there are "
                f"{len(toggles)} menu toggles: {toggles}")
        for wrong in set(self.NUMBER_WORDS.values()) - {word}:
            self.assertNotIn(f"{wrong} toggles", intro,
                msg=f"The intro also claims '{wrong} toggles'.")

    def test_every_menu_toggle_has_a_field_in_the_dialog(self):
        """The intro promises the menu mirrors the dialog. Hold it to that."""
        field_ids = {f.get("id") for f in self._config_root().iter("Field")}
        prefs = {"menuToggleDeviceChangeLog":     "logEnabled",
                 "menuToggleGroupTriggers":       "groupEnabled",
                 "menuToggleTimestamps":          "timestampEnabled",
                 "menuToggleActivityInEventLog":  "logActivityToEventLog"}
        for callback in self._menu_toggle_callbacks():
            self.assertIn(callback, prefs,
                msg=f"New menu toggle {callback} - add its pref here and to "
                    f"PluginConfig.xml.")
            self.assertIn(prefs[callback], field_ids,
                msg=f"{callback} flips a pref with no field in the dialog.")

    def test_the_master_switch_no_longer_promises_the_event_log(self):
        """It read 'write ... to the event log', which stopped being true.

        Two fields contradicting each other is worse than either being
        wrong on its own: the reader cannot tell which to believe.
        """
        text = self._description("logEnabled").lower()
        self.assertIn("own log", text,
            msg="The master switch must say where the changes actually go.")
        self.assertNotIn("write monitored device and variable changes to the "
                         "event log", text,
            msg="That is the pre-change wording, and it is now false.")

    def test_the_event_log_field_admits_the_master_switch_can_silence_it(self):
        """It claimed the changes ALWAYS reach the plugin's own log.

        They do not: deviceUpdated returns on 'if not self.log_enabled'
        before any narration is produced, so that checkbox silences both
        routes and this field has to say so.
        """
        text = self._description("logActivityToEventLog").lower()
        self.assertNotIn("always", text,
            msg="Nothing here is unconditional - the master switch outranks it.")
        self.assertIn("device change log", text,
            msg="This field must name the switch that can silence it.")

    def test_the_master_switch_really_does_silence_both_routes(self):
        """The claim above, checked against the code rather than trusted."""
        plugin = make_plugin({"logEnabled": False,
                              "logActivityToEventLog": True})
        orig = MockDevice(812537401, "Basin Occupancy Sensor", on_state=False)
        new  = MockDevice(812537401, "Basin Occupancy Sensor", on_state=True)
        plugin.deviceUpdated(orig, new)

        self.assertEqual(event_log_messages(plugin), [])
        self.assertEqual(plugin_file_messages(plugin), [],
            msg="With the master switch off there is no narration at all.")

    def test_the_debug_field_warns_that_it_overrides_the_quiet_default(self):
        """The one route left that puts the narration back, so it is named."""
        text = self._description("showDebugInfo").lower()
        self.assertIn("event log", text,
            msg="Debug logging re-routes the narration; the field must say so.")



# ======================================
# ENTRY POINT
# ======================================

if __name__ == "__main__":
    print("\nDevice Activity Monitor Plugin - Mock Test Suite")
    print(f"plugin.py: {_plugin_path}")
    print(f"Monitored devices in DEVICE_MONITOR:    {len(DEVICE_MONITOR)}")
    print(f"Monitored variables in VARIABLE_MONITOR: {len(VARIABLE_MONITOR)}\n")
    unittest.main(verbosity=2)
