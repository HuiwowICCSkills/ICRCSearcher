# ICRCSearcher 部署指引

独立检索 ICRC 国际人道法数据库（条约、条文评注、国家实践）和习惯国际人道法规则/实践。只访问 `ihl-databases.icrc.org`。

仓库：<https://github.com/HuiwowICCSkills/ICRCSearcher>（公开）。

## 1. 环境

Python 3.10+，依赖 `requests`、`beautifulsoup4`、`pypdf`；无需浏览器、Cookie 或机构登录。

## 2. 安装

```powershell
git clone https://github.com/HuiwowICCSkills/ICRCSearcher.git "$env:USERPROFILE\.codex\skills\ICRCSearcher"
python -m pip install -r "$env:USERPROFILE\.codex\skills\ICRCSearcher\requirements.txt"
```

## 3. 自检

```powershell
& "$env:USERPROFILE\.codex\skills\ICRCSearcher\run.ps1" doctor
```

`doctor` 分别探测 `tspc_treaty_search` 和 `cihl_rule_search`；`ok: true` 表示至少一个索引可用。

## 4. 使用

```powershell
$icrc = "$env:USERPROFILE\.codex\skills\ICRCSearcher\run.ps1"
& $icrc search 'genocide' --database all --limit 5 --out './icrc.json'
& $icrc search 'superior responsibility' --database ihl --limit 5
& $icrc fetch 'https://ihl-databases.icrc.org/en/...' --out './record.json' --text-out './record.txt'
```

## 5. 排错

| 现象 | 处理 |
| --- | --- |
| `command responsibility` 全部 403 | ICRC 的查询级安全策略，不是 Cloudflare；适配器会自动做词项交集，或改用 `superior responsibility`、单词检索 |
| `status=partial` | 部分索引失败；读 `warnings`，不要把部分结果当全库结果 |
| `unavailable-or-incomplete` | 本次没有取得任何记录，不能写成“没有资料” |
| 索引计数差异很大 | 不同索引口径不同；`total` 只是服务端计数之和，不是去重案件数 |

## 6. 边界

本 skill 不做 ICRC 本地 Rules/Practice 书籍的 PDF 回退；需要旧版书籍文本时使用 `LegalToolsSearcher` 并注明版次。ICRC 评注和国家实践是次级材料，条约原文和习惯法规则需分别标注。

## 实测效果（2026-11-09）

以下命令与结果来自本机 `~/.codex/skills/ICRCSearcher` 的实网运行；检索日期 2026-11-09（Asia/Shanghai），输出为该次运行实际返回的 JSON 报告。

```powershell
& .\run.ps1 search 'command responsibility' --database all --limit 5
```

- 状态：`ok`；服务端/索引报告 `total = 15`；本次返回 5 条。
- 该 `total` 是多个索引服务端计数之和，按索引拆分：`tspc_article_search = 1`、`tspc_commentary_search = 3`、`np_search = 5`、`cihl_rule_search = 6`（其余索引为 0），不是去重后的案件或文书数。
- 代表性结果：

| 题名 | 类型 / 日期 | 链接 |
| --- | --- | --- |
| Article 28 - Responsibility of commanders and other superiors | retrieved_metadata；无日期字段 | https://ihl-databases.icrc.org/en/jsonapi/paragraph/treaty_content/1e0950f9-dfa7-43e0-b495-b0f11a49ede3?resourceVersion=id%3A1594639 |
| tspc_commentary_search: 15e0aaa0-3b8f-4ccd-a366-ff75249a3f32 | retrieved_metadata；无日期字段 | https://ihl-databases.icrc.org/en/jsonapi/paragraph/treaty_commentary/15e0aaa0-3b8f-4ccd-a366-ff75249a3f32?resourceVersion=id%3A2830178 |
| tspc_commentary_search: dafe76c4-68a4-4b9a-97e9-48db281ff4df | retrieved_metadata；无日期字段 | https://ihl-databases.icrc.org/en/jsonapi/paragraph/treaty_commentary/dafe76c4-68a4-4b9a-97e9-48db281ff4df?resourceVersion=id%3A2846501 |
| Ford v. Garcia (re. crimes against US citizens committed in El Salvador), Court of Appeals, Eleventh Circuit, 30 April 2002 | retrieved_metadata；无日期字段 | https://ihl-databases.icrc.org/en/national-practice/ford-v-garcia-re-crimes-against-us-citizens-committed-el-salvador-court-appeals |

> 说明：命中横跨条约条文索引（Article 28 原文条目）、条约评注索引（3 个评注段落）和国家实践索引（含 Ford v. Garcia 一国司法实践条目），说明 `--database all` 确实在多个索引中生效、而不是单库检索。但返回行是 ICRC Drupal JSON:API 的段落级记录（`result_type = retrieved_metadata`，`content_scope`：ICRC Drupal JSON:API record matched term-by-term and intersected locally; not a full-text judgment），只代表该段落被词项匹配，本轮没有读取段落正文；两个 `tspc_commentary_search` 行为适配器输出的记录标识而非可读题名，引用前须用 `fetch` 打开链接确认评注所属条文与段落。评注与国家实践属于次级材料，条约原文和习惯法规则须分别标注。