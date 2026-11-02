# The Daily Brief · 英文财经早报（云端自动版）

每天早上 7:00（北京时间）自动抓取财经快讯 → 精修英文 → 生成神经语音广播 → 发布网页。
无需自己的电脑开机，手机也能打开看。

---

## 部署步骤（大约 5 分钟，只需做一次）

### 1. 建仓库
1. 打开 https://github.com/new
2. Repository name 填 `daily-brief`
3. 选 **Public**（免费版 Pages 需要公开仓库；内容是公开可查的）
4. 点 **Create repository**

### 2. 上传文件
1. 在新建的仓库页面点 **uploading an existing file**
2. 把本文件夹里的**所有内容**（包括 `.github` 这个隐藏文件夹、`data`、`scripts`、`index.html`）整个拖进浏览器
3. 点 **Commit changes**

> 如果拖拽 `.github` 不成功（Windows 上以 `.` 开头的文件夹容易被隐藏），
> 用页面 **Add file → Create new file**，文件名填 `.github/workflows/daily.yml`，
> 再把本文件夹里同名文件的内容整段粘进去，提交即可。

### 3. 开启网页发布
1. 仓库 → **Settings** → 左侧 **Pages**
2. **Source** 选 **GitHub Actions**（不要选 Deploy from a branch）
3. 记下页面顶部会显示的网址：`https://<你的用户名>.github.io/daily-brief/`

### 4. 立刻跑一次验证
1. 仓库 → **Actions** → 左侧 **Daily Brief** → 右侧 **Run workflow** → 绿色按钮
2. 等 15-25 分钟（首次要下载 315MB 语音模型，会久一点）
3. 跑完后打开第 3 步的网址，能看到当天内容就成功了

### 5. 装成手机 App（可选，1 分钟）
页面已内置 PWA，可直接装到手机桌面，全屏无地址栏，断网也能打开、听过的广播离线可放：

- **安卓 / 微信内**：打开网址 → 右上角菜单 → **添加到主屏幕**
- **iPhone Safari**：打开网址 → 底部 **分享** → **添加到主屏幕**

> 必须用 Safari（iPhone）或 Chrome / Edge（安卓）打开，微信里点"添加到桌面"也可用。
> 图标是深藏青底 + DB 字样，装好后和真 App 一样。

---

## 这个文件夹里都有什么

| 文件 / 文件夹 | 作用 |
|---|---|
| `index.html` | 页面本体（报纸风，中英对照 + 广播播放器） |
| `manifest.webmanifest`、`sw.js`、`icons/` | 手机装成 App 所需（PWA 配置 / 离线缓存 / 图标） |
| `data/news.json` `data/news.js` | 新闻数据，每天自动更新 |
| `data/audio/日期/` | 每天生成的广播 MP3 |
| `scripts/` | 抓新闻、精修英文、生成音频的脚本 |
| `.github/workflows/daily.yml` | 定时任务（每天 7:00 自动跑全套） |

---

## 英文质量：配置 AI 精修（强烈建议）

不做这一步，英文是机器翻译的，专有名词容易出错（比如把 ING 译错）。
配一个便宜的模型 API 即可，一天成本约几分钱：

1. 去 https://platform.deepseek.com 注册并充值（10 元能跑很久），创建 API Key
2. 仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
   - Name: `LLM_API_KEY`
   - Secret: 粘贴你的 key
3. 想用别的模型（OpenAI 等兼容接口）再加两个 **Repository variables**：
   - `LLM_BASE_URL`：如 `https://api.openai.com/v1`
   - `LLM_MODEL`：如 `gpt-4o-mini`

没配 key 也能正常出报，只是英文是机翻底稿。

---

## 日常怎么用

| 想做的事 | 怎么做 |
|---|---|
| 在家看最新一期 | 直接打开 `https://<用户名>.github.io/daily-brief/` |
| 手机上随时手动更新 | GitHub 手机 App → 仓库 → Actions → Daily Brief → Run workflow |
| 看某天跑失败了没 | 仓库 → Actions，红色叉号点进去看日志 |
| 改页面样式 | 直接改 `index.html`，提交后自动重新发布 |

## 说明

- **定时延迟**：GitHub 的定时任务高峰期可能延迟 5-30 分钟，属正常
- **时间**：cron 写的是 UTC 23:00，对应北京时间次日 07:00
- **保存期**：新闻与音频保留最近 7 期，更早的会自动清理
- **公开性**：Public 仓库意味着代码和内容都公开，介意的话改用私有仓库 + 付费方案
- **国内访问**：`github.io` 在国内有时偏慢，可以正常打开只是加载慢一点

---

## 出问题怎么办

| 现象 | 原因与处理 |
|---|---|
| 打开网址 404 | Settings → Pages 里 Source 没选 **GitHub Actions**；或第一次 Actions 还没跑完 |
| 页面显示"暂无数据" | 说明 `data/` 没上传成功，补传 `data` 文件夹再跑一次 Actions |
| Actions 里没有 Daily Brief 这个任务 | `.github/workflows/daily.yml` 没上传（隐藏文件夹最常漏），按第 2 步的备用办法手动新建 |
| Actions 红色叉 | 点进去看日志，通常是 pip 安装或模型下载超时，重新 Run workflow 一次即可 |
| 能看文字但点广播没声音 | 检查 `data/audio/` 是否有当天的 mp3；手机需先点一次播放（浏览器要求用户交互） |
| 英文有奇怪的专有名词 | 没配 `LLM_API_KEY`，配一下就会由 AI 精修（见上） |
