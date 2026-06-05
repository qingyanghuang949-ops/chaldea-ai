"""
FGO Wiki (Mooncell) 数据爬虫
通过 MediaWiki API 爬取 fgo.wiki 的结构化数据，存入 SQLite 数据库
"""

import requests
import sqlite3
import json
import time
import re
import os
import sys
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "https://fgo.wiki/api.php"
DB_PATH = os.path.join(os.path.dirname(__file__), "fgo_wiki.db")
HEADERS = {"User-Agent": "FGO-Wiki-Scraper/1.0 (Personal Use)"}

# 请求间隔（秒），避免给服务器造成压力
REQUEST_DELAY = 0.5


def api_get(params, retries=3):
    """调用 MediaWiki API，带重试"""
    params["format"] = "json"
    for attempt in range(retries):
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  [ERROR] API请求失败: {e}")
                return None


def get_all_category_members(category, limit=500):
    """获取分类下的所有页面"""
    members = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": str(limit),
        "cmtype": "page",
    }
    while True:
        data = api_get(params)
        if not data or "query" not in data:
            break
        members.extend(data["query"]["categorymembers"])
        if "continue" in data:
            params["cmcontinue"] = data["continue"]["cmcontinue"]
            time.sleep(REQUEST_DELAY)
        else:
            break
    return members


def get_page_wikitext(title):
    """获取页面的 wikitext 源码"""
    data = api_get({
        "action": "parse",
        "page": title,
        "prop": "wikitext",
    })
    if data and "parse" in data:
        return data["parse"]["wikitext"]["*"]
    return None


def get_page_html(title):
    """获取页面的 HTML（用于某些需要渲染的数据）"""
    data = api_get({
        "action": "parse",
        "page": title,
        "prop": "text",
    })
    if data and "parse" in data:
        return data["parse"]["text"]["*"]
    return None


# ──────────────────────────────────────────────
# Wikitext 模板解析
# ──────────────────────────────────────────────

def parse_template_params(wikitext, template_name):
    """从 wikitext 中提取指定模板的参数"""
    # 匹配 {{模板名 | param1=value1 | param2=value2 }}
    pattern = r'\{\{' + re.escape(template_name) + r'\s*\|([\s\S]*?)\}\}'
    matches = re.findall(pattern, wikitext)
    results = []
    for match in matches:
        params = {}
        # 按 | 分割，但要注意嵌套
        parts = []
        depth = 0
        current = ""
        for ch in match:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            elif ch == '|' and depth == 0:
                parts.append(current.strip())
                current = ""
                continue
            current += ch
        if current.strip():
            parts.append(current.strip())

        for part in parts:
            if '=' in part:
                key, _, value = part.partition('=')
                params[key.strip()] = value.strip()
        results.append(params)
    return results


def extract_between_templates(wikitext, start_template, end_template=None):
    """提取两个模板标记之间的内容"""
    start_idx = wikitext.find(start_template)
    if start_idx == -1:
        return ""
    start_idx += len(start_template)
    if end_template:
        end_idx = wikitext.find(end_template, start_idx)
        if end_idx == -1:
            return wikitext[start_idx:]
        return wikitext[start_idx:end_idx]
    return wikitext[start_idx:]


# ──────────────────────────────────────────────
# 数据库操作
# ──────────────────────────────────────────────

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA encoding='UTF-8'")

    # 从者表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS servants (
            page_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            rarity INTEGER,
            class TEXT,
            obtain_method TEXT,
            cv TEXT,
            illustrator TEXT,
            attribute1 TEXT,
            attribute2 TEXT,
            gender TEXT,
            height TEXT,
            weight TEXT,
            sub_attribute TEXT,
            base_atk INTEGER,
            base_hp INTEGER,
            max_atk INTEGER,
            max_hp INTEGER,
            p90_atk INTEGER,
            p90_hp INTEGER,
            p100_atk INTEGER,
            p100_hp INTEGER,
            card_deck TEXT,
            np_rate TEXT,
            hit_count TEXT,
            star_rate TEXT,
            death_rate TEXT,
            crit_weight INTEGER,
            traits TEXT,
            nicknames TEXT,
            wikitext_raw TEXT,
            fetched_at TEXT
        )
    """)

    # 宝具表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS noble_phantasms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servant_page_id INTEGER,
            name_cn TEXT,
            name_jp TEXT,
            card_color TEXT,
            np_type TEXT,
            rank TEXT,
            kind TEXT,
            effects TEXT,
            np_values TEXT,
            is_strengthened INTEGER DEFAULT 0,
            FOREIGN KEY (servant_page_id) REFERENCES servants(page_id)
        )
    """
    )

    # 技能表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servant_page_id INTEGER,
            skill_type TEXT,
            name_cn TEXT,
            name_jp TEXT,
            cooldown INTEGER,
            effects TEXT,
            skill_values TEXT,
            is_strengthened INTEGER DEFAULT 0,
            FOREIGN KEY (servant_page_id) REFERENCES servants(page_id)
        )
    """)

    # 礼装表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS craft_essences (
            page_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            rarity INTEGER,
            cost INTEGER,
            hp_max INTEGER,
            atk_max INTEGER,
            effects TEXT,
            illustrator TEXT,
            wikitext_raw TEXT,
            fetched_at TEXT
        )
    """)

    # 道具表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            page_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            item_type TEXT,
            wikitext_raw TEXT,
            fetched_at TEXT
        )
    """)

    # 敌人表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS enemies (
            page_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            class TEXT,
            traits TEXT,
            wikitext_raw TEXT,
            fetched_at TEXT
        )
    """)

    # 页面索引（记录所有爬取过的页面）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS page_index (
            page_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT,
            fetched_at TEXT
        )
    """)

    conn.commit()
    return conn


# ──────────────────────────────────────────────
# 从者数据解析
# ──────────────────────────────────────────────

def parse_servant(wikitext, page_id, name):
    """解析从者页面的 wikitext"""
    now = datetime.now().isoformat()

    # 基础数值
    base = parse_template_params(wikitext, "基础数值")
    if not base:
        return None

    b = base[0]

    servant = {
        "page_id": page_id,
        "name": name,
        "rarity": int(b.get("稀有度", 0) or 0),
        "class": b.get("职阶", ""),
        "obtain_method": b.get("获取途径", ""),
        "cv": b.get("声优", ""),
        "illustrator": b.get("画师", ""),
        "attribute1": b.get("属性1", ""),
        "attribute2": b.get("属性2", ""),
        "gender": b.get("性别", ""),
        "height": b.get("身高", ""),
        "weight": b.get("体重", ""),
        "sub_attribute": b.get("副属性", ""),
        "base_atk": int(b.get("基础ATK", 0) or 0),
        "base_hp": int(b.get("基础HP", 0) or 0),
        "max_atk": int(b.get("满级ATK", 0) or 0),
        "max_hp": int(b.get("满级HP", 0) or 0),
        "p90_atk": int(b.get("90级ATK", 0) or 0),
        "p90_hp": int(b.get("90级HP", 0) or 0),
        "p100_atk": int(b.get("100级ATK", 0) or 0),
        "p100_hp": int(b.get("100级HP", 0) or 0),
        "card_deck": json.dumps([
            b.get("第一张卡", ""), b.get("第二张卡", ""),
            b.get("第三张卡", ""), b.get("第四张卡", ""),
            b.get("第五张卡", "")
        ], ensure_ascii=False),
        "np_rate": json.dumps({
            "Q": b.get("Q卡np率", ""), "A": b.get("A卡np率", ""),
            "B": b.get("B卡np率", ""), "EX": b.get("EX卡np率", ""),
            "NP": b.get("宝具np率", ""), "hit": b.get("受击np率", "")
        }, ensure_ascii=False),
        "hit_count": json.dumps({
            "Q": b.get("Q卡hit数", ""), "A": b.get("A卡hit数", ""),
            "B": b.get("B卡hit数", ""), "EX": b.get("EX卡hit数", ""),
            "NP": b.get("宝具卡hit数", "")
        }, ensure_ascii=False),
        "star_rate": b.get("出星率", ""),
        "death_rate": b.get("即死率", ""),
        "crit_weight": int(b.get("暴击权重", 0) or 0),
        "traits": json.dumps([
            b.get(f"特性{i}", "") for i in range(1, 10)
            if b.get(f"特性{i}", "")
        ], ensure_ascii=False),
        "nicknames": b.get("昵称", ""),
        "wikitext_raw": wikitext,
        "fetched_at": now,
    }

    # 宝具
    nps = []
    np_templates = parse_template_params(wikitext, "宝具")
    for np_data in np_templates:
        effects = []
        for key in ["效果A", "效果B", "效果C"]:
            if np_data.get(key):
                effects.append(np_data[key])
        values = {}
        for key, val in np_data.items():
            if re.match(r'数值[A-C]\d', key):
                values[key] = val
        nps.append({
            "name_cn": np_data.get("中文名", ""),
            "name_jp": np_data.get("日文名", ""),
            "card_color": np_data.get("卡色", ""),
            "np_type": np_data.get("类型", ""),
            "rank": np_data.get("阶级", ""),
            "kind": np_data.get("种类", ""),
            "effects": json.dumps(effects, ensure_ascii=False),
            "values": json.dumps(values, ensure_ascii=False),
        })

    # 技能
    skills = []
    skill_templates = parse_template_params(wikitext, "持有技能")
    for sk in skill_templates:
        effects = []
        for key in sorted(sk.keys()):
            if re.match(r'^\d+$', key) or key.startswith("效果"):
                if sk[key]:
                    effects.append(sk[key])
        values = {}
        for key, val in sk.items():
            if re.match(r'^\d+$', key):
                values[key] = val
        skills.append({
            "skill_type": "active",
            "name_cn": sk.get("2", sk.get("技能名", "")),
            "name_jp": sk.get("3", ""),
            "cooldown": int(sk.get("4", 0) or 0),
            "effects": json.dumps(effects, ensure_ascii=False),
            "values": json.dumps(values, ensure_ascii=False),
        })

    # 职阶技能
    class_skills = parse_template_params(wikitext, "职阶技能")
    for cs in class_skills:
        # 职阶技能格式不同，单独处理
        pass

    return servant, nps, skills


# ──────────────────────────────────────────────
# 礼装数据解析
# ──────────────────────────────────────────────

def parse_craft_essence(wikitext, page_id, name):
    """解析概念礼装页面"""
    now = datetime.now().isoformat()
    ce_data = parse_template_params(wikitext, "概念礼装")
    if not ce_data:
        return None

    c = ce_data[0]
    
    # HP/ATK 格式: "750/3000" 或 "0"
    hp_raw = c.get("HP", "0")
    atk_raw = c.get("ATK", "0")
    hp_max = 0
    atk_max = 0
    if "/" in str(hp_raw):
        try:
            hp_max = int(hp_raw.split("/")[-1])
        except:
            pass
    else:
        try:
            hp_max = int(hp_raw)
        except:
            pass
    if "/" in str(atk_raw):
        try:
            atk_max = int(atk_raw.split("/")[-1])
        except:
            pass
    else:
        try:
            atk_max = int(atk_raw)
        except:
            pass

    return {
        "page_id": page_id,
        "name": c.get("名称", name),
        "rarity": int(c.get("稀有度", 0) or 0),
        "cost": int(c.get("cost", 0) or 0),
        "hp_max": hp_max,
        "atk_max": atk_max,
        "effects": c.get("持有技能", ""),
        "illustrator": c.get("画师", ""),
        "wikitext_raw": wikitext,
        "fetched_at": now,
    }


# ──────────────────────────────────────────────
# 道具数据解析
# ──────────────────────────────────────────────

def parse_item(wikitext, page_id, name):
    """解析道具页面 ({{道具信息}} 模板)"""
    now = datetime.now().isoformat()
    item_data = parse_template_params(wikitext, "道具信息")
    if not item_data:
        return None

    d = item_data[0]
    return {
        "page_id": page_id,
        "name": d.get("中文名称", name),
        "description": d.get("中文详细信息", ""),
        "item_type": d.get("分类", ""),
        "wikitext_raw": wikitext,
        "fetched_at": now,
    }


# ──────────────────────────────────────────────
# 敌人数据解析
# ──────────────────────────────────────────────

def parse_enemy_from_table(wikitext):
    """从敌人一览页面的wikitext表格中提取敌人数据"""
    enemies = []
    # 敌人数据在wikitext表格中，格式为:
    # {| class="wikitable"
    # |- (header row)
    # ! 头像 ! 名称 ! 职阶 ! ...
    # |- (data row)
    # | 图片 || 名称 || 职阶 || ...
    # |}

    lines = wikitext.split('\n')
    current_section = ""
    in_table = False
    is_header = True
    headers = []
    current_row = []

    for line in lines:
        stripped = line.strip()

        # 检测section标题
        if stripped.startswith('==') and stripped.endswith('=='):
            current_section = stripped.strip('= ')
            continue

        # 表格开始
        if stripped.startswith('{|'):
            in_table = True
            is_header = True
            headers = []
            current_row = []
            continue

        # 表格结束
        if stripped == '|}':
            in_table = False
            is_header = False
            continue

        if not in_table:
            continue

        # 表头行
        if stripped.startswith('!'):
            # 解析表头
            header_text = stripped.lstrip('!')
            parts = re.split(r'\!\s*', header_text)
            headers = [re.sub(r'<[^>]+>', '', p).strip() for p in parts if p.strip()]
            is_header = False
            continue

        # 新行
        if stripped == '-':
            # 处理之前积累的行
            if current_row:
                enemy = _parse_enemy_row(current_row, headers, current_section)
                if enemy:
                    enemies.append(enemy)
            current_row = []
            continue

        # 数据行 (以 | 或 || 开头)
        if stripped.startswith('|'):
            # 分割单元格
            cell_text = stripped
            if cell_text.startswith('||'):
                cells = [c.strip() for c in cell_text.split('||') if c.strip()]
            elif cell_text.startswith('|'):
                first_cell = cell_text[1:].strip()
                rest = cell_text[1:]
                if '||' in rest:
                    parts = rest.split('||')
                    cells = [parts[0].strip()] + [p.strip() for p in parts[1:] if p.strip()]
                else:
                    cells = [first_cell]
            else:
                cells = []

            current_row.extend(cells)

    # 处理最后一行
    if current_row:
        enemy = _parse_enemy_row(current_row, headers, current_section)
        if enemy:
            enemies.append(enemy)

    return enemies


def _parse_enemy_row(cells, headers, section):
    """解析一行敌人数据"""
    if len(cells) < 2:
        return None

    def clean_text(text):
        """清理wikitext标记"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除文件链接
        text = re.sub(r'\[\[文件:[^\]]*\]\]', '', text)
        # 移除普通链接
        text = re.sub(r'\[\[([^\]|]+)\|?([^\]]*)\]\]', lambda m: m.group(2) or m.group(1), text)
        # 移除粗体标记
        text = re.sub(r"'''([^']*)'''", r'\1', text)
        # 清理多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    # 第一列通常是头像(图片), 第二列是名称
    name = clean_text(cells[1]) if len(cells) > 1 else ""
    cls = clean_text(cells[2]) if len(cells) > 2 else ""
    traits = clean_text(cells[4]) if len(cells) > 4 else ""

    if not name:
        return None

    return {
        "name": name,
        "class": cls,
        "traits": traits,
        "section": section,
        "wikitext_raw": '||'.join(cells),
    }


# ──────────────────────────────────────────────
# 主爬取流程
# ──────────────────────────────────────────────

def crawl_servants(conn):
    """爬取所有从者数据"""
    print("=" * 60)
    print("开始爬取从者数据...")
    print("=" * 60)

    members = get_all_category_members("英灵图鉴")
    print(f"找到 {len(members)} 个从者页面")

    success = 0
    failed = 0

    for i, member in enumerate(members):
        page_id = member["pageid"]
        title = member["title"]

        # 跳过已存在的
        existing = conn.execute(
            "SELECT page_id FROM servants WHERE page_id=?", (page_id,)
        ).fetchone()
        if existing:
            print(f"  [{i+1}/{len(members)}] 跳过（已存在）: {title}")
            continue

        print(f"  [{i+1}/{len(members)}] 爬取: {title} ...", end=" ")
        wikitext = get_page_wikitext(title)
        time.sleep(REQUEST_DELAY)

        if not wikitext:
            print("FAILED（无法获取）")
            failed += 1
            continue

        result = parse_servant(wikitext, page_id, title)
        if not result:
            print("FAILED（解析失败）")
            failed += 1
            # 仍然保存原始数据
            conn.execute("""
                INSERT OR REPLACE INTO page_index (page_id, title, category, fetched_at)
                VALUES (?, ?, ?, ?)
            """, (page_id, title, "英灵图鉴", datetime.now().isoformat()))
            continue

        servant, nps, skills_list = result

        conn.execute("""
            INSERT OR REPLACE INTO servants
            (page_id, name, rarity, class, obtain_method, cv, illustrator,
             attribute1, attribute2, gender, height, weight, sub_attribute,
             base_atk, base_hp, max_atk, max_hp, p90_atk, p90_hp, p100_atk, p100_hp,
             card_deck, np_rate, hit_count, star_rate, death_rate, crit_weight,
             traits, nicknames, wikitext_raw, fetched_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            servant["page_id"], servant["name"], servant["rarity"],
            servant["class"], servant["obtain_method"], servant["cv"],
            servant["illustrator"], servant["attribute1"], servant["attribute2"],
            servant["gender"], servant["height"], servant["weight"],
            servant["sub_attribute"], servant["base_atk"], servant["base_hp"],
            servant["max_atk"], servant["max_hp"], servant["p90_atk"],
            servant["p90_hp"], servant["p100_atk"], servant["p100_hp"],
            servant["card_deck"], servant["np_rate"], servant["hit_count"],
            servant["star_rate"], servant["death_rate"], servant["crit_weight"],
            servant["traits"], servant["nicknames"], servant["wikitext_raw"],
            servant["fetched_at"]
        ))

        for np in nps:
            conn.execute("""
                INSERT INTO noble_phantasms
                (servant_page_id, name_cn, name_jp, card_color, np_type, rank, kind, effects, np_values)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                page_id, np["name_cn"], np["name_jp"], np["card_color"],
                np["np_type"], np["rank"], np["kind"], np["effects"], np["values"]
            ))

        for sk in skills_list:
            conn.execute("""
                INSERT INTO skills
                (servant_page_id, skill_type, name_cn, name_jp, cooldown, effects, skill_values)
                VALUES (?,?,?,?,?,?,?)
            """, (
                page_id, sk["skill_type"], sk["name_cn"], sk["name_jp"],
                sk["cooldown"], sk["effects"], sk["values"]
            ))

        conn.execute("""
            INSERT OR REPLACE INTO page_index (page_id, title, category, fetched_at)
            VALUES (?, ?, ?, ?)
        """, (page_id, title, "英灵图鉴", datetime.now().isoformat()))

        # 每10条批量提交
        if (i + 1) % 10 == 0:
            conn.commit()
        print(f"OK ({servant['class']} {servant['rarity']}★)")
        success += 1

    conn.commit()
    print(f"\n从者爬取完成: 成功 {success}, 失败 {failed}, 总计 {len(members)}")
    return success


def crawl_craft_essences(conn):
    """爬取概念礼装数据"""
    print("\n" + "=" * 60)
    print("开始爬取概念礼装数据...")
    print("=" * 60)

    members = get_all_category_members("概念礼装")
    print(f"找到 {len(members)} 个礼装页面")

    success = 0
    for i, member in enumerate(members):
        page_id = member["pageid"]
        title = member["title"]

        existing = conn.execute(
            "SELECT page_id FROM craft_essences WHERE page_id=?", (page_id,)
        ).fetchone()
        if existing:
            print(f"  [{i+1}/{len(members)}] 跳过（已存在）: {title}")
            continue

        print(f"  [{i+1}/{len(members)}] 爬取: {title} ...", end=" ")
        wikitext = get_page_wikitext(title)
        time.sleep(REQUEST_DELAY)

        if not wikitext:
            print("FAILED")
            continue

        ce = parse_craft_essence(wikitext, page_id, title)
        if not ce:
            print("FAILED（解析失败）")
            continue

        conn.execute("""
            INSERT OR REPLACE INTO craft_essences
            (page_id, name, rarity, cost, hp_max, atk_max, effects, illustrator, wikitext_raw, fetched_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            ce["page_id"], ce["name"], ce["rarity"], ce["cost"],
            ce["hp_max"], ce["atk_max"], ce["effects"], ce["illustrator"],
            ce["wikitext_raw"], ce["fetched_at"]
        ))

        conn.execute("""
            INSERT OR REPLACE INTO page_index (page_id, title, category, fetched_at)
            VALUES (?, ?, ?, ?)
        """, (page_id, title, "概念礼装图鉴", datetime.now().isoformat()))

        conn.commit()
        print(f"OK ({ce['rarity']}★)")
        success += 1

    print(f"\n礼装爬取完成: 成功 {success}")
    return success


def crawl_generic_category(conn, category, table_name, parser_func=None):
    """通用分类爬取"""
    print(f"\n{'='*60}")
    print(f"开始爬取: {category}")
    print(f"{'='*60}")

    members = get_all_category_members(category)
    print(f"找到 {len(members)} 个页面")

    success = 0
    for i, member in enumerate(members):
        page_id = member["pageid"]
        title = member["title"]

        existing = conn.execute(
            f"SELECT page_id FROM {table_name} WHERE page_id=?", (page_id,)
        ).fetchone()
        if existing:
            continue

        print(f"  [{i+1}/{len(members)}] {title} ...", end=" ")
        wikitext = get_page_wikitext(title)
        time.sleep(REQUEST_DELAY)

        if not wikitext:
            print("FAILED")
            continue

        if parser_func:
            parsed = parser_func(wikitext, page_id, title)
            if parsed:
                # 动态插入
                cols = ", ".join(parsed.keys())
                placeholders = ", ".join(["?"] * len(parsed))
                conn.execute(
                    f"INSERT OR REPLACE INTO {table_name} ({cols}) VALUES ({placeholders})",
                    list(parsed.values())
                )

        conn.execute("""
            INSERT OR REPLACE INTO page_index (page_id, title, category, fetched_at)
            VALUES (?, ?, ?, ?)
        """, (page_id, title, category, datetime.now().isoformat()))

        conn.commit()
        print("OK")
        success += 1

    print(f"\n{category} 爬取完成: {success} 个")
    return success


# ──────────────────────────────────────────────
# 统计
# ──────────────────────────────────────────────

def print_stats(conn):
    """打印数据库统计"""
    print("\n" + "=" * 60)
    print("数据库统计")
    print("=" * 60)

    tables = {
        "servants": "从者",
        "noble_phantasms": "宝具",
        "skills": "技能",
        "craft_essences": "概念礼装",
        "items": "道具",
        "enemies": "敌人",
        "page_index": "页面索引",
    }

    for table, label in tables.items():
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {label}: {count} 条")
        except:
            print(f"  {label}: 表不存在")

    # 从者按职阶统计
    print("\n从者按职阶分布:")
    try:
        rows = conn.execute(
            "SELECT class, COUNT(*) FROM servants GROUP BY class ORDER BY COUNT(*) DESC"
        ).fetchall()
        for cls, cnt in rows:
            print(f"  {cls or '未知'}: {cnt}")
    except:
        pass

    # 从者按稀有度统计
    print("\n从者按稀有度分布:")
    try:
        rows = conn.execute(
            "SELECT rarity, COUNT(*) FROM servants GROUP BY rarity ORDER BY rarity"
        ).fetchall()
        for r, cnt in rows:
            print(f"  {r}★: {cnt}")
    except:
        pass


# ──────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────

def crawl_items(conn):
    """爬取道具数据 (Category:道具)"""
    print("\n" + "=" * 60)
    print("开始爬取道具数据...")
    print("=" * 60)

    members = get_all_category_members("道具")
    print(f"找到 {len(members)} 个道具页面")

    success = 0
    failed = 0
    for i, member in enumerate(members):
        page_id = member["pageid"]
        title = member["title"]

        existing = conn.execute(
            "SELECT page_id FROM items WHERE page_id=?", (page_id,)
        ).fetchone()
        if existing:
            continue

        print(f"  [{i+1}/{len(members)}] {title} ...", end=" ")
        wikitext = get_page_wikitext(title)
        time.sleep(REQUEST_DELAY)

        if not wikitext:
            print("FAILED")
            failed += 1
            continue

        item = parse_item(wikitext, page_id, title)
        if not item:
            print("FAILED（解析失败）")
            failed += 1
            continue

        conn.execute("""
            INSERT OR REPLACE INTO items
            (page_id, name, description, item_type, wikitext_raw, fetched_at)
            VALUES (?,?,?,?,?,?)
        """, (
            item["page_id"], item["name"], item["description"],
            item["item_type"], item["wikitext_raw"], item["fetched_at"]
        ))

        conn.execute("""
            INSERT OR REPLACE INTO page_index (page_id, title, category, fetched_at)
            VALUES (?, ?, ?, ?)
        """, (page_id, title, "道具", datetime.now().isoformat()))

        conn.commit()
        print("OK")
        success += 1

    print(f"\n道具爬取完成: 成功 {success}, 失败 {failed}, 总计 {len(members)}")
    return success


def crawl_enemies(conn):
    """爬取敌人数据 (敌人一览页面及子页面)"""
    print("\n" + "=" * 60)
    print("开始爬取敌人数据...")
    print("=" * 60)

    # 敌人数据在 "敌人一览" 页面及其子页面中
    enemy_pages = ["敌人一览"]

    # 获取子页面
    sub_pages = get_all_category_members("敌人一览")  # 不在分类中，用allpages
    # 用 API 查询子页面
    data = api_get({
        "action": "query",
        "list": "allpages",
        "apprefix": "敌人一览/",
        "apnamespace": "0",
        "aplimit": "500",
    })
    if data and "query" in data:
        for page in data["query"]["allpages"]:
            enemy_pages.append(page["title"])

    print(f"找到 {len(enemy_pages)} 个敌人页面")

    total_enemies = 0
    for page_title in enemy_pages:
        print(f"\n  处理: {page_title}")

        # 检查是否已爬取
        existing = conn.execute(
            "SELECT page_id FROM page_index WHERE title=? AND category=?",
            (page_title, "敌人一览")
        ).fetchone()
        if existing:
            print(f"    跳过（已存在）")
            continue

        # 获取页面wikitext
        wikitext = get_page_wikitext(page_title)
        time.sleep(REQUEST_DELAY)

        if not wikitext:
            print(f"    FAILED（无法获取）")
            continue

        # 获取page_id
        page_data = api_get({"action": "query", "titles": page_title, "format": "json"})
        page_id = 0
        if page_data and "query" in page_data:
            pages = page_data["query"].get("pages", {})
            for pid, pdata in pages.items():
                page_id = int(pid)

        # 解析敌人数据
        enemies = parse_enemy_from_table(wikitext)
        print(f"    找到 {len(enemies)} 个敌人")

        for j, enemy in enumerate(enemies):
            # 用名称+页面作为唯一标识
            enemy_page_id = page_id * 10000 + j
            conn.execute("""
                INSERT OR REPLACE INTO enemies
                (page_id, name, class, traits, wikitext_raw, fetched_at)
                VALUES (?,?,?,?,?,?)
            """, (
                enemy_page_id, enemy["name"], enemy["class"],
                enemy["traits"], enemy["wikitext_raw"],
                datetime.now().isoformat()
            ))

        # 记录页面索引
        conn.execute("""
            INSERT OR REPLACE INTO page_index (page_id, title, category, fetched_at)
            VALUES (?, ?, ?, ?)
        """, (page_id, page_title, "敌人一览", datetime.now().isoformat()))

        conn.commit()
        total_enemies += len(enemies)

    print(f"\n敌人爬取完成: 共 {total_enemies} 个敌人")
    return total_enemies


def main():
    print(f"FGO Wiki 爬虫启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据库: {DB_PATH}")
    print()

    conn = init_db()

    # 1. 爬取从者
    crawl_servants(conn)

    # 2. 爬取概念礼装
    crawl_craft_essences(conn)

    # 3. 爬取道具
    crawl_items(conn)

    # 4. 爬取敌人
    crawl_enemies(conn)

    # 5. 统计
    print_stats(conn)

    conn.close()
    print("\n爬取完成！")


if __name__ == "__main__":
    main()
