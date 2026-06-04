# 体育彩票胜平负国家队预测项目 V1

本项目是一个只针对国家队比赛的体育彩票胜平负概率分析 CLI MVP。它输出主胜 / 平 / 客胜概率、官方奖金隐含概率对比和 CSV / JSON / Markdown 报告。

本项目只提供概率分析，不提供投注建议，不承诺中奖或盈利。

## 边界

- V1 只做国家队，不做俱乐部比赛。
- V1 只做本地 CLI，不做网页前端。
- V1 不自动抓取中国体彩网。
- V1 不自动投注，不给投注金额建议，不做组合生成。
- V1 不把官方奖金作为训练标签。
- V1 的调参接口只是占位，`adjusted_*` 概率等于 `base_*` 概率。

## 获取国家队历史数据

推荐数据源：https://github.com/openfootball/internationals

同步真实历史数据：

```powershell
python -m sporttery_national.cli fetch-history --source openfootball --output data/raw/internationals/openfootball-internationals
```

导入真实历史数据：

```powershell
python -m sporttery_national.cli import-history --source openfootball --input data/raw/internationals/openfootball-internationals --output data/processed/national_matches.jsonl
```

训练模型：

```powershell
python -m sporttery_national.cli train --data data/processed/national_matches.jsonl --model-dir models/national
```

回测：

```powershell
python -m sporttery_national.cli backtest --data data/processed/national_matches.jsonl --model-dir models/national --output reports/backtests
```

导入会生成 `reports/import_history_summary.md`，解析失败和未知队名会写入 `reports/import_errors/`。

## CSV 数据来源

如果暂时不用 openfootball，也可以继续导入用户提供的简化 CSV：

```powershell
python -m sporttery_national.cli import-history --source csv --input data/raw/internationals/sample.csv --output data/processed/national_matches.jsonl
```

当期体彩比赛由手动 CSV 输入。必填列：

```csv
match_id,date,kickoff,home_team,away_team,odds_home,odds_draw,odds_away
```

可选列：

```csv
issue_id,competition,neutral,venue,notes
```

## CLI

```powershell
python -m sporttery_national.cli fetch-history --source openfootball --output data/raw/internationals/openfootball-internationals
python -m sporttery_national.cli import-history --source openfootball --input data/raw/internationals/openfootball-internationals --output data/processed/national_matches.jsonl
python -m sporttery_national.cli train --data data/processed/national_matches.jsonl --model-dir models/national
python -m sporttery_national.cli backtest --data data/processed/national_matches.jsonl --model-dir models/national --output reports/backtests
python -m sporttery_national.cli predict --fixtures data/raw/lottery_fixtures/current_issue.csv --model-dir models/national --output reports/predictions
python -m sporttery_national.cli teams --query 德国
```

当前实现仅使用 Python 标准库。处理后历史数据明确保存为 JSONL，不伪装成 Parquet。

## 预测输出字段

输出字段固定为：

```text
issue_id, match_id, date, kickoff, competition, venue, neutral,
home_team_raw, away_team_raw, home_team, away_team,
odds_home, odds_draw, odds_away,
implied_home_win_prob, implied_draw_prob, implied_away_win_prob,
base_home_win_prob, base_draw_prob, base_away_win_prob,
adjusted_home_win_prob, adjusted_draw_prob, adjusted_away_win_prob,
top1_pick, second_pick, probability_gap, top1_label, confidence, risk_note,
prob_diff_home, prob_diff_draw, prob_diff_away,
model_version, feature_version, created_at
```

后续网页和用户调参模块应读取这些稳定字段。调参层只允许修改 `adjusted_*` 概率，不允许修改训练数据或模型权重。

## V1.1 预测解释规则

V1.1 只增强预测报告解释质量，不修改训练主逻辑，不实现真实用户调参，不提供投注建议。

### confidence

`confidence` 基于首选概率、第二概率和风险场景计算：

- `max_prob >= 0.55` 且 `max_prob - second_prob >= 0.18`：`high`
- `max_prob >= 0.45` 且 `max_prob - second_prob >= 0.10`：`medium`
- 其他：`low`
- 如果赛事是 `Friendly` / `友谊赛`，最高只给 `medium`
- 如果 `neutral=True`，最高只给 `medium`

### second_pick / probability_gap

- `second_pick` 是第二高概率对应的胜平负结果，取值仍为 `3/1/0`
- `probability_gap = top1_prob - second_prob`

### risk_note

`risk_note` 会按每场比赛生成中文风险说明，可能包含：

- 首选概率与第二概率的差距说明
- 友谊赛、预选赛、杯赛、中立场等赛事风险说明
- 模型概率与官方隐含概率的对比说明
- 未提供官方奖金时的市场概率对比缺失说明

`risk_note` 必须保留声明：`仅供概率研究，不承诺中奖或盈利。`

禁止输出 `必中`、`稳赚`、`保证中奖`、`推荐下注`、`稳胆`、`必买` 等投注承诺或诱导用语。

## V1 CLI 验证流程

项目提供两个 PowerShell 脚本，用于在 Windows 上重复验证 CLI MVP。

如果脚本执行被当前 PowerShell 策略拦截，先在当前窗口运行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

完整 smoke test：

```powershell
.\scripts\smoke_test_v1.ps1
```

该脚本会依次执行：

1. 显示 Python 版本。
2. 运行 `python -m unittest discover -s tests -v`。
3. 运行 `python -m compileall src tests`。
4. 同步或更新 `openfootball/internationals`。
5. 导入真实国家队历史数据到 `data/processed/national_matches.jsonl`。
6. 训练 `models/national`。
7. 回测并输出到 `reports/backtests`。

样例竞彩预测：

```powershell
.\scripts\predict_sample.ps1
```

该脚本使用 `data/raw/lottery_fixtures/sample_issue.csv`，读取已训练的 `models/national`，并在 `reports/predictions` 下生成：

- `predictions.csv`
- `predictions.json`
- `predictions.md`

验证时重点检查：

- 单元测试是否全部 OK。
- `import-history` 是否保留约 49,000 场国家队比赛。
- `train` 是否生成 `models/national` 下的模型状态文件。
- `backtest` 是否输出 Top1 Accuracy、Log Loss、Brier Score。
- `predict` 是否生成 CSV / JSON / Markdown。
- 预测结果里 `base_*` 和 `adjusted_*` 是否都存在。
- V1 中 `adjusted_*` 是否等于 `base_*`。
- 每场三项概率相加是否接近 1。

## V1.2 赛后结果录入与结算

V1.2 新增 `settle` 命令，用于把预测结果和赛后比分合并，评估预测表现。赛果只用于结算评估，不会回写训练数据，也不会触发模型重训。

赛果 CSV 示例：

```csv
issue_id,match_id,home_score,away_score,result_status,notes
202606,001,1,2,final,sample away win
```

必填列：

- `issue_id`
- `match_id`
- `home_score`
- `away_score`

可选列：

- `result_status`
- `notes`

`issue_id` 和 `match_id` 会始终按字符串读取和匹配，前导 `0` 会被保留。`home_score` / `away_score` 必须是非负整数。比分会转换为实际赛果：

- 主队进球更多：`actual_result = 3`
- 双方进球相同：`actual_result = 1`
- 客队进球更多：`actual_result = 0`

运行结算：

```powershell
python -m sporttery_national.cli settle --predictions reports/predictions/predictions.csv --results data/raw/results/sample_results.csv --output reports/settlements
```

输出文件：

- `reports/settlements/settlements.csv`
- `reports/settlements/settlements.json`
- `reports/settlements/settlements.md`
- `reports/settlements/settlement_summary.json`

如果预测文件中存在某场比赛，但赛果 CSV 中缺少对应的 `issue_id + match_id`，`settle` 会直接失败并列出缺失 key，不生成部分结算报告。predictions 和 results 内部也都会检查 `issue_id + match_id` 是否唯一；重复 key 会直接报错。

核心指标：

- `Top1 Accuracy`：`top1_pick == actual_result` 的比例。
- `Log Loss`：`-log(max(actual_prob, 1e-15))`，其中 `actual_prob` 是实际赛果对应的预测概率。
- `Brier Score`：三分类 one-hot 形式的 `sum((p_i - y_i)^2)`，不除以类别数。
- `base` 使用模型原始概率 `base_*`。
- `adjusted` 使用调参后概率 `adjusted_*`。

当前 V1.2 仍不实现真实用户调参，因此 `adjusted_* == base_*`，`adjusted_hit == base_hit`。后续调参模块上线后，结算报告可直接比较 base 与 adjusted 的差异。

样例结算脚本：

```powershell
.\scripts\settle_sample.ps1
```

如果 `reports/predictions/predictions.csv` 不存在，先运行：

```powershell
.\scripts\predict_sample.ps1
```

本项目只提供概率研究和赛后评估，不提供投注建议，不承诺中奖或盈利。

## V1.3 回测诊断报告

V1.3 增强 `backtest` 输出，用于分析模型在国家队胜平负预测中的偏差和弱点。该功能只做模型诊断，不修改训练主逻辑，也不提供投注建议。

运行回测：

```powershell
python -m sporttery_national.cli backtest --data data/processed/national_matches.jsonl --model-dir models/national --output reports/backtests
```

输出文件：

- `reports/backtests/backtest_details.csv`：逐场回测明细，适合排查单场预测、概率、命中情况和错误样例。
- `reports/backtests/backtest_details.json`：逐场明细 JSON，便于后续程序读取。
- `reports/backtests/backtest_summary.json`：总体指标、分组指标、偏差诊断和校准分桶，供后续网页或调参模块读取。
- `reports/backtests/backtest_report.md`：人工复盘报告，包含混淆矩阵、分组表现、校准分桶和高置信错误样例。

重点指标：

- `draw_recall`：真实结果为平局时，模型 top1 也预测平局的比例，可用于判断模型是否低估平局。
- `draw_bias_diagnostics`：比较真实平局率、预测平局率和平均平局概率，辅助定位平局偏差。
- `prediction_bias`：比较真实结果分布和 top1 预测分布，查看主胜/平/客胜是否系统性偏移。
- `by_confidence`：按 high / medium / low 分组，判断 confidence 是否可靠。
- `calibration_bins`：按 top1 概率分桶，观察模型给出某个概率水平时的实际命中率。
- `recent_windows`：查看 2000 年以来、最近 10 年、最近 5 年的表现变化。

Markdown 报告中的 competition 分组只展示样本数较大的赛事，完整赛事表现以 `backtest_summary.json` 为准。

## V1.4 本地参数实验器

V1.4 新增 `adjust` 命令，用于在不修改 base 模型、不重训、不写回训练数据的前提下，对预测概率做本地后处理实验。它不是网页调参功能，也不开放给用户系统。

参数文件示例：

```json
{
  "experiment_name": "draw_plus_market_light",
  "draw_bias": 0.03,
  "upset_bias": 0.02,
  "market_weight": 0.20,
  "temperature": 1.05
}
```

参数含义：

- `experiment_name`：实验名称，必须是非空字符串。
- `draw_bias`：提高或降低平局概率，范围 `-0.10` 到 `0.10`。
- `upset_bias`：提高冷门方向概率，范围 `0.00` 到 `0.10`。
- `market_weight`：融合官方隐含概率，范围 `0.00` 到 `1.00`；odds 缺失时跳过并记录 note。
- `temperature`：概率温度缩放，范围 `0.70` 到 `1.50`；小于 1 更尖锐，大于 1 更平滑。

`apply_adjustment(base_probs, params, implied_probs)` 统一返回 `home/draw/away/note`。其中 `home/draw/away` 是归一化后的三项概率，`note` 只是逐场说明，不参与概率求和、范围检查或 top1 排序。

运行流程：

```powershell
.\scripts\predict_sample.ps1
.\scripts\adjust_sample.ps1
.\scripts\settle_adjusted_sample.ps1
```

也可以直接运行 CLI：

```powershell
python -m sporttery_national.cli adjust --predictions reports/predictions/predictions.csv --params configs/adjustment/sample_params.json --output reports/adjustments
```

输出文件：

- `reports/adjustments/adjusted_predictions.csv`
- `reports/adjustments/adjusted_predictions.json`
- `reports/adjustments/adjustment_summary.json`
- `reports/adjustments/adjustment_report.md`

`adjusted_predictions` 会保留原始 `base_*` 和原始 `top1_*` 字段，并新增 `adjusted_top1_pick`、`adjusted_top1_label`、`adjusted_second_pick`、`adjusted_probability_gap`、`adjusted_confidence` 等实验字段。`base_*` 永远不被覆盖。

`adjustment_report.md` 会统计 top1 改变场次、odds 缺失导致 `market_weight` 未生效的场次，以及 `avg_abs_home_shift`、`avg_abs_draw_shift`、`avg_abs_away_shift`、`avg_abs_prob_shift` 等平均概率变动幅度。`changed_picks` 只统计 `top1_pick != adjusted_top1_pick` 的比赛，概率改变但首选不变不会计入。

结算 adjusted 结果：

```powershell
python -m sporttery_national.cli settle --predictions reports/adjustments/adjusted_predictions.csv --results data/raw/results/sample_results.csv --output reports/settlements_adjusted
```

当 settlement 输入中存在 `adjusted_top1_pick` 时，必须同时存在可解析的 `adjusted_home_win_prob`、`adjusted_draw_prob`、`adjusted_away_win_prob`；否则直接失败。校验通过后，`adjusted_hit` 使用 adjusted top1 判断，`base_hit` 仍使用原始 `top1_pick`。这样可以比较 base vs adjusted。

短期 adjusted 表现更好不代表可以直接写回模型。V1.4 的定位是本地研究工具，用大量样本检验某种后处理策略是否稳定改善表现。

## 前端可读取输出文件

前端或后续网页模块优先读取 JSON 文件，Markdown 仅用于展示和人工复盘：

- `reports/predictions/predictions.json`：当期比赛预测结果。
- `reports/backtests/backtest_summary.json`：回测汇总、偏差诊断、分组指标和校准分桶。
- `reports/backtests/backtest_details.json`：逐场回测明细。
- `reports/settlements/settlements.json`：逐场赛后结算明细。
- `reports/settlements/settlement_summary.json`：赛后结算汇总。
- `reports/adjustments/adjusted_predictions.json`：参数实验后的逐场预测结果。
- `reports/adjustments/adjustment_summary.json`：参数实验汇总，适合前端结构化读取。
- `reports/adjustments/adjustment_report.md`：参数实验展示型报告，不建议作为结构化数据源。

JSON 类型约定：

- `issue_id` 和 `match_id` 始终为字符串，保留前导 0。
- 概率、odds、probability gap、Log Loss、Brier、Accuracy 等指标为 JSON number；缺失数值为 `null`。
- `top1_pick`、`second_pick`、`actual_result`、`adjusted_top1_pick`、`adjusted_second_pick` 等结果编码为 JSON number。
- 所有 JSON 输出禁止 `NaN`、`Infinity`、`-Infinity`；如出现非法浮点值，写出阶段会直接失败。
