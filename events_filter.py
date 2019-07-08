from dateutil import parser
from dateutil.relativedelta import relativedelta
from graphql import GraphQLError
import pytz

utc = pytz.utc


def filter_events_by_date_range(events, start_date, end_date):
    """
    Return events that  fall in the date range
    """
    if not (start_date and end_date):
        return events
    start_date, end_date = format_range_dates(start_date, end_date)
    filtered_events = []
    for event in events:
        event_start_date = parser.parse(event.start_time).astimezone(utc)
        event_end_date = parser.parse(event.end_time).astimezone(utc)
        if event_start_date >= start_date and event_end_date <= end_date:
            filtered_events.append(event)
            filtered_events.sort(
                key=lambda x: parser.parse(x.start_time).astimezone(utc),
                reverse=True)
    return filtered_events


def format_range_dates(start_date, end_date):
    """
    Convert dates to date objects and add one day to end_date
    Data from front-end doesn't include time
    """

    if start_date > end_date:
        raise GraphQLError("Start date must be lower than end date")
    start_date = parser.parse(start_date).astimezone(utc)
    end_date = parser.parse(end_date).astimezone(utc) + relativedelta(days=1)
    return(start_date, end_date)
