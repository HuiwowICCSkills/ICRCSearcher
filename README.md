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
