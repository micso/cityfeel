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
      0.0: '#95a5a6',  // Brak oceny (szary)
      'COMMENT_ONLY': '#9b59b6', // [NOWE] Tylko komentarz (fioletowy)
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

  // Stan filtrów
  let activeFilters = [];

  // Stan dla dodawania emocji
  let addEmotionModal = null;
  let isUserAuthenticated = false;
  let selectedCoordinates = null;
  let proximityRadius = 50; // domyślnie 50m
  let emotionPointsUrl = '/api/emotion-points/';

  // === INICJALIZACJA ===
  function init() {
    map = window.map;
    const mapElement = document.getElementById('map');
    isUserAuthenticated = mapElement.dataset.userAuthenticated === 'true';
    proximityRadius = parseInt(mapElement.dataset.proximityRadius, 10) || 50;
    emotionPointsUrl = mapElement.dataset.emotionPointsUrl || '/api/emotion-points/';

    if (isUserAuthenticated) {
      initAddEmotionFeature();
    }

    initFilters();

    // Cluster group
    markerClusterGroup = L.markerClusterGroup({
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      iconCreateFunction: createClusterIcon
    });

    map.addLayer(markerClusterGroup);
    map.on('moveend', debounce(loadVisibleLocations, CONFIG.DEBOUNCE_DELAY));
    loadVisibleLocations();
  }

  // === OBSŁUGA FILTRÓW ===
  function initFilters() {
    const filtersContainer = document.getElementById('map-filters');
    if (!filtersContainer) return;

    const buttons = filtersContainer.querySelectorAll('.filter-btn');

    buttons.forEach(btn => {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        const btn = e.currentTarget;
        const value = parseInt(btn.dataset.value, 10);

        if (activeFilters.includes(value)) {
          activeFilters = activeFilters.filter(v => v !== value);
          toggleFilterButtonStyle(btn, false);
        } else {
          activeFilters.push(value);
          toggleFilterButtonStyle(btn, true);
        }
        loadVisibleLocations(true);
      });
    });
  }

  function toggleFilterButtonStyle(btn, isActive) {
    const classList = Array.from(btn.classList);
    const outlineClass = classList.find(c => c.startsWith('btn-outline-'));

    if (outlineClass) {
      const solidClass = outlineClass.replace('btn-outline-', 'btn-');
      if (isActive) {
        btn.classList.remove(outlineClass);
        btn.classList.add(solidClass, 'text-white', 'shadow');
      }
    } else {
        const solidClass = classList.find(c => c.startsWith('btn-') && !c.startsWith('btn-outline-') && c !== 'btn-sm');
        if (solidClass) {
             const outlineClass = solidClass.replace('btn-', 'btn-outline-');
             if (!isActive) {
                 btn.classList.remove(solidClass, 'text-white', 'shadow');
                 btn.classList.add(outlineClass);
             }
        }
    }
  }

  // === CLUSTER ICON ===
  function createClusterIcon(cluster) {
    const childMarkers = cluster.getAllChildMarkers();
    const avgValue = calculateAverageEmotionValue(childMarkers);

    // [NOWE] Sprawdź czy w klastrze są jakiekolwiek komentarze
    // (używane tylko jeśli avgValue == 0, czyli brak ocen)
    const hasComments = childMarkers.some(m => m.options.hasComments);

    const count = childMarkers.length;
    const color = getColorByValue(avgValue, hasComments);

    return L.divIcon({
      html: `<div style="background-color: ${color}"><span>${count}</span></div>`,
      className: 'marker-cluster-custom',
      iconSize: L.point(40, 40)
    });
  }

  function calculateAverageEmotionValue(markers) {
    if (!markers.length) return 0;

    // Bierzemy pod uwagę tylko markery z oceną (>0)
    const ratedMarkers = markers.filter(m => m.options.emotionValue && m.options.emotionValue > 0);

    if (ratedMarkers.length === 0) return 0;

    const sum = ratedMarkers.reduce((acc, marker) => {
      return acc + marker.options.emotionValue;
    }, 0);

    return sum / ratedMarkers.length;
  }

  // === KOLORY ===
  function getColorByValue(value, hasComments = false) {
    // [ZMIANA] Jeśli brak oceny (0 lub null)
    if (!value || value <= 0) {
        // Jeśli ma komentarze -> Fioletowy, w przeciwnym razie -> Szary
        return hasComments ? CONFIG.EMOTION_COLORS['COMMENT_ONLY'] : CONFIG.EMOTION_COLORS[0.0];
    }

    if (value < 1.5) return CONFIG.EMOTION_COLORS[1.0];
    if (value < 2.5) return CONFIG.EMOTION_COLORS[2.0];
    if (value < 3.5) return CONFIG.EMOTION_COLORS[3.0];
    if (value < 4.5) return CONFIG.EMOTION_COLORS[4.0];
    return CONFIG.EMOTION_COLORS[5.0];
  }

  // === LOADING LOCATIONS ===
  function loadVisibleLocations(force = false) {
    const bounds = map.getBounds();

    // Normalizuj współrzędne do zakresu -180..180
    // (potrzebne gdy mapa okrąża Ziemię i lng przekracza ±180)
    const sw = bounds.getSouthWest().wrap();
    const ne = bounds.getNorthEast().wrap();

    const bbox = [
      sw.lng,
      sw.lat,
      ne.lng,
      ne.lat
    ].join(',');

    if (!force && currentBounds === bbox) return;
    currentBounds = bbox;

    const apiUrl = document.getElementById('map').dataset.apiUrl || '/api/locations/';
    let url = `${apiUrl}?bbox=${bbox}`;

    if (activeFilters.length > 0) {
        url += `&emotional_value=${activeFilters.join(',')}`;
    }

    fetchLocations(url);
  }

  function fetchLocations(url) {
    document.body.style.cursor = 'wait';
    fetch(url, { headers: { 'Accept': 'application/json' } })
      .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
      .then(data => displayLocations(data.results || []))
      .catch(error => console.error('Error fetching locations:', error))
      .finally(() => document.body.style.cursor = 'default');
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
    const { coordinates, avg_emotional_value, comments_count } = location;
    const { latitude, longitude } = coordinates;

    // [NOWE] Sprawdź czy są komentarze
    const hasComments = comments_count > 0;

    // Pobierz kolor (uwzględniając komentarze przy braku oceny)
    const color = getColorByValue(avg_emotional_value, hasComments);

    const marker = L.circleMarker([latitude, longitude], {
      radius: 10,
      fillColor: color,
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.8,
      emotionValue: avg_emotional_value,
      hasComments: hasComments // [NOWE] Przechowaj info dla klastrowania
    });

    marker.bindPopup(createPopupContent(location));
    return marker;
  }

  // === POPUP ===
  function createPopupContent(location) {
    const { name, avg_emotional_value, emotion_points_count, comments_count, id, latest_comment } = location;
    const stars = getStarsHTML(avg_emotional_value);
    const detailsUrl = `/map/location/${id}/`;

    const ratingText = `Oparte na ${emotion_points_count || 0} ${pluralize(emotion_points_count)}`;
    let commentsText = '';
    const count = comments_count || 0;
    if (count === 1) commentsText = '1 komentarz';
    else if (count > 1 && count < 5) commentsText = `${count} komentarze`;
    else commentsText = `${count} komentarzy`;

    let commentHtml = '';
    if (latest_comment) {
      let ratingBadge = '';
      if (typeof latest_comment.emotional_value === 'number') {
          ratingBadge = `<span class="badge bg-warning text-dark border ms-2" style="font-size: 0.7rem;">${latest_comment.emotional_value}/5</span>`;
      }

      commentHtml = `
        <div class="mt-2 mb-2 p-2 bg-light border-start border-3 border-primary rounded-end text-start">
            <div class="d-flex justify-content-between align-items-center small text-muted mb-1">
                <strong>${escapeHtml(latest_comment.username)}</strong>
                ${ratingBadge}
            </div>
            <p class="mb-0 small fst-italic text-dark" style="line-height: 1.2;">
                "${escapeHtml(latest_comment.content)}"
            </p>
        </div>
      `;
    } else {
      commentHtml = `
        <div class="mt-2 mb-2 p-2 bg-light rounded text-center text-muted small fst-italic">
            Brak opinii. Bądź pierwszy!
        </div>
      `;
    }

    return `
      <div class="location-popup" style="min-width: 220px;">
        <h6 class="mb-2 fw-bold">${escapeHtml(name)}</h6>
        <div class="emotion-rating mb-1">
          ${stars}
          <span class="ms-2 text-muted fw-bold">${avg_emotional_value ? avg_emotional_value.toFixed(1) : '-'}</span>
        </div>
        <p class="text-muted small mb-2">${ratingText} &bull; ${commentsText}</p>
        ${commentHtml}
        <a href="${detailsUrl}" class="btn btn-sm btn-primary w-100 mt-1">Zobacz szczegóły</a>
      </div>
    `;
  }

  function getStarsHTML(value) {
    if (!value || value <= 0) return '<span class="text-muted small">Brak ocen</span>';
    const fullStars = Math.floor(value);
    const hasHalfStar = (value % 1) >= 0.5;
    let html = '';
    for (let i = 0; i < 5; i++) {
      if (i < fullStars) html += '★';
      else if (i === fullStars && hasHalfStar) html += '☆';
      else html += '☆';
    }
    return `<span class="stars" style="color: #f39c12; font-size: 1.2rem;">${html}</span>`;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function pluralize(count) {
    return 'ocenach';
  }

  function showEmotionError(message) { alert(message); }
  function debounce(func, delay) {
    return function(...args) { clearTimeout(debounceTimer); debounceTimer = setTimeout(() => func.apply(this, args), delay); };
  }
  function hideEmotionErrors() {
    const errorsDiv = document.getElementById('emotionErrors');
    if (errorsDiv) errorsDiv.classList.add('d-none');
  }

  // === ADD EMOTION FEATURE ===
  function handleApiErrors(errorData) {
    showEmotionError('Wystąpił błąd danych.');
  }

  function initAddEmotionFeature() {
    const modalElement = document.getElementById('addEmotionModal');
    if (!modalElement) return;
    addEmotionModal = new bootstrap.Modal(modalElement);
    map.on('click', handleMapClick);
    document.getElementById('map').classList.add('clickable-map');
    initStarRating();
    document.getElementById('submitEmotion').addEventListener('click', handleEmotionSubmit);
    modalElement.addEventListener('hidden.bs.modal', resetEmotionForm);
  }

  function handleMapClick(e) {
    const { lat, lng } = e.latlng;
    selectedCoordinates = { latitude: lat, longitude: lng };
    document.getElementById('coordinatesDisplay').textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    checkProximityAndShowInfo(lat, lng);
    addEmotionModal.show();
  }

  function checkProximityAndShowInfo(lat, lng) {
    const proximityInfo = document.getElementById('proximityInfo');
    const proximityText = document.getElementById('proximityText');
    const locationNameContainer = document.getElementById('locationNameContainer');
    const allMarkers = markerClusterGroup.getLayers();
    let closestMarker = null;
    let minDistance = Infinity;

    allMarkers.forEach(marker => {
      const markerLatLng = marker.getLatLng();
      const distance = map.distance([lat, lng], markerLatLng);
      if (distance < proximityRadius && distance < minDistance) {
        minDistance = distance;
        closestMarker = marker;
      }
    });

    if (closestMarker) {
      const popupContent = closestMarker.getPopup().getContent();
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = popupContent;
      const locationName = tempDiv.querySelector('h6').textContent;
      proximityText.textContent = `Twoja ocena zostanie przypisana do: "${locationName}"`;
      proximityInfo.classList.remove('d-none');
      proximityInfo.classList.add('alert-info');
      locationNameContainer.classList.add('d-none');
    } else {
      proximityText.textContent = 'Utworzysz nową lokalizację w tym miejscu';
      proximityInfo.classList.remove('d-none');
      proximityInfo.classList.add('alert-warning');
      locationNameContainer.classList.remove('d-none');
    }
  }

  function initStarRating() {
    const starRating = document.getElementById('starRating');
    const stars = starRating.querySelectorAll('label');
    const radios = starRating.querySelectorAll('input[type="radio"]');

    stars.forEach((star, index) => {
      star.addEventListener('mouseenter', function() {
        for (let i = stars.length - 1; i >= index; i--) stars[i].style.color = '#f39c12';
        for (let i = index - 1; i >= 0; i--) stars[i].style.color = '#ddd';
      });
    });
    starRating.addEventListener('mouseleave', function() {
      const checkedRadio = starRating.querySelector('input[type="radio"]:checked');
      if (checkedRadio) updateStarsDisplay(checkedRadio);
      else stars.forEach(star => star.style.color = '#ddd');
    });
    radios.forEach(radio => {
      radio.addEventListener('change', function() { updateStarsDisplay(this); });
    });
  }

  function updateStarsDisplay(checkedRadio) {
    const starRating = document.getElementById('starRating');
    const stars = starRating.querySelectorAll('label');
    const value = parseInt(checkedRadio.value, 10);
    stars.forEach((star, index) => {
      if (5 - index <= value) star.style.color = '#f39c12';
      else star.style.color = '#ddd';
    });
  }

  async function handleEmotionSubmit() {
    const emotionalValue = document.querySelector('input[name="emotional_value"]:checked');
    const privacyStatus = document.getElementById('privacyStatus').value;
    const locationNameInput = document.getElementById('locationName');
    const locationNameContainer = document.getElementById('locationNameContainer');
    const commentInput = document.getElementById('emotionComment');
    const commentValue = commentInput ? commentInput.value.trim() : '';

    if (!emotionalValue) { showEmotionError('Musisz wybrać ocenę.'); return; }
    hideEmotionErrors();

    const submitBtn = document.getElementById('submitEmotion');
    const submitText = document.getElementById('submitText');
    const submitSpinner = document.getElementById('submitSpinner');
    submitBtn.disabled = true;
    submitText.classList.add('d-none');
    submitSpinner.classList.remove('d-none');

    const locationData = { coordinates: { latitude: selectedCoordinates.latitude, longitude: selectedCoordinates.longitude } };
    if (!locationNameContainer.classList.contains('d-none')) {
      if (locationNameInput.value.trim()) locationData.name = locationNameInput.value.trim();
    }

    const payload = {
      location: locationData,
      emotional_value: parseInt(emotionalValue.value, 10),
      privacy_status: privacyStatus,
      comment: commentValue
    };

    try {
      const csrfToken = getCsrfToken();
      const response = await fetch(emotionPointsUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify(payload)
      });
      if (!response.ok) { handleApiErrors(await response.json()); return; }
      handleEmotionSuccess(await response.json());
    } catch (error) {
      showEmotionError('Błąd połączenia.');
    } finally {
      submitBtn.disabled = false;
      submitText.classList.remove('d-none');
      submitSpinner.classList.add('d-none');
    }
  }

  function handleEmotionSuccess(data) {
    addEmotionModal.hide();
    const toast = new bootstrap.Toast(document.getElementById('successToast'));
    document.getElementById('successMessage').textContent = `Ocena zapisana!`;
    toast.show();
    loadVisibleLocations(true);
  }

  function resetEmotionForm() {
    const radios = document.querySelectorAll('input[name="emotional_value"]');
    radios.forEach(radio => radio.checked = false);
    document.querySelectorAll('#starRating label').forEach(star => star.style.color = '#ddd');
    document.getElementById('privacyStatus').value = 'public';
    document.getElementById('locationName').value = '';
    document.getElementById('locationNameContainer').classList.add('d-none');
    const commentInput = document.getElementById('emotionComment');
    if (commentInput) commentInput.value = '';
    hideEmotionErrors();
    document.getElementById('proximityInfo').classList.add('d-none');
    selectedCoordinates = null;
  }

  function getCsrfToken() {
    if (!document.cookie) return null;
    const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : null;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

})();