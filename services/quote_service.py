"""
KIS WebSocket 단일 연결 관리 + 심볼별 asyncio.Queue 브로드캐스트.
해외주식 yfinance 폴링 공유 (OverseasQuoteManager + Finnhub WS).
FastAPI lifespan에서 start() / stop() 호출.
국내(KR): H0STCNT0 체결가 + H0STASP0 호가 실시간 수신
         WS 끊김 시 KIS REST FHKST01010100 5초 폴링 자동 전환
해외(US): Finnhub WS (FINNHUB_API_KEY 설정 시) 또는 yfinance 2초 폴링
"""
import asyncio
import json
import logging

import requests  # approval_key / REST fallback (동기)
import websockets
from collections import defaultdict

from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_BASE_URL, FINNHUB_API_KEY

KIS_WS_URL = "ws://ops.koreainvestment.com:21000"

logger = logging.getLogger(__name__)


# ── KIS REST 토큰 캐시 (quote_service 전용, HTTPException 없이 동작) ──────────

_rest_token: str | None = None


def _get_rest_token_sync() -> str | None:
    """KIS REST 액세스 토큰 발급 (동기). 실패 시 None 반환."""
    global _rest_token
    if _rest_token:
        return _rest_token
    if not KIS_APP_KEY or not KIS_APP_SECRET:
        return None
    try:
        res = requests.post(
            f"{KIS_BASE_URL}/oauth2/tokenP",
            headers={"content-type": "application/json"},
            json={"grant_type": "client_credentials", "appkey": KIS_APP_KEY, "appsecret": KIS_APP_SECRET},
            timeout=10,
        )
        _rest_token = res.json()["access_token"]
        return _rest_token
    except Exception as e:
        logger.error("[QuoteService] REST 토큰 발급 실패: %s", e)
        return None


def _clear_rest_token():
    global _rest_token
    _rest_token = None


# ── KISQuoteManager ────────────────────────────────────────────────────────────

class KISQuoteManager:
    def __init__(self):
        self._approval_key: str | None = None
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._subscribed_symbols: set[str] = set()
        self._ws = None
        self._task: asyncio.Task | None = None
        self._running = False
        # REST fallback
        self._fallback_mode: bool = False
        self._fallback_task: asyncio.Task | None = None

    # ── lifecycle ──────────────────────────────────────────────────

    async def start(self):
        if not (KIS_APP_KEY and KIS_APP_SECRET):
            logger.warning("[QuoteService] KIS 키 미설정 — 실시간 호가 비활성화")
            return
        self._running = True
        self._task = asyncio.create_task(self._connect_loop())
        logger.info("[QuoteService] KIS WebSocket 관리자 시작")

    async def stop(self):
        self._running = False
        self._fallback_mode = False
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
        if self._fallback_task:
            self._fallback_task.cancel()
            try:
                await self._fallback_task
            except asyncio.CancelledError:
                pass
        logger.info("[QuoteService] KIS WebSocket 관리자 종료")

    # ── pub/sub ────────────────────────────────────────────────────

    async def subscribe(self, symbol: str, queue: asyncio.Queue):
        self._subscribers[symbol].add(queue)
        if symbol not in self._subscribed_symbols and self._ws:
            try:
                await self._send_subscribe(symbol)
            except Exception as e:
                logger.warning("[QuoteService] 구독 요청 실패: %s — %s", symbol, e)
        # 즉시 초기 가격 push (비개장일 포함)
        asyncio.create_task(self._push_initial_price(symbol, queue))

    def unsubscribe(self, symbol: str, queue: asyncio.Queue):
        self._subscribers[symbol].discard(queue)
        if not self._subscribers[symbol]:
            self._subscribers.pop(symbol, None)
            self._subscribed_symbols.discard(symbol)

    # ── 초기 가격 push ─────────────────────────────────────────────

    async def _push_initial_price(self, symbol: str, queue: asyncio.Queue):
        """구독 즉시 yfinance 최근 가격 push (비개장일 대응)."""
        try:
            loop = asyncio.get_event_loop()
            from stock.market import fetch_price
            data = await loop.run_in_executor(None, fetch_price, symbol)
            if data and data.get("price"):
                msg = {
                    "type": "price",
                    "symbol": symbol,
                    "price": data["price"],
                    "sign": "3",
                    "change": 0.0,
                    "change_rate": data.get("change_pct") or 0.0,
                }
                try:
                    queue.put_nowait(msg)
                except asyncio.QueueFull:
                    pass
        except Exception as e:
            logger.debug("[QuoteService] 초기 가격 push 실패: %s — %s", symbol, e)

    # ── 내부 메서드 ────────────────────────────────────────────────

    async def _send_subscribe(self, symbol: str):
        approval_key = self._get_approval_key()
        for tr_id in ["H0STCNT0", "H0STASP0"]:
            msg = {
                "header": {
                    "approval_key": approval_key,
                    "personalseckey": "1",
                    "custtype": "P",
                    "tr_type": "1",
                    "content-type": "utf-8",
                },
                "body": {"input": {"tr_id": tr_id, "tr_key": symbol}},
            }
            await self._ws.send(json.dumps(msg))
        self._subscribed_symbols.add(symbol)
        logger.debug("[QuoteService] 구독 등록: %s", symbol)

    def _get_approval_key(self) -> str:
        if self._approval_key:
            return self._approval_key
        res = requests.post(
            f"{KIS_BASE_URL}/oauth2/Approval",
            headers={"content-type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "appkey": KIS_APP_KEY,
                "secretkey": KIS_APP_SECRET,
            },
            timeout=10,
        )
        self._approval_key = res.json()["approval_key"]
        return self._approval_key

    async def _connect_loop(self):
        backoff = 1.0
        while self._running:
            try:
                await self._run_ws()
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("[QuoteService] WS 오류: %s — %.0f초 후 재연결", e, backoff)
                self._approval_key = None
                await self._broadcast_all({"type": "disconnected"})
                # WS 끊김 시 REST fallback 시작
                if not self._fallback_mode:
                    self._fallback_mode = True
                    self._fallback_task = asyncio.create_task(self._rest_fallback_loop())
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    async def _run_ws(self):
        # WS 재연결 성공 → fallback 해제
        self._fallback_mode = False
        self._subscribed_symbols.clear()
        async with websockets.connect(KIS_WS_URL, ping_interval=None) as ws:
            self._ws = ws
            logger.info("[QuoteService] KIS WebSocket 연결됨")
            for symbol in list(self._subscribers.keys()):
                await self._send_subscribe(symbol)
            async for message in ws:
                if not self._running:
                    break
                await self._handle_message(message)
        self._ws = None

    async def _handle_message(self, data: str):
        if not data:
            return
        if data[0] in ('0', '1'):
            tokens = data.split('|')
            if len(tokens) < 4:
                return
            tr_id = tokens[1]
            if tr_id == "H0STCNT0":
                parsed = self._parse_execution(tokens[3])
                if parsed:
                    await self._broadcast(parsed["symbol"], {"type": "price", **parsed})
            elif tr_id == "H0STASP0":
                parsed = self._parse_orderbook(tokens[3])
                if parsed:
                    await self._broadcast(parsed["symbol"], {"type": "orderbook", **parsed})
        else:
            try:
                ctrl = json.loads(data)
            except json.JSONDecodeError:
                return
            tr_id = ctrl.get("header", {}).get("tr_id")
            if tr_id == "PINGPONG":
                await self._ws.send(data)

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

    async def _broadcast_all(self, message: dict):
        for symbol in list(self._subscribers.keys()):
            await self._broadcast(symbol, message)

    # ── REST Fallback ──────────────────────────────────────────────

    async def _rest_fallback_loop(self):
        """WS 끊김 시 KIS REST FHKST01010100 5초 폴링 (price only)."""
        logger.info("[QuoteService] REST fallback 폴링 시작")
        while self._fallback_mode and self._running:
            symbols = list(self._subscribers.keys())
            for symbol in symbols:
                if not self._fallback_mode or not self._running:
                    break
                try:
                    msg = await self._fetch_rest_price(symbol)
                    if msg:
                        await self._broadcast(symbol, msg)
                except Exception as e:
                    logger.debug("[QuoteService] REST fallback %s: %s", symbol, e)
                # 심볼 간 0.2초 간격 (KIS API 호출 제한 분산)
                await asyncio.sleep(0.2)
            await asyncio.sleep(5)
        logger.info("[QuoteService] REST fallback 폴링 종료")

    async def _fetch_rest_price(self, symbol: str) -> dict | None:
        if not KIS_APP_KEY or not KIS_APP_SECRET:
            return None

        loop = asyncio.get_event_loop()

        def _sync():
            token = _get_rest_token_sync()
            if not token:
                return None
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": KIS_APP_KEY,
                "appsecret": KIS_APP_SECRET,
                "tr_id": "FHKST01010100",
                "custtype": "P",
            }
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": symbol,
            }
            resp = requests.get(
                f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
                headers=headers,
                params=params,
                timeout=5,
            )
            if resp.status_code == 401:
                _clear_rest_token()
                return None
            output = resp.json().get("output", {})
            price = float(output.get("stck_prpr", 0) or 0)
            if price <= 0:
                # 비개장일: yfinance fallback으로 직전 거래일 가격 반환
                try:
                    from stock.market import fetch_price
                    data = fetch_price(symbol)
                    if data and data.get("price"):
                        return {
                            "type": "price",
                            "symbol": symbol,
                            "price": data["price"],
                            "sign": "3",
                            "change": 0.0,
                            "change_rate": data.get("change_pct") or 0.0,
                        }
                except Exception:
                    pass
                return None
            return {
                "type": "price",
                "symbol": symbol,
                "price": price,
                "sign": output.get("prdy_vrss_sign", "3"),
                "change": float(output.get("prdy_vrss", 0) or 0),
                "change_rate": float(output.get("prdy_ctrt", 0) or 0),
            }

        return await loop.run_in_executor(None, _sync)

    def _parse_execution(self, raw: str) -> dict | None:
        t = raw.split('^')
        if len(t) < 6:
            return None

        def sf(v):
            try:
                return float(v)
            except Exception:
                return 0.0

        return {
            "symbol": t[0],
            "price": sf(t[2]),
            "sign": t[3],
            "change": sf(t[4]),
            "change_rate": sf(t[5]),
        }

    def _parse_orderbook(self, raw: str) -> dict | None:
        t = raw.split('^')
        if len(t) < 45:
            return None

        def sf(v):
            try:
                return float(v)
            except Exception:
                return 0.0

        asks = [{"price": sf(t[3 + i]), "volume": sf(t[23 + i])} for i in range(10)]
        bids = [{"price": sf(t[13 + i]), "volume": sf(t[33 + i])} for i in range(10)]

        return {
            "symbol": t[0],
            "asks": asks,
            "bids": bids,
            "total_ask_volume": sf(t[43]),
            "total_bid_volume": sf(t[44]),
        }


# ── FinnhubWSClient ────────────────────────────────────────────────────────────

class FinnhubWSClient:
    """Finnhub WebSocket 클라이언트. 무료 플랜 30 심볼 한도."""

    FINNHUB_WS_URL = "wss://ws.finnhub.io"
    MAX_SYMBOLS = 30

    def __init__(self, api_key: str, on_trade):
        self._api_key = api_key
        self._on_trade = on_trade  # async callable(symbol: str, price: float)
        self._ws = None
        self._task: asyncio.Task | None = None
        self._running = False
        self._subscribed: set[str] = set()

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


# ── 싱글턴 ────────────────────────────────────────────────────────────────────

_manager: KISQuoteManager | None = None
_overseas_manager: OverseasQuoteManager | None = None


def get_manager() -> KISQuoteManager:
    global _manager
    if _manager is None:
        _manager = KISQuoteManager()
    return _manager


def get_overseas_manager() -> OverseasQuoteManager:
    global _overseas_manager
    if _overseas_manager is None:
        _overseas_manager = OverseasQuoteManager()
    return _overseas_manager
