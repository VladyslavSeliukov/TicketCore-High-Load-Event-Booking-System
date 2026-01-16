from pydantic import BaseModel, Field, ConfigDict

class TicketCreate(BaseModel):
    event_name: str = Field(..., min_length=3, max_length=100, description='Name of the event', examples=['Korn Europe Tour 2026'])
    price: int = Field(..., gt=0, description='Price in cents. Each dollar has 100 cents', examples=['10000'])
    quantity: int = Field(..., gt=0, description='Quantity of tickets', examples=['100'])

class TicketResponse(TicketCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)