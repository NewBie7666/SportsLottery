import EmptyState from "./EmptyState";
import MetricCard from "./MetricCard";
import { entries, integer, number, percent, text } from "../lib/format";
import type { DataResult } from "../lib/loadData";
import type { BacktestDetail, BacktestSummary } from "../lib/types";

type Props = {
  summary: DataResult<BacktestSummary>;
  details: DataResult<BacktestDetail[]>;
};

export default function BacktestSummaryView({ summary, details }: Props) {
  return (
    <section>
      <div className="section-title">
        <h2>回测诊断</h2>
        <p>读取 public/data/backtest_summary.json 和 backtest_details.json</p>
      </div>
      <EmptyState result={summary} />
      {summary.status === "ready" && (
        <>
          <div className="metrics-grid">
            <MetricCard label="总场次" value={integer(summary.data.total_matches)} />
            <MetricCard label="首选命中率" value={percent(summary.data.top1_accuracy, 2)} />
            <MetricCard label="平均 Log Loss" value={number(summary.data.avg_log_loss, 4)} />
            <MetricCard label="平均 Brier" value={number(summary.data.avg_brier, 4)} />
            <MetricCard label="平局召回率" value={percent(summary.data.draw_recall, 2)} />
            <MetricCard label="主胜召回率" value={percent(summary.data.home_win_recall, 2)} />
            <MetricCard label="客胜召回率" value={percent(summary.data.away_win_recall, 2)} />
            <MetricCard
              label="明细场次"
              value={details.status === "ready" ? integer(details.data.length) : "--"}
            />
          </div>
          <MetricNotes />
          <DrawBiasNotice summary={summary.data} />
          <RecordTable title="平局偏差" rows={entries(summary.data.draw_bias_diagnostics)} formatter="number" />
          <BiasTable summary={summary.data} />
          <MetricGroup title="置信等级分组" group={summary.data.by_confidence} />
          <MetricGroup title="近期窗口" group={summary.data.recent_windows} />
          <CalibrationTable rows={summary.data.calibration_bins ?? []} />
        </>
      )}
    </section>
  );
}

function MetricNotes() {
  return (
    <div className="info-list">
      <span>Log Loss 越低越好，用于衡量概率质量。</span>
      <span>Brier 越低越好，用于衡量三分类概率误差。</span>
      <span>平局召回率用于观察模型是否能把真实平局预测为首选平局。</span>
      <span>校准分桶用于比较模型给出的概率和实际命中率是否接近。</span>
    </div>
  );
}

function DrawBiasNotice({ summary }: { summary: BacktestSummary }) {
  const diagnostics = summary.draw_bias_diagnostics;
  const drawActualRate = diagnostics?.draw_actual_rate;
  const drawTop1Rate = diagnostics?.draw_top1_rate;
  const shouldShow =
    typeof drawActualRate === "number" &&
    drawActualRate > 0 &&
    (drawTop1Rate === 0 || summary.draw_recall === 0);

  if (!shouldShow) return null;

  return (
    <div className="notice notice-warning">
      模型历史回测中几乎不把平局作为首选，可能系统性低估平局 Top1 召回。
    </div>
  );
}

function RecordTable({ title, rows, formatter }: { title: string; rows: Array<[string, unknown]>; formatter: "number" }) {
  if (!rows.length) return null;
  return (
    <div className="table-block">
      <h3>{title}</h3>
      <table>
        <tbody>
          {rows.map(([key, value]) => (
            <tr key={key}>
              <th>{key}</th>
              <td className="num">{formatter === "number" ? number(value, 4) : text(value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BiasTable({ summary }: { summary: BacktestSummary }) {
  const labels = ["3", "1", "0"];
  const bias = summary.prediction_bias;
  if (!bias) return null;
  return (
    <div className="table-block">
      <h3>预测分布偏差</h3>
      <table>
        <thead>
          <tr>
            <th>结果</th>
            <th className="num">实际占比</th>
            <th className="num">Top1 占比</th>
            <th className="num">差值</th>
          </tr>
        </thead>
        <tbody>
          {labels.map((label) => (
            <tr key={label}>
              <td>{label}</td>
              <td className="num">{percent(bias.actual_distribution?.[label], 2)}</td>
              <td className="num">{percent(bias.top1_distribution?.[label], 2)}</td>
              <td className="num">{percent(bias.distribution_gap?.[label], 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MetricGroup({ title, group }: { title: string; group?: Record<string, { matches?: number; accuracy?: number | null; avg_log_loss?: number | null; avg_brier?: number | null; draw_recall?: number | null }> }) {
  const rows = entries(group);
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
            <th className="num">Brier</th>
            <th className="num">平局召回率</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([name, raw]) => {
            const item = raw as { matches?: number; accuracy?: number | null; avg_log_loss?: number | null; avg_brier?: number | null; draw_recall?: number | null };
            return (
              <tr key={name}>
                <td>{name}</td>
                <td className="num">{integer(item.matches)}</td>
                <td className="num">{percent(item.accuracy, 2)}</td>
                <td className="num">{number(item.avg_log_loss, 4)}</td>
                <td className="num">{number(item.avg_brier, 4)}</td>
                <td className="num">{percent(item.draw_recall, 2)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function CalibrationTable({ rows }: { rows: NonNullable<BacktestSummary["calibration_bins"]> }) {
  if (!rows.length) return null;
  return (
    <div className="table-block">
      <h3>校准分桶</h3>
      <table>
        <thead>
          <tr>
            <th>分桶</th>
            <th className="num">场次</th>
            <th className="num">平均首选概率</th>
            <th className="num">首选命中率</th>
            <th className="num">Log Loss</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.bin}>
              <td>{row.bin}</td>
              <td className="num">{integer(row.matches)}</td>
              <td className="num">{percent(row.avg_top1_prob, 2)}</td>
              <td className="num">{percent(row.accuracy, 2)}</td>
              <td className="num">{number(row.avg_log_loss, 4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
