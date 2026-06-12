# FIFA 2026 Virtual Betting Simulator

一个面向反赌教育的世界杯虚拟投注模拟网站。项目模拟常见体育投注页面的核心流程，但不接入真实支付、不提供真实博彩服务，用虚拟资金记录用户在世界杯比赛中的下注、输赢和资金变化，帮助直观看到赌博风险。

## 项目定位

本项目仅用于学习、展示和反赌教育：

- 不提供真实充值、提现或博彩服务
- 所有资金均为虚拟资金
- 赔率和赛果来自公开页面抓取，仅作为模拟案例
- 结算只按足球常规时间和伤停补时结果处理，不计加时和点球

## 功能亮点

- 2026 世界杯赛程展示，时间按北京时间显示
- 用户注册与登录，注册后默认现实资金 10000
- 现实资金和网站赌资分离展示
- 支持虚拟转入、转出、下注和交易流水记录
- 胜平负 1X2 玩法，单场最多下注 5000
- 比赛开始前 48 小时内开放下注，开赛后关闭下注
- 从 BetExplorer 抓取 bet365.us、BetMGM.us、Stake.com 三家 1X2 赔率并计算平均赔率
- 从 BetExplorer 抓取真实比分，抓不到时不会随机生成比分
- 自动根据真实比分结算已下注比赛
- 首页展示当前登录用户自己的模拟输赢情况，未登录时不显示个人实况

## 技术栈

- Python 3
- Flask
- Flask-Login
- Flask-SQLAlchemy
- SQLite
- Requests
- lxml
- Bootstrap 5

## 本地运行

1. 克隆项目并进入目录

```bash
git clone <your-repo-url>
cd FIFA
```

2. 创建并激活虚拟环境

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 初始化数据库

```bash
python init_data.py
```

5. 启动网站

```bash
python app.py
```

打开：

```text
http://127.0.0.1:5001
```

## 环境变量

可以参考 `.env.example`：

```env
SECRET_KEY=change-me-before-deploy
DATABASE_URL=sqlite:///betting.db
```

本地开发不配置也能运行。部署到公网时应设置自己的 `SECRET_KEY`，数据库建议换成 PostgreSQL。

## 数据说明

- `work_worldcup.html` 是初始化赛程用的公开页面快照。
- `instance/betting.db` 是本地运行生成的数据库，包含用户、资金、下注和交易记录，不应提交到 GitHub。
- 临时抓取文件、IDE 配置和缓存已通过 `.gitignore` 排除。

## 重要说明

这个项目的目标不是鼓励投注，而是通过可视化的虚拟下注记录展示赌博风险。请勿将本项目改造成真实博彩、支付或现金结算系统。

## 后续可改进

- 将 SQLite 切换为 PostgreSQL
- 增加后台定时任务，定时更新赔率和比分
- 增加管理员后台，查看抓取失败和结算日志
- 增加测试用例和部署脚本
- 优化移动端交互和页面文案
