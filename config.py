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