
import json
import datetime

# ================= 配置区域 =================
INPUT_FILE = 'raw_chat.json' 
OUTPUT_FILE = 'chat_data.json'
TARGET_PEER_ID = '3060496688413c0f9495e69e123f2aa7'
SOURCE_VALUE_IS_ME = 1
# ===========================================

def parse_time(timestamp_ms):
    try:
        ts_float = float(timestamp_ms) / 1000.0
        dt = datetime.datetime.fromtimestamp(ts_float)
        # 返回 (完整时间字符串, 日期字符串, 只有时分字符串)
        return dt.strftime('%Y-%m-%d %H:%M:%S'), dt.strftime('%Y-%m-%d'), dt.strftime('%H:%M')
    except Exception:
        return str(timestamp_ms), "1970-01-01", "00:00"

def process_json_data():
    messages = []
    print(f"正在读取 {INPUT_FILE}...")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            
        if not isinstance(raw_data, list):
            raw_data = [raw_data]

        count = 0

        for item in raw_data:
            peer_id = item.get('PEER_USER_ID')
            
            if peer_id == TARGET_PEER_ID:
                content = item.get('CONTENT')
                create_time = item.get('CREATE_TIME', 0)
                msg_type = item.get('TYPE')
                source = item.get('SOURCE')
                
                # ==== 新增：获取撤回状态 ====
                # 假设 1 代表已撤回，0 代表正常 (根据常见逻辑推断)
                # 即使 JSON 里没有 RECALL 字段，get() 也会返回 0
                is_recalled = item.get('RECALL') == 1

                # ==== 判断发送者 ====
                is_me = (source == SOURCE_VALUE_IS_ME)

                full_time, date_str, short_time = parse_time(create_time)
                
                msg_obj = {
                    "id": item.get('_id'),
                    "content": content,
                    "time": full_time,      # 完整时间
                    "short_time": short_time, # 时:分 (用于前端展示)
                    "date": date_str,
                    "isMe": is_me,
                    "isRecalled": is_recalled, # 新增字段
                    "type": str(msg_type),
                    "raw_ts": create_time
                }
                messages.append(msg_obj)
                count += 1
        
        messages.sort(key=lambda x: x['raw_ts'])

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)

        print(f"处理完成！共提取 {count} 条记录。")
        print(f"已包含撤回(RECALL)字段数据。")

    except Exception as e:
        print(f"发生错误：{e}")

if __name__ == "__main__":
    process_json_data()
