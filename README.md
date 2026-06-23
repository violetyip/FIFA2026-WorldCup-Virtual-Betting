# FIFA 2026 World Cup Virtual Betting Simulator

这是一个以 **反赌教育** 为出发点的世界杯虚拟投注模拟网站。

它并不提供真实充值、提现或博彩服务，而是把常见体育投注平台里的几个关键动作做成一个可观察的模拟过程：用户拿到一笔虚拟资金，选择比赛，查看公开赔率，下注，然后等待真实比分结算。最后，系统会把每一次转入、下注、输赢和余额变化都记录下来，让“赌博带来的资金波动”变得直观可见。

简单说，这不是一个教人怎么赌的网站，而是一个让人看清楚赌博风险的演示项目。

## 项目想法

很多反赌提醒都停留在口号层面，比如“十赌九输”“远离赌博”。这些话当然是对的，但如果只是文字，冲击力往往不够。

所以这个项目尝试换一种方式表达：

把一个看起来很像真实体育投注网站的流程搭出来，但所有钱都是虚拟的，所有结果都可回看，所有盈亏都清清楚楚写进流水里。用户可以在一个安全的环境里看到，下注并不是一个简单的“猜中就赢”的游戏，它会不断影响资金、心理预期和风险判断。

## 主要功能

- 展示 2026 世界杯赛程，比赛时间统一转换为北京时间
- 支持用户注册和登录，每个新用户默认获得 10,000 元虚拟现实资金
- 区分“现实资金”和“网站赌资”，模拟资金被转入投注平台后的变化
- 支持虚拟转入、提回、下注、中奖、亏损等完整交易流水
- 支持胜平负 1X2 玩法，单场投注上限为 5,000 元
- 比赛开始前 48 小时内开放下注，开赛后自动关闭投注入口
- 从 BetExplorer 抓取公开 1X2 赔率，并按可获取来源计算平均赔率
- 从 BetExplorer 抓取真实比分；如果抓不到比分，不会用随机结果冒充
- 根据真实比分自动结算用户投注
- 首页只展示当前登录用户自己的模拟输赢情况，未登录时不暴露个人数据

## 技术栈

- Python 3
- Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite
- Requests
- lxml
- Bootstrap 5

## 项目结构

```text
FIFA/
├── app.py                 # Flask 入口，包含路由、下注、钱包和结算逻辑
├── models.py              # SQLAlchemy 数据模型
├── init_data.py           # 初始化 2026 世界杯赛程和基础赔率数据
├── odds_updater.py        # 抓取公开赔率和比分
├── wsgi.py                # 服务器部署入口
├── templates/             # 页面模板
├── static/                # 样式和前端脚本
├── instance/betting.db    # 本地运行生成的 SQLite 数据库，不建议提交
├── requirements.txt       # Python 依赖
├── requirements-server.txt# 服务器额外依赖（包含 gunicorn）
└── README.md
```

## 本地运行

克隆项目后进入目录：

```bash
git clone https://github.com/violetyip/FIFA-2026-.git
cd FIFA-2026-
```

创建并激活虚拟环境：

```bash
python -m venv .venv
.venv\Scripts\activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

初始化数据库：

```bash
python init_data.py
```

启动网站：

```bash
python app.py
```

然后在浏览器中打开：

```text
http://127.0.0.1:5001
```

## 环境变量

项目提供了 `.env.example` 作为参考：

```env
SECRET_KEY=change-me-before-deploy
DATABASE_URL=sqlite:///betting.db
```

本地开发时不配置环境变量也可以运行。

如果部署到公网，建议至少设置自己的 `SECRET_KEY`，并把 SQLite 换成 PostgreSQL 或其他更适合生产环境的数据库。

## ECS 最简部署

如果只是部署到阿里云 ECS 给朋友使用，最简单可以这样做：

```bash
git clone https://github.com/violetyip/FIFA-2026-.git
cd FIFA-2026-
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-server.txt
python init_data.py
export SECRET_KEY=change-me
export FLASK_DEBUG=0
export PORT=5001
gunicorn -w 2 -b 0.0.0.0:5001 wsgi:app
```

服务器上还需要放行安全组端口。如果你前面用 Nginx 反向代理，就开放 `80/443`；如果只是临时给朋友访问，也可以先直接开放 `5001`。

为了避免每个请求都触发赔率和比分抓取，项目现在支持通过环境变量控制自动刷新：

```env
AUTO_REFRESH_ENABLED=1
ODDS_REFRESH_INTERVAL_SECONDS=900
SCORES_REFRESH_INTERVAL_SECONDS=300
```

## 数据来源说明

- `work_worldcup.html` 是用于初始化赛程的公开页面快照。
- 赔率和比分来自公开网页抓取，只用于学习和模拟展示。
- `instance/betting.db` 是本地运行产生的数据库，包含用户、投注和交易流水，不应提交到 GitHub。
- 抓取失败时，项目不会伪造赔率或比分；缺失数据会保持缺失状态。

## 项目边界

这个项目只用于学习、课程展示和反赌教育。

它不会，也不应该被改造成：

- 真实博彩网站
- 真实充值或提现系统
- 现金结算平台
- 鼓励用户投注的产品

项目里的所有资金都是虚拟资金，所有下注行为都只是模拟记录。

## 后续可以继续完善的方向

- 增加管理员后台，查看赔率抓取、比分抓取和结算日志
- 增加定时任务，让赔率和比分更新不依赖用户访问页面
- 增加测试用例，覆盖下注、结算和资金流水等关键逻辑
- 优化移动端页面体验
- 增加更直观的资金曲线，让亏损变化更容易被看见

## 一句话总结

这个项目想做的事情很简单：

用一个可运行、可交互、可回看的虚拟投注平台，提醒人们真实赌博并不是游戏，而是一种会持续放大风险的行为。
