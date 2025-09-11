智慧行程規劃器 (Smart Itinerary Planner)
這是一個智慧化、時間感知的旅遊行程規劃工具。它能根據使用者輸入的地點清單、旅遊時間以及交通偏好，自動進行地理分群、路徑優化，並考慮地點的營業時間，最終生成一份視覺化的多日互動式地圖行程表。

✨ 核心功能
地理位置分群 (Geographic Clustering)：使用 Scikit-learn 的凝聚式分群演算法，自動將鄰近的地點結合成適合一同遊覽的「區域」或「群組」。

多日行程排程 (Multi-Day Scheduling)：能根據使用者設定的總旅遊天數、每日的起訖時間，自動將行程分配到不同天，解決單日無法玩完所有景點的問題。

時間感知規劃 (Time-Aware Planning)：

整合營業時間：在規劃時會主動檢查地點在預計抵達時間是否營業，避免「撲空」。

動態時間模擬：會計算交通時間與景點停留時間，以時間軸的方式推進，產生真實可行的時間表。

客製化交通模式 (Configurable Travel Modes)：使用者可以自由設定「群組之間」（例如：搭乘大眾運輸）和「群組內部」（例如：步行）的交通方式。

互動式地圖視覺化 (Interactive Map Visualization)：使用 Folium 函式庫，將最終行程輸出成一個 itinerary_map.html 檔案。地圖包含：

每日行程路徑。

每個群組以不同顏色區分。

包含停留順序、預計抵達時間的地點標記。

可點擊的地點彈出視窗，顯示評分、地址等詳細資訊。

方便總覽的側邊欄。

🛠️ 技術棧 (Tech Stack)
程式語言: Python 3

主要函式庫:

googlemaps: 用於與 Google Maps Platform APIs 互動 (Places, Directions, Distance Matrix, Geocoding)。

scikit-learn: 用於執行地理位置分群演算法。

folium: 用於建立與視覺化互動式 HTML 地圖。

numpy: 用於進行地理座標的數學運算。

haversine & polyline: 用於地理距離計算與路徑解碼。

python-dotenv: 用於管理環境變數 (API 金鑰)。

📂 專案結構
我們的專案採用了模組化的結構，職責分明，易於維護與擴充。

.
├── .env                  # 儲存你的 Google Maps API 金鑰
├── config.py             # 所有使用者設定都在這裡！
├── google_api_service.py # 封裝所有與 Google API 的互動
├── planner.py            # 核心規劃演算法 (分群、多日行程模擬)
├── visualizer.py         # 負責產生 Folium 互動地圖
├── main.py               # 程式主入口，負責串連所有模組
└── itinerary_map.html    # (執行後產生的輸出檔案)
🚀 安裝與設定
請依照以下步驟來設定與執行專案。

1. 前置需求
確認你已安裝 Python 3.8 或更新版本。

一個有效的 Google Cloud Platform 帳號。

2. 取得 Google Maps API 金鑰
本專案需要用到以下四個 Google Maps APIs，請確保你已在你的 GCP 專案中啟用它們，並取得一組 API 金鑰。

Places API

Directions API

Distance Matrix API

Geocoding API

3. 設定專案
Bash

# 1. (可選) 複製專案
# git clone https://your-repository-url.git
# cd ultimate_smart_travel

# 2. 建立並啟用 Python 虛擬環境
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate

# 3. 安裝必要的函式庫
pip install googlemaps scikit-learn folium numpy haversine polyline python-dotenv

# 4. 建立 API 金鑰設定檔
# 在專案根目錄下建立一個名為 .env 的檔案，並填入以下內容：
GOOGLE_MAPS_API_KEY="在此貼上你的API金鑰"
⚙️ 如何使用
設定你的旅程:
打開 config.py 檔案，這是你唯一的設定中心。你可以在這裡修改：

INPUT_LOCATIONS: 你想去的景點清單。

ITINERARY_START_LOCATION & ITINERARY_END_LOCATION: 整個旅程的起點與終點。

TRIP_START_TIME & TRIP_END_TIME: 整個旅程的開始與結束日期時間。

DAY_START_HOUR & DAY_END_HOUR: 每日行程的活動時間。

DEFAULT_STAY_DURATION_MINS: 每個景點的預計停留時間。

INTER_CLUSTER_TRAVEL_MODE & INTRA_CLUSTER_TRAVEL_MODE: 設定交通方式。

執行規劃器:
確認你的虛擬環境已啟用，然後在終端機中執行：

Bash

python main.py
查看結果:

終端機: 程式會依序印出每個執行步驟的 log，並在最後顯示每日的行程時間表摘要。

互動地圖: 程式執行完畢後，專案資料夾中會產生一個 itinerary_map.html 檔案。請用你的網頁瀏覽器打開它，即可看到視覺化的完整行程！