import EmptyState from "./EmptyState";
import MetricCard from "./MetricCard";
import { entries, integer, number, percent, text } from "../lib/format";
import type { DataResult } from "../lib/loadData";
import type { AdjustmentSummary, PredictionRow } from "../lib/types";

type Props = {
  summary: DataResult<AdjustmentSummary>;
  adjustedRows: DataResult<PredictionRow[]>;
};

export default function AdjustmentSummaryView({ summary, adjustedRows }: Props) {
  return (
    <section>
      <div className="section-title">
        <h2>参数实验</h2>
        <p>读取 public/data/adjustment_summary.json 和 adjusted_predictions.json</p>
      </div>
      <EmptyState result={summary} />
      {summary.status === "ready" && (
        <>
          <div className="metrics-grid">
            <MetricCard label="实验名称" value={text(summary.data.experiment_name)} wide />
            <MetricCard label="总场次" value={integer(summary.data.total_matches)} />
            <MetricCard label="调整后预测数" value={adjustedRows.status === "ready" ? integer(adjustedRows.data.length) : "--"} />
            <MetricCard label="首选变化数" value={integer(summary.data.changed_pick_count ?? summary.data.changed_top1_count)} />
            <MetricCard label="市场概率跳过数" value={integer(summary.data.market_skipped_count ?? summary.data.market_weight_skipped_count)} />
            <MetricCard label="平均概率变动" value={percent(summary.data.avg_abs_prob_shift, 2)} />
            <MetricCard label="主胜概率变动" value={percent(summary.data.avg_abs_home_shift, 2)} />
            <MetricCard label="平局概率变动" value={percent(summary.data.avg_abs_draw_shift, 2)} />
            <MetricCard label="客胜概率变动" value={percent(summary.data.avg_abs_away_shift, 2)} />
          </div>
          {(summary.data.total_matches ?? 0) < 100 && (
            <div className="notice notice-warning">
              当前参数实验样本量较小，仅用于流程验证，不代表策略长期有效。
            </div>
          )}
          <ParamsTable params={summary.data.adjustment_params} />
          <DistributionTable
            base={summary.data.base_top1_distribution}
            adjusted={summary.data.adjusted_top1_distribution}
          />
          <ChangedPicks rows={summary.data.changed_picks ?? []} />
        </>
      )}
    </section>
  );
}

function ParamsTable({ params }: { params?: Record<string, unknown> }) {
  const rows = entries(params);
  if (!rows.length) return null;
  return (
    <div className="table-block">
      <h3>实验参数</h3>
      <table>
        <tbody>
          {rows.map(([key, value]) => (
            <tr key={key}>
              <th>{key}</th>
              <td className="num">{text(value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DistributionTable({ base, adjusted }: { base?: Record<string, number>; adjusted?: Record<string, number> }) {
  const labels = Array.from(new Set([...Object.keys(base ?? {}), ...Object.keys(adjusted ?? {})]));
  if (!labels.length) return null;
  return (
    <div className="table-block">
      <h3>Top1 分布</h3>
      <table>
        <thead>
          <tr>
            <th>结果</th>
            <th className="num">Base 首选数</th>
            <th className="num">Adjusted 首选数</th>
          </tr>
        </thead>
        <tbody>
          {labels.map((label) => (
            <tr key={label}>
              <td>{label}</td>
              <td className="num">{integer(base?.[label])}</td>
              <td className="num">{integer(adjusted?.[label])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ChangedPicks({ rows }: { rows: NonNullable<AdjustmentSummary["changed_picks"]> }) {
  if (!rows.length) {
    return <p className="empty">没有首选结果变化的比赛。</p>;
  }
  return (
    <div className="table-block">
      <h3>首选变化样例</h3>
      <table>
        <thead>
          <tr>
            <th>期号</th>
            <th>场次</th>
            <th>主队</th>
            <th>客队</th>
            <th>Base 首选</th>
            <th>Adjusted 首选</th>
            <th className="num">Base 主胜</th>
            <th className="num">Base 平</th>
            <th className="num">Base 客胜</th>
            <th className="num">Adj 主胜</th>
            <th className="num">Adj 平</th>
            <th className="num">Adj 客胜</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 20).map((row, index) => (
            <tr key={`${row.issue_id ?? "issue"}-${row.match_id ?? index}`}>
              <td>{text(row.issue_id)}</td>
              <td>{text(row.match_id)}</td>
              <td>{text(row.home_team)}</td>
              <td>{text(row.away_team)}</td>
              <td>{text(row.top1_label)}</td>
              <td>{text(row.adjusted_top1_label)}</td>
              <td className="num">{percent(row.base_home_win_prob, 1)}</td>
              <td className="num">{percent(row.base_draw_prob, 1)}</td>
              <td className="num">{percent(row.base_away_win_prob, 1)}</td>
              <td className="num">{percent(row.adjusted_home_win_prob, 1)}</td>
              <td className="num">{percent(row.adjusted_draw_prob, 1)}</td>
              <td className="num">{percent(row.adjusted_away_win_prob, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
