"""
FGO Servant Personality Extractor v2
Improved dialogue extraction with flexible name matching.
"""
import sqlite3
import re
import json
import os
import sys
from collections import defaultdict

DB_PATH = r'D:\fgo ai\fgo_wiki.db'
ASSETS_JSON = r'D:\fgo ai\基本资料\servant_assets.json'
OUTPUT_PATH = r'D:\fgo ai\chat_system\personalities.json'

def extract_dialogue_lines(script_text, character_names):
    """Extract dialogue lines for a character using flexible name matching."""
    lines = []
    # Build regex pattern: ＠slot：name or ＠name
    # The character name appears after ： or directly after ＠
    for name in character_names:
        # Escape special regex chars in name
        escaped = re.escape(name)
        # Match: ＠[slot]：[name] then dialogue until [k]
        pattern = r'＠(?:\w+：)?' + escaped + r'[\s]*\n(.*?)\[k\]'
        matches = re.findall(pattern, script_text, re.DOTALL)
        for match in matches:
            # Clean script commands
            clean = re.sub(r'\[.*?\]', '', match)
            # Remove narrator lines (？1, ？2, etc.)
            clean = re.sub(r'^[？?]\d+[:：].*$', '', clean, flags=re.MULTILINE)
            clean = re.sub(r'^[？?!！]+$', '', clean, flags=re.MULTILINE)
            # Split into individual lines
            for subline in clean.split('\n'):
                subline = subline.strip()
                if subline and len(subline) > 1 and not re.match(r'^[\s\-\.\,\。]+$', subline):
                    lines.append(subline)
    return lines

def get_name_variants(name_jp, name_cn, wikitext):
    """Generate name variants for flexible matching."""
    variants = set()
    
    # Full names
    if name_jp:
        variants.add(name_jp)
    if name_cn:
        variants.add(name_cn)
    
    # Split by common separators and add parts
    if name_jp:
        parts = re.split(r'[・\s]', name_jp)
        for p in parts:
            if len(p) >= 2:
                variants.add(p)
    
    if name_cn:
        # Chinese name parts
        parts = name_cn.split('·')
        for p in parts:
            if len(p) >= 2:
                variants.add(p)
        # Also try without parenthetical
        base = re.sub(r'[（(].*?[）)]', '', name_cn).strip()
        if base and base != name_cn:
            variants.add(base)
    
    # Extract battle name from wikitext
    if wikitext:
        battle_jp = re.search(r'日文战斗名\s*=\s*(.+)', wikitext)
        if battle_jp:
            variants.add(battle_jp.group(1).strip())
        battle_cn = re.search(r'中文战斗名\s*=\s*(.+)', wikitext)
        if battle_cn:
            variants.add(battle_cn.group(1).strip())
        # Also card names
        card_jp = re.search(r'日文卡面名\s*=\s*(.+)', wikitext)
        if card_jp:
            variants.add(card_jp.group(1).strip())
        card_cn = re.search(r'中文卡面名\s*=\s*(.+)', wikitext)
        if card_cn:
            variants.add(card_cn.group(1).strip())
    
    # Remove empty and very short strings
    variants = {v.strip() for v in variants if v and len(v.strip()) >= 2}
    return list(variants)

def infer_personality_from_wiki(name_cn, wikitext):
    """Infer personality from wiki description."""
    traits = []
    text = wikitext[:5000] if wikitext else ''
    
    # Extract from profile/description sections
    profile_sections = [
        r'==\s*(?:简介|概述|介绍|人物简介|人物详情|角色详情)\s*==\s*\n(.*?)(?=\n==|\Z)',
        r'==\s*Profile\s*==\s*\n(.*?)(?=\n==|\Z)',
    ]
    description = ''
    for pat in profile_sections:
        m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            description = m.group(1).strip()[:800]
            break
    
    # Extract personality keywords from wikitext
    trait_map = {
        '正义': '正义感强，重视秩序',
        '善良': '性格温柔善良',
        '秩序': '遵守秩序，行事端正',
        '混沌': '行为自由奔放，不拘常规',
        '中立': '立场中立，不偏不倚',
        '王': '具有王者气质，威严庄重',
        '姫|公主': '公主气质，优雅高贵',
        '魔術|魔术': '精通魔术',
        '剣|剑': '剑术精湛',
        '弓': '擅长弓术',
        '騎|骑': '骑乘技能优秀',
        '暗殺|暗杀': '擅长暗杀技巧',
        '狂': '有狂化倾向',
        '復讐|复仇': '背负复仇之念',
        '花': '如花般美丽',
        '料理|烹饪': '擅长料理',
        '歌|唱歌': '擅长歌唱',
        '武': '武艺高强',
    }
    
    for pattern, desc in trait_map.items():
        if re.search(pattern, text[:3000]):
            traits.append(desc)
    
    if not traits:
        traits.append('来自Fate/Grand Order的英灵')
    
    return '。'.join(traits[:6]) + '。', description

def extract_speech_style(dialogue_lines):
    """Analyze speech patterns."""
    if not dialogue_lines:
        return '说话方式自然得体。'
    
    styles = []
    sample = dialogue_lines[:100]
    total = len(sample)
    if total == 0:
        return '说话方式自然得体。'
    
    # Polite speech
    polite = sum(1 for l in sample if 'です' in l or 'ます' in l or 'ございます' in l)
    if polite > total * 0.2:
        styles.append('使用丁寧語（です/ます体）')
    
    # Casual
    casual = sum(1 for l in sample if any(w in l for w in ['だぜ', 'だろ', 'じゃねえ', 'ぜ', 'ぜよ', 'だねえ']))
    if casual > total * 0.15:
        styles.append('说话风格较为随意粗犷')
    
    # First person
    for l in sample[:30]:
        if re.search(r'^私|^わたし|^わたくし', l):
            styles.append('一人称是「私」')
            break
        if re.search(r'^僕', l):
            styles.append('一人称是「僕」')
            break
        if re.search(r'^俺', l):
            styles.append('一人称是「俺」')
            break
    
    # Archaic/formal
    archaic = sum(1 for l in sample if any(w in l for w in ['でござる', 'ござる', '拙者', 'わらわ']))
    if archaic > 0:
        styles.append('使用古风/特殊说话方式')
    
    # Kansai dialect
    kansai = sum(1 for l in sample if any(w in l for w in ['やで', 'やねん', 'ほんま', 'あかん']))
    if kansai > 0:
        styles.append('使用关西方言')
    
    if not styles:
        styles.append('说话方式自然得体')
    
    return '。'.join(styles) + '。'

def build_system_prompt(name_jp, name_cn, class_name, rarity, personality, speech_style, sample_dialogues):
    """Build system prompt."""
    stars = '★' * rarity if rarity else ''
    dialogue_text = '\n'.join([f'- {d}' for d in sample_dialogues[:10]]) if sample_dialogues else '（暂无台词数据）'
    
    return f"""你是{name_jp}（{name_cn}），来自Fate/Grand Order的{class_name}职阶从者。稀有度：{stars}

【性格特点】
{personality}

【说话风格】
{speech_style}

【经典台词参考】
{dialogue_text}

【行为准则】
- 始终保持角色设定，用符合{name_jp}性格的方式回复
- 回复要自然、有感情、符合角色设定
- 使用中文回复，但角色名和专有名词保留日文
- 适当使用角色的口头禅和语气词
- 回复长度适中，不要太长
- 如果被问到游戏外的事情，可以适当角色扮演回应
- 称呼用户为「御主」（マスター）"""

def main():
    print("=" * 60)
    print("FGO Servant Personality Extractor v2")
    print("=" * 60)
    
    with open(ASSETS_JSON, 'r', encoding='utf-8') as f:
        assets_list = json.load(f)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Pre-load all story scripts grouped by region
    print("Loading story scripts...")
    cursor.execute('SELECT region, script_text FROM story_scripts')
    scripts_by_region = defaultdict(list)
    for region, text in cursor.fetchall():
        scripts_by_region[region].append(text)
    print(f"Loaded {sum(len(v) for v in scripts_by_region.values())} scripts")
    
    # Get all servants
    cursor.execute('SELECT page_id, name, rarity, class, wikitext_raw, nicknames FROM servants ORDER BY page_id')
    servants = cursor.fetchall()
    
    personalities = {}
    total = len(servants)
    
    for idx, (page_id, name_cn, rarity, class_name, wikitext, nicknames) in enumerate(servants):
        print(f'\r[{idx+1}/{total}] Processing: {name_cn}', end='', flush=True)
        
        # Extract Japanese name
        name_jp = name_cn
        if wikitext:
            m = re.search(r'日文名\s*=\s*(.+)', wikitext)
            if m:
                name_jp = m.group(1).strip()
        
        # Extract internal ID
        svt_ids = re.findall(r'从者内部id\s*=\s*(\d+)', wikitext or '')
        internal_id = svt_ids[0] if svt_ids else None
        
        # Find matching asset
        artwork_file = None
        icon_file = None
        if internal_id:
            for asset in assets_list:
                af = asset.get('artwork_file') or ''
                if str(asset['id']) == internal_id or (internal_id and internal_id in af):
                    artwork_file = asset['artwork_file']
                    icon_file = asset['icon_file']
                    break
        
        # Generate name variants for matching
        name_variants = get_name_variants(name_jp, name_cn, wikitext)
        
        # Extract dialogue from JP scripts
        dialogue_lines = []
        for script in scripts_by_region.get('JP', []):
            lines = extract_dialogue_lines(script, name_variants)
            dialogue_lines.extend(lines)
        
        # Extract from CN scripts
        for script in scripts_by_region.get('CN', []):
            lines = extract_dialogue_lines(script, name_variants)
            dialogue_lines.extend(lines)
        
        # Deduplicate while preserving order
        seen = set()
        unique_lines = []
        for line in dialogue_lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        dialogue_lines = unique_lines
        
        # Build personality
        if len(dialogue_lines) >= 5:
            all_text = ' '.join(dialogue_lines[:200])
            trait_keywords = {
                '食|吃': '对食物有特别的执着',
                '戦|战|战斗': '好战，享受战斗',
                '愛|爱': '重视爱与羁绊',
                'マスター|御主|主人': '重视与御主的关系',
                '誓|忠诚': '忠诚可靠',
                '笑': '性格开朗',
                '涙|泣|哭': '感情丰富',
                '怒': '性格直率',
                '楽|快乐': '乐观积极',
                '強|强': '追求强大',
                '優|温柔': '温柔体贴',
                '幸|幸福': '珍惜幸福时光',
                '守|保护': '有强烈的保护欲',
                '友|朋友': '重视友情',
                '勝|胜利': '追求胜利',
                '敗|负|输': '不服输',
                '信|相信': '值得信赖',
            }
            
            detected = []
            for kw, desc in trait_keywords.items():
                if re.search(kw, all_text):
                    detected.append(desc)
            
            personality = f'来自FGO的{class_name}职阶从者。'
            if detected:
                personality += '。'.join(detected[:6]) + '。'
            else:
                personality += '性格鲜明，有独特的个性。'
        else:
            personality, _ = infer_personality_from_wiki(name_cn, wikitext)
        
        speech_style = extract_speech_style(dialogue_lines)
        sample = dialogue_lines[:15]
        
        system_prompt = build_system_prompt(
            name_jp, name_cn, class_name, rarity,
            personality, speech_style, sample
        )
        
        personalities[str(page_id)] = {
            'page_id': page_id,
            'name_cn': name_cn,
            'name_jp': name_jp,
            'class': class_name,
            'rarity': rarity,
            'internal_id': internal_id,
            'artwork_file': artwork_file,
            'icon_file': icon_file,
            'personality': personality,
            'speech_style': speech_style,
            'sample_dialogues': sample,
            'system_prompt': system_prompt,
            'dialogue_count': len(dialogue_lines),
        }
    
    conn.close()
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(personalities, f, ensure_ascii=False, indent=2)
    
    print(f'\n\nDone! Saved {len(personalities)} servant profiles to {OUTPUT_PATH}')
    with_dialogue = sum(1 for v in personalities.values() if v['dialogue_count'] > 0)
    print(f'Servants with dialogue: {with_dialogue}/{len(personalities)}')
    
    # Show some stats
    top = sorted(personalities.values(), key=lambda x: x['dialogue_count'], reverse=True)[:10]
    print('\nTop 10 by dialogue count:')
    for s in top:
        print(f"  {s['name_jp']} ({s['name_cn']}): {s['dialogue_count']} lines")

if __name__ == '__main__':
    main()
