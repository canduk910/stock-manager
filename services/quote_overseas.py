"""해외주식 시세 관리.

FinnhubWSClient: Finnhub WebSocket 실시간 (30 심볼 한도)
KISOverseasOrderbookWS: KIS HDFSASP0 WebSocket 호가 실시간 (REQ-WS-01)
OverseasQuoteManager: KIS 우선 폴링 (REQ-INTEG-05) → 실패 시 yfinance fallback.
                      Finnhub WS 가용 시 WS 우선.
                      KIS 호가 WS 가용 시 호가도 WS 우선, 끊김 시 REST 폴링 자동 폴백.
"""
import asyncio
import json
import logging

import websockets
from collections import defaultdict

from config import FINNHUB_API_KEY
from services import _telemetry
from stock.kis_overseas_client import get_kis_price, get_kis_orderbook

logger = logging.getLogger(__name__)


# ── 폴링 메시지 빌더 (REQ-INTEG-05) ───────────────────────────────────────────


def _fetch_quote_message_yf(symbol: str) -> dict | None:
    """기존 yfinance 폴링 메시지 빌더 (fallback 경로)."""
    from stock.yf_client import _ticker
    try:
        fi = _ticker(symbol).fast_info
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
    except Exception as e:
        logger.debug("[OverseasQuote] yf 폴링 오류 %s: %s", symbol, e)
        return None


def _fetch_quote_message(symbol: str) -> dict | None:
    """KIS 우선 → yfinance fallback. WS 메시지 shape 보존.

    REQ-INTEG-05: 폴링 1회 호출용. KIS 정상 시 KIS 사용, 실패 시 yfinance.
    fallback 트리거 시 logger.warning + telemetry 카운터.
    """
    try:
        kis = get_kis_price(symbol)
    except Exception as e:
        # ConfigError(503) 등은 시스템 호출 컨텍스트에선 운영자 인지 필요하지만
        # 여기선 폴링 무중단을 위해 yfinance fallback. 단 한번만 warning.
        logger.warning("[OverseasQuote] KIS 호출 예외 → yfinance fallback (%s): %s", symbol, e)
        _telemetry.record_event("quote_overseas.fallback_to_yf")
        return _fetch_quote_message_yf(symbol)

    if kis:
        try:
            change = float(kis.get("change") or 0.0)
            rate = float(kis.get("change_rate") or 0.0)
            return {
                "type": "price",
                "symbol": symbol,
                "price": round(float(kis["last"]), 2),
                "change": round(change, 2),
                "change_rate": round(rate, 2),
                "sign": "2" if change >= 0 else "5",
            }
        except (TypeError, ValueError, KeyError) as e:
            logger.warning("[OverseasQuote] KIS 응답 매핑 실패 → yfinance fallback (%s): %s", symbol, e)
            _telemetry.record_event("quote_overseas.fallback_to_yf")
            return _fetch_quote_message_yf(symbol)

    # KIS None — fallback (warning 1회)
    logger.warning("[OverseasQuote] KIS None → yfinance fallback (%s)", symbol)
    _telemetry.record_event("quote_overseas.fallback_to_yf")
    return _fetch_quote_message_yf(symbol)


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


# ── KISOverseasOrderbookWS ────────────────────────────────────────────────────


class KISOverseasOrderbookWS:
    """KIS 해외 호가(HDFSASP0) WebSocket 클라이언트.

    REQ-WS-01.

    - 단일 WS 연결로 다수 종목 호가 토픽 다중화
    - 인증: ``routers/_kis_auth.get_approval_key`` 재사용 (운영자/사용자 키)
    - 토픽 키: ``f"D{exchange3}{symbol}"`` (실시간)
    - 메시지 파서: ``wrapper.parse_overseas_orderbook``
    - 재연결: 지수 백오프 1→2→4→8→16→30s 캡 (KIS rate limit 준수)
    - 콜백:
        - ``on_orderbook(payload: dict)`` 메시지 수신 시
        - ``on_disconnect()`` 연결 끊김 감지 시
        - ``on_reconnect()`` 재연결+토픽 재등록 완료 시
    - KIS 키 부재/토큰 발급 실패는 즉시 RuntimeError → OverseasQuoteManager가 REST 폴백
    """

    KIS_OVERSEAS_WS_URL = "ws://ops.koreainvestment.com:21000"

    def __init__(self, on_orderbook=None, on_disconnect=None, on_reconnect=None):
        self.on_orderbook = on_orderbook
        self.on_disconnect = on_disconnect
        self.on_reconnect = on_reconnect

        self._ws = None
        self._running = False
        self._task: asyncio.Task | None = None
        self._connected = False
        self._approval_key: str | None = None

        # 토픽 키 → 등록 상태 (재연결 시 재등록용)
        self._subscriptions: set[str] = set()

    # ── public ───────────────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def start(self):
        """WS 연결 + 메시지 루프 시작. KIS 키/토큰 미가용 시 즉시 RuntimeError."""
        if self._running:
            return
        # 사전 인증 확인 — 실패 시 OverseasQuoteManager가 REST 폴백 결정
        approval = self._issue_approval_key()
        if not approval:
            raise RuntimeError("KIS WS approval key 발급 실패 (KIS 키 부재 또는 인증 오류)")
        self._approval_key = approval

        self._running = True
        self._task = asyncio.create_task(self._connect_loop())
        _telemetry.record_event("quote_overseas.kis_orderbook_ws.start")

    async def stop(self):
        """WS 연결 해제 + 모든 구독 정리."""
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
            except (asyncio.CancelledError, Exception):
                pass
        self._task = None
        self._connected = False
        self._subscriptions.clear()
        _telemetry.record_event("quote_overseas.kis_orderbook_ws.stop")

    async def subscribe(self, rsym: str):
        """토픽 등록(예: ``DNASAAPL``).

        WS 연결 중이면 즉시 송신, 끊김 상태면 다음 재연결에 자동 재등록.
        """
        if rsym in self._subscriptions:
            return
        self._subscriptions.add(rsym)
        if self._connected and self._ws:
            try:
                await self._send_subscribe(rsym, register=True)
                _telemetry.record_event("quote_overseas.kis_orderbook_ws.topic_subscribe")
            except Exception as e:
                logger.warning("[KIS-OB-WS] subscribe %s 실패: %s", rsym, e)

    async def unsubscribe(self, rsym: str):
        if rsym not in self._subscriptions:
            return
        self._subscriptions.discard(rsym)
        if self._connected and self._ws:
            try:
                await self._send_subscribe(rsym, register=False)
                _telemetry.record_event("quote_overseas.kis_orderbook_ws.topic_unsubscribe")
            except Exception as e:
                logger.warning("[KIS-OB-WS] unsubscribe %s 실패: %s", rsym, e)

    # ── 인증 ─────────────────────────────────────────────────────────────────

    def _issue_approval_key(self) -> str | None:
        """KIS WS approval_key 발급. 실패 시 None.

        Approval key는 KIS REST `/oauth2/Approval` 엔드포인트에서 발급.
        OverseasQuoteManager 시스템 호출이므로 user_id=None(운영자 키).
        """
        try:
            from routers._kis_auth import get_kis_credentials
        except Exception as e:
            logger.warning("[KIS-OB-WS] _kis_auth import 실패: %s", e)
            return None
        try:
            app_key, app_secret, _, _, _ = get_kis_credentials(None)
        except Exception as e:
            logger.warning("[KIS-OB-WS] KIS 자격증명 조회 실패: %s", e)
            return None

        try:
            import requests as _req  # 표준 의존성
            url = "https://openapi.koreainvestment.com:9443/oauth2/Approval"
            body = {
                "grant_type": "client_credentials",
                "appkey": app_key,
                "secretkey": app_secret,
            }
            resp = _req.post(url, headers={"content-type": "application/json"},
                             data=json.dumps(body), timeout=10)
            if resp.status_code != 200:
                logger.warning("[KIS-OB-WS] approval 발급 실패 status=%s", resp.status_code)
                return None
            return resp.json().get("approval_key")
        except Exception as e:
            logger.warning("[KIS-OB-WS] approval 발급 예외: %s", e)
            return None

    # ── 연결 루프 ────────────────────────────────────────────────────────────

    async def _connect_loop(self):
        backoff = 1.0
        was_connected_once = False
        while self._running:
            try:
                await self._run_ws()
                # 정상 종료 — 다시 연결 시 백오프 초기화
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("[KIS-OB-WS] 오류: %s — %.0fs 후 재연결", e, backoff)
                _telemetry.record_event("quote_overseas.kis_orderbook_ws.reconnect_attempt")
            # 연결 끊김 알림 (한번이라도 연결된 적이 있으면)
            if was_connected_once and self._running:
                try:
                    if self.on_disconnect:
                        await self.on_disconnect()
                except Exception as e:
                    logger.debug("[KIS-OB-WS] on_disconnect 콜백 예외: %s", e)
                _telemetry.record_event("quote_overseas.kis_orderbook_ws.disconnect")
            was_connected_once = was_connected_once or self._connected
            self._connected = False
            if not self._running:
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)

    async def _run_ws(self):
        async with websockets.connect(
            self.KIS_OVERSEAS_WS_URL, ping_interval=None
        ) as ws:
            self._ws = ws
            self._connected = True
            _telemetry.record_event("quote_overseas.kis_orderbook_ws.connect")
            logger.info("[KIS-OB-WS] 연결됨 (재구독 %d 토픽)", len(self._subscriptions))

            # 모든 토픽 재등록
            for rsym in list(self._subscriptions):
                try:
                    await self._send_subscribe(rsym, register=True)
                except Exception as e:
                    logger.warning("[KIS-OB-WS] %s 재구독 실패: %s", rsym, e)
            # 재연결 콜백 (호출처가 REST 폴러를 정리)
            try:
                if self.on_reconnect:
                    await self.on_reconnect()
            except Exception as e:
                logger.debug("[KIS-OB-WS] on_reconnect 콜백 예외: %s", e)

            async for message in ws:
                if not self._running:
                    break
                await self._handle_message(message)
        self._ws = None
        self._connected = False

    async def _send_subscribe(self, rsym: str, register: bool):
        """KIS WS 구독/해지 프레임 송신."""
        if not self._ws or not self._approval_key:
            return
        fmt = {
            "header": {
                "approval_key": self._approval_key,
                "personalseckey": "1",
                "custtype": "P",
                "tr_type": "1" if register else "2",  # 1=등록, 2=해지
                "content-type": "utf-8",
            },
            "body": {
                "input": {
                    "tr_id": "HDFSASP0",
                    "tr_key": rsym,
                }
            }
        }
        await self._ws.send(json.dumps(fmt))

    async def _handle_message(self, data):
        """수신 메시지 처리 — 호가는 ``0|HDFSASP0|...|<payload>`` 또는 ``1|HDFSASP0|...``.

        제어 프레임(JSON)은 응답 코드만 검사. PINGPONG 자동 응답.
        """
        if not isinstance(data, str):
            return
        if not data:
            return
        first = data[0]
        if first in ("0", "1"):
            tokens = data.split("|")
            if len(tokens) < 4:
                return
            tr_id = tokens[1]
            if tr_id != "HDFSASP0":
                return
            payload = tokens[3]
            try:
                # wrapper.parse_overseas_orderbook 재사용
                from wrapper import parse_overseas_orderbook
                parsed = parse_overseas_orderbook(payload)
            except Exception as e:
                logger.debug("[KIS-OB-WS] parse 실패: %s", e)
                return
            if parsed and self.on_orderbook:
                try:
                    await self.on_orderbook(parsed)
                except Exception as e:
                    logger.debug("[KIS-OB-WS] on_orderbook 콜백 예외: %s", e)
        else:
            # 제어 프레임
            try:
                ctrl = json.loads(data)
                tr_id = ctrl.get("header", {}).get("tr_id")
                if tr_id == "PINGPONG":
                    if self._ws:
                        await self._ws.send(data)
            except Exception:
                return


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
        # REQ-WS-05: KIS 호가 폴러 (가격 채널과 분리)
        self._orderbook_pollers: dict[str, asyncio.Task] = {}
        self._latest: dict[str, dict] = {}
        self._prev_close: dict[str, float] = {}  # Finnhub change 계산용
        self._finnhub_syms: set[str] = set()     # Finnhub 처리 중인 심볼
        self._finnhub: FinnhubWSClient | None = None
        # REQ-WS-01: KIS 호가 WS
        self._kis_ob_ws = None  # KISOverseasOrderbookWS or None (사용 불가 시 None)
        self._kis_ob_symbols: dict[str, str] = {}  # symbol → exchange3 캐시
        self._running = False

    async def start(self):
        self._running = True
        if FINNHUB_API_KEY:
            self._finnhub = FinnhubWSClient(FINNHUB_API_KEY, self._on_finnhub_trade)
            await self._finnhub.start()
            logger.info("[OverseasQuote] Finnhub WS 활성화 (최대 %d 심볼)", FinnhubWSClient.MAX_SYMBOLS)
        else:
            logger.info("[OverseasQuote] FINNHUB_API_KEY 미설정 — yfinance 폴링 모드")

        # REQ-WS-01: KIS 호가 WS 기동 시도 (실패 시 graceful, REST 폴링 fallback)
        try:
            self._kis_ob_ws = KISOverseasOrderbookWS(
                on_orderbook=self._on_kis_orderbook_ws_message,
                on_disconnect=self._on_kis_ob_ws_disconnect,
                on_reconnect=self._on_kis_ob_ws_reconnect,
            )
            await self._kis_ob_ws.start()
            logger.info("[OverseasQuote] KIS 호가 WS 활성화")
        except Exception as e:
            self._kis_ob_ws = None
            logger.info("[OverseasQuote] KIS 호가 WS 비활성 (REST 폴링 사용): %s", e)

        logger.info("[OverseasQuote] 해외주식 시세 관리자 시작")

    async def stop(self):
        self._running = False
        if self._finnhub:
            await self._finnhub.stop()
        if self._kis_ob_ws:
            try:
                await self._kis_ob_ws.stop()
            except Exception:
                pass
            self._kis_ob_ws = None
        all_tasks = list(self._pollers.values()) + list(self._orderbook_pollers.values())
        for task in all_tasks:
            task.cancel()
        for task in all_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._pollers.clear()
        self._orderbook_pollers.clear()
        self._kis_ob_symbols.clear()
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
            # yfinance/KIS 가격 폴링 모드
            if symbol not in self._pollers or self._pollers[symbol].done():
                self._pollers[symbol] = asyncio.create_task(self._poll_loop(symbol))

        # REQ-WS-01: 호가 채널 — KIS WS 우선, 끊김/실패 시 REST 폴링
        # WS 사용 가능 + 연결됨 → 토픽 등록만 (REST 폴링 미시작)
        # WS 사용 불가/끊김 → REST 폴링 즉시 시작
        await self._subscribe_orderbook(symbol)

    async def _subscribe_orderbook(self, symbol: str) -> None:
        """호가 구독 진입점. WS 우선/REST 폴백 결정."""
        if self._kis_ob_ws is not None and self._kis_ob_ws.is_connected:
            # WS 토픽 등록 — REST 폴러는 미시작
            try:
                rsym = await self._build_kis_topic_async(symbol)
                if rsym:
                    await self._kis_ob_ws.subscribe(rsym)
                    return
                # 토픽 빌드 실패 시 REST 폴백
            except Exception as e:
                logger.debug("[OverseasQuote] KIS WS subscribe 실패 (%s): %s", symbol, e)
        # REST 폴백
        if symbol not in self._orderbook_pollers or self._orderbook_pollers[symbol].done():
            self._orderbook_pollers[symbol] = asyncio.create_task(
                self._orderbook_poll_loop(symbol)
            )

    def unsubscribe(self, symbol: str, queue: asyncio.Queue):
        self._subscribers[symbol].discard(queue)
        if not self._subscribers[symbol]:
            self._subscribers.pop(symbol, None)
            # Finnhub 구독 해제
            if symbol in self._finnhub_syms:
                self._finnhub_syms.discard(symbol)
                if self._finnhub:
                    asyncio.create_task(self._finnhub.unsubscribe(symbol))
            # 폴러 cancel (가격)
            task = self._pollers.pop(symbol, None)
            if task:
                task.cancel()
            # REQ-WS-05/01: 호가 폴러 cancel + KIS WS 토픽 해지
            ob_task = self._orderbook_pollers.pop(symbol, None)
            if ob_task:
                ob_task.cancel()
            if self._kis_ob_ws is not None:
                excd = self._kis_ob_symbols.pop(symbol, None)
                if excd:
                    rsym = f"D{excd}{symbol}"
                    asyncio.create_task(self._kis_ob_ws.unsubscribe(rsym))
            self._latest.pop(symbol, None)
            self._prev_close.pop(symbol, None)

    async def _prefetch_and_subscribe(self, symbol: str):
        """Finnhub 구독 전 KIS 우선(yfinance fallback) 으로 전일 종가 + 초기 시세 확보 후 WS 구독.

        REQ-INTEG-05: KIS 우선 → 실패 시 yfinance.
        """
        loop = asyncio.get_event_loop()
        try:
            msg = await loop.run_in_executor(None, _fetch_quote_message, symbol)
            if msg:
                # change 계산용 prev_close 추정 (price - change)
                try:
                    prev_val = float(msg["price"]) - float(msg.get("change") or 0.0)
                    if prev_val > 0:
                        self._prev_close[symbol] = prev_val
                except (TypeError, ValueError, KeyError):
                    pass
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
        """심볼별 KIS 우선 2초 폴링 태스크.

        REQ-INTEG-05: 폴링 1회마다 KIS 우선 → 실패 시 yfinance fallback.
        폴링 주기(2초) 변경 없음. WS 메시지 shape 보존.
        """
        loop = asyncio.get_event_loop()
        while self._running and symbol in self._subscribers:
            try:
                msg = await loop.run_in_executor(None, _fetch_quote_message, symbol)
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

    async def _orderbook_poll_loop(self, symbol: str):
        """KIS 10단계 호가 REST 폴링 (REQ-WS-05).

        2초 주기로 ``get_kis_orderbook`` 호출 → ``{type:"orderbook", ...}`` broadcast.
        실패(None) 시 메시지 미발행, 폴러 유지(다음 주기 재시도).
        """
        loop = asyncio.get_event_loop()
        while self._running and symbol in self._subscribers:
            try:
                ob = await loop.run_in_executor(None, get_kis_orderbook, symbol)
                if ob:
                    msg = {
                        "type": "orderbook",
                        "symbol": symbol,
                        "asks": ob.get("asks", []),
                        "bids": ob.get("bids", []),
                        "total_ask_volume": ob.get("total_ask_volume"),
                        "total_bid_volume": ob.get("total_bid_volume"),
                    }
                    await self._broadcast(symbol, msg)
                    _telemetry.record_event("quote_overseas.kis_orderbook.success")
                else:
                    _telemetry.record_event("quote_overseas.kis_orderbook.fail")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.debug("[OverseasQuote] %s 호가 폴링 오류: %s", symbol, e)
                _telemetry.record_event("quote_overseas.kis_orderbook.fail")
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

    # ── REQ-WS-01: KIS 호가 WS 통합 ──────────────────────────────────────────

    async def _build_kis_topic_async(self, symbol: str) -> str | None:
        """심볼 → KIS WS 토픽 키(``D{exchange3}{symbol}``).

        거래소 resolve는 동기 함수이므로 executor에서 실행.
        실패 시 None.
        """
        loop = asyncio.get_event_loop()
        try:
            from stock.kis_overseas_client import _resolve_exchange
            excd = await loop.run_in_executor(None, _resolve_exchange, symbol)
        except Exception as e:
            logger.debug("[OverseasQuote] %s 거래소 resolve 실패: %s", symbol, e)
            return None
        if not excd:
            return None
        self._kis_ob_symbols[symbol] = excd
        return f"D{excd}{symbol}"

    async def _on_kis_orderbook_ws_message(self, payload: dict) -> None:
        """KIS WS 호가 메시지 도달 → broadcast (shape 보존)."""
        symbol = payload.get("symbol")
        if not symbol or symbol not in self._subscribers:
            return
        msg = {
            "type": "orderbook",
            "symbol": symbol,
            "asks": payload.get("asks", []),
            "bids": payload.get("bids", []),
            "total_ask_volume": payload.get("total_ask_volume"),
            "total_bid_volume": payload.get("total_bid_volume"),
        }
        # WS 메시지 도달 시 해당 종목 REST 폴러 중단 (중복 방지)
        ob_task = self._orderbook_pollers.pop(symbol, None)
        if ob_task and not ob_task.done():
            ob_task.cancel()
        await self._broadcast(symbol, msg)
        _telemetry.record_event("quote_overseas.kis_orderbook_ws.message")

    async def _on_kis_ob_ws_disconnect(self) -> None:
        """KIS WS 끊김 → 모든 구독 종목에 REST 폴링 자동 시작."""
        logger.info("[OverseasQuote] KIS 호가 WS 끊김 — REST 폴링 fallback 시작")
        for symbol in list(self._subscribers.keys()):
            if symbol not in self._orderbook_pollers or self._orderbook_pollers[symbol].done():
                self._orderbook_pollers[symbol] = asyncio.create_task(
                    self._orderbook_poll_loop(symbol)
                )

    async def _on_kis_ob_ws_reconnect(self) -> None:
        """KIS WS 재연결 + 토픽 재등록 완료 → 모든 REST 호가 폴러 중단 (WS 우선).

        토픽 재등록은 KISOverseasOrderbookWS._run_ws에서 자동 처리.
        Manager는 모든 구독 종목에 대해 토픽 키만 새로 만들어 재등록 보장.
        """
        logger.info("[OverseasQuote] KIS 호가 WS 재연결 — REST 폴링 중단")
        for symbol in list(self._subscribers.keys()):
            # 토픽 재등록 (캐시된 거래소 사용 + 미캐시는 resolve)
            try:
                rsym = await self._build_kis_topic_async(symbol)
                if rsym and self._kis_ob_ws is not None:
                    await self._kis_ob_ws.subscribe(rsym)
            except Exception as e:
                logger.debug("[OverseasQuote] %s 재구독 실패: %s", symbol, e)
            # REST 폴러 cancel
            ob_task = self._orderbook_pollers.pop(symbol, None)
            if ob_task and not ob_task.done():
                ob_task.cancel()
