class EventError(Exception):
    pass


class EventNotFoundError(EventError):
    pass


class EventDeleteError(EventError):
    pass


class TicketError(Exception):
    pass


class TicketsSoldOutError(TicketError):
    pass


class TicketNotFoundError(TicketError):
    pass
