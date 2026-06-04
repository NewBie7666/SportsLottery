from __future__ import annotations

import argparse
import json
from pathlib import Path

from sporttery_national.evaluation.backtester import backtest as run_backtest
from sporttery_national.export.csv_exporter import write_predictions_csv
from sporttery_national.export.json_exporter import write_predictions_json
from sporttery_national.export.markdown_report import write_markdown_report
from sporttery_national.ingest.fixture_loader import load_fixtures
from sporttery_national.ingest.history_fetcher import fetch_history
from sporttery_national.ingest.history_loader import import_history
from sporttery_national.mapping.team_normalizer import TeamNormalizer
from sporttery_national.models.predictor import predict_fixtures
from sporttery_national.models.trainer import train as train_model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sporttery-national")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch-history")
    p.add_argument("--source", choices=["openfootball"], required=True)
    p.add_argument("--output", required=True)

    p = sub.add_parser("import-history")
    p.add_argument("--source", choices=["csv", "openfootball"], default="csv")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--aliases")
    p.add_argument("--report-dir", default="reports")

    p = sub.add_parser("train")
    p.add_argument("--data", required=True)
    p.add_argument("--model-dir", required=True)

    p = sub.add_parser("backtest")
    p.add_argument("--data", required=True)
    p.add_argument("--model-dir")
    p.add_argument("--output", required=True)

    p = sub.add_parser("predict")
    p.add_argument("--fixtures", required=True)
    p.add_argument("--model-dir", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--history")
    p.add_argument("--aliases")

    p = sub.add_parser("teams")
    p.add_argument("--query", required=True)
    p.add_argument("--aliases")

    args = parser.parse_args(argv)
    if args.command == "fetch-history":
        print(fetch_history(args.source, args.output))
    elif args.command == "import-history":
        summary = import_history(args.input, args.output, args.aliases, source=args.source, report_dir=args.report_dir)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.command == "train":
        print(json.dumps(train_model(args.data, args.model_dir), ensure_ascii=False, indent=2))
    elif args.command == "backtest":
        print(json.dumps(run_backtest(args.data, args.output), ensure_ascii=False, indent=2))
    elif args.command == "predict":
        rows = predict_fixtures(load_fixtures(args.fixtures, args.aliases), args.model_dir, args.history)
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=True)
        write_predictions_csv(output / "predictions.csv", rows)
        write_predictions_json(output / "predictions.json", rows)
        write_markdown_report(output / "predictions.md", rows)
        print(f"Wrote {len(rows)} predictions to {output}")
    elif args.command == "teams":
        print(json.dumps(TeamNormalizer(args.aliases).query(args.query), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
