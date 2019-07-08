import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType
from graphql import GraphQLError

from api.events.models import Events as EventsModel
from api.room.models import Room as RoomModel
from helpers.calendar.events import RoomSchedules, CalendarEvents
from helpers.email.email import notification
from helpers.calendar.credentials import get_single_calendar_event
from helpers.auth.authentication import Auth
from helpers.calendar.analytics_helper import CommonAnalytics
from helpers.auth.user_details import get_user_from_db
from helpers.pagination.paginate import ListPaginate, Paginate, validate_page
from helpers.devices.devices import update_device_last_seen
from helpers.events_filter.events_filter import (
    filter_events_by_date_range
)
import pytz
from dateutil import parser
from datetime import datetime, timedelta


class Events(SQLAlchemyObjectType):
    """
        Returns the events payload
    """
    class Meta:
        model = EventsModel


class DailyRoomEvents(graphene.ObjectType):
    """
    Returns days with their events
    """
    day = graphene.String()
    events = graphene.List(Events)


class EventCheckin(graphene.Mutation):
    """
        Returns the eventcheckin payload
    """
    class Arguments:
        calendar_id = graphene.String(required=True)
        event_id = graphene.String(required=True)
        event_title = graphene.String(required=True)
        start_time = graphene.String(required=True)
        end_time = graphene.String(required=True)
        number_of_participants = graphene.Int(required=True)
        check_in_time = graphene.String(required=False)
    event = graphene.Field(Events)

    def mutate(self, info, **kwargs):
        room_id, event = check_event_in_db(self, info, "checked_in", **kwargs)
        if kwargs.get('check_in_time'):
            update_device_last_seen(info, room_id, kwargs['check_in_time'])
        if not event:
            event = EventsModel(
                event_id=kwargs['event_id'],
                room_id=room_id,
                event_title=kwargs['event_title'],
                start_time=kwargs['start_time'],
                end_time=kwargs['end_time'],
                number_of_participants=kwargs['number_of_participants'],
                checked_in=True,
                cancelled=False)
            event.save()
        return EventCheckin(event=event)


class CancelEvent(graphene.Mutation):
    """
        Returns the payload on event cancelation
    """
    class Arguments:
        calendar_id = graphene.String(required=True)
        event_id = graphene.String(required=True)
        event_title = graphene.String(required=True)
        start_time = graphene.String(required=True)
        end_time = graphene.String(required=True)
        number_of_participants = graphene.Int()
    event = graphene.Field(Events)

    def mutate(self, info, **kwargs):
        # mutation to create an event
        room_id, event = check_event_in_db(self, info, "cancelled", **kwargs)
        try:
            device_last_seen = parser.parse(
                    kwargs['start_time']) + timedelta(minutes=10)
        except ValueError:
            raise GraphQLError("Invalid start time")
        update_device_last_seen(info, room_id, device_last_seen)
        if not event:
            event = EventsModel(
                event_id=kwargs['event_id'],
                room_id=room_id,
                event_title=kwargs['event_title'],
                start_time=kwargs['start_time'],
                end_time=kwargs['end_time'],
                number_of_participants=kwargs['number_of_participants'],
                checked_in=False,
                cancelled=True,
                auto_cancelled=True)
            event.save()
        calendar_event = get_single_calendar_event(
                                                    kwargs['calendar_id'],
                                                    kwargs['event_id']
                                                )
        event_reject_reason = 'after 10 minutes'
        if not notification.event_cancellation_notification(
                                                            calendar_event,
                                                            room_id,
                                                            event_reject_reason
                                                            ):
            raise GraphQLError("Event cancelled but email not sent")
        return CancelEvent(event=event)


class EndEvent(graphene.Mutation):
    """
    Mutation to end an event
    Returns event payload on ending the event
    """
    class Arguments:
        calendar_id = graphene.String(required=True)
        event_id = graphene.String(required=True)
        start_time = graphene.String(required=True)
        end_time = graphene.String(required=True)
        meeting_end_time = graphene.String(required=True)
    event = graphene.Field(Events)

    def mutate(self, info, **kwargs):
        room_id, event = check_event_in_db(self, info, "ended", **kwargs)
        if not event:
            event = EventsModel(
                event_id=kwargs['event_id'],
                meeting_end_time=kwargs['meeting_end_time']
                )
            event.save()

        return EndEvent(event=event)


class SyncEventData(graphene.Mutation):
    """
    Mutation to sync the event data in the db
    with the one on google calendar
    """
    message = graphene.String()

    def mutate(self, info):
        CalendarEvents().sync_all_events()
        return SyncEventData(message="success")


class MrmNotification(graphene.Mutation):
    """
    Mutation to receive notification from MRM_PUSH
    service
    """
    message = graphene.String()

    class Arguments:
        calendar_id = graphene.String()

    def mutate(self, info, calendar_id):
        room = RoomModel.query.filter_by(calendar_id=calendar_id).first()
        CalendarEvents().sync_single_room_events(room)
        return MrmNotification(message="success")


def check_event_in_db(instance, info, event_check, **kwargs):
    room_id = RoomSchedules().check_event_status(info, **kwargs)
    event = EventsModel.query.filter_by(
        start_time=kwargs['start_time'],
        event_id=kwargs['event_id']).scalar()
    if event and event_check == 'cancelled':
        event.cancelled = True
        event.auto_cancelled = True
        event.save()
        return room_id, event
    elif event and event_check == 'checked_in':
        event.checked_in = True
        if 'check_in_time' in kwargs:
            event.check_in_time = kwargs['check_in_time']
        else:
            event.check_in_time = None
        event.save()
        return room_id, event
    elif event and event_check == 'ended':
        if event.meeting_end_time:
            raise GraphQLError("Event has already ended")
        event.meeting_end_time = kwargs['meeting_end_time']
        event.save()
        return room_id, event
    return room_id, event


class Mutation(graphene.ObjectType):
    event_checkin = EventCheckin.Field()
    cancel_event = CancelEvent.Field()
    end_event = EndEvent.Field(
        description="Mutation to end a calendar event given the arguments\
            \n- calendar_id: The unique identifier of the calendar event\
            [required]\n- event_id: The unique identifier of the target\
                 calendar event[required]\
            \n- event_id: The unique identifier of the calendar event[required]\
            \n- start_time: The start time of the calendar event[required]\
            \n- end_time: The field with the end time of the calendar event\
            [required]\
            \n- meeting_end_time: The time the calendar event ended[required]")
    sync_event_data = SyncEventData.Field()
    mrm_notification = MrmNotification.Field()
    event_checkin = EventCheckin.Field(
        description="Mutation to check in to a calendar event given the arguments\
            \n- calendar_id: The unique identifier of the calendar event\
            [required]\n- event_id: The unique identifier of the target\
                 calendar event[required]\
            \n- event_title: The title field of the calendar event[required]\
            \n- start_time: The start time of the calendar event[required]\
            \n- end_time: The field with the end time of the calendar event\
            [required]")
    cancel_event = CancelEvent.Field(
        description="Mutation to cancel a claendar event given the arguments\
            \n- calendar_id: The unique identifier of the calendar event\
            [required]\n- event_id: The unique identifier of the target \
                calendar event\
            [required]\n- event_title: The title field of the calendar event\
            [required]\n- start_time: The start time of the calendar event\
            [required]\n- end_time: The field with the end time of the calendar\
             event[required]")


class PaginateEvents(Paginate):
    """
        Paginates the returned events with the number of pages,\
            the total number of events if it has next or previous page\
                the current page and the events field
    """
    events = graphene.List(Events)

    # def resolve_events(self, info):
    def resolve_events(self, info, **kwargs):
        page = self.page
        per_page = self.per_page
        query = Events.get_query(info)
        active_events = query.filter(EventsModel.state == 'active')
        if not page:
            return active_events
        page = validate_page(page)
        self.query_total = active_events.count()
        result = active_events.limit(
            per_page).offset(page * per_page)
        if result.count() == 0:
            return GraphQLError("No events found")
        return result


class PaginatedEvent(graphene.ObjectType):
    """
        Paginate the number of events returned
    """
    events = graphene.List(Events)
    pages = graphene.Int()
    query_total = graphene.Int()
    has_next = graphene.Boolean()
    has_previous = graphene.Boolean()
    events = graphene.List(Events)
    page = graphene.Int(),
    per_page = graphene.Int(),


class PaginatedDailyRoomEvents(graphene.ObjectType):
    """
    Paginated result for daily room events
    """
    DailyRoomEvents = graphene.List(DailyRoomEvents)
    has_previous = graphene.Boolean()
    has_next = graphene.Boolean()
    pages = graphene.Int()
    query_total = graphene.Int()


class Query(graphene.ObjectType):
    events = graphene.Field(
        PaginateEvents,
        page=graphene.Int(),
        per_page=graphene.Int(),
        description="Returns a list of paginated events and accepts the arguments\
            \n- page: The returned events page\
            \n- per_page: The number of events per page")

    all_events_by_date_range = graphene.Field(
        PaginatedEvent,
        start_date=graphene.String(),
        end_date=graphene.String(),
        page=graphene.Int(),
        per_page=graphene.Int(),
        description="Query that returns a list of events given the arguments\
            \n- start_date: The date and time to start selection \
                            when filtering by time period\
            \n- end_date: The date and time to end selection \
                            when filtering by time period")

    all_events = graphene.Field(
        PaginatedDailyRoomEvents,
        start_date=graphene.String(),
        end_date=graphene.String(),
        page=graphene.Int(),
        per_page=graphene.Int(),
        description="Query that returns a list of events given the arguments\
            \n- start_date: The date and time to start selection \
                            when filtering by time period\
            \n- end_date: The date and time to end selection \
                            when filtering by time period\
            \n- page: Page number to select when paginating\
            \n- per_page: The maximum number of pages per page when paginating")

    def resolve_events(self, info, **kwargs):
        # Returns the total number of events
        return PaginateEvents(**kwargs)

    def resolve_all_events_by_date_range(self, info, **kwargs):
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        page = kwargs.get('page')
        per_page = kwargs.get('per_page')
        if page is not None and page < 1:
            raise GraphQLError("page must be at least 1")
        if per_page is not None and per_page < 1:
            raise GraphQLError("perPage must be at least 1")
        if page and not per_page:
            raise GraphQLError("perPage argument missing")
        if per_page and not page:
            raise GraphQLError("page argument missing")
        # get all events by date range
        query = Events.get_query(info)
        events = query.filter(
            EventsModel.state == 'active'
            )
        response = filter_events_by_date_range(
            events,
            start_date, end_date
            )
        if not response:
            raise GraphQLError('Events do not exist for the date range')
        else:
            if page and per_page:
                paginated_response = ListPaginate(
                    iterable=response,
                    per_page=per_page,
                    page=page)
                current_page = paginated_response.current_page
                has_previous = paginated_response.has_previous
                has_next = paginated_response.has_next
                pages = paginated_response.pages
                query_total = paginated_response.query_total
                return PaginatedEvent(
                    events=current_page,
                    has_previous=has_previous,
                    has_next=has_next,
                    query_total=query_total,
                    pages=pages)

            return PaginatedEvent(events=response)

    @Auth.user_roles('Admin', 'Default User')
    def resolve_all_events(self, info, **kwargs):
        page = kwargs.get('page')
        per_page = kwargs.get('per_page')
        if page is not None and page < 1:
            raise GraphQLError("page must be at least 1")
        if per_page is not None and per_page < 1:
            raise GraphQLError("perPage must be at least 1")
        if page and not per_page:
            raise GraphQLError("perPage argument missing")
        if per_page and not page:
            raise GraphQLError("page argument missing")
        user = get_user_from_db()
        start_date, end_date = CommonAnalytics.all_analytics_date_validation(
            self, kwargs['start_date'], kwargs['end_date']
        )
        query = Events.get_query(info)
        all_events, all_dates = CommonAnalytics.get_all_events_and_dates(
            query, start_date, end_date
        )
        events_in_location = CalendarEvents().get_events_in_location(
            user, all_events)
        all_days_events = []
        for date in set(all_dates):
            daily_events = []
            for event in events_in_location:
                CommonAnalytics.format_date(event.start_time)
                event_start_date = parser.parse(
                    event.start_time).astimezone(pytz.utc)
                day_of_event = event_start_date.strftime("%a %b %d %Y")
                if date == day_of_event:
                    daily_events.append(event)
            if page and per_page:
                events = divide_daily_events_per_page(
                    self, date, per_page, daily_events)
                all_days_events = all_days_events + events
            else:
                all_days_events.append(
                    DailyRoomEvents(
                        day=date,
                        events=daily_events
                    )
                )
            all_days_events.sort(key=lambda x: datetime.strptime(x.day, "%a %b %d %Y"), reverse=True) # noqa
        if page and per_page:
            paginated_events = ListPaginate(
                iterable=all_days_events,
                per_page=1,
                page=page)
            has_previous = paginated_events.has_previous
            has_next = paginated_events.has_next
            current_page = paginated_events.current_page
            pages = paginated_events.pages
            query_total = paginated_events.query_total
            return PaginatedDailyRoomEvents(
                                     DailyRoomEvents=current_page,
                                     has_previous=has_previous,
                                     has_next=has_next,
                                     query_total=query_total,
                                     pages=pages)

        return PaginatedDailyRoomEvents(DailyRoomEvents=all_days_events)


def divide_daily_events_per_page(self, date, max_per_page, daily_events):
    events = []
    max_daily_events = max_per_page
    events_per_page = []
    for event_index, day_event in enumerate(daily_events):
        event_number = event_index + 1
        events_per_page.append(day_event)
        if (event_number == max_daily_events or
                len(daily_events) == event_number):
            events.append(
                DailyRoomEvents(
                    day=date,
                    events=events_per_page
                )
            )
            events_per_page = []
            max_daily_events += max_per_page
    return events