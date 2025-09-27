# config.py (v5 - More Inclusive Settings)
"""
存放所有使用者可配置的參數。
調整參數以確保更多地點被包含在行程中。
"""
import os
from dotenv import load_dotenv
from datetime import datetime, time, timedelta

load_dotenv()

# --- API 金鑰 ---
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    raise ValueError("請在 .env 檔案中設定 GOOGLE_MAPS_API_KEY")

# --- 規劃模式選擇 ---
PLANNING_MODE = 'location_only'  # 'time_aware' or 'location_only'

# --- 使用者輸入 ---
INPUT_LOCATIONS = [
    "安可鐘", "維也納聖彼得教堂", "德梅爾咖啡店",
    "聖斯德望主教座堂", "奧地利國家圖書館",
    "霍夫堡", "奧地利國會大廈", "Haus der Musik",
    "維也納博物館", "卡爾教堂", 
    "美景宮", "Kunsthistorisches Museum Wien", "Naturhistorisches Museum Wien",
    "維也納市政廳", "百水公寓"
]
ITINERARY_START_LOCATION = "smartments Wien Hauptbahnhof"
ITINERARY_END_LOCATION = "smartments Wien Hauptbahnhof"

today = datetime.now().date()
# --- 時間設定 (僅在 'time_aware' 模式下生效) ---
TRIP_START_TIME = datetime.combine(today, time(9, 0)) 
TRIP_END_TIME = datetime.combine(today + timedelta(days=2), time(22, 0))  # 延長到3天
DAY_START_HOUR = 8  # 提早開始時間
DAY_END_HOUR = 23   # 延後結束時間
DEFAULT_STAY_DURATION_MINS = 60  # 減少停留時間以容納更多地點

# --- 演算法與交通參數 (調整為更包容的設定) ---
DISTANCE_THRESHOLD_KM = 1.2  # 增加分群距離，讓更多地點被分在一起
WALKING_TIME_LIMIT_SECONDS = 20 * 60  # 增加步行時間限制到20分鐘
BRUTE_FORCE_LIMIT = 12  # 增加暴力搜尋上限
INTER_CLUSTER_TRAVEL_MODE = "transit"
INTRA_CLUSTER_TRAVEL_MODE = "walking"

# --- 新增：強制包含所有地點的設定 ---
FORCE_INCLUDE_ALL_LOCATIONS = True  # 強制包含所有地點
IGNORE_OPENING_HOURS = True  # 忽略營業時間限制
EXTEND_DAYS_IF_NEEDED = True  # 如果需要，自動延長天數