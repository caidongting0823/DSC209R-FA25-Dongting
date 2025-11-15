// Import Mapbox as an ESM module
import mapboxgl from 'https://cdn.jsdelivr.net/npm/mapbox-gl@2.15.0/+esm';

// Import D3 as an ES module
import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7.9.0/+esm';

// URLs for the Bluebikes data
const INPUT_BLUEBIKES_STATIONS_URL =
  'https://dsc-courses.github.io/dsc209r-2025-fa/labs/lab07/data/bluebikes-stations.json';

const INPUT_BLUEBIKES_TRIPS_URL =
  'https://dsc106.com/labs/lab07/data/bluebikes-traffic-2024-03.csv';

const MINUTES_PER_DAY = 1440;

// Global station list (geometry + metadata)
let stations = [];

// For Step 5.4: buckets of trips by minute
let departuresByMinute = Array.from({ length: MINUTES_PER_DAY }, () => []);
let arrivalsByMinute = Array.from({ length: MINUTES_PER_DAY }, () => []);

// Current time filter in minutes since midnight (-1 = any time)
let timeFilter = -1;

// Set your Mapbox access token here (your token is already set)
mapboxgl.accessToken =
  'pk.eyJ1IjoiY2FpZG9uZ3RpbmcwODIzIiwiYSI6ImNtaHpvaXRtbjBxNm8ybG9wczg4bGo4b2oifQ.JO7KXXo799BB8l8c-XZ2fg';

// Initialize the map
const map = new mapboxgl.Map({
  container: 'map', // ID of the div where the map will render
  style: 'mapbox://styles/caidongting0823/cmhzpa2jo00k801su3iut2cyt', // Your custom style
  // style: 'mapbox://styles/mapbox/streets-v12', // Mapbox Light style
  center: [-71.09415, 42.36027], // [longitude, latitude] (Cambridge/Boston area)
  zoom: 12,
  minZoom: 5,
  maxZoom: 18
});

// ---------- Helper functions ----------

// Convert a station's lat/long to pixel coordinates on the current map view
function getCoords(station) {
  const point = new mapboxgl.LngLat(station.lon, station.lat);
  const { x, y } = map.project(point);
  return { cx: x, cy: y };
}

// Format minutes since midnight as "HH:MM AM/PM"
function formatTime(minutes) {
  const date = new Date(0, 0, 0, 0, minutes);
  return date.toLocaleString('en-US', { timeStyle: 'short' });
}

// Minutes since midnight for a Date object
function minutesSinceMidnight(date) {
  return date.getHours() * 60 + date.getMinutes();
}

// Step 5.4: efficient filtering using pre-bucketed trips
function filterByMinute(tripsByMinute, minute) {
  if (minute === -1) {
    // no filtering: flatten all buckets
    return tripsByMinute.flat();
  }

  const n = tripsByMinute.length; // 1440
  let minMinute = (minute - 60 + n) % n;
  let maxMinute = (minute + 60) % n;

  // If the window wraps past midnight
  if (minMinute > maxMinute) {
    const beforeMidnight = tripsByMinute.slice(minMinute);
    const afterMidnight = tripsByMinute.slice(0, maxMinute);
    return beforeMidnight.concat(afterMidnight).flat();
  } else {
    return tripsByMinute.slice(minMinute, maxMinute).flat();
  }
}

// Step 5.3 / 5.4: compute arrivals, departures, total per station
function computeStationTraffic(baseStations, timeFilter = -1) {
  // Get the trips in the relevant time window
  const departureTrips = filterByMinute(departuresByMinute, timeFilter);
  const arrivalTrips = filterByMinute(arrivalsByMinute, timeFilter);

  // Roll up counts by station id
  const departures = d3.rollup(
    departureTrips,
    v => v.length,
    d => d.start_station_id
  );

  const arrivals = d3.rollup(
    arrivalTrips,
    v => v.length,
    d => d.end_station_id
  );

  // Attach arrivals / departures / totalTraffic to each station
  return baseStations.map(station => {
    const id = station.short_name; // station short code used in the CSV
    const dep = departures.get(id) ?? 0;
    const arr = arrivals.get(id) ?? 0;

    return {
      ...station,
      departures: dep,
      arrivals: arr,
      totalTraffic: dep + arr
    };
  });
}

// Step 6: color scale for traffic flow (0 = arrivals, 1 = departures)
const stationFlow = d3
  .scaleQuantize()
  .domain([0, 1])
  .range([0, 0.5, 1]);

// Tooltip helper: attach a <title> to each circle
function addTooltip(selection) {
  selection.each(function (d) {
    const circle = d3.select(this);
    circle.selectAll('title').remove();
    circle
      .append('title')
      .text(
        `${d.totalTraffic} trips (${d.departures} departures, ${d.arrivals} arrivals)`
      );
  });
}

// ---------- Main Map Logic ----------

map.on('load', async () => {
  console.log('Map loaded ✅');

  // --- Boston bike lanes source & layer (Step 2) ---
  map.addSource('boston_route', {
    type: 'geojson',
    data: 'https://bostonopendata-boston.opendata.arcgis.com/datasets/boston::existing-bike-network-2022.geojson?outSR=%7B%22latestWkid%22%3A3857%2C%22wkid%22%3A102100%7D'
  });

  map.addLayer({
    id: 'boston-bike-lanes',
    type: 'line',
    source: 'boston_route',
    paint: {
      'line-color': '#32D400',
      'line-width': 3,
      'line-opacity': 0.6
    }
  });

  // --- Cambridge bike lanes source & layer (Step 2.3) ---
  map.addSource('cambridge_route', {
    type: 'geojson',
    data: 'https://raw.githubusercontent.com/cambridgegis/cambridgegis_data/main/Recreation/Bike_Facilities/RECREATION_BikeFacilities.geojson'
  });

  map.addLayer({
    id: 'cambridge-bike-lanes',
    type: 'line',
    source: 'cambridge_route',
    paint: {
      'line-color': '#32D400',
      'line-width': 3,
      'line-opacity': 0.6
    }
  });

  // --- Step 3.1: Fetch station JSON ---
  let jsonData;
  try {
    jsonData = await d3.json(INPUT_BLUEBIKES_STATIONS_URL);
    console.log('Loaded JSON Data:', jsonData);
  } catch (error) {
    console.error('Error loading station JSON:', error);
    return;
  }

  // Normalize station coordinates
  stations = jsonData.data.stations
    .map(station => {
      const lat = parseFloat(station.lat);
      const lon = parseFloat(station.lon);
      return {
        ...station,
        lat,
        lon
      };
    })
    .filter(s => Number.isFinite(s.lat) && Number.isFinite(s.lon));

  console.log('Stations Array (filtered):', stations);
  console.log('First station:', stations[0]);

  // --- Step 4.1: Load trips CSV and bucket by minute ---
  let trips = [];
  try {
    trips = await d3.csv(
      INPUT_BLUEBIKES_TRIPS_URL,
      trip => {
        trip.started_at = new Date(trip.started_at);
        trip.ended_at = new Date(trip.ended_at);

        const startedMinutes = minutesSinceMidnight(trip.started_at);
        const endedMinutes = minutesSinceMidnight(trip.ended_at);

        if (Number.isFinite(startedMinutes)) {
          departuresByMinute[startedMinutes].push(trip);
        }
        if (Number.isFinite(endedMinutes)) {
          arrivalsByMinute[endedMinutes].push(trip);
        }

        return trip;
      }
    );
    console.log('Loaded trips:', trips.length);
  } catch (error) {
    console.error('Error loading trips CSV:', error);
  }

  // --- Step 4.2: compute initial traffic (no time filter) ---
  stations = computeStationTraffic(stations); // timeFilter = -1 by default

  // --- Step 4.3 + 4.4: SVG overlay and circles sized by traffic ---
  const svg = d3.select('#map').select('svg');

  let radiusScale = d3
    .scaleSqrt()
    .domain([0, d3.max(stations, d => d.totalTraffic)])
    .range([0, 20]);

  const circles = svg
    .selectAll('circle')
    .data(stations, d => d.short_name)
    .enter()
    .append('circle')
    .attr('r', d => radiusScale(d.totalTraffic))
    .attr('stroke', 'white')
    .attr('stroke-width', 1)
    .attr('fill-opacity', 0.6)
    .style('pointer-events', 'auto')
    .style('--departure-ratio', d => {
      const ratio = d.totalTraffic > 0 ? d.departures / d.totalTraffic : 0.5;
      return stationFlow(ratio);
    })
    .call(addTooltip);


  // Position circles on the map
  function updatePositions() {
    circles
      .attr('cx', d => getCoords(d).cx)
      .attr('cy', d => getCoords(d).cy);
  }

  // Initial positioning
  updatePositions();

  // Reposition markers on map interactions
  map.on('move', updatePositions);
  map.on('zoom', updatePositions);
  map.on('resize', updatePositions);
  map.on('moveend', updatePositions);

  // ---------- Step 5: Interactive data filtering ----------

  const timeSlider = document.getElementById('time-slider');
  const selectedTime = document.getElementById('selected-time');
  const anyTimeLabel = document.getElementById('any-time');

  // Recompute station traffic for the current filter and update circle sizes
  function updateScatterPlot(currentFilter) {
    const filteredStations = computeStationTraffic(stations, currentFilter);

    const maxTraffic = d3.max(filteredStations, d => d.totalTraffic) || 0;
    radiusScale.domain([0, maxTraffic]);

    // Change circle size range depending on whether filtering is applied (Step 5.4)
    if (currentFilter === -1) {
      // Overview: many stations -> keep dots fairly small
      radiusScale.range([0, 20]);
    } else {
      // Filtered (fewer trips): make dots a bit bigger, but not huge
      radiusScale.range([2, 30]);
    }

    circles
      .data(filteredStations, d => d.short_name)
      .attr('r', d => radiusScale(d.totalTraffic))
      .style('--departure-ratio', d => {
        const ratio = d.totalTraffic > 0 ? d.departures / d.totalTraffic : 0.5;
        return stationFlow(ratio);
      })
      .call(addTooltip);

    // Positions are recomputed on map move/zoom, but we can refresh once too
    updatePositions();
  }

  // Step 5.2: react to slider movement
  function updateTimeDisplay() {
    timeFilter = Number(timeSlider.value);

    if (timeFilter === -1) {
      selectedTime.textContent = '';
      anyTimeLabel.style.display = 'block';
    } else {
      selectedTime.textContent = formatTime(timeFilter);
      anyTimeLabel.style.display = 'none';
    }

    updateScatterPlot(timeFilter);
  }

  // Listen for slider input
  timeSlider.addEventListener('input', updateTimeDisplay);

  // Initialize display to the default slider value
  updateTimeDisplay();
});
