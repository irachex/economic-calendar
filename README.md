# Economic Calendar Generator

Automatically fetch and generate US economic events calendar (.ics) with GitHub Actions. Supports Google Calendar, Apple Calendar, and other iCal-compatible apps.

Just subscribe [this ics link](https://irachex.github.io/economic-calendar/output/us-economic-calendar.ics) in your calendar app.

## Features

- 📊 **CPI** (Consumer Price Index) - Monthly inflation data
- 💼 **NFP** (Non-Farm Payrolls) - Monthly employment report
- 🏦 **FOMC** (Federal Reserve Meetings) - 8 meetings per year
- 📈 **GDP** - Quarterly economic growth data
- 💰 **Core PCE** - Fed's preferred inflation gauge
- 🛒 **Retail Sales** - Consumer spending indicator

## Subscribe

Subscribe: `https://irachex.github.io/economic-calendar/output/us-economic-calendar.ics`

The calendar will auto-sync daily.

## Local Development

```bash
# Generate calendar
python src/generate_ics.py

# View output
open ../output/us-economic-calendar.ics
```

---

**Note**: Event times are in US Eastern Time (ET). Your calendar app will automatically convert to your local timezone.
