import json
import os
import re

DATA_PATH = "./info"
DB = {"courses": {}}

def load_data():
    """启动时加载所有 JSON 数据到内存"""
    if not os.path.exists(DATA_PATH): return
    
    for filename in os.listdir(DATA_PATH):
        if filename.endswith(".json"):
            try:
                with open(os.path.join(DATA_PATH, filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 假设 JSON 是列表，构建以 code 为 key 的字典
                    if isinstance(data, list):
                        for item in data:
                            if "code" in item:
                                DB["courses"][item["code"]] = item
            except Exception as e:
                print(f"Error loading {filename}: {e}")

# 初始化加载
load_data()

def look_up_course_info(course_code):
    """根据课程号返回详细信息"""
    return DB["courses"].get(course_code, None)

def find_course_codes_in_text(text):
    """用正则提取文本中提到的课程号 (如 15-112)"""
    # 匹配类似 15-112, 76-100 的格式
    return re.findall(r"\d{2}-\d{3}", text)