import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'D:\fgo ai\chat_system\personalities.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check a sample system prompt
pid = '190'  # 玛修
if pid in data:
    prompt = data[pid].get('system_prompt', '')
    print(f"Sample system prompt for {data[pid].get('name_cn', pid)}:")
    print(prompt[:500])
    print("...")
