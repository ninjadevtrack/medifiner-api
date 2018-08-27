from datetime import timedelta


def daterange(start, stop, step=timedelta(days=1), inclusive=False):
    # inclusive=False to behave like range by default
    if step.days > 0:
        while start < stop:
            yield start
            start = start + step
    elif step.days < 0:
        while start > stop:
            yield start
            start = start + step
    if inclusive and start == stop:
        yield start


def percentage(part, whole):
    return 100 * float(part) / float(whole)


def get_overall(supply_levels):
    low = 0
    medium = 0
    high = 0
    for level in supply_levels:
        if level == 1:
            low += 1
        elif level == 2 or level == 3:
            medium += 1
        elif level == 4:
            high += 1
    total = sum([low, medium, high])
    if total:
        return {
            'low': percentage(low, total),
            'medium': percentage(medium, total),
            'high': percentage(high, total),
        }
    return {
        'low': 0.0,
        'medium': 0.0,
        'high': 0.0,
    }
