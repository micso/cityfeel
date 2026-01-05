/**
 * CityFeel Emotion Map
 * Wyświetlanie lokalizacji z emocjami z clustering i dynamic loading
 */
(function() {
  'use strict';

  // === KONFIGURACJA ===
  const CONFIG = {
    DEBOUNCE_DELAY: 300,  // ms - opóźnienie dla moveend event

    // Kolory według avg_emotional_value (1-5)
    EMOTION_COLORS: {
      1.0: '#e74c3c',  // Bardzo negatywne (czerwony)
      2.0: '#e67e22',  // Negatywne (pomarańczowy)
      3.0: '#f39c12',  // Neutralne (żółty)
      4.0: '#2ecc71',  // Pozytywne (zielony)
      5.0: '#27ae60',  // Bardzo pozytywne (ciemnozielony)
    }
  };

  // === STAN ===
  let map = null;
  let markerClusterGroup = null;
  let debounceTimer = null;
  let currentBounds = null;

  // === INICJALIZACJA ===
  function init() {
    // Mapa jest już zainicjalizowana w template jako window.map
    map = window.map;

    // Cluster group
    markerClusterGroup = L.markerClusterGroup({
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      iconCreateFunction: createClusterIcon
    });

    map.addLayer(markerClusterGroup);

    // Event listeners
    map.on('moveend', debounce(loadVisibleLocations, CONFIG.DEBOUNCE_DELAY));

    // Pierwsze załadowanie
    loadVisibleLocations();
  }

  // === CLUSTER ICON ===
  function createClusterIcon(cluster) {
    const childMarkers = cluster.getAllChildMarkers();
    const avgValue = calculateAverageEmotionValue(childMarkers);
    const count = childMarkers.length;
    const color = getColorByValue(avgValue);

    return L.divIcon({
      html: `<div style="background-color: ${color}"><span>${count}</span></div>`,
      className: 'marker-cluster-custom',
      iconSize: L.point(40, 40)
    });
  }

  function calculateAverageEmotionValue(markers) {
    if (!markers.length) return 3.0;

    const sum = markers.reduce((acc, marker) => {
      return acc + (marker.options.emotionValue || 3.0);
    }, 0);

    return sum / markers.length;
  }

  // === KOLORY ===
  function getColorByValue(value) {
    if (!value) return CONFIG.EMOTION_COLORS[3.0];

    if (value < 1.5) return CONFIG.EMOTION_COLORS[1.0];
    if (value < 2.5) return CONFIG.EMOTION_COLORS[2.0];
    if (value < 3.5) return CONFIG.EMOTION_COLORS[3.0];
    if (value < 4.5) return CONFIG.EMOTION_COLORS[4.0];
    return CONFIG.EMOTION_COLORS[5.0];
  }

  // === LOADING LOCATIONS ===
  function loadVisibleLocations() {
    const bounds = map.getBounds();
    const bbox = [
      bounds.getSouthWest().lng,
      bounds.getSouthWest().lat,
      bounds.getNorthEast().lng,
      bounds.getNorthEast().lat
    ].join(',');

    // Sprawdź czy bounds się zmieniły
    if (currentBounds === bbox) return;
    currentBounds = bbox;

    // Pobierz API URL z data attribute
    const apiUrl = document.getElementById('map').dataset.apiUrl || '/api/locations/';
    const url = `${apiUrl}?bbox=${bbox}`;

    fetchLocations(url);
  }

  function fetchLocations(url) {
    fetch(url, {
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json'
      }
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        displayLocations(data.results || []);
      })
      .catch(error => {
        console.error('Error fetching locations:', error);
        showError('Nie udało się pobrać lokalizacji.');
      });
  }

  // === WYŚWIETLANIE MARKERÓW ===
  function displayLocations(locations) {
    markerClusterGroup.clearLayers();

    locations.forEach(location => {
      const marker = createMarker(location);
      markerClusterGroup.addLayer(marker);
    });
  }

  function createMarker(location) {
    const { coordinates, avg_emotional_value, name, id, emotion_points_count } = location;
    const { latitude, longitude } = coordinates;
    const color = getColorByValue(avg_emotional_value);

    const marker = L.circleMarker([latitude, longitude], {
      radius: 10,
      fillColor: color,
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.8,
      emotionValue: avg_emotional_value
    });

    marker.bindPopup(createPopupContent(location));

    return marker;
  }

  // === POPUP ===
  function createPopupContent(location) {
    const { name, avg_emotional_value, emotion_points_count, id } = location;

    const stars = getStarsHTML(avg_emotional_value);
    const detailsUrl = `/map/location/${id}/`;

    return `
      <div class="location-popup">
        <h5 class="mb-2">${escapeHtml(name)}</h5>
        <div class="emotion-rating mb-2">
          ${stars}
          <span class="ms-2 text-muted">${avg_emotional_value ? avg_emotional_value.toFixed(1) : 'Brak'}</span>
        </div>
        <p class="text-muted small mb-2">Oparte na ${emotion_points_count || 0} ${pluralize(emotion_points_count)}</p>
        <a href="${detailsUrl}" class="btn btn-sm btn-primary w-100">Zobacz szczegóły</a>
      </div>
    `;
  }

  function getStarsHTML(value) {
    if (!value) return '<span class="text-muted">Brak ocen</span>';

    const fullStars = Math.floor(value);
    const hasHalfStar = (value % 1) >= 0.5;
    let html = '';

    for (let i = 0; i < 5; i++) {
      if (i < fullStars) {
        html += '★';
      } else if (i === fullStars && hasHalfStar) {
        html += '☆';
      } else {
        html += '☆';
      }
    }

    return `<span class="stars" style="color: #f39c12; font-size: 1.2rem;">${html}</span>`;
  }

  // === UTILITIES ===
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function pluralize(count) {
    if (count === 1) return 'ocenie';
    if (count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 10 || count % 100 >= 20)) {
      return 'ocenach';
    }
    return 'ocenach';
  }

  function showError(message) {
    alert(message);
  }

  function debounce(func, delay) {
    return function(...args) {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => func.apply(this, args), delay);
    };
  }

  // === AUTO-INIT ===
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
