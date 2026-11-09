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
