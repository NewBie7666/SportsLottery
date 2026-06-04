import EmptyState from "./EmptyState";
import MetricCard from "./MetricCard";
import { entries, integer, number, percent } from "../lib/format";
import type { DataResult } from "../lib/loadData";
import type { SettlementRow, SettlementSummary } from "../lib/types";

type Props = {
  summary: DataResult<SettlementSummary>;
  rows: DataResult<SettlementRow[]>;
  adjustedSummary: DataResult<SettlementSummary>;
};

export default function SettlementSummaryView({ summary, rows, adjustedSummary }: Props) {
  return (
    <section>
      <div className="section-title">
        <h2>赛后结算</h2>
        <p>读取 public/data/settlement_summary.json 和 settlements.json</p>
      </div>
      <EmptyState result={summary} />
      {summary.status === "ready" && (
        <>
          <div className="metrics-grid">
            <MetricCard label="总场次" value={integer(summary.data.total_matches)} />
            <MetricCard label="逐场明细" value={rows.status === "ready" ? integer(rows.data.length) : "--"} />
            <MetricCard label="Base 首选命中率" value={percent(summary.data.base_top1_accuracy, 2)} />
            <MetricCard label="Adjusted 首选命中率" value={percent(summary.data.adjusted_top1_accuracy, 2)} />
            <MetricCard label="Base Log Loss" value={number(summary.data.base_avg_log_loss, 4)} />
            <MetricCard label="Adjusted Log Loss" value={number(summary.data.adjusted_avg_log_loss, 4)} />
            <MetricCard label="Base Brier" value={number(summary.data.base_avg_brier, 4)} />
            <MetricCard label="Adjusted Brier" value={number(summary.data.adjusted_avg_brier, 4)} />
            <MetricCard label="错误场次" value={integer(summary.data.error_count)} />
          </div>
          {(summary.data.total_matches ?? 0) < 30 && (
            <div className="notice notice-warning">
              结算样本较少，Accuracy / Log Loss / Brier 仅供流程验证。
            </div>
          )}
          {adjustedSummary.status === "ready" && (
            <div className="notice">
              参数实验结算快照：Adjusted 首选命中率 {percent(adjustedSummary.data.adjusted_top1_accuracy, 2)}，
              Adjusted Log Loss {number(adjustedSummary.data.adjusted_avg_log_loss, 4)}。
            </div>
          )}
          <GroupTable title="置信等级分组" group={summary.data.by_confidence} />
          <GroupTable title="赛事类型分组" group={summary.data.by_competition} />
        </>
      )}
    </section>
  );
}

function GroupTable({ title, group }: { title: string; group?: Record<string, { matches?: number; accuracy?: number | null; avg_log_loss?: number | null }> }) {
  const rows = entries(group).slice(0, 20);
  if (!rows.length) return null;
  return (
    <div className="table-block">
      <h3>{title}</h3>
      <table>
        <thead>
          <tr>
            <th>分组</th>
            <th className="num">场次</th>
            <th className="num">首选命中率</th>
            <th className="num">Log Loss</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([name, raw]) => {
            const item = raw as { matches?: number; accuracy?: number | null; avg_log_loss?: number | null };
            return (
              <tr key={name}>
                <td>{name}</td>
                <td className="num">{integer(item.matches)}</td>
                <td className="num">{percent(item.accuracy, 2)}</td>
                <td className="num">{number(item.avg_log_loss, 4)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
