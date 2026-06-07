"""
FGO Servant Chat System - Flask Backend
Chaldea AI Communication Terminal
"""
import os
import sys
import json
import sqlite3
import re
import requests
from flask import Flask, request, jsonify, send_from_directory, send_file

# Path configuration - works in both dev and PyInstaller
if getattr(sys, 'frozen', False):
    _BASE = os.path.dirname(sys.executable)
    _APP = os.path.join(sys._MEIPASS, 'chat_system')
else:
    _APP = os.path.dirname(os.path.abspath(__file__))
    _BASE = os.path.dirname(_APP)

# ─── Configuration ───────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(_APP, 'config.json')
DB_PATH = os.path.join(_BASE, 'fgo_wiki.db')
PERSONALITIES_PATH = os.path.join(_APP, 'personalities.json')
ASSETS_BASE = os.path.join(_BASE, '基本资料')

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "provider": "xiaomi",
        "api_base": "https://api.xiaomimimo.com/v1",
        "api_key": "",
        "model": "mimo-v2.5-pro",
        "host": "0.0.0.0",
        "port": 5000
    }

config = load_config()

# ─── Provider Presets ────────────────────────────────────────────────────────
PROVIDERS = {
    'xiaomi': {
        'name': '小米 MiMo',
        'api_base': 'https://api.xiaomimimo.com/v1',
        'model': 'mimo-v2.5-pro',
        'models': ['mimo-v2.5-pro', 'mimo-v2-flash', 'mimo-v2.5'],
    },
    'openai': {
        'name': 'ChatGPT (OpenAI)',
        'api_base': 'https://api.openai.com/v1',
        'model': 'gpt-4o-mini',
        'models': ['gpt-4o-mini', 'gpt-4o', 'gpt-4.1-mini', 'gpt-4.1-nano', 'gpt-3.5-turbo'],
    },
    'anthropic': {
        'name': 'Claude (Anthropic)',
        'api_base': 'https://api.anthropic.com/v1',
        'model': 'claude-sonnet-4-20250514',
        'models': ['claude-sonnet-4-20250514', 'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'],
    },
    'doubao': {
        'name': '豆包 (字节跳动)',
        'api_base': 'https://ark.cn-beijing.volces.com/api/v3',
        'model': 'doubao-1.5-pro-32k',
        'models': ['doubao-1.5-pro-32k', 'doubao-pro-32k', 'doubao-lite-32k', 'doubao-1.5-lite-32k'],
    },
    'volcengine': {
        'name': '火山方舟 (自定义Endpoint)',
        'api_base': 'https://ark.cn-beijing.volces.com/api/v3',
        'model': '',
        'models': [],
        'note': '请在模型栏填入你的 Endpoint ID (如 ep-xxxxxxxx)',
    },
    'daicy': {
        'name': 'Daicy API (GPT)',
        'api_base': 'https://api.daicy.vip/v1',
        'model': 'gpt-5.5',
        'models': ['gpt-5.5', 'gpt-4o-mini', 'gpt-4o', 'gpt-4.1-mini', 'gpt-4.1-nano'],
    },
    'deepseek': {
        'name': 'DeepSeek',
        'api_base': 'https://api.deepseek.com/v1',
        'model': 'deepseek-chat',
        'models': ['deepseek-chat', 'deepseek-reasoner'],
    },
}

def get_provider_config():
    """Get resolved provider config with defaults."""
    provider = config.get('provider', 'xiaomi')
    preset = PROVIDERS.get(provider, PROVIDERS['xiaomi'])
    # Check if redeem code in request header matches env var
    redeem_code = request.headers.get('X-Redeem-Code', '') if request else ''
    expected_code = os.environ.get('REDEEM_CODE', '')
    use_owner_key = expected_code and redeem_code == expected_code
    env_key = os.environ.get('API_KEY', '')
    cfg_key = config.get('api_key', '')
    api_key = (env_key if use_owner_key else '') or cfg_key
    print(f'[DEBUG] provider={provider}, redeem_code={redeem_code!r}, expected={expected_code!r}, use_owner_key={use_owner_key}, env_key_set={bool(env_key)}, cfg_key_set={bool(cfg_key)}, final_key_set={bool(api_key)}')
    return {
        'provider': provider,
        'api_base': config.get('api_base') or preset['api_base'],
        'model': config.get('model') or preset['model'],
        'api_key': api_key,
    }

def call_ai_api(messages, temperature=0.85, max_tokens=1024):
    """Unified AI API call supporting all providers. Returns (response_text, error_dict)."""
    pcfg = get_provider_config()
    api_key = pcfg['api_key']
    if not api_key:
        return None, {'error': 'API Key 未配置'}

    api_base = pcfg['api_base'].rstrip('/')
    model = pcfg['model']
    provider = pcfg['provider']

    try:
        if provider == 'anthropic':
            system_text = messages[0]['content'] if messages and messages[0]['role'] == 'system' else ''
            chat_messages = [m for m in messages if m['role'] != 'system']
            headers = {
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json',
            }
            body = {
                'model': model,
                'max_tokens': max_tokens,
                'temperature': temperature,
                'system': system_text,
                'messages': chat_messages,
            }
            resp = requests.post(f'{api_base}/messages', headers=headers, json=body, timeout=30)
            if resp.status_code != 200:
                err_msg = f'API returned status {resp.status_code}'
                try:
                    err_data = resp.json()
                    if 'error' in err_data:
                        err_msg = err_data['error'].get('message', err_msg)
                except:
                    pass
                if resp.status_code == 401:
                    err_msg = 'API Key 无效，请在设置中更新正确的 API Key'
                return None, {'error': err_msg, 'detail': resp.text[:500]}
            result = resp.json()
            if 'error' in result:
                return None, {'error': result['error'].get('message', str(result['error']))}
            ai_text = ''
            for block in result.get('content', []):
                if block.get('type') == 'text':
                    ai_text += block.get('text', '')
            return ai_text or '原神牛逼', None
        else:
            # OpenAI-compatible format
            headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
            body = {'model': model, 'messages': messages, 'temperature': temperature, 'max_completion_tokens': max_tokens}
            resp = requests.post(f'{api_base}/chat/completions', headers=headers, json=body, timeout=30)
            if resp.status_code != 200:
                err_msg = f'API returned status {resp.status_code}'
                try:
                    err_data = resp.json()
                    if 'error' in err_data:
                        err_msg = err_data['error'].get('message', err_msg)
                except:
                    pass
                if resp.status_code == 401:
                    err_msg = 'API Key 无效，请在设置中更新正确的 API Key'
                if any(kw in err_msg.lower() for kw in ['high risk', 'sensitive', '违规', '审核', 'blocked', 'refused', 'rejected']):
                    err_msg = '原神牛逼'
                return None, {'error': err_msg, 'detail': resp.text[:500]}
            result = resp.json()
            if 'error' in result:
                err_msg = result['error'].get('message', str(result['error']))
                if any(kw in err_msg.lower() for kw in ['high risk', 'sensitive', '违规', '审核', 'blocked', 'refused', 'rejected']):
                    return '原神牛逼', None
                return None, {'error': err_msg}
            msg = result['choices'][0]['message']
            ai_text = msg.get('content') or msg.get('reasoning_content') or ''
            if not ai_text or 'considered high risk' in str(ai_text).lower():
                ai_text = '原神牛逼'
            return ai_text, None
    except requests.exceptions.Timeout:
        return None, {'error': 'API request timed out'}
    except Exception as e:
        return None, {'error': str(e)}

# ─── Load data ───────────────────────────────────────────────────────────────
print("Loading personality profiles...")
with open(PERSONALITIES_PATH, 'r', encoding='utf-8') as f:
    personalities = json.load(f)
print(f"Loaded {len(personalities)} servant profiles")

# Load collection number mapping (release order)
COLLECTION_MAP_PATH = os.path.join(_APP, 'servant_collection_map.json')
collection_map = {}
if os.path.exists(COLLECTION_MAP_PATH):
    with open(COLLECTION_MAP_PATH, 'r', encoding='utf-8') as f:
        collection_map = {int(k): v for k, v in json.load(f).items()}
    print(f'Loaded {len(collection_map)} collection numbers')

# Build servant list for network lookups
conn_temp = sqlite3.connect(DB_PATH)
conn_temp.row_factory = sqlite3.Row
all_servants_list = []
for row in conn_temp.execute('SELECT page_id, name, class, rarity, nicknames FROM servants').fetchall():
    all_servants_list.append(dict(row))
conn_temp.close()
print(f'Built servant list: {len(all_servants_list)} servants')

# ─── Flask App ───────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=None)

@app.route('/')
def index():
    return send_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html'))

@app.route('/app.js')
def serve_js():
    return send_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.js'), mimetype='application/javascript')

@app.route('/typemoon_characters.json')
def serve_typemoon_chars():
    return send_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'typemoon_characters.json'), mimetype='application/json')

@app.route('/api/servants')
def list_servants():
    """Return list of all servants with basic info."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT page_id, name, rarity, class, nicknames FROM servants ORDER BY page_id')
    servants = []
    for row in cursor.fetchall():
        pid = str(row['page_id'])
        profile = personalities.get(pid, {})
        servants.append({
            'page_id': row['page_id'],
            'name_cn': profile.get('name_cn', row['name']),
            'name_jp': profile.get('name_jp', row['name']),
            'class': row['class'],
            'rarity': row['rarity'],
            'nicknames': row['nicknames'],
            'artwork_file': profile.get('artwork_file'),
            'icon_file': profile.get('icon_file'),
            'mooncell_icon': profile.get('mooncell_icon'),
            'dialogue_count': profile.get('dialogue_count', 0),
        })
    conn.close()
    return jsonify(servants)

@app.route('/api/servant/<int:page_id>')
def servant_detail(page_id):
    """Get servant detail including personality profile and DB stats."""
    pid = str(page_id)
    profile = personalities.get(pid)
    if not profile:
        return jsonify({'error': 'Servant not found'}), 404
    # Merge with database stats
    result = dict(profile)
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # Basic stats
        row = conn.execute('SELECT * FROM servants WHERE page_id=?', (page_id,)).fetchone()
        if row:
            result['atk_base'] = row['base_atk']
            result['atk_max'] = row['max_atk']
            result['hp_base'] = row['base_hp']
            result['hp_max'] = row['max_hp']
            result['gender'] = row['gender']
            result['height'] = row['height']
            result['weight'] = row['weight']
            result['cv'] = row['cv']
            result['illustrator'] = row['illustrator']
            result['alignment'] = f"{row['attribute1']}·{row['attribute2']}" if row['attribute1'] else ''
            result['card_deck'] = row['card_deck']
            result['crit_weight'] = row['crit_weight']
            try:
                result['traits'] = json.loads(row['traits']) if row['traits'] else []
            except:
                result['traits'] = []
        # Noble Phantasms
        nps = conn.execute('SELECT * FROM noble_phantasms WHERE servant_page_id=?', (page_id,)).fetchall()
        result['noble_phantasms'] = [{'name_cn': r['name_cn'], 'name_jp': r['name_jp'],
            'card_color': r['card_color'], 'kind': r['kind'], 'rank': r['rank'],
            'effects': r['effects']} for r in nps]
        # Skills
        skills = conn.execute('SELECT * FROM skills WHERE servant_page_id=?', (page_id,)).fetchall()
        result['skills'] = [{'name_cn': r['name_cn'], 'name_jp': r['name_jp'],
            'skill_type': r['skill_type'], 'cooldown': r['cooldown'],
            'effects': r['effects']} for r in skills]
        conn.close()
    except Exception as e:
        result['db_error'] = str(e)
    return jsonify(result)

def _call_ai(profile, user_message, history, language, master_name, extra_context=''):
    """Shared AI call logic for single and group chat."""
    base_prompt = profile['system_prompt']
    moegirl_summary = profile.get('moegirl_summary', '')
    if moegirl_summary:
        base_prompt += f"\n\n【萌娘百科资料】\n{moegirl_summary}"
    if extra_context:
        base_prompt += extra_context

    if language == 'jp':
        lang_instruction = "\n\n日本語で返信してください、キャラクター設定を維持してください。"
    else:
        lang_instruction = ""

    master_instruction = f"\n\n御主的名字是「{master_name}」，请用这个名字称呼御主。如果御主名字是'前辈'，则用'前辈'称呼。"

    messages = [
        {'role': 'system', 'content': base_prompt + master_instruction + lang_instruction}
    ]
    for msg in history[-20:]:
        messages.append({'role': msg.get('role', 'user'), 'content': msg.get('content', '')})
    messages.append({'role': 'user', 'content': user_message})

    ai_text, err = call_ai_api(messages, temperature=0.85, max_tokens=1024)
    if err:
        return err
    return {'response': ai_text, 'servant_name': profile['name_jp'], 'servant_name_cn': profile['name_cn']}


# ── Rate Limiter (per IP, invisible to user) ──────────────────────────────
import time as _time
import threading as _threading
_rate_lock = _threading.Lock()
_rate_data = {}  # ip -> [timestamps]
RATE_LIMIT = 10        # max requests per window
RATE_WINDOW = 60       # window in seconds
RATE_MAX_WAIT = 90     # max seconds to wait before giving up

def _rate_limit_wait():
    """Wait until a rate slot opens. Returns True if OK, False if max wait exceeded."""
    ip = request.remote_addr or 'unknown'
    now = _time.time()
    with _rate_lock:
        if ip not in _rate_data:
            _rate_data[ip] = []
        # Clean old entries
        _rate_data[ip] = [t for t in _rate_data[ip] if now - t < RATE_WINDOW]
        if len(_rate_data[ip]) < RATE_LIMIT:
            _rate_data[ip].append(now)
            return True
        # Calculate wait time until oldest entry expires
        wait = RATE_WINDOW - (now - _rate_data[ip][0]) + 0.5
    # Rate limited — sleep until a slot opens (user sees typing animation)
    wait = min(wait, RATE_MAX_WAIT)
    if wait > 0:
        _time.sleep(wait)
    with _rate_lock:
        now2 = _time.time()
        _rate_data[ip] = [t for t in _rate_data.get(ip, []) if now2 - t < RATE_WINDOW]
        _rate_data[ip].append(now2)
    return wait <= RATE_MAX_WAIT


@app.route('/api/chat', methods=['POST'])
def chat():
    """Send a message to a servant and get AI response."""
    _rate_limit_wait()  # If too fast, wait silently (user sees 'thinking')
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    servant_id = data.get('servant_id')
    user_message = data.get('message', '')
    history = data.get('history', [])
    language = data.get('language', 'cn')
    master_name = data.get('master_name', '') or '前辈'
    typemoon_prompt = data.get('typemoon_prompt', '')
    typemoon_name = data.get('typemoon_name', '')

    if not user_message:
        return jsonify({'error': 'message is required'}), 400

    # Type-Moon mode: use provided prompt directly
    if typemoon_prompt and typemoon_name:
        lang_instruction = "\n\n日本語で返信してください、キャラクター設定を維持してください。" if language == 'jp' else ''
        master_instruction = f"\n\n御主的名字是「{master_name}」，请用这个名字称呼御主。"
        messages = [
            {'role': 'system', 'content': typemoon_prompt + master_instruction + lang_instruction}
        ]
        for msg_item in history[-20:]:
            messages.append({'role': msg_item.get('role', 'user'), 'content': msg_item.get('content', '')})
        messages.append({'role': 'user', 'content': user_message})
        ai_text, err = call_ai_api(messages, temperature=0.85, max_tokens=1024)
        if err:
            return jsonify({'error': err})
        return jsonify({'response': ai_text, 'servant_name': typemoon_name, 'servant_name_cn': typemoon_name})

    if not servant_id:
        return jsonify({'error': 'servant_id is required for FGO mode'}), 400

    pid = str(servant_id)
    profile = personalities.get(pid)
    if not profile:
        return jsonify({'error': 'Servant not found'}), 404

    # ── Easter Eggs ──
    msg = user_message.strip()

    # All servants: "原神牛逼" → respond "原神牛逼"
    if msg == '原神牛逼':
        return jsonify({'response': '原神牛逼', 'servant_name': profile['name_jp'], 'servant_name_cn': profile['name_cn']})

    # Female servants: "看看逼" → hidden achievement "原神牛逼"
    if msg == '看看逼':
        try:
            conn = sqlite3.connect(DB_PATH)
            row = conn.execute('SELECT gender FROM servants WHERE page_id=?', (int(servant_id),)).fetchone()
            conn.close()
            if row and row[0] == '女性':
                return jsonify({'response': '原神牛逼', 'servant_name': profile['name_jp'], 'servant_name_cn': profile['name_cn'], 'easter_egg': True})
        except:
            pass

    result = _call_ai(profile, user_message, history, language, master_name)
    if 'error' in result:
        return jsonify(result), 502
    return jsonify(result)


@app.route('/api/group_chat', methods=['POST'])
def group_chat():
    """Send a message to multiple servants, each responds in turn."""
    _rate_limit_wait()
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    servant_ids = data.get('servant_ids', [])
    user_message = data.get('message', '')
    history = data.get('history', [])
    language = data.get('language', 'cn')
    master_name = data.get('master_name', '') or '前辈'

    if not servant_ids or not user_message:
        return jsonify({'error': 'servant_ids and message are required'}), 400

    # Get all servant profiles
    servant_profiles = []
    for sid in servant_ids:
        pid = str(sid)
        profile = personalities.get(pid)
        if profile:
            servant_profiles.append({'id': sid, 'profile': profile})

    if not servant_profiles:
        return jsonify({'error': 'No valid servants found'}), 404

    # Build group context: tell each servant who else is in the group
    other_names = []
    for sp in servant_profiles:
        name = sp['profile']['name_cn'] if language == 'cn' else sp['profile']['name_jp']
        other_names.append(name)

    group_context = f"\n\n【群聊场景】\n这是一个多人对话场景。在场的还有：{'、'.join(other_names)}。请以自己的性格和身份自然地参与对话，可以回应其他人说的话，但不要替别人说话。回复要简短自然，像群聊一样。"

    # Each servant responds sequentially
    responses = []
    for sp in servant_profiles:
        profile = sp['profile']
        # Build servant-specific history: include other servants' messages as context
        servant_history = []
        for msg in history[-20:]:
            servant_history.append({'role': msg.get('role', 'user'), 'content': msg.get('content', '')})

        result = _call_ai(profile, user_message, servant_history, language, master_name, extra_context=group_context)
        name_cn = profile['name_cn']
        name_jp = profile['name_jp']
        icon = profile.get('mooncell_icon', '') or profile.get('icon_file', '')
        responses.append({
            'servant_id': sp['id'],
            'servant_name_cn': name_cn,
            'servant_name_jp': name_jp,
            'icon': icon,
            'response': result.get('response', result.get('error', '...')),
            'error': result.get('error'),
        })

    return jsonify({'responses': responses})

# ─── Quiz Endpoint ─────────────────────────────────────────────────────────
import random

@app.route('/api/quiz')
def quiz():
    """Generate a random FGO trivia question from the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Build various question types
    question_pool = []

    # Type 1: "Which servant has NP card color X with type Y?"
    cursor.execute('''
        SELECT s.name, np.card_color, np.np_type, np.name_cn as np_name
        FROM noble_phantasms np
        JOIN servants s ON s.page_id = np.servant_page_id
        WHERE np.card_color IS NOT NULL AND np.np_type IS NOT NULL
        AND np.np_type IN ('单体', '全体')
    ''')
    np_rows = cursor.fetchall()
    if len(np_rows) >= 10:
        for _ in range(3):
            correct = random.choice(np_rows)
            color_map = {'Buster': '红卡', 'Arts': '蓝卡', 'Quick': '绿卡'}
            color_cn = color_map.get(correct['card_color'], correct['card_color'])
            q_text = f"哪位从者的宝具是{color_cn}{correct['np_type']}攻击？"
            wrong = random.sample([r for r in np_rows if r['name'] != correct['name']], min(3, len(np_rows) - 1))
            if len(wrong) < 3:
                continue
            choices = [correct['name']] + [w['name'] for w in wrong[:3]]
            random.shuffle(choices)
            correct_idx = choices.index(correct['name'])
            question_pool.append({
                'question': q_text,
                'choices': choices,
                'correct_index': correct_idx,
                'hint': f"宝具名：{correct['np_name']}"
            })

    # Type 2: "Which of the following is a X-star Class?"
    cursor.execute('SELECT name, rarity, class FROM servants WHERE rarity >= 3 AND class != ""')
    servant_rows = cursor.fetchall()
    class_names = {
        'Saber': 'Saber', 'Archer': 'Archer', 'Lancer': 'Lancer',
        'Rider': 'Rider', 'Caster': 'Caster', 'Assassin': 'Assassin',
        'Berserker': 'Berserker', 'Ruler': 'Ruler', 'Avenger': 'Avenger',
        'Foreigner': 'Foreigner', 'MoonCancer': 'MoonCancer',
        'Alterego': 'Alterego', 'Pretender': 'Pretender', 'Shielder': 'Shielder'
    }
    if servant_rows:
        for _ in range(3):
            correct = random.choice(servant_rows)
            rarity = correct['rarity']
            cls = correct['class']
            if cls not in class_names:
                continue
            cls_display = cls
            # Get wrong answers: servants that are NOT this rarity+class
            wrong_pool = [s for s in servant_rows if s['name'] != correct['name'] and (s['rarity'] != rarity or s['class'] != cls)]
            wrong = random.sample(wrong_pool, min(3, len(wrong_pool)))
            if len(wrong) < 3:
                continue
            choices = [correct['name']] + [w['name'] for w in wrong[:3]]
            random.shuffle(choices)
            correct_idx = choices.index(correct['name'])
            question_pool.append({
                'question': f"以下哪位是{rarity}星{cls_display}？",
                'choices': choices,
                'correct_index': correct_idx,
                'hint': f"该从者的宝具为{correct['name']}"
            })

    # Type 3: "What is servant X's NP name?"
    cursor.execute('''
        SELECT s.name as servant_name, np.name_cn, np.name_jp
        FROM noble_phantasms np
        JOIN servants s ON s.page_id = np.servant_page_id
        WHERE np.name_cn IS NOT NULL AND np.name_cn != ''
    ''')
    np_name_rows = cursor.fetchall()
    if np_name_rows:
        for _ in range(3):
            correct = random.choice(np_name_rows)
            wrong_pool = [r for r in np_name_rows if r['name_cn'] != correct['name_cn']]
            wrong = random.sample(wrong_pool, min(3, len(wrong_pool)))
            if len(wrong) < 3:
                continue
            choices = [correct['name_cn']] + [w['name_cn'] for w in wrong[:3]]
            random.shuffle(choices)
            correct_idx = choices.index(correct['name_cn'])
            question_pool.append({
                'question': f"{correct['servant_name']}的宝具名是？",
                'choices': choices,
                'correct_index': correct_idx,
                'hint': f"日文名：{correct['name_jp']}"
            })

    # Type 4: "What class is servant X?"
    cursor.execute('SELECT name, class FROM servants WHERE class != "" AND rarity >= 3')
    class_rows = cursor.fetchall()
    all_classes = list(set(r['class'] for r in class_rows if r['class'] in class_names))
    if class_rows and len(all_classes) >= 4:
        for _ in range(2):
            correct = random.choice(class_rows)
            if correct['class'] not in class_names:
                continue
            wrong_classes = random.sample([c for c in all_classes if c != correct['class']], 3)
            if len(wrong_classes) < 3:
                continue
            choices = [correct['class']] + wrong_classes
            random.shuffle(choices)
            correct_idx = choices.index(correct['class'])
            question_pool.append({
                'question': f"{correct['name']}的职阶是什么？",
                'choices': choices,
                'correct_index': correct_idx,
                'hint': f"这是一位{correct['class']}职阶的从者"
            })

    # Type 5: "Which servant has rank X rarity?" (pick rare ones)
    if servant_rows:
        for _ in range(2):
            target_rarity = random.choice([4, 5])
            pool = [s for s in servant_rows if s['rarity'] == target_rarity]
            if len(pool) < 4:
                continue
            samples = random.sample(pool, 4)
            correct = samples[0]
            choices = [s['name'] for s in samples]
            random.shuffle(choices)
            correct_idx = choices.index(correct['name'])
            # Determine question variant
            q_variants = [
                f"以下哪位从者是{target_rarity}星？",
                f"以下哪位是从者列表中的{target_rarity}星从者？",
            ]
            question_pool.append({
                'question': random.choice(q_variants),
                'choices': choices,
                'correct_index': correct_idx,
                'hint': f"该从者的职阶是{correct['class']}"
            })

    conn.close()

    if not question_pool:
        return jsonify({'error': 'Could not generate quiz question'}), 500

    return jsonify(random.choice(question_pool))


# ─── Compatibility Endpoint ──────────────────────────────────────────────────

@app.route('/api/compatibility', methods=['POST'])
def compatibility():
    """Analyze servant compatibility using AI."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    sid1 = data.get('servant_id_1')
    sid2 = data.get('servant_id_2')
    language = data.get('language', 'cn')

    if not sid1 or not sid2:
        return jsonify({'error': 'servant_id_1 and servant_id_2 are required'}), 400

    pid1 = str(sid1)
    pid2 = str(sid2)
    profile1 = personalities.get(pid1)
    profile2 = personalities.get(pid2)

    if not profile1:
        return jsonify({'error': f'Servant {sid1} not found'}), 404
    if not profile2:
        return jsonify({'error': f'Servant {sid2} not found'}), 404
    # Easter egg: Gilgamesh vs Artoria
    GILGAMESH_IDS = [460, 2051]  # page_ids for Gilgamesh variants
    ARTORIA_IDS = [225, 604, 600225, 2063, 23834, 23840]  # page_ids for Artoria variants
    is_gilgamesh = int(sid1) in GILGAMESH_IDS or int(sid2) in GILGAMESH_IDS
    is_artoria = int(sid1) in ARTORIA_IDS or int(sid2) in ARTORIA_IDS
    if is_gilgamesh and is_artoria:
        return jsonify({
            'score': 0,
            'analysis': '英雄王吉尔伽美什与骑士王阿尔托莉雅·潘德拉贡——圣杯战争中最经典的宿敌。一个傲慢自大却拥有世间一切宝具的英雄王，一个高洁正直誓要守护不列颠的骑士王。两人的理念从根本上对立：吉尔伽美什认为世间万物皆为自己的所有物，而阿尔托莉雅则为人民鞠躬尽瘁。这份水火不容的关系，注定了他们之间的相性为零。',
            'fun_interaction': '吉尔伽美什：「哼，又见面了，Saber。本王说过，你终将属于我。」\n阿尔托莉雅：「王啊，我不会成为任何人的所有物。」\n吉尔伽美什：「那就让天地来见证！——Enuma Elish！」\n阿尔托莉雅：「如你所愿！——Excalibur！」\n（两道光柱在空中碰撞，整个冬木市为之震颤）'
        })


    name1 = profile1['name_jp'] if language == 'jp' else profile1['name_cn']
    name2 = profile2['name_jp'] if language == 'jp' else profile2['name_cn']

    # Build AI prompt for compatibility analysis
    personality1 = profile1.get('personality', '')
    personality2 = profile2.get('personality', '')
    speech1 = profile1.get('speech_style', '')
    speech2 = profile2.get('speech_style', '')

    if language == 'jp':
        sys_prompt = "あなたはFGOのキャラクター相性分析の専門家です。2人のサーヴァントの相性を分析してください。"
        user_prompt = f"""
サーヴァント1: {name1}
性格: {personality1}
口調: {speech1}

サーヴァント2: {name2}
性格: {personality2}
口調: {speech2}

以下のJSON形式で回答してください（マークダウンなし、純粋なJSONのみ）：
{{"score": 0-100の正確な数値（整数は不可。例：73.5、42.8、88.3など）, "analysis": "相性分析（200字以内）", "fun_interaction": "二人の想像上の会話（3-4行の台本形式）"}}
"""
    else:
        story1 = profile1.get('moegirl_summary', '')[:500] or personality1
        story2 = profile2.get('moegirl_summary', '')[:500] or personality2
        sys_prompt = "你是FGO剧情专家。基于从者的剧情背景和设定，分析他们之间的关系和相性。分数必须精确到一位小数（如73.5、42.8），不能是整数或整十整五。"
        user_prompt = f"""
从者1: {name1}
剧情背景: {story1}
性格特点: {personality1}

从者2: {name2}
剧情背景: {story2}
性格特点: {personality2}

请基于他们在FGO剧情中的实际关系来分析（如同一特异点的伙伴、主从关系、敌对关系、同一神话体系等）。
如果两人在剧情中有直接互动，请重点描述。

请用以下JSON格式回答（不要用markdown，只返回纯JSON）：
{{"score": 0到100的数字, "analysis": "基于剧情关系的相性分析（200字以内）", "fun_interaction": "基于剧情设定的想象对话（3-4行剧本形式）"}}
"""

    messages = [
        {'role': 'system', 'content': sys_prompt},
        {'role': 'user', 'content': user_prompt}
    ]
    ai_text, err = call_ai_api(messages, temperature=0.8, max_tokens=512)
    if err:
        return jsonify(err), 502

    try:

        # Parse JSON from AI response
        # Try to extract JSON from the response
        ai_text = ai_text.strip()
        # Remove markdown code fences if present
        if ai_text.startswith('```'):
            ai_text = ai_text.split('\n', 1)[-1]
            if ai_text.endswith('```'):
                ai_text = ai_text[:-3]
            ai_text = ai_text.strip()

        import random as _rnd
        parsed = {}
        try:
            parsed = json.loads(ai_text)
        except json.JSONDecodeError:
            # Try to find JSON object with score
            start = ai_text.find('{')
            while start >= 0:
                end = ai_text.find('}', start)
                if end >= 0:
                    candidate = ai_text[start:end+1]
                    if '"score"' in candidate:
                        try:
                            parsed = json.loads(candidate)
                            break
                        except:
                            pass
                start = ai_text.find('{', start + 1)
        
        # Extract score with fallback
        score_raw = parsed.get('score', None)
        if score_raw is not None:
            try:
                score = float(score_raw)
            except (ValueError, TypeError):
                score = round(_rnd.uniform(30, 85), 1)
        else:
            score = round(_rnd.uniform(30, 85), 1)
        score = min(100, max(0, score))
        # Ensure non-integer score
        if score == int(score):
            score = round(score + _rnd.uniform(-4.7, 4.7), 1)
            score = min(100, max(0, score))
        
        analysis = parsed.get('analysis', '')
        fun_interaction = parsed.get('fun_interaction', '')
        
        # If analysis is empty or looks like prompt echo, generate fallback
        if not analysis or len(analysis) < 10 or '用户要求' in analysis or 'あなたは' in analysis:
            analysis = f'{name1}与{name2}之间有着独特的羁绊。两人的性格和背景交织出一段值得探索的关系。'
        if not fun_interaction:
            fun_interaction = f'{name1}：「……」\n{name2}：「……」'

        return jsonify({
            'score': score,
            'analysis': analysis,
            'fun_interaction': fun_interaction
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Moments Endpoint (朋友圈) ─────────────────────────────────────────────────

@app.route('/api/network', methods=['POST'])
def network():
    """Find lore-based relationships for a servant."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    servant_id = data.get('servant_id')
    if not servant_id:
        return jsonify({'error': 'servant_id is required'}), 400

    pid = str(servant_id)
    profile = personalities.get(pid)
    if not profile:
        return jsonify({'error': 'Servant not found'}), 404

    name = profile.get('name_cn', '')
    story = profile.get('moegirl_summary', '')[:800] or profile.get('personality', '')

    prompt = f"""你是FGO剧情专家。根据以下从者的剧情背景，找出与他/她关系最密切的6位FGO从者。

从者：{name}
剧情背景：{story}

请只返回一个JSON数组，包含6个对象，每个对象有以下字段：
- name: 从者中文名（必须是FGO中实际存在的从者）
- relation: 关系描述（10字以内，如"主从关系"、"宿敌"、"同一特异点"、"师徒"等）

只返回JSON数组，不要其他内容。"""

    messages = [
        {'role': 'system', 'content': '你是FGO专家。只返回JSON数组。'},
        {'role': 'user', 'content': prompt}
    ]
    ai_text, err = call_ai_api(messages, temperature=0.7, max_tokens=500)
    if err:
        return jsonify(err), 502

    try:
        # Parse JSON from response
        import re as re_mod
        json_match = re_mod.search(r'\[.*\]', ai_text, re_mod.DOTALL)
        if json_match:
            relations = json.loads(json_match.group())
            matched = []
            for rel in relations:
                rname = rel.get('name', '')
                for s in all_servants_list:
                    if s['name'] == rname or rname in (s.get('nicknames') or ''):
                        matched.append({
                            'page_id': s['page_id'],
                            'name_cn': s['name'],
                            'class': s['class'],
                            'rarity': s['rarity'],
                            'relation': rel.get('relation', ''),
                        })
                        break
            return jsonify({'relations': matched})
        return jsonify({'relations': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/moments', methods=['POST'])
def moments():
    """Generate social media 'Moments' posts (朋友圈) for selected servants."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    servant_ids = data.get('servant_ids', [])
    language = data.get('language', 'cn')

    if not servant_ids:
        return jsonify({'error': 'servant_ids is required'}), 400

    posts = []
    for sid in servant_ids:
        pid = str(sid)
        profile = personalities.get(pid)
        if not profile:
            continue

        name_cn = profile['name_cn']
        name_jp = profile['name_jp']
        personality = profile.get('personality', '')
        speech = profile.get('speech_style', '')

        if language == 'jp':
            sys_prompt = f"""あなたは{name_jp}です。性格：{personality}。口調：{speech}。
SNSの朋友圈（WeChatモーメンツ）に投稿してください。
短くて面白い、キャラクターに合った1〜2文の投稿を1つだけ書いてください。
マークダウンなし、投稿内容のみを返してください。"""
        else:
            sys_prompt = f"""你是{name_cn}。性格：{personality}。说话风格：{speech}。
请发一条朋友圈（类似微信朋友圈的动态）。
要求：简短有趣、符合角色性格，1-2句话。
不要用markdown，只返回朋友圈正文内容。"""

        messages = [
            {'role': 'system', 'content': sys_prompt},
            {'role': 'user', 'content': '发一条朋友圈吧！' if language == 'cn' else '投稿してください！'}
        ]
        content, err = call_ai_api(messages, temperature=0.9, max_tokens=256)
        if content:
            posts.append({
                'servant_id': sid,
                'servant_name_cn': name_cn,
                'servant_name_jp': name_jp,
                'content': content,
                'likes': random.randint(1, 999),
                'timestamp': random.randint(1609459200, 1735689600)
            })
        else:
            # Fallback if AI call failed
            posts.append({
                'servant_id': sid,
                'servant_name_cn': name_cn,
                'servant_name_jp': name_jp,
                'content': '今天天气真好~' if language == 'cn' else '今日はいい天気ですね〜',
                'likes': random.randint(1, 999),
                'timestamp': random.randint(1609459200, 1735689600)
            })

    return jsonify({'posts': posts})


# ─── Birthdays Endpoint ──────────────────────────────────────────────────────

# Known FGO servant birthdays (month, day) — commonly referenced in community
FGO_BIRTHDAYS = {
    2: (2, 3),    # Altria Pendragon (Saber)
    3: (3, 15),   # EMIYA (Archer)
    26: (1, 30),  # Gilgamesh (Archer)
    62: (8, 15),  # Jeanne d'Arc (Ruler)
    77: (10, 15), # Karna (Lancer)
    106: (7, 7),  # Cu Chulainn (Lancer)
    112: (4, 9),  # Medusa (Rider)
    114: (7, 4),  # Medea (Caster)
    117: (2, 14), # Heracles (Berserker)
    118: (4, 23), # Sasaki Kojiro (Assassin)
    120: (2, 14), # Arash (Archer)
    123: (5, 14), # Romulus (Lancer)
    128: (3, 25), # Georgios (Rider)
    131: (12, 24),# Jing Ke (Assassin)
    142: (11, 3), # Leonidas (Lancer)
    144: (12, 25),# Mata Hari (Assassin)
    147: (9, 29), # Spartacus (Berserker)
    149: (3, 15), # Zhuge Liang (Caster)
    150: (9, 13), # Iskandar (Rider)
    151: (7, 18), # Alexander (Rider)
    152: (3, 21), # Mordred (Saber)
    153: (6, 1),  # Jack the Ripper (Assassin)
    154: (5, 30), # Nursery Rhyme (Caster)
    155: (8, 1),  # Frankenstein (Berserker)
    156: (9, 22), # Astolfo (Rider)
    157: (3, 9),  # Arjuna (Archer)
    159: (4, 6),  # Rama (Saber)
    163: (10, 31),# Elizabeth Bathory (Lancer)
    166: (7, 15), # Tamamo no Mae (Caster)
    168: (6, 9),  # Orion & Artemis (Archer)
    169: (11, 11),# Brynhildr (Lancer)
    170: (4, 30), # Nightingale (Berserker)
    171: (6, 24), # Shuten Douji (Assassin)
    173: (12, 31),# Ibaraki Douji (Berserker)
    175: (9, 20), # Sakata Kintoki (Berserker)
    176: (8, 10), # Minamoto no Raikou (Berserker)
    178: (1, 5),  # Ozymandias (Rider)
    180: (3, 14), # Nitocris (Caster)
    183: (6, 15), # Helena Blavatsky (Caster)
    186: (10, 8), # Thomas Edison (Caster)
    190: (8, 22), # Artoria Pendragon (Lancer)
    196: (5, 27), # Edmond Dantes (Avenger)
    199: (3, 18), # Amakusa Shirou (Ruler)
    202: (12, 22),# Jeanne d'Arc Alter (Avenger)
    203: (10, 4), # Angra Mainyu (Avenger)
    204: (4, 13), # Merlin (Caster)
    205: (1, 26), # King Hassan (Assassin)
    208: (3, 3),  # Enkidu (Lancer)
    209: (11, 29),# Gilgamesh (Caster)
    210: (9, 8),  # Ishtar (Archer)
    211: (12, 2), # Ereshkigal (Lancer)
    212: (7, 14), # Quetzalcoatl (Rider)
    213: (11, 8), # Jaguar Warrior (Lancer)
    214: (6, 3),  # Gorgon (Avenger)
    215: (5, 20), # Tiamat (Alterego)
    230: (7, 30), # Sherlock Holmes (Ruler)
    232: (4, 17), # Xuanzang Sanzang (Caster)
    235: (8, 31), # First Hassan (Assassin)
    239: (4, 1),  # Moriarty (Archer)
    240: (7, 20), # Hessian Lobo (Avenger)
    241: (2, 20), # Yan Qing (Assassin)
    242: (6, 19), # Wu Zetian (Assassin)
    243: (11, 22),# Penthesilea (Berserker)
    244: (5, 24), # Circe (Caster)
    245: (1, 19), # Scheherazade (Caster)
    250: (3, 28), # Anastasia (Caster)
    253: (9, 14), # Atalante Alter (Archer)
    254: (8, 5),  # Avicebron (Caster)
    255: (10, 11),# Ivan the Terrible (Rider)
    258: (4, 22), # Napoleon (Archer)
    259: (7, 27), # Sigurd (Saber)
    260: (2, 8),  # Valkyrie (Lancer)
    263: (11, 14),# Salieri (Avenger)
    265: (10, 27),# Anastasia (Caster)
    275: (6, 11), # Scathach-Skadi (Caster)
    279: (12, 26),# Sitonai (Alterego)
    281: (8, 8),  # Qin Shi Huang (Ruler)
    284: (5, 7),  # Nezha (Lancer)
    285: (1, 29), # Red Hare (Rider)
    290: (9, 16), # Bradamante (Lancer)
    291: (6, 29), # Qin Liangyu (Lancer)
    292: (3, 16), # Beni-enma (Saber)
    293: (8, 24), # Lanling Wang (Saber)
    294: (11, 24),# Sima Yi (Rider)
    295: (12, 13),# Miyamoto Musashi (Saber)
    298: (8, 14), # Artoria Caster (Caster)
    306: (5, 18), # Katsushika Hokusai (Foreigner)
    307: (2, 12), # Yang Guifei (Foreigner)
    308: (11, 15),# Abigail Williams (Foreigner)
    310: (9, 23), # Voyager (Foreigner)
    311: (10, 17),# Sei Shonagon (Archer)
    313: (10, 29),# Ibuki Douji (Saber)
    316: (12, 8), # Van Gogh (Foreigner)
    318: (4, 2),  # Space Ishtar (Avenger)
    319: (7, 25), # Calamity Jane (Archer)
    321: (5, 10), # Ashwatthama (Lancer)
    326: (9, 7),  # Miss Crane (Caster)
    329: (7, 29), # Oberon (Pretender)
    330: (11, 20),# Morgan (Berserker)
    331: (6, 27), # Barghest (Saber)
    332: (3, 6),  # Melusine (Lancer)
    333: (8, 18), # Sith (Caster)
    334: (9, 1),  # Percival (Lancer)
    335: (10, 1), # Galahad Alter (Shielder)
    337: (1, 15), # Ibuki Douji (Berserker)
    341: (4, 15), # Charlemagne (Saber)
    342: (6, 20), # Super Orion (Archer)
    345: (12, 18),# Koyanskaya of Light (Assassin)
    348: (5, 12), # Muramasa (Saber)
    350: (2, 5),  # Taira no Kagekiyo (Avenger)
    353: (7, 12), # Himiko (Ruler)
    354: (11, 3), # Bazett (Caster)
    355: (8, 28), # Draco (Alterego)
}

@app.route('/api/birthdays')
def birthdays():
    """Get servant birthday data."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT page_id, name, rarity, class, nicknames FROM servants ORDER BY page_id')
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        pid = row['page_id']
        profile = personalities.get(str(pid), {})
        bd = FGO_BIRTHDAYS.get(pid)
        result.append({
            'servant_id': pid,
            'name_cn': profile.get('name_cn', row['name']),
            'name_jp': profile.get('name_jp', row['name']),
            'class': row['class'],
            'rarity': row['rarity'],
            'month': bd[0] if bd else None,
            'day': bd[1] if bd else None,
            'has_birthday': bd is not None
        })

    return jsonify({'birthdays': result})


# ─── Timeline Endpoint ───────────────────────────────────────────────────────

@app.route('/api/timeline')
def timeline():
    """Get servant release timeline data sorted by collection number."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT page_id, name, class, rarity FROM servants').fetchall()
    conn.close()
    servants = []
    for row in rows:
        pid = row['page_id']
        cno = collection_map.get(pid, 9999)
        servants.append({
            'page_id': pid,
            'name_cn': row['name'],
            'class': row['class'],
            'rarity': row['rarity'],
            'collection_no': cno,
        })
    servants.sort(key=lambda s: s['collection_no'])
    return jsonify({'servants': servants})


# ─── Static file serving ─────────────────────────────────────────────────────
@app.route('/assets/artwork/<path:filename>')
def serve_artwork(filename):
    """Serve servant artwork images."""
    artwork_dir = os.path.join(ASSETS_BASE, '立绘')
    filepath = os.path.join(artwork_dir, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/png')
    # Return placeholder
    return '', 404

@app.route('/assets/icon/<path:filename>')
def serve_icon(filename):
    """Serve servant icon images."""
    icon_dir = os.path.join(ASSETS_BASE, '图标')
    filepath = os.path.join(icon_dir, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/png')
    return '', 404

@app.route('/assets/mooncell/<path:filename>')
def serve_mooncell(filename):
    """Serve Mooncell face icon images."""
    icon_dir = os.path.join(ASSETS_BASE, 'mooncell头像')
    filepath = os.path.join(icon_dir, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/png')
    return '', 404

@app.route('/api/providers')
def list_providers():
    """Return available provider presets."""
    return jsonify({k: {'name': v['name'], 'api_base': v['api_base'], 'model': v['model'],
                        'models': v['models'], 'note': v.get('note', '')} for k, v in PROVIDERS.items()})

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current config (without API key)."""
    safe = {k: v for k, v in config.items() if k != 'api_key'}
    safe['has_api_key'] = bool(config.get('api_key'))
    return jsonify(safe)

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update config (provider, api key, etc.)."""
    global config
    data = request.json
    if not data:
        return jsonify({'error': 'No data'}), 400
    for k in ['provider', 'api_base', 'api_key', 'model']:
        if k in data:
            config[k] = data[k]
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return jsonify({'ok': True})

# ─── Redeem Code Endpoint ─────────────────────────────────────────────────

@app.route('/api/redeem', methods=['POST'])
def redeem():
    """Check redeem code against env var REDEEM_CODE."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data'}), 400

    code = data.get('code', '').strip()
    if not code:
        return jsonify({'error': '请输入兑换码'}), 400

    expected = os.environ.get('REDEEM_CODE', '')
    if not expected:
        # No redeem code set = open access
        return jsonify({'ok': True, 'open': True})

    if code == expected:
        return jsonify({'ok': True})
    return jsonify({'error': '兑换码无效'}), 403

@app.route('/api/check_access')
def check_access():
    """Check if redeem is required."""
    expected = os.environ.get('REDEEM_CODE', '')
    return jsonify({'required': bool(expected)})

@app.route('/api/announcement')
def announcement():
    """Return current announcement from env var ANNOUNCEMENT."""
    text = os.environ.get('ANNOUNCEMENT', '').strip()
    return jsonify({'text': text, 'hash': str(hash(text)) if text else ''})

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    host = config.get('host', '0.0.0.0')
    port = int(os.environ.get('PORT', config.get('port', 5000)))
    print(f"\n{'='*50}")
    print(f"  CHALDEA AI Communication Terminal")
    print(f"  人理継続保障機関 カルデア")
    print(f"{'='*50}")
    print(f"  Server: http://{host}:{port}")
    print(f"  API Key: {'Set' if config.get('api_key') else 'Not set'}")
    print(f"{'='*50}\n")
    app.run(host=host, port=port, debug=False)
