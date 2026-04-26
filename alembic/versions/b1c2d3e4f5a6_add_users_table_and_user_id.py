"""Add users table and user_id to per-user tables.

Revision ID: b1c2d3e4f5a6
Revises: f3a8b1c7d9e2
Create Date: 2026-04-25

PostgreSQL + SQLite 양쪽 호환.
- PostgreSQL: ALTER TABLE로 PK 직접 변경
- SQLite: render_as_batch=True 활용 (batch_alter_table)
"""

from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "f3a8b1c7d9e2"
branch_labels = None
depends_on = None


def _is_sqlite():
    return op.get_bind().dialect.name == "sqlite"


def _find_pk_name(table_name):
    """PostgreSQL에서 실제 PK 제약조건 이름을 런타임 조회."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT constraint_name FROM information_schema.table_constraints "
        "WHERE table_name = :t AND constraint_type = 'PRIMARY KEY'"
    ), {"t": table_name})
    row = result.fetchone()
    return row[0] if row else f"{table_name}_pkey"


def _find_unique_name(table_name, col_name):
    """PostgreSQL에서 특정 컬럼의 UNIQUE 제약조건 이름을 런타임 조회."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT tc.constraint_name "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.constraint_column_usage ccu "
        "  ON tc.constraint_name = ccu.constraint_name "
        "  AND tc.table_schema = ccu.table_schema "
        "WHERE tc.table_name = :t AND tc.constraint_type = 'UNIQUE' "
        "  AND ccu.column_name = :c"
    ), {"t": table_name, "c": col_name})
    row = result.fetchone()
    return row[0] if row else f"{table_name}_{col_name}_key"


def upgrade() -> None:
    # 1. users 테이블 생성
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String, unique=True, nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("hashed_password", sa.String, nullable=False),
        sa.Column("role", sa.String, nullable=False, server_default="user"),
        sa.Column("created_at", sa.String, nullable=False, server_default=""),
        sa.Column("updated_at", sa.String, nullable=False, server_default=""),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # 2. 복합 PK 테이블 — user_id 추가 + PK 변경
    _add_user_id_composite_pk("watchlist")
    _add_user_id_composite_pk("watchlist_order")
    _add_user_id_composite_pk("market_board_stocks")
    _add_user_id_composite_pk("market_board_order")
    _add_user_id_composite_pk("advisory_stocks")
    _add_user_id_composite_pk("advisory_cache")

    # 3. Auto-increment PK 테이블 — ADD COLUMN user_id
    with op.batch_alter_table("advisory_reports") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer, nullable=False, server_default="1"))

    with op.batch_alter_table("backtest_jobs") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer, nullable=False, server_default="1"))

    # 4. strategies: user_id 추가 + unique(name) → unique(user_id, name)
    _upgrade_strategies()


def _add_user_id_composite_pk(table_name):
    """복합 PK 테이블에 user_id 추가. SQLite/PostgreSQL 양쪽 호환."""
    if _is_sqlite():
        # SQLite: batch_alter_table로 처리 (render_as_batch=True)
        # batch mode에서 PK 변경 불가 → 수동 재생성
        _sqlite_recreate_with_user_id(table_name)
    else:
        # PostgreSQL: ALTER TABLE 직접 사용
        pk_name = _find_pk_name(table_name)
        # 1) user_id 컬럼 추가 (기존 행 = 1)
        op.add_column(table_name, sa.Column("user_id", sa.Integer, nullable=False, server_default="1"))
        # 2) 기존 PK 제거 (런타임 조회된 이름 사용)
        op.drop_constraint(pk_name, table_name, type_="primary")
        # 3) 새 PK 추가 (user_id 포함)
        op.create_primary_key(f"{table_name}_pkey", table_name, ["user_id", "code", "market"])
        # 4) server_default 제거 (이미 적용됨)
        op.alter_column(table_name, "user_id", server_default=None)


def _sqlite_recreate_with_user_id(table_name):
    """SQLite 전용: 테이블 재생성으로 PK 변경."""
    # 테이블 컬럼 정보를 런타임에 조회
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table_name})"))
    existing_cols = [row[1] for row in result]  # column names

    tmp = f"_tmp_{table_name}"
    cols_str = ", ".join(existing_cols)

    # 새 테이블 생성 (user_id 포함)
    col_defs = f"user_id INTEGER NOT NULL, {', '.join(f'{c} {_get_col_type(table_name, c)}' for c in existing_cols)}"
    pk_def = "PRIMARY KEY (user_id, code, market)"

    op.execute(sa.text(f"CREATE TABLE {tmp} ({col_defs}, {pk_def})"))
    op.execute(sa.text(f"INSERT INTO {tmp} (user_id, {cols_str}) SELECT 1, {cols_str} FROM {table_name}"))
    op.drop_table(table_name)
    op.rename_table(tmp, table_name)


def _get_col_type(table_name, col_name):
    """SQLite PRAGMA에서 컬럼 타입을 추론."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table_name})"))
    for row in result:
        if row[1] == col_name:
            return row[2] or "TEXT"
    return "TEXT"


def _upgrade_strategies():
    """strategies: user_id 추가 + unique(name) → unique(user_id, name)."""
    if _is_sqlite():
        # SQLite: 전체 재생성
        tmp = "_tmp_strategies"
        op.execute(sa.text(
            f"CREATE TABLE {tmp} ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL DEFAULT 1, "
            "name VARCHAR NOT NULL, "
            "description TEXT, "
            "strategy_type VARCHAR NOT NULL, "
            "yaml_content TEXT, "
            "builder_state_json JSON, "
            "created_at VARCHAR NOT NULL, "
            "UNIQUE(user_id, name))"
        ))
        op.execute(sa.text(
            f"INSERT INTO {tmp} (id, user_id, name, description, strategy_type, yaml_content, builder_state_json, created_at) "
            "SELECT id, 1, name, description, strategy_type, yaml_content, builder_state_json, created_at FROM strategies"
        ))
        op.drop_table("strategies")
        op.rename_table(tmp, "strategies")
    else:
        # PostgreSQL
        uq_name = _find_unique_name("strategies", "name")
        op.add_column("strategies", sa.Column("user_id", sa.Integer, nullable=False, server_default="1"))
        # unique(name) 제거 (런타임 조회된 이름 사용) → unique(user_id, name) 추가
        op.drop_constraint(uq_name, "strategies", type_="unique")
        op.create_unique_constraint("uq_strategy_user_name", "strategies", ["user_id", "name"])
        op.alter_column("strategies", "user_id", server_default=None)


def downgrade() -> None:
    if _is_sqlite():
        _downgrade_sqlite()
    else:
        _downgrade_postgres()


def _downgrade_postgres():
    # strategies
    uq_name = _find_unique_name("strategies", "name")  # uq_strategy_user_name
    op.drop_constraint(uq_name, "strategies", type_="unique")
    op.create_unique_constraint("strategies_name_key", "strategies", ["name"])
    op.drop_column("strategies", "user_id")

    # auto-increment tables
    op.drop_column("backtest_jobs", "user_id")
    op.drop_column("advisory_reports", "user_id")

    # composite PK tables
    for table in ["advisory_cache", "advisory_stocks", "market_board_order",
                   "market_board_stocks", "watchlist_order", "watchlist"]:
        pk_name = _find_pk_name(table)
        op.drop_constraint(pk_name, table, type_="primary")
        op.create_primary_key(f"{table}_pkey", table, ["code", "market"])
        op.drop_column(table, "user_id")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")


def _downgrade_sqlite():
    # strategies: restore unique(name)
    tmp = "_tmp_strategies"
    op.execute(sa.text(
        f"CREATE TABLE {tmp} ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "name VARCHAR UNIQUE NOT NULL, "
        "description TEXT, "
        "strategy_type VARCHAR NOT NULL, "
        "yaml_content TEXT, "
        "builder_state_json JSON, "
        "created_at VARCHAR NOT NULL)"
    ))
    op.execute(sa.text(
        f"INSERT INTO {tmp} (id, name, description, strategy_type, yaml_content, builder_state_json, created_at) "
        "SELECT id, name, description, strategy_type, yaml_content, builder_state_json, created_at FROM strategies"
    ))
    op.drop_table("strategies")
    op.rename_table(tmp, "strategies")

    with op.batch_alter_table("backtest_jobs") as batch_op:
        batch_op.drop_column("user_id")

    with op.batch_alter_table("advisory_reports") as batch_op:
        batch_op.drop_column("user_id")

    # 복합 PK 테이블 되돌리기
    for table in ["advisory_cache", "advisory_stocks", "market_board_order",
                   "market_board_stocks", "watchlist_order", "watchlist"]:
        conn = op.get_bind()
        result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
        all_cols = [row[1] for row in result]
        cols_no_uid = [c for c in all_cols if c != "user_id"]
        cols_str = ", ".join(cols_no_uid)

        tmp = f"_tmp_{table}"
        # type info 기반 CREATE TABLE은 복잡하므로 CTAS 사용
        op.execute(sa.text(f"CREATE TABLE {tmp} AS SELECT {cols_str} FROM {table}"))
        op.drop_table(table)
        op.rename_table(tmp, table)

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
