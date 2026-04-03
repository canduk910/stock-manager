"""해외주식 시세 관리.

FinnhubWSClient: Finnhub WebSocket 실시간 (30 심볼 한도)
OverseasQuoteManager: Finnhub WS 또는 yfinance 2초 폴링
"""
import asyncio
import json
import logging

import websockets
from collections import defaultdict

from config import FINNHUB_API_KEY

logger = logging.getLogger(__name__)


# ── FinnhubWSClient ────────────────────────────────────────────────────────────

class FinnhubWSClient:
    """Finnhub WebSocket 클라이언트. 무료 플랜 30 심볼 한도."""

    FINNHUB_WS_URL = "wss://ws.finnhub.io"
    MAX_SYMBOLS = 30

    def __init__(self, api_key: str, on_trade):
        self._api_key = api_key
        self._on_trade = on_trade
        self._ws = None
        self._running = False
        self._subscribed: set[str] = set()
        self._task: asyncio.Task | None = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._connect_loop())

    async def stop(self):
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def can_subscribe(self) -> bool:
        return len(self._subscribed) < self.MAX_SYMBOLS

    async def subscribe(self, symbol: str):
        self._subscribed.add(symbol)
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
            except Exception:
                pass

    async def unsubscribe(self, symbol: str):
        self._subscribed.discard(symbol)
        if self._ws:
            try:
                await self._ws.send(json.dumps({"type": "unsubscribe", "symbol": symbol}))
            except Exception:
                pass

    async def _connect_loop(self):
        backoff = 1.0
        while self._running:
            try:
                await self._run_ws()
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("[FinnhubWS] 오류: %s — %.0f초 후 재연결", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    async def _run_ws(self):
        url = f"{self.FINNHUB_WS_URL}?token={self._api_key}"
        async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
            self._ws = ws
            logger.info("[FinnhubWS] 연결됨 (%d 심볼 재구독)", len(self._subscribed))
            for sym in list(self._subscribed):
                await ws.send(json.dumps({"type": "subscribe", "symbol": sym}))
            async for message in ws:
                if not self._running:
                    break
                await self._handle_message(message)
        self._ws = None

    async def _handle_message(self, data: str):
        try:
            msg = json.loads(data)
        except json.JSONDecodeError:
            return
        if msg.get("type") == "trade" and msg.get("data"):
            # 배열에서 마지막(최신) 체결만 사용
            latest = msg["data"][-1]
            symbol = latest.get("s")
            price = latest.get("p")
            if symbol and price:
                await self._on_trade(symbol, float(price))


# ── OverseasQuoteManager ──────────────────────────────────────────────────────

class OverseasQuoteManager:
    """해외주식 시세 폴링 공유 매니저.

    FINNHUB_API_KEY 있음: Finnhub WS 실시간 (30 심볼) + yfinance 폴링 fallback
    FINNHUB_API_KEY 없음: yfinance 2초 폴링 (기존 방식)
    구독자 0이면 폴러/WS 구독 자동 해제.
    """

    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._pollers: dict[str, asyncio.Task] = {}
        self._latest: dict[str, dict] = {}
        self._prev_close: dict[str, float] = {}  # Finnhub change 계산용
        self._finnhub_syms: set[str] = set()     # Finnhub 처리 중인 심볼
        self._finnhub: FinnhubWSClient | None = None
        self._running = False

    async def start(self):
        self._running = True
        if FINNHUB_API_KEY:
            self._finnhub = FinnhubWSClient(FINNHUB_API_KEY, self._on_finnhub_trade)
            await self._finnhub.start()
            logger.info("[OverseasQuote] Finnhub WS 활성화 (최대 %d 심볼)", FinnhubWSClient.MAX_SYMBOLS)
        else:
            logger.info("[OverseasQuote] FINNHUB_API_KEY 미설정 — yfinance 폴링 모드")
        logger.info("[OverseasQuote] 해외주식 시세 관리자 시작")

    async def stop(self):
        self._running = False
        if self._finnhub:
            await self._finnhub.stop()
        for task in self._pollers.values():
            task.cancel()
        for task in self._pollers.values():
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._pollers.clear()
        logger.info("[OverseasQuote] 해외주식 시세 관리자 종료")

    async def subscribe(self, symbol: str, queue: asyncio.Queue):
        self._subscribers[symbol].add(queue)
        # 최신 시세가 있으면 즉시 전송
        if symbol in self._latest:
            try:
                queue.put_nowait(self._latest[symbol])
            except asyncio.QueueFull:
                pass

        # Finnhub 모드: 한도 이내면 WS 구독
        if self._finnhub and self._finnhub.can_subscribe() and symbol not in self._finnhub_syms:
            self._finnhub_syms.add(symbol)
            # 전일 종가 pre-fetch (change 계산용) + 즉시 시세 브로드캐스트
            asyncio.create_task(self._prefetch_and_subscribe(symbol))
        else:
            # yfinance 폴링 모드
            if symbol not in self._pollers or self._pollers[symbol].done():
                self._pollers[symbol] = asyncio.create_task(self._poll_loop(symbol))

    def unsubscribe(self, symbol: str, queue: asyncio.Queue):
        self._subscribers[symbol].discard(queue)
        if not self._subscribers[symbol]:
            self._subscribers.pop(symbol, None)
            # Finnhub 구독 해제
            if symbol in self._finnhub_syms:
                self._finnhub_syms.discard(symbol)
                if self._finnhub:
                    asyncio.create_task(self._finnhub.unsubscribe(symbol))
            # 폴러 cancel
            task = self._pollers.pop(symbol, None)
            if task:
                task.cancel()
            self._latest.pop(symbol, None)
            self._prev_close.pop(symbol, None)

    async def _prefetch_and_subscribe(self, symbol: str):
        """Finnhub 구독 전 yfinance로 전일 종가 + 초기 시세 확보 후 WS 구독."""
        from stock.yf_client import _ticker
        loop = asyncio.get_event_loop()
        try:
            def _fetch():
                fi = _ticker(symbol).fast_info
                # 비개장일에 last_price가 None인 경우 previous_close로 fallback
                last = fi.last_price or fi.previous_close
                return fi.previous_close, last

            prev, last = await loop.run_in_executor(None, _fetch)
            if prev:
                self._prev_close[symbol] = float(prev)
            # 초기 시세 즉시 broadcast (prev 없어도 last만 있으면 broadcast)
            if last:
                prev_val = float(prev) if prev else float(last)
                ch = float(last) - prev_val if prev else 0.0
                rt = ch / prev_val * 100 if prev else 0.0
                msg = {
                    "type": "price",
                    "symbol": symbol,
                    "price": round(float(last), 2),
                    "change": round(ch, 2),
                    "change_rate": round(rt, 2),
                    "sign": "2" if ch >= 0 else "5",
                }
                self._latest[symbol] = msg
                await self._broadcast(symbol, msg)
        except Exception as e:
            logger.debug("[OverseasQuote] 초기 시세 prefetch 실패 %s: %s", symbol, e)
        # Finnhub WS 구독 (초기 시세와 무관하게 등록)
        if self._finnhub and symbol in self._finnhub_syms:
            await self._finnhub.subscribe(symbol)

    async def _on_finnhub_trade(self, symbol: str, price: float):
        """Finnhub 체결 콜백."""
        if symbol not in self._subscribers:
            return
        prev = self._prev_close.get(symbol, 0.0)
        ch = price - prev if prev else 0.0
        rt = ch / prev * 100 if prev else 0.0
        msg = {
            "type": "price",
            "symbol": symbol,
            "price": round(price, 2),
            "change": round(ch, 2),
            "change_rate": round(rt, 2),
            "sign": "2" if ch >= 0 else "5",
        }
        self._latest[symbol] = msg
        await self._broadcast(symbol, msg)

    async def _poll_loop(self, symbol: str):
        """심볼별 yfinance 2초 폴링 태스크 (Finnhub 미설정 또는 한도 초과 심볼)."""
        from stock.yf_client import _ticker
        loop = asyncio.get_event_loop()
        while self._running and symbol in self._subscribers:
            try:
                def _fetch():
                    fi = _ticker(symbol).fast_info
                    # 비개장일에 last_price가 None인 경우 previous_close로 fallback
                    p = fi.last_price or fi.previous_close
                    if not p:
                        return None
                    prev = fi.previous_close or p
                    ch = (p - prev) if prev else 0.0
                    rt = (ch / prev * 100) if prev else 0.0
                    return {
                        "type": "price",
                        "symbol": symbol,
                        "price": round(float(p), 2),
                        "change": round(float(ch), 2),
                        "change_rate": round(float(rt), 2),
                        "sign": "2" if ch >= 0 else "5",
                    }

                msg = await loop.run_in_executor(None, _fetch)
                if msg is None:
                    await asyncio.sleep(2)
                    continue
                self._latest[symbol] = msg
                await self._broadcast(symbol, msg)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.debug("[OverseasQuote] %s 폴링 오류: %s", symbol, e)
            await asyncio.sleep(2)

    async def _broadcast(self, symbol: str, message: dict):
        for q in list(self._subscribers.get(symbol, set())):
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass
