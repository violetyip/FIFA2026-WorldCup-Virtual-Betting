from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    wallet_balance = db.Column(db.Float, default=10000.0)   # 真实钱包
    bet_balance = db.Column(db.Float, default=0.0)           # 赌资
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bets = db.relationship('Bet', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    match_no = db.Column(db.Integer, unique=True)
    group_name = db.Column(db.String(20), nullable=False)
    match_day = db.Column(db.Integer, default=1)
    team1 = db.Column(db.String(50), nullable=False)
    team2 = db.Column(db.String(50), nullable=False)
    match_time = db.Column(db.DateTime, nullable=False)      # 北京时间
    venue = db.Column(db.String(120))
    status = db.Column(db.String(20), default='upcoming')    # upcoming / betting_closed / live / finished
    score1 = db.Column(db.Integer, default=0)
    score2 = db.Column(db.Integer, default=0)

    odds = db.relationship('Odds', backref='match', lazy=True)
    bets = db.relationship('Bet', backref='match', lazy=True)

    @property
    def total_goals(self):
        return self.score1 + self.score2

    @property
    def result(self):
        """胜平负结果"""
        if self.status != 'finished':
            return None
        if self.score1 > self.score2:
            return 'home_win'
        elif self.score1 < self.score2:
            return 'away_win'
        else:
            return 'draw'

    @property
    def over_under_result(self):
        """大小球结果 (盘口2.5)"""
        if self.status != 'finished':
            return None
        return 'over' if self.total_goals > 2.5 else 'under'


class Odds(db.Model):
    __tablename__ = 'odds'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    odds_type = db.Column(db.String(20), nullable=False)       # win_draw_lose / over_under
    selection = db.Column(db.String(20), nullable=False)        # home_win/draw/away_win/over/under

    bet365_initial = db.Column(db.Float)
    bet365_current = db.Column(db.Float)
    willhill_initial = db.Column(db.Float)
    willhill_current = db.Column(db.Float)
    pinnacle_initial = db.Column(db.Float)
    pinnacle_current = db.Column(db.Float)
    avg_initial = db.Column(db.Float)
    avg_current = db.Column(db.Float)
    source_one_name = db.Column(db.String(80))
    source_two_name = db.Column(db.String(80))
    source_three_name = db.Column(db.String(80))
    source_note = db.Column(db.String(300))
    source_url = db.Column(db.String(300))
    verified_at = db.Column(db.DateTime)


class Bet(db.Model):
    __tablename__ = 'bets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    odds_type = db.Column(db.String(20), nullable=False)
    selection = db.Column(db.String(20), nullable=False)
    odds_value = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')      # pending / won / lost
    payout = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)            # deposit/withdraw/bet_place/bet_win/bet_lose
    amount = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float)                        # 操作后余额
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
