"""Estimate AI spend based on commit activity and known pricing.

Since developers use individual Anthropic accounts (no org admin API),
we estimate spend using lines changed, average tokens per line, and
published pricing. When org admin API becomes available, this can be
supplemented with actual billing data.
"""

import argparse
import logging
from datetime import date, timedelta
from decimal import Decimal

from collector.db import get_connection, load_config, upsert_ai_spend

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def estimate_spend(config: dict, target_date: date):
    """Estimate AI spend for a given date based on daily_contributions data."""
    spend_config = config.get("spend", {}).get("estimation", {})

    if not spend_config:
        logger.warning("No spend estimation config found")
        return

    conn = get_connection(config)
    try:
        # Read daily_contributions for the target date
        with conn.cursor() as cur:
            cur.execute(
                "SELECT repo, tool, lines_added, lines_removed "
                "FROM daily_contributions WHERE date = %s",
                (target_date,),
            )
            contributions = cur.fetchall()

        if not contributions:
            logger.info(f"No contributions found for {target_date}")
            return

        rows = []
        for repo, tool, lines_added, lines_removed, in contributions:
            if tool == "human":
                continue  # No AI spend for human commits

            tool_config = spend_config.get(tool)
            if not tool_config:
                logger.debug(f"No spend config for tool: {tool}")
                continue

            total_lines = lines_added + lines_removed

            if "tokens_per_line" in tool_config:
                # Token-based estimation (e.g., Claude)
                tokens_per_line = tool_config["tokens_per_line"]
                input_output_ratio = tool_config.get("input_output_ratio", 3)
                input_price = Decimal(str(tool_config.get("input_price_per_m", 3.0)))
                output_price = Decimal(str(tool_config.get("output_price_per_m", 15.0)))

                # Estimate tokens: output tokens ≈ lines * tokens_per_line
                # Input tokens ≈ output tokens * input_output_ratio
                tokens_output = total_lines * tokens_per_line
                tokens_input = tokens_output * input_output_ratio

                # Calculate spend
                spend = (
                    Decimal(tokens_input) / Decimal(1_000_000) * input_price
                    + Decimal(tokens_output) / Decimal(1_000_000) * output_price
                )

                rows.append((
                    target_date,
                    repo,
                    tool,
                    float(round(spend, 2)),
                    tokens_input,
                    tokens_output,
                    "estimated",
                ))

            elif "monthly_per_seat" in tool_config:
                # Flat-rate estimation (e.g., Windsurf)
                monthly_rate = Decimal(str(tool_config["monthly_per_seat"]))

                # Count active users for this tool on this date
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(DISTINCT author) FROM daily_active_users "
                        "WHERE date = %s AND repo = %s AND tool = %s",
                        (target_date, repo, tool),
                    )
                    active_users = cur.fetchone()[0] or 0

                if active_users == 0:
                    continue

                # Estimate daily spend: monthly rate / ~22 working days * active users
                daily_spend = monthly_rate / Decimal(22) * Decimal(active_users)

                rows.append((
                    target_date,
                    repo,
                    tool,
                    float(round(daily_spend, 2)),
                    0,  # no token tracking for flat-rate tools
                    0,
                    "estimated",
                ))

        if rows:
            upsert_ai_spend(conn, rows)
            logger.info(f"Upserted {len(rows)} spend estimates for {target_date}")
        else:
            logger.info(f"No AI spend to estimate for {target_date}")

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Estimate AI spend from commit activity")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        help="Date to estimate spend for (YYYY-MM-DD). Defaults to yesterday.",
    )
    parser.add_argument(
        "--backfill-days",
        type=int,
        default=0,
        help="Number of days to backfill (0 = just the target date).",
    )
    args = parser.parse_args()

    config = load_config()
    target = args.date or (date.today() - timedelta(days=1))

    for i in range(args.backfill_days + 1):
        d = target - timedelta(days=i)
        logger.info(f"Estimating spend for {d}")
        estimate_spend(config, d)


if __name__ == "__main__":
    main()
