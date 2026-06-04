import EmptyState from "./EmptyState";
import { percent, text } from "../lib/format";
import type { DataResult } from "../lib/loadData";
import type { PredictionRow } from "../lib/types";

type Props = {
  result: DataResult<PredictionRow[]>;
};

export default function PredictionTable({ result }: Props) {
  return (
    <section>
      <div className="section-title">
        <h2>预测结果</h2>
        <p>读取 public/data/predictions.json</p>
      </div>
      <EmptyState result={result} />
      {result.status === "ready" && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>期号</th>
                <th>场次</th>
                <th>主队</th>
                <th>客队</th>
                <th className="num">主胜</th>
                <th className="num">平</th>
                <th className="num">客胜</th>
                <th>首选</th>
                <th className="num">次选</th>
                <th className="num">概率差</th>
                <th>置信等级</th>
                <th>风险说明</th>
              </tr>
            </thead>
            <tbody>
              {result.data.map((row, index) => (
                <tr key={`${row.issue_id ?? "issue"}-${row.match_id ?? index}`}>
                  <td>{text(row.issue_id)}</td>
                  <td>{text(row.match_id)}</td>
                  <td>{text(row.home_team)}</td>
                  <td>{text(row.away_team)}</td>
                  <td className="num">{percent(row.base_home_win_prob, 1)}</td>
                  <td className="num">{percent(row.base_draw_prob, 1)}</td>
                  <td className="num">{percent(row.base_away_win_prob, 1)}</td>
                  <td>{text(row.top1_label)}</td>
                  <td className="num">{text(row.second_pick)}</td>
                  <td className="num">{percent(row.probability_gap, 1)}</td>
                  <td><span className={`pill ${text(row.confidence)}`}>{text(row.confidence)}</span></td>
                  <td className="note">{text(row.risk_note)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
