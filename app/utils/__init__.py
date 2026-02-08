"""Utility functions package."""

def derive_no_bid_ask(yes_bid, yes_ask):
    """Derive no_bid and no_ask from yes_bid and yes_ask.
    
    In binary markets: yes_bid + no_ask = 100, yes_ask + no_bid = 100
    """
    no_bid = (100 - yes_ask) if yes_ask is not None else None
    no_ask = (100 - yes_bid) if yes_bid is not None else None
    return no_bid, no_ask

