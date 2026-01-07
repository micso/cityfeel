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

  // Stan dla dodawania emocji
  let addEmotionModal = null;
  let isUserAuthenticated = false;
  let selectedCoordinates = null;
  let proximityRadius = 50; // domyślnie 50m, nadpisane z data-attribute
  let emotionPointsUrl = '/api/emotion-points/'; // fallback, nadpisane z data-attribute

  // === INICJALIZACJA ===
  function init() {
    // Mapa jest już zainicjalizowana w template jako window.map
    map = window.map;

    // Sprawdź czy user jest zalogowany i pobierz konfigurację z data-attributes
    const mapElement = document.getElementById('map');
    isUserAuthenticated = mapElement.dataset.userAuthenticated === 'true';
    proximityRadius = parseInt(mapElement.dataset.proximityRadius, 10) || 50;
    emotionPointsUrl = mapElement.dataset.emotionPointsUrl || '/api/emotion-points/';

    // Inicjalizacja funkcjonalności dodawania emocji (tylko dla zalogowanych)
    if (isUserAuthenticated) {
      initAddEmotionFeature();
    }

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
  function loadVisibleLocations(force = false) {
    const bounds = map.getBounds();
    const bbox = [
      bounds.getSouthWest().lng,
      bounds.getSouthWest().lat,
      bounds.getNorthEast().lng,
      bounds.getNorthEast().lat
    ].join(',');

    // Sprawdź czy bounds się zmieniły (chyba że force=true)
    if (!force && currentBounds === bbox) return;
    currentBounds = bbox;

    // Pobierz API URL z data attribute (generowany przez {% url 'api:locations-list' %})
    // Fallback '/api/locations/' używany tylko w razie problemów z template
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
    const { name, avg_emotional_value, emotion_points_count, comments_count, id, latest_comment } = location;

    const stars = getStarsHTML(avg_emotional_value);
    const detailsUrl = `/map/location/${id}/`;

    // 1. Budujemy teksty
    // "Oparte na 5 ocenach" (zakładamy, że funkcja pluralize robi robotę, tak jak wcześniej)
    const ratingText = `Oparte na ${emotion_points_count || 0} ${pluralize(emotion_points_count)}`;

    // "• 2 komentarze" (prosta odmiana dla słowa komentarz)
    let commentsText = '';
    const count = comments_count || 0;
    if (count === 1) commentsText = '1 komentarz';
    else if (count > 1 && count < 5) commentsText = `${count} komentarze`;
    else commentsText = `${count} komentarzy`;

    let commentHtml = '';
    if (latest_comment) {
      commentHtml = `
        <div class="mt-2 mb-2 p-2 bg-light border-start border-3 border-primary rounded-end text-start">
            <div class="d-flex justify-content-between small text-muted mb-1">
                <strong>${escapeHtml(latest_comment.username)}</strong>
                <span>${latest_comment.emotional_value}/5</span>
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

        <p class="text-muted small mb-2">
            ${ratingText} &bull; ${commentsText}
        </p>
        
        ${commentHtml}

        <a href="${detailsUrl}" class="btn btn-sm btn-primary w-100 mt-1">Zobacz szczegóły</a>
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

  // === ADD EMOTION FEATURE ===

  /**
   * Inicjalizacja funkcjonalności dodawania emocji.
   * Wywoływana tylko dla zalogowanych użytkowników.
   */
  function initAddEmotionFeature() {
    // Inicjalizacja Bootstrap Modal
    const modalElement = document.getElementById('addEmotionModal');
    if (!modalElement) {
      console.warn('Modal #addEmotionModal nie został znaleziony w HTML');
      return;
    }

    addEmotionModal = new bootstrap.Modal(modalElement);

    // Event listener dla kliknięcia na mapę
    map.on('click', handleMapClick);

    // Dodaj wizualną wskazówkę (cursor: crosshair)
    document.getElementById('map').classList.add('clickable-map');

    // Inicjalizacja interaktywnych gwiazdek
    initStarRating();

    // Event listener dla przycisku Submit
    document.getElementById('submitEmotion').addEventListener('click', handleEmotionSubmit);

    // Event listener dla zamknięcia modala - reset formularza
    modalElement.addEventListener('hidden.bs.modal', resetEmotionForm);
  }

  /**
   * Obsługa kliknięcia na mapę.
   * Otwiera modal z formularzem dodawania emocji.
   */
  function handleMapClick(e) {
    const { lat, lng } = e.latlng;

    // Zapisz współrzędne
    selectedCoordinates = { latitude: lat, longitude: lng };

    // Wyświetl współrzędne w modalu
    document.getElementById('coordinatesDisplay').textContent =
      `${lat.toFixed(5)}, ${lng.toFixed(5)}`;

    // Sprawdź proximity matching
    checkProximityAndShowInfo(lat, lng);

    // Otwórz modal
    addEmotionModal.show();
  }

  /**
   * Sprawdza czy w pobliżu klikniętego punktu (w promieniu proximityRadius)
   * istnieje już jakaś lokalizacja i wyświetla info o tym w modalu.
   */
  function checkProximityAndShowInfo(lat, lng) {
    const proximityInfo = document.getElementById('proximityInfo');
    const proximityText = document.getElementById('proximityText');
    const locationNameContainer = document.getElementById('locationNameContainer');

    // Pobierz wszystkie markery z cluster group
    const allMarkers = markerClusterGroup.getLayers();

    // Znajdź najbliższy marker w promieniu
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

    // Pokaż info jeśli znaleziono bliską lokalizację
    if (closestMarker) {
      const popupContent = closestMarker.getPopup().getContent();

      // Wyciągnij nazwę lokalizacji z popup HTML (parsing)
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = popupContent;
      const locationName = tempDiv.querySelector('h5').textContent;

      proximityText.textContent =
        `Twoja ocena zostanie przypisana do: "${locationName}" (${Math.round(minDistance)}m od kliknięcia)`;
      proximityInfo.classList.remove('d-none');
      proximityInfo.classList.add('alert-info');

      // Ukryj pole nazwy - przypisujemy do istniejącej lokalizacji
      locationNameContainer.classList.add('d-none');
    } else {
      proximityText.textContent = 'Utworzysz nową lokalizację w tym miejscu';
      proximityInfo.classList.remove('d-none');
      proximityInfo.classList.add('alert-warning');

      // Pokaż pole nazwy - użytkownik tworzy nową lokalizację
      locationNameContainer.classList.remove('d-none');
    }
  }

  /**
   * Inicjalizacja interaktywnych gwiazdek (click, hover preview).
   */
  function initStarRating() {
    const starRating = document.getElementById('starRating');
    const stars = starRating.querySelectorAll('label');
    const radios = starRating.querySelectorAll('input[type="radio"]');

    // Hover effect - preview
    stars.forEach((star, index) => {
      star.addEventListener('mouseenter', function() {
        // Podświetl gwiazdki od prawej do tej nad którą jest hover
        for (let i = stars.length - 1; i >= index; i--) {
          stars[i].style.color = '#f39c12';
        }
        // Przyciemnij pozostałe
        for (let i = index - 1; i >= 0; i--) {
          stars[i].style.color = '#ddd';
        }
      });
    });

    // Usunięcie hover - powrót do checked state
    starRating.addEventListener('mouseleave', function() {
      const checkedRadio = starRating.querySelector('input[type="radio"]:checked');
      if (checkedRadio) {
        updateStarsDisplay(checkedRadio);
      } else {
        // Wszystkie gwiazdki szare
        stars.forEach(star => star.style.color = '#ddd');
      }
    });

    // Click - zaznacz i zapisz
    radios.forEach(radio => {
      radio.addEventListener('change', function() {
        updateStarsDisplay(this);
      });
    });
  }

  /**
   * Aktualizuje wyświetlanie gwiazdek na podstawie zaznaczonego radio.
   */
  function updateStarsDisplay(checkedRadio) {
    const starRating = document.getElementById('starRating');
    const stars = starRating.querySelectorAll('label');
    const value = parseInt(checkedRadio.value, 10);

    // Wypełnij gwiazdki od prawej (5) do zaznaczonej wartości
    stars.forEach((star, index) => {
      const starValue = 5 - index; // gwiazdki są w odwrotnej kolejności w HTML
      if (starValue <= value) {
        star.style.color = '#f39c12'; // żółty
      } else {
        star.style.color = '#ddd'; // szary
      }
    });
  }

  /**
   * Obsługa wysłania formularza - dodanie emocji.
   */
  async function handleEmotionSubmit() {
    // Pobierz wartości z formularza
    const emotionalValue = document.querySelector('input[name="emotional_value"]:checked');
    const privacyStatus = document.getElementById('privacyStatus').value;
    const locationNameInput = document.getElementById('locationName');
    const locationNameContainer = document.getElementById('locationNameContainer');

    // Walidacja
    if (!emotionalValue) {
      showEmotionError('Musisz wybrać ocenę (kliknij na gwiazdki).');
      return;
    }

    // Ukryj błędy
    hideEmotionErrors();

    // Pokaż spinner
    const submitBtn = document.getElementById('submitEmotion');
    const submitText = document.getElementById('submitText');
    const submitSpinner = document.getElementById('submitSpinner');

    submitBtn.disabled = true;
    submitText.classList.add('d-none');
    submitSpinner.classList.remove('d-none');

    // Przygotuj dane lokalizacji
    const locationData = {
      coordinates: {
        latitude: selectedCoordinates.latitude,
        longitude: selectedCoordinates.longitude
      }
    };

    // Jeśli pole nazwy jest widoczne i wypełnione, dodaj name
    if (!locationNameContainer.classList.contains('d-none')) {
      const locationName = locationNameInput.value.trim();
      if (locationName) {
        locationData.name = locationName;
      }
    }

    // Przygotuj payload
    const payload = {
      location: locationData,
      emotional_value: parseInt(emotionalValue.value, 10),
      privacy_status: privacyStatus
    };

    try {
      // Pobierz CSRF token
      const csrfToken = getCsrfToken();

      // Wyślij POST request (URL z data-attribute, generowany przez {% url 'api:emotion_points-list' %})
      const response = await fetch(emotionPointsUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(payload)
      });

      // Obsługa odpowiedzi
      if (!response.ok) {
        // Obsługa błędów walidacji
        const errorData = await response.json();
        handleApiErrors(errorData);
        return;
      }

      // Sukces
      const data = await response.json();
      handleEmotionSuccess(data);

    } catch (error) {
      console.error('Network error:', error);
      showEmotionError('Błąd połączenia. Sprawdź połączenie internetowe i spróbuj ponownie.');
    } finally {
      // Przywróć przycisk
      submitBtn.disabled = false;
      submitText.classList.remove('d-none');
      submitSpinner.classList.add('d-none');
    }
  }

  /**
   * Obsługa sukcesu - zamknij modal, pokaż toast, odśwież mapę.
   */
  function handleEmotionSuccess(data) {
    // Zamknij modal
    addEmotionModal.hide();

    // Pokaż toast sukcesu
    const toastElement = document.getElementById('successToast');
    const toastBody = document.getElementById('successMessage');

    // Dostosuj komunikat
    const locationName = data.location?.name || 'lokalizacja';
    toastBody.textContent = `Twoja ocena została zapisana dla: ${locationName}`;

    const toast = new bootstrap.Toast(toastElement, {
      autohide: true,
      delay: 4000
    });
    toast.show();

    // Odśwież mapę - przeładuj widoczne lokalizacje (force=true aby pominąć sprawdzanie bounds)
    loadVisibleLocations(true);
  }

  /**
   * Obsługa błędów z API.
   */
  function handleApiErrors(errorData) {
    let errorMessage = 'Wystąpił błąd podczas dodawania oceny.';

    // Parsowanie błędów z DRF
    if (errorData.emotional_value) {
      errorMessage = Array.isArray(errorData.emotional_value)
        ? errorData.emotional_value[0]
        : errorData.emotional_value;
    } else if (errorData.location) {
      if (errorData.location.coordinates) {
        if (errorData.location.coordinates.latitude) {
          errorMessage = errorData.location.coordinates.latitude;
        } else if (errorData.location.coordinates.longitude) {
          errorMessage = errorData.location.coordinates.longitude;
        }
      }
    } else if (errorData.privacy_status) {
      errorMessage = Array.isArray(errorData.privacy_status)
        ? errorData.privacy_status[0]
        : errorData.privacy_status;
    } else if (errorData.detail) {
      errorMessage = errorData.detail;
    } else if (errorData.non_field_errors) {
      errorMessage = Array.isArray(errorData.non_field_errors)
        ? errorData.non_field_errors[0]
        : errorData.non_field_errors;
    }

    showEmotionError(errorMessage);
  }

  /**
   * Wyświetla błąd w modalu.
   */
  function showEmotionError(message) {
    const errorsDiv = document.getElementById('emotionErrors');
    errorsDiv.textContent = message;
    errorsDiv.classList.remove('d-none');
  }

  /**
   * Ukrywa błędy w modalu.
   */
  function hideEmotionErrors() {
    const errorsDiv = document.getElementById('emotionErrors');
    errorsDiv.classList.add('d-none');
  }

  /**
   * Resetuje formularz po zamknięciu modala.
   */
  function resetEmotionForm() {
    // Odznacz wszystkie radio buttons
    const radios = document.querySelectorAll('input[name="emotional_value"]');
    radios.forEach(radio => radio.checked = false);

    // Reset gwiazdek - wszystkie szare
    const stars = document.querySelectorAll('#starRating label');
    stars.forEach(star => star.style.color = '#ddd');

    // Resetuj privacy status
    document.getElementById('privacyStatus').value = 'public';

    // Wyczyść i ukryj pole nazwy lokalizacji
    const locationNameInput = document.getElementById('locationName');
    const locationNameContainer = document.getElementById('locationNameContainer');
    locationNameInput.value = '';
    locationNameContainer.classList.add('d-none');

    // Ukryj komunikaty
    hideEmotionErrors();
    const proximityInfo = document.getElementById('proximityInfo');
    proximityInfo.classList.add('d-none');
    proximityInfo.classList.remove('alert-info', 'alert-warning');

    // Wyczyść współrzędne
    selectedCoordinates = null;
    document.getElementById('coordinatesDisplay').textContent = '-';
  }

  /**
   * Pobiera CSRF token z cookies.
   */
  function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;

    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }

    return cookieValue;
  }

  // === AUTO-INIT ===
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
