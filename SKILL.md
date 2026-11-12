---
name: ICRCSearcher
description: 独立检索 ICRC 国际人道法数据库（条约、条文评注、国家实践）与习惯国际人道法规则/实践；走 ihl-databases.icrc.org 的 Drupal JSON:API，支持多索引检索和记录正文读取。
---

# ICRCSearcher

> **`<skill-dir>`** = 本 SKILL.md 所在目录。核心脚本为 `<skill-dir>/scripts/icrc_search.py`；Windows 用 `<skill-dir>/run.ps1`，macOS/Linux 用 `<skill-dir>/run.sh`。部署与排错见 [README.md](README.md)。

这个 skill 只做 `ihl-databases.icrc.org` 一个站点，覆盖两组数据库：

| `--database` | 索引 |
| --- | --- |
| `ihl` | `tspc_treaty_search`、`tspc_article_search`、`tspc_commentary_search`、`tspc_participant_search`、`np_search` |
| `customary` | `cihl_rule_search`、`cihl_practice_search` |
| `all`（默认） | 以上全部 |

## 命令

```powershell
# 检索全部 ICRC 索引
& '<skill-dir>/run.ps1' search 'genocide' --database all --limit 5 --out './icrc-search.json'

# 只查条约/评注/国家实践
& '<skill-dir>/run.ps1' search 'superior responsibility' --database ihl --limit 5

# 只查习惯国际人道法规则与实践
& '<skill-dir>/run.ps1' search 'distinction' --database customary --limit 5

# 国家实践按日期范围收窄（仅 np_search）
& '<skill-dir>/run.ps1' search 'genocide' --database ihl --date-from 2000-01-01 --date-to 2020-12-31 --limit 5

# 读取一条记录或页面
& '<skill-dir>/run.ps1' fetch 'https://ihl-databases.icrc.org/en/...' --out './icrc-record.json' --text-out './icrc-record.txt'

# 部署自检
& '<skill-dir>/run.ps1' doctor
```

通用参数：`--out`、`--cache`、`--cache-ttl`、`--offline`、`--timeout`。`search` 另有 `--database`、`--lang`（默认 `en`）、`--limit`（每个索引 1..50）、`--offset`、`--date-from`、`--date-to`、`--no-term-fallback`；`fetch` 另有 `--text-out`。

## 结果边界

- `search` 返回每条记录的 `index`、`id`、`title`、`url` 和 Drupal `attributes`；`snippet` 只从记录自身的文本字段截取，**不是**另行取得的全文。
- `counts` 是每个索引服务端报告的命中数；`total` 是这些计数之和（能取到时）。不同索引的计数口径不完全相同，不能把 `total` 当作去重后的案件数。
- `--date-from`/`--date-to` 目前只作用于 `np_search`（国家实践），因为这是实测可用的 JSON:API 日期过滤；其他索引仍按关键词返回。报告里的 `date_range.applied_to` 会说明这一点。站点的 Search 页面另有“All/Any/Exact Search Terms”、States、Languages、1899–2026 日期等前端筛选；JSON:API 没有与这些 UI 控件一一对应的单值参数，不能假装已经复刻。
- ICRC 的 `filter[fulltext]` 对某些多词短语（例如 `command responsibility`）会触发站点自己的查询级 403/503，这不是 Cloudflare。适配器在**全部**索引都因该原因失败时，会退化为按词分别检索并做有界交集，结果标为 `icrc-token-intersection`，并明确说明不是站点自己的短语检索；可用 `--no-term-fallback` 关闭。
- `status=partial` 表示部分索引成功、部分失败；`unavailable-or-incomplete` 表示本次没有取得任何记录，不能写成“没有资料”。先换单词或替代表述（例如 `superior responsibility`），再判断数据库是否不可用。
- 习惯国际人道法的本地 Rules/Practice 书籍回退不在本 skill 内；需要旧版书籍文本时使用 `LegalToolsSearcher`，并注明版次和“不是最新线上实践”。
- ICRC 页面和记录是条约、评注、国家实践或习惯法材料；输出时区分条约原文、评注、国家实践和习惯法规则，不要把评注当条约条文。

## 参考

- 2026-11-09 实测：7 个 JSON:API 索引、`meta.count`、`command responsibility` 的 403 与词项回退：[references/icrc-search.md](references/icrc-search.md)
- 部署、环境与排错：[README.md](README.md)
