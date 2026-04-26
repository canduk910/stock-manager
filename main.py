import asyncio
import os
import threading
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# .env 파일 로드 (config.py 임포트 전에 호출해야 환경변수 반영)
load_dotenv()

from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD_STK, KIS_ACNT_PRDT_CD_FNO, FINNHUB_API_KEY

# SQLAlchemy ORM 초기화 (모든 모델 import → Base.metadata 등록)
import db.models  # noqa: F401, E402
from db.base import Base  # noqa: E402
from db.session import engine  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    _testing = os.environ.get("TESTING")

    if not _testing:
        # Alembic 마이그레이션 적용 (신규 설치 / 스키마 변경 시)
        try:
            from alembic.config import Config as AlembicConfig
            from alembic import command as alembic_command
            alembic_cfg = AlembicConfig(os.path.join(os.path.dirname(__file__), "alembic.ini"))
            alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "alembic"))
            alembic_command.upgrade(alembic_cfg, "head")
            print("[정보] DB 마이그레이션 완료 (alembic upgrade head)")
        except Exception as e:
            print(f"[경고] DB 마이그레이션 실패: {e}")

        missing = [name for name, val in (
            ("KIS_APP_KEY", KIS_APP_KEY),
            ("KIS_APP_SECRET", KIS_APP_SECRET),
            ("KIS_ACNT_NO", KIS_ACNT_NO),
            ("KIS_ACNT_PRDT_CD_STK", KIS_ACNT_PRDT_CD_STK),
        ) if not val]
        if missing:
            print(f"[경고] KIS 환경변수 누락: {', '.join(missing)} — 잔고/주문 비활성화")
        if not KIS_ACNT_PRDT_CD_FNO:
            print("[정보] KIS_ACNT_PRDT_CD_FNO 미설정 — 선물옵션 잔고 조회 비활성화")

        if not FINNHUB_API_KEY:
            print("[정보] FINNHUB_API_KEY 미설정 — 해외주식 시세 yfinance 폴링 모드 (15분 지연)")

        # 종목 심볼맵 pre-warm (Docker 재시작 후 캐시 초기화 → 첫 검색 지연 방지)
        def _prewarm_symbol_map():
            try:
                from stock.symbol_map import get_symbol_map
                get_symbol_map()
                print("[정보] 종목 심볼맵 로딩 완료")
            except Exception as e:
                print(f"[경고] 종목 심볼맵 로딩 실패: {e}")
            try:
                from stock.fno_master import get_fno_symbol_map
                fno_map = get_fno_symbol_map()
                print(f"[정보] FNO 마스터 로딩 완료 ({len(fno_map)}종목)")
            except Exception as e:
                print(f"[경고] FNO 마스터 로딩 실패: {e}")
        threading.Thread(target=_prewarm_symbol_map, daemon=True).start()

        # 실시간 호가 WebSocket 관리자 시작
        from services.quote_service import get_manager as get_quote_manager, get_overseas_manager
        quote_manager = get_quote_manager()
        await quote_manager.start()

        # 해외주식 시세 폴링 관리자 시작
        overseas_manager = get_overseas_manager()
        await overseas_manager.start()

        # 예약주문 스케줄러 백그라운드 시작
        from services.reservation_service import start_scheduler, stop_scheduler
        scheduler_task = asyncio.create_task(start_scheduler())

        # 투자 파이프라인 스케줄러 시작 (08:00 KR / 16:00 US)
        from services.scheduler_service import setup_scheduler as setup_pipeline_scheduler, shutdown_scheduler as shutdown_pipeline_scheduler
        setup_pipeline_scheduler()

    yield

    if not _testing:
        shutdown_pipeline_scheduler()
        stop_scheduler()
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        await overseas_manager.stop()
        await quote_manager.stop()


app = FastAPI(title="Stock Manager API", lifespan=lifespan)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# ServiceError → HTTP 응답 변환 (서비스 레이어에서 HTTPException 직접 사용 제거)
from services.exceptions import ServiceError  # noqa: E402

@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

# CORS: 프론트엔드 개발 서버 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
from routers import auth, screener, earnings, balance, watchlist, detail, order, quote, advisory, search, market_board, macro, portfolio_advisor, report, pipeline, backtest, tax  # noqa: E402

app.include_router(auth.router)
app.include_router(screener.router)
app.include_router(earnings.router)
app.include_router(balance.router)
app.include_router(watchlist.router)
app.include_router(detail.router)
app.include_router(order.router)
app.include_router(quote.router)
app.include_router(advisory.router)
app.include_router(search.router)
app.include_router(market_board.router)
app.include_router(macro.router)
app.include_router(portfolio_advisor.router)
app.include_router(report.router)
app.include_router(pipeline.router)
app.include_router(backtest.router)
app.include_router(tax.router)


# 프론트엔드 빌드 결과 정적 파일 서빙 (API 라우터 등록 이후에 마운트)
_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    # JS/CSS 등 정적 에셋
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")

    # SPA 캐치올: API에 매칭되지 않는 모든 경로에 index.html 반환
    # (React Router가 클라이언트 사이드에서 라우팅 처리)
    # index.html은 캐싱 금지 — 배포 후 브라우저가 항상 최신 번들을 로드하도록 함
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        response = FileResponse(os.path.join(_frontend_dist, "index.html"))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
