import logging
from webull import webull, paper_webull

log = logging.getLogger("webull.client")


class WebullClient:
    def __init__(self, email: str, password: str, trade_pin: str, device_id: str = "", paper: bool = True):
        if paper:
            self._wb = paper_webull()
        else:
            self._wb = webull()

        if device_id:
            self._wb._did = device_id

        result = self._wb.login(email, password)
        log.info("Login result: %s", result)

        if not paper:
            self._wb.get_trade_token(trade_pin)

    def get_price(self, symbol: str) -> float:
        quote = self._wb.get_quote(symbol)
        price = quote.get("close") or quote.get("pPrice")
        if price is None:
            raise ValueError(f"No price in quote for {symbol}: {quote}")
        return float(price)

    def place_order(self, symbol: str, qty: int, side: str) -> dict:
        action = "BUY" if side == "buy" else "SELL"
        result = self._wb.place_order(
            stock=symbol,
            action=action,
            orderType="MKT",
            enforce="DAY",
            qty=qty,
        )
        log.info("place_order %s %s x%d → %s", action, symbol, qty, result)
        return result or {}
