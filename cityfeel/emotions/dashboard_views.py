import json
import datetime
from django.shortcuts import render
from django.db.models import Count, Avg
from django.db.models.functions import TruncDate, ExtractIsoWeekDay, ExtractHour
from django.core.cache import cache  # DODANO IMPORT CACHE
from .models import EmotionPoint


def city_statistics_dashboard(request):
    LABELS = {1: 'Bardzo negatywne', 2: 'Negatywne', 3: 'Neutralne', 4: 'Pozytywne', 5: 'Bardzo pozytywne'}
    WEEKDAYS_PL = {1: 'poniedziałek', 2: 'wtorek', 3: 'środa', 4: 'czwartek', 5: 'piątek', 6: 'sobota', 7: 'niedziela'}

    curr_year, curr_week, _ = datetime.date.today().isocalendar()
    year_param = request.GET.get('year')
    week_param = request.GET.get('week_num')

    try:
        year = int(year_param) if year_param else curr_year
        week = int(week_param) if week_param else curr_week
    except ValueError:
        year, week = curr_year, curr_week

    start_of_week = datetime.datetime.strptime(f'{year}-W{week:02d}-1', "%G-W%V-%u").date()
    end_of_week = start_of_week + datetime.timedelta(days=6)
    week_display = f"{start_of_week.strftime('%d.%m')} - {end_of_week.strftime('%d.%m')}"

    # CACHOWANIE DOSTĘPNYCH DAT (Zmieniają się rzadko, trzymamy 1 godzinę)
    dates_cache_key = 'dashboard_available_dates'
    dates_data = cache.get(dates_cache_key)

    if not dates_data:
        years_in_db = EmotionPoint.objects.dates('created_at', 'year')
        available_years = sorted(list(set(d.year for d in years_in_db)))
        if not available_years: available_years = [curr_year]
        if curr_year not in available_years:
            available_years.append(curr_year)
            available_years.sort()

        dates_data = {'available_years': available_years}
        cache.set(dates_cache_key, dates_data, 60 * 60)  # Cache na 1 godzinę

    available_years = dates_data['available_years']

    available_weeks = []
    max_week = datetime.date(year, 12, 28).isocalendar()[1]
    for w in range(1, max_week + 1):
        w_start = datetime.datetime.strptime(f'{year}-W{w:02d}-1', "%G-W%V-%u").date()
        w_end = w_start + datetime.timedelta(days=6)
        label = f"Tydzień {w} ({w_start.strftime('%d.%m')} - {w_end.strftime('%d.%m')})"
        available_weeks.append({'num': w, 'label': label})

    # =========================================================
    # GŁÓWNY SYSTEM CACHOWANIA CIĘŻKICH ZAPYTAŃ BAZODANOWYCH
    # =========================================================
    cache_key = f'dashboard_stats_{year}_{week}'
    stats_data = cache.get(cache_key)

    if not stats_data:
        # JEŚLI NIE MA W CACHE -> MĘCZYMY BAZĘ DANYCH
        qs = EmotionPoint.objects.filter(created_at__iso_year=year, created_at__week=week)

        emotions_over_time = list(qs.annotate(date=TruncDate('created_at')).values('date', 'emotional_value').annotate(
            count=Count('id')).order_by('date'))
        for item in emotions_over_time: item['emotion'] = LABELS.get(item['emotional_value'], 'Nieznane')

        weekly_trends = list(
            qs.annotate(weekday=ExtractIsoWeekDay('created_at')).values('weekday', 'emotional_value').annotate(
                count=Count('id')))
        for item in weekly_trends: item['emotion'] = LABELS.get(item['emotional_value'], 'Nieznane')

        popular_locations = list(
            qs.values('location__id', 'location__name').annotate(count=Count('id')).order_by('-count')[:10])

        hourly_stats = list(
            qs.annotate(weekday=ExtractIsoWeekDay('created_at'), hour=ExtractHour('created_at')).values('weekday',
                                                                                                        'hour').annotate(
                count=Count('id'), avg_val=Avg('emotional_value')))

        saddest_info, happiest_info = None, None
        if hourly_stats:
            valid_stats = [s for s in hourly_stats if s['count'] >= 10]
            if not valid_stats:
                max_count = max(s['count'] for s in hourly_stats)
                valid_stats = [s for s in hourly_stats if s['count'] == max_count]

            saddest = min(valid_stats, key=lambda x: x['avg_val'])
            happiest = max(valid_stats, key=lambda x: x['avg_val'])

            saddest_info = {'day': WEEKDAYS_PL[saddest['weekday']], 'hour': saddest['hour'], 'count': saddest['count'],
                            'avg': round(saddest['avg_val'], 1)}
            happiest_info = {'day': WEEKDAYS_PL[happiest['weekday']], 'hour': happiest['hour'],
                             'count': happiest['count'], 'avg': round(happiest['avg_val'], 1)}

        # Zapisujemy wyliczone dane do cache
        stats_data = {
            'emotions_over_time_json': json.dumps(emotions_over_time, default=str),
            'weekly_trends_json': json.dumps(weekly_trends),
            'popular_locations_json': json.dumps(popular_locations),
            'saddest_info': saddest_info,
            'happiest_info': happiest_info,
        }
        # Zapisz w pamięci na 15 minut (900 sekund)
        cache.set(cache_key, stats_data, 900)

    # Budujemy ostateczny kontekst dla HTML
    context = {
        'year': year,
        'week': week,
        'week_display': week_display,
        'available_years': available_years,
        'available_weeks': available_weeks,
        **stats_data  # Rozpakowujemy dane z cache
    }

    return render(request, 'emotions/dashboard.html', context)