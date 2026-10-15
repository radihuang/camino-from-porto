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
| `photos/01_Porto-Labruge/` 這類「數字_」開頭的資料夾 | **原始素材**，含 GPS，只留本機、不進版控 |
| `photos/<id>/` | 處理後的照片（長邊 1920px、已清 EXIF）；`thumbs/` 是縮圖 |
| `videos/<id>/` | 處理後的短片（720p、已清中繼資料）＋同名 `.jpg` 封面 |
| `data/basemap.json` | 地圖底圖（海岸線、河流、國界），由 `scripts/build_basemap.py` 產生，平常不用動 |

## 新增一段的內容

1. 原始照片和影片放進 `photos/03_Rates-Barcelos/`（資料夾名稱要「兩位數字_」開頭，才會被排除在版控外）
2. 處理：`uv run python scripts/prepare_media.py photos/03_Rates-Barcelos day03`
   會輸出到 `photos/day03/`、`videos/day03/`，並印出可以直接貼進 `.md` 的區塊；重跑會略過已處理的檔
3. 日記從 Heptabase 擷取：`uv run python scripts/import_journal.py day03`
   只讀不寫；會排除所有待辦項目（每天固定的「肯定／感恩／學習／故事」與私人待辦）。印出的是語音輸入原文，貼進 `.md` 前要整理錯字、刪掉不公開的內容（人名、對同伴的抱怨、健康細節）
4. 新增 `stages/day03.md`，格式照 `stages/day02.md`
5. 在 `data/stages.json` 把那一段的 `"ready": false` 改成 `true`
6. 檢查：`uv run python scripts/check_content.py`
7. `git add -A && git commit -m "Day 3 內容" && git push`

### Markdown 裡的四種特殊區塊

一般 Markdown 照常寫（`## 標題`、清單、**粗體**、`> 引言`），另外有四種用三個反引號包起來的區塊：

````markdown
```gallery
day03/IMG_1234.jpg | Barcelos 的中世紀石橋
day03/IMG_1240.jpg | 公雞
```

```video
day03/IMG_1250.mp4 | 市集
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
- `video`：手機拍的短片（幾秒到一兩分鐘），放在自己網站上。路徑從 `videos/` 後面開始寫。
- `youtube`：長影片用這個，每行一支，填 YouTube 網址裡 `v=` 後面那 11 個字元。影片建議上傳成「不公開」再貼 ID。
- `qa`：第一行 `Q:` 是問題；`狀態:` 填「已查證」會顯示綠色，其他（或不寫）一律顯示「未查證」。

## 地圖

- 底圖資料：Natural Earth 10m（公有領域）。要改地圖範圍才需要重跑：
  `uv run python scripts/build_basemap.py <放 natural-earth geojson 的資料夾>`
- 路線來自 OpenStreetMap 的朝聖之路路線（ODbL，頁尾已標註），由 `scripts/build_routes.py` 在路網上算每段的最短路徑，輸出 `data/routes.json`。
  腳本會把算出的公里數跟 `stages.json` 的計畫公里數比對，差超過 20% 會警告（目前 12 段都在 ±11% 內）。
  Porto 市區到 Matosinhos 這段 OSM 沒畫，是腳本裡 `MANUAL_PREFIX` 手動補的地標連線。
  重跑方式見腳本開頭的說明（要先用 Overpass API 下載路網）。
- 地圖上的站點座標在 `stages.json` 的 `places`，是各站實際經過的地標（教堂、古橋、廣場）。
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
| YouTube 影片沒出現 | 影片 ID 不是 11 個字元，整行會被略過。 |
| 原始照片被 commit 了 | 資料夾名稱不是「兩位數字_」開頭，沒被 `.gitignore` 排除。commit 前用 `git status` 確認只有 `photos/dayXX/`、`videos/dayXX/`。 |
| `prepare_media.py` 說略過某些檔 | 格式不認得（目前支援 jpg/jpeg/heic/png、mov/mp4/m4v）。 |
| Heptabase 擷取時報 `unable to open database` | Heptabase 資料庫位置不同。用環境變數指定：`HEPTA_DB=/路徑/hepta.db uv run python scripts/import_journal.py day03` |
| 改了 CSS／JS 但畫面沒變 | 瀏覽器快取。把 `index.html`／`stage.html` 裡的 `?v=` 後面的數字加 1。 |
| 推上 GitHub 後線上沒更新 | 到 repo 的 Actions 頁看 `pages build and deployment` 有沒有失敗；`.nojekyll` 不能刪。 |
