"""
KIS WebSocket 단일 연결 관리 + 심볼별 asyncio.Queue 브로드캐스트.
FastAPI lifespan에서 start() / stop() 호출.
국내(KR): H0STCNT0 체결가 + H0STASP0 호가 실시간 수신
"""
import asyncio
import json
import logging
import os

import requests  # approval_key 발급 (동기 REST)
import websockets
from collections import defaultdict

KIS_WS_URL = "ws://ops.koreainvestment.com:21000"

logger = logging.getLogger(__name__)


class KISQuoteManager:
    def __init__(self):
        self._approval_key: str | None = None
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._subscribed_symbols: set[str] = set()
        self._ws = None
        self._task: asyncio.Task | None = None
        self._running = False

    # ── lifecycle ──────────────────────────────────────────────────

    async def start(self):
        if not (os.getenv("KIS_APP_KEY") and os.getenv("KIS_APP_SECRET")):
            logger.warning("[QuoteService] KIS 키 미설정 — 실시간 호가 비활성화")
            return
        self._running = True
        self._task = asyncio.create_task(self._connect_loop())
        logger.info("[QuoteService] KIS WebSocket 관리자 시작")

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
        logger.info("[QuoteService] KIS WebSocket 관리자 종료")

    # ── pub/sub ────────────────────────────────────────────────────

    async def subscribe(self, symbol: str, queue: asyncio.Queue):
        self._subscribers[symbol].add(queue)
        if symbol not in self._subscribed_symbols and self._ws:
            try:
                await self._send_subscribe(symbol)
            except Exception as e:
                logger.warning("[QuoteService] 구독 요청 실패: %s — %s", symbol, e)

    def unsubscribe(self, symbol: str, queue: asyncio.Queue):
        self._subscribers[symbol].discard(queue)
        if not self._subscribers[symbol]:
            self._subscribers.pop(symbol, None)
            self._subscribed_symbols.discard(symbol)

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
            f"{os.getenv('KIS_BASE_URL', 'https://openapi.koreainvestment.com:9443')}/oauth2/Approval",
            headers={"content-type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "appkey": os.getenv("KIS_APP_KEY"),
                "secretkey": os.getenv("KIS_APP_SECRET"),
            },
            timeout=10,
        )
        self._approval_key = res.json()["approval_key"]
        return self._approval_key

    async def _connect_loop(self):
        while self._running:
            try:
                await self._run_ws()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("[QuoteService] WS 오류: %s — 5초 후 재연결", e)
                self._approval_key = None
                self._subscribed_symbols.clear()
                await asyncio.sleep(5)

    async def _run_ws(self):
        async with websockets.connect(KIS_WS_URL, ping_interval=None) as ws:
            self._ws = ws
            logger.info("[QuoteService] KIS WebSocket 연결됨")
            # 기존 구독 심볼 재등록
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
        # 실시간 데이터: '0|tr_id|count|payload'
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
            # JSON 제어 메시지 (PINGPONG 등)
            try:
                ctrl = json.loads(data)
            except json.JSONDecodeError:
                return
            tr_id = ctrl.get("header", {}).get("tr_id")
            if tr_id == "PINGPONG":
                await self._ws.send(data)

    async def _broadcast(self, symbol: str, message: dict):
        for q in list(self._subscribers.get(symbol, set())):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass  # 느린 클라이언트 drop

    def _parse_execution(self, raw: str) -> dict | None:
        """
        H0STCNT0 페이로드 파싱.
        [0]=종목코드, [2]=현재가, [3]=전일대비부호, [4]=전일대비, [5]=전일대비율
        """
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
        """
        H0STASP0 페이로드 파싱 (plaintext, AES 복호화 불필요).
        [0]=종목코드
        [3~12]=매도호가01~10 (최우선=index3, 최열위=index12)
        [13~22]=매수호가01~10 (최우선=index13, 최열위=index22)
        [23~32]=매도호가잔량01~10
        [33~42]=매수호가잔량01~10
        [43]=총매도잔량, [44]=총매수잔량
        """
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


# 싱글턴
_manager: KISQuoteManager | None = None


def get_manager() -> KISQuoteManager:
    global _manager
    if _manager is None:
        _manager = KISQuoteManager()
    return _manager
