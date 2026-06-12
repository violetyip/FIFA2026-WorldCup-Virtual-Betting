import re
import time
import warnings
from datetime import datetime, timedelta

import lxml.html
import requests
from requests import RequestsDependencyWarning

from models import Match, Odds, db

warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
warnings.filterwarnings("ignore", message=".*urllib3.*", category=Warning)

BETEXPLORER_BASE = "https://www.betexplorer.com"
BETEXPLORER_WORLD_CUP_URL = f"{BETEXPLORER_BASE}/football/world/world-championship-2026/"
BETEXPLORER_EVENT_LIST_URLS = (
    BETEXPLORER_WORLD_CUP_URL,
    f"{BETEXPLORER_WORLD_CUP_URL}fixtures/",
    f"{BETEXPLORER_WORLD_CUP_URL}results/",
)
PREFERRED_BOOKS = ("bet365.us", "BetMGM.us", "Stake.com")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

AJAX_HEADERS = {
    **HEADERS,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

TEAM_EN = {
    "墨西哥": "Mexico",
    "南非": "South Africa",
    "韩国": "South Korea",
    "捷克": "Czech Republic",
    "加拿大": "Canada",
    "波黑": "Bosnia and Herzegovina",
    "卡塔尔": "Qatar",
    "瑞士": "Switzerland",
    "巴西": "Brazil",
    "摩洛哥": "Morocco",
    "海地": "Haiti",
    "苏格兰": "Scotland",
    "美国": "United States",
    "巴拉圭": "Paraguay",
    "澳大利亚": "Australia",
    "土耳其": "Turkey",
    "德国": "Germany",
    "库拉索": "Curacao",
    "科特迪瓦": "Ivory Coast",
    "厄瓜多尔": "Ecuador",
    "荷兰": "Netherlands",
    "日本": "Japan",
    "瑞典": "Sweden",
    "突尼斯": "Tunisia",
    "比利时": "Belgium",
    "埃及": "Egypt",
    "伊朗": "Iran",
    "新西兰": "New Zealand",
    "西班牙": "Spain",
    "佛得角": "Cape Verde",
    "沙特阿拉伯": "Saudi Arabia",
    "乌拉圭": "Uruguay",
    "法国": "France",
    "塞内加尔": "Senegal",
    "伊拉克": "Iraq",
    "挪威": "Norway",
    "阿根廷": "Argentina",
    "阿尔及利亚": "Algeria",
    "奥地利": "Austria",
    "约旦": "Jordan",
    "葡萄牙": "Portugal",
    "民主刚果": "DR Congo",
    "乌兹别克斯坦": "Uzbekistan",
    "哥伦比亚": "Colombia",
    "英格兰": "England",
    "克罗地亚": "Croatia",
    "加纳": "Ghana",
    "巴拿马": "Panama",
}


def _norm(value):
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _team_norms(value):
    norms = {_norm(value)}
    aliases = {
        "United States": ("USA", "US"),
        "USA": ("United States", "US"),
        "Bosnia and Herzegovina": ("Bosnia & Herzegovina", "Bosnia Herzegovina"),
        "Bosnia & Herzegovina": ("Bosnia and Herzegovina", "Bosnia Herzegovina"),
        "DR Congo": ("D.R. Congo", "Democratic Republic of the Congo"),
        "D.R. Congo": ("DR Congo", "Democratic Republic of the Congo"),
        "Curacao": ("Curaçao",),
        "Curaçao": ("Curacao",),
    }
    for alias in aliases.get(value, ()):
        norms.add(_norm(alias))
    return norms


def _teams_match(row_home, row_away, home_en, away_en):
    row_home_norm = _norm(row_home)
    row_away_norm = _norm(row_away)
    home_norms = _team_norms(home_en)
    away_norms = _team_norms(away_en)
    if row_home_norm in home_norms and row_away_norm in away_norms:
        return True, False
    if row_home_norm in away_norms and row_away_norm in home_norms:
        return True, True
    return False, False


def _fetch_doc(session, url):
    cache = getattr(session, "_betexplorer_doc_cache", None)
    if cache is None:
        cache = {}
        setattr(session, "_betexplorer_doc_cache", cache)
    if url in cache:
        return cache[url]

    response = _get_with_retries(session, url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    doc = lxml.html.fromstring(response.text)
    cache[url] = doc
    return doc


def _get_with_retries(session, url, **kwargs):
    last_exc = None
    for attempt in range(3):
        try:
            return session.get(url, **kwargs)
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(0.8 + attempt * 0.7)
    raise last_exc


def _find_betexplorer_event(session, match):
    home_en = TEAM_EN.get(match.team1, match.team1)
    away_en = TEAM_EN.get(match.team2, match.team2)

    for url in BETEXPLORER_EVENT_LIST_URLS:
        doc = _fetch_doc(session, url)

        for link in doc.xpath("//a[contains(@href, '/football/world/world-championship-2026/')]"):
            href = link.get("href") or ""
            event_match = re.search(r"/([A-Za-z0-9]{8})/?$", href)
            if not event_match:
                continue

            link_text = " ".join(link.text_content().split())
            if " - " not in link_text:
                continue
            row_home, row_away = [part.strip() for part in link_text.split(" - ", 1)]
            matched, is_reversed = _teams_match(row_home, row_away, home_en, away_en)
            if not matched:
                continue

            detail_url = BETEXPLORER_BASE + href if href.startswith("/") else href
            return {
                "event_id": event_match.group(1),
                "detail_url": detail_url,
                "row_home": row_home,
                "row_away": row_away,
                "is_reversed": is_reversed,
            }

        for item in doc.xpath("//li[contains(@class, 'tournamentLiContent')][@data-event-id]"):
            home_nodes = item.xpath(".//*[contains(@class, 'participantHome')]//p")
            away_nodes = item.xpath(".//*[contains(@class, 'participantAway')]//p")
            link_nodes = item.xpath(".//a[contains(@href, '/football/world/world-championship-2026/')]")
            if not home_nodes or not away_nodes or not link_nodes:
                continue

            row_home = " ".join(home_nodes[0].text_content().split())
            row_away = " ".join(away_nodes[0].text_content().split())
            matched, is_reversed = _teams_match(row_home, row_away, home_en, away_en)
            if not matched:
                continue

            href = link_nodes[0].get("href") or ""
            detail_url = BETEXPLORER_BASE + href if href.startswith("/") else href
            return {
                "event_id": item.get("data-event-id"),
                "detail_url": detail_url,
                "row_home": row_home,
                "row_away": row_away,
                "is_reversed": is_reversed,
            }
    return None


def _score_from_row(row):
    for node in row.xpath(".//td//a | .//td"):
        text = " ".join(node.text_content().split())
        match = re.match(r"^(\d+)\s*:\s*(\d+)$", text)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def update_match_score(match, session=None):
    close_session = session is None
    session = session or requests.Session()
    home_en = TEAM_EN.get(match.team1, match.team1)
    away_en = TEAM_EN.get(match.team2, match.team2)

    try:
        for url in BETEXPLORER_EVENT_LIST_URLS:
            doc = _fetch_doc(session, url)
            for link in doc.xpath("//a[contains(@href, '/football/world/world-championship-2026/')]"):
                href = link.get("href") or ""
                if not re.search(r"/[A-Za-z0-9]{8}/?$", href):
                    continue

                link_text = " ".join(link.text_content().split())
                if " - " not in link_text:
                    continue
                row_home, row_away = [part.strip() for part in link_text.split(" - ", 1)]
                matched, is_reversed = _teams_match(row_home, row_away, home_en, away_en)
                if not matched:
                    continue

                rows = link.xpath("./ancestor::tr[1]")
                if not rows:
                    continue
                score = _score_from_row(rows[0])
                if not score:
                    return False, "BetExplorer 暂未给出完场比分"

                score1, score2 = score
                if is_reversed:
                    score1, score2 = score2, score1
                match.score1 = score1
                match.score2 = score2
                match.status = "finished"
                db.session.commit()
                return True, f"已更新真实比分 {score1}-{score2}"
    except requests.RequestException as exc:
        return False, f"BetExplorer 比分联网失败：{exc.__class__.__name__}"
    finally:
        if close_session:
            session.close()

    return False, "BetExplorer 未找到该场比分"


def update_finished_scores(limit=None):
    session = requests.Session()
    count = 0
    candidates = Match.query.filter(Match.match_no <= 104, Match.status != "finished").order_by(Match.match_no).all()
    for match in candidates:
        if limit is not None and count >= limit:
            break
        changed, _ = update_match_score(match, session=session)
        if changed:
            count += 1
    return count


def _parse_bookmaker_rows(odds_html):
    doc = lxml.html.fromstring(odds_html)
    rows = {}

    for row in doc.xpath("//tr[@data-bid or @data-originid or .//*[@data-odd]]"):
        row_text = " ".join(row.text_content().split())
        book = next((name for name in PREFERRED_BOOKS if name.lower() in row_text.lower()), None)
        if not book:
            continue

        values = []
        for node in row.xpath(".//*[@data-odd]")[:3]:
            try:
                values.append(round(float(node.get("data-odd")), 2))
            except (TypeError, ValueError):
                continue
        if len(values) == 3:
            rows[book] = values

    if rows:
        return rows

    text = " ".join(doc.text_content().split())
    for book in PREFERRED_BOOKS:
        found = re.search(
            rf"{re.escape(book)}\s+([1-9]\d?\.\d{{2}})\s+([1-9]\d?\.\d{{2}})\s+([1-9]\d?\.\d{{2}})",
            text,
            re.I,
        )
        if found:
            rows[book] = [round(float(value), 2) for value in found.groups()]
    return rows


def _parse_1x2_detail(session, event):
    headers = {**AJAX_HEADERS, "Referer": event["detail_url"]}
    response = _get_with_retries(
        session,
        f"{BETEXPLORER_BASE}/match-odds/{event['event_id']}/0/1x2/odds/",
        headers=headers,
        params={"lang": "en"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return _parse_bookmaker_rows(payload.get("odds", ""))


def _apply_1x2(match, event, bookmaker_odds):
    order = ["home_win", "draw", "away_win"]
    if event["is_reversed"]:
        order = ["away_win", "draw", "home_win"]

    values_by_selection = {selection: [] for selection in order}
    for book in PREFERRED_BOOKS:
        values = bookmaker_odds.get(book)
        if not values:
            continue
        for selection, value in zip(order, values):
            values_by_selection[selection].append((book, value))

    changed = False
    now = datetime.utcnow()
    for odds in Odds.query.filter_by(match_id=match.id, odds_type="win_draw_lose").all():
        items = values_by_selection.get(odds.selection, [])[:3]
        if not items:
            continue

        names = [name for name, _ in items]
        values = [value for _, value in items]
        odds.bet365_current = values[0] if len(values) > 0 else None
        odds.willhill_current = values[1] if len(values) > 1 else None
        odds.pinnacle_current = values[2] if len(values) > 2 else None
        odds.bet365_initial = odds.bet365_initial or odds.bet365_current
        odds.willhill_initial = odds.willhill_initial or odds.willhill_current
        odds.pinnacle_initial = odds.pinnacle_initial or odds.pinnacle_current
        odds.source_one_name = names[0] if len(names) > 0 else None
        odds.source_two_name = names[1] if len(names) > 1 else None
        odds.source_three_name = names[2] if len(names) > 2 else None
        odds.avg_current = round(sum(values) / len(values), 2)
        odds.avg_initial = odds.avg_initial or odds.avg_current
        odds.source_url = event["detail_url"]
        odds.source_note = (
            f"BetExplorer 1X2: {event['row_home']} vs {event['row_away']}; "
            + "; ".join(f"{name}={vals[0]}/{vals[1]}/{vals[2]}" for name, vals in bookmaker_odds.items())
        )
        odds.verified_at = now
        changed = True
    return changed


def update_match_odds(match, force=False):
    odds_rows = Odds.query.filter_by(match_id=match.id, odds_type="win_draw_lose").all()
    if not force:
        recent = [o for o in odds_rows if o.verified_at and datetime.utcnow() - o.verified_at < timedelta(minutes=20)]
        if recent:
            return False, "20分钟内已更新过"

    session = requests.Session()
    return _update_match_odds_with_session(match, session)


def _update_match_odds_with_session(match, session):
    try:
        event = _find_betexplorer_event(session, match)
        if not event:
            return False, "BetExplorer 未找到该场比赛"

        bookmaker_odds = _parse_1x2_detail(session, event)
    except requests.RequestException as exc:
        return False, f"BetExplorer 联网失败：{exc.__class__.__name__}"

    if not bookmaker_odds:
        return False, "BetExplorer 详情页暂未返回 1X2 机构赔率"

    changed = _apply_1x2(match, event, bookmaker_odds)
    db.session.commit()
    if changed:
        return True, f"已从 BetExplorer 更新 {len(bookmaker_odds)} 家机构 1X2 赔率"
    return False, "没有可写入的新赔率"


def update_all_betexplorer_odds(limit=None):
    count = 0
    session = requests.Session()
    matches = Match.query.filter(Match.match_no <= 72).order_by(Match.match_no).all()
    for match in matches:
        if limit is not None and count >= limit:
            break
        changed, _ = _update_match_odds_with_session(match, session)
        if changed:
            count += 1
    return count
