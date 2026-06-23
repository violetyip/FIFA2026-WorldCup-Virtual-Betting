#!/usr/bin/env python3
"""Refresh public odds, scores, and settlement data outside web requests."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from app import app, now_bjt, settle_match
from models import Bet, Match, db
from odds_updater import update_all_betexplorer_odds, update_finished_scores


@dataclass
class RefreshSummary:
    moved_to_live: int = 0
    odds_updated: int = 0
    scores_updated: int = 0
    settled_matches: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh public match data without blocking Flask requests. "
            "With no flags, the script refreshes odds, scores, and settlement."
        )
    )
    parser.add_argument(
        "--odds",
        action="store_true",
        help="Refresh published 1X2 odds.",
    )
    parser.add_argument(
        "--scores",
        action="store_true",
        help="Refresh finished match scores.",
    )
    parser.add_argument(
        "--settle",
        action="store_true",
        help="Settle bets for matches that are already marked finished.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Refresh odds, scores, and settlement explicitly.",
    )
    return parser.parse_args()


def sync_started_matches() -> int:
    """Move matches past kickoff from upcoming to live."""
    matches = Match.query.filter(
        Match.status == "upcoming",
        Match.match_time <= now_bjt(),
    ).all()
    for match in matches:
        match.status = "live"
    if matches:
        db.session.commit()
    return len(matches)


def settle_finished_matches() -> int:
    """Settle matches that already have a real final score recorded."""
    matches = (
        Match.query.join(Bet, Bet.match_id == Match.id)
        .filter(Match.status == "finished", Bet.status == "pending")
        .distinct()
        .all()
    )
    for match in matches:
        settle_match(match)
    return len(matches)


def should_run_all(args: argparse.Namespace) -> bool:
    return args.all or not any((args.odds, args.scores, args.settle))


def run_refresh(args: argparse.Namespace) -> RefreshSummary:
    summary = RefreshSummary()
    run_all = should_run_all(args)
    refresh_odds = run_all or args.odds
    refresh_scores = run_all or args.scores
    refresh_settlement = run_all or args.settle

    with app.app_context():
        if refresh_scores or refresh_settlement:
            summary.moved_to_live = sync_started_matches()
        if refresh_odds:
            summary.odds_updated = update_all_betexplorer_odds()
        if refresh_scores:
            summary.scores_updated = update_finished_scores()
        if refresh_settlement:
            summary.settled_matches = settle_finished_matches()
        db.session.commit()

    return summary


def print_summary(summary: RefreshSummary) -> None:
    print("Refresh completed.")
    print(f"Matches moved to live: {summary.moved_to_live}")
    print(f"Matches with refreshed odds: {summary.odds_updated}")
    print(f"Matches with refreshed scores: {summary.scores_updated}")
    print(f"Finished matches settled: {summary.settled_matches}")


def main() -> int:
    args = parse_args()
    try:
        summary = run_refresh(args)
    except KeyboardInterrupt:
        print("Refresh cancelled by user.", file=sys.stderr)
        return 130
    except Exception as exc:  # pragma: no cover - CLI safety net
        print(f"Refresh failed: {exc}", file=sys.stderr)
        return 1

    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
