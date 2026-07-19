"""
项目资金实时跟踪与预警管理系统 — FastAPI 后端
"""
import os, sqlite3, json, calendar
from datetime import date, datetime, timedelta
from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import logging
import bcrypt
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "fund-tracker-secret-key-2026")
JWT_ALG = "HS256"

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Fund Tracker")
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "funds.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db

# ═══════════ 数据库初始化 ═══════════
def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            parent_id INTEGER DEFAULT NULL,
            budget REAL DEFAULT 0,
            stop_loss REAL DEFAULT 0,
            risk_ratio REAL DEFAULT 0.9,
            category TEXT DEFAULT 'main',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        
        CREATE TABLE IF NOT EXISTS expansion_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            level INTEGER NOT NULL,
            name TEXT NOT NULL,
            conditions TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            day_seq INTEGER NOT NULL DEFAULT 0,
            amount REAL NOT NULL,
            project_id INTEGER,
            remark TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            alert_type TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            resolved_at TEXT,
            resolve_note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        
        CREATE TABLE IF NOT EXISTS expansion_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            level INTEGER NOT NULL,
            operator TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        
        CREATE TABLE IF NOT EXISTS daily_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            net_amount REAL DEFAULT 0,
            total_income REAL DEFAULT 0,
            total_expense REAL DEFAULT 0,
            budget_usage REAL DEFAULT 0,
            stop_loss_diff REAL DEFAULT 0,
            expansion_level INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    db.commit()
    # 插入默认项目（如为空）
    count = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    if count == 0:
        db.executescript("""
            INSERT INTO projects (name, code, category, budget, stop_loss, risk_ratio) 
            VALUES ('项目A', 'A', 'main', 500000, 100000, 0.9);
            INSERT INTO projects (name, code, category, budget, stop_loss, risk_ratio) 
            VALUES ('项目B', 'B', 'main', 300000, 50000, 0.85);
            INSERT INTO projects (name, code, category, budget, stop_loss, risk_ratio) 
            VALUES ('项目C', 'C', 'main', 200000, 30000, 0.8);
            INSERT INTO projects (name, code, category, budget, stop_loss, risk_ratio) 
            VALUES ('其他', 'OTHER', 'other', 0, 0, 0);
        """)
        db.commit()
    db.close()

init_db()

# ═══════════ 认证工具 ═══════════
def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def create_token(user_id: int, phone: str) -> str:
    payload = {"user_id": user_id, "phone": phone, "exp": datetime.utcnow() + timedelta(days=30)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def verify_token(authorization: str) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录或token无效")
    try:
        token = authorization[7:]
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "token已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "token无效")

def _uid(authorization: str) -> int:
    return verify_token(authorization)["user_id"]

def get_current_user(authorization: str = Header(...)) -> dict:
    """FastAPI 依赖注入：验证token，返回用户信息"""
    return verify_token(authorization)

# ═══════════ 模型 ═══════════
class TransactionIn(BaseModel):
    date: str
    amount: float
    project_id: Optional[int] = None
    remark: str = ""

class ProjectIn(BaseModel):
    name: str
    code: str
    parent_id: Optional[int] = None
    budget: float = 0
    stop_loss: float = 0
    risk_ratio: float = 0.9
    category: str = "main"

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    budget: Optional[float] = None
    stop_loss: Optional[float] = None
    risk_ratio: Optional[float] = None

class ExpansionIn(BaseModel):
    project_id: int
    level: int
    name: str
    conditions: str = "{}"

class AlertResolve(BaseModel):
    status: str = "resolved"
    resolve_note: str = ""

class AuthRegister(BaseModel):
    phone: str
    password: str

class AuthLogin(BaseModel):
    phone: str
    password: str

# ═══════════ 认证 API ═══════════
@app.post("/api/auth/register")
def register(body: AuthRegister):
    if not body.phone or not body.password:
        raise HTTPException(400, "手机号和密码不能为空")
    if len(body.password) < 6:
        raise HTTPException(400, "密码至少6位")
    db = get_db()
    exist = db.execute("SELECT id FROM users WHERE phone=?", (body.phone.strip(),)).fetchone()
    if exist:
        db.close()
        raise HTTPException(409, "该手机号已注册")
    hashed = hash_password(body.password)
    db.execute("INSERT INTO users (phone, password_hash) VALUES (?,?)", (body.phone.strip(), hashed))
    db.commit()
    uid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    token = create_token(uid, body.phone.strip())
    db.close()
    return {"token": token, "user_id": uid, "phone": body.phone.strip()}

@app.post("/api/auth/login")
def login(body: AuthLogin):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE phone=?", (body.phone.strip(),)).fetchone()
    db.close()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "手机号或密码错误")
    token = create_token(user["id"], user["phone"])
    return {"token": token, "user_id": user["id"], "phone": user["phone"]}

@app.get("/api/auth/me")
def me(authorization: str = Header(...)):
    payload = verify_token(authorization)
    return {"user_id": payload["user_id"], "phone": payload["phone"]}

# ═══════════ 工具函数 ═══════════
BASE_DATE = date(2025, 1, 1)
def calc_day_seq(d: str) -> int:
    """返回年内第几天：1月1日=1，12月31日=365/366"""
    dt = datetime.strptime(d, "%Y-%m-%d").date()
    return dt.timetuple().tm_yday

def calc_project_net(db, pid: int, date_filter: str = "") -> float:
    filter_clause = f" AND date {date_filter}" if date_filter else ""
    rows = db.execute(
        f"SELECT COALESCE(SUM(amount),0) as net FROM transactions WHERE project_id=?{filter_clause}",
        (pid,)
    ).fetchone()
    sub_rows = db.execute(
        "SELECT id FROM projects WHERE parent_id=?", (pid,)
    ).fetchall()
    net = rows["net"] or 0
    for s in sub_rows:
        net += calc_project_net(db, s["id"], date_filter)
    return net

def calc_project_expense(db, pid: int, date_filter: str = "") -> float:
    filter_clause = f" AND date {date_filter}" if date_filter else ""
    rows = db.execute(
        f"SELECT COALESCE(SUM(amount),0) as exp FROM transactions WHERE project_id=? AND amount<0{filter_clause}",
        (pid,)
    ).fetchone()
    sub_rows = db.execute(
        "SELECT id FROM projects WHERE parent_id=?", (pid,)
    ).fetchall()
    exp = abs(rows["exp"] or 0)
    for s in sub_rows:
        exp += calc_project_expense(db, s["id"], date_filter)
    return exp

def sync_parent_budget(db, parent_id: int):
    """子项目预算变动后，自动汇总到父项目"""
    total = db.execute(
        "SELECT COALESCE(SUM(budget),0) FROM projects WHERE parent_id=?", (parent_id,)
    ).fetchone()[0]
    db.execute("UPDATE projects SET budget=? WHERE id=?", (total, parent_id))

def check_alerts(db, pid: int):
    proj = db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    if not proj or proj["category"] == "other":
        return
    net = calc_project_net(db, pid)
    expense = calc_project_expense(db, pid)
    budget = proj["budget"] or 1
    stop_loss = proj["stop_loss"] or 1
    risk_ratio = proj["risk_ratio"] or 0.9
    
    # 预算预警：仅当预算>0 且 项目净资金≤0（亏损）时触发
    if budget <= 0 or net > 0:
        clear_alert(db, pid, "budget")
        clear_alert(db, pid, "budget_rate")
    else:
        budget_pct = expense / budget
        if budget_pct >= 1.0:
            upsert_alert(db, pid, "budget", "danger", f"预算已超支 {budget_pct*100:.0f}%")
        elif budget_pct >= 0.95:
            upsert_alert(db, pid, "budget", "warning", f"预算使用 {budget_pct*100:.0f}%(≥95%)")
        elif budget_pct >= 0.80:
            upsert_alert(db, pid, "budget", "info", f"预算使用 {budget_pct*100:.0f}%(≥80%)")
        else:
            clear_alert(db, pid, "budget")
        
        # 预算消耗速率：按近7日日均支出，剩余可支撑天数
        seven_days_ago = (date.today() - timedelta(days=7)).isoformat()
        recent = db.execute(
            "SELECT COALESCE(SUM(amount),0) as exp FROM transactions WHERE project_id=? AND amount<0 AND date >= ?",
            (pid, seven_days_ago)
        ).fetchone()
        daily_avg = abs(recent["exp"] or 0) / 7
        if daily_avg > 0:
            remaining = budget - expense
            days_left = remaining / daily_avg
            if days_left <= 7:
                upsert_alert(db, pid, "budget_rate", "danger", f"按近7日支出速度，预算{days_left:.0f}天后耗尽")
            elif days_left <= 14:
                upsert_alert(db, pid, "budget_rate", "warning", f"按近7日支出速度，预算{days_left:.0f}天后耗尽")
            elif days_left <= 30:
                upsert_alert(db, pid, "budget_rate", "info", f"预算还可支撑{days_left:.0f}天")
            else:
                clear_alert(db, pid, "budget_rate")
        else:
            clear_alert(db, pid, "budget_rate")
    
    # 止损预警：净资金接近止损值
    if stop_loss > 0:
        ratio = abs(net) / stop_loss if net < 0 else 0
        if ratio >= risk_ratio and net < 0:
            upsert_alert(db, pid, "stop_loss", "danger", f"净资金趋近止损线 ({ratio*100:.0f}%)")
        elif abs(net) < stop_loss * 1.2 and net < 0:
            upsert_alert(db, pid, "stop_loss", "warning", f"资金接近止损线")
        else:
            clear_alert(db, pid, "stop_loss")

def upsert_alert(db, pid, atype, level, msg):
    exist = db.execute(
        "SELECT id, status FROM alerts WHERE project_id=? AND alert_type=? AND status='active'",
        (pid, atype)
    ).fetchone()
    if not exist:
        db.execute(
            "INSERT INTO alerts (project_id, alert_type, level, message) VALUES (?,?,?,?)",
            (pid, atype, level, msg)
        )
    elif exist["status"] == "active":
        db.execute(
            "UPDATE alerts SET level=?, message=?, created_at=datetime('now','localtime') WHERE id=?",
            (level, msg, exist["id"])
        )

def clear_alert(db, pid, atype):
    db.execute(
        "UPDATE alerts SET status='auto_cleared', resolved_at=datetime('now','localtime') WHERE project_id=? AND alert_type=? AND status='active'",
        (pid, atype)
    )

def check_expansion_drawdown(db, pid):
    """检查已解锁的拓展等级是否回撤（净资金/预算跌破解锁条件）"""
    unlocked = db.execute(
        "SELECT DISTINCT level FROM expansion_records WHERE project_id=? ORDER BY level",
        (pid,)
    ).fetchall()
    if not unlocked:
        return  # 未解锁任何等级，跳过

    proj = db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    if not proj:
        return
    net = calc_project_net(db, pid)
    expense = calc_project_expense(db, pid)
    budget_usage = expense / (proj["budget"] or 1) * 100

    for row in unlocked:
        level = row["level"]
        lv = db.execute(
            "SELECT * FROM expansion_levels WHERE project_id=? AND level=?",
            (pid, level)
        ).fetchone()
        if not lv:
            continue
        conds = json.loads(lv["conditions"] or "{}")
        alert_type = f"expansion_drawdown_{level}"

        drawdown = False
        msgs = []
        for k, v in conds.items():
            if k == "net_min" and net < v:
                drawdown = True
                msgs.append(f"净资金<¥{v}(当前¥{round(net)})")
            elif k == "budget_max" and budget_usage > v:
                drawdown = True
                msgs.append(f"预算>{v}%(当前{round(budget_usage,1)}%)")

        if drawdown:
            upsert_alert(db, pid, alert_type, "warning",
                         f"第{level}级「{lv['name']}」回撤 | " + ", ".join(msgs))
        else:
            clear_alert(db, pid, alert_type)

    # 清理已删除等级的残留告警（只清除不再存在于 expansion_levels 的等级）
    all_levels = db.execute(
        "SELECT level FROM expansion_levels WHERE project_id=?", (pid,)
    ).fetchall()
    valid_types = [f"expansion_drawdown_{r['level']}" for r in all_levels]
    if valid_types:
        placeholders = ','.join(['?'] * len(valid_types))
        db.execute(
            f"UPDATE alerts SET status='auto_cleared', resolved_at=datetime('now','localtime') "
            f"WHERE project_id=? AND alert_type LIKE 'expansion_drawdown_%' "
            f"AND status='active' AND alert_type NOT IN ({placeholders})",
            (pid, *valid_types)
        )
    else:
        db.execute(
            "UPDATE alerts SET status='auto_cleared', resolved_at=datetime('now','localtime') "
            "WHERE project_id=? AND alert_type LIKE 'expansion_drawdown_%' AND status='active'",
            (pid,)
        )

# ═══════════ 项目 API ═══════════
@app.get("/api/projects")
def list_projects(user: dict = Depends(get_current_user)):
    db = get_db()
    rows = db.execute("SELECT * FROM projects ORDER BY category, id").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["net_amount"] = calc_project_net(db, r["id"])
        d["total_expense"] = calc_project_expense(db, r["id"])
        d["budget_usage"] = round(d["total_expense"] / d["budget"] * 100, 1) if d["budget"] > 0 else 0
        d["stop_loss_diff"] = round(d["net_amount"] - d["stop_loss"], 2)
        d["alert_count"] = db.execute(
            "SELECT COUNT(*) FROM alerts WHERE project_id=? AND status='active'",
            (r["id"],)
        ).fetchone()[0]
        # 拓展等级：已解锁最高级 + 总等级数
        top = db.execute(
            "SELECT level FROM expansion_records WHERE project_id=? ORDER BY level DESC LIMIT 1",
            (r["id"],)
        ).fetchone()
        d["expansion_level"] = top[0] if top else 0
        d["expansion_total"] = db.execute(
            "SELECT COUNT(*) FROM expansion_levels WHERE project_id=?", (r["id"],)
        ).fetchone()[0]
        result.append(d)
    db.close()
    return result

@app.post("/api/projects")
def create_project(p: ProjectIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db.execute(
        "INSERT INTO projects (name, code, parent_id, budget, stop_loss, risk_ratio, category) VALUES (?,?,?,?,?,?,?)",
        (p.name, p.code, p.parent_id, p.budget, p.stop_loss, p.risk_ratio, p.category)
    )
    db.commit()
    pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    if p.parent_id:
        sync_parent_budget(db, p.parent_id)
        db.commit()
    db.close()
    return {"id": pid}

@app.put("/api/projects/{pid}")
def update_project(pid: int, p: ProjectUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    existing = db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    if not existing:
        db.close()
        raise HTTPException(404, "项目不存在")
    db.execute(
        "UPDATE projects SET name=?, budget=?, stop_loss=?, risk_ratio=? WHERE id=?",
        (p.name or existing["name"], 
         p.budget if p.budget is not None else existing["budget"],
         p.stop_loss if p.stop_loss is not None else existing["stop_loss"],
         p.risk_ratio if p.risk_ratio is not None else existing["risk_ratio"],
         pid)
    )
    db.commit()
    if existing["parent_id"]:
        sync_parent_budget(db, existing["parent_id"])
        db.commit()
    db.close()
    return {"ok": True}

@app.delete("/api/projects/{pid}")
def delete_project(pid: int, user: dict = Depends(get_current_user)):
    db = get_db()
    existing = db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    parent_id = existing["parent_id"] if existing else None
    db.execute("DELETE FROM projects WHERE id=?", (pid,))
    db.commit()
    if parent_id:
        sync_parent_budget(db, parent_id)
        db.commit()
    db.close()
    return {"ok": True}

# ═══════════ 流水 API ═══════════
@app.get("/api/transactions")
def list_transactions(user: dict = Depends(get_current_user), 
    project_id: Optional[int] = None,
    start_date: str = "",
    end_date: str = "",
    page: int = 1,
    page_size: int = 30,
):
    db = get_db()
    sql = "SELECT t.*, p.name as project_name, p.code as project_code, p.category, pp.name as parent_name FROM transactions t LEFT JOIN projects p ON t.project_id=p.id LEFT JOIN projects pp ON p.parent_id=pp.id WHERE 1=1"
    params = []
    if project_id:
        sql += " AND t.project_id=?"
        params.append(project_id)
    if start_date:
        sql += " AND t.date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND t.date <= ?"
        params.append(end_date)
    sql += " ORDER BY t.date DESC, t.id DESC"
    
    rows = db.execute(sql, params).fetchall()
    total = len(rows)
    page_size = max(1, min(page_size, 200))
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    
    result = []
    for r in rows[start:start + page_size]:
        d = dict(r)
        d["day_seq"] = calc_day_seq(r["date"])
        # 子项目显示 "父项目 > 子项目"
        if r["category"] == "sub" and r["parent_name"]:
            d["project_name"] = f"{r['parent_name']} > {r['project_name']}"
        result.append(d)

    # 峰值日：正负最多的一天
    where_clauses = []
    peak_params = []
    if project_id:
        where_clauses.append("t.project_id=?")
        peak_params.append(project_id)
    if start_date:
        where_clauses.append("t.date >= ?")
        peak_params.append(start_date)
    if end_date:
        where_clauses.append("t.date <= ?")
        peak_params.append(end_date)
    wc = (" AND " + " AND ".join(where_clauses)) if where_clauses else ""
    
    peak_positive = db.execute(
        "SELECT t.date, t.amount, p.name as project_name, p.category, pp.name as parent_name FROM transactions t LEFT JOIN projects p ON t.project_id=p.id LEFT JOIN projects pp ON p.parent_id=pp.id WHERE 1=1 AND t.amount > 0" + wc + " ORDER BY t.amount DESC LIMIT 1",
        peak_params).fetchone()
    peak_negative = db.execute(
        "SELECT t.date, t.amount, p.name as project_name, p.category, pp.name as parent_name FROM transactions t LEFT JOIN projects p ON t.project_id=p.id LEFT JOIN projects pp ON p.parent_id=pp.id WHERE 1=1 AND t.amount < 0" + wc + " ORDER BY t.amount ASC LIMIT 1",
        peak_params).fetchone()

    def _peak_name(row):
        if row and row["category"] == "sub" and row["parent_name"]:
            r = dict(row)
            r["project_name"] = f"{row['parent_name']} > {row['project_name']}"
            return r
        return dict(row) if row else None
    
    db.close()
    return {
        "items": result, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages,
        "peak_positive": _peak_name(peak_positive),
        "peak_negative": _peak_name(peak_negative),
    }

@app.post("/api/transactions")
def create_transaction(t: TransactionIn, user: dict = Depends(get_current_user)):
    db = get_db()
    day_seq = calc_day_seq(t.date)
    db.execute(
        "INSERT INTO transactions (date, day_seq, amount, project_id, remark) VALUES (?,?,?,?,?)",
        (t.date, day_seq, t.amount, t.project_id, t.remark)
    )
    db.commit()
    tid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    # 检查预警（子项目 + 父项目）
    if t.project_id:
        check_alerts(db, t.project_id)
        check_expansion_drawdown(db, t.project_id)
        parent = db.execute("SELECT parent_id FROM projects WHERE id=?", (t.project_id,)).fetchone()
        if parent and parent["parent_id"]:
            check_alerts(db, parent["parent_id"])
            check_expansion_drawdown(db, parent["parent_id"])
    db.commit()
    db.close()
    return {"id": tid}

@app.put("/api/transactions/{tid}")
def update_transaction(tid: int, t: TransactionIn, user: dict = Depends(get_current_user)):
    db = get_db()
    day_seq = calc_day_seq(t.date)
    db.execute(
        "UPDATE transactions SET date=?, day_seq=?, amount=?, project_id=?, remark=? WHERE id=?",
        (t.date, day_seq, t.amount, t.project_id, t.remark, tid)
    )
    db.commit()
    if t.project_id:
        check_alerts(db, t.project_id)
        check_expansion_drawdown(db, t.project_id)
        parent = db.execute("SELECT parent_id FROM projects WHERE id=?", (t.project_id,)).fetchone()
        if parent and parent["parent_id"]:
            check_alerts(db, parent["parent_id"])
            check_expansion_drawdown(db, parent["parent_id"])
    db.commit()
    db.close()
    return {"ok": True}

@app.delete("/api/transactions/{tid}")
def delete_transaction(tid: int, user: dict = Depends(get_current_user)):
    db = get_db()
    row = db.execute("SELECT project_id FROM transactions WHERE id=?", (tid,)).fetchone()
    db.execute("DELETE FROM transactions WHERE id=?", (tid,))
    db.commit()
    if row and row["project_id"]:
        check_alerts(db, row["project_id"])
        check_expansion_drawdown(db, row["project_id"])
        parent = db.execute("SELECT parent_id FROM projects WHERE id=?", (row["project_id"],)).fetchone()
        if parent and parent["parent_id"]:
            check_alerts(db, parent["parent_id"])
            check_expansion_drawdown(db, parent["parent_id"])
    db.commit()
    db.close()
    return {"ok": True}

# ═══════════ 预警 API ═══════════
@app.get("/api/alerts")
def list_alerts(status: str = "active", user: dict = Depends(get_current_user)):
    db = get_db()
    sql = "SELECT a.*, p.name as project_name FROM alerts a LEFT JOIN projects p ON a.project_id=p.id"
    if status and status != "all":
        sql += " WHERE a.status=?"
        rows = db.execute(sql + " ORDER BY a.created_at DESC", (status,)).fetchall()
    else:
        rows = db.execute(sql + " ORDER BY a.created_at DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]

@app.put("/api/alerts/{aid}")
def resolve_alert(aid: int, body: AlertResolve, user: dict = Depends(get_current_user)):
    db = get_db()
    db.execute(
        "UPDATE alerts SET status=?, resolved_at=datetime('now','localtime'), resolve_note=? WHERE id=?",
        (body.status, body.resolve_note, aid)
    )
    db.commit()
    db.close()
    return {"ok": True}

# ═══════════ 拓展 API ═══════════
@app.get("/api/expansion/{project_id}")
def get_expansion(project_id: int, user: dict = Depends(get_current_user)):
    db = get_db()
    levels = db.execute(
        "SELECT * FROM expansion_levels WHERE project_id=? ORDER BY level",
        (project_id,)
    ).fetchall()
    proj = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not proj:
        raise HTTPException(404, "项目不存在")
    
    net = calc_project_net(db, project_id)
    budget_usage = calc_project_expense(db, project_id) / (proj["budget"] or 1) * 100
    
    # 已解锁等级
    unlocked_set = {r["level"] for r in db.execute(
        "SELECT DISTINCT level FROM expansion_records WHERE project_id=?",
        (project_id,)
    ).fetchall()}
    
    result = []
    for lv in levels:
        conds = json.loads(lv["conditions"] or "{}")
        unlocked = lv["level"] in unlocked_set
        met = True
        detail = {}
        for k, v in conds.items():
            if k == "net_min":
                ok = net >= v
                label = f"净资金≥¥{v:,}"
                detail[label] = "✓" if ok else "✗"
                if not ok: met = False
            elif k == "budget_max":
                ok = budget_usage <= v
                label = f"预算使用≤{v}%"
                detail[label] = "✓" if ok else "✗"
                if not ok: met = False
        result.append({"id": lv["id"], "level": lv["level"], "name": lv["name"],
                       "conditions": conds, "met": met, "detail": detail,
                       "unlocked": unlocked, 
                       "drawdown": unlocked and not met})  # 已解锁但条件不满足=回撤
    db.close()
    return {"levels": result, "net_amount": round(net, 2), "budget_usage": round(budget_usage, 1)}

@app.post("/api/expansion")
def create_expansion(e: ExpansionIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db.execute(
        "INSERT INTO expansion_levels (project_id, level, name, conditions) VALUES (?,?,?,?)",
        (e.project_id, e.level, e.name, e.conditions)
    )
    db.commit()
    db.close()
    return {"ok": True}

@app.put("/api/expansion/{eid}")
def update_expansion(eid: int, e: ExpansionIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db.execute(
        "UPDATE expansion_levels SET level=?, name=?, conditions=? WHERE id=?",
        (e.level, e.name, e.conditions, eid)
    )
    db.commit()
    db.close()
    return {"ok": True}

@app.post("/api/expansion/{project_id}/upgrade")
def upgrade_expansion(project_id: int, level: int = Query(...), user: dict = Depends(get_current_user)):
    db = get_db()
    db.execute(
        "INSERT INTO expansion_records (project_id, level) VALUES (?,?)",
        (project_id, level)
    )
    db.commit()
    db.close()
    return {"ok": True}

@app.delete("/api/expansion/{eid}")
def delete_expansion(eid: int, user: dict = Depends(get_current_user)):
    db = get_db()
    db.execute("DELETE FROM expansion_levels WHERE id=?", (eid,))
    db.commit()
    db.close()
    return {"ok": True}

# ═══════════ 汇总统计 API ═══════════

def _get_date_filter(period: str) -> str:
    today = date.today()
    if not period or period == "all":
        return ""
    elif period == "today":
        return f"date = '{today.isoformat()}'"
    elif period == "yesterday":
        yest = (today - timedelta(days=1)).isoformat()
        return f"date = '{yest}'"
    elif period == "week":
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return f"date >= '{monday.isoformat()}' AND date <= '{sunday.isoformat()}'"
    elif period == "last_week":
        monday = today - timedelta(days=today.weekday())
        last_monday = monday - timedelta(days=7)
        last_sunday = monday - timedelta(days=1)
        return f"date >= '{last_monday.isoformat()}' AND date <= '{last_sunday.isoformat()}'"
    elif period == "month":
        start = today.replace(day=1).isoformat()
        return f"date >= '{start}'"
    elif period == "last_month":
        first = today.replace(day=1)
        if first.month == 1:
            last_start = first.replace(year=first.year-1, month=12, day=1).isoformat()
        else:
            last_start = first.replace(month=first.month-1, day=1).isoformat()
        last_end = (first - timedelta(days=1)).isoformat()
        return f"date >= '{last_start}' AND date <= '{last_end}'"
    elif period == "year":
        start = today.replace(month=1, day=1).isoformat()
        return f"date >= '{start}'"
    elif period == "last_year":
        last_start = today.replace(year=today.year-1, month=1, day=1).isoformat()
        last_end = today.replace(year=today.year-1, month=12, day=31).isoformat()
        return f"date >= '{last_start}' AND date <= '{last_end}'"
    return ""

def _get_period_boundary(period: str) -> tuple:
    """返回 (start_date_str_for_before_query, None_if_open_ended)"""
    today = date.today()
    if not period or period == "all":
        return (None, None)  # 无限范围
    elif period == "today":
        return (today.isoformat(), (today + timedelta(days=1)).isoformat())
    elif period == "yesterday":
        yest = today - timedelta(days=1)
        return (yest.isoformat(), today.isoformat())
    elif period == "week":
        monday = today - timedelta(days=today.weekday())
        return (monday.isoformat(), (monday + timedelta(days=7)).isoformat())
    elif period == "last_week":
        monday = today - timedelta(days=today.weekday())
        last_monday = monday - timedelta(days=7)
        return (last_monday.isoformat(), monday.isoformat())
    elif period == "month":
        start = today.replace(day=1)
        end = (start.replace(month=start.month % 12 + 1, day=1) if start.month < 12
               else start.replace(year=start.year + 1, month=1, day=1))
        return (start.isoformat(), end.isoformat())
    elif period == "last_month":
        first = today.replace(day=1)
        if first.month == 1:
            last_start = first.replace(year=first.year-1, month=12, day=1)
        else:
            last_start = first.replace(month=first.month-1, day=1)
        return (last_start.isoformat(), first.isoformat())
    elif period == "year":
        start = today.replace(month=1, day=1)
        return (start.isoformat(), today.replace(year=today.year + 1, month=1, day=1).isoformat())
    elif period == "last_year":
        last_start = today.replace(year=today.year-1, month=1, day=1)
        last_end = today.replace(year=today.year, month=1, day=1)
        return (last_start.isoformat(), last_end.isoformat())
    return (None, None)

def _calc_project_stats(db, pid: int, date_filter: str) -> dict:
    """计算单个项目的统计（含子项目）"""
    fc = f" AND {date_filter}" if date_filter else ""
    rows = db.execute(
        f"SELECT COALESCE(SUM(amount),0) as net, COALESCE(SUM(CASE WHEN amount>0 THEN amount ELSE 0 END),0) as income, COALESCE(SUM(CASE WHEN amount<0 THEN amount ELSE 0 END),0) as expense FROM transactions WHERE project_id=?{fc}",
        (pid,)
    ).fetchone()
    return {
        "net": round(rows["net"], 2),
        "income": round(rows["income"], 2),
        "expense": round(abs(rows["expense"]), 2),
    }

def _calc_project_balance(db, pid: int, before_date: str) -> float:
    """计算某个日期之前的累计余额"""
    row = db.execute(
        "SELECT COALESCE(SUM(amount),0) as bal FROM transactions WHERE project_id=? AND date < ?",
        (pid, before_date)
    ).fetchone()
    return round(row["bal"], 2)

def _fill_week_daily(raw_daily: list, period: str) -> list:
    """周周期时按日汇总并补全7天，无交易的日子填充0"""
    if period not in ('week', 'last_week'):
        return raw_daily
    # 按日汇总
    agg = {}
    for d in raw_daily:
        agg[d['date']] = agg.get(d['date'], 0) + d['amount']
    # 计算周一
    today = date.today()
    if period == 'week':
        monday = today - timedelta(days=today.weekday())
    else:
        monday = today - timedelta(days=today.weekday() + 7)
    full = []
    for i in range(7):
        d = (monday + timedelta(days=i)).isoformat()
        full.append({'date': d, 'amount': round(agg.get(d, 0), 2)})
    return full

def _build_project_tree(db, period: str) -> list:
    """构建项目层级树，含本期统计 + 上期余额"""
    date_filter = _get_date_filter(period)
    boundary = _get_period_boundary(period)
    
    projs = db.execute("SELECT * FROM projects WHERE category!='other' ORDER BY code").fetchall()
    main = [p for p in projs if not p["parent_id"]]
    subs = [p for p in projs if p["parent_id"]]
    
    result = []
    for m in main:
        children = []
        agg = {"net": 0, "income": 0, "expense": 0}
        agg_balance_before = 0
        for s in subs:
            if s["parent_id"] == m["id"]:
                cs = _calc_project_stats(db, s["id"], date_filter)
                agg["net"] += cs["net"]
                agg["income"] += cs["income"]
                agg["expense"] += cs["expense"]
                # 上期余额
                balance_before = _calc_project_balance(db, s["id"], boundary[0]) if boundary[0] else None
                agg_balance_before += (balance_before or 0)
                balance_after = round((balance_before or 0) + cs["net"], 2) if balance_before is not None else None
                # 日明细
                daily_rows = db.execute(
                    f"SELECT date, amount FROM transactions WHERE project_id=? AND {date_filter} ORDER BY date",
                    (s["id"],)
                ).fetchall() if date_filter else []
                daily = _fill_week_daily([{"date": r["date"], "amount": r["amount"]} for r in daily_rows], period)
                children.append({
                    "id": s["id"], "name": s["name"], "code": s["code"],
                    "net": cs["net"], "income": cs["income"], "expense": cs["expense"],
                    "budget": s["budget"], "stop_loss": s["stop_loss"],
                    "budget_usage": round(cs["expense"] / s["budget"] * 100, 1) if s["budget"] > 0 else 0,
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                    "daily": daily,
                })
        self_stats = _calc_project_stats(db, m["id"], date_filter)
        agg["net"] += self_stats["net"]
        agg["income"] += self_stats["income"]
        agg["expense"] += self_stats["expense"]
        # 主项目日明细 = 汇总所有子项目每日数据
        daily_m = []
        if children:
            agg_by_date = {}
            for c in children:
                for d in c["daily"]:
                    agg_by_date[d["date"]] = round(agg_by_date.get(d["date"], 0) + d["amount"], 2)
            daily_m = sorted([{"date": k, "amount": v} for k, v in agg_by_date.items()], key=lambda x: x["date"])
            daily_m = _fill_week_daily(daily_m, period)
        # 主项目上期余额（所有子项目余额之和）
        balance_before_main = agg_balance_before
        balance_after_main = round(balance_before_main + agg["net"], 2) if boundary[0] else None
        result.append({
            "id": m["id"], "name": m["name"], "code": m["code"],
            "net": round(agg["net"], 2), "income": round(agg["income"], 2), "expense": round(agg["expense"], 2),
            "budget": m["budget"], "stop_loss": m["stop_loss"],
            "budget_usage": round(agg["expense"] / m["budget"] * 100, 1) if m["budget"] > 0 else 0,
            "stop_loss_diff": round(agg["net"] - m["stop_loss"], 2) if m["stop_loss"] else 0,
            "balance_before": balance_before_main if boundary[0] else None,
            "balance_after": balance_after_main if boundary[0] else None,
            "daily": daily_m,
            "sub_projects": children,
        })
    return result

@app.get("/api/stats")
def get_stats(period: str = "all", user: dict = Depends(get_current_user)):
    db = get_db()
    date_filter = _get_date_filter(period)
    fc = f" AND {date_filter}" if date_filter else ""
    
    glob = db.execute(
        f"SELECT COALESCE(SUM(amount),0) as net, COUNT(*) as cnt FROM transactions WHERE 1=1{fc}"
    ).fetchone()
    
    projects = _build_project_tree(db, period)
    
    db.close()
    return {
        "global": {"net": round(glob["net"], 2), "count": glob["cnt"]},
        "projects": projects,
    }

@app.get("/api/stats/summary")
def get_summary(user: dict = Depends(get_current_user)):
    """一次性返回四个周期+对比数据（用于总览页豆腐块）"""
    db = get_db()
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # 本周一
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    # 上周：上上周一到上周日
    last_week_start = monday - timedelta(days=7)
    last_week_end = monday - timedelta(days=1)
    # 本月
    month_start = today.replace(day=1)
    # 上月
    if month_start.month == 1:
        last_month_start = month_start.replace(year=month_start.year-1, month=12)
    else:
        last_month_start = month_start.replace(month=month_start.month-1)
    last_month_end = month_start - timedelta(days=1)
    # 本年
    year_start = today.replace(month=1, day=1)
    # 上年
    last_year_start = today.replace(year=today.year-1, month=1, day=1)
    last_year_end = today.replace(year=today.year-1, month=12, day=31)
    
    # 周数：本月第几周
    cal = calendar.monthcalendar(today.year, today.month)
    week_num = 0
    for i, wk in enumerate(cal):
        if today.day in wk:
            week_num = i + 1
            break
    
    def _query(date_where: str) -> dict:
        """执行单个条件查询，返回 {income, expense, net}"""
        row = db.execute(
            f"SELECT COALESCE(SUM(CASE WHEN amount>0 THEN amount ELSE 0 END),0) as income, COALESCE(SUM(CASE WHEN amount<0 THEN abs(amount) ELSE 0 END),0) as expense FROM transactions WHERE {date_where}"
        ).fetchone()
        inc = round(row["income"], 2)
        exp = round(row["expense"], 2)
        return {"income": inc, "expense": exp, "net": round(inc - exp, 2)}
    
    def _range(start_date: date, end_date: date) -> str:
        return f"date >= '{start_date.isoformat()}' AND date <= '{end_date.isoformat()}'"
    
    result = {
        "today":     {**_query(f"date = '{today.isoformat()}'"),     "label": f"{today.month}月{today.day}日"},
        "yesterday":  _query(f"date = '{yesterday.isoformat()}'"),
        "week":      {**_query(_range(monday, sunday)),   "label": f"{today.month}月第{week_num}周"},
        "last_week":  _query(_range(last_week_start, last_week_end)),
        "month":     {**_query(f"date >= '{month_start.isoformat()}'"), "label": f"{today.year}年{today.month}月"},
        "last_month": _query(_range(last_month_start, last_month_end)),
        "year":      {**_query(f"date >= '{year_start.isoformat()}'"), "label": f"{today.year}年"},
        "last_year":  _query(_range(last_year_start, last_year_end)),
    }
    db.close()
    return result

@app.get("/api/stats/dashboard")
def dashboard(period: str = "all", user: dict = Depends(get_current_user)):
    db = get_db()
    today = date.today()
    
    # 日期过滤条件
    date_filter = ""
    if period == "today":
        date_filter = f"= '{today.isoformat()}'"
    elif period == "week":
        monday = today - timedelta(days=today.weekday())
        date_filter = f">= '{monday.isoformat()}'"
    elif period == "month":
        start = today.replace(day=1).isoformat()
        date_filter = f">= '{start}'"
    elif period == "year":
        start = today.replace(month=1, day=1).isoformat()
        date_filter = f">= '{start}'"
    
    projects = db.execute("SELECT * FROM projects WHERE category!='other'").fetchall()
    alert_count = db.execute("SELECT COUNT(*) FROM alerts WHERE status='active'").fetchone()[0]
    
    total_net = 0
    total_income = 0
    total_expense = 0
    proj_list = []
    for p in projects:
        net = calc_project_net(db, p["id"], date_filter)
        exp = calc_project_expense(db, p["id"], date_filter)
        inc = db.execute(
            f"SELECT COALESCE(SUM(amount),0) FROM transactions WHERE project_id=? AND amount>0 {'AND date ' + date_filter if date_filter else ''}",
            (p["id"],)
        ).fetchone()[0]
        total_net += net
        total_income += inc
        total_expense += exp
        proj_list.append({
            "id": p["id"], "name": p["name"], "code": p["code"],
            "net": round(net, 2), "budget": p["budget"], "stop_loss": p["stop_loss"],
            "budget_usage": round(exp / p["budget"] * 100, 1) if p["budget"] > 0 else 0,
            "alert_count": db.execute("SELECT COUNT(*) FROM alerts WHERE project_id=? AND status='active'", (p["id"],)).fetchone()[0],
        })
    
    # 趋势图数据（按周期调整粒度）
    trend = []
    if period == "today":
        d = today.isoformat()
        row = db.execute("SELECT COALESCE(SUM(amount),0) as net FROM transactions WHERE date=?", (d,)).fetchone()
        trend.append({"date": "今日", "net": round(row["net"], 2)})
    elif period == "week":
        # 本周7天
        for i in range(6, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            row = db.execute("SELECT COALESCE(SUM(amount),0) as net FROM transactions WHERE date=?", (d,)).fetchone()
            trend.append({"date": d[5:], "net": round(row["net"], 2)})
    elif period == "month":
        # 本月按日
        days_in_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        for d in range(1, days_in_month.day + 1):
            ds = today.replace(day=d).isoformat()
            row = db.execute("SELECT COALESCE(SUM(amount),0) as net FROM transactions WHERE date=?", (ds,)).fetchone()
            trend.append({"date": str(d), "net": round(row["net"], 2)})
    elif period == "year":
        # 今年按月
        for m in range(1, 13):
            start_m = today.replace(month=m, day=1).isoformat()
            end_m = (today.replace(month=m, day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            end_str = end_m.isoformat()
            row = db.execute(
                "SELECT COALESCE(SUM(amount),0) as net FROM transactions WHERE date>=? AND date<=?",
                (start_m, end_str)
            ).fetchone()
            trend.append({"date": f"{m}月", "net": round(row["net"], 2)})
    else:
        # all: 近7日
        for i in range(6, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            row = db.execute("SELECT COALESCE(SUM(amount),0) as net FROM transactions WHERE date=?", (d,)).fetchone()
            trend.append({"date": d[5:], "net": round(row["net"], 2)})
    
    db.close()
    return {
        "project_count": len(projects),
        "alert_count": alert_count,
        "total_net": round(total_net, 2),
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "projects": proj_list,
        "trend": trend,
    }

@app.get("/api/dashboard/projects")
def dashboard_projects(user: dict = Depends(get_current_user)):
    """返回可选项目列表（用于走势图选择）"""
    db = get_db()
    rows = db.execute("SELECT id, name, code, parent_id FROM projects WHERE category!='other' ORDER BY parent_id IS NULL DESC, parent_id, id").fetchall()
    db.close()
    return {"projects": [{"id": r["id"], "name": r["name"], "code": r["code"], "parent_id": r["parent_id"]} for r in rows]}

@app.get("/api/dashboard/trend")
def dashboard_trend(project_ids: str = "", period: str = "day", user: dict = Depends(get_current_user)):
    """走势数据：每个项目独立一条线，父项目=子项目汇总
    period: year|month|week|day
    返回 {dates, labels, series: [{project_id, name, color, data}]}
    """
    db = get_db()
    
    ids = [int(x) for x in project_ids.split(",") if x.strip()]
    if not ids:
        db.close()
        return {"dates": [], "labels": [], "series": []}
    
    # 区分父项目和子项目
    placeholders = ",".join("?" for _ in ids)
    all_projects = db.execute(
        f"SELECT id, name, parent_id FROM projects WHERE id IN ({placeholders})", ids
    ).fetchall()
    
    project_names = {}
    parent_ids, child_ids = set(), set()
    for p in all_projects:
        project_names[p["id"]] = p["name"]
        if p["parent_id"] is None:
            parent_ids.add(p["id"])
        else:
            child_ids.add(p["id"])
    
    # 父项目→子项目映射
    parent_children = {}
    all_child_ids = set(child_ids)
    for pid in parent_ids:
        children = db.execute(
            "SELECT id FROM projects WHERE parent_id=?", (pid,)
        ).fetchall()
        parent_children[pid] = [r["id"] for r in children]
        all_child_ids.update(r["id"] for r in children)
    
    if not all_child_ids:
        db.close()
        return {"dates": [], "labels": [], "series": []}
    
    # 查询所有子项目交易（父项目自身无交易）
    cids = list(all_child_ids)
    placeholders = ",".join("?" for _ in cids)
    rows = db.execute(
        f"SELECT date, amount, project_id FROM transactions WHERE project_id IN ({placeholders}) ORDER BY date",
        cids
    ).fetchall()
    db.close()
    
    if not rows:
        return {"dates": [], "labels": [], "series": []}
    
    from collections import defaultdict
    buckets = defaultdict(lambda: defaultdict(float))
    
    for r in rows:
        d = r["date"]
        amt = r["amount"]
        pid = r["project_id"]
        
        if period == "year":       key = d[:4] + "-01-01"
        elif period == "month":    key = d[:7] + "-01"
        elif period == "week":
            dt = date.fromisoformat(d)
            key = (dt - timedelta(days=dt.weekday())).isoformat()
        else:                      key = d
        
        buckets[pid][key] += amt
    
    # 父项目 = 聚合所有子项目（选中时才聚合）
    for pid, cids_list in parent_children.items():
        if pid in ids:
            for child_id in cids_list:
                for k, v in buckets[child_id].items():
                    buckets[pid][k] += v
    
    # 收集所有时段key
    all_keys = set()
    for pid in ids:
        if pid in buckets:
            all_keys.update(buckets[pid].keys())
    
    sorted_keys = sorted(all_keys)
    
    # 生成labels
    labels = []
    for k in sorted_keys:
        if period == "year":       labels.append(k[:4] + "年")
        elif period == "month":    labels.append(k[:7].replace("-", "年") + "月")
        elif period == "week":
            dt = date.fromisoformat(k)
            labels.append(f"{dt.month}/{dt.day}周")
        else:
            parts = k.split("-")
            labels.append(f"{int(parts[1])}/{int(parts[2])}")
    
    # 调色板
    palette = ["#1989fa", "#07c160", "#ee0a24", "#ff976a", "#9b59b6", "#f39c12", "#1abc9c", "#e74c3c"]
    
    series = []
    for idx, pid in enumerate(ids):
        pd = buckets.get(pid, {})
        data = [round(pd.get(k, 0), 2) for k in sorted_keys]
        series.append({
            "project_id": pid,
            "name": project_names.get(pid, f"项目{pid}"),
            "color": palette[idx % len(palette)],
            "data": data,
        })
    
    return {"dates": sorted_keys, "labels": labels, "series": series}

@app.get("/api/export")
def export_excel(user: dict = Depends(get_current_user)):
    import csv, io
    db = get_db()
    rows = db.execute(
        "SELECT t.date, t.day_seq, t.amount, p.name as project, t.remark FROM transactions t LEFT JOIN projects p ON t.project_id=p.id ORDER BY t.date DESC"
    ).fetchall()
    db.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["日期", "日期序号", "金额", "项目", "备注"])
    for r in rows:
        writer.writerow([r["date"], r["day_seq"], r["amount"], r["project"] or "", r["remark"]])
    return {"csv": output.getvalue()}

# ═══════════ 静态文件 ═══════════
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")
    app.mount("/fund/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="fund_assets")

@app.get("/fund/{full_path:path}")
async def serve_fund_spa(full_path: str = ""):
    fp = os.path.join(FRONTEND_DIR, full_path)
    if os.path.isfile(fp):
        return FileResponse(fp)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{full_path:path}")
async def serve_spa(full_path: str = ""):
    fp = os.path.join(FRONTEND_DIR, full_path)
    if os.path.isfile(fp):
        return FileResponse(fp)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
