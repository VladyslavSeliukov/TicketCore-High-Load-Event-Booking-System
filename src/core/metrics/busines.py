from prometheus_client import Counter

TICKETS_RESERVED_TOTAL = Counter(
    "business_tickets_reserved_total",
    "Number of tickets successfully reserved (held in Redis)",
)

TICKETS_SOLD_TOTAL = Counter(
    "business_tickets_sold_total",
    "Number of tickets successfully paid and moved to SOLD status",
)

TICKETS_CANCELED_TOTAL = Counter(
    "business_tickets_canceled_total",
    "Number of tickets canceled",
    ["reason"],
)
