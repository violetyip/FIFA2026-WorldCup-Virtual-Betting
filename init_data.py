"""
初始化 2026 世界杯赛程和真实赔率快照。

赛程来源：项目目录中的 work_worldcup.html 公开赛程快照。
时间存储：北京时间（UTC+8）。
赔率原则：只录入有公开来源的赔率；缺失项保持为空，不用模拟数据冒充。
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

import lxml.html

from app import app
from models import db, Match, Odds


TEAM_ZH = {
    "Mexico": "墨西哥",
    "South Africa": "南非",
    "South Korea": "韩国",
    "Czech Republic": "捷克",
    "Canada": "加拿大",
    "Bosnia and Herzegovina": "波黑",
    "Qatar": "卡塔尔",
    "Switzerland": "瑞士",
    "Brazil": "巴西",
    "Morocco": "摩洛哥",
    "Haiti": "海地",
    "Scotland": "苏格兰",
    "United States": "美国",
    "Paraguay": "巴拉圭",
    "Australia": "澳大利亚",
    "Turkey": "土耳其",
    "Germany": "德国",
    "Curaçao": "库拉索",
    "Ivory Coast": "科特迪瓦",
    "Ecuador": "厄瓜多尔",
    "Netherlands": "荷兰",
    "Japan": "日本",
    "Sweden": "瑞典",
    "Tunisia": "突尼斯",
    "Belgium": "比利时",
    "Egypt": "埃及",
    "Iran": "伊朗",
    "New Zealand": "新西兰",
    "Spain": "西班牙",
    "Cape Verde": "佛得角",
    "Saudi Arabia": "沙特阿拉伯",
    "Uruguay": "乌拉圭",
    "France": "法国",
    "Senegal": "塞内加尔",
    "Iraq": "伊拉克",
    "Norway": "挪威",
    "Argentina": "阿根廷",
    "Algeria": "阿尔及利亚",
    "Austria": "奥地利",
    "Jordan": "约旦",
    "Portugal": "葡萄牙",
    "DR Congo": "民主刚果",
    "Uzbekistan": "乌兹别克斯坦",
    "Colombia": "哥伦比亚",
    "England": "英格兰",
    "Croatia": "克罗地亚",
    "Ghana": "加纳",
    "Panama": "巴拿马",
}

GROUPS = {
    "A": ["墨西哥", "南非", "韩国", "捷克"],
    "B": ["加拿大", "波黑", "卡塔尔", "瑞士"],
    "C": ["巴西", "摩洛哥", "海地", "苏格兰"],
    "D": ["美国", "巴拉圭", "澳大利亚", "土耳其"],
    "E": ["德国", "库拉索", "科特迪瓦", "厄瓜多尔"],
    "F": ["荷兰", "日本", "瑞典", "突尼斯"],
    "G": ["比利时", "埃及", "伊朗", "新西兰"],
    "H": ["西班牙", "佛得角", "沙特阿拉伯", "乌拉圭"],
    "I": ["法国", "塞内加尔", "伊拉克", "挪威"],
    "J": ["阿根廷", "阿尔及利亚", "奥地利", "约旦"],
    "K": ["葡萄牙", "民主刚果", "乌兹别克斯坦", "哥伦比亚"],
    "L": ["英格兰", "克罗地亚", "加纳", "巴拿马"],
}

GROUP_BY_TEAM = {team: group for group, teams in GROUPS.items() for team in teams}

REAL_ODDS = {
    # 公开页可核到的赔率片段。没有完整三家 1X2 时，缺失值保持 None。
    (1, "win_draw_lose", "home_win"): {
        "source_one": 1.38,
        "source_one_name": "FanDuel",
        "note": "FanDuel moneyline Mexico -260，换算十进制约 1.38；NY Post 2026-06-11 赛前报道。",
        "url": "https://nypost.com/2026/06/11/betting/mexico-vs-south-africa-prediction-odds-picks-best-bet-for-world-cup-opener/",
    },
    (1, "win_draw_lose", "away_win"): {
        "source_one": 9.00,
        "source_one_name": "FanDuel",
        "note": "FanDuel moneyline South Africa +800，换算十进制 9.00；NY Post 2026-06-11 赛前报道。",
        "url": "https://nypost.com/2026/06/11/betting/mexico-vs-south-africa-prediction-odds-picks-best-bet-for-world-cup-opener/",
    },
}


def parse_bjt(raw_text):
    cleaned = raw_text.replace("\xa0", " ")
    match = re.search(
        r"([A-Z][a-z]+)\s+(\d{1,2}),\s+2026.*?(\d{1,2}):(\d{2})\s+([ap])\.m\.\s+UTC([−-])(\d+)",
        cleaned,
    )
    if not match:
        raise ValueError(f"无法解析比赛时间: {cleaned[:120]}")

    month, day, hour, minute, ap, sign, offset = match.groups()
    hour = int(hour) % 12
    if ap == "p":
        hour += 12
    local_time = datetime.strptime(f"{month} {day} 2026 {hour}:{minute}", "%B %d %Y %H:%M")
    offset_hours = int(offset)
    utc_time = local_time + timedelta(hours=offset_hours if sign in ("−", "-") else -offset_hours)
    return utc_time + timedelta(hours=8)


def parse_venue(raw_text):
    cleaned = raw_text.replace("\xa0", " ")
    match = re.search(r"\[Report \d+\]\s*(.*?)\s*(?:Referee:|$)", cleaned, re.S)
    if not match:
        return ""
    return " ".join(match.group(1).split())


def zh_team(name):
    name = name.strip()
    return TEAM_ZH.get(name, name.replace("Winner", "小组第1").replace("Runner-up", "小组第2"))


def stage_for(match_no, team1, team2):
    if match_no <= 72:
        return GROUP_BY_TEAM.get(team1) or GROUP_BY_TEAM.get(team2) or "小组赛"
    if match_no <= 88:
        return "32强"
    if match_no <= 96:
        return "16强"
    if match_no <= 100:
        return "8强"
    if match_no <= 102:
        return "半决赛"
    if match_no == 103:
        return "三四名"
    return "决赛"


def extract_schedule():
    html_path = Path(__file__).with_name("work_worldcup.html")
    if not html_path.exists():
        raise FileNotFoundError("缺少 work_worldcup.html，无法初始化真实赛程快照。")

    doc = lxml.html.parse(str(html_path))
    rows = []
    for box in doc.xpath('//div[contains(@class,"footballbox")]'):
        text = box.text_content()
        tables = box.xpath('.//table[contains(@class,"fevent")]')
        if not tables:
            continue
        cells = [c.text_content().strip().replace("\xa0", " ") for c in tables[0].xpath(".//th")]
        if len(cells) < 3 or not cells[1].startswith("Match "):
            continue
        match_no = int(cells[1].split()[1])
        team1 = zh_team(cells[0])
        team2 = zh_team(cells[2])
        rows.append(
            {
                "match_no": match_no,
                "team1": team1,
                "team2": team2,
                "match_time": parse_bjt(text),
                "venue": parse_venue(text),
                "group_name": stage_for(match_no, team1, team2),
            }
        )
    return sorted(rows, key=lambda row: row["match_no"])


def create_odds(match):
    selections = [
        ("win_draw_lose", "home_win"),
        ("win_draw_lose", "draw"),
        ("win_draw_lose", "away_win"),
    ]
    for odds_type, selection in selections:
        data = REAL_ODDS.get((match.match_no, odds_type, selection), {})
        values = [data.get("source_one"), data.get("source_two"), data.get("source_three")]
        available = [v for v in values if v is not None]
        avg = round(sum(available) / len(available), 2) if available else None
        db.session.add(
            Odds(
                match_id=match.id,
                odds_type=odds_type,
                selection=selection,
                bet365_initial=data.get("source_one"),
                bet365_current=data.get("source_one"),
                willhill_initial=data.get("source_two"),
                willhill_current=data.get("source_two"),
                pinnacle_initial=data.get("source_three"),
                pinnacle_current=data.get("source_three"),
                source_one_name=data.get("source_one_name"),
                source_two_name=data.get("source_two_name"),
                source_three_name=data.get("source_three_name"),
                avg_initial=avg,
                avg_current=avg,
                source_note=data.get("note", "暂未录入可核验的公开赔率来源。"),
                source_url=data.get("url"),
                verified_at=datetime(2026, 6, 11, 21, 0) if data else None,
            )
        )


def init_database():
    db.drop_all()
    db.create_all()

    group_counts = {}
    for row in extract_schedule():
        group_counts[row["group_name"]] = group_counts.get(row["group_name"], 0) + 1
        match = Match(
            match_no=row["match_no"],
            group_name=row["group_name"],
            match_day=(group_counts[row["group_name"]] + 1) // 2 if row["match_no"] <= 72 else 0,
            team1=row["team1"],
            team2=row["team2"],
            match_time=row["match_time"],
            venue=row["venue"],
            status="upcoming",
        )
        db.session.add(match)
        db.session.flush()
        create_odds(match)

    db.session.commit()
    print(f"成功初始化 {Match.query.count()} 场比赛，时间均为北京时间。")
    first = Match.query.order_by(Match.match_time).first()
    print(f"首场：#{first.match_no} {first.team1} vs {first.team2} {first.match_time:%Y-%m-%d %H:%M} 北京时间")
    print(f"赔率：已录入可核验公开来源 {sum(1 for o in Odds.query.all() if o.avg_current is not None)} 项，其余保持缺失。")


if __name__ == "__main__":
    with app.app_context():
        init_database()
