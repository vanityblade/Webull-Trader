import time
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from src.client import WebullClient
from src.strategies.tsla_3attempt import TslaStrategy, Phase, SYMBOL
from src.config import LOGS_DIR

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("webull.tsla_runner")

EST = ZoneInfo("America/New_York")
POLL_SECONDS = 5


def log_summary(strategy):
    path = LOGS_DIR / "tsla_3attempt.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(strategy.summary()) + "\n")


def execute_actions(client, actions, current_price):
    for act in actions:
        action = act["action"]
        qty    = act["qty"]
        reason = act.get("reason", "")
        try:
            if action in ("buy", "cover"):
                order = client.place_order(SYMBOL, qty, "buy")
                log.info("ORDER %s %s x%d reason=%s -> %s", action, SYMBOL, qty, reason, order)
            elif action in ("sell", "short"):
                order = client.place_order(SYMBOL, qty, "sell")
                log.info("ORDER %s %s x%d reason=%s -> %s", action, SYMBOL, qty, reason, order)
        except Exception as e:
            log.error("Failed to execute %s: %s", action, e)


def run(client):
    strategy = TslaStrategy()
    log.info("TSLA 3-Attempt strategy started. Waiting for 10:00 AM EST...")
    try:
        while strategy.state.phase != Phase.DONE:
            now_est = datetime.now(EST)
            if not (9 <= now_est.hour < 16):
                log.info("Outside market hours (%s EST) - sleeping 60s", now_est.strftime("%H:%M"))
                time.sleep(60)
                continue
            try:
                price = client.get_price(SYMBOL)
                actions = strategy.tick(price, now_est)
                if actions:
                    execute_actions(client, actions, price)
            except Exception as e:
                log.error("Tick error: %s", e)
            time.sleep(POLL_SECONDS)
    finally:
        summary = strategy.summary()
        log.info("Strategy complete. Summary: %s", summary)
        log_summary(strategy)


def main():
    from src.config import WEBULL_EMAIL, WEBULL_PASSWORD, WEBULL_TRADE_PIN, WEBULL_DEVICE_ID
    client = WebullClient(
        email=WEBULL_EMAIL,
        password=WEBULL_PASSWORD,
        trade_pin=WEBULL_TRADE_PIN,
        device_id=WEBULL_DEVICE_ID,
        paper=True,
    )
    run(client)


if __name__ == "__main__":
    main()
