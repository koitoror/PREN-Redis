# from dateutil import parser
# from dateutil.relativedelta import relativedelta
# from graphql import GraphQLError


# def filter_events_by_date_range(events, start_date, end_date):
#     """
#     Return events that  fall in the date range
#     """
#     if not (start_date and end_date):
#         return events
#     start_date, end_date = format_range_dates(start_date, end_date)
#     filtered_events = []
#     for event in events:
#         event_start_date = parser.parse(event.start_date)
#         event_end_date = parser.parse(event.end_date)
#         if event_start_date >= start_date and event_end_date <= end_date:
#             filtered_events.append(event)
#     return filtered_events


# def format_range_dates(start_date, end_date):
#     """
#     Convert dates to date objects and add one day to end_date
#     Data from front-end doesn't include time
#     """
#     start_date = parser.parse(start_date).strftime('%Y-%m-%d')
#     end_date = parser.parse(end_date).strftime('%Y-%m-%d')
#     if start_date > end_date:
#         raise GraphQLError("Start date must be lower than end date")
#     start_date = parser.parse(start_date)
#     end_date = parser.parse(end_date) + relativedelta(days=1)
#     return(start_date, end_date)
