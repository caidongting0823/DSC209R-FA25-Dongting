import pandas as pd
import requests
import time


def download_earthquakes(start_date, end_date, region_name, lat_min, lat_max, lon_min, lon_max, min_mag=4.5):
    base_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    params = {
        'format': 'csv',
        'starttime': start_date,
        'endtime': end_date,
        'minmagnitude': min_mag,
        'minlatitude': lat_min,
        'maxlatitude': lat_max,
        'minlongitude': lon_min,
        'maxlongitude': lon_max,
        'orderby': 'time'
    }

    print(f"  {region_name}: {start_date} to {end_date}...", end=' ')

    try:
        response = requests.get(base_url, params=params, timeout=30)

        if response.status_code == 200:
            # Count lines (minus header)
            line_count = len(response.text.split('\n')) - 2
            print(f"✓ {line_count} earthquakes")
            return response.text
        else:
            print(f"✗ Error {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ Exception: {e}")
        return None


# Define bounding boxes for each US region
REGIONS = {
    'Conterminous_US': {
        'lat_min': 24.6,  # Southern tip of Florida/Texas
        'lat_max': 50.0,  # Canadian border
        'lon_min': -125.0,  # Pacific coast
        'lon_max': -65.0  # Atlantic coast
    },
    "Alaska_west_dateline": {
        'lat_min': 50.0,  # Alaska south
        'lat_max': 72.0,  # Alaska north
        'lon_min': -180.0,  # Western hemisphere limit
        'lon_max': -169.5  # Just west of Alaska
    },
    "Alaska_main": {
        'lat_min': 54.0,  # Alaska south
        'lat_max': 72.0,  # Alaska north
        'lon_min': -169.5,  # Just west of Alaska
        'lon_max': -129.0  # Eastern Alaska
    },
    "Alaska_east_dateline": {
        'lat_min': 50.0,  # Alaska south
        'lat_max': 72.0,  # Alaska north
        'lon_min': 170.0,  # Just east of Alaska
        'lon_max': 180.0  # Eastern hemisphere limit
    },
    'Hawaii': {
        'lat_min': 18.5,  # Big Island south
        'lat_max': 22.5,  # Kauai north
        'lon_min': -161.0,  # Western islands
        'lon_max': -154.5  # Big Island east
    },
    'Puerto_Rico': {
        'lat_min': 17.5,  # South coast
        'lat_max': 18.8,  # North coast
        'lon_min': -67.5,  # West coast
        'lon_max': -64.0  # East coast + Virgin Islands
    }
}

# Time periods - with M4.5+, we can use longer chunks
date_ranges = [
    # Early decades - 10 years each
    ('1925-01-01', '1934-12-31'),
    ('1935-01-01', '1944-12-31'),
    ('1945-01-01', '1954-12-31'),
    ('1955-01-01', '1964-12-31'),
    ('1965-01-01', '1974-12-31'),
    ('1975-01-01', '1984-12-31'),
    ('1985-01-01', '1994-12-31'),

    # Recent decades - 5 years each
    ('1995-01-01', '1999-12-31'),
    ('2000-01-01', '2004-12-31'),
    ('2005-01-01', '2009-12-31'),
    ('2010-01-01', '2014-12-31'),
    ('2015-01-01', '2019-12-31'),
    ('2020-01-01', '2024-12-31'),
    ('2025-01-01', '2025-11-02'),
]

print(f"Downloading M4.5+ earthquakes for {len(date_ranges)} time periods...")
print(f"Regions: Conterminous US, Alaska (3 boxes), Hawaii, Puerto Rico")
print('=' * 70)

all_data = []

for i, (start, end) in enumerate(date_ranges, 1):
    print(f"\n[{i}/{len(date_ranges)}] {start} to {end}:")

    period_data = []

    # Download each region separately for this time period
    for region_name, bounds in REGIONS.items():
        csv_text = download_earthquakes(
            start, end, region_name,
            bounds['lat_min'], bounds['lat_max'],
            bounds['lon_min'], bounds['lon_max'],
            min_mag=4.5
        )

        if csv_text:
            period_data.append(csv_text)

        time.sleep(1)  # Small delay between regions

    all_data.extend(period_data)
    time.sleep(2)  # Delay between time periods

print(f"\n{'=' * 70}")
print("Processing and combining data...")
print('=' * 70)

# Combine all CSV texts
if all_data:
    # Start with first dataset (has header)
    combined_text = all_data[0]

    # Add subsequent datasets (skip their headers)
    for csv_text in all_data[1:]:
        lines = csv_text.split('\n')
        if len(lines) > 1:
            # Skip header line, add data
            combined_text += '\n' + '\n'.join(lines[1:])

    # Save to temporary file
    with open('temp_combined.csv', 'w', encoding='utf-8') as f:
        f.write(combined_text)

    # Read with pandas to clean and deduplicate
    df = pd.read_csv('temp_combined.csv')

    print(f"\n  Raw total: {len(df):,} earthquakes")

    # Remove duplicates (some might be near region boundaries)
    df = df.drop_duplicates(subset=['time', 'latitude', 'longitude', 'mag'])
    print(f"  After deduplication: {len(df):,} earthquakes")


    # Add region column based on coordinates
    def classify_region(row):
        lat, lon = row['latitude'], row['longitude']

        # Check Alaska (three boxes)
        if (REGIONS['Alaska_west_dateline']['lat_min'] <= lat <= REGIONS['Alaska_west_dateline']['lat_max'] and
                REGIONS['Alaska_west_dateline']['lon_min'] <= lon <= REGIONS['Alaska_west_dateline']['lon_max']):
            return 'Alaska'
        elif (REGIONS['Alaska_main']['lat_min'] <= lat <= REGIONS['Alaska_main']['lat_max'] and
              REGIONS['Alaska_main']['lon_min'] <= lon <= REGIONS['Alaska_main']['lon_max']):
            return 'Alaska'
        elif (REGIONS['Alaska_east_dateline']['lat_min'] <= lat <= REGIONS['Alaska_east_dateline']['lat_max'] and
              REGIONS['Alaska_east_dateline']['lon_min'] <= lon <= REGIONS['Alaska_east_dateline']['lon_max']):
            return 'Alaska'
        # Check Hawaii
        elif (REGIONS['Hawaii']['lat_min'] <= lat <= REGIONS['Hawaii']['lat_max'] and
              REGIONS['Hawaii']['lon_min'] <= lon <= REGIONS['Hawaii']['lon_max']):
            return 'Hawaii'
        # Check Puerto Rico
        elif (REGIONS['Puerto_Rico']['lat_min'] <= lat <= REGIONS['Puerto_Rico']['lat_max'] and
              REGIONS['Puerto_Rico']['lon_min'] <= lon <= REGIONS['Puerto_Rico']['lon_max']):
            return 'Puerto Rico'
        # Everything else is Conterminous US
        else:
            return 'Conterminous US'


    df['region'] = df.apply(classify_region, axis=1)

    # Sort by time
    df = df.sort_values('time')

    # Save final file
    df.to_csv('us_earthquakes_m4.5_complete.csv', index=False)

    # Print summary statistics
    print(f"\n{'=' * 70}")
    print("✓ SUCCESS!")
    print('=' * 70)
    print(f"Total earthquakes (M4.5+): {len(df):,}")
    print(f"Date range: {df['time'].min()} to {df['time'].max()}")
    print(f"Magnitude range: {df['mag'].min():.1f} to {df['mag'].max():.1f}")
    print(f"\nBreakdown by region:")
    print(df['region'].value_counts().to_string())
    print(f"\nSaved as: us_earthquakes_m4.5_complete.csv")
    print('=' * 70)

    # Clean up temp file
    import os

    os.remove('temp_combined.csv')
else:
    print("\n✗ No data downloaded successfully")