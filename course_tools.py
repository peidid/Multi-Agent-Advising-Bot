import json
import os
import re

DATA_PATH = "./data/courses"
DB = {"courses": {}}

def load_data():
    """Load all JSON course files into memory."""
    if not os.path.exists(DATA_PATH):
        print(f"⚠️  Warning: Course data path not found: {DATA_PATH}")
        print(f"   Course lookup features will be limited.")
        return
    
    try:
        files = os.listdir(DATA_PATH)
        json_files = [f for f in files if f.endswith(".json")]
        
        if not json_files:
            print(f"⚠️  Warning: No JSON files found in {DATA_PATH}")
            return
        
        for filename in json_files:
            try:
                file_path = os.path.join(DATA_PATH, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Each JSON file is a single course object with a "code" field
                    if isinstance(data, dict) and "code" in data:
                        DB["courses"][data["code"]] = data
                    # Handle legacy format where JSON might be a list
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and "code" in item:
                                DB["courses"][item["code"]] = item
            except Exception as e:
                # Continue loading other files even if one fails
                print(f"⚠️  Error loading {filename}: {e}")
                continue
        
        if DB["courses"]:
            print(f"✅ Loaded {len(DB['courses'])} courses from {DATA_PATH}")
        else:
            print(f"⚠️  Warning: No valid course data loaded from {DATA_PATH}")
            
    except Exception as e:
        print(f"⚠️  Error accessing course data directory: {e}")
        print(f"   Course lookup features will be limited.")

# 初始化加载
try:
    load_data()
except Exception as e:
    print(f"⚠️  Failed to load course data: {e}")
    print(f"   System will continue with limited course lookup functionality.")

def look_up_course_info(course_code):
    """根据课程号返回详细信息"""
    return DB["courses"].get(course_code, None)

def find_course_codes_in_text(text):
    """用正则提取文本中提到的课程号 (如 15-112)"""
    # 匹配类似 15-112, 76-100 的格式
    return re.findall(r"\d{2}-\d{3}", text)