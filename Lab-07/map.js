// Import Mapbox as an ESM module
import mapboxgl from 'https://cdn.jsdelivr.net/npm/mapbox-gl@2.15.0/+esm';

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

});
