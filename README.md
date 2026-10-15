# 從 Porto 走到世界盡頭

2026 葡萄牙之路（Caminho Português）的對外紀錄網站：一張手繪風地圖，每一段路有自己的頁面，放照片、影片、去過的地方，以及路上問 AI 的問題。

純 HTML / CSS / JS，沒有框架、沒有建置步驟，放在 GitHub Pages。

## 本機預覽

```bash
cd ~/Downloads/10_Project/20261015_camino-from-porto
python3 -m http.server 8731
```

瀏覽器開 <http://127.0.0.1:8731/>。直接雙擊 `index.html` 打不開（瀏覽器不允許 `file://` 讀取資料檔），一定要透過上面的伺服器。

## 檔案在哪

| 路徑 | 內容 |
| --- | --- |
| `data/stages.json` | 每一段的基本資料：日期、標題、公里數、終點站、`ready`（是否已整理） |
| `stages/<id>.md` | 每一段的內容，一段一個檔 |
| `photos/<id>/` | 照片（建議長邊 1920px）；`photos/<id>/thumbs/` 放縮圖，沒有縮圖會自動用原圖 |
| `data/basemap.json` | 地圖底圖（海岸線、河流、國界），由 `scripts/build_basemap.py` 產生，平常不用動 |

## 新增一段的內容

1. 照片放進 `photos/day03/`（例如 `photos/day03/IMG_1234.jpg`）
2. 新增 `stages/day03.md`，格式照 `stages/day01.md`
3. 在 `data/stages.json` 把那一段的 `"ready": false` 改成 `true`
4. 檢查：`uv run python scripts/check_content.py`
5. `git add -A && git commit -m "Day 3 內容" && git push`

### Markdown 裡的三種特殊區塊

一般 Markdown 照常寫（`## 標題`、清單、**粗體**、`> 引言`），另外有三種用三個反引號包起來的區塊：

````markdown
```gallery
day03/IMG_1234.jpg | Barcelos 的中世紀石橋
day03/IMG_1240.jpg | 公雞
```

```youtube
dQw4w9WgXcQ | 過橋那一段
```

```qa
Q: 巴塞洛斯公雞的傳說是什麼？
狀態: 已查證
答案寫在這裡，可以用 **Markdown**，可以很多段。
```
````

- `gallery`：每行一張照片，`|` 後面是說明（可省略）。路徑從 `photos/` 後面開始寫。
- `youtube`：每行一支，填 YouTube 網址裡 `v=` 後面那 11 個字元。影片建議上傳成「不公開」再貼 ID。
- `qa`：第一行 `Q:` 是問題；`狀態:` 填「已查證」會顯示綠色，其他（或不寫）一律顯示「未查證」。

## 地圖

- 底圖資料：Natural Earth 10m（公有領域）。要改地圖範圍才需要重跑：
  `uv run python scripts/build_basemap.py <放 natural-earth geojson 的資料夾>`
- 路線目前是**示意**：Day 1、Day 2 有手動加中途點（`stages.json` 的 `via`），其他段是站與站的連線。之後用 Apple 健身匯出的 GPX 取代（待做）。
- `mode`：`walk` 實線、`bus` 虛線、`stay` 不畫線。

## 測試

```bash
uv run pytest -q
```

測的是 `scripts/check_content.py`：除了檢查真實內容，也用暫存資料確認它真的抓得到缺照片、影片 ID 錯、`ready` 卻沒有 `.md`、站點不存在這幾種錯。

## 常見錯誤與處理

| 症狀 | 原因與處理 |
| --- | --- |
| 打開是空白頁 | 用了雙擊開檔。改用上面的 `python3 -m http.server`。 |
| 某一段顯示「內容載入失敗（…HTTP 404）」 | `stages.json` 標了 `ready: true`，但 `stages/<id>.md` 不存在或檔名拼錯。跑 `check_content.py` 會列出來。 |
| 照片是空白格子 | 路徑寫錯或檔案沒放進去。`check_content.py` 會列出找不到的照片。路徑只能用英數、`-`、`_`、`.`、`/`，不能有空白或中文。 |
| 影片沒出現 | 影片 ID 不是 11 個字元，整行會被略過。 |
| 改了 CSS／JS 但畫面沒變 | 瀏覽器快取。把 `index.html`／`stage.html` 裡的 `?v=1` 改成 `?v=2`。 |
| 推上 GitHub 後線上沒更新 | 到 repo 的 Actions 頁看 `pages build and deployment` 有沒有失敗；`.nojekyll` 不能刪。 |
