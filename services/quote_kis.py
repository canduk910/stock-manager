"""KIS WebSocket 단일 연결 관리 + 심볼별 asyncio.Queue 브로드캐스트.

국내(KR): H0STCNT0 체결가 + H0STASP0 호가 실시간 수신
         WS 끊김 시 KIS REST FHKST01010100 3초 폴링 자동 전환
선물옵션(FNO): H0IFASP0/H0IFCNT0(지수) H0IOASP0/H0IOCNT0(지수옵션)
              H0ZFASP0/H0ZFCNT0(주식선물) H0ZOASP0/H0ZOCNT0(주식옵션)
              동일 WS 연결, 5레벨(지수) 또는 10레벨(주식) 호가
체결통보(H0STCNI0): KIS_HTS_ID 설정 시 AES-CBC 복호화
"""
import asyncio
import json
import logging
import time

import requests
import websockets
from collections import defaultdict

from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_BASE_URL, KIS_HTS_ID
from routers._kis_auth import get_access_token_safe, clear_token_cache

KIS_WS_URL = "ws://ops.koreainvestment.com:21000"

logger = logging.getLogger(__name__)

# ── FNO WS TR_ID 상수 ──────────────────────────────────────────────────────────

_FNO_TR_IDS: dict[str, dict] = {
    "IF": {"orderbook": "H0IFASP0", "execution": "H0IFCNT0", "levels": 5},   # 지수선물
    "IO": {"orderbook": "H0IOASP0", "execution": "H0IOCNT0", "levels": 5},   # 지수옵션
    "ZF": {"orderbook": "H0ZFASP0", "execution": "H0ZFCNT0", "levels": 10},  # 주식선물
    "ZO": {"orderbook": "H0ZOASP0", "execution": "H0ZOCNT0", "levels": 10},  # 주식옵션
}
_FNO_EXECUTION_TR_IDS: set[str] = {"H0IFCNT0", "H0IOCNT0", "H0ZFCNT0", "H0ZOCNT0"}
_FNO_ORDERBOOK_TR_IDS: set[str] = {"H0IFASP0", "H0IOASP0", "H0ZFASP0", "H0ZOASP0"}
_FNO_5LEVEL_TR_IDS:   set[str] = {"H0IFASP0", "H0IOASP0"}


def _resolve_fno_type(symbol: str) -> str:
    """FNO 심볼 → 상품 유형 코드 ('IF'|'IO'|'ZF'|'ZO')."""
    if not symbol:
        return "IF"
    ch = symbol[0]
    if ch == "1":
        return "IF"
    if ch == "2":
        return "IO"
    if ch == "3":
        # 주식선물 vs 주식옵션 구분: fno_master의 product_type 활용
        try:
            from stock.fno_master import validate_fno_symbol
            info = validate_fno_symbol(symbol)
            if info and "옵션" in info.get("product_type", ""):
                return "ZO"
        except Exception:
            # FNO 마스터 미로드 시 기본 선물(ZF)로 fallback
            pass
        return "ZF"
    return "IF"


# ── KISQuoteManager ────────────────────────────────────────────────────────────

class KISQuoteManager:
    def __init__(self):
        self._approval_key: str | None = None
        self._approval_key_at: float = 0
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._subscribed_symbols: set[str] = set()
        self._ws = None
        self._task: asyncio.Task | None = None
        self._running = False
        # REST fallback
        self._fallback_mode: bool = False
        self._fallback_task: asyncio.Task | None = None
        # FNO 구독 관리
        self._fno_symbols: set[str] = set()
        self._fno_types: dict[str, str] = {}  # symbol → 'IF'|'IO'|'ZF'|'ZO'
        # 체결통보
        self._aes_key: str | None = None
        self._aes_iv: str | None = None
        self._notice_subscribers: set[asyncio.Queue] = set()

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

    async def subscribe(self, symbol: str, queue: asyncio.Queue, is_fno: bool = False):
        self._subscribers[symbol].add(queue)
        if is_fno:
            self._fno_symbols.add(symbol)
        if symbol not in self._subscribed_symbols and self._ws:
            try:
                if symbol in self._fno_symbols:
                    await self._send_subscribe_fno(symbol)
                else:
                    await self._send_subscribe(symbol)
            except Exception as e:
                logger.warning("[QuoteService] 구독 요청 실패: %s — %s", symbol, e)
        # 즉시 초기 가격 push (비개장일 포함)
        if symbol in self._fno_symbols:
            asyncio.create_task(self._push_initial_price_fno(symbol, queue))
        else:
            asyncio.create_task(self._push_initial_price(symbol, queue))

    def unsubscribe(self, symbol: str, queue: asyncio.Queue):
        self._subscribers[symbol].discard(queue)
        if not self._subscribers[symbol]:
            self._subscribers.pop(symbol, None)
            self._subscribed_symbols.discard(symbol)
            self._fno_symbols.discard(symbol)
            self._fno_types.pop(symbol, None)

    async def subscribe_notice(self, queue: asyncio.Queue):
        """체결통보(H0STCNI0) 구독."""
        self._notice_subscribers.add(queue)

    def unsubscribe_notice(self, queue: asyncio.Queue):
        self._notice_subscribers.discard(queue)

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

    async def _push_initial_price_fno(self, symbol: str, queue: asyncio.Queue):
        """FNO 구독 즉시 REST FHMIF10000000으로 초기 시세 push."""
        try:
            loop = asyncio.get_event_loop()
            msg = await loop.run_in_executor(None, self._fetch_fno_rest_price_sync, symbol)
            if msg:
                try:
                    queue.put_nowait(msg)
                except asyncio.QueueFull:
                    pass
        except Exception as e:
            logger.debug("[QuoteService] FNO 초기 가격 push 실패: %s — %s", symbol, e)

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

    async def _send_subscribe_fno(self, symbol: str):
        fno_type = _resolve_fno_type(symbol)
        self._fno_types[symbol] = fno_type
        tr_info = _FNO_TR_IDS[fno_type]
        approval_key = self._get_approval_key()
        for tr_id in [tr_info["execution"], tr_info["orderbook"]]:
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
        logger.debug("[QuoteService] FNO 구독 등록: %s (%s)", symbol, fno_type)

    async def _send_subscribe_notice(self):
        """H0STCNI0 체결통보 구독 등록."""
        if not KIS_HTS_ID:
            return
        approval_key = self._get_approval_key()
        msg = {
            "header": {
                "approval_key": approval_key,
                "personalseckey": "1",
                "custtype": "P",
                "tr_type": "1",
                "content-type": "utf-8",
            },
            "body": {"input": {"tr_id": "H0STCNI0", "tr_key": KIS_HTS_ID}},
        }
        await self._ws.send(json.dumps(msg))
        logger.info("[QuoteService] 체결통보(H0STCNI0) 구독 등록")

    _APPROVAL_KEY_TTL = 12 * 3600  # 12시간

    def _get_approval_key(self) -> str:
        if self._approval_key and (time.time() - self._approval_key_at) < self._APPROVAL_KEY_TTL:
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
        self._approval_key_at = time.time()
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
                self._approval_key_at = 0
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
                if symbol in self._fno_symbols:
                    await self._send_subscribe_fno(symbol)
                else:
                    await self._send_subscribe(symbol)
            # 체결통보 구독
            await self._send_subscribe_notice()
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
            elif tr_id in _FNO_EXECUTION_TR_IDS:
                parsed = self._parse_fno_execution(tokens[3])
                if parsed:
                    await self._broadcast(parsed["symbol"], {"type": "price", **parsed})
            elif tr_id in _FNO_ORDERBOOK_TR_IDS:
                levels = 5 if tr_id in _FNO_5LEVEL_TR_IDS else 10
                parsed = self._parse_fno_orderbook(tokens[3], levels)
                if parsed:
                    await self._broadcast(parsed["symbol"], {"type": "orderbook", **parsed})
            elif tr_id == "H0STCNI0":
                parsed = self._parse_notice(tokens[3])
                if parsed:
                    await self._broadcast_notice(parsed)
        else:
            try:
                ctrl = json.loads(data)
            except json.JSONDecodeError:
                return
            tr_id = ctrl.get("header", {}).get("tr_id")
            # AES key/iv 캡처 (체결통보 복호화용)
            if tr_id in ("H0STCNI0", "H0STCNI9", "H0STASP0"):
                output = ctrl.get("body", {}).get("output", {})
                aes_key = output.get("key")
                aes_iv = output.get("iv")
                if aes_key and aes_iv:
                    self._aes_key = aes_key
                    self._aes_iv = aes_iv
                    logger.debug("[QuoteService] AES key/iv 수신 (tr_id=%s)", tr_id)
            if tr_id == "PINGPONG":
                await self._ws.send(data)

    _drop_count: dict[str, int] = {}

    async def _broadcast(self, symbol: str, message: dict):
        for q in list(self._subscribers.get(symbol, set())):
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                cnt = self._drop_count[symbol] = self._drop_count.get(symbol, 0) + 1
                if cnt % 100 == 1:
                    logger.warning("[QuoteManager] %s: %d messages dropped (queue full)", symbol, cnt)
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass

    async def _broadcast_all(self, message: dict):
        for symbol in list(self._subscribers.keys()):
            await self._broadcast(symbol, message)

    # ── REST Fallback ──────────────────────────────────────────────

    async def _rest_fallback_loop(self):
        """WS 끊김 시 KIS REST 3초 폴링 (price only). FNO는 FHMIF10000000, 국내는 FHKST01010100."""
        logger.info("[QuoteService] REST fallback 폴링 시작")
        while self._fallback_mode and self._running:
            symbols = list(self._subscribers.keys())
            for symbol in symbols:
                if not self._fallback_mode or not self._running:
                    break
                try:
                    if symbol in self._fno_symbols:
                        loop = asyncio.get_event_loop()
                        msg = await loop.run_in_executor(None, self._fetch_fno_rest_price_sync, symbol)
                    else:
                        msg = await self._fetch_rest_price(symbol)
                    if msg:
                        await self._broadcast(symbol, msg)
                except Exception as e:
                    logger.debug("[QuoteService] REST fallback %s: %s", symbol, e)
                await asyncio.sleep(0.1)  # 심볼 간 0.1초 (KIS 초당 10건)
            await asyncio.sleep(3)  # 폴링 주기 3초
        logger.info("[QuoteService] REST fallback 폴링 종료")

    async def _fetch_rest_price(self, symbol: str) -> dict | None:
        if not KIS_APP_KEY or not KIS_APP_SECRET:
            return None

        loop = asyncio.get_event_loop()

        def _sync():
            token = get_access_token_safe()
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
                clear_token_cache()
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

    @staticmethod
    def _sf(v) -> float:
        try:
            return float(v)
        except Exception:
            return 0.0

    def _parse_execution(self, raw: str) -> dict | None:
        t = raw.split('^')
        if len(t) < 6:
            return None
        sf = self._sf
        result = {
            "symbol": t[0],
            "price": sf(t[2]),
            "sign": t[3],
            "change": sf(t[4]),
            "change_rate": sf(t[5]),
        }
        # H0STCNT0: t[7]=시가, t[8]=고가, t[9]=저가
        if len(t) > 9:
            result["open"] = sf(t[7])
            result["high"] = sf(t[8])
            result["low"] = sf(t[9])
        return result

    def _parse_orderbook(self, raw: str) -> dict | None:
        t = raw.split('^')
        if len(t) < 45:
            return None
        sf = self._sf
        asks = [{"price": sf(t[3 + i]), "volume": sf(t[23 + i])} for i in range(10)]
        bids = [{"price": sf(t[13 + i]), "volume": sf(t[33 + i])} for i in range(10)]
        return {
            "symbol": t[0],
            "asks": asks,
            "bids": bids,
            "total_ask_volume": sf(t[43]),
            "total_bid_volume": sf(t[44]),
        }

    def _parse_fno_execution(self, raw: str) -> dict | None:
        """FNO 체결 파싱. H0IFCNT0/H0IOCNT0/H0ZFCNT0/H0ZOCNT0 공통.
        [0]=종목코드, [2]=전일대비, [3]=부호, [4]=대비율, [5]=현재가
        """
        t = raw.split('^')
        if len(t) < 6:
            return None
        sf = self._sf
        return {
            "symbol": t[0],
            "price": sf(t[5]),
            "sign": t[3],
            "change": sf(t[2]),
            "change_rate": sf(t[4]),
        }

    def _parse_fno_orderbook(self, raw: str, levels: int) -> dict | None:
        """FNO 호가 파싱.
        5레벨(H0IFASP0/H0IOASP0):
          [0]=종목코드, [2-6]=매도호가1-5, [7-11]=매수호가1-5,
          [22-26]=매도잔량1-5, [27-31]=매수잔량1-5, [34]=총매도잔량, [35]=총매수잔량
        10레벨(H0ZFASP0/H0ZOASP0):
          5레벨 확장 구조 (실데이터 확인 후 오프셋 조정 필요)
        """
        t = raw.split('^')
        sf = self._sf
        if levels == 5:
            if len(t) < 36:
                return None
            asks = [{"price": sf(t[2 + i]), "volume": sf(t[22 + i])} for i in range(5)]
            bids = [{"price": sf(t[7 + i]), "volume": sf(t[27 + i])} for i in range(5)]
            return {
                "symbol": t[0],
                "asks": asks,
                "bids": bids,
                "total_ask_volume": sf(t[34]),
                "total_bid_volume": sf(t[35]),
            }
        else:
            # 10레벨: H0ZFASP0/H0ZOASP0 — 오프셋은 5레벨과 유사한 패턴으로 추정
            # [0]=종목, [2-11]=매도호가1-10, [12-21]=매수호가1-10,
            # [32-41]=매도잔량1-10, [42-51]=매수잔량1-10, [54]=총매도, [55]=총매수
            if len(t) < 56:
                logger.debug("[QuoteService] FNO 10레벨 호가 필드 부족: %d", len(t))
                return None
            asks = [{"price": sf(t[2 + i]),  "volume": sf(t[32 + i])} for i in range(10)]
            bids = [{"price": sf(t[12 + i]), "volume": sf(t[42 + i])} for i in range(10)]
            return {
                "symbol": t[0],
                "asks": asks,
                "bids": bids,
                "total_ask_volume": sf(t[54]),
                "total_bid_volume": sf(t[55]),
            }

    def _parse_notice(self, encrypted_data: str) -> dict | None:
        """H0STCNI0 체결통보 AES 복호화 + 파싱."""
        if not self._aes_key or not self._aes_iv:
            logger.warning("[QuoteService] AES key/iv 없음 — 체결통보 복호화 불가")
            return None
        try:
            from Crypto.Cipher import AES as AES_Cipher
            from Crypto.Util.Padding import unpad
            from base64 import b64decode
            cipher = AES_Cipher.new(
                self._aes_key.encode('utf-8'),
                AES_Cipher.MODE_CBC,
                self._aes_iv.encode('utf-8'),
            )
            dec = unpad(cipher.decrypt(b64decode(encrypted_data)), AES_Cipher.block_size).decode('utf-8')
            tokens = dec.split('^')
            if len(tokens) < 22:
                logger.warning("[QuoteService] 체결통보 필드 부족: %d개", len(tokens))
                return None
            return {
                "type": "execution_notice",
                "order_no": tokens[2],
                "org_order_no": tokens[3],
                "symbol": tokens[8],
                "side": "buy" if tokens[4] == "02" else "sell",
                "filled_qty": tokens[9],
                "filled_price": tokens[10],
                "filled_time": tokens[11],
                "is_rejected": tokens[12],
                "is_filled": tokens[13],
                "is_accepted": tokens[14],
                "order_qty": tokens[16],
                "symbol_name": tokens[21],
                "order_price": tokens[22] if len(tokens) > 22 else "",
            }
        except ImportError:
            logger.error("[QuoteService] pycryptodome 미설치 — pip install pycryptodome")
            return None
        except Exception as e:
            logger.error("[QuoteService] 체결통보 복호화 실패: %s", e)
            return None

    async def _broadcast_notice(self, message: dict):
        """체결통보를 모든 notice 구독자에게 전송."""
        for q in list(self._notice_subscribers):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    q.put_nowait(message)
                except asyncio.QueueFull:
                    pass
        if message.get("is_filled") == "2":
            logger.info(
                "[QuoteService] 체결통보: %s %s %s주 @ %s",
                message.get("symbol_name", ""),
                message.get("side", ""),
                message.get("filled_qty", ""),
                message.get("filled_price", ""),
            )

    def _fetch_fno_rest_price_sync(self, symbol: str) -> dict | None:
        """FNO 현재가 REST 조회 (동기). FHMIF10000000 사용."""
        if not KIS_APP_KEY or not KIS_APP_SECRET:
            return None
        try:
            token = get_access_token_safe()
            if not token:
                return None
            fno_type = self._fno_types.get(symbol)
            if not fno_type:
                fno_type = _resolve_fno_type(symbol)
                self._fno_types[symbol] = fno_type
            tr_info = _FNO_TR_IDS.get(fno_type, _FNO_TR_IDS["IF"])
            # mrkt_div: IF/IO → F/O, ZF/ZO → JF
            mrkt_div_map = {"IF": "F", "IO": "O", "ZF": "JF", "ZO": "JF"}
            mrkt_div = mrkt_div_map.get(fno_type, "F")
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": KIS_APP_KEY,
                "appsecret": KIS_APP_SECRET,
                "tr_id": "FHMIF10000000",
                "custtype": "P",
            }
            params = {
                "FID_COND_MRKT_DIV_CODE": mrkt_div,
                "FID_INPUT_ISCD": symbol,
            }
            resp = requests.get(
                f"{KIS_BASE_URL}/uapi/domestic-futureoption/v1/quotations/inquire-price",
                headers=headers,
                params=params,
                timeout=5,
            )
            if resp.status_code == 401:
                clear_token_cache()
                return None
            output = resp.json().get("output", {})
            price = float(output.get("last", 0) or output.get("stck_prpr", 0) or 0)
            if price <= 0:
                return None
            prev = float(output.get("base", 0) or 0)
            change = price - prev if prev else 0.0
            change_rate = (change / prev * 100) if prev else 0.0
            sign = "2" if change > 0 else ("5" if change < 0 else "3")
            return {
                "type": "price",
                "symbol": symbol,
                "price": price,
                "sign": sign,
                "change": change,
                "change_rate": change_rate,
            }
        except Exception as e:
            logger.debug("[QuoteService] FNO REST 가격 조회 실패 %s: %s", symbol, e)
            return None
