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
