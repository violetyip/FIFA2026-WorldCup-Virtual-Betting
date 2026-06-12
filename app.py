import os
import threading
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Match, Odds, Bet, Transaction
from odds_updater import update_all_betexplorer_odds, update_finished_scores, update_match_odds, update_match_score

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-fifa-worldcup-betting-sim-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///betting.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─── 辅助函数 ───────────────────────────────────────────

def get_selection_label(selection):
    labels = {
        'home_win': '主胜', 'draw': '平局', 'away_win': '客胜',
    }
    return labels.get(selection, selection)


def get_odds_type_label(ot):
    return '胜平负' if ot == 'win_draw_lose' else ot


app.jinja_env.globals.update(get_selection_label=get_selection_label)
REFRESHING_ODDS = set()
REFRESHING_ALL_ODDS = False
REFRESHING_SCORES = False


def now_bjt():
    return datetime.utcnow() + timedelta(hours=8)


def refresh_match_odds_async(match_id, force=False):
    if match_id in REFRESHING_ODDS:
        return
    REFRESHING_ODDS.add(match_id)

    def worker():
        try:
            with app.app_context():
                match = Match.query.get(match_id)
                if match:
                    update_match_odds(match, force=force)
        finally:
            REFRESHING_ODDS.discard(match_id)

    threading.Thread(target=worker, daemon=True).start()


def refresh_all_odds_async():
    global REFRESHING_ALL_ODDS
    if REFRESHING_ALL_ODDS:
        return
    REFRESHING_ALL_ODDS = True

    def worker():
        global REFRESHING_ALL_ODDS
        try:
            with app.app_context():
                update_all_betexplorer_odds(limit=72)
        finally:
            REFRESHING_ALL_ODDS = False

    threading.Thread(target=worker, daemon=True).start()


def refresh_scores_async():
    global REFRESHING_SCORES
    if REFRESHING_SCORES:
        return
    REFRESHING_SCORES = True

    def worker():
        global REFRESHING_SCORES
        try:
            with app.app_context():
                update_finished_scores()
        finally:
            REFRESHING_SCORES = False

    threading.Thread(target=worker, daemon=True).start()


def record_transaction(user, ttype, amount, desc):
    """记录交易行为"""
    t = Transaction(
        user_id=user.id, type=ttype, amount=amount,
        balance_after=user.bet_balance if ttype != 'deposit' and ttype != 'withdraw' else user.wallet_balance,
        description=desc
    )
    db.session.add(t)


def settle_match(match):
    """结算一场比赛的所有投注"""
    if match.status != 'finished':
        return
    result = match.result

    bets = Bet.query.filter_by(match_id=match.id, status='pending').all()
    for bet in bets:
        if bet.odds_type == 'win_draw_lose':
            if bet.selection == result:
                bet.status = 'won'
                bet.payout = bet.amount * bet.odds_value
                bet.user.bet_balance += bet.payout
                record_transaction(bet.user, 'bet_win', bet.payout,
                                   f'投注命中: {match.team1} vs {match.team2} {get_selection_label(bet.selection)}，赔率{bet.odds_value}，赢得{bet.payout:.2f}')
            else:
                bet.status = 'lost'
                bet.payout = 0
                record_transaction(bet.user, 'bet_lose', -bet.amount,
                                   f'投注未中: {match.team1} vs {match.team2} {get_selection_label(bet.selection)}，损失{bet.amount:.2f}')
    db.session.commit()


def check_and_settle_matches():
    """检查并结算已结束的比赛"""
    now = now_bjt()
    live_matches = Match.query.filter_by(status='live').all()
    for match in live_matches:
        if match.match_time + timedelta(hours=2) <= now:
            changed, _ = update_match_score(match)
            if changed:
                settle_match(match)

    # 自动将 upcoming 比赛在开赛前关闭投注
    upcoming = Match.query.filter_by(status='upcoming').all()
    for match in upcoming:
        if match.match_time <= now:
            match.status = 'live'


# ─── 路由 ───────────────────────────────────────────────

@app.before_request
def before_request():
    check_and_settle_matches()


@app.route('/')
def index():
    check_and_settle_matches()
    refresh_scores_async()
    refresh_all_odds_async()
    groups = {}
    matches = Match.query.order_by(Match.match_no).all()
    for m in matches:
        groups.setdefault(m.group_name, []).append(m)

    # 只展示当前登录账号自己的模拟结果；未登录时不展示实况面板。
    if current_user.is_authenticated:
        user_bets_query = Bet.query.filter_by(user_id=current_user.id)
        total_bets = user_bets_query.count()
        total_won = user_bets_query.filter_by(status='won').count()
        total_lost = user_bets_query.filter_by(status='lost').count()
        total_amount = db.session.query(db.func.sum(Bet.amount)).filter_by(user_id=current_user.id).scalar() or 0
        total_payout = db.session.query(db.func.sum(Bet.payout)).filter_by(user_id=current_user.id).scalar() or 0
    else:
        total_bets = total_won = total_lost = 0
        total_amount = total_payout = 0

    stats = {
        'total_bets': total_bets,
        'total_won': total_won,
        'total_lost': total_lost,
        'win_rate': (total_won / total_bets * 100) if total_bets > 0 else 0,
        'total_amount': total_amount,
        'total_payout': total_payout,
        'profit': total_payout - total_amount,
    }
    return render_template('index.html', groups=groups, stats=stats)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        user = User.query.filter_by(username=username).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        flash('账号不存在，请先注册', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if not username:
            flash('请输入账号', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('该账号已存在', 'danger')
        else:
            user = User(username=username, wallet_balance=10000.0, bet_balance=0.0)
            user.set_password(os.urandom(16).hex())
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('注册成功！现实资金默认为 10,000 元', 'success')
            return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/match/<int:match_id>')
def match_detail(match_id):
    check_and_settle_matches()
    match = Match.query.get_or_404(match_id)
    refresh_match_odds_async(match.id, force=True)
    odds_list = Odds.query.filter_by(match_id=match_id).all()

    # 按盘口类型分组
    wl_odds = [o for o in odds_list if o.odds_type == 'win_draw_lose']

    # 当前用户在此比赛的投注
    user_bets = []
    if current_user.is_authenticated:
        user_bets = Bet.query.filter_by(user_id=current_user.id, match_id=match_id).all()

    # 计算距离开赛时间
    now = now_bjt()
    time_to_match = (match.match_time - now).total_seconds()
    can_bet = (match.status == 'upcoming' and 0 < time_to_match <= 48 * 3600)
    betting_closed = match.status in ('live', 'finished', 'betting_closed')

    return render_template('match.html', match=match, wl_odds=wl_odds,
                           user_bets=user_bets, can_bet=can_bet, betting_closed=betting_closed,
                           time_to_match=time_to_match)


@app.route('/bet', methods=['POST'])
@login_required
def place_bet():
    match_id = int(request.form.get('match_id'))
    odds_id = int(request.form.get('odds_id'))
    amount = float(request.form.get('amount', 0))

    match = Match.query.get_or_404(match_id)
    odds = Odds.query.get_or_404(odds_id)
    if odds.match_id != match.id:
        flash('赔率信息与比赛不匹配，请重新选择', 'danger')
        return redirect(url_for('match_detail', match_id=match_id))

    odds_type = odds.odds_type
    selection = odds.selection
    odds_value = odds.avg_current
    if odds_type != 'win_draw_lose':
        flash('本项目已取消大小球玩法，只保留胜平负。', 'danger')
        return redirect(url_for('match_detail', match_id=match_id))
    if odds_value is None:
        flash('该选项暂未录入可核验的真实赔率，不能下注', 'danger')
        return redirect(url_for('match_detail', match_id=match_id))

    # 验证
    now = now_bjt()
    time_to_match = (match.match_time - now).total_seconds()
    if match.status != 'upcoming' or time_to_match <= 0 or time_to_match > 48 * 3600:
        flash('该比赛当前不可投注', 'danger')
        return redirect(url_for('match_detail', match_id=match_id))

    if amount <= 0 or amount > 5000:
        flash('投注金额需在 0-5000 之间', 'danger')
        return redirect(url_for('match_detail', match_id=match_id))

    if current_user.bet_balance < amount:
        flash('网站赌资不足，请先从现实资金转入', 'danger')
        return redirect(url_for('match_detail', match_id=match_id))

    # 检查单场限额
    existing = Bet.query.filter_by(user_id=current_user.id, match_id=match_id).all()
    total_on_match = sum(b.amount for b in existing)
    if total_on_match + amount > 5000:
        flash(f'本场已投注 {total_on_match:.0f} 元，单场上限 5000 元', 'danger')
        return redirect(url_for('match_detail', match_id=match_id))

    # 下注
    current_user.bet_balance -= amount
    bet = Bet(
        user_id=current_user.id, match_id=match_id,
        odds_type=odds_type, selection=selection,
        odds_value=odds_value, amount=amount
    )
    db.session.add(bet)
    record_transaction(current_user, 'bet_place', -amount,
                       f'下注: {match.team1} vs {match.team2} {get_selection_label(selection)} @ {odds_value}，金额 {amount:.2f}')
    db.session.commit()

    flash(f'下注成功！{get_selection_label(selection)} {amount:.2f} 元 @ {odds_value}', 'success')
    return redirect(url_for('match_detail', match_id=match_id))


@app.route('/wallet')
@login_required
def wallet():
    return render_template('wallet.html')


@app.route('/wallet/deposit', methods=['POST'])
@login_required
def deposit():
    amount = float(request.form.get('amount', 0))
    if amount <= 0:
        flash('转入金额需大于 0', 'danger')
        return redirect(url_for('wallet'))
    if current_user.wallet_balance < amount:
        flash('现实资金不足', 'danger')
        return redirect(url_for('wallet'))
    current_user.wallet_balance -= amount
    current_user.bet_balance += amount
    record_transaction(current_user, 'deposit', amount, f'从现实资金转入网站赌资: {amount:.2f} 元')
    db.session.commit()
    flash(f'转入成功！{amount:.2f} 元已进入网站赌资', 'success')
    return redirect(url_for('wallet'))


@app.route('/wallet/withdraw', methods=['POST'])
@login_required
def withdraw():
    amount = float(request.form.get('amount', 0))
    if amount <= 0:
        flash('提回金额需大于 0', 'danger')
        return redirect(url_for('wallet'))
    if current_user.bet_balance < amount:
        flash('网站赌资不足', 'danger')
        return redirect(url_for('wallet'))
    current_user.bet_balance -= amount
    current_user.wallet_balance += amount
    record_transaction(current_user, 'withdraw', amount, f'从网站赌资提回现实资金: {amount:.2f} 元')
    db.session.commit()
    flash(f'提回成功！{amount:.2f} 元已回到现实资金', 'success')
    return redirect(url_for('wallet'))


@app.route('/my_bets')
@login_required
def my_bets():
    bets = Bet.query.filter_by(user_id=current_user.id).order_by(Bet.created_at.desc()).all()
    # 统计
    total_bet = sum(b.amount for b in bets if b.status != 'pending')
    total_won = sum(b.payout for b in bets if b.status == 'won')
    total_stake = sum(b.amount for b in bets)
    return render_template('my_bets.html', bets=bets, total_bet=total_bet,
                           total_won=total_won, total_stake=total_stake)


@app.route('/history')
@login_required
def history():
    txns = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.created_at.desc()).all()
    return render_template('history.html', transactions=txns)


# ─── 启动 ───────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001, use_reloader=False)
