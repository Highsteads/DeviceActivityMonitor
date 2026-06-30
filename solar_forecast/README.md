# Day-ahead solar forecast → overnight battery top-up advisor

A small, standalone Python tool that answers a very specific question:

> It's 2am. Should I top my battery up at the cheap import rate, and if so by
> how many kWh, so that it's **full by 4pm** for the peak-export window —
> *without* overpaying on days when the sun was going to fill it anyway?

It's built around the asker's setup (Flux tariff, 8.6 kWp split North/South,
18 kWh battery, Central Scotland) but every number is a command-line flag, so
it works for any system.

It is **stdlib-only** — no `pip install`, no API key. It talks to the free
[Open-Meteo](https://open-meteo.com/) forecast API, which is the short answer
to *"would meteo help him out?"*: **yes, and here's exactly how.**

---

## TL;DR — is there a "half decent" way to predict tomorrow's solar?

Short version for the forum: there's no perfect day-ahead solar number, but
you can get a genuinely useful one for free.

- **Best free data source:** Open-Meteo's forecast API. Unlike a plain cloud-%
  forecast, it returns **plane-of-array irradiance** (`global_tilted_irradiance`)
  for *your* roof's tilt and azimuth, plus temperature and cloud cover, hour by
  hour, up to 16 days out — no key, no sign-up. (forecast.solar and Solcast are
  the well-known alternatives; Solcast's free tier is good but rate-limited and
  needs registration. Open-Meteo is the easiest to automate.)
- **The trick isn't the forecast, it's the decision.** Because being *short* at
  4pm (missing 27p export) costs about **5× more** than *over-topping* (5.5p), the
  maths says you should deliberately plan for a **gloomier-than-forecast day** —
  roughly the bottom-third outcome — and top up to cover *that*. You'll over-top
  a little on average, which is exactly the cheap mistake you want to make.

This tool does both halves: pulls the forecast for your two roofs and turns it
into a single "import N kWh tonight" recommendation.

---

## Quick start

```bash
cd solar_forecast

# Tomorrow, telling it the battery is currently at 25%:
python3 solar_forecast.py --soc 25

# A specific day, machine-readable output (for cron / Indigo):
python3 solar_forecast.py --soc 25 --date 2026-07-02 --json
```

Example output on a dull forecast:

```
Solar + battery plan for 2026-07-02
========================================================
Forecast generation : 8.4 kWh total  (South 6.1 kWh, North 2.3 kWh)
Peak output         : 1.1 kW around 11:00
Mean daytime cloud  : 95 %
--------------------------------------------------------
Battery now         : 4.5 kWh (25 %)
Projected at 16:00  : 6.8 kWh (38 %) with no overnight top-up
--------------------------------------------------------
RECOMMENDATION: import 13.5 kWh between 02:00-05:00 (~GBP 2.02 at 15.0p/kWh).
  -> lands you at ~100 % by 16:00 on the central forecast, and stays full
     even if the day comes in at the gloomier end (designed for 66 % of the
     central forecast).
--------------------------------------------------------
Why bias towards topping up:
  short of full at 16:00 costs ~27.0p/kWh (missed peak export);
  over-topping costs only ~5.5p/kWh (import price minus standard export).
```

On a sunny forecast it simply says *"no overnight top-up needed — solar alone
should fill the battery by 16:00."*

---

## How it works

### 1. Forecast each roof separately

Open-Meteo's `global_tilted_irradiance` takes a `tilt` and an `azimuth`
(`0 = South`, `±180 = North`), so the South and North planes are requested
independently — one HTTP call each. That matters a lot at 56°N: in mid-summer
the North roof can still do most of what the South roof does (17-hour days, lots
of diffuse light), but in winter it's a rounding error. A flat "cloud %" can't
tell you that; tilted irradiance can.

### 2. Convert irradiance → AC energy

For each array, each hour:

```
DC_kW = kWp × (GTI / 1000) × [1 + tempco × (T_cell − 25)] × system_loss
T_cell = T_air + (GTI / 800) × (NOCT − 20)        # standard NOCT model
```

The two arrays' DC are summed and **clipped at the inverter's AC limit**
(12 kW here — with 8.64 kWp it never actually clips in Scotland, but the model
handles it). Defaults: `tempco = −0.35 %/°C`, `NOCT = 45 °C`,
`system_loss = 0.86` (soiling, wiring, mismatch, inverter efficiency). Cold
Scottish panels actually run *above* nameplate efficiency, which the temperature
term captures.

### 3. Simulate the battery to 4pm

Walk from the current state of charge through to 16:00, hour by hour: solar
above the house load charges the battery (capped by the charge rate and the
remaining headroom); solar below the load discharges it. That gives the
projected SoC at 4pm **with no overnight help**.

### 4. Size the top-up from the *economics*, not just the forecast

This is the bit worth sharing. The costs are asymmetric:

| Mistake | Cost per kWh | Why |
|---|---|---|
| **Over-top** (imported more than needed) | **5.5p** | paid 15p to import, dumped it early at the 9.5p standard rate → lose 5.5p |
| **Under-top** (short of full at 4pm) | **27p** | that kWh can't be sold into the 4–7pm peak window |

This is the classic **newsvendor problem**. The cost-optimal plan covers the
shortfall up to the *critical fractile*:

```
fractile = under_cost / (under_cost + over_cost) = 27 / (27 + 5.5) ≈ 0.83
```

So you should aim to be full **83% of the time** — i.e. plan for a day whose
solar comes in at only the ~17th percentile of the forecast distribution. With a
day-ahead uncertainty of ~35% (`--cv 0.35`), that works out to designing for
about **two-thirds of the central forecast**, and topping up to fill *that*
gloomier day. You'll slightly over-top on an average day — which, per the table
above, is the cheap mistake. Exactly the behaviour the asker wanted:

> *"I'm generally much better having full batteries from 4pm, even if I risk
> topping up more than I need to."*

The recommended top-up is finally capped by physical reality: the remaining
battery headroom, and how much the charger can actually push in the 02:00–05:00
window (`max_charge_kw × 3h`).

---

## Options

| Flag | Default | Meaning |
|---|---|---|
| `--soc` | 20 | current battery state of charge, **%** |
| `--date` | tomorrow | target day, `YYYY-MM-DD` |
| `--lat` / `--lon` | 56.1 / −3.9 | location (Central Scotland) |
| `--load-kw` | 0.5 | average house load during the day, kW |
| `--cv` | 0.35 | day-ahead forecast uncertainty (coefficient of variation). Lower = more confident = smaller hedge |
| `--battery-kwh` | 18 | usable battery capacity |
| `--inverter-kw` | 12 | inverter AC limit |
| `--max-charge-kw` | 5 | battery charge rate (sets the overnight cap) |
| `--south-kwp` / `--north-kwp` | 4.32 / 4.32 | array sizes (9 × 480 W each) |
| `--tilt` | 35 | roof pitch, degrees |
| `--import-price` | 0.15 | cheap overnight import, £/kWh |
| `--peak-export` | 0.27 | peak export, £/kWh |
| `--standard-export` | 0.095 | standard export, £/kWh |
| `--under-cost` | = peak export | override the "cost of being short". Use `0.12` (peak − import) if you'd rather count the *net* loss instead of the gross peak rate |
| `--offline FILE` | — | read a saved Open-Meteo JSON instead of the network (demo/testing) |
| `--json` | — | machine-readable output |

### `--under-cost`: 27p or 12p?

The asker framed being short as a flat **27p** loss (the peak rate you couldn't
capture). A stricter accountant would say the *avoidable* loss is **12p**
(27p peak − 15p you'd have paid to import it overnight), because the alternative
to exporting it wasn't "free" — you had to buy it. Both are defensible; 27p
pushes you to top up more aggressively. The tool defaults to 27p to match the
question, and `--under-cost 0.12` switches to the net view (which lowers the
recommended top-up).

---

## Tuning it to reality

The absolute kWh figure is only as good as the assumptions — treat it as a
**rough day-ahead signal, not a meter reading**. To make it genuinely yours:

1. Compare a week of forecasts against what your inverter actually produced and
   nudge `--system-loss` (in `System`) until the sunny days line up.
2. Set `--load-kw` to your real average daytime draw (check your consumption
   history — it's rarely a flat 0.5 kW).
3. Set `--cv` from how spread-out your forecast-vs-actual errors are. Settled
   high-pressure days deserve a low `cv`; changeable Atlantic fronts a high one.

The **relative** day-to-day signal ("tomorrow is a top-up day, the day after
isn't") and the asymmetric top-up sizing are robust even before you calibrate.

---

## Wiring it into Indigo

This is deliberately a plain script so it can run anywhere — terminal, `cron`,
or an Indigo **Script Editor** action. Two easy patterns:

- **Variable bridge:** run `--json` from a nightly schedule, parse
  `recommended_topup_kwh`, and write it to an Indigo variable that your existing
  battery-charge action group reads.
- **Direct import:** `import solar_forecast`, call `fetch_forecast()` and
  `recommend()` from a Python action, and act on the dict.

(It's intentionally separate from the Device Activity Monitor plugin in this
repo — different job, no Indigo dependency, no shared state.)

---

## Tests

Fully offline — no network, no third-party packages, same philosophy as the
plugin's `test_plugin.py`:

```bash
cd solar_forecast
python3 test_solar_forecast.py -v
```

Covers the PV conversion (STC sanity, temperature derate, inverter clipping),
the battery simulation (charge/discharge/clamping/rate-limit), the newsvendor
top-up sizing (fractile maths, uncertainty response, physical caps), and the
Open-Meteo request building / response parsing with mocked data.

---

## Caveats (it's an imperfect art form — the asker said so)

- A single deterministic forecast can't really give a probability distribution;
  the `cv` hedge is a pragmatic stand-in, not an ensemble.
- House load is modelled as a flat average. Big midday loads (EV, immersion)
  change the picture — set `--load-kw` accordingly or extend the model.
- It plans to 4pm and ignores what happens *after* 7pm; it's optimising the
  peak-export window specifically.
- Forecasts at 56°N in changeable weather will be wrong sometimes. The whole
  point of the asymmetric sizing is to make those errors land on the cheap side.

---

© 2026 CliveS · MIT licence (same as the rest of this repo).
