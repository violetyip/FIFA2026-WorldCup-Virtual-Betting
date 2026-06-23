# FIFA 2026 World Cup Virtual Betting Simulator

这是一个以**反赌教育**为出发点的世界杯虚拟投注模拟网站。

它不提供真钱充值、提现或博彩服务，而是把常见体育投注平台里的几个关键动作做成一个可观察的模拟流程：用户拿到一笔虚拟资金，选择比赛，查看公开赔率，下单，然后等待真实比分结算。系统会把每一次转入、下注、输赢和余额变化都记录下来，让“赌博带来的资金波动”变得更直观可见。

一句话概括：这不是一个教人怎么赌的网站，而是一个帮助人看清赌博风险的演示项目。

## 项目特点

- 展示 2026 世界杯赛程，比赛时间统一转换为北京时间
- 支持用户注册、登录、虚拟钱包、下注记录和交易流水
- 明确区分“现实资金”和“网站赌资”，贴合反赌教育表达
- 只保留 1X2 胜平负玩法，单场下注总额上限为 5000
- 从公开网页抓取可核验的 1X2 赔率与真实比分
- 根据真实比分自动结算，抓取失败时不会伪造结果
- 首页只展示当前登录用户自己的模拟统计

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
├── app.py                    # Flask 入口，负责页面、下注、钱包和结算逻辑
├── models.py                 # SQLAlchemy 数据模型
├── init_data.py              # 初始化 2026 世界杯赛程与基础赔率
├── odds_updater.py           # 抓取公开赔率和真实比分
├── refresh_data.py           # 手动或定时刷新赔率、比分和结算
├── wsgi.py                   # Gunicorn / WSGI 启动入口
├── templates/                # Jinja2 模板
├── static/                   # 样式和前端脚本
├── instance/betting.db       # 本地运行生成的 SQLite 数据库
├── requirements.txt          # 本地开发依赖
├── requirements-server.txt   # 服务器部署依赖
└── README.md
```

## 本地运行

先克隆项目并进入目录：

```bash
git clone <your-repo-url>
cd FIFA
```

准备 Python 环境，任选一种方式：

```bash
conda activate <your-env>
```

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

浏览器打开：

```text
http://127.0.0.1:5001
```

## 数据刷新方式

推荐把“网页访问”和“外部数据刷新”彻底分开：

- 网页请求只读数据库，不在用户打开页面时顺手抓赔率或比分
- 赔率、比分、结算通过独立脚本 `refresh_data.py` 处理
- 本地使用时手动运行脚本
- 云端部署时用 `cron` 定时运行同一个脚本

默认全量刷新：

```bash
python refresh_data.py
```

可选参数：

```bash
python refresh_data.py --odds
python refresh_data.py --scores
python refresh_data.py --settle
python refresh_data.py --all
```

说明：

- `--odds`：刷新公开 1X2 赔率
- `--scores`：刷新比赛真实比分
- `--settle`：结算所有已完场但仍有待结算投注的比赛
- `--all`：显式执行“赔率 + 比分 + 结算”，效果等同于不带参数运行

## 环境变量

项目提供 `.env.example` 作为参考：

```env
SECRET_KEY=change-me-before-deploy
DATABASE_URL=sqlite:///betting.db
FLASK_DEBUG=0
PORT=5001
```

本地开发时可以直接使用默认值。部署到公网时，至少应设置自己的 `SECRET_KEY`，并根据需要把 `SQLite` 换成更适合生产环境的数据库。

## 云端部署

如果只是部署到一台 Linux 服务器，可以按下面的通用流程：

```bash
git clone <your-repo-url>
cd FIFA
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-server.txt
python init_data.py
export SECRET_KEY=change-me
export FLASK_DEBUG=0
export PORT=5001
gunicorn -w 2 -b 0.0.0.0:5001 wsgi:app
```

如果前面有 Nginx 反向代理，就开放 `80/443`；如果只是临时给朋友访问，也可以先开放应用端口。

## 定时刷新示例

Linux `cron` 示例，每 10 分钟刷新一次：

```cron
*/10 * * * * cd /path/to/FIFA && /path/to/python refresh_data.py --all >> /var/log/fifa-refresh.log 2>&1
```

如果你希望比分抓取更频繁，也可以拆成两条任务，例如一条专门跑 `--scores`，另一条低频跑 `--odds`。

## 数据来源说明

- `work_worldcup.html` 用于初始化赛程快照
- 赔率和比分来自公开网页抓取，只用于学习和模拟展示
- `instance/betting.db` 是本地运行产生的数据文件，不应提交到 GitHub
- 抓取失败时项目不会伪造赔率或比分，缺失数据会继续保持缺失状态

## 项目边界

这个项目只用于学习、课程展示和反赌教育，不会也不应该被改造成：

- 真实博彩网站
- 真实充值或提现系统
- 现金结算平台
- 鼓励用户投注的产品

项目里的所有资金都是虚拟资金，所有下注行为都只是模拟记录。

## 后续可继续完善的方向

- 增加管理后台，查看赔率抓取、比分抓取和结算日志
- 增加自动化测试，覆盖下注、结算和资金流水等关键逻辑
- 优化移动端页面体验
- 增加更直观的资金变化图表

## 总结

这个项目想做的事情很简单：

用一个可运行、可交互、可回看数据变化的虚拟投注平台，提醒人们真实赌博并不是游戏，而是一种会持续放大风险的行为。
