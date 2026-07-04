from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import logging

log = logging.getLogger("buzembe.tsla")

SYMBOL        = "TSLA"
LONG_QTY      = 100
SHORT_QTY     = 200
LONG_STOP     = 0.40
SHORT_STOP    = 0.40
CONTINUATION  = 0.30
TRAIL_PCT     = 0.10


class Phase(Enum):
    IDLE          = auto()
    LONG          = auto()
    LONG_EXITED   = auto()
    SHORT         = auto()
    DONE          = auto()


@dataclass
class StrategyState:
    phase: Phase = Phase.IDLE
    long_entry: Optional[float] = None
    long_exit:  Optional[float] = None
    short_entry: Optional[float] = None
    best_price:    Optional[float] = None
    trailing_stop: Optional[float] = None
    long_order_id:  Optional[str] = None
    short_order_id: Optional[str] = None
    log: list = field(default_factory=list)

    def record(self, event: str, price: float, **kwargs):
        entry = {"ts": datetime.utcnow().isoformat(), "event": event, "price": price, **kwargs}
        self.log.append(entry)
        log.info("[%s] %s @ %.4f  %s", self.phase.name, event, price, kwargs or "")


class TslaStrategy:
    def __init__(self):
        self.state = StrategyState()

    def tick(self, price: float, now_est: datetime) -> list[dict]:
        s = self.state
        if s.phase == Phase.IDLE:
            return self._handle_idle(price, now_est)
        elif s.phase == Phase.LONG:
            return self._handle_long(price)
        elif s.phase == Phase.LONG_EXITED:
            return self._handle_long_exited(price)
        elif s.phase == Phase.SHORT:
            return self._handle_short(price)
        return []

    def _handle_idle(self, price, now_est):
        s = self.state
        entry_hour, entry_minute = 10, 0
        if now_est.hour > entry_hour or (now_est.hour == entry_hour and now_est.minute >= entry_minute):
            s.phase = Phase.LONG
            s.long_entry = price
            s.best_price = price
            s.trailing_stop = None
            s.record("long_entry", price, qty=LONG_QTY)
            return [{"action": "buy", "symbol": SYMBOL, "qty": LONG_QTY}]
        return []

    def _handle_long(self, price):
        s = self.state
        pnl = price - s.long_entry
        if pnl > 0:
            if s.best_price is None or price > s.best_price:
                s.best_price = price
                s.trailing_stop = s.best_price * (1 - TRAIL_PCT)
        exit_reason = None
        if s.trailing_stop is not None and price <= s.trailing_stop:
            exit_reason = "trailing_stop"
        elif pnl <= -LONG_STOP:
            exit_reason = "stop_loss"
        if exit_reason:
            s.long_exit = price
            s.record("long_exit", price, reason=exit_reason, pnl_per_share=round(pnl, 4))
            s.phase = Phase.LONG_EXITED if exit_reason == "stop_loss" else Phase.DONE
            return [{"action": "sell", "symbol": SYMBOL, "qty": LONG_QTY, "reason": exit_reason}]
        return []

    def _handle_long_exited(self, price):
        s = self.state
        if s.long_exit - price >= CONTINUATION:
            s.short_entry = price
            s.best_price  = price
            s.trailing_stop = None
            s.phase = Phase.SHORT
            s.record("short_entry", price, qty=SHORT_QTY)
            return [{"action": "short", "symbol": SYMBOL, "qty": SHORT_QTY}]
        return []

    def _handle_short(self, price):
        s = self.state
        pnl = s.short_entry - price
        if pnl > 0:
            if s.best_price is None or price < s.best_price:
                s.best_price = price
                s.trailing_stop = s.best_price * (1 + TRAIL_PCT)
        exit_reason = None
        if s.trailing_stop is not None and price >= s.trailing_stop:
            exit_reason = "trailing_stop"
        elif pnl <= -SHORT_STOP:
            exit_reason = "stop_loss"
        if exit_reason:
            s.record("short_exit", price, reason=exit_reason, pnl_per_share=round(pnl, 4))
            s.phase = Phase.DONE
            return [{"action": "cover", "symbol": SYMBOL, "qty": SHORT_QTY, "reason": exit_reason}]
        return []

    def summary(self):
        s = self.state
        return {
            "phase":        s.phase.name,
            "long_entry":   s.long_entry,
            "long_exit":    s.long_exit,
            "short_entry":  s.short_entry,
            "trailing_stop": s.trailing_stop,
            "events":       s.log,
        }
