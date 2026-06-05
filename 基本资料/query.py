"""
FGO Wiki 数据库查询工具
用法: python query.py [命令] [参数]
"""

import sqlite3
import json
import sys
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "fgo_wiki.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_stats():
    """显示数据库统计"""
    conn = get_conn()
    print("=" * 50)
    print("FGO Wiki 数据库统计")
    print("=" * 50)

    tables = {
        "servants": "从者",
        "noble_phantasms": "宝具",
        "skills": "技能",
        "craft_essences": "概念礼装",
        "page_index": "页面索引",
    }
    for table, label in tables.items():
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {label}: {count} 条")
        except:
            print(f"  {label}: 表不存在")

    print("\n从者按职阶:")
    for row in conn.execute("SELECT class, COUNT(*) as cnt FROM servants GROUP BY class ORDER BY cnt DESC"):
        print(f"  {row['class'] or '未知'}: {row['cnt']}")

    print("\n从者按稀有度:")
    for row in conn.execute("SELECT rarity, COUNT(*) as cnt FROM servants GROUP BY rarity ORDER BY rarity"):
        print(f"  {row['rarity']}★: {row['cnt']}")

    print("\n礼装按稀有度:")
    for row in conn.execute("SELECT rarity, COUNT(*) as cnt FROM craft_essences GROUP BY rarity ORDER BY rarity"):
        print(f"  {row['rarity']}★: {row['cnt']}")

    conn.close()


def cmd_search(keyword):
    """搜索从者"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT name, rarity, class, max_atk, max_hp FROM servants WHERE name LIKE ? ORDER BY rarity DESC",
        (f"%{keyword}%",)
    ).fetchall()

    if not rows:
        print(f"未找到包含「{keyword}」的从者")
        return

    print(f"\n搜索「{keyword}」找到 {len(rows)} 个结果:")
    print(f"{'名称':<25} {'★':>2} {'职阶':<12} {'ATK':>6} {'HP':>6}")
    print("-" * 60)
    for r in rows:
        print(f"{r['name']:<25} {r['rarity']:>2} {r['class'] or '?':<12} {r['max_atk']:>6} {r['max_hp']:>6}")
    conn.close()


def cmd_servant(name):
    """查看从者详情"""
    conn = get_conn()
    row = conn.execute("SELECT * FROM servants WHERE name = ?", (name,)).fetchone()
    if not row:
        # 模糊搜索
        row = conn.execute("SELECT * FROM servants WHERE name LIKE ?", (f"%{name}%",)).fetchone()
    if not row:
        print(f"未找到从者: {name}")
        return

    print(f"\n{'=' * 50}")
    print(f"{row['name']} ({row['rarity']}★ {row['class']})")
    print(f"{'=' * 50}")
    print(f"CV: {row['cv']}")
    print(f"画师: {row['illustrator']}")
    print(f"属性: {row['attribute1']}·{row['attribute2']} ({row['sub_attribute']})")
    print(f"性别: {row['gender']}  身高: {row['height']}  体重: {row['weight']}")
    print(f"获取途径: {row['obtain_method']}")
    print(f"\nATK: {row['base_atk']} → {row['max_atk']} (Lv90: {row['p90_atk']}, Lv100: {row['p100_atk']})")
    print(f"HP:  {row['base_hp']} → {row['max_hp']} (Lv90: {row['p90_hp']}, Lv100: {row['p100_hp']})")

    cards = json.loads(row['card_deck'])
    print(f"\n指令卡: {' '.join(cards)}")
    print(f"暴击权重: {row['crit_weight']}")
    print(f"出星率: {row['star_rate']}  即死率: {row['death_rate']}")

    traits = json.loads(row['traits'])
    print(f"特性: {', '.join(traits)}")
    if row['nicknames']:
        print(f"昵称: {row['nicknames']}")

    # 宝具
    nps = conn.execute("SELECT * FROM noble_phantasms WHERE servant_page_id = ?", (row['page_id'],)).fetchall()
    if nps:
        print(f"\n{'─' * 30}")
        print("宝具:")
        for np in nps:
            effects = json.loads(np['effects'])
            print(f"  {np['name_cn']} ({np['card_color']} {np['kind']})")
            for eff in effects:
                print(f"    - {eff}")

    # 技能
    skills = conn.execute("SELECT * FROM skills WHERE servant_page_id = ?", (row['page_id'],)).fetchall()
    if skills:
        print(f"\n{'─' * 30}")
        print("技能:")
        for sk in skills:
            effects = json.loads(sk['effects'])
            print(f"  {sk['name_cn']} (CD: {sk['cooldown']}回合)")
            for eff in effects:
                print(f"    - {eff}")

    conn.close()


def cmd_ce_search(keyword):
    """搜索概念礼装"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT name, rarity, cost, hp_max, atk_max, effects FROM craft_essences WHERE name LIKE ? ORDER BY rarity DESC",
        (f"%{keyword}%",)
    ).fetchall()

    if not rows:
        print(f"未找到包含「{keyword}」的礼装")
        return

    print(f"\n搜索「{keyword}」找到 {len(rows)} 个结果:")
    for r in rows:
        print(f"\n  {r['name']} ({r['rarity']}★ COST:{r['cost']})")
        print(f"    HP: {r['hp_max']}  ATK: {r['atk_max']}")
        if r['effects']:
            print(f"    效果: {r['effects'][:100]}...")
    conn.close()


def cmd_top_atk(n=10, rarity=None):
    """ATK排行"""
    conn = get_conn()
    query = "SELECT name, rarity, class, max_atk FROM servants"
    params = []
    if rarity:
        query += " WHERE rarity = ?"
        params.append(rarity)
    query += " ORDER BY max_atk DESC LIMIT ?"
    params.append(n)

    rows = conn.execute(query, params).fetchall()
    title = f"{'★' + str(rarity) + ' ' if rarity else ''}ATK Top {n}"
    print(f"\n{title}:")
    print(f"{'#':>3} {'名称':<25} {'★':>2} {'职阶':<12} {'ATK':>6}")
    print("-" * 55)
    for i, r in enumerate(rows, 1):
        print(f"{i:>3} {r['name']:<25} {r['rarity']:>2} {r['class'] or '?':<12} {r['max_atk']:>6}")
    conn.close()


def cmd_sql(query):
    """执行自定义SQL"""
    conn = get_conn()
    try:
        rows = conn.execute(query).fetchall()
        if rows:
            # 打印列名
            cols = rows[0].keys()
            print(" | ".join(cols))
            print("-" * 80)
            for row in rows:
                print(" | ".join(str(row[c]) for c in cols))
        else:
            print("查询无结果")
    except Exception as e:
        print(f"SQL错误: {e}")
    conn.close()


def main():
    if len(sys.argv) < 2:
        print("""
FGO Wiki 数据库查询工具

命令:
  stats                     显示数据库统计
  search <关键词>           搜索从者
  servant <名称>            查看从者详情
  ce <关键词>               搜索概念礼装
  top [数量] [--rarity N]   ATK排行
  sql <SQL语句>             自定义查询

示例:
  python query.py search 阿尔托莉雅
  python query.py servant 阿尔托莉雅·潘德拉贡
  python query.py top 20 --rarity 5
  python query.py sql "SELECT name, class FROM servants WHERE rarity=5 LIMIT 10"
""")
        return

    cmd = sys.argv[1]

    if cmd == "stats":
        cmd_stats()
    elif cmd == "search" and len(sys.argv) > 2:
        cmd_search(" ".join(sys.argv[2:]))
    elif cmd == "servant" and len(sys.argv) > 2:
        cmd_servant(" ".join(sys.argv[2:]))
    elif cmd == "ce" and len(sys.argv) > 2:
        cmd_ce_search(" ".join(sys.argv[2:]))
    elif cmd == "top":
        n = 10
        rarity = None
        args = sys.argv[2:]
        for i, arg in enumerate(args):
            if arg == "--rarity" and i + 1 < len(args):
                rarity = int(args[i + 1])
            elif arg.isdigit():
                n = int(arg)
        cmd_top_atk(n, rarity)
    elif cmd == "sql" and len(sys.argv) > 2:
        cmd_sql(" ".join(sys.argv[2:]))
    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
