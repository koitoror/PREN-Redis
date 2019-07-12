from dateutil import parser
from datetime import datetime, timedelta
from graphql import GraphQLError
import pytz

utc = pytz.utc


def sort_events_by_date_range(events):
    """
    Return events that  fall in the date range
    """
    events.sort(
        key=lambda x: parser.parse(x.start_time).astimezone(utc),
        reverse=True)
    return events


def format_range_dates(start_date, end_date):
    """
    Convert dates to date objects and add one day to end_date
    Data from front-end doesn't include time
    """
    if start_date > end_date:
        raise GraphQLError("Start date must be lower than end date")

    start_date = datetime.strptime(start_date, '%b %d %Y')
    end_date = (datetime.strptime(end_date, '%b %d %Y') + timedelta(days=1))

    start_date = start_date.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')
    end_date = end_date.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')

    return (start_date, end_date)
