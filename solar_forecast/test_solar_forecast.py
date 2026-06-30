#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    test_solar_forecast.py
# Description: Offline unit tests for solar_forecast.py. No network, no
#              third-party packages — same "runs anywhere" philosophy as the
#              plugin's test_plugin.py.
# Author:      CliveS & Claude
# Date:        30-06-2026
# Version:     1.0.0
#
# Run from Terminal:
#   cd solar_forecast
#   python3 test_solar_forecast.py -v

import unittest
from datetime import date

import solar_forecast as sf


def make_system(**kw):
    sysm = sf.System()
    for k, v in kw.items():
        setattr(sysm, k, v)
    return sysm


def flat_forecast(hours, south_gti, north_gti, temp=10.0, cloud=50.0):
    """Build a synthetic forecast dict with constant irradiance over `hours`."""
    return {
        h: {"gti": {"South": south_gti, "North": north_gti},
            "temp": temp, "cloud": cloud}
        for h in hours
    }


class TestPVConversion(unittest.TestCase):
    def test_stc_no_loss_returns_kwp(self):
        """1000 W/m^2, zero tempco, unity loss -> output equals kWp exactly."""
        sysm = make_system(temp_coeff=0.0, system_loss=1.0)
        arr = sf.Array("South", 4.32, 35.0, sf.AZIMUTH_SOUTH)
        self.assertAlmostEqual(sf.array_dc_power(1000.0, 20.0, arr, sysm), 4.32, places=6)

    def test_zero_irradiance_zero_power(self):
        sysm = make_system()
        arr = sysm.arrays[0]
        self.assertEqual(sf.array_dc_power(0.0, 20.0, arr, sysm), 0.0)
        self.assertEqual(sf.array_dc_power(-5.0, 20.0, arr, sysm), 0.0)

    def test_temperature_derate(self):
        """Hotter air -> less power for a negative tempco."""
        sysm = make_system(system_loss=1.0)
        arr = sysm.arrays[0]
        cold = sf.array_dc_power(600.0, 0.0, arr, sysm)
        hot = sf.array_dc_power(600.0, 30.0, arr, sysm)
        self.assertGreater(cold, hot)

    def test_inverter_clipping(self):
        """Combined DC above the inverter limit is clipped to the AC limit."""
        sysm = make_system(inverter_kw=5.0, system_loss=1.0, temp_coeff=0.0)
        gti = {"South": 1000.0, "North": 1000.0}  # 4.32 + 4.32 = 8.64 kW DC
        self.assertEqual(sf.system_ac_power(gti, 15.0, sysm), 5.0)

    def test_no_clipping_below_limit(self):
        sysm = make_system(inverter_kw=12.0, system_loss=1.0, temp_coeff=0.0)
        gti = {"South": 1000.0, "North": 0.0}  # 4.32 kW DC, well under 12
        self.assertAlmostEqual(sf.system_ac_power(gti, 25.0, sysm), 4.32, places=6)

    def test_cell_temperature_model(self):
        # NOCT 45 -> +25 degC per 800 W/m^2; at 800 the rise is exactly 25.
        self.assertAlmostEqual(sf.cell_temperature(10.0, 800.0, 45.0), 35.0, places=6)


class TestSocSimulation(unittest.TestCase):
    def test_pure_discharge(self):
        sysm = make_system(battery_kwh=18.0)
        plan = sf.DayPlan()  # day_start 5, peak_start 16 -> 11 hours
        gen = {h: 0.0 for h in range(5, 16)}
        soc = sf.simulate_soc(gen, 10.0, sysm, plan, load_kw=0.5)
        self.assertAlmostEqual(soc, 10.0 - 11 * 0.5, places=6)  # 4.5

    def test_discharge_clamps_at_zero(self):
        sysm = make_system(battery_kwh=18.0)
        plan = sf.DayPlan()
        gen = {h: 0.0 for h in range(5, 16)}
        soc = sf.simulate_soc(gen, 2.0, sysm, plan, load_kw=2.0)
        self.assertEqual(soc, 0.0)

    def test_charge_clamps_at_capacity(self):
        sysm = make_system(battery_kwh=18.0, max_charge_kw=5.0)
        plan = sf.DayPlan()
        gen = {h: 6.0 for h in range(5, 16)}  # big surplus every hour
        soc = sf.simulate_soc(gen, 10.0, sysm, plan, load_kw=0.5)
        self.assertEqual(soc, 18.0)

    def test_charge_rate_limited(self):
        sysm = make_system(battery_kwh=100.0, max_charge_kw=1.0)  # huge battery
        plan = sf.DayPlan()
        gen = {h: 10.0 for h in range(5, 16)}  # surplus, but charge capped at 1 kW
        soc = sf.simulate_soc(gen, 0.0, sysm, plan, load_kw=0.0)
        self.assertAlmostEqual(soc, 11 * 1.0, places=6)  # 11 hours * 1 kW

    def test_solar_scale_reduces_soc(self):
        sysm = make_system(battery_kwh=18.0)
        plan = sf.DayPlan()
        gen = {h: 2.0 for h in range(5, 16)}
        full = sf.simulate_soc(gen, 5.0, sysm, plan, load_kw=0.5, solar_scale=1.0)
        dim = sf.simulate_soc(gen, 5.0, sysm, plan, load_kw=0.5, solar_scale=0.5)
        self.assertGreater(full, dim)


class TestDesignScale(unittest.TestCase):
    def test_symmetric_costs_give_unity(self):
        t = sf.Tariff(import_price=0.20, standard_export=0.10)  # over_cost 0.10
        scale = sf.design_scale(t, forecast_cv=0.3, under_cost=0.10)  # under==over
        self.assertAlmostEqual(scale, 1.0, places=6)

    def test_asker_economics_discount_forecast(self):
        # under 0.27, over 0.055 -> fractile 0.831 -> design ~0.665 of central.
        t = sf.Tariff()  # defaults: import .15, peak .27, standard .095
        scale = sf.design_scale(t, forecast_cv=0.35)
        self.assertAlmostEqual(scale, 0.665, delta=0.01)

    def test_higher_uncertainty_lowers_scale(self):
        t = sf.Tariff()
        low = sf.design_scale(t, forecast_cv=0.20)
        high = sf.design_scale(t, forecast_cv=0.50)
        self.assertGreater(low, high)

    def test_scale_never_negative(self):
        t = sf.Tariff()
        self.assertGreaterEqual(sf.design_scale(t, forecast_cv=5.0), 0.0)


class TestParsing(unittest.TestCase):
    PAYLOAD = {
        "latitude": 56.1, "longitude": -3.9,
        "hourly": {
            "time": ["2026-07-01T22:00", "2026-07-01T23:00",
                     "2026-07-02T00:00", "2026-07-02T12:00", "2026-07-02T13:00"],
            "global_tilted_irradiance": [0.0, 0.0, 0.0, 540.0, 500.0],
            "temperature_2m": [11.0, 10.0, 9.0, 16.0, 17.0],
            "cloud_cover": [80, 85, 90, 30, 35],
        },
    }

    def test_parse_filters_to_target_day(self):
        rows = sf.parse_hours(self.PAYLOAD, "South", date(2026, 7, 2))
        self.assertEqual(set(rows.keys()), {0, 12, 13})
        self.assertAlmostEqual(rows[12]["gti"]["South"], 540.0)
        self.assertAlmostEqual(rows[12]["temp"], 16.0)
        self.assertEqual(rows[12]["cloud"], 30.0)

    def test_parse_handles_nulls(self):
        payload = {
            "hourly": {
                "time": ["2026-07-02T12:00"],
                "global_tilted_irradiance": [None],
                "temperature_2m": [None],
                "cloud_cover": [None],
            }
        }
        rows = sf.parse_hours(payload, "South", date(2026, 7, 2))
        self.assertEqual(rows[12]["gti"]["South"], 0.0)

    def test_build_url_azimuth_and_dates(self):
        sysm = sf.System()
        south = sysm.arrays[0]
        north = sysm.arrays[1]
        url_s = sf.build_url(sysm, south, date(2026, 7, 2))
        url_n = sf.build_url(sysm, north, date(2026, 7, 2))
        self.assertIn("azimuth=0", url_s)
        self.assertIn("azimuth=180", url_n)
        self.assertIn("start_date=2026-07-02", url_s)
        self.assertIn("end_date=2026-07-02", url_s)
        self.assertIn("global_tilted_irradiance", url_s)

    def test_fetch_forecast_merges_arrays(self):
        """Injected fetcher returns a different GTI per array; merge keeps both."""
        def fake_fetch(url):
            # azimuth=0 is South, azimuth=180 is North
            gti = 600.0 if "azimuth=0" in url else 100.0
            name_val = gti
            return {
                "hourly": {
                    "time": ["2026-07-02T12:00", "2026-07-02T13:00"],
                    "global_tilted_irradiance": [name_val, name_val],
                    "temperature_2m": [15.0, 15.0],
                    "cloud_cover": [40, 40],
                }
            }
        sysm = sf.System()
        merged = sf.fetch_forecast(sysm, date(2026, 7, 2), fetch=fake_fetch)
        self.assertEqual(set(merged.keys()), {12, 13})
        self.assertAlmostEqual(merged[12]["gti"]["South"], 600.0)
        self.assertAlmostEqual(merged[12]["gti"]["North"], 100.0)


class TestRecommend(unittest.TestCase):
    def test_sunny_day_central_forecast_fills(self):
        """On the central forecast a sunny day fills the battery with no help."""
        sysm = sf.System()
        tariff = sf.Tariff()
        plan = sf.DayPlan()
        # Strong sun 08:00-15:00 on the south roof.
        forecast = flat_forecast(range(8, 16), south_gti=700.0, north_gti=120.0,
                                 temp=16.0, cloud=10.0)
        rec = sf.recommend(forecast, start_soc_kwh=3.6, sysm=sysm, tariff=tariff,
                           plan=plan, load_kw=0.5, forecast_cv=0.35)
        self.assertGreater(rec["total_generation_kwh"], 15.0)
        self.assertGreaterEqual(rec["soc_4pm_no_topup_pct"], 99.0)
        self.assertEqual(rec["shortfall_central_kwh"], 0.0)

    def test_confident_sunny_day_no_topup(self):
        """With a confident forecast (low cv) the hedge disappears entirely."""
        sysm = sf.System()
        tariff = sf.Tariff()
        plan = sf.DayPlan()
        forecast = flat_forecast(range(8, 16), south_gti=700.0, north_gti=120.0,
                                 temp=16.0, cloud=10.0)
        rec = sf.recommend(forecast, start_soc_kwh=3.6, sysm=sysm, tariff=tariff,
                           plan=plan, load_kw=0.5, forecast_cv=0.02)
        self.assertEqual(rec["recommended_topup_kwh"], 0.0)

    def test_uncertainty_increases_hedge_topup(self):
        """Same sunny forecast, more uncertainty -> a larger hedge top-up."""
        sysm = sf.System()
        tariff = sf.Tariff()
        plan = sf.DayPlan()
        forecast = flat_forecast(range(8, 16), south_gti=700.0, north_gti=120.0,
                                 temp=16.0, cloud=10.0)
        low = sf.recommend(forecast, 3.6, sysm, tariff, plan, forecast_cv=0.15)
        high = sf.recommend(forecast, 3.6, sysm, tariff, plan, forecast_cv=0.45)
        self.assertGreaterEqual(high["recommended_topup_kwh"],
                                low["recommended_topup_kwh"])

    def test_cloudy_day_recommends_topup(self):
        sysm = sf.System()
        tariff = sf.Tariff()
        plan = sf.DayPlan()
        # Thick cloud, weak generation 09:00-15:00, battery nearly empty.
        forecast = flat_forecast(range(9, 15), south_gti=120.0, north_gti=40.0,
                                 temp=9.0, cloud=92.0)
        start = 0.15 * sysm.battery_kwh
        rec = sf.recommend(forecast, start_soc_kwh=start, sysm=sysm, tariff=tariff,
                           plan=plan, load_kw=0.5, forecast_cv=0.35)
        self.assertGreater(rec["recommended_topup_kwh"], 0.0)
        # Never exceeds physical headroom or what the charger can push overnight.
        headroom = sysm.battery_kwh - start
        overnight_cap = sysm.max_charge_kw * plan.cheap_hours
        self.assertLessEqual(rec["recommended_topup_kwh"], min(headroom, overnight_cap) + 1e-9)
        self.assertGreater(rec["topup_cost_gbp"], 0.0)

    def test_topup_capped_by_overnight_window(self):
        """Slow charger -> top-up bounded by max_charge_kw * cheap hours."""
        sysm = make_system(max_charge_kw=1.0)  # only 1 kW -> 3 kWh in 02:00-05:00
        tariff = sf.Tariff()
        plan = sf.DayPlan()
        forecast = flat_forecast(range(9, 15), south_gti=50.0, north_gti=10.0,
                                 temp=8.0, cloud=98.0)
        rec = sf.recommend(forecast, start_soc_kwh=1.0, sysm=sysm, tariff=tariff,
                           plan=plan, load_kw=0.5, forecast_cv=0.35)
        self.assertLessEqual(rec["recommended_topup_kwh"], 3.0 + 1e-9)
        self.assertAlmostEqual(rec["recommended_topup_kwh"], 3.0, places=6)

    def test_topup_capped_by_headroom(self):
        """Nearly-full battery -> top-up bounded by remaining headroom."""
        sysm = sf.System()
        tariff = sf.Tariff()
        plan = sf.DayPlan()
        forecast = flat_forecast(range(9, 15), south_gti=50.0, north_gti=10.0,
                                 temp=8.0, cloud=98.0)
        start = sysm.battery_kwh - 2.0  # only 2 kWh of headroom
        rec = sf.recommend(forecast, start_soc_kwh=start, sysm=sysm, tariff=tariff,
                           plan=plan, load_kw=0.5, forecast_cv=0.35)
        self.assertLessEqual(rec["recommended_topup_kwh"], 2.0 + 1e-9)

    def test_per_array_split(self):
        sysm = sf.System()
        tariff = sf.Tariff()
        plan = sf.DayPlan()
        forecast = flat_forecast(range(8, 16), south_gti=600.0, north_gti=120.0)
        rec = sf.recommend(forecast, start_soc_kwh=5.0, sysm=sysm, tariff=tariff,
                           plan=plan)
        # South array (more irradiance) must out-generate the North array.
        self.assertGreater(rec["per_array_kwh"]["South"], rec["per_array_kwh"]["North"])


class TestReportFormatting(unittest.TestCase):
    def test_report_renders(self):
        sysm = sf.System()
        tariff = sf.Tariff()
        plan = sf.DayPlan()
        forecast = flat_forecast(range(8, 16), south_gti=300.0, north_gti=80.0)
        rec = sf.recommend(forecast, start_soc_kwh=4.0, sysm=sysm, tariff=tariff,
                           plan=plan)
        rec["date"] = "2026-07-02"
        text = sf.format_report(rec, sysm, tariff, plan)
        self.assertIn("Solar + battery plan for 2026-07-02", text)
        self.assertIn("RECOMMENDATION", text)


if __name__ == "__main__":
    unittest.main()
