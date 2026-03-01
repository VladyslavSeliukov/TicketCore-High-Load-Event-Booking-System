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


class AuthError(Exception):
    pass


class UserAlreadyExistsError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class InactiveUserError(AuthError):
    pass
