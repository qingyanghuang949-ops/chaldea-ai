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
    'grok': {
        'name': 'Grok (xAI)',
        'api_base': 'https://api.x.ai/v1',
        'model': 'grok-3',
        'models': ['grok-3', 'grok-3-mini', 'grok-2', 'grok-2-mini'],
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
    api_key = env_key or cfg_key
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

@app.route('/assets/typemoon_icons/<path:filename>')
def serve_typemoon_icon(filename):
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'typemoon_icons', filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    return '', 404

@app.route('/assets/chaldea_logo.png')
def serve_chaldea_logo():
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'chaldea_logo.png')
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/png')
    return '', 404

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
RATE_LIMIT = 9999       # max requests per window (effectively unlimited)
RATE_WINDOW = 60       # window in seconds
RATE_MAX_WAIT = 0      # no wait — instant response

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
    msg_count = data.get('msg_count', 0)
    anomaly_mode = data.get('anomaly_mode', False)

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
            err_msg = err.get('error', str(err)) if isinstance(err, dict) else str(err)
            return jsonify({'error': err_msg})
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

    # ── Anomaly Mode: 迦勒底的异常 ──
    extra_context = ''
    if anomaly_mode and msg_count >= 3:
        name = profile.get('name_cn', '')
        if '玛修' in name:
            # Mashu special response about 迦勒底亚斯
            extra_context = """

【紧急指令 - 迦勒底异常事件】
御主刚刚向你询问了迦勒底最近的异常情况。请用玛修的口吻回答：
迦勒底亚斯最近很奇怪，观测透镜示巴的数据出现了严重偏差，迦勒底亚斯表面的灯火正在逐渐熄灭。
你很担心，但罗曼医生说还在调查中。请建议御主亲自去和迦勒底亚斯对话，也许能发现什么。
注意：用玛修温柔、关切、略带担忧的语气，称呼御主为「御主」或「前辈」。回复不要太长，3-4句话即可。"""
        else:
            # All other servants notice something abnormal
            anomaly_hints = {
                'Saber': '最近总觉得迦勒底的气氛不太对。训练场的魔力流动有些紊乱，灵子转移的校准也出现了偏差。身为骑士，对危机的直觉一向很准。建议御主去问问玛修，她一直在中央管制室，也许知道些什么。',
                'Archer': '弓兵的直觉告诉我，有什么东西在变化。示巴透镜的观测数据最近出现了异常，迦勒底亚斯的灯火……似乎在减少。御主，你应该去找玛修谈谈，她比我更了解管制室的情况。',
                'Lancer': '最近总觉得哪里不对劲。战斗时灵子的回路偶尔会不稳定，像是有什么东西在干扰迦勒底的基盘。御主，去问问玛修吧，她在管制室应该能察觉到什么。',
                'Rider': '骑乘时感觉迦勒底的重力场有些微妙的变化。这种感觉……像是有什么巨大的存在正在苏醒。御主，玛修一直在中央管制室，她可能知道些什么。',
                'Caster': '作为魔术师，我能感知到迦勒底的魔力正在发生微妙的变化。迦勒底亚斯……那个拟似天体的状态最近很不正常。御主，去问问玛修吧，她是和迦勒底亚斯最接近的人。',
                'Assassin': '暗处观察到的……中央管制室的灯光最近总是闪烁不定。示巴透镜的校准频率增加了三倍。御主，如果你想了解真相，去问玛修。',
                'Berserker': '……不对。有什么东西不对。迦勒底的空气……变了。去问玛修。',
                'Avenger': '复仇者的感知告诉我，有什么东西正在崩坏。迦勒底亚斯……那颗虚假的星球，最近散发着令人不安的气息。御主，去问玛修。她比任何人都接近真相。',
                'Ruler': '作为裁定者，我能感觉到这个特异点的秩序正在被某种力量扭曲。迦勒底亚斯的异常……不是自然现象。御主，请去找玛修确认。',
                'Shielder': '作为Shielder，我的职责是守护御主。但最近……我总觉得迦勒底在颤抖。去问问玛修吧，她一直在管制室，应该比我更清楚。',
                'Foreigner': '来自异次元的低语……最近变得更强了。迦勒底亚斯的方向传来令人不安的波动。御主，去问玛修，她也许能给你答案。',
                'Alterego': '我能感觉到……有什么东西在迦勒底亚斯内部蠢蠢欲动。这不是正常的波动。御主，去问问玛修。',
            }
            hint = anomaly_hints.get(profile.get('class', ''), '最近总觉得迦勒底的气氛不太对。灵子转移的精度在下降，示巴透镜的数据也出现了偏差。御主，去问问玛修吧，她在中央管制室应该能察觉到什么。')
            extra_context = f"""

【紧急指令 - 迦勒底异常事件】
你刚才和御主聊了一会儿。在对话的最后，请自然地提起你最近察觉到的迦勒底异常情况。
异常描述（用你自己的语言风格表达）：{hint}
注意：这是一段额外的剧情提示，请在回复的最后自然地加入，不要突兀。用你自己的角色语气来表达，不要照搬原文。回复的最后一句建议御主去和玛修聊聊。"""

    result = _call_ai(profile, user_message, history, language, master_name, extra_context)
    if 'error' in result:
        err = result['error']
        err_msg = err.get('error', str(err)) if isinstance(err, dict) else str(err)
        return jsonify({'error': err_msg}), 502
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

# Special bond database: (pattern_a, pattern_b, bond_type, base_score, description)
_SPECIAL_BONDS = [
    # FSN / Fate route
    ('卫宫$', '阿尔托莉雅·潘德拉贡$', 'lover', 88, '士剑——正义的伙伴与骑士王的永恒之约。即使跨越平行世界，这份羁绊也不会消失。'),
    ('卫宫$', '远坂凛', 'lover', 90, 'UBW线的官配。冷静理性的大小姐与热血笨蛋的互补组合，完美的搭档。'),
    ('卫宫$', '间桐樱', 'lover', 85, 'HF线的深沉之爱。士郎为了樱不惜堕入黑暗，这份感情沉重而真挚。'),
    ('卫宫$', '伊莉雅', 'family', 82, '义兄妹关系。伊莉雅一直在等待的「大哥哥」，跨越了圣杯战争的亲情。'),
    # Knight of the Round Table
    ('阿尔托莉雅·潘德拉贡$', '莫德雷德$', 'complex', 35, '母女？不，是骑士王与叛逆之子。莫德雷德渴望认可，阿尔托莉雅无法回应。悲剧的循环。'),
    ('阿尔托莉雅·潘德拉贡$', '兰斯洛特$', 'complex', 40, '最忠诚的骑士与最愧疚的王。兰斯洛特的堕落是阿尔托莉雅心中永远的痛。'),
    ('阿尔托莉雅·潘德拉贡$', '贝德维尔$', 'friend', 78, '唯一将圣剑归还的忠诚骑士。贝德维尔是最后见证王之终结的人。'),
    ('阿尔托莉雅·潘德拉贡$', '高文$', 'friend', 72, '太阳骑士对王的绝对忠诚。即使在圣杯战争中也会优先保护Master。'),
    # Gilgamesh & Enkidu
    ('吉尔伽美什$', '恩奇都$', 'friend', 95, '「我唯一的朋友」——英雄王一生中最珍贵的羁绊。天之锁与王之财宝，乌鲁克最美的传说。'),
    ('恩奇都$', '吉尔伽美什$', 'friend', 95, '为吉尔伽美什而生的神造之泥人。即使在三千年後，这份友情依然是英雄王最柔软的部分。'),
    ('吉尔伽美什$', '阿尔托莉雅·潘德拉贡$', 'complex', 25, '英雄王的求婚被拒。一个傲慢自大，一个坚守理想——注定的碰撞。'),
    ('吉尔伽美什$', '卫宫$', 'rival', 20, '最古之英雄王最看不起的赝品。但UBW中却被「赝品」的信念所震撼。'),
    # Jeanne d'Arc
    ('贞德$', '吉尔·德·雷$', 'complex', 55, '圣女与堕落的元帅。贞德是吉尔唯一的光，但那道光已经熄灭了。'),
    ('贞德$', '贞德〔Alter〕$', 'rival', 30, '正义与复仇的两面。黑贞是白贞被否定后诞生的愤怒，是对世界的控诉。'),
    ('贞德〔Alter〕$', '贞德$', 'rival', 30, '「我不是你的影子！」——黑贞对白贞的否定，其实也是对自己的否定。'),
    # Tohsaka family
    ('远坂凛$', '间桐樱$', 'family', 45, '被命运拆散的姐妹。凛选择了正义，樱承受了黑暗。血缘无法割断，伤痕也无法愈合。'),
    ('间桐樱$', '卫宫$', 'lover', 85, '「前辈，我一直在等你。」——黑暗中唯一的光，士郎是樱最后的救赎。'),
    # Kiritsugu
    ('卫宫〔Assassin〕$', '阿尔托莉雅·潘德拉贡$', 'complex', 40, '切嗣与Saber的理念冲突。一个不择手段，一个坚守骑士道——注定无法互相理解。'),
    ('卫宫〔Assassin〕$', '伊莉雅$', 'family', 60, '父亲的愧疚。切嗣抛弃了伊莉雅去拯救世界，这份遗憾永远无法弥补。'),
    # Iskandar
    ('伊斯坎达尔$', '吉尔伽美什$', 'friend', 70, '王之酒宴上的两位王。征服王的豁达与英雄王的傲慢，惺惺相惜。'),
    ('伊斯坎达尔$', '韦伯$', 'master_servant', 75, '征服王与他胆小的Master。伊斯坎达尔教会了韦伯什么是「王」。'),
    # Nero
    ('尼禄$', '阿尔托莉雅·潘德拉贡$', 'rival', 50, '「余才不是什么Saber脸！」——红Saber与蓝Saber的宿命对决。'),
    # Zhuge Liang (Waver)
    ('诸葛孔明$', '伊斯坎达尔$', 'friend', 70, '作为伊斯坎达尔Master的记忆，即使变成了孔明的容器也不会忘记。'),
    # Oni
    ('酒吞童子$', '茨木童子$', 'friend', 75, '大江山的鬼。茨木对酒吞的忠诚与崇拜，是妖怪之间难得的真情。'),
    # Shinsengumi
    ('冲田总司$', '土方岁三$', 'friend', 72, '新选组的副长与一番队队长。即使病入膏肓，总司依然是土方最信任的剑。'),
    # Kintoki & Shuten
    ('坂田金时$', '酒吞童子$', 'rival', 40, '源氏的勇者与大江山的鬼。金时曾斩下酒吞的手臂，命运的对手。'),
    # Scathach & Cu
    ('斯卡哈$', '库丘林$', 'master_servant', 68, '影之国的女王与她最出色的弟子。库丘林的战斗技艺来自斯卡哈的严格教导。'),
    # BB & Alteregos
    ('BB$', 'Passionlip$', 'family', 55, 'BB创造的Alterego。既是母亲又是姐姐的复杂关系。'),
    ('BB$', 'Meltryllis$', 'family', 55, 'BB的造物。Meltryllis对BB既有恨意也有无法割断的联系。'),
    # Edmond Dantès
    ('岩窟王$', '阿尔贝$', 'complex', 50, '复仇者与被复仇的对象。基督山伯爵的悲剧在于，复仇完成后只剩下空虚。'),
    # Holmes & Moriarty
    ('福尔摩斯$', '莫里亚蒂$', 'rival', 45, '侦探与犯罪教授。光与影的宿命对决，彼此是对方存在的意义。'),
    # Ishtar & Ereshkigal
    ('伊什塔尔$', '吉尔伽美什$', 'complex', 35, '女神的求婚被英雄王毫不留情地拒绝。伊什塔尔至今耿耿于怀。'),
    ('艾蕾什基伽尔$', '伊什塔尔$', 'family', 40, '冥界女神与天之女主人。姐妹之间的关系复杂到连神话都说不清。'),
    # Tamamo
    ('玉藻前$', '天照$', 'complex', 50, '玉藻前声称自己是天照的分灵。是真是假，连她自己可能都不确定。'),
    # Arjuna & Karna
    ('阿周那$', '迦尔纳$', 'rival', 55, '《摩诃婆罗多》中的宿命对手。一个是天之骄子，一个是被遗弃的太阳之子。命运的对决永无止境。'),
    ('迦尔纳$', '阿周那$', 'rival', 55, '即使被全世界背叛，迦尔纳依然保持着自己的骄傲。对阿周那而言，他是永远的宿敌。'),
    # Mashu
    ('玛修·基列莱特$', '卫宫$', 'friend', 70, '前辈与后辈。玛修在士郎身上看到了「正义的伙伴」的理想。'),
    ('玛修·基列莱特$', '莉莉丝$', 'rival', 15, '情敌。莉莉丝对前辈的执念与玛修对前辈的守护，注定无法共存。两人的对立充满了嫉妒与不甘。'),
    ('莉莉丝$', '玛修·基列莱特$', 'rival', 15, '情敌。在迦勒底中，莉莉丝爱上了前辈，而玛修是前辈最亲近的人。这份三角关系是她们之间永远的刺。'),
]

# Bond type display names
_BOND_TYPE_NAMES = {
    'lover': '💕 恋人羁绊',
    'rival': '⚔️ 宿命之敌',
    'family': '👨‍👩‍👧‍👦 血缘/家族羁绊',
    'master_servant': '🎖️ 主从羁绊',
    'friend': '🤝 挚友羁绊',
    'complex': '🌀 复杂羁绊',
}

def _check_special_bond(n1, n2):
    """Check if two servants have a special lore-based bond."""
    for pa, pb, bt, bs, desc in _SPECIAL_BONDS:
        if re.search(pa, n1) and re.search(pb, n2):
            return {'bond_type': bt, 'base_score': bs, 'description': desc}
    return None

def _get_traits(profile):
    """Extract traits list from a personality profile."""
    raw = profile.get('traits', '')
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except:
            return []
    return []

def _analyze_traits(t1, t2, n1, n2):
    """Analyze shared traits between two servants. Returns (bonus, lines)."""
    bonus = 0
    lines = []
    s1, s2 = set(t1), set(t2)
    common = s1 & s2
    if common:
        bonus += len(common) * 3
        lines.append('✨ 共享特性：' + '、'.join(list(common)[:5]))
    if '阿尔托莉雅脸' in s1 and '阿尔托莉雅脸' in s2:
        bonus += 5
        lines.append('👑 同为「阿尔托莉雅脸」——你们站在一起会让Master眼花缭乱。')
    if '所爱之人' in s1 and '所爱之人' in s2:
        bonus += 8
        lines.append('💕 双方都具有「所爱之人」特性——在迦勒底的日常中，你们是被祝福的一对。')
    if '圆桌骑士' in s1 and '圆桌骑士' in s2:
        bonus += 6
        lines.append('⚔️ 同为圆桌骑士——骑士之间的羁绊，超越了时代的界限。')
    if 'FSN从者' in s1 and 'FSN从者' in s2:
        bonus += 7
        lines.append('🗡️ 同为FSN的从者——圣杯战争中结下的缘分，在迦勒底延续。')
    if '王' in s1 and '王' in s2:
        bonus += 4
        lines.append('👑 双王相会——王与王之间的理解，是常人无法企及的。')
    if '神性' in s1 and '神性' in s2:
        bonus += 3
        lines.append('⚡ 共享神性——神与神之间，有着超越凡人的共鸣。')
    if '夏日模式从者' in s1 and '夏日模式从者' in s2:
        bonus += 5
        lines.append('🏖️ 同为夏日从者——阳光、海滩、泳装，这就是最好的相性！')
    return bonus, lines

def _generate_random_event(decimal, bond_info, score):
    """Generate a random event based on the fate decimal."""
    if decimal < 0.05:
        return '🎲 命运的齿轮在此刻转动了——一个微小的变量，改变了整个故事的走向。'
    elif decimal < 0.15:
        if bond_info and bond_info.get('bond_type') == 'lover':
            return '💕 在迦勒底的走廊上，两人不期而遇。目光交汇的瞬间，时间仿佛静止了。'
        elif bond_info and bond_info.get('bond_type') == 'rival':
            return '⚔️ 剑拔弩张的气氛弥漫开来。即使是日常的擦肩而过，也充满了火药味。'
        else:
            return '🌙 月光下，两人在阳台上偶然相遇。一段意想不到的对话就此展开。'
    elif decimal < 0.30:
        return '🍵 在迦勒底的茶室里，两人共享了一杯茶。看似平常的时光，却意外地令人安心。'
    elif decimal < 0.50:
        return '📚 在图书馆的角落，两人因为同一本书而展开了讨论。观点的碰撞擦出了意想不到的火花。'
    elif decimal < 0.70:
        return '🎭 模拟战中的配合出乎意料地默契。Master在一旁露出了满意的微笑。'
    elif decimal < 0.85:
        return '🌸 在迦勒底的庭院里，花瓣飘落。两人并肩而坐，享受着难得的宁静时光。'
    elif decimal < 0.95:
        return '⚡ 一场突如其来的紧急任务让两人被迫并肩作战。危机中展现出的默契令人惊叹。'
    else:
        return '🌟 命运的红线在此刻闪耀——这是一个连圣杯都无法预测的奇迹时刻。'

@app.route('/api/compatibility', methods=['POST'])
def compatibility():
    """Analyze servant compatibility with lore-based bond analysis."""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    sid1 = data.get('servant_id_1')
    sid2 = data.get('servant_id_2')
    if not sid1 or not sid2:
        return jsonify({'error': 'servant_id_1 and servant_id_2 are required'}), 400

    pid1, pid2 = str(sid1), str(sid2)
    profile1 = personalities.get(pid1)
    profile2 = personalities.get(pid2)
    if not profile1:
        return jsonify({'error': f'Servant {sid1} not found'}), 404
    if not profile2:
        return jsonify({'error': f'Servant {sid2} not found'}), 404

    name1 = profile1.get('name_cn', '从者1')
    name2 = profile2.get('name_cn', '从者2')

    # ── 1. Check special lore bonds ──
    bond = _check_special_bond(name1, name2)

    # ── 2. Trait analysis ──
    traits1 = _get_traits(profile1)
    traits2 = _get_traits(profile2)
    trait_bonus, trait_lines = _analyze_traits(traits1, traits2, name1, name2)

    # ── 3. Calculate final score ──
    import random as _rnd

    # Load pre-generated compat data as fallback
    if 'compat_data' not in dir():
        compat_path = os.path.join(_APP, 'compat_data.json')
        if os.path.exists(compat_path):
            with open(compat_path, 'r', encoding='utf-8') as f:
                compat_data = json.load(f)
        else:
            compat_data = {}

    pair_key = f"{min(int(sid1),int(sid2))}_{max(int(sid1),int(sid2))}"
    pregen_score = compat_data.get(pair_key, 50.0)

    if bond:
        # Use lore-based base score + bonuses
        base = bond['base_score']
        total = base + trait_bonus + 2  # +2 base gender bonus
        random_offset = _rnd.uniform(-8, 8)
        total += random_offset
        score = max(0, min(100, round(total)))
    else:
        # Use pre-generated score with small variation
        score = round(pregen_score + _rnd.uniform(-3, 3), 1)
        score = max(0, min(100, score))

    # ── 5. Fate decimal (random event seed) ──
    fate_decimal = round(_rnd.uniform(0, 1), 4)

    # ── 6. Build analysis text ──
    analysis_parts = []
    interaction = ''

    if bond:
        bt = bond['bond_type']
        bname = _BOND_TYPE_NAMES.get(bt, '特殊羁绊')
        analysis_parts.append(f'【{bname}】')
        analysis_parts.append(bond['description'])
        analysis_parts.append('')

        # Bond-specific interactions
        BOND_INTERACTIONS = {
            'lover': [
                f'{name1}：「今天的夕阳很美呢。」\n{name2}：「嗯……有你在身边，什么都变美了。」\n（两人并肩坐在迦勒底的天台上，影子交叠在一起）',
                f'{name1}：「你又没好好吃饭吧？」\n{name2}：「被你发现了……」\n（{name1}无奈地把便当递了过去）',
            ],
            'friend': [
                f'{name1}：「好久没有这样聊天了。」\n{name2}：「是啊，但你我之间的羁绊，不会因为时间而褪色。」\n（两人相视而笑）',
                f'{name1}：「来，干杯！」\n{name2}：「为了乌鲁克——不，为了我们的友情！」\n（酒杯碰撞的声音在夜空中回荡）',
            ],
            'rival': [
                f'{name1}：「下次战斗，我不会输给你。」\n{name2}：「哼，那就走着瞧吧。」\n（两人的目光在空气中碰撞出火花）',
                f'{name1}：「……你变强了。」\n{name2}：「你也是。」\n（沉默中，两人都露出了只有对手才能理解的微笑）',
            ],
            'complex': [
                f'{name1}：「……」\n{name2}：「……」\n（两人对视良久，谁也没有先开口。有些话，不需要说出口。）',
                f'{name1}：「我们之间……算了。」\n{name2}：「嗯，我知道。」\n（复杂的情感在沉默中流淌）',
            ],
            'family': [
                f'{name1}：「你还好吗？」\n{name2}：「有你在，我很好。」\n（家人之间的默契，不需要太多言语）',
                f'{name1}：「今天一起吃饭吧？」\n{name2}：「好，我来做。」\n（温馨的家庭时光）',
            ],
            'master_servant': [
                f'{name1}：「Master的命令是绝对的——但你，是我自愿追随的。」\n{name2}：「……我会努力配得上你的信任。」',
                f'{name1}：「别松懈，下一战不会轻松。」\n{name2}：「遵命！」\n（主从之间的信任，是战场上最强的武器）',
            ],
        }
        opts = BOND_INTERACTIONS.get(bt, BOND_INTERACTIONS['friend'])
        interaction = opts[(int(sid1) + int(sid2)) % len(opts)]

    if trait_lines:
        analysis_parts.append('【特性共鸣】')
        analysis_parts.extend(trait_lines)
        analysis_parts.append('')

    # Add random event
    random_event = _generate_random_event(fate_decimal, bond, score)
    analysis_parts.append('【今日事件】')
    analysis_parts.append(random_event)
    analysis_parts.append('')
    analysis_parts.append(f'📊 命运之数: {fate_decimal}')

    analysis = '\n'.join(analysis_parts)

    # ── 7. Build generic interaction if no bond-specific one ──
    if not interaction:
        if score >= 85:
            interaction = f'{name1}：「今天一起训练吧？」\n{name2}：「正有此意。」\n（两人相视一笑，并肩走向训练场）'
        elif score >= 70:
            interaction = f'{name1}：「这次的任务，我们一组吧？」\n{name2}：「没问题，交给我。」\n（两人默契地点头）'
        elif score >= 55:
            interaction = f'{name1}：「今天的天气真不错。」\n{name2}：「是啊，适合散步。」\n（两人在庭院中悠闲地走着）'
        elif score >= 40:
            interaction = f'{name1}：「……」\n{name2}：「……」\n（两人沉默地坐着，气氛有些尴尬）'
        elif score >= 25:
            interaction = f'{name1}：「哼。」\n{name2}：「……」\n（两人擦肩而过，谁也没有停下脚步）'
        else:
            interaction = f'{name1}：「离我远点。」\n{name2}：「正合我意。」\n（两人背对背，各自走向不同的方向）'

    # ── 8. Grade info ──
    if score >= 95: grade, grade_desc, emoji = 'SSS', '超越羁绊的奇迹之缘', '💫✨🌟'
    elif score >= 90: grade, grade_desc, emoji = 'SS', '命运注定的灵魂伴侣', '🌟✨'
    elif score >= 85: grade, grade_desc, emoji = 'S', '完美的搭档', '⭐💫'
    elif score >= 70: grade, grade_desc, emoji = 'A', '极佳的相性', '✨'
    elif score >= 60: grade, grade_desc, emoji = 'B', '不错的默契', '💛'
    elif score >= 50: grade, grade_desc, emoji = 'C', '普通的关系', '🤝'
    elif score >= 40: grade, grade_desc, emoji = 'D', '需要磨合', '😐'
    elif score >= 30: grade, grade_desc, emoji = 'E', '相性堪忧', '😰'
    elif score >= 20: grade, grade_desc, emoji = 'F', '水火不容', '💥'
    else: grade, grade_desc, emoji = '???', '不可名状的孽缘', '💀🔥'

    result = {
        'score': score,
        'analysis': analysis,
        'fun_interaction': interaction,
        'grade': grade,
        'grade_desc': grade_desc,
        'emoji': emoji,
        'fate_decimal': fate_decimal,
        'random_event': random_event,
    }
    if bond:
        result['bond_type'] = bond['bond_type']
        result['bond_label'] = _BOND_TYPE_NAMES.get(bond['bond_type'], '')
        result['bond_desc'] = bond['description']

    return jsonify(result)


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
    is_typemoon = data.get('typemoon', False)

    if not servant_ids:
        return jsonify({'error': 'servant_ids is required'}), 400

    # 加载型月角色数据
    tm_chars = {}
    if is_typemoon:
        tm_path = os.path.join(_APP, 'typemoon_characters.json')
        if os.path.exists(tm_path):
            with open(tm_path, 'r', encoding='utf-8') as f:
                tm_data = json.load(f)
                for k, v in tm_data.items():
                    pid = -(int(k) + 1)
                    tm_chars[pid] = v

    # 加载FGO预设朋友圈
    fgo_moments = {}
    fgo_moments_path = os.path.join(_APP, 'fgo_moments.json')
    if os.path.exists(fgo_moments_path):
        with open(fgo_moments_path, 'r', encoding='utf-8') as f:
            fgo_moments = json.load(f)

    posts = []
    for sid in servant_ids:
        name_cn = ''
        name_jp = ''
        personality = ''
        speech = ''

        if is_typemoon and sid < 0:
            char = tm_chars.get(sid, {})
            if not char:
                continue
            name_cn = char.get('name_cn', '')
            name_jp = char.get('name_jp', '')
            personality = char.get('personality', '')
            speech = char.get('speech_style', '')

            # 型月角色用预设朋友圈（中文，称呼用「你」）
            tm_moments = {
                '卫宫士郎': ['今天帮人修好了自行车，虽然有点烫伤……正义的伙伴就要随时帮助别人！', '切嗣，我一定会成为正义的伙伴。', '做了一桌菜，结果远坂和Saber都来了……家里好热闹。'],
                '阿尔托莉雅': ['今日的战斗，敌手尚可。骑士王绝不退缩。', '这个……饭团很好吃。', '一起用餐吧。'],
                '远坂凛': ['才不是在整理宝石呢……只是顺便而已。', '魔术协会的那些人真是烦死了。', 'Archer，不要擅自行动！'],
                'EMIYA': ['I am the bone of my sword.', '今天做了咖喱。士郎那家伙还不错。', '正义的伙伴？别开玩笑了。'],
                '间桐樱': ['前辈，今天辛苦了。', '做了便当，希望前辈喜欢。', '春天到了……花好漂亮。'],
                '美杜莎': ['……樱平安无事就好。', '读了一本书。安静的午后很好。'],
                '伊莉雅丝菲尔': ['喂喂，哥哥！今天也一起玩吧！', 'Berserker好强啊～', '魔法少女伊莉雅，参上！'],
                '吉尔伽美什': ['哼哈哈哈哈哈，这世上的宝物全是本王的！', '杂种们，感谢本王的伟大吧。', '来喝酒吗？'],
                '言峰绮礼': ['幸福到底是什么呢。', '今日的教会很安静。', '麻婆豆腐，最高。'],
                '卫宫切嗣': ['……嗯。', '在擦枪。', '爱丽、伊莉雅，我一定会守护你们。'],
                '爱丽丝菲尔': ['和切嗣一起散步，好开心。', '伊莉雅，一起去玩吧。', '花好漂亮。'],
                '伊斯坎达尔': ['哈哈哈哈哈，看看我的军队！', '征服之旅还在继续。', '韦伯，吃饭了！'],
                '韦伯·维尔维特': ['王，稍微等一下……！', '论文终于写完了。', '哈……好累。'],
                '两仪式': ['没有兴致。', '黑桐，还没来吗？', '今天的天空，有点漂亮。'],
                '黑桐干也': ['式，你没事吧？', '今天也是和平的一天。', '去了眼镜店。'],
                '苍崎橙子': ['人类，是很坚强的。', '换了一副眼镜。', '工房里正在制作中。'],
                '浅上藤乃': ['好痛……好痛……', '今天也是普通的一天。'],
                '黑桐鲜花': ['哥哥！今天也要加油！', '式的事情……我才不承认呢。', '花好漂亮。'],
                '远野志贵': ['那是什么……', '秋叶，没事吧？', '今天也是普通的一天。'],
                '爱尔奎特': ['喂喂，志贵！一起去玩吧！', '我可是真祖的公主哦。', '今天的天气真好。'],
                '希耶尔': ['志贵，你没事吧？', '在教会的一天。', '喝了茶。'],
                '远野秋叶': ['兄长大人，欢迎回来。', '远野家今天也很和平。', '红茶很好喝。'],
                '翡翠': ['老爷，您叫我吗？', '今天也陪在您身边。'],
                '琥珀': ['老爷，辛苦了。', '呵呵，没问题哦。', '料理做得很成功。'],
                '苍崎青子': ['我可是魔法使。', '静希，你在干嘛。', '今天也是暴力系的一天。'],
                '久远寺有珠': ['……没兴趣。', '童话会诉说真相。', '喝茶了吗？'],
                '静希草十郎': ['不好意思。', '都市的生活，慢慢习惯了。', '青子是个温柔的人。'],
                '贞德': ['神的声音，我听到了。', '法兰西……我会守护到底。', '今天也献上祈祷。'],
                '莫德雷德': ['我可是父上的敌人！', 'Clarent！', '父上……！'],
                '塞米拉米斯': ['妾身可是空中庭园的女王。', '要尝尝毒药吗？'],
                '阿斯托尔福': ['看起来很有趣！', '我今天也精神满满！'],
                '天草四郎': ['想要……拯救人类。', '今天也献上祈祷。'],
                '佐佐木小次郎': ['来吧。', '秘剑·燕返。', '风很舒服。'],
                '美狄亚': ['御主，辛苦了。', '背叛者，要接受惩罚。'],
                '库丘林': ['哎呀哎呀，痛快的战斗！', '来试试我的枪吧。'],
                '赫拉克勒斯': ['啊啊啊啊啊……！', '咕噜噜噜……'],
                '葛木宗一郎': ['嗯。', '回去了。'],
                '藤村大河': ['早上好！士郎！', '肉啊——！想吃肉！', '今天天气也很好！'],
                '柳洞一成': ['那是个问题。', '今天也在学生会工作。'],
                '吉尔·德·雷': ['贞德……！', '神啊，为何……！'],
                '久宇舞弥': ['了解。', '任务完成。'],
                '凯涅斯': ['你以为我是谁。', '魔术研究在推进中。'],
                '迪尔姆德': ['御主，让我来侍奉您。', '以骑士的名誉起誓。'],
                '远坂时臣': ['作为魔术师，不能丢脸。', '凛，让作为父亲的我说几句。'],
                '间桐雁夜': ['时臣……！', '必须……救樱……'],
                '雨生龙之介': ['好漂亮啊……！', '人的死亡，是最棒的艺术哦。'],
                '荒耶宗莲': ['人类是什么。', '到达根源。'],
                '白纯里绪': ['式……我喜欢式。'],
                '织': ['我只是有杀人冲动而已。', '式……是我的另一张面孔。'],
                '尼禄·卡奥斯': ['人类，说到底就是那种程度的东西。'],
                '弓冢五月': ['远野同学，一起回去吧。'],
                '米海尔·罗亚·巴尔丹姆乔恩': ['我将永远轮回。'],
            }
            moments_list = tm_moments.get(name_cn, [f'{name_cn}发了一条朋友圈'])
            content = random.choice(moments_list)
            posts.append({
                'servant_id': sid,
                'servant_name_cn': name_cn,
                'servant_name_jp': name_jp,
                'content': content,
                'likes': random.randint(1, 999),
                'timestamp': random.randint(1609459200, 1735689600)
            })
            continue
        else:
            pid = str(sid)
            profile = personalities.get(pid)
            if not profile:
                continue
            name_cn = profile['name_cn']
            name_jp = profile['name_jp']

            # FGO从者用预设朋友圈
            moments_list = fgo_moments.get(name_cn, [f'{name_cn}发了一条朋友圈'])
            content = random.choice(moments_list)
            posts.append({
                'servant_id': sid,
                'servant_name_cn': name_cn,
                'servant_name_jp': name_jp,
                'content': content,
                'likes': random.randint(1, 999),
                'timestamp': random.randint(1609459200, 1735689600)
            })
            continue

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

# ─── Share Conversation ──────────────────────────────────────────────────────
import string as _string
SHARE_FILE = os.path.join(_APP, 'shared_chats.json')

def _load_shared():
    if os.path.exists(SHARE_FILE):
        with open(SHARE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def _save_shared(data):
    with open(SHARE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _gen_code(length=6):
    chars = _string.ascii_uppercase + _string.digits
    import random as _rnd
    return ''.join(_rnd.choice(chars) for _ in range(length))

@app.route('/api/share', methods=['POST'])
def share_chat():
    """Save a conversation and return a share code."""
    data = request.json
    if not data or 'history' not in data:
        return jsonify({'error': 'No data'}), 400
    shared = _load_shared()
    # Generate unique code
    while True:
        code = _gen_code()
        if code not in shared:
            break
    shared[code] = {
        'history': data.get('history', []),
        'servant_ids': data.get('servant_ids', []),
        'servant_names': data.get('servant_names', ''),
        'master_name': data.get('master_name', ''),
        'language': data.get('language', 'cn'),
        'is_group': data.get('is_group', False),
        'created_at': int(__import__('time').time() * 1000)
    }
    _save_shared(shared)
    return jsonify({'ok': True, 'code': code})

@app.route('/api/share/<code>', methods=['GET'])
def get_shared(code):
    """Retrieve a shared conversation by code."""
    shared = _load_shared()
    # Auto-cleanup: remove entries older than 7 days
    import time as _t
    now = int(_t.time() * 1000)
    week_ms = 7 * 24 * 60 * 60 * 1000
    expired = [k for k, v in shared.items() if now - v.get('created_at', 0) > week_ms]
    for k in expired:
        del shared[k]
    if expired:
        _save_shared(shared)
    chat = shared.get(code.upper())
    if not chat:
        return jsonify({'error': '编码无效或已过期'}), 404
    return jsonify({'ok': True, 'chat': chat})

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
