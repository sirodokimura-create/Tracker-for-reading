import calendar
from datetime import datetime

def get_month_name(month_num):
    months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
              'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    return months[month_num - 1]

def generate_calendar_html(year, month, reading_cache):



    month_name = get_month_name(month)
    _, total_days = calendar.monthrange(year, month)

    weeks_html = ''
    for block_start in range(1, total_days + 1, 7):
        block_end = min(block_start + 6, total_days)
        days_in_block = block_end - block_start + 1
        read_days = 0
        for day in range(block_start, block_end + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            if date_str in reading_cache:
                read_days += 1

        fill_percent = (read_days / days_in_block * 100) if days_in_block > 0 else 0
        week_label = f"{block_start} – {block_end}"

        week_html = f'''
        <div class="calendar-week">
            <div class="calendar-week-fill" style="height: {fill_percent:.1f}%;"></div>
            <div class="week-label">{week_label}</div>
        </div>
        '''
        weeks_html += week_html


    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    html = f'''
    <div class="calendar-nav">
        <button class="calendar-nav-prev" data-year="{prev_year}" data-month="{prev_month}">◀ {get_month_name(prev_month)}</button>
        <button class="calendar-nav-today" data-year="{datetime.now().year}" data-month="{datetime.now().month}">Сегодня</button>
        <span class="calendar-month-year">{month_name} {year}</span>
        <button class="calendar-nav-next" data-year="{next_year}" data-month="{next_month}">{get_month_name(next_month)} ▶</button>
    </div>
    <div class="calendar-weeks-vertical">
        {weeks_html}
    </div>
    '''
    return html