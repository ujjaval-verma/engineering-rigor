from pydantic import BaseModel, Field


class Money(BaseModel, frozen=True):
    """Integer cents. Money is never a float (invariant 1)."""

    cents: int = Field(ge=0)


def add_money(a: Money, b: Money) -> Money:
    return Money(cents=a.cents + b.cents)
