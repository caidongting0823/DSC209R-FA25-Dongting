// Import Mapbox as an ESM module
import mapboxgl from 'https://cdn.jsdelivr.net/npm/mapbox-gl@2.15.0/+esm';

// Import D3 as an ES module
import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7.9.0/+esm';

// URL for the Bluebikes station JSON
const INPUT_BLUEBIKES_STATIONS_URL =
  'https://dsc-courses.github.io/dsc209r-2025-fa/labs/lab07/data/bluebikes-stations.json';

// Global array to hold station objects
let stations = [];

// Set your Mapbox access token here (keep your own token)
mapboxgl.accessToken = 'pk.eyJ1IjoiY2FpZG9uZ3RpbmcwODIzIiwiYSI6ImNtaHpvaXRtbjBxNm8ybG9wczg4bGo4b2oifQ.JO7KXXo799BB8l8c-XZ2fg';

// Initialize the map
const map = new mapboxgl.Map({
  container: 'map', // ID of the div where the map will render
  style: 'mapbox://styles/caidongting0823/cmhzpa2jo00k801su3iut2cyt', // Your custom style
  center: [-71.09415, 42.36027], // [longitude, latitude] (Cambridge/Boston area)
  zoom: 12,
  minZoom: 5,
  maxZoom: 18
});

// Helper: convert station lat/long to pixel coordinates on the current map view
function getCoords(station) {
  // We'll populate station.lat / station.lon when parsing the JSON
  const point = new mapboxgl.LngLat(station.lon, station.lat);
  const { x, y } = map.project(point);
  return { cx: x, cy: y };
}

// Wait for the map to fully load before adding sources/layers
map.on('load', async () => {
  console.log('Map loaded ✅');

  // --- Boston bike lanes source ---
  map.addSource('boston_route', {
    type: 'geojson',
    data: 'https://bostonopendata-boston.opendata.arcgis.com/datasets/boston::existing-bike-network-2022.geojson?outSR=%7B%22latestWkid%22%3A3857%2C%22wkid%22%3A102100%7D'
  });

  // --- Boston bike lanes layer ---
  map.addLayer({
    id: 'boston-bike-lanes',
    type: 'line',
    source: 'boston_route',
    paint: {
      'line-color': '#32D400', // bright green
      'line-width': 3,
      'line-opacity': 0.6
    }
  });

  // --- Cambridge bike lanes source ---
  map.addSource('cambridge_route', {
    type: 'geojson',
    data: 'https://raw.githubusercontent.com/cambridgegis/cambridgegis_data/main/Recreation/Bike_Facilities/RECREATION_BikeFacilities.geojson'
  });

  // --- Cambridge bike lanes layer ---
  map.addLayer({
    id: 'cambridge-bike-lanes',
    type: 'line',
    source: 'cambridge_route',
    paint: {
      // You can make this slightly different if you want,
      // or keep it identical to Boston’s style.
      'line-color': '#32D400',
      'line-width': 3,
      'line-opacity': 0.6
    }
  });

  // Step 3.1: Fetch stations JSON
  let jsonData;

  try {
    const jsonurl = INPUT_BLUEBIKES_STATIONS_URL;

    // Await JSON fetch (D3 helper)
    jsonData = await d3.json(jsonurl);

    console.log('Loaded JSON Data:', jsonData); // Log to verify structure
  } catch (error) {
    console.error('Error loading JSON:', error); // Handle errors
    return; // Don't continue if stations failed to load
  }

  // Station data lives under jsonData.data.stations.
  // Normalize lat/lon properties (JSON uses lowercase lat / lon)
  stations = jsonData.data.stations
    .map((station) => {
      const lat = parseFloat(station.lat);
      const lon = parseFloat(station.lon);

      return {
        ...station,
        lat,
        lon
      };
    })
    // Filter out stations with invalid coordinates
    .filter((s) => Number.isFinite(s.lat) && Number.isFinite(s.lon));

  console.log('Stations Array (filtered):', stations);
  console.log('First station:', stations[0]);


  // Step 3.2: Select SVG overlay
  const svg = d3.select('#map').select('svg');

  // Step 3.3: Add station markers
  const circles = svg
    .selectAll('circle')
    .data(stations)
    .enter()
    .append('circle')
    .attr('r', 5) // Radius of the circle (we’ll adjust with traffic later)
    .attr('fill', 'steelblue')
    .attr('stroke', 'white')
    .attr('stroke-width', 1)
    .attr('opacity', 0.8);

  function updatePositions() {
    circles
      .attr('cx', (d) => getCoords(d).cx)
      .attr('cy', (d) => getCoords(d).cy);
  }

  // Initial positioning
  updatePositions();

  // Reposition markers on map interactions
  map.on('move', updatePositions);   // during map movement
  map.on('zoom', updatePositions);   // during zooming
  map.on('resize', updatePositions); // on window resize
  map.on('moveend', updatePositions); // final adjustment after movement ends


});
