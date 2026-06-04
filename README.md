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

## 数据来源

历史国家队赛果建议使用 `openfootball/internationals` 一类公开国家队历史比赛数据。导入器支持递归读取 `.csv` 和简单 Football.TXT 风格 `.txt` 文件，并会排除 U23、Olympic team、B team、XI、Select、All Stars 等非成年国家队记录。

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
python -m sporttery_national.cli import-history --input data/raw/internationals --output data/processed/national_matches.parquet
python -m sporttery_national.cli train --data data/processed/national_matches.parquet --model-dir models/national
python -m sporttery_national.cli backtest --data data/processed/national_matches.parquet --model-dir models/national --output reports/backtests
python -m sporttery_national.cli predict --fixtures data/raw/lottery_fixtures/current_issue.csv --model-dir models/national --output reports/predictions
python -m sporttery_national.cli teams --query 德国
```

当前实现仅使用 Python 标准库。若安装 `pandas + pyarrow`，后续可以把存储层替换为真正 Parquet；当前 `.parquet` 路径使用内部 JSONL 记录格式，CLI 读写保持稳定。

## 预测输出字段

输出字段固定为：

```text
issue_id, match_id, date, kickoff, competition, venue, neutral,
home_team_raw, away_team_raw, home_team, away_team,
odds_home, odds_draw, odds_away,
implied_home_win_prob, implied_draw_prob, implied_away_win_prob,
base_home_win_prob, base_draw_prob, base_away_win_prob,
adjusted_home_win_prob, adjusted_draw_prob, adjusted_away_win_prob,
top1_pick, top1_label, confidence, risk_note,
prob_diff_home, prob_diff_draw, prob_diff_away,
model_version, feature_version, created_at
```

后续网页和用户调参模块应读取这些稳定字段。调参层只允许修改 `adjusted_*` 概率，不允许修改训练数据或模型权重。
