# Lahore PM2.5 vs the WHO guideline

**Research question:** Over the last 12 months, on what share of days did Lahore's daily PM2.5 exceed the WHO 2021 24-hour guideline of 15 µg/m³, and how does that change across the year?

## Why it matters
Lahore's winter smog is a recurring public-health emergency. Headlines usually quote a single bad day; this analysis asks how often the air is unsafe across a whole year, using open monitoring data.

## Data
- **Source:** [OpenAQ](https://openaq.org) v3 API, daily aggregates (`/v3/sensors/{id}/days`) for every fixed PM2.5 sensor within 25 km of central Lahore (31.5204, 74.3587).
- **Guideline:** WHO Global Air Quality Guidelines (2021): PM2.5 24-hour mean 15 µg/m³, annual mean 5 µg/m³. Interim target 1 for 24 hours: 75 µg/m³.
- Raw data is saved to `data/raw_daily_pm25.csv` exactly as downloaded.

## Method
1. **Clean:** drop negative values, values above 1000 µg/m³ (sensor errors), days with less than 75% hourly coverage, and duplicate sensor-days.
2. **City value per day:** median across all sensors that reported that day. The median limits the effect of one faulty sensor.
3. **Measure:** share of days above 15 µg/m³ and above 75 µg/m³, the mean against the annual guideline, the worst day, and the same by month.

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "OPENAQ_API_KEY=your-key" > .env      # free key from explore.openaq.org; .env is git-ignored
python -m pytest -q                        # offline tests
python fetch_openaq.py                     # downloads the last 365 days
python analyze.py                          # writes results/
```

## Results
Period: ___ to ___ · Days with data: ___ · Sensors used: ___ (reference monitors: ___)

| Measure | Value |
|---|---|
| Days above WHO 24-hour guideline (15 µg/m³) | ___ % |
| Days above WHO interim target 1 (75 µg/m³) | ___ % |
| Median daily PM2.5 | ___ µg/m³ |
| Mean daily PM2.5 vs WHO annual guideline (5 µg/m³) | ___ × |
| Worst day | ___ (___ µg/m³, ___ × the 24-hour guideline) |

![daily](results/daily_pm25.png)
![monthly](results/monthly_exceedance.png)

## My observations
_(3-5 lines after looking at the charts)_

## Limitations
- OpenAQ aggregates many providers. Some Lahore sensors are low-cost sensors, which can read high in humid conditions; the share of reference monitors is reported above.
- Sensors are not evenly spread across the city, and the set of active sensors changes over the year.
- The mean of daily values over this window is only an approximation of an official annual mean.
- Days with no valid sensor are missing, not zero; months with few days are less reliable.

## Next steps
- Compare low-cost sensors with reference monitors on the same days.
- Add weather (humidity, wind, temperature inversions) and crop-burning periods to explain the winter peak.
- Repeat for Karachi, Islamabad and a UK city such as Glasgow as a contrast.
