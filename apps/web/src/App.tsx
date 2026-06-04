import { useEffect, useState } from "react";
import AdjustmentSummaryView from "./components/AdjustmentSummary";
import BacktestSummaryView from "./components/BacktestSummary";
import PredictionTable from "./components/PredictionTable";
import SettlementSummaryView from "./components/SettlementSummary";
import { loadJson, type DataResult } from "./lib/loadData";
import type {
  AdjustmentSummary,
  BacktestDetail,
  BacktestSummary,
  PredictionRow,
  SettlementRow,
  SettlementSummary,
} from "./lib/types";

type DashboardData = {
  predictions: DataResult<PredictionRow[]>;
  backtestSummary: DataResult<BacktestSummary>;
  backtestDetails: DataResult<BacktestDetail[]>;
  settlementSummary: DataResult<SettlementSummary>;
  settlements: DataResult<SettlementRow[]>;
  adjustmentSummary: DataResult<AdjustmentSummary>;
  adjustedPredictions: DataResult<PredictionRow[]>;
  adjustedSettlementSummary: DataResult<SettlementSummary>;
};

const emptyData: DashboardData = {
  predictions: { status: "loading" },
  backtestSummary: { status: "loading" },
  backtestDetails: { status: "loading" },
  settlementSummary: { status: "loading" },
  settlements: { status: "loading" },
  adjustmentSummary: { status: "loading" },
  adjustedPredictions: { status: "loading" },
  adjustedSettlementSummary: { status: "loading" },
};

export default function App() {
  const [data, setData] = useState<DashboardData>(emptyData);

  useEffect(() => {
    let mounted = true;
    async function load() {
      const [
        predictions,
        backtestSummary,
        backtestDetails,
        settlementSummary,
        settlements,
        adjustmentSummary,
        adjustedPredictions,
        adjustedSettlementSummary,
      ] = await Promise.all([
        loadJson<PredictionRow[]>("/data/predictions.json", "请先运行 scripts\\predict_sample.ps1"),
        loadJson<BacktestSummary>("/data/backtest_summary.json", "请先运行 scripts\\smoke_test_v1.ps1"),
        loadJson<BacktestDetail[]>("/data/backtest_details.json", "请先运行 scripts\\smoke_test_v1.ps1"),
        loadJson<SettlementSummary>("/data/settlement_summary.json", "请先运行 scripts\\settle_sample.ps1"),
        loadJson<SettlementRow[]>("/data/settlements.json", "请先运行 scripts\\settle_sample.ps1"),
        loadJson<AdjustmentSummary>("/data/adjustment_summary.json", "请先运行 scripts\\adjust_sample.ps1"),
        loadJson<PredictionRow[]>("/data/adjusted_predictions.json", "请先运行 scripts\\adjust_sample.ps1"),
        loadJson<SettlementSummary>(
          "/data/settlements_adjusted/settlement_summary.json",
          "请先运行 scripts\\settle_adjusted_sample.ps1",
        ),
      ]);
      if (mounted) {
        setData({
          predictions,
          backtestSummary,
          backtestDetails,
          settlementSummary,
          settlements,
          adjustmentSummary,
          adjustedPredictions,
          adjustedSettlementSummary,
        });
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <main>
      <header className="page-header">
        <div>
          <p className="eyebrow">SportsLottery V1.5</p>
          <h1>国家队胜平负报告查看器</h1>
        </div>
        <p className="disclaimer">本页面仅展示概率研究结果，不提供投注建议，不承诺中奖或盈利。</p>
      </header>

      <PredictionTable result={data.predictions} />
      <BacktestSummaryView summary={data.backtestSummary} details={data.backtestDetails} />
      <SettlementSummaryView
        summary={data.settlementSummary}
        rows={data.settlements}
        adjustedSummary={data.adjustedSettlementSummary}
      />
      <AdjustmentSummaryView summary={data.adjustmentSummary} adjustedRows={data.adjustedPredictions} />
    </main>
  );
}
