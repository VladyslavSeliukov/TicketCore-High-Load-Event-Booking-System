class EventError(Exception):
    """Base exception for all event-related domain errors."""

    pass


class EventNotFoundError(EventError):
    """Raised when a requested event cannot be found in the database."""

    pass


class EventDeleteError(EventError):
    """Raised when an event cannot be deleted due to existing ticket relations."""

    pass


class TicketError(Exception):
    """Base exception for all ticket-related domain errors."""

    pass


class TicketsSoldOutError(TicketError):
    """Raised when attempting to reserve a ticket for a sold-out ticket type."""

    pass


class TicketNotFoundError(TicketError):
    """Raised when a requested ticket cannot be found or does not belong to the user."""

    pass


class AuthError(Exception):
    """Base exception for all authentication and authorization errors."""

    pass


class UserAlreadyExistsError(AuthError):
    """Raised during registration if the provided email is already in use."""

    pass


class InvalidCredentialsError(AuthError):
    """Raised when a login attempt fails due to an incorrect email or password."""

    pass


class InactiveUserError(AuthError):
    """Raised when a deactivated user attempts to log in or perform actions."""

    pass


class TicketTypeError(Exception):
    """Base exception for all ticket type-related domain errors."""

    pass


class TicketTypeNotFoundError(TicketTypeError):
    """Raised when a requested ticket type cannot be found."""

    pass


class TicketTypeDeleteError(TicketTypeError):
    """Raised when a ticket type cannot be deleted due to existing ticket relations."""

    pass


class TicketTypeQuantity(TicketTypeError):
    """Raised when attempting to reduce ticket capacity below already sold."""

    pass


class EmptyUpdateDataError(Exception):
    """Raised when an update request payload contains no fields to modify."""

    pass


class IdempotencyError(Exception):
    """Base exception for idempotency lock and caching errors."""

    pass


class IdempotencyConflictError(IdempotencyError):
    """Raised when payload mismatches the original request for the idempotency key."""

    pass


class IdempotencyStateError(IdempotencyError):
    """Raised when the idempotency cache is corrupted.

    Also raised when experiencing lock contention.
    """

    pass


class PaymentError(Exception):
    """Base exception for ticket payment processing errors."""

    pass


class TicketReservationExpireError(PaymentError):
    """Raised when paying for a ticket whose reservation has timed out."""

    pass


class TicketAlreadyPaidError(PaymentError):
    """Raised when a payment attempt is made on an already SOLD ticket."""

    pass
