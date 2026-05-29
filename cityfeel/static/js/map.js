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

            // Warstwa ZŁA (1.0 - 2.5) -> Czerwony
            GRADIENT_BAD: {
                0.4: '#e74c3c',
                1.0: '#b03a2e'
            },
            // Warstwa NEUTRALNA (2.5 - 3.5) -> Żółty/Pomarańczowy
            GRADIENT_NEUTRAL: {
                0.4: '#f39c12',
                1.0: '#d35400'
            },
            // Warstwa DOBRA (3.5 - 5.0) -> Zielony
            GRADIENT_GOOD: {
                0.4: '#2ecc71',
                1.0: '#196f3d'
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
    let closestLocationData = null; // DODANA ZMIENNA
    let proximityRadius = 50;
    let emotionPointsUrl = '/api/emotion-points/';

    // Time filter state
    const timeFilter = {
        from: null,
        to: null,
        dataMin: null,
        dataMax: null,
        slider: null,
        chart: null,
        debounceTimer: null,
        playInterval: null,
        playing: false,
        ready: false,
        bucket: 'day',
        bucketAvgs: [],
        savedRange: null,
        fullBuckets: null,
        histogramMode: 'overview',
    };

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
        initTimeFilterToggle();
        initTimeFilter();
        initReportModal();

        markerClusterGroup = L.markerClusterGroup({
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
            iconCreateFunction: createClusterIcon
        });

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

        const timeKey = timeFilter.from && timeFilter.to
            ? `${timeFilter.from.toISOString()}|${timeFilter.to.toISOString()}`
            : '';
        const cacheKey = `${bbox}|${timeKey}`;
        if (!force && currentBounds === cacheKey) return;
        currentBounds = cacheKey;

        const apiUrl = document.getElementById('map').dataset.apiUrl || '/api/locations/';
        let url = `${apiUrl}?bbox=${bbox}`;

        if (activeFilters.length > 0) {
            url += `&emotional_value=${activeFilters.join(',')}`;
        }
        if (timeFilter.from && timeFilter.to) {
            url += `&created_after=${encodeURIComponent(timeFilter.from.toISOString())}`;
            url += `&created_before=${encodeURIComponent(timeFilter.to.toISOString())}`;
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
        const { coordinates, avg_emotional_value, id, emotion_points_count, comments_count, latest_comment } = location;
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

        marker.on('popupopen', () => {
            loadAndRenderLocationTimeline(id);

            // Rejestracja kliknięcia "Zgłoś lokalizację"
            const reportLocBtn = document.querySelector(`.btn-report-location[data-location-id="${id}"]`);
            if (reportLocBtn) {
                reportLocBtn.addEventListener('click', () => {
                    openReportModal('location', id);
                });
            }

            // Rejestracja kliknięcia "Zgłoś komentarz"
            if (latest_comment && latest_comment.id) {
                const reportComBtn = document.querySelector(`.btn-report-comment[data-comment-id="${latest_comment.id}"]`);
                if (reportComBtn) {
                    reportComBtn.addEventListener('click', () => {
                        openReportModal('comment', latest_comment.id);
                    });
                }
            }
        });
        return marker;
    }

    function loadAndRenderLocationTimeline(locationId) {
        const canvas = document.querySelector(`canvas.location-timeline[data-location-id="${locationId}"]`);
        if (!canvas || typeof Chart === 'undefined') return;
        if (canvas.dataset.rendered === '1') return;

        fetch(`/api/locations/${locationId}/emotion-timeline/?bucket=day`, {
            credentials: 'same-origin',
            headers: { 'Accept': 'application/json' }
        })
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
            .then(buckets => {
                if (!buckets || buckets.length === 0) {
                    canvas.parentElement.innerHTML = '<p class="text-muted small fst-italic mb-0">Brak historii emocji</p>';
                    return;
                }
                const labels = buckets.map(b => b.bucket);
                const values = buckets.map(b => b.avg_value);
                new Chart(canvas, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: values,
                            borderColor: '#0d6efd',
                            backgroundColor: 'rgba(13, 110, 253, 0.15)',
                            borderWidth: 2,
                            pointRadius: 2,
                            tension: 0.3,
                            fill: true,
                        }],
                    },
                    options: {
                        animation: false,
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false }, tooltip: { enabled: true } },
                        scales: {
                            x: { display: false },
                            y: { min: 1, max: 5, ticks: { stepSize: 1 } },
                        },
                    },
                });
                canvas.dataset.rendered = '1';
            })
            .catch(err => console.warn('Location timeline fetch failed:', err));
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
            // Bezpieczne sprawdzanie czy komentarz jest "cudzy" i jesteśmy zalogowani
            const showReportIcon = latest_comment.id && !latest_comment.is_mine && isUserAuthenticated;

            commentHtml = `
        <div class="mt-2 mb-2 p-2 bg-light border-start border-3 border-primary rounded-end text-start position-relative pe-4">
            <div class="d-flex justify-content-between small text-muted mb-1">
                <strong>${escapeHtml(latest_comment.username)}</strong>
                <span>${latest_comment.emotional_value ? latest_comment.emotional_value + '/5' : ''}</span>
            </div>
            <p class="mb-0 small fst-italic text-dark" style="line-height: 1.2;">
                "${escapeHtml(latest_comment.content)}"
            </p>
            ${showReportIcon ? `
            <button class="btn btn-sm btn-link text-danger position-absolute top-50 end-0 translate-middle-y p-1 btn-report-comment" data-comment-id="${latest_comment.id}" title="Zgłoś komentarz">
                <i class="bi bi-exclamation-circle-fill fs-5"></i>
            </button>` : ''}
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
      <div class="location-popup" style="min-width: 240px;">
        <h6 class="mb-2 fw-bold">${escapeHtml(name)}</h6>

        <div class="emotion-rating mb-1">
          ${avg_emotional_value ? stars : ''}
          <span class="ms-2 text-muted fw-bold">${avg_emotional_value ? avg_emotional_value.toFixed(1) : 'Brak ocen'}</span>
        </div>

        <p class="text-muted small mb-2">
            ${ratingText} &bull; ${commentsText}
        </p>

        <div class="mb-2" style="height: 70px;">
            <canvas class="location-timeline" data-location-id="${id}"></canvas>
        </div>

        ${commentHtml}

        <div class="d-flex gap-2 mt-1">
            <a href="${detailsUrl}" class="btn btn-sm btn-primary flex-grow-1">Zobacz szczegóły</a>
            ${isUserAuthenticated ? `<button class="btn btn-sm btn-outline-danger btn-report-location" data-location-id="${id}" title="Zgłoś lokalizację"><i class="bi bi-flag"></i> Zgłoś</button>` : ''}
        </div>
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

    async function handleMapClick(e) {
        const { lat, lng } = e.latlng;
        selectedCoordinates = { latitude: lat, longitude: lng };
        document.getElementById('coordinatesDisplay').textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;

        // Pokaż okienko od razu, by aplikacja wydawała się responsywna
        addEmotionModal.show();

        // Czekaj na odpowiedź z serwera (szukanie we WSZYSTKICH punktach bazy)
        await checkProximityViaAPI(lat, lng);
    }

    async function checkProximityViaAPI(lat, lng) {
        const proximityAlert = document.getElementById('proximityAlert');
        const proximityText = document.getElementById('proximityText');
        const proximityChoices = document.getElementById('proximityChoices');
        const locationNameContainer = document.getElementById('locationNameContainer');
        const choiceExisting = document.getElementById('choiceExisting');
        const choiceNew = document.getElementById('choiceNew');

        proximityText.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Szukanie punktów w pobliżu...';
        proximityAlert.classList.remove('d-none', 'alert-warning', 'alert-info');
        proximityAlert.classList.add('alert-secondary');
        proximityChoices.classList.add('d-none');

        let allCandidates = [];

        // 1. Zbieramy punkty, które aktualnie WIDAĆ na mapie
        currentLocationsData.forEach(loc => {
            allCandidates.push({
                id: loc.id,
                name: loc.name,
                lat: loc.coordinates.latitude,
                lon: loc.coordinates.longitude
            });
        });

        // 2. Pobieramy ukryte punkty z API (bazy danych)
        try {
            const response = await fetch(`/api/locations/nearby/?lat=${lat}&lon=${lng}&radius=${proximityRadius}`);
            if (response.ok) {
                const hiddenPoints = await response.json();
                if (Array.isArray(hiddenPoints)) {
                    hiddenPoints.forEach(hp => {
                        // Unikamy dodawania punktu podwójnie (jeśli już jest na ekranie)
                        if (!allCandidates.find(c => c.id === hp.id)) {
                            allCandidates.push(hp);
                        }
                    });
                }
            }
        } catch (error) {
            console.error("Błąd sieci przy szukaniu ukrytych lokalizacji", error);
        }

        // 3. Obliczamy DOKŁADNĄ odległość w metrach dla WSZYSTKICH punktów
        let minDistance = Infinity;
        closestLocationData = null;

        allCandidates.forEach(loc => {
            // Leaflet świetnie mierzy metry!
            const dist = map.distance([lat, lng], [loc.lat, loc.lon]);
            if (dist < proximityRadius && dist < minDistance) {
                minDistance = dist;
                closestLocationData = loc;
                closestLocationData.distance = dist; // Zapisujemy metry, żeby nie było NaN
            }
        });

        // 4. Pokazujemy wynik użytkownikowi
        // 4. Pokazujemy wynik użytkownikowi
        if (closestLocationData) {
            // SPRAWDZAMY CZY PUNKT JEST WIDOCZNY NA EKRANIE
            const isVisibleOnMap = currentLocationsData.some(loc => loc.id === closestLocationData.id);

            if (isVisibleOnMap) {
                proximityText.innerHTML = `W pobliżu wykryto: <strong>"${closestLocationData.name}"</strong> (${Math.round(closestLocationData.distance)}m stąd).`;
            } else {
                proximityText.innerHTML = `W pobliżu wykryto ukryty punkt: <strong>"${closestLocationData.name}"</strong> (${Math.round(closestLocationData.distance)}m stąd).`;
            }

            proximityAlert.classList.remove('alert-secondary', 'alert-warning');
            proximityAlert.classList.add('alert-info');
            proximityChoices.classList.remove('d-none');

            choiceExisting.checked = true;
            locationNameContainer.classList.add('d-none');

            choiceExisting.onchange = () => locationNameContainer.classList.add('d-none');
            choiceNew.onchange = () => locationNameContainer.classList.remove('d-none');

        } else {
            proximityText.textContent = 'Utworzysz nową lokalizację w tym miejscu.';
            proximityAlert.classList.remove('alert-secondary', 'alert-info');
            proximityAlert.classList.add('alert-warning');
            proximityChoices.classList.add('d-none');

            choiceNew.checked = true;
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
        const commentInput = document.getElementById('emotionComment');
        const choiceNew = document.getElementById('choiceNew');

        const isNewLocation = choiceNew && choiceNew.checked;

        if (!emotionalValue) {
            showEmotionError('Musisz wybrać ocenę (kliknij na gwiazdki).');
            return;
        }

        if (isNewLocation || !closestLocationData) {
            if (!locationNameInput.value.trim()) {
                showEmotionError('Musisz podać nazwę dla nowej lokalizacji.');
                return;
            }
        }

        hideEmotionErrors();
        const submitBtn = document.getElementById('submitEmotion');
        const submitText = document.getElementById('submitText');
        const submitSpinner = document.getElementById('submitSpinner');

        submitBtn.disabled = true;
        submitText.classList.add('d-none');
        submitSpinner.classList.remove('d-none');

        let locationData = {};
        if (isNewLocation || !closestLocationData) {
            // ZUPEŁNIE NOWE MIEJSCE: Wysyłamy wymyśloną nazwę i kliknięte współrzędne
            locationData = {
                name: locationNameInput.value.trim(),
                coordinates: { latitude: selectedCoordinates.latitude, longitude: selectedCoordinates.longitude }
            };
        } else {
            // PRZYPIĘCIE DO STAREGO (Ukrytego):
            // Wysyłamy ID oraz DOKŁADNE współrzędne istniejącego punktu z bazy (a nie z myszki)
            locationData = {
                id: closestLocationData.id,
                coordinates: {
                    latitude: closestLocationData.lat,
                    longitude: closestLocationData.lon
                }
            };
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
        document.getElementById('proximityAlert').classList.add('d-none');
        document.getElementById('proximityChoices').classList.add('d-none');
        document.getElementById('choiceExisting').checked = true;
        closestLocationData = null;
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

    // === NOWE FUNKCJE HEATMAPY ===

    function initTimeFilterToggle() {
        const toggle = document.getElementById('timeFilterToggle');
        const panel = document.getElementById('time-filter');
        if (!toggle || !panel) return;

        const stored = localStorage.getItem('cf:timeFilterVisible');
        const visible = stored === null ? true : stored === 'true';
        toggle.checked = visible;
        panel.classList.toggle('d-none', !visible);
        if (!visible) disableTimeFilter();

        toggle.addEventListener('change', (e) => {
            const show = e.target.checked;
            panel.classList.toggle('d-none', !show);
            localStorage.setItem('cf:timeFilterVisible', String(show));
            if (show) {
                loadTimeHistogram();
            } else {
                disableTimeFilter();
                loadVisibleLocations(true);
            }
        });
    }

    function disableTimeFilter() {
        if (timeFilter.playing) stopAnimation();
        timeFilter.from = null;
        timeFilter.to = null;
        timeFilter.histogramMode = 'overview';
    }

    function isTimeFilterPanelHidden() {
        const panel = document.getElementById('time-filter');
        return panel && panel.classList.contains('d-none');
    }

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
            if (map.hasLayer(markerClusterGroup)) map.removeLayer(markerClusterGroup);

            if (!map.hasLayer(heatLayerBad)) map.addLayer(heatLayerBad);
            if (!map.hasLayer(heatLayerNeutral)) map.addLayer(heatLayerNeutral);
            if (!map.hasLayer(heatLayerGood)) map.addLayer(heatLayerGood);

            updateHeatmapData(currentLocationsData);
        } else {
            if (map.hasLayer(heatLayerBad)) map.removeLayer(heatLayerBad);
            if (map.hasLayer(heatLayerNeutral)) map.removeLayer(heatLayerNeutral);
            if (map.hasLayer(heatLayerGood)) map.removeLayer(heatLayerGood);

            if (!map.hasLayer(markerClusterGroup)) {
                map.addLayer(markerClusterGroup);
            }
            displayLocations(currentLocationsData);
        }
    }

    function updateHeatmapData(locations) {
        if (!heatLayerBad) return;

        const badPoints = [];
        const neutralPoints = [];
        const goodPoints = [];

        locations.forEach(loc => {
            const val = loc.avg_emotional_value || 0;
            const point = [
                loc.coordinates.latitude,
                loc.coordinates.longitude,
                0.8
            ];

            if (val < 2.5) {
                badPoints.push(point);
            } else if (val >= 2.5 && val < 3.8) {
                neutralPoints.push(point);
            } else {
                goodPoints.push(point);
            }
        });

        heatLayerBad.setLatLngs(badPoints);
        heatLayerNeutral.setLatLngs(neutralPoints);
        heatLayerGood.setLatLngs(goodPoints);
    }

    // === FILTR CZASOWY ===

    function initTimeFilter() {
        if (typeof noUiSlider === 'undefined' || typeof Chart === 'undefined') {
            console.warn('Time filter: noUiSlider or Chart.js not loaded');
            return;
        }

        const sliderEl = document.getElementById('timeRangeSlider');
        const canvas = document.getElementById('timeHistogram');
        const playBtn = document.getElementById('playAnimation');
        const presetsEl = document.getElementById('timePresets');

        if (!sliderEl || !canvas || !playBtn || !presetsEl) return;

        const now = Date.now();
        const yearAgo = now - 365 * 24 * 3600 * 1000;

        timeFilter.slider = noUiSlider.create(sliderEl, {
            start: [yearAgo, now],
            connect: true,
            range: { min: yearAgo, max: now },
            step: 60 * 60 * 1000,
            behaviour: 'drag-tap',
            tooltips: false,
        });

        timeFilter.slider.on('update', (values) => {
            timeFilter.from = new Date(parseFloat(values[0]));
            timeFilter.to = new Date(parseFloat(values[1]));
            updateTimeRangeLabel();
            applyRangeOverlay();
        });

        timeFilter.slider.on('start', () => {
            if (timeFilter.histogramMode === 'zoomed' && timeFilter.fullBuckets) {
                timeFilter.histogramMode = 'overview';
                runZoomTransition('out', () => renderChartOnly(timeFilter.fullBuckets));
            }
        });

        timeFilter.slider.on('set', () => {
            scheduleTimeFilterRefresh();
            clearActivePreset();
            if (timeFilter.from && timeFilter.to) {
                timeFilter.histogramMode = 'zoomed';
                fetchHistogramZoomed();
            } else {
                timeFilter.histogramMode = 'overview';
                if (timeFilter.fullBuckets) renderChartOnly(timeFilter.fullBuckets);
            }
        });

        timeFilter.chart = new Chart(canvas, {
            type: 'bar',
            data: { labels: [], datasets: [{ data: [], backgroundColor: [], borderWidth: 0 }] },
            options: {
                animation: false,
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: true,
                        displayColors: false,
                        callbacks: {
                            title: (items) => formatBucketRange(items[0].label),
                            label: (item) => {
                                const idx = item.dataIndex;
                                const ds = item.dataset.data;
                                const avg = timeFilter.bucketAvgs ? timeFilter.bucketAvgs[idx] : null;
                                const count = ds[idx];
                                const lines = [`Liczba ocen: ${count}`];
                                if (avg != null) lines.push(`Średnia emocja: ${Number(avg).toFixed(2)} / 5`);
                                return lines;
                            },
                        },
                    },
                },
                scales: {
                    x: { display: false },
                    y: { display: false, beginAtZero: true },
                },
                layout: { padding: 0 },
            },
        });

        presetsEl.addEventListener('click', (e) => {
            const btn = e.target.closest('.tf-preset');
            if (!btn) return;
            applyTimePreset(btn.dataset.preset, btn);
        });

        playBtn.addEventListener('click', toggleAnimation);
// NOWOŚĆ: Obsługa kalendarza "Wehikuł czasu"
        const exactPicker = document.getElementById('exactTimePicker');
        if (exactPicker) {
            exactPicker.addEventListener('change', (e) => {
                const pickedDate = new Date(e.target.value);
                if (isNaN(pickedDate.getTime())) return;

                // Tworzymy wąskie okno czasowe (np. +/- 12 godzin wokół wybranej daty)
                // aby wyłapać nastroje z tamtego konkretnego momentu w historii.
                const centerMs = pickedDate.getTime();
                const halfWindow = 12 * 3600 * 1000;

                // Przestawiamy suwak, co automatycznie odświeży mapę i wczyta starą historię!
                timeFilter.slider.set([centerMs - halfWindow, centerMs + halfWindow]);
                clearActivePreset();
            });
        }
        map.on('moveend', debounceTimeHistogram);
        setTimeout(loadTimeHistogram, 400);
    }

    function debounceTimeHistogram() {
        clearTimeout(timeFilter.debounceTimer);
        timeFilter.debounceTimer = setTimeout(loadTimeHistogram, CONFIG.DEBOUNCE_DELAY);
    }

    function scheduleTimeFilterRefresh() {
        clearTimeout(timeFilter.debounceTimer);
        timeFilter.debounceTimer = setTimeout(() => loadVisibleLocations(true), CONFIG.DEBOUNCE_DELAY);
    }

    function loadTimeHistogram() {
        if (isTimeFilterPanelHidden()) return;
        const bbox = currentBboxString();
        const bucket = pickBucketForCurrentRange();
        timeFilter.bucket = bucket;
        updateBucketGranularityLabel(bucket);

        let url = `/api/emotion-points/histogram/?bbox=${bbox}&bucket=${bucket}`;
        if (activeFilters.length > 0) {
            url += `&emotional_value=${activeFilters.join(',')}`;
        }

        fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
            .then(buckets => {
                timeFilter.fullBuckets = buckets;
                renderHistogram(buckets);
                if (timeFilter.histogramMode === 'zoomed' && timeFilter.from && timeFilter.to) {
                    fetchHistogramZoomed();
                }
            })
            .catch(err => console.error('Time histogram fetch failed:', err));
    }

    function fetchHistogramZoomed() {
        if (!timeFilter.from || !timeFilter.to) return;
        const bbox = currentBboxString();
        const bucket = pickBucketForCurrentRange();
        timeFilter.bucket = bucket;
        updateBucketGranularityLabel(bucket);

        let url = `/api/emotion-points/histogram/?bbox=${bbox}&bucket=${bucket}`;
        url += `&created_after=${encodeURIComponent(timeFilter.from.toISOString())}`;
        url += `&created_before=${encodeURIComponent(timeFilter.to.toISOString())}`;
        if (activeFilters.length > 0) {
            url += `&emotional_value=${activeFilters.join(',')}`;
        }

        const timeline = document.querySelector('.tf-timeline');
        if (timeline) timeline.classList.add('tf-zooming-in');

        fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
            .then(buckets => {
                renderChartOnly(buckets);
                if (timeline) requestAnimationFrame(() => timeline.classList.remove('tf-zooming-in'));
            })
            .catch(err => {
                console.error('Zoomed histogram fetch failed:', err);
                if (timeline) timeline.classList.remove('tf-zooming-in');
            });
    }

    function currentBboxString() {
        const bounds = map.getBounds();
        const sw = bounds.getSouthWest().wrap();
        const ne = bounds.getNorthEast().wrap();
        return [sw.lng, sw.lat, ne.lng, ne.lat].join(',');
    }

    function runZoomTransition(direction, swapFn) {
        const timeline = document.querySelector('.tf-timeline');
        if (!timeline) { swapFn(); return; }
        const cls = direction === 'in' ? 'tf-zooming-in' : 'tf-zooming-out';
        timeline.classList.add(cls);
        setTimeout(() => {
            swapFn();
            requestAnimationFrame(() => timeline.classList.remove(cls));
        }, 140);
    }

    function renderChartOnly(buckets) {
        if (!timeFilter.chart) return;
        if (!buckets || buckets.length === 0) {
            timeFilter.chart.data.labels = [];
            timeFilter.chart.data.datasets[0].data = [];
            timeFilter.chart.data.datasets[0].backgroundColor = [];
            timeFilter.bucketAvgs = [];
            timeFilter.chart.update('none');
            updateAxisTicks();
            applyRangeOverlay();
            return;
        }
        timeFilter.chart.data.labels = buckets.map(b => b.bucket);
        timeFilter.chart.data.datasets[0].data = buckets.map(b => b.count);
        timeFilter.bucketAvgs = buckets.map(b => b.avg_value);
        timeFilter.chart.data.datasets[0].backgroundColor = buckets.map(b => avgValueToColor(b.avg_value));
        timeFilter.chart.update('none');
        updateAxisTicks();
        applyRangeOverlay();
    }

    function pickBucketForCurrentRange() {
        const from = timeFilter.from || timeFilter.dataMin;
        const to = timeFilter.to || timeFilter.dataMax;
        if (!from || !to) return 'day';
        const span = to - from;
        const day = 24 * 3600 * 1000;
        if (span < 2 * day) return 'hour';
        if (span < 60 * day) return 'day';
        if (span < 365 * day) return 'week';
        return 'month';
    }

    function renderHistogram(buckets) {
        const playBtn = document.getElementById('playAnimation');

        if (!buckets || buckets.length === 0) {
            timeFilter.chart.data.labels = [];
            timeFilter.chart.data.datasets[0].data = [];
            timeFilter.chart.data.datasets[0].backgroundColor = [];
            timeFilter.bucketAvgs = [];
            timeFilter.chart.update();
            timeFilter.ready = false;
            if (playBtn) playBtn.disabled = true;
            return;
        }

        const labels = buckets.map(b => b.bucket);
        const counts = buckets.map(b => b.count);
        const colors = buckets.map(b => avgValueToColor(b.avg_value));

        timeFilter.chart.data.labels = labels;
        timeFilter.chart.data.datasets[0].data = counts;
        timeFilter.chart.data.datasets[0].backgroundColor = colors;
        timeFilter.bucketAvgs = buckets.map(b => b.avg_value);
        timeFilter.chart.update();

        const tsMin = new Date(buckets[0].bucket).getTime();
        const tsMaxRaw = new Date(buckets[buckets.length - 1].bucket).getTime();
        const tsMax = tsMaxRaw > tsMin ? tsMaxRaw : tsMin + 24 * 3600 * 1000;

        timeFilter.dataMin = new Date(tsMin);
        timeFilter.dataMax = new Date(tsMax);
        updateAxisTicks();

        const wasAllRange = !timeFilter.from && !timeFilter.to;
        const oldFrom = timeFilter.from ? timeFilter.from.getTime() : tsMin;
        const oldTo = timeFilter.to ? timeFilter.to.getTime() : tsMax;
        timeFilter.slider.updateOptions({ range: { min: tsMin, max: tsMax } }, false);

        if (!timeFilter.ready) {
            timeFilter.slider.set([tsMin, tsMax], false);
            timeFilter.from = null;
            timeFilter.to = null;
            updateTimeRangeLabel(tsMin, tsMax);
        } else {
            timeFilter.slider.set([
                Math.max(tsMin, oldFrom),
                Math.min(tsMax, oldTo),
            ], false);
            if (wasAllRange) {
                timeFilter.from = null;
                timeFilter.to = null;
                updateTimeRangeLabel(tsMin, tsMax);
            }
        }

        timeFilter.ready = true;
        if (playBtn) playBtn.disabled = false;
        applyRangeOverlay();
    }

    const BUCKET_LABELS_PL = {
        hour: '1 godzina',
        day: '1 dzień',
        week: '1 tydzień',
        month: '1 miesiąc',
    };

    const MONTH_PL_SHORT = ['sty', 'lut', 'mar', 'kwi', 'maj', 'cze', 'lip', 'sie', 'wrz', 'paź', 'lis', 'gru'];

    function pluralizePL(n, singular, few, many) {
        if (n === 1) return singular;
        const lastDigit = n % 10;
        const lastTwo = n % 100;
        if (lastDigit >= 2 && lastDigit <= 4 && (lastTwo < 12 || lastTwo > 14)) return few;
        return many;
    }

    function hexToRgba(hex, alpha) {
        const h = hex.replace('#', '');
        const r = parseInt(h.substring(0, 2), 16);
        const g = parseInt(h.substring(2, 4), 16);
        const b = parseInt(h.substring(4, 6), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    function formatRangePL(from, to) {
        const day = d => `${d.getDate()} ${MONTH_PL_SHORT[d.getMonth()]}`;
        const dayYear = d => `${day(d)} ${d.getFullYear()}`;
        const hour = d => `${pad(d.getHours())}:${pad(d.getMinutes())}`;

        if (timeFilter.bucket === 'hour') {
            const sameDay = from.toDateString() === to.toDateString();
            if (sameDay) return `${day(from)} ${from.getFullYear()}, ${hour(from)} – ${hour(to)}`;
            return `${day(from)} ${hour(from)} – ${dayYear(to)} ${hour(to)}`;
        }
        if (from.getFullYear() === to.getFullYear()) {
            if (from.getMonth() === to.getMonth() && from.getDate() !== to.getDate()) {
                return `${from.getDate()} – ${day(to)} ${to.getFullYear()}`;
            }
            return `${day(from)} – ${day(to)} ${to.getFullYear()}`;
        }
        return `${dayYear(from)} – ${dayYear(to)}`;
    }

    function formatTickPL(d) {
        if (timeFilter.bucket === 'hour') {
            return `${d.getDate()} ${MONTH_PL_SHORT[d.getMonth()]} ${d.getFullYear()}, ${pad(d.getHours())}:00`;
        }
        if (timeFilter.bucket === 'month') {
            return `${MONTH_PL_SHORT[d.getMonth()]} ${d.getFullYear()}`;
        }
        return `${d.getDate()} ${MONTH_PL_SHORT[d.getMonth()]} ${d.getFullYear()}`;
    }

    function updateBucketGranularityLabel(bucket) {
        const el = document.getElementById('bucketGranularityLabel');
        if (!el) return;
        el.textContent = `Każdy słupek = ${BUCKET_LABELS_PL[bucket] || bucket}`;
    }

    function formatBucketTick(isoLabel) {
        if (!isoLabel) return '';
        const d = new Date(isoLabel);
        if (isNaN(d.getTime())) return isoLabel;
        if (timeFilter.bucket === 'hour') {
            return `${pad(d.getDate())}.${pad(d.getMonth() + 1)} ${pad(d.getHours())}:00`;
        }
        if (timeFilter.bucket === 'month') {
            return `${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
        }
        return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}`;
    }

    function formatBucketRange(isoLabel) {
        const start = new Date(isoLabel);
        if (isNaN(start.getTime())) return isoLabel;
        const end = new Date(start);
        if (timeFilter.bucket === 'hour') {
            end.setHours(end.getHours() + 1);
        } else if (timeFilter.bucket === 'day') {
            end.setDate(end.getDate() + 1);
        } else if (timeFilter.bucket === 'week') {
            end.setDate(end.getDate() + 7);
        } else if (timeFilter.bucket === 'month') {
            end.setMonth(end.getMonth() + 1);
        }
        return formatRangePL(start, end);
    }

    function avgValueToColor(avg) {
        if (avg == null) return '#bdc3c7';
        if (avg < 1.5) return CONFIG.EMOTION_COLORS[1.0];
        if (avg < 2.5) return CONFIG.EMOTION_COLORS[2.0];
        if (avg < 3.5) return CONFIG.EMOTION_COLORS[3.0];
        if (avg < 4.5) return CONFIG.EMOTION_COLORS[4.0];
        return CONFIG.EMOTION_COLORS[5.0];
    }

    function applyRangeOverlay() {
        if (!timeFilter.chart) return;
        const labels = timeFilter.chart.data.labels;
        if (!labels || !labels.length) {
            updateBucketTotalCount(0);
            return;
        }

        const fromTs = timeFilter.from ? timeFilter.from.getTime() : null;
        const toTs = timeFilter.to ? timeFilter.to.getTime() : null;
        const noFilter = fromTs == null && toTs == null;
        const isZoomed = timeFilter.histogramMode === 'zoomed';

        const counts = timeFilter.chart.data.datasets[0].data;
        const colors = [];
        let totalInRange = 0;

        for (let i = 0; i < labels.length; i++) {
            const ts = new Date(labels[i]).getTime();
            const inRange = noFilter || isZoomed || (ts >= fromTs && ts <= toTs);
            const baseHex = avgValueToColor(timeFilter.bucketAvgs[i]);
            colors.push(inRange ? baseHex : hexToRgba(baseHex, 0.18));
            if (inRange) totalInRange += counts[i] || 0;
        }

        timeFilter.chart.data.datasets[0].backgroundColor = colors;
        timeFilter.chart.update('none');
        updateBucketTotalCount(totalInRange);
    }

    function updateBucketTotalCount(n) {
        const el = document.getElementById('bucketTotalCount');
        if (!el) return;
        const word = pluralizePL(n, 'ocena', 'oceny', 'ocen');
        el.textContent = `${n} ${word} w wybranym oknie`;
    }

    function updateAxisTicks() {
        const axis = document.getElementById('tfAxis');
        if (!axis) return;
        const spans = axis.querySelectorAll('span');
        if (spans.length < 3) return;

        const labels = timeFilter.chart && timeFilter.chart.data.labels;
        if (!labels || labels.length === 0) {
            spans[0].textContent = '';
            spans[1].textContent = '';
            spans[2].textContent = '';
            return;
        }

        const first = new Date(labels[0]);
        const last = new Date(labels[labels.length - 1]);
        const mid = new Date(first.getTime() + (last.getTime() - first.getTime()) / 2);
        spans[0].textContent = formatTickPL(first);
        spans[1].textContent = formatTickPL(mid);
        spans[2].textContent = formatTickPL(last);
    }

    function updateTimeRangeLabel(fromTs, toTs) {
        const label = document.getElementById('timeRangeLabel');
        if (!label) return;
        const from = fromTs != null ? new Date(fromTs) : timeFilter.from;
        const to = toTs != null ? new Date(toTs) : timeFilter.to;
        if (!from || !to) {
            label.textContent = '—';
            return;
        }
        label.textContent = formatRangePL(from, to);
    }

    function formatDate(d) {
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }

    function pad(n) { return n < 10 ? `0${n}` : `${n}`; }

    function applyTimePreset(preset, btnEl) {
        if (!timeFilter.dataMax) return;

        const max = timeFilter.dataMax.getTime();
        const min = timeFilter.dataMin.getTime();
        let from = min;
        let to = max;

        if (preset === 'all') {
            timeFilter.slider.set([min, max], false);
            timeFilter.from = null;
            timeFilter.to = null;
        } else {
            const day = 24 * 3600 * 1000;
            const spans = { day: 1, week: 7, month: 30, year: 365 };
            const days = spans[preset] || 7;
            from = Math.max(min, max - days * day);
            timeFilter.slider.set([from, max], false);
            timeFilter.from = new Date(from);
            timeFilter.to = new Date(max);
        }

        markActivePreset(btnEl);
        updateTimeRangeLabel(from, to);
        applyRangeOverlay();
        scheduleTimeFilterRefresh();

        if (preset === 'all') {
            timeFilter.histogramMode = 'overview';
            if (timeFilter.fullBuckets) {
                runZoomTransition('out', () => renderChartOnly(timeFilter.fullBuckets));
            } else {
                loadTimeHistogram();
            }
        } else {
            timeFilter.histogramMode = 'zoomed';
            fetchHistogramZoomed();
        }
    }

    function markActivePreset(activeBtn) {
        const presetsEl = document.getElementById('timePresets');
        if (!presetsEl) return;
        presetsEl.querySelectorAll('.tf-preset').forEach(b => b.classList.remove('active'));
        if (activeBtn) activeBtn.classList.add('active');
    }

    function clearActivePreset() {
        markActivePreset(null);
    }

    function toggleAnimation() {
        if (timeFilter.playing) {
            stopAnimation();
        } else {
            startAnimation();
        }
    }

    function startAnimation() {
        if (!timeFilter.ready || !timeFilter.dataMin || !timeFilter.dataMax) return;

        const hasRange = timeFilter.from && timeFilter.to;
        const min = hasRange ? timeFilter.from.getTime() : timeFilter.dataMin.getTime();
        const max = hasRange ? timeFilter.to.getTime() : timeFilter.dataMax.getTime();

        timeFilter.savedRange = {
            from: timeFilter.from ? timeFilter.from.getTime() : null,
            to: timeFilter.to ? timeFilter.to.getTime() : null,
        };
        const totalSpan = max - min;
        if (totalSpan <= 0) return;

        const windowSize = Math.max(60 * 60 * 1000, totalSpan / 15);
        const step = Math.max(60 * 1000, totalSpan / 60);
        const tickMs = 200;
        let cursor = min;

        timeFilter.playing = true;
        document.getElementById('playIcon').textContent = '⏸';
        document.getElementById('playLabel').textContent = 'Stop';
        document.getElementById('playAnimation').classList.add('playing');

        timeFilter.playInterval = setInterval(() => {
            const from = cursor;
            const to = Math.min(max, cursor + windowSize);
            timeFilter.slider.set([from, to], false);
            timeFilter.from = new Date(from);
            timeFilter.to = new Date(to);
            updateTimeRangeLabel(from, to);
            loadVisibleLocations(true);

            cursor += step;
            if (cursor + windowSize > max) {
                stopAnimation();
            }
        }, tickMs);
    }

    function stopAnimation() {
        if (timeFilter.playInterval) clearInterval(timeFilter.playInterval);
        timeFilter.playInterval = null;
        timeFilter.playing = false;
        document.getElementById('playIcon').textContent = '▶';
        document.getElementById('playLabel').textContent = 'Animuj';
        document.getElementById('playAnimation').classList.remove('playing');

        const saved = timeFilter.savedRange;
        if (saved) {
            const dataMin = timeFilter.dataMin.getTime();
            const dataMax = timeFilter.dataMax.getTime();
            const from = saved.from != null ? saved.from : dataMin;
            const to = saved.to != null ? saved.to : dataMax;
            timeFilter.slider.set([from, to], false);
            timeFilter.from = saved.from != null ? new Date(saved.from) : null;
            timeFilter.to = saved.to != null ? new Date(saved.to) : null;
            updateTimeRangeLabel(from, to);
            loadVisibleLocations(true);
            timeFilter.savedRange = null;
        }
    }

    function initReportModal() {
        if (document.getElementById('reportModal')) return;
        const modalHtml = `
        <div class="modal fade" id="reportModal" tabindex="-1" aria-hidden="true">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="reportModalTitle">Zgłoś naruszenie</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Zamknij"></button>
              </div>
              <div class="modal-body">
                <div id="reportErrors" class="alert alert-danger d-none"></div>
                <input type="hidden" id="reportTargetType">
                <input type="hidden" id="reportTargetId">
                <div class="mb-3">
                  <label class="form-label">Powód zgłoszenia</label>
                  <select class="form-select" id="reportReason">
                    <option value="spam">Spam lub reklama</option>
                    <option value="hate_speech">Mowa nienawiści / Nękanie</option>
                    <option value="inappropriate">Nieodpowiednia treść</option>
                    <option value="fake_location">Fałszywa lokalizacja</option>
                    <option value="other">Inne</option>
                  </select>
                </div>
                <div class="mb-3">
                  <label class="form-label">Dodatkowy opis</label>
                  <textarea class="form-control" id="reportDescription" rows="3"></textarea>
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Anuluj</button>
                <button type="button" class="btn btn-danger" id="submitReportBtn">Wyślij zgłoszenie</button>
              </div>
            </div>
          </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        document.getElementById('submitReportBtn').addEventListener('click', submitReport);
    }

    function openReportModal(targetType, targetId) {
        if (!isUserAuthenticated) {
            alert("Musisz być zalogowany, aby zgłosić zawartość.");
            return;
        }
        document.getElementById('reportTargetType').value = targetType;
        document.getElementById('reportTargetId').value = targetId;
        document.getElementById('reportReason').value = 'spam';
        document.getElementById('reportDescription').value = '';
        document.getElementById('reportErrors').classList.add('d-none');

        document.getElementById('reportModalTitle').textContent = targetType === 'comment' ? 'Zgłoś komentarz' : 'Zgłoś lokalizację';

        const modal = new bootstrap.Modal(document.getElementById('reportModal'));
        modal.show();
    }

    async function submitReport() {
        const targetType = document.getElementById('reportTargetType').value;
        const targetId = document.getElementById('reportTargetId').value;
        const reason = document.getElementById('reportReason').value;
        const desc = document.getElementById('reportDescription').value;
        const btn = document.getElementById('submitReportBtn');
        const errDiv = document.getElementById('reportErrors');

        errDiv.classList.add('d-none');
        btn.disabled = true;

        const payload = {
            reason: reason,
            description: desc
        };

        if (targetType === 'location') payload.location = targetId;
        if (targetType === 'comment') payload.comment = targetId;

        try {
            const response = await fetch('/api/reports/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error('Wystąpił błąd podczas wysyłania zgłoszenia.');

            const modalEl = document.getElementById('reportModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal.hide();

            const toastElement = document.getElementById('successToast');
            if (toastElement) {
                document.getElementById('successMessage').textContent = 'Zgłoszenie zostało wysłane do moderacji.';
                new bootstrap.Toast(toastElement).show();
            } else {
                alert('Zgłoszenie zostało wysłane do moderacji.');
            }
        } catch (e) {
            errDiv.textContent = e.message;
            errDiv.classList.remove('d-none');
        } finally {
            btn.disabled = false;
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();