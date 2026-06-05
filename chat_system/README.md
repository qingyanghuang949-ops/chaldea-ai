# CHALDEA - FGO 从者AI对话系统

基于 Xiaomi MiMo AI 的 Fate/Grand Order 从者角色扮演对话系统。

## 功能

- 458位从者角色可选
- 从剧情脚本中提取的性格档案
- 基于AI的角色扮演对话
- 迦勒底风格的精美UI

## 快速开始

### 1. 安装依赖

```bash
pip install flask requests
```

### 2. 提取性格档案（已完成）

```bash
python extract_personalities.py
```

### 3. 配置API

编辑 `config.json`，填入你的 API Key：

```json
{
  "api_base": "https://api.xiaomimimo.com/v1",
  "api_key": "你的API密钥",
  "model": "MiMo-v2.5"
}
```

也可以在网页界面的设置中配置。

### 4. 启动

```bash
python app.py
```

或双击 `start.bat`。

然后打开浏览器访问 http://localhost:5000

## 文件结构

```
chat_system/
├── app.py                  # Flask 后端
├── index.html              # 前端页面
├── extract_personalities.py # 性格提取脚本
├── personalities.json       # 提取的性格数据（458个从者）
├── config.json              # API 配置
├── start.bat                # Windows 启动脚本
└── README.md                # 本文件
```

## 技术栈

- **后端**: Python + Flask
- **前端**: 原生 HTML/CSS/JS（无框架依赖）
- **数据库**: SQLite（fgo_wiki.db）
- **AI**: Xiaomi MiMo API（OpenAI兼容格式）

## 数据来源

- 从者数据: `fgo_wiki.db`（458个从者）
- 剧情脚本: 16771条脚本（JP + CN）
- 角色立绘/图标: `基本资料/立绘/` & `基本资料/图标/`
