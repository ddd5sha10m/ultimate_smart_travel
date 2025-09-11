'''
# config.py
"""
存放所有使用者可配置的參數。
"""
import os
from dotenv import load_dotenv

# 從 .env 檔案載入環境變數
load_dotenv()

# --- API 金鑰 ---
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    raise ValueError("請在 .env 檔案中設定 GOOGLE_MAPS_API_KEY")

# --- 使用者輸入 ---
# 欲規劃的地點清單
INPUT_LOCATIONS = [
    "安可鐘", "維也納聖彼得教堂", "德梅爾咖啡店", "聖斯德望主教座堂", "奧地利國家圖書館",
        "霍夫堡", "奧地利國會大廈", "Haus der Musik", 
        "Wien Museum", "卡爾教堂", 
        "美景宮", "Kunsthistorisches Museum Wien", "Naturhistorisches Museum Wien",
        "維也納市政廳",
        "百水公寓"
]

# 行程的起點與終點
ITINERARY_START_LOCATION = "smartments Wien Hauptbahnhof"
ITINERARY_END_LOCATION = "smartments Wien Hauptbahnhof"

# --- 演算法參數 ---
# 凝聚式分群的距離閾值 (公里)
DISTANCE_THRESHOLD_KM = 0.8 

# 步行時間半徑 (秒)，用於精煉群組
WALKING_TIME_LIMIT_SECONDS = 10 * 60

# 暴力窮舉法的上限，避免計算時間過長
BRUTE_FORCE_LIMIT = 9 

# 群組間的交通方式: "driving", "transit", "bicycling", "walking"
INTER_CLUSTER_TRAVEL_MODE = "transit"
'''
'''
# config.py (v3)
"""
存放所有使用者可配置的參數。
"""
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# --- API 金鑰 ---
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    raise ValueError("請在 .env 檔案中設定 GOOGLE_MAPS_API_KEY")

# --- 使用者輸入 ---
INPUT_LOCATIONS = [
    "安可鐘", "維也納聖彼得教堂", "德梅爾咖啡店", "聖斯德望主教座堂", "奧地利國家圖書館",
    "霍夫堡", "奧地利國會大廈", "Haus der Musik", 
    "Wien Museum", "卡爾教堂", 
    "美景宮", "Kunsthistorisches Museum Wien", "Naturhistorisches Museum Wien",
    "維也納市政廳", "百水公寓"
]
ITINERARY_START_LOCATION = "smartments Wien Hauptbahnhof"
ITINERARY_END_LOCATION = "smartments Wien Hauptbahnhof"

# --- [全新] 時間設定 ---
# 設定行程的開始與結束時間 (年, 月, 日, 時, 分)
TRIP_START_TIME = datetime(2025, 9, 11, 9, 0)  # 2025年9月11日 早上 9:00
TRIP_END_TIME = datetime(2025, 9, 13, 22, 0) # 2025年9月13日 晚上 10:00

# 每日行程的開始與結束時間 (24小時制)
DAY_START_HOUR = 9
DAY_END_HOUR = 22

# 每個景點的預計平均停留時間 (分鐘)
DEFAULT_STAY_DURATION_MINS = 90

# --- 演算法與交通參數 ---
DISTANCE_THRESHOLD_KM = 0.8
WALKING_TIME_LIMIT_SECONDS = 10 * 60
BRUTE_FORCE_LIMIT = 9

# 群組「之間」的交通方式
INTER_CLUSTER_TRAVEL_MODE = "driving" # 使用開車的

# [全新] 群組「內部」的交通方式
INTRA_CLUSTER_TRAVEL_MODE = "walking" # 群內用走路的
'''
# config.py (v4)
"""
存放所有使用者可配置的參數。
新增 PLANNING_MODE 來切換規劃模式。
"""
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# --- API 金鑰 ---
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    raise ValueError("請在 .env 檔案中設定 GOOGLE_MAPS_API_KEY")

# --- [全新] 規劃模式選擇 ---
# 'time_aware': 進行詳細的時間感知多日排程 (考慮營業時間、停留長度、自動分天)。
# 'location_only': 僅進行地點分群與最佳路徑排序 (不考慮時間與營業時間)。
PLANNING_MODE = 'location_only' # <--- 在這裡切換你想要的功能！

# --- 使用者輸入 ---
INPUT_LOCATIONS = [
    "安可鐘", "維也納聖彼得教堂", "德梅爾咖啡店"
    , "聖斯德望主教座堂", "奧地利國家圖書館",
    "霍夫堡", "奧地利國會大廈", "Haus der Musik",
    "維也納博物館", "卡爾教堂", 
    "美景宮", "Kunsthistorisches Museum Wien", "Naturhistorisches Museum Wien",
    "維也納市政廳", "百水公寓"
]
ITINERARY_START_LOCATION = "smartments Wien Hauptbahnhof"
ITINERARY_END_LOCATION = "smartments Wien Hauptbahnhof"

# --- 時間設定 (僅在 'time_aware' 模式下生效) ---
TRIP_START_TIME = datetime(2025, 9, 11, 9, 0)
TRIP_END_TIME = datetime(2025, 9, 13, 22, 0)
DAY_START_HOUR = 9
DAY_END_HOUR = 22
DEFAULT_STAY_DURATION_MINS = 90

# --- 演算法與交通參數 ---
DISTANCE_THRESHOLD_KM = 0.8
WALKING_TIME_LIMIT_SECONDS = 10 * 60
BRUTE_FORCE_LIMIT = 9
INTER_CLUSTER_TRAVEL_MODE = "transit"
INTRA_CLUSTER_TRAVEL_MODE = "walking"