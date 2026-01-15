/**
 * CityFeel Emotion Map
 * Wyświetlanie lokalizacji z emocjami z clustering i dynamic loading
 */
(function () {
    'use strict';

    // === KONFIGURACJA ===
    const CONFIG = {
        DEBOUNCE_DELAY: 300,  // ms - opóźnienie dla moveend event

        // Specjalne kolory punktów
        COLORS: {
            EMPTY: '#7f8c8d',   // Szary - brak ocen i komentarzy
            COMMENT: '#9b59b6'  // Fioletowy - tylko komentarze (brak ocen)
        },

        // Kolory według avg_emotional_value (1-5)
        EMOTION_COLORS: {
            1.0: '#e74c3c',  // Bardzo negatywne (czerwony)
            2.0: '#e67e22',  // Negatywne (pomarańczowy)
            3.0: '#f39c12',  // Neutralne (żółty)
            4.0: '#2ecc71',  // Pozytywne (zielony)
            5.0: '#27ae60',  // Bardzo pozytywne (ciemnozielony)
        },

        // 3 ODDZIELNE WARSTWY HEATMAPY
        HEATMAP: {
            RADIUS: 35,
            BLUR: 20,
            MAX_ZOOM: 16,
            MIN_OPACITY: 0.5,

            // Warstwa ZŁA (1.0 - 2.5) -> Odcienie czerwieni
            GRADIENT_BAD: {
                0.4: '#e74c3c', // Czerwony
                1.0: '#b03a2e'  // Ciemny Czerwony
            },
            // Warstwa NEUTRALNA (2.5 - 3.5) -> Odcienie żółtego
            GRADIENT_NEUTRAL: {
                0.4: '#f39c12', // Żółty
                1.0: '#d35400'  // Ciemny Pomarańcz
            },
            // Warstwa DOBRA (3.5 - 5.0) -> Odcienie zieleni
            GRADIENT_GOOD: {
                0.4: '#2ecc71', // Jasny Zielony
                1.0: '#196f3d'  // Bardzo Ciemny Zielony
            }
        }
    };

    // === STAN ===
    let map = null;
    let markerClusterGroup = null;
    let debounceTimer = null;
    let currentBounds = null;

    // Heatmap layers
    let heatLayerBad = null;
    let heatLayerNeutral = null;
    let heatLayerGood = null;

    let isHeatmapActive = false;
    let currentLocationsData = [];

    // Filters & UI
    let activeFilters = [];
    let addEmotionModal = null;
    let isUserAuthenticated = false;
    let selectedCoordinates = null;
    let proximityRadius = 50;
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
        initHeatmapControls();

        // Markery
        markerClusterGroup = L.markerClusterGroup({
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
            iconCreateFunction: createClusterIcon
        });

        // Heatmapy (3 warstwy)
        if (typeof L.heatLayer === 'function') {
            const commonOptions = {
                radius: CONFIG.HEATMAP.RADIUS,
                blur: CONFIG.HEATMAP.BLUR,
                maxZoom: CONFIG.HEATMAP.MAX_ZOOM,
                minOpacity: CONFIG.HEATMAP.MIN_OPACITY
            };

            heatLayerBad = L.heatLayer([], { ...commonOptions, gradient: CONFIG.HEATMAP.GRADIENT_BAD });
            heatLayerNeutral = L.heatLayer([], { ...commonOptions, gradient: CONFIG.HEATMAP.GRADIENT_NEUTRAL });
            heatLayerGood = L.heatLayer([], { ...commonOptions, gradient: CONFIG.HEATMAP.GRADIENT_GOOD });
        }

        map.addLayer(markerClusterGroup);
        map.on('moveend', debounce(loadVisibleLocations, CONFIG.DEBOUNCE_DELAY));

        loadVisibleLocations();
    }

    // === FILTRY ===
    function initFilters() {
        const filtersContainer = document.getElementById('map-filters');
        if (!filtersContainer) return;

        const buttons = filtersContainer.querySelectorAll('.filter-btn');

        buttons.forEach(btn => {
            btn.addEventListener('click', function (e) {
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
            } else {
                // Pozostaje outline
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

    // === IKONY KLASTRÓW ===
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

    function getColorByValue(value) {
        if (!value) return CONFIG.EMOTION_COLORS[3.0];
        if (value < 1.5) return CONFIG.EMOTION_COLORS[1.0];
        if (value < 2.5) return CONFIG.EMOTION_COLORS[2.0];
        if (value < 3.5) return CONFIG.EMOTION_COLORS[3.0];
        if (value < 4.5) return CONFIG.EMOTION_COLORS[4.0];
        return CONFIG.EMOTION_COLORS[5.0];
    }

    // === POBIERANIE DANYCH ===
    function loadVisibleLocations(force = false) {
        const bounds = map.getBounds();
        const sw = bounds.getSouthWest().wrap();
        const ne = bounds.getNorthEast().wrap();
        const bbox = [sw.lng, sw.lat, ne.lng, ne.lat].join(',');

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
        fetch(url, {
            credentials: 'same-origin',
            headers: { 'Accept': 'application/json' }
        })
            .then(response => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            })
            .then(data => {
                const locations = Array.isArray(data) ? data : (data.results || []);
                currentLocationsData = locations;

                if (isHeatmapActive) {
                    updateHeatmapData(locations);
                } else {
                    displayLocations(locations);
                }
            })
            .catch(error => {
                console.error('Error fetching locations:', error);
            })
            .finally(() => {
                document.body.style.cursor = 'default';
            });
    }

    // === RYSOWANIE MARKERÓW ===
    function displayLocations(locations) {
        markerClusterGroup.clearLayers();
        locations.forEach(location => {
            const marker = createMarker(location);
            markerClusterGroup.addLayer(marker);
        });
    }

    function createMarker(location) {
        const { coordinates, avg_emotional_value, name, id, emotion_points_count, comments_count } = location;
        const { latitude, longitude } = coordinates;

        let color;
        if (emotion_points_count > 0) {
            color = getColorByValue(avg_emotional_value);
        } else if (comments_count > 0) {
            color = CONFIG.COLORS.COMMENT;
        } else {
            color = CONFIG.COLORS.EMPTY;
        }

        const marker = L.circleMarker([latitude, longitude], {
            radius: 10,
            fillColor: color,
            color: '#ffffff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8,
            emotionValue: avg_emotional_value || 3.0
        });

        marker.bindPopup(createPopupContent(location));
        return marker;
    }

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
            commentHtml = `
        <div class="mt-2 mb-2 p-2 bg-light border-start border-3 border-primary rounded-end text-start">
            <div class="d-flex justify-content-between small text-muted mb-1">
                <strong>${escapeHtml(latest_comment.username)}</strong>
                <span>${latest_comment.emotional_value ? latest_comment.emotional_value + '/5' : ''}</span>
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
          ${avg_emotional_value ? stars : ''}
          <span class="ms-2 text-muted fw-bold">${avg_emotional_value ? avg_emotional_value.toFixed(1) : 'Brak ocen'}</span>
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
        if (!value) return '';
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
        if (count === 1) return 'ocenie';
        if (count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 10 || count % 100 >= 20)) return 'ocenach';
        return 'ocenach';
    }

    function showError(message) { alert(message); }

    function debounce(func, delay) {
        return function (...args) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // === DODAWANIE EMOCJI (MODAL) ===
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

        let closestLocation = null;
        let minDistance = Infinity;

        currentLocationsData.forEach(loc => {
            const dist = map.distance([lat, lng], [loc.coordinates.latitude, loc.coordinates.longitude]);
            if (dist < proximityRadius && dist < minDistance) {
                minDistance = dist;
                closestLocation = loc;
            }
        });

        if (closestLocation) {
            proximityText.textContent = `Twoja ocena zostanie przypisana do: "${closestLocation.name}" (${Math.round(minDistance)}m od kliknięcia)`;
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
            star.addEventListener('mouseenter', function () {
                for (let i = stars.length - 1; i >= index; i--) stars[i].style.color = '#f39c12';
                for (let i = index - 1; i >= 0; i--) stars[i].style.color = '#ddd';
            });
        });

        starRating.addEventListener('mouseleave', function () {
            const checkedRadio = starRating.querySelector('input[type="radio"]:checked');
            if (checkedRadio) updateStarsDisplay(checkedRadio);
            else stars.forEach(star => star.style.color = '#ddd');
        });

        radios.forEach(radio => {
            radio.addEventListener('change', function () { updateStarsDisplay(this); });
        });
    }

    function updateStarsDisplay(checkedRadio) {
        const starRating = document.getElementById('starRating');
        const stars = starRating.querySelectorAll('label');
        const value = parseInt(checkedRadio.value, 10);

        stars.forEach((star, index) => {
            const starValue = 5 - index;
            if (starValue <= value) star.style.color = '#f39c12';
            else star.style.color = '#ddd';
        });
    }

    async function handleEmotionSubmit() {
        const emotionalValue = document.querySelector('input[name="emotional_value"]:checked');
        const privacyStatus = document.getElementById('privacyStatus').value;
        const locationNameInput = document.getElementById('locationName');
        const locationNameContainer = document.getElementById('locationNameContainer');
        const commentInput = document.getElementById('emotionComment');

        if (!emotionalValue) {
            showEmotionError('Musisz wybrać ocenę (kliknij na gwiazdki).');
            return;
        }

        hideEmotionErrors();
        const submitBtn = document.getElementById('submitEmotion');
        const submitText = document.getElementById('submitText');
        const submitSpinner = document.getElementById('submitSpinner');

        submitBtn.disabled = true;
        submitText.classList.add('d-none');
        submitSpinner.classList.remove('d-none');

        const locationData = {
            coordinates: { latitude: selectedCoordinates.latitude, longitude: selectedCoordinates.longitude }
        };

        if (!locationNameContainer.classList.contains('d-none')) {
            const locationName = locationNameInput.value.trim();
            if (locationName) locationData.name = locationName;
        }

        const payload = {
            location: locationData,
            emotional_value: parseInt(emotionalValue.value, 10),
            privacy_status: privacyStatus,
            comment: commentInput ? commentInput.value.trim() : ''
        };

        try {
            const csrfToken = getCsrfToken();
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

            if (!response.ok) {
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.includes("application/json")) {
                    const errorData = await response.json();
                    handleApiErrors(errorData);
                } else {
                    throw new Error(`Błąd serwera (${response.status}).`);
                }
                return;
            }

            const data = await response.json();
            handleEmotionSuccess(data);

        } catch (error) {
            console.error('Network error:', error);
            showEmotionError(error.message || 'Błąd połączenia.');
        } finally {
            submitBtn.disabled = false;
            submitText.classList.remove('d-none');
            submitSpinner.classList.add('d-none');
        }
    }

    function handleEmotionSuccess(data) {
        addEmotionModal.hide();
        const toastElement = document.getElementById('successToast');
        const toastBody = document.getElementById('successMessage');
        const locationName = data.location?.name || 'lokalizacja';
        toastBody.textContent = `Twoja ocena została zapisana dla: ${locationName}`;
        const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 4000 });
        toast.show();
        loadVisibleLocations(true);
    }

    function handleApiErrors(errorData) {
        let errorMessage = 'Wystąpił błąd.';
        if (errorData.emotional_value) errorMessage = Array.isArray(errorData.emotional_value) ? errorData.emotional_value[0] : errorData.emotional_value;
        else if (errorData.detail) errorMessage = errorData.detail;
        showEmotionError(errorMessage);
    }

    function showEmotionError(message) {
        const errorsDiv = document.getElementById('emotionErrors');
        errorsDiv.textContent = message;
        errorsDiv.classList.remove('d-none');
    }

    function hideEmotionErrors() {
        document.getElementById('emotionErrors').classList.add('d-none');
    }

    function resetEmotionForm() {
        document.querySelectorAll('input[name="emotional_value"]').forEach(r => r.checked = false);
        document.querySelectorAll('#starRating label').forEach(s => s.style.color = '#ddd');
        document.getElementById('privacyStatus').value = 'public';
        document.getElementById('locationName').value = '';
        document.getElementById('locationNameContainer').classList.add('d-none');
        const comment = document.getElementById('emotionComment');
        if (comment) comment.value = '';
        hideEmotionErrors();
        document.getElementById('proximityInfo').classList.add('d-none');
        selectedCoordinates = null;
        document.getElementById('coordinatesDisplay').textContent = '-';
    }

    function getCsrfToken() {
        const name = 'csrftoken';
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    return decodeURIComponent(cookie.substring(name.length + 1));
                }
            }
        }
        return null;
    }

    // === OBSŁUGA PRZEŁĄCZANIA WIDOKU ===

    function initHeatmapControls() {
        const toggle = document.getElementById('heatmapToggle');
        const radiusInput = document.getElementById('heatmapRadius');
        const settingsDiv = document.getElementById('heatmapSettings');

        if (toggle) {
            toggle.addEventListener('change', function (e) {
                isHeatmapActive = e.target.checked;
                toggleHeatmapView();
                if (isHeatmapActive) {
                    settingsDiv.classList.remove('d-none');
                } else {
                    settingsDiv.classList.add('d-none');
                }
            });
        }

        if (radiusInput) {
            radiusInput.addEventListener('input', function (e) {
                const radius = parseInt(e.target.value, 10);
                if (heatLayerBad) heatLayerBad.setOptions({ radius: radius });
                if (heatLayerNeutral) heatLayerNeutral.setOptions({ radius: radius });
                if (heatLayerGood) heatLayerGood.setOptions({ radius: radius });
            });
        }
    }

    function toggleHeatmapView() {
        if (!heatLayerBad) return;

        if (isHeatmapActive) {
            // Włącz heatmapę (wszystkie 3 warstwy)
            if (map.hasLayer(markerClusterGroup)) map.removeLayer(markerClusterGroup);

            if (!map.hasLayer(heatLayerBad)) map.addLayer(heatLayerBad);
            if (!map.hasLayer(heatLayerNeutral)) map.addLayer(heatLayerNeutral);
            if (!map.hasLayer(heatLayerGood)) map.addLayer(heatLayerGood);

            updateHeatmapData(currentLocationsData);
        } else {
            // Wyłącz heatmapę
            if (map.hasLayer(heatLayerBad)) map.removeLayer(heatLayerBad);
            if (map.hasLayer(heatLayerNeutral)) map.removeLayer(heatLayerNeutral);
            if (map.hasLayer(heatLayerGood)) map.removeLayer(heatLayerGood);

            if (!map.hasLayer(markerClusterGroup)) {
                map.addLayer(markerClusterGroup);
            }

            // NAPRAWA: Zawsze odśwież markery przy powrocie do normalnego widoku!
            displayLocations(currentLocationsData);
        }
    }

    function updateHeatmapData(locations) {
        if (!heatLayerBad) return;

        // Rozdzielamy punkty na 3 "koszyki"
        const badPoints = [];
        const neutralPoints = [];
        const goodPoints = [];

        locations.forEach(loc => {
            const val = loc.avg_emotional_value || 0;
            const point = [
                loc.coordinates.latitude,
                loc.coordinates.longitude,
                0.8 // Stała wysoka intensywność (kolor zależy od warstwy, nie od zagęszczenia)
            ];

            // 1. ZŁA (1.0 - 2.5)
            if (val < 2.5) {
                badPoints.push(point);
            }
            // 2. NEUTRALNA (2.5 - 3.5)
            else if (val >= 2.5 && val < 3.8) {
                neutralPoints.push(point);
            }
            // 3. DOBRA (3.5 - 5.0)
            else {
                goodPoints.push(point);
            }
        });

        // Aktualizujemy każdą warstwę niezależnie
        heatLayerBad.setLatLngs(badPoints);
        heatLayerNeutral.setLatLngs(neutralPoints);
        heatLayerGood.setLatLngs(goodPoints);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();