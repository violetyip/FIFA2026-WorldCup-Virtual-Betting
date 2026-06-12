# Project Summary

## 项目名称

FIFA 2026 World Cup Virtual Betting

## 一句话介绍

基于 Flask 的世界杯虚拟体育投注模拟平台，通过真实赛程、公开赔率、虚拟资金和自动结算记录，展示赌博行为可能带来的资金波动和风险。

## 可以写进简历的描述

- 使用 Flask、SQLAlchemy 和 Bootstrap 构建世界杯虚拟投注平台，支持注册登录、虚拟钱包、资金转入转出、下注记录和交易流水。
- 基于公开赛程快照初始化 2026 世界杯 104 场比赛，并统一转换为北京时间展示。
- 设计胜平负 1X2 赔率模型，从 BetExplorer 抓取 bet365.us、BetMGM.us、Stake.com 三家公开赔率，计算平均赔率作为模拟结算依据。
- 实现真实比分抓取和自动结算逻辑，避免使用随机比分；抓不到真实比分时不结算，保证模拟数据可核验。
- 为反赌教育场景设计用户资金面板和输赢统计，未登录时隐藏个人数据，登录后只展示当前账号的模拟结果。

## 技术关键词

Flask, SQLAlchemy, Flask-Login, SQLite, Requests, lxml, Bootstrap, Web Scraping, Data Modeling, Anti-Gambling Education

## 项目亮点

- 真实赛程和公开赔率结合，比纯随机模拟更适合案例展示。
- 资金行为有完整流水，能追踪充值、提现、下注、中奖和亏损。
- 明确区分现实资金和网站赌资，贴合反赌教育的表达目标。
- 赔率和比分抓取失败时不伪造数据，降低错误结算风险。
