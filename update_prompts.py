import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Load data
with open(r'D:\fgo ai\chat_system\personalities.json', 'r', encoding='utf-8') as f:
    personalities = json.load(f)

with open(r'D:\fgo ai\chat_system\cn_dialogues.json', 'r', encoding='utf-8') as f:
    cn_dialogues = json.load(f)

# Update each servant with CN dialogue and improved system prompt
updated = 0
for pid, info in personalities.items():
    # Add CN dialogue samples
    cn_lines = cn_dialogues.get(pid, [])
    info['cn_dialogues'] = cn_lines
    
    # Update system prompt to be more Chinese-friendly
    name_cn = info.get('name_cn', '')
    name_jp = info.get('name_jp', '')
    cls = info.get('class', '')
    rarity = info.get('rarity', 0)
    personality = info.get('personality', '')
    speech_style = info.get('speech_style', '')
    
    # Build improved system prompt
    stars = '★' * rarity
    prompt = f"你是{name_cn}（{name_jp}），来自Fate/Grand Order的{cls}职阶从者。稀有度：{stars}\n\n"
    
    if personality:
        prompt += f"【性格特点】\n{personality}\n\n"
    
    if speech_style:
        prompt += f"【说话风格】\n{speech_style}\n\n"
    
    # Add CN dialogue samples if available
    if cn_lines:
        prompt += "【中文台词参考】\n"
        for line in cn_lines[:5]:
            prompt += f"- {line}\n"
        prompt += "\n"
    
    # Add story memory placeholder
    story_memory = info.get('story_memory', [])
    if story_memory:
        prompt += "## 你参与过的剧情记忆：\n"
        for i, mem in enumerate(story_memory[:10], 1):
            quest = mem.get('quest', '')
            summary = mem.get('summary', '')[:150]
            if quest and summary:
                prompt += f"{i}. 【{quest}】{summary}...\n"
        prompt += "\n以上是你亲身经历过的剧情事件。请基于这些记忆来回答关于剧情的问题。你没有参与过的剧情事件，你不会知道。\n"
    
    prompt += f"\n请用中文回复。你必须使用中文与用户对话，不要使用日语。保持{name_cn}的角色设定，用符合{name_cn}性格的方式回复。"
    
    info['system_prompt'] = prompt
    updated += 1

# Save
with open(r'D:\fgo ai\chat_system\personalities.json', 'w', encoding='utf-8') as f:
    json.dump(personalities, f, ensure_ascii=False, indent=2)

print(f"Updated {updated} servants with CN dialogue and improved prompts")

# Show sample
pid = '2275'  # 贞德
if pid in personalities:
    print(f"\nSample prompt for {personalities[pid]['name_cn']}:")
    print(personalities[pid]['system_prompt'][:500])
