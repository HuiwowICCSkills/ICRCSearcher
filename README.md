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

## 实测效果（2026-11-12）

以下命令与结果来自本机 `~/.codex/skills/ICRCSearcher` 的实网运行；检索日期 2026-11-12（Asia/Shanghai），输出为该次运行实际返回的 JSON 报告。

```powershell
$icrc = "$env:USERPROFILE\.codex\skills\ICRCSearcher\run.ps1"
& $icrc search 'genocide' --database ihl --date-from 2000-01-01 --date-to 2020-12-31 --limit 5
```

- 状态：`ok`；各索引计数为 `tspc_treaty_search=4`、`tspc_article_search=30`、`tspc_commentary_search=219`、`tspc_participant_search=291`、`np_search=148`，合计 `total=692`；本次返回 20 条（每索引 5 条，去重前）。
- 日期过滤：只作用于 `np_search`（国家实践）；`date_range.applied_to` 已标明。其他国家实践无日期时为 222 条，加 2000–2020 后为 148 条。
- 代表性结果：

| 题名 | 索引 | 链接 |
| --- | --- | --- |
| Convention on the Prevention and Punishment of the Crime of Genocide, 9 December 1948. | tspc_treaty_search | https://ihl-databases.icrc.org/en/ihl-treaties/genocide-conv-1948 |
| Statute of the International Criminal Tribunal for Rwanda, 8 November 1994 | tspc_treaty_search | https://ihl-databases.icrc.org/en/ihl-treaties/ictr-statute-1994 |
| Agreement between the United Nations and the Government of Sierra Leone and Statute of the Special Court for Sierra Leone, 16 January 2002 | tspc_treaty_search | https://ihl-databases.icrc.org/en/ihl-treaties/scsl-agreement-2002 |

> 说明：`total=692` 是各索引服务端计数之和，不是去重后的案件数；搜索结果和 `snippet` 来自记录自身字段，不是另行取得的全文。条约、评注、国家实践和习惯法规则必须分别标注。
