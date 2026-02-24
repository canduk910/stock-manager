import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = [name for name, val in (
        ("KIS_APP_KEY", os.getenv("KIS_APP_KEY")),
        ("KIS_APP_SECRET", os.getenv("KIS_APP_SECRET")),
        ("KIS_ACNT_NO", os.getenv("KIS_ACNT_NO")),
        ("KIS_ACNT_PRDT_CD", os.getenv("KIS_ACNT_PRDT_CD")),
    ) if not val]
    if missing:
        print(f"[경고] KIS 환경변수 누락: {', '.join(missing)} — 잔고 조회 비활성화")
    yield


app = FastAPI(title="Stock Manager API", lifespan=lifespan)

# CORS: 프론트엔드 개발 서버 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
from routers import screener, earnings, balance, watchlist, detail  # noqa: E402

app.include_router(screener.router)
app.include_router(earnings.router)
app.include_router(balance.router)
app.include_router(watchlist.router)
app.include_router(detail.router)


# 프론트엔드 빌드 결과 정적 파일 서빙 (API 라우터 등록 이후에 마운트)
_frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend_dist):
    # JS/CSS 등 정적 에셋
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")

    # SPA 캐치올: API에 매칭되지 않는 모든 경로에 index.html 반환
    # (React Router가 클라이언트 사이드에서 라우팅 처리)
    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse(os.path.join(_frontend_dist, "index.html"))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
