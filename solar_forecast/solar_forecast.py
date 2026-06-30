#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    solar_forecast.py
# Description: Day-ahead solar generation forecast + overnight battery top-up
#              advisor, driven by the free Open-Meteo API. Estimates how much
#              a North/South split PV array will generate tomorrow, simulates
#              the battery state-of-charge to the start of the peak-export
#              window, and recommends how many kWh to import in the cheap
#              overnight window so the battery is full by 4pm even on a
#              cloudier-than-forecast day.
# Author:      CliveS & Claude
# Date:        30-06-2026
# Version:     1.0.0
#
# Standalone — pure Python 3 standard library, no Indigo runtime and no
# third-party packages. Run it from a terminal, a cron job, or import the
# functions into an Indigo Script Editor action.
#
#   python3 solar_forecast.py --soc 25
#   python3 solar_forecast.py --soc 25 --date 2026-07-02 --json
#
# Tests live in test_solar_forecast.py and run fully offline.

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import NormalDist

API_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo azimuth convention for global_tilted_irradiance:
#   0 = South, -90 = East, 90 = West, +/-180 = North   (tilt 0..90).
AZIMUTH_SOUTH = 0.0
AZIMUTH_NORTH = 180.0


# ======================================================================
# SYSTEM / TARIFF / ASSUMPTION MODEL
# Defaults describe the asker's Central-Scotland setup. Everything is
# overridable on the command line so anyone can point it at their own kit.
# ======================================================================

@dataclass
class Array:
    """One roof plane of panels."""
    name: str
    kwp: float          # peak DC rating, kW (e.g. 9 x 480W = 4.32)
    tilt: float         # degrees from horizontal
    azimuth: float      # Open-Meteo convention (0=S, 180=N)


@dataclass
class System:
    latitude: float = 56.1          # Central Scotland (Stirling/Falkirk area)
    longitude: float = -3.9
    arrays: list[Array] = field(default_factory=lambda: [
        Array("South", 4.32, 35.0, AZIMUTH_SOUTH),
        Array("North", 4.32, 35.0, AZIMUTH_NORTH),
    ])
    inverter_kw: float = 12.0       # AC clipping limit
    battery_kwh: float = 18.0       # usable capacity
    max_charge_kw: float = 5.0      # how fast the battery can charge

    # PV conversion model
    temp_coeff: float = -0.0035     # power tempco, per degC (-0.35 %/degC)
    noct: float = 45.0              # nominal operating cell temp, degC
    system_loss: float = 0.86       # DC-side derate (soiling/wiring/mismatch/inverter)


@dataclass
class Tariff:
    import_price: float = 0.15      # 2-5am cheap import, GBP/kWh
    peak_export: float = 0.27       # 4-7pm peak export, GBP/kWh
    standard_export: float = 0.095  # daytime export outside the peak window

    @property
    def over_cost(self) -> float:
        """Loss per kWh imported overnight that you didn't need: you paid
        import_price for it then dumped it early at standard_export."""
        return self.import_price - self.standard_export

    @property
    def under_cost(self) -> float:
        """Loss per kWh you are *short* of full at 4pm — a kWh you could not
        sell into the peak window. The asker frames this as the full peak
        rate (27p); override with --under-cost if you prefer the net-of-import
        figure (peak - import)."""
        return self.peak_export


@dataclass
class DayPlan:
    """Window boundaries, in local clock hours, for the modelled day."""
    cheap_start: int = 2            # overnight cheap import window start
    cheap_end: int = 5              # overnight cheap import window end
    day_start: int = 5              # when we start tracking solar into battery
    peak_start: int = 16            # 4pm — battery should be full by here

    @property
    def cheap_hours(self) -> int:
        return self.cheap_end - self.cheap_start


# ======================================================================
# PV CONVERSION — irradiance on the panel -> AC energy
# ======================================================================

def cell_temperature(t_air: float, gti: float, noct: float = 45.0) -> float:
    """Estimate panel cell temperature from air temp and plane-of-array
    irradiance using the standard NOCT model."""
    return t_air + (gti / 800.0) * (noct - 20.0)


def array_dc_power(gti: float, t_air: float, arr: Array, sysm: System) -> float:
    """DC power (kW) for one array given plane-of-array irradiance (W/m^2)
    and air temperature (degC). Includes temperature derate and fixed losses."""
    if gti <= 0.0:
        return 0.0
    dc = arr.kwp * (gti / 1000.0)                       # linear in irradiance
    t_cell = cell_temperature(t_air, gti, sysm.noct)
    dc *= 1.0 + sysm.temp_coeff * (t_cell - 25.0)       # warmer panels = less power
    dc *= sysm.system_loss
    return max(dc, 0.0)


def system_ac_power(gti_by_array: dict[str, float], t_air: float, sysm: System) -> float:
    """Total AC power (kW) for the whole system in one hour: sum the arrays'
    DC, then clip at the shared inverter's AC limit."""
    dc_total = sum(
        array_dc_power(gti_by_array.get(arr.name, 0.0), t_air, arr, sysm)
        for arr in sysm.arrays
    )
    return min(dc_total, sysm.inverter_kw)


# ======================================================================
# OPEN-METEO FETCH (the only part that touches the network)
# ======================================================================

def _http_get_json(url: str, timeout: float = 20.0) -> dict:
    """Default network fetcher. Injected/replaced in tests."""
    req = urllib.request.Request(url, headers={"User-Agent": "solar-forecast/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https only)
        return json.loads(resp.read().decode("utf-8"))


def build_url(sysm: System, arr: Array, target: date) -> str:
    """Build the Open-Meteo request URL for one array on one day."""
    params = {
        "latitude": f"{sysm.latitude:.4f}",
        "longitude": f"{sysm.longitude:.4f}",
        "hourly": "global_tilted_irradiance,temperature_2m,cloud_cover",
        "tilt": f"{arr.tilt:.0f}",
        "azimuth": f"{arr.azimuth:.0f}",
        "timezone": "auto",
        "start_date": target.isoformat(),
        "end_date": target.isoformat(),
    }
    return f"{API_URL}?{urllib.parse.urlencode(params)}"


def parse_hours(payload: dict, array_name: str, target: date) -> dict[int, dict]:
    """Pull the per-hour values out of one Open-Meteo response, keyed by the
    local clock hour (0..23). Only rows on `target` are kept."""
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    gti = hourly.get("global_tilted_irradiance") or []
    temp = hourly.get("temperature_2m") or []
    cloud = hourly.get("cloud_cover") or []
    target_iso = target.isoformat()

    out: dict[int, dict] = {}
    for i, ts in enumerate(times):
        # ts looks like "2026-07-01T14:00" in local time (timezone=auto)
        day_part, _, time_part = ts.partition("T")
        if day_part != target_iso:
            continue
        hour = int(time_part[:2])
        out[hour] = {
            "gti": {array_name: _num(gti, i)},
            "temp": _num(temp, i),
            "cloud": _num(cloud, i),
        }
    return out


def _num(seq, i, default=0.0):
    """Open-Meteo uses null for missing samples; coerce to a float."""
    try:
        v = seq[i]
    except (IndexError, TypeError):
        return default
    return default if v is None else float(v)


def fetch_forecast(sysm: System, target: date, fetch=_http_get_json) -> dict[int, dict]:
    """Fetch and merge per-hour forecast across every array.

    Returns {hour: {"gti": {arrayName: W/m2, ...}, "temp": degC, "cloud": %}}.
    One request per array (each carries a different tilt/azimuth); temperature
    and cloud are taken from the first array's response.
    """
    merged: dict[int, dict] = {}
    for idx, arr in enumerate(sysm.arrays):
        payload = fetch(build_url(sysm, arr, target))
        hours = parse_hours(payload, arr.name, target)
        for hour, row in hours.items():
            if hour not in merged:
                merged[hour] = {"gti": {}, "temp": row["temp"], "cloud": row["cloud"]}
            merged[hour]["gti"].update(row["gti"])
            if idx == 0:  # trust the first array for shared scalars
                merged[hour]["temp"] = row["temp"]
                merged[hour]["cloud"] = row["cloud"]
    return merged


# ======================================================================
# GENERATION + BATTERY SIMULATION
# ======================================================================

def hourly_generation(forecast: dict[int, dict], sysm: System) -> dict[int, float]:
    """AC energy (kWh) generated in each clock hour. Hourly Open-Meteo
    irradiance is an hour-mean, so kW over a 1-hour step == kWh."""
    return {
        hour: system_ac_power(row["gti"], row["temp"], sysm)
        for hour, row in forecast.items()
    }


def per_array_generation(forecast: dict[int, dict], sysm: System) -> dict[str, float]:
    """Daily kWh attributable to each array (pre-inverter-clip; for display)."""
    totals = {arr.name: 0.0 for arr in sysm.arrays}
    for row in forecast.values():
        for arr in sysm.arrays:
            totals[arr.name] += array_dc_power(
                row["gti"].get(arr.name, 0.0), row["temp"], arr, sysm
            )
    return totals


def simulate_soc(
    gen_by_hour: dict[int, float],
    start_soc: float,
    sysm: System,
    plan: DayPlan,
    load_kw: float,
    solar_scale: float = 1.0,
) -> float:
    """Walk the battery from `start_soc` (kWh) at day_start through to
    peak_start, charging on solar surplus and discharging to cover house
    load. Returns the SoC (kWh) at peak_start, clamped to [0, capacity].

    `solar_scale` shrinks (or grows) every hour's generation to model a
    cloudier- or sunnier-than-central day.
    """
    soc = max(0.0, min(start_soc, sysm.battery_kwh))
    for hour in range(plan.day_start, plan.peak_start):
        gen = gen_by_hour.get(hour, 0.0) * solar_scale
        net = gen - load_kw            # kWh surplus(+) / deficit(-) this hour
        if net >= 0.0:
            charge = min(net, sysm.max_charge_kw, sysm.battery_kwh - soc)
            soc += charge
        else:
            soc = max(0.0, soc + net)  # discharge; grid backfill not modelled
    return soc


# ======================================================================
# THE RECOMMENDATION — asymmetric "newsvendor" top-up sizing
# ======================================================================

def design_scale(tariff: Tariff, forecast_cv: float, under_cost: float | None = None) -> float:
    """How much to discount the central solar forecast when sizing the top-up.

    Being short at 4pm costs `under_cost` per kWh; over-topping costs
    `over_cost`. The cost-optimal plan covers the shortfall up to the
    critical fractile  Cu / (Cu + Co)  of the *shortfall* distribution —
    equivalently it designs for the (1 - fractile) quantile of *generation*.
    With under_cost >> over_cost that quantile is well below the central
    forecast, i.e. we deliberately plan for a gloomier-than-expected day.
    """
    cu = tariff.under_cost if under_cost is None else under_cost
    co = tariff.over_cost
    if cu <= 0.0 and co <= 0.0:
        return 1.0
    fractile = cu / (cu + co)                       # target service level
    gen_quantile = 1.0 - fractile                   # gloomier tail of generation
    z = NormalDist().inv_cdf(gen_quantile)          # negative for q < 0.5
    return max(0.0, 1.0 + z * forecast_cv)


def recommend(
    forecast: dict[int, dict],
    start_soc_kwh: float,
    sysm: System,
    tariff: Tariff,
    plan: DayPlan,
    load_kw: float = 0.5,
    forecast_cv: float = 0.35,
    under_cost: float | None = None,
) -> dict:
    """Produce the full day-ahead recommendation from a fetched forecast."""
    gen_by_hour = hourly_generation(forecast, sysm)

    # Daily / window totals for display.
    total_gen = sum(gen_by_hour.values())
    window_gen = sum(g for h, g in gen_by_hour.items()
                     if plan.day_start <= h < plan.peak_start)
    peak_kw = max(gen_by_hour.values(), default=0.0)
    peak_hour = max(gen_by_hour, key=gen_by_hour.get, default=None) \
        if gen_by_hour else None
    day_cloud = [row["cloud"] for h, row in forecast.items()
                 if plan.day_start <= h < plan.peak_start]
    mean_cloud = sum(day_cloud) / len(day_cloud) if day_cloud else 0.0

    # Central forecast: where does the battery land at 4pm with no top-up?
    soc_central = simulate_soc(gen_by_hour, start_soc_kwh, sysm, plan, load_kw)
    shortfall_central = max(0.0, sysm.battery_kwh - soc_central)

    # Design (pessimistic) forecast for sizing the top-up.
    scale = design_scale(tariff, forecast_cv, under_cost)
    soc_design = simulate_soc(gen_by_hour, start_soc_kwh, sysm, plan, load_kw,
                              solar_scale=scale)
    shortfall_design = max(0.0, sysm.battery_kwh - soc_design)

    # The top-up: fill the design-day shortfall, capped by battery headroom
    # and by how much the charger can physically push in the cheap window.
    headroom = max(0.0, sysm.battery_kwh - start_soc_kwh)
    overnight_cap = sysm.max_charge_kw * plan.cheap_hours
    topup = min(shortfall_design, headroom, overnight_cap)

    # Where we'd land at 4pm on the central forecast if we DO top up.
    soc_after = simulate_soc(gen_by_hour, start_soc_kwh + topup, sysm, plan, load_kw)

    return {
        "date": None,  # filled in by caller
        "total_generation_kwh": round(total_gen, 2),
        "window_generation_kwh": round(window_gen, 2),
        "per_array_kwh": {k: round(v, 2) for k, v in
                          per_array_generation(forecast, sysm).items()},
        "peak_ac_kw": round(peak_kw, 2),
        "peak_hour": peak_hour,
        "mean_daytime_cloud_pct": round(mean_cloud, 0),
        "start_soc_kwh": round(start_soc_kwh, 2),
        "start_soc_pct": round(100.0 * start_soc_kwh / sysm.battery_kwh, 0),
        "soc_4pm_no_topup_kwh": round(soc_central, 2),
        "soc_4pm_no_topup_pct": round(100.0 * soc_central / sysm.battery_kwh, 0),
        "shortfall_central_kwh": round(shortfall_central, 2),
        "design_scale": round(scale, 3),
        "shortfall_design_kwh": round(shortfall_design, 2),
        "recommended_topup_kwh": round(topup, 2),
        "topup_cost_gbp": round(topup * tariff.import_price, 2),
        "soc_4pm_after_topup_kwh": round(soc_after, 2),
        "soc_4pm_after_topup_pct": round(100.0 * soc_after / sysm.battery_kwh, 0),
        "protected_peak_value_gbp": round(topup * tariff.under_cost
                                          if under_cost is None
                                          else topup * under_cost, 2),
    }


# ======================================================================
# HUMAN-READABLE OUTPUT
# ======================================================================

def format_report(rec: dict, sysm: System, tariff: Tariff, plan: DayPlan) -> str:
    lines = []
    lines.append(f"Solar + battery plan for {rec['date']}")
    lines.append("=" * 56)
    arrays = ", ".join(f"{name} {kwh:.1f} kWh"
                       for name, kwh in rec["per_array_kwh"].items())
    lines.append(f"Forecast generation : {rec['total_generation_kwh']:.1f} kWh "
                 f"total  ({arrays})")
    peak_h = rec["peak_hour"]
    peak_txt = f"{peak_h:02d}:00" if peak_h is not None else "n/a"
    lines.append(f"Peak output         : {rec['peak_ac_kw']:.1f} kW around {peak_txt}")
    lines.append(f"Mean daytime cloud  : {rec['mean_daytime_cloud_pct']:.0f} %")
    lines.append("-" * 56)
    lines.append(f"Battery now         : {rec['start_soc_kwh']:.1f} kWh "
                 f"({rec['start_soc_pct']:.0f} %)")
    lines.append(f"Projected at {plan.peak_start}:00  : "
                 f"{rec['soc_4pm_no_topup_kwh']:.1f} kWh "
                 f"({rec['soc_4pm_no_topup_pct']:.0f} %) with no overnight top-up")
    lines.append("-" * 56)
    if rec["recommended_topup_kwh"] <= 0.05:
        lines.append("RECOMMENDATION: no overnight top-up needed — solar alone "
                     f"should fill the battery by {plan.peak_start}:00.")
    else:
        lines.append(f"RECOMMENDATION: import {rec['recommended_topup_kwh']:.1f} kWh "
                     f"between {plan.cheap_start:02d}:00-{plan.cheap_end:02d}:00 "
                     f"(~GBP {rec['topup_cost_gbp']:.2f} at "
                     f"{tariff.import_price*100:.1f}p/kWh).")
        lines.append(f"  -> lands you at ~{rec['soc_4pm_after_topup_pct']:.0f} % by "
                     f"{plan.peak_start}:00 on the central forecast, and stays full "
                     "even if the day comes in")
        lines.append(f"     at the gloomier end (designed for "
                     f"{rec['design_scale']*100:.0f} % of the central forecast).")
    lines.append("-" * 56)
    lines.append("Why bias towards topping up:")
    lines.append(f"  short of full at {plan.peak_start}:00 costs ~"
                 f"{tariff.under_cost*100:.1f}p/kWh (missed peak export);")
    lines.append(f"  over-topping costs only ~{tariff.over_cost*100:.1f}p/kWh "
                 "(import price minus standard export).")
    lines.append("Estimate only — trim the load/cv/tilt assumptions to your own data.")
    return "\n".join(lines)


# ======================================================================
# CLI
# ======================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Day-ahead solar forecast + overnight battery top-up advisor "
                    "(Open-Meteo).")
    p.add_argument("--soc", type=float, default=20.0,
                   help="current battery state of charge, %% (default 20)")
    p.add_argument("--date", type=str, default=None,
                   help="target day YYYY-MM-DD (default: tomorrow)")
    p.add_argument("--lat", type=float, default=None, help="latitude")
    p.add_argument("--lon", type=float, default=None, help="longitude")
    p.add_argument("--load-kw", type=float, default=0.5,
                   help="average house load, kW (default 0.5)")
    p.add_argument("--cv", type=float, default=0.35,
                   help="day-ahead solar forecast uncertainty, coefficient of "
                        "variation (default 0.35)")
    p.add_argument("--battery-kwh", type=float, default=None, help="usable battery kWh")
    p.add_argument("--inverter-kw", type=float, default=None, help="inverter AC limit kW")
    p.add_argument("--max-charge-kw", type=float, default=None, help="battery charge rate kW")
    p.add_argument("--south-kwp", type=float, default=None, help="south array kWp")
    p.add_argument("--north-kwp", type=float, default=None, help="north array kWp")
    p.add_argument("--tilt", type=float, default=None, help="roof tilt degrees")
    p.add_argument("--import-price", type=float, default=None, help="cheap import GBP/kWh")
    p.add_argument("--peak-export", type=float, default=None, help="peak export GBP/kWh")
    p.add_argument("--standard-export", type=float, default=None, help="standard export GBP/kWh")
    p.add_argument("--under-cost", type=float, default=None,
                   help="override cost per kWh short at 4pm (default = peak export)")
    p.add_argument("--offline", type=str, default=None,
                   help="read a saved Open-Meteo JSON instead of the network "
                        "(one array only; for testing)")
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return p


def _apply_overrides(args, sysm: System, tariff: Tariff) -> None:
    if args.lat is not None:
        sysm.latitude = args.lat
    if args.lon is not None:
        sysm.longitude = args.lon
    if args.battery_kwh is not None:
        sysm.battery_kwh = args.battery_kwh
    if args.inverter_kw is not None:
        sysm.inverter_kw = args.inverter_kw
    if args.max_charge_kw is not None:
        sysm.max_charge_kw = args.max_charge_kw
    if args.south_kwp is not None:
        sysm.arrays[0].kwp = args.south_kwp
    if args.north_kwp is not None:
        sysm.arrays[1].kwp = args.north_kwp
    if args.tilt is not None:
        for arr in sysm.arrays:
            arr.tilt = args.tilt
    if args.import_price is not None:
        tariff.import_price = args.import_price
    if args.peak_export is not None:
        tariff.peak_export = args.peak_export
    if args.standard_export is not None:
        tariff.standard_export = args.standard_export


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    sysm, tariff, plan = System(), Tariff(), DayPlan()
    _apply_overrides(args, sysm, tariff)

    target = date.fromisoformat(args.date) if args.date else date.today() + timedelta(days=1)

    if args.offline:
        with open(args.offline, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        # Offline mode supports a single-array file; map it onto every array
        # so the model still runs (useful for demos/tests without a network).
        forecast: dict[int, dict] = {}
        for arr in sysm.arrays:
            hours = parse_hours(payload, arr.name, target)
            for hour, row in hours.items():
                slot = forecast.setdefault(
                    hour, {"gti": {}, "temp": row["temp"], "cloud": row["cloud"]})
                slot["gti"].update(row["gti"])
    else:
        try:
            forecast = fetch_forecast(sysm, target)
        except Exception as exc:  # noqa: BLE001 - surface any network/parse error cleanly
            print(f"ERROR fetching forecast: {exc}", file=sys.stderr)
            return 2

    if not forecast:
        print("ERROR: no forecast hours returned for that date.", file=sys.stderr)
        return 2

    start_soc = max(0.0, min(args.soc, 100.0)) / 100.0 * sysm.battery_kwh
    rec = recommend(forecast, start_soc, sysm, tariff, plan,
                    load_kw=args.load_kw, forecast_cv=args.cv,
                    under_cost=args.under_cost)
    rec["date"] = target.isoformat()

    if args.json:
        print(json.dumps(rec, indent=2))
    else:
        print(format_report(rec, sysm, tariff, plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
