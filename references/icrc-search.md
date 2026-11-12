# ICRC 检索实测记录（2026-11-09）

## 端点

`https://ihl-databases.icrc.org/{lang}/jsonapi/index/{index}`

参数：`page[limit]`、`page[offset]`、`filter[fulltext]`

请求头：`Accept: application/vnd.api+json`、浏览器式 UA。

## 索引

| 组 | 索引 |
| --- | --- |
| `ihl` | `tspc_treaty_search`、`tspc_article_search`、`tspc_commentary_search`、`tspc_participant_search`、`np_search` |
| `customary` | `cihl_rule_search`、`cihl_practice_search` |

## 2026-11-09 实测

`genocide --database all --limit 2`：

| 索引 | `meta.count` |
| --- | --- |
| tspc_treaty_search | 4 |
| tspc_article_search | 30 |
| tspc_commentary_search | 219 |
| tspc_participant_search | 291 |
| np_search | 222 |
| cihl_rule_search | 21 |
| cihl_practice_search | 1,658 |

合计 `total=2445`，返回 13 条（每个索引 2 条，去重前）。

`superior responsibility --database ihl --limit 2` → `total=216`，正常。

## 重要异常：`command responsibility`

- 直接请求七个索引全部返回 **HTTP 403**，响应是 ICRC 自己的 1,250 字节 HTML 安全页，不是 Cloudflare challenge。
- 单词 `command`、`responsibility` 分别可正常返回；`superior responsibility` 也可正常返回。
- 适配器因此在全部索引都失败且查询含多个词时，按词分别检索并做有界交集，结果标为 `icrc-token-intersection`；实测 `command responsibility --database ihl --limit 3` 得到 `total=9`、`status=ok`，并保留原始 403 warnings。

## 记录结构

- `data[].id`：记录 id
- `data[].attributes`：`title`、`field_short_title`、`field_treaty_content_title`、`field_np_english_title`、`field_path`、`body` / `field_cihl_content` 等
- `meta.count`：该索引服务端计数
- `links.self.href`：记录 API URL（部分为 `http://`，需改 HTTPS）

## 边界

- `total` 是各索引计数之和，不是去重案件数。
- 本地 Rules/Practice 书籍回退不在本 skill；需要时用 `LegalToolsSearcher`。

## Search 页面的高级筛选（2026-11-12 浏览器核对）

`https://ihl-databases.icrc.org/en/search` 是一个 React 表单，页面文案和控件包括：

- 关键词输入 + Search type：`All Search Terms` / `Any Search Term` / `Exact Search Term`
- 数据库单选：Treaties, States Parties and Commentaries；Customary IHL（Rules / Practice）；National Practice
- Filters：States、Languages（English 等）、Dates（1899–2026 滑块）

前端把表单编码为
`/en/search/search-results?language=en&keyword=<词>&keywordType=all|any|exact&from=<年>&to=<年>&order=ASC&countries=<ISO代码,...>&tspc=...&cihl=...&npc=...&npt=...`。
直接请求该 URL 会被 ICRC security policy 拦截（`Request Not Compliant`），所以当前 CLI 继续走 JSON:API；日期过滤只对 `np_search` 实测有效（`filter[date_lower]` / `filter[date_upper]`，`path=date`）：`genocide` 222 条 → 2000–2020 年 148 条。

`command responsibility` 在 JSON:API 的 `filter[fulltext]` 和带引号形式都会触发站点级 403；这是查询级策略，不是网络失败。要使用站点的 All/Any/Exact 语义、States 或 Languages，需在真实浏览器中操作 Search 页，不能声称 JSON:API 已支持这些控件。
