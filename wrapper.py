#-------------------------------------------------#
# 한국투자증권 python wrapper                     #
#-------------------------------------------------#

import json
import pickle
import asyncio
from base64 import b64decode
from multiprocessing import Process, Queue
import datetime
import requests
import zipfile
import os
import pandas as pd
import websockets
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

EXCHANGE_CODE = {
    "홍콩": "HKS",
    "뉴욕": "NYS",
    "나스닥": "NAS",
    "아멕스": "AMS",
    "도쿄": "TSE",
    "상해": "SHS",
    "심천": "SZS",
    "상해지수": "SHI",
    "심천지수": "SZI",
    "호치민": "HSX",
    "하노이": "HNX"
}

# 해외주식 주문
# 해외주식 잔고
EXCHANGE_CODE2 = {
    "미국전체": "NASD",
    "나스닥": "NAS",
    "뉴욕": "NYSE",
    "아멕스": "AMEX",
    "홍콩": "SEHK",
    "상해": "SHAA",
    "심천": "SZAA",
    "도쿄": "TKSE",
    "하노이": "HASE",
    "호치민": "VNSE"
}

EXCHANGE_CODE3 = {
    "나스닥": "NASD",
    "뉴욕": "NYSE",
    "아멕스": "AMEX",
    "홍콩": "SEHK",
    "상해": "SHAA",
    "심천": "SZAA",
    "도쿄": "TKSE",
    "하노이": "HASE",
    "호치민": "VNSE"
}

EXCHANGE_CODE4 = {
    "나스닥": "NAS",
    "뉴욕": "NYS",
    "아멕스": "AMS",
    "홍콩": "HKS",
    "상해": "SHS",
    "심천": "SZS",
    "도쿄": "TSE",
    "하노이": "HNX",
    "호치민": "HSX",
    "상해지수": "SHI",
    "심천지수": "SZI"
}

CURRENCY_CODE = {
    "나스닥": "USD",
    "뉴욕": "USD",
    "아멕스": "USD",
    "홍콩": "HKD",
    "상해": "CNY",
    "심천": "CNY",
    "도쿄": "JPY",
    "하노이": "VND",
    "호치민": "VND"
}

execution_items = [
    "유가증권단축종목코드", "주식체결시간", "주식현재가", "전일대비부호", "전일대비",
    "전일대비율", "가중평균주식가격", "주식시가", "주식최고가", "주식최저가",
    "매도호가1", "매수호가1", "체결거래량", "누적거래량", "누적거래대금",
    "매도체결건수", "매수체결건수", "순매수체결건수", "체결강도", "총매도수량",
    "총매수수량", "체결구분", "매수비율", "전일거래량대비등락율", "시가시간",
    "시가대비구분", "시가대비", "최고가시간", "고가대비구분", "고가대비",
    "최저가시간", "저가대비구분", "저가대비", "영업일자", "신장운영구분코드",
    "거래정지여부", "매도호가잔량", "매수호가잔량", "총매도호가잔량", "총매수호가잔량",
    "거래량회전율", "전일동시간누적거래량", "전일동시간누적거래량비율", "시간구분코드",
    "임의종료구분코드", "정적VI발동기준가"
]

orderbook_items = [
    "유가증권 단축 종목코드",
    "영업시간",
    "시간구분코드",
    "매도호가01",
    "매도호가02",
    "매도호가03",
    "매도호가04",
    "매도호가05",
    "매도호가06",
    "매도호가07",
    "매도호가08",
    "매도호가09",
    "매도호가10",
    "매수호가01",
    "매수호가02",
    "매수호가03",
    "매수호가04",
    "매수호가05",
    "매수호가06",
    "매수호가07",
    "매수호가08",
    "매수호가09",
    "매수호가10",
    "매도호가잔량01",
    "매도호가잔량02",
    "매도호가잔량03",
    "매도호가잔량04",
    "매도호가잔량05",
    "매도호가잔량06",
    "매도호가잔량07",
    "매도호가잔량08",
    "매도호가잔량09",
    "매도호가잔량10",
    "매수호가잔량01",
    "매수호가잔량02",
    "매수호가잔량03",
    "매수호가잔량04",
    "매수호가잔량05",
    "매수호가잔량06",
    "매수호가잔량07",
    "매수호가잔량08",
    "매수호가잔량09",
    "매수호가잔량10",
    "총매도호가 잔량", # 43
    "총매수호가 잔량",
    "시간외 총매도호가 잔량",
    "시간외 총매수호가 증감",
    "예상 체결가",
    "예상 체결량",
    "예상 거래량",
    "예상체결 대비",
    "부호",
    "예상체결 전일대비율",
    "누적거래량",
    "총매도호가 잔량 증감",
    "총매수호가 잔량 증감",
    "시간외 총매도호가 잔량",
    "시간외 총매수호가 증감",
    "주식매매 구분코드"
]

notice_items = [
    "고객ID", "계좌번호", "주문번호", "원주문번호", "매도매수구분", "정정구분", "주문종류",
    "주문조건", "주식단축종목코드", "체결수량", "체결단가", "주식체결시간", "거부여부",
    "체결여부", "접수여부", "지점번호", "주문수량", "계좌명", "체결종목명", "신용구분",
    "신용대출일자", "체결종목명40", "주문가격"
]


class KoreaInvestmentWS(Process):
    """WebSocket
    """
    def __init__(self, api_key: str, api_secret: str, tr_id_list: list,
                 tr_key_list: list, user_id: str = None):
        """_summary_
        Args:
            api_key (str): _description_
            api_secret (str): _description_
            tr_id_list (list): _description_
            tr_key_list (list): _description_
            user_id (str, optional): _description_. Defaults to None.
        """
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret
        self.tr_id_list = tr_id_list
        self.tr_key_list = tr_key_list
        self.user_id = user_id
        self.aes_key = None
        self.aes_iv = None
        self.queue = Queue()
        self.base_url = "https://openapi.koreainvestment.com:9443"

    def run(self):
        """_summary_
        """
        asyncio.run(self.ws_client())

    async def ws_client(self):
        ## WebSocket client
        uri = "ws://ops.koreainvestment.com:21000"

        approval_key = self.get_approval()

        async with websockets.connect(uri, ping_interval=None) as websocket:
            header = {
                "approval_key": approval_key,
                "personalseckey": "1",
                "custtype": "P",
                "tr_type": "1",
                "content-type": "utf-8"
            }
            fmt = {
                "header": header,
                "body": {
                    "input": {
                        "tr_id": None,
                        "tr_key": None,
                    }
                }
            }

            # 주식체결, 주식호가 등록
            for tr_id in self.tr_id_list:
                for tr_key in self.tr_key_list:
                    fmt["body"]["input"]["tr_id"] = tr_id
                    fmt["body"]["input"]["tr_key"] = tr_key
                    subscribe_data = json.dumps(fmt)
                    await websocket.send(subscribe_data)

            # 체결 통보 등록
            if self.user_id is not None:
                fmt["body"]["input"]["tr_id"] = "H0STCNI0"
                fmt["body"]["input"]["tr_key"] = self.user_id
                subscribe_data = json.dumps(fmt)
                await websocket.send(subscribe_data)

            while True:
                data = await websocket.recv()

                if data[0] == '0':
                    # 주식체결, 오더북
                    tokens = data.split('|')
                    if tokens[1] == "H0STCNT0":     # 주식 체결 데이터
                        self.parse_execution(tokens[2], tokens[3])
                    elif tokens[1] == "H0STASP0":
                        self.parse_orderbook(tokens[3])
                elif data[0] == '1':
                    tokens = data.split('|')
                    if tokens[1] == "H0STCNI0":
                        self.parse_notice(tokens[3])
                else:
                    ctrl_data = json.loads(data)
                    tr_id = ctrl_data["header"]["tr_id"]

                    if tr_id != "PINGPONG":
                        rt_cd = ctrl_data["body"]["rt_cd"]
                        if rt_cd == '1':
                            break
                        elif rt_cd == '0':
                            if tr_id in ["H0STASP0", "K0STCNI9", "H0STCNI0", "H0STCNI9"]:
                                self.aes_key = ctrl_data["body"]["output"]["key"]
                                self.aes_iv  = ctrl_data["body"]["output"]["iv"]

                    elif tr_id == "PINGPONG":
                        await websocket.send(data)

    def get_approval(self) -> str:
        """실시간 (웹소켓) 접속키 발급

        Returns:
            str: 웹소켓 접속키
        """
        headers = {"content-type": "application/json"}
        body = {"grant_type": "client_credentials",
                "appkey": self.api_key,
                "secretkey": self.api_secret}
        PATH = "oauth2/Approval"
        URL = f"{self.base_url}/{PATH}"
        res = requests.post(URL, headers=headers, data=json.dumps(body))
        return res.json()["approval_key"]

    def aes_cbc_base64_dec(self, cipher_text: str):
        """_summary_
        Args:
            cipher_text (str): _description_
        Returns:
            _type_: _description_
        """
        cipher = AES.new(self.aes_key.encode('utf-8'), AES.MODE_CBC, self.aes_iv.encode('utf-8'))
        return bytes.decode(unpad(cipher.decrypt(b64decode(cipher_text)), AES.block_size))

    def parse_notice(self, notice_data: str):
        """_summary_
        Args:
            notice_data (_type_): 주식 체잔 데이터
        """
        aes_dec_str = self.aes_cbc_base64_dec(notice_data)
        tokens = aes_dec_str.split('^')
        notice_data = dict(zip(notice_items, tokens))
        self.queue.put(['체잔', notice_data])

    def parse_execution(self, count: str, execution_data: str):
        """주식현재가 실시간 주식 체결가 데이터 파싱
        Args:
            count (str): the number of data
            execution_data (str): 주식 체결 데이터
        """
        tokens = execution_data.split('^')
        for i in range(int(count)):
            parsed_data = dict(zip(execution_items, tokens[i * 46: (i + 1) * 46]))
            self.queue.put(['체결', parsed_data])

    def parse_orderbook(self, orderbook_data: str):
        """_summary_
        Args:
            orderbook_data (str): 주식 호가 데이터
        """
        recvvalue = orderbook_data.split('^')
        orderbook = dict(zip(orderbook_items, recvvalue))
        self.queue.put(['호가', orderbook])

    def get(self):
        """get data from the queue

        Returns:
            _type_: _description_
        """
        data = self.queue.get()
        return data

    def terminate(self):
        if self.is_alive():
            self.kill()

    # ── REQ-WRAPPER-03: 해외 호가 WS 구독/해지 ────────────────────────────────
    def subscribe_overseas_orderbook(self, rsym: str) -> None:
        """해외 실시간 호가(HDFSASP0) 토픽 등록.

        Args:
            rsym: 실시간 심볼키. 형식 ``D{exchange3}{symbol}`` (실시간 D, 지연 R).
                  예) ``DNASAAPL`` (NAS의 AAPL 실시간).
        """
        if "HDFSASP0" not in self.tr_id_list:
            self.tr_id_list.append("HDFSASP0")
        if rsym not in self.tr_key_list:
            self.tr_key_list.append(rsym)

    def unsubscribe_overseas_orderbook(self, rsym: str) -> None:
        """해외 실시간 호가(HDFSASP0) 토픽 해지.

        등록되지 않은 키 해지 호출은 예외 없이 무시한다.
        """
        if rsym in self.tr_key_list:
            self.tr_key_list.remove(rsym)


# ── REQ-WRAPPER-03: 해외 호가 WS 메시지 파서 (모듈 레벨, services 공용) ─────────


def parse_overseas_orderbook(raw: str) -> dict | None:
    """KIS 해외 실시간 호가(HDFSASP0) 메시지 → 표준 dict.

    KIS 가이드 추정 ``^`` 구분 페이로드:
        [0]=rsym(D/R + EXCD3 + SYMB)
        [1..6]=영업일/현지일/현지시간/한국일/한국시간 메타
        [7..16]=매도호가1~10
        [17..26]=매수호가1~10
        [27..36]=매도잔량1~10
        [37..46]=매수잔량1~10
        [47]=총매도잔량
        [48]=총매수잔량

    응답 단계가 부족하면(빈 가격/잔량) 받은 단계만 반환.

    Args:
        raw: ``^`` 구분 raw 메시지.

    Returns:
        ``{"symbol", "exchange", "asks": [...], "bids": [...], "total_ask_volume",
        "total_bid_volume"}`` 또는 ``None`` (필드 부족 시).
    """
    if not raw:
        return None
    t = raw.split("^")
    if len(t) < 49:
        return None

    rsym = t[0] or ""
    if len(rsym) < 4:
        return None
    # rsym = D/R + EXCD3 + SYMB
    exchange = rsym[1:4]
    symbol = rsym[4:]
    if exchange not in ("NAS", "NYS", "AMS"):
        # 도쿄/홍콩 등 v1 미지원 — None 반환
        return None

    def _f(s: str) -> float:
        try:
            return float(s)
        except (TypeError, ValueError):
            return 0.0

    def _i(s: str) -> int:
        try:
            return int(float(s))
        except (TypeError, ValueError):
            return 0

    asks: list[dict] = []
    bids: list[dict] = []
    for i in range(10):
        p_ask = _f(t[7 + i])
        v_ask = _i(t[27 + i])
        if p_ask > 0:
            asks.append({"price": p_ask, "volume": v_ask})
        p_bid = _f(t[17 + i])
        v_bid = _i(t[37 + i])
        if p_bid > 0:
            bids.append({"price": p_bid, "volume": v_bid})

    return {
        "symbol": symbol,
        "exchange": exchange,
        "asks": asks,
        "bids": bids,
        "total_ask_volume": _i(t[47]),
        "total_bid_volume": _i(t[48]),
    }


class KoreaInvestment:
    '''
    한국투자증권 REST API
    '''
    def __init__(self, api_key: str, api_secret: str, acc_no: str,
                 exchange: str = "서울", mock: bool = False):
        """생성자
        Args:
            api_key (str): 발급받은 API key
            api_secret (str): 발급받은 API secret
            acc_no (str): 계좌번호 체계의 앞 8자리-뒤 2자리
            exchange (str): "서울", "나스닥", "뉴욕", "아멕스", "홍콩", "상해", "심천",
                            "도쿄", "하노이", "호치민"
            mock (bool): True (mock trading), False (real trading)
        """
        self.mock = mock
        self.set_base_url(mock)
        self.api_key = api_key
        self.api_secret = api_secret

        # account number
        self.acc_no = acc_no
        self.acc_no_prefix = acc_no.split('-')[0]
        self.acc_no_postfix = acc_no.split('-')[1]

        self.exchange = exchange

        # access token
        self.access_token = None
        if self.check_access_token():
            self.load_access_token()
        else:
            self.issue_access_token()

    def set_base_url(self, mock: bool = True):
        """테스트(모의투자) 서버 사용 설정
        Args:
            mock(bool, optional): True: 테스트서버, False: 실서버 Defaults to True.
        """
        if mock:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"

    def issue_access_token(self):
        """OAuth인증/접근토큰발급
        """
        path = "oauth2/tokenP"
        url = f"{self.base_url}/{path}"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.api_key,
            "appsecret": self.api_secret
        }

        resp = requests.post(url, headers=headers, data=json.dumps(data))
        resp_data = resp.json()
        self.access_token = f'Bearer {resp_data["access_token"]}'

        # add extra information for the token verification
        now = datetime.datetime.now()
        resp_data['timestamp'] = int(now.timestamp()) + resp_data["expires_in"]
        resp_data['api_key'] = self.api_key
        resp_data['api_secret'] = self.api_secret

        # dump access token
        with open("token.dat", "wb") as f:
            pickle.dump(resp_data, f)

    def check_access_token(self):
        """check access token

        Returns:
            Bool: True: token is valid, False: token is not valid
        """
        try:
            f = open("token.dat", "rb")
            data = pickle.load(f)
            f.close()

            expire_epoch = data['timestamp']
            now_epoch = int(datetime.datetime.now().timestamp())
            status = False

            if ((now_epoch - expire_epoch > 0) or
                (data['api_key'] != self.api_key) or
                (data['api_secret'] != self.api_secret)):
                status = False
            else:
                status = True
            return status
        except IOError:
            return False

    def load_access_token(self):
        """load access token
        """
        with open("token.dat", "rb") as f:
            data = pickle.load(f)
            self.access_token = f'Bearer {data["access_token"]}'

    def issue_hashkey(self, data: dict):
        """해쉬키 발급
        Args:
            data (dict): POST 요청 데이터
        Returns:
            _type_: _description_
        """
        path = "uapi/hashkey"
        url = f"{self.base_url}/{path}"
        headers = {
           "content-type": "application/json",
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "User-Agent": "Mozilla/5.0"
        }
        resp = requests.post(url, headers=headers, data=json.dumps(data))
        haskkey = resp.json()["HASH"]
        return haskkey

    def fetch_price(self, symbol: str) -> dict:
        """국내주식시세/주식현재가 시세
           해외주식현재가/해외주식 현재체결가

        Args:
            symbol (str): 종목코드

        Returns:
            dict: _description_
        """
        if self.exchange == "서울":
            return self.fetch_domestic_price("J", symbol)
        else:
            return self.fetch_oversea_price(symbol)

    def fetch_domestic_price(self, market_code: str, symbol: str) -> dict:
        """주식현재가시세
        Args:
            market_code (str): 시장 분류코드
            symbol (str): 종목코드
        Returns:
            dict: API 개발 가이드 참조
        """
        path = "uapi/domestic-stock/v1/quotations/inquire-price"
        url = f"{self.base_url}/{path}"
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "FHKST01010100"
        }
        params = {
            "fid_cond_mrkt_div_code": market_code,
            "fid_input_iscd": symbol
        }
        resp = requests.get(url, headers=headers, params=params)
        return resp.json()

    def fetch_oversea_price(self, symbol: str) -> dict:
        """해외주식현재가/해외주식 현재체결가
        Args:
            symbol (str): 종목코드
        Returns:
            dict: API 개발 가이드 참조
        """
        path = "uapi/overseas-price/v1/quotations/price"
        url = f"{self.base_url}/{path}"

        # request header
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "HHDFS00000300"
        }

        # query parameter
        exchange_code = EXCHANGE_CODE[self.exchange]
        params = {
            "AUTH": "",
            "EXCD": exchange_code,
            "SYMB": symbol
        }
        resp = requests.get(url, headers=headers, params=params)
        return resp.json()

    def fetch_today_1m_ohlcv(self, symbol: str, to: str=""):
        """국내주식시세/주식당일분봉조회

        Args:
            symbol (str): 6자리 종목코드
            to (str, optional): "HH:MM:00". Defaults to "".
        """
        result = {}
        now = datetime.datetime.now()

        if to == "":
            to = now.strftime("%H%M%S")

            # kospi market end time
            if to > "153000":
                to = "153000"

        output = self._fetch_today_1m_ohlcv(symbol, to)
        output2 = output['output2']
        last_hour = output2[-1]['stck_cntg_hour']

        result['output1'] = output['output1']
        result['output2'] = output2

        while last_hour > "090100":
            # last minute
            dt1 = datetime.datetime(
                year=now.year,
                month=now.month,
                day=now.day,
                hour=int(last_hour[:2]),
                minute=int(last_hour[2:4])
            )
            delta = datetime.timedelta(minutes=1)

            # 1 minute ago
            dt2 = dt1 - delta
            to = dt2.strftime("%H%M%S")

            # request 1minute ohlcv
            output = self._fetch_today_1m_ohlcv(symbol, to)
            output2 = output['output2']
            last_hour = output2[-1]['stck_cntg_hour']

            result['output2'].extend(output2)

        return result

    def _fetch_today_1m_ohlcv(self, symbol: str, to: str):
        """국내주식시세/주식당일분봉조회

        Args:
            symbol (str): 6자리 종목코드
            to (str): "HH:MM:SS"
        """
        path = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
        url = f"{self.base_url}/{path}"
        headers = {
           "content-type": "application/json; charset=utf-8",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "FHKST03010200",
           "tr_cont": "",
        }

        params = {
            "fid_etc_cls_code": "",
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": symbol,
            "fid_input_hour_1": to,
            "fid_pw_data_incu_yn": "Y"
        }
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def fetch_ohlcv(self, symbol: str, timeframe: str = 'D', start_day:str="", end_day:str="",
                    adj_price: bool = True) -> dict:
        """fetch OHLCV (day, week, month)
        Args:
            symbol (str): 종목코드
            timeframe (str): "D" (일), "W" (주), "M" (월)
            start_day (str): 조회시작일자
            end_day (str): 조회종료일자
            adj_price (bool, optional): True: 수정주가 반영, False: 수정주가 미반영. Defaults to True.
        Returns:
            dict: _description_
        """
        if self.exchange == '서울':
            resp = self.fetch_ohlcv_domestic(symbol, timeframe, start_day, end_day, adj_price)
        else:
            resp = self.fetch_ohlcv_overesea(symbol, timeframe, end_day, adj_price)
        return resp

    def fetch_ohlcv_recent30(self, symbol: str, timeframe: str = 'D', adj_price: bool = True) -> dict:
        """국내주식시세/주식 현재가 일자별
        Args:
            symbol (str): 종목코드
            timeframe (str): "D" (일), "W" (주), "M" (월)
            adj_price (bool, optional): True: 수정주가 반영, False: 수정주가 미반영. Defaults to True.
        Returns:
            dict: _description_
        """
        path = "uapi/domestic-stock/v1/quotations/inquire-daily-price"
        url = f"{self.base_url}/{path}"
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "FHKST01010400"
        }

        adj_param = "1" if adj_price else "0"
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": symbol,
            "fid_org_adj_prc": adj_param,
            "fid_period_div_code": timeframe
        }
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def fetch_symbols(self):
        """fetch symbols from the exchange

        Returns:
            pd.DataFrame: pandas dataframe
        """
        if self.exchange == "서울":
            df = self.fetch_kospi_symbols()
            kospi_df = df[['단축코드', '한글명', '그룹코드']].copy()
            kospi_df['시장'] = '코스피'

            df = self.fetch_kosdaq_symbols()
            kosdaq_df = df[['단축코드', '한글명', '그룹코드']].copy()
            kosdaq_df['시장'] = '코스닥'

            df = pd.concat([kospi_df, kosdaq_df], axis=0)

        return df

    def download_master_file(self, base_dir: str, file_name: str, url: str):
        """download master file

        Args:
            base_dir (str): download directory
            file_name (str: filename
            url (str): url
        """
        os.chdir(base_dir)

        # delete legacy master file
        if os.path.exists(file_name):
            os.remove(file_name)

        # download master file
        resp = requests.get(url)
        with open(file_name, "wb") as f:
            f.write(resp.content)

        # unzip
        kospi_zip = zipfile.ZipFile(file_name)
        kospi_zip.extractall()
        kospi_zip.close()

    def parse_kospi_master(self, base_dir: str):
        """parse kospi master file

        Args:
            base_dir (str): directory where kospi code exists

        Returns:
            _type_: _description_
        """
        file_name = base_dir + "/kospi_code.mst"
        tmp_fil1 = base_dir + "/kospi_code_part1.tmp"
        tmp_fil2 = base_dir + "/kospi_code_part2.tmp"

        wf1 = open(tmp_fil1, mode="w", encoding="cp949")
        wf2 = open(tmp_fil2, mode="w")

        with open(file_name, mode="r", encoding="cp949") as f:
            for row in f:
                rf1 = row[0:len(row) - 228]
                rf1_1 = rf1[0:9].rstrip()
                rf1_2 = rf1[9:21].rstrip()
                rf1_3 = rf1[21:].strip()
                wf1.write(rf1_1 + ',' + rf1_2 + ',' + rf1_3 + '\n')
                rf2 = row[-228:]
                wf2.write(rf2)

        wf1.close()
        wf2.close()

        part1_columns = ['단축코드', '표준코드', '한글명']
        df1 = pd.read_csv(tmp_fil1, header=None, encoding='cp949', names=part1_columns)

        field_specs = [
            2, 1, 4, 4, 4,
            1, 1, 1, 1, 1,
            1, 1, 1, 1, 1,
            1, 1, 1, 1, 1,
            1, 1, 1, 1, 1,
            1, 1, 1, 1, 1,
            1, 9, 5, 5, 1,
            1, 1, 2, 1, 1,
            1, 2, 2, 2, 3,
            1, 3, 12, 12, 8,
            15, 21, 2, 7, 1,
            1, 1, 1, 1, 9,
            9, 9, 5, 9, 8,
            9, 3, 1, 1, 1
        ]

        part2_columns = [
            '그룹코드', '시가총액규모', '지수업종대분류', '지수업종중분류', '지수업종소분류',
            '제조업', '저유동성', '지배구조지수종목', 'KOSPI200섹터업종', 'KOSPI100',
            'KOSPI50', 'KRX', 'ETP', 'ELW발행', 'KRX100',
            'KRX자동차', 'KRX반도체', 'KRX바이오', 'KRX은행', 'SPAC',
            'KRX에너지화학', 'KRX철강', '단기과열', 'KRX미디어통신', 'KRX건설',
            'Non1', 'KRX증권', 'KRX선박', 'KRX섹터_보험', 'KRX섹터_운송',
            'SRI', '기준가', '매매수량단위', '시간외수량단위', '거래정지',
            '정리매매', '관리종목', '시장경고', '경고예고', '불성실공시',
            '우회상장', '락구분', '액면변경', '증자구분', '증거금비율',
            '신용가능', '신용기간', '전일거래량', '액면가', '상장일자',
            '상장주수', '자본금', '결산월', '공모가', '우선주',
            '공매도과열', '이상급등', 'KRX300', 'KOSPI', '매출액',
            '영업이익', '경상이익', '당기순이익', 'ROE', '기준년월',
            '시가총액', '그룹사코드', '회사신용한도초과', '담보대출가능', '대주가능'
        ]

        df2 = pd.read_fwf(tmp_fil2, widths=field_specs, names=part2_columns)
        df = pd.merge(df1, df2, how='outer', left_index=True, right_index=True)

        # clean temporary file and dataframe
        del (df1)
        del (df2)
        os.remove(tmp_fil1)
        os.remove(tmp_fil2)
        return df

    def parse_kosdaq_master(self, base_dir: str):
        """parse kosdaq master file

        Args:
            base_dir (str): directory where kosdaq code exists

        Returns:
            _type_: _description_
        """
        file_name = base_dir + "/kosdaq_code.mst"
        tmp_fil1 = base_dir +  "/kosdaq_code_part1.tmp"
        tmp_fil2 = base_dir +  "/kosdaq_code_part2.tmp"

        wf1 = open(tmp_fil1, mode="w", encoding="cp949")
        wf2 = open(tmp_fil2, mode="w")
        with open(file_name, mode="r", encoding="cp949") as f:
            for row in f:
                rf1 = row[0:len(row) - 222]
                rf1_1 = rf1[0:9].rstrip()
                rf1_2 = rf1[9:21].rstrip()
                rf1_3 = rf1[21:].strip()
                wf1.write(rf1_1 + ',' + rf1_2 + ',' + rf1_3 + '\n')

                rf2 = row[-222:]
                wf2.write(rf2)

        wf1.close()
        wf2.close()

        part1_columns = ['단축코드', '표준코드', '한글명']
        df1 = pd.read_csv(tmp_fil1, header=None, encoding="cp949", names=part1_columns)

        field_specs = [
            2, 1, 4, 4, 4,      # line 20
            1, 1, 1, 1, 1,      # line 27
            1, 1, 1, 1, 1,      # line 32
            1, 1, 1, 1, 1,      # line 38
            1, 1, 1, 1, 1,      # line 43
            1, 9, 5, 5, 1,      # line 48
            1, 1, 2, 1, 1,      # line 54
            1, 2, 2, 2, 3,      # line 64
            1, 3, 12, 12, 8,    # line 69
            15, 21, 2, 7, 1,    # line 75
            1, 1, 1, 9, 9,      # line 80
            9, 5, 9, 8, 9,      # line 85
            3, 1, 1, 1
        ]

        part2_columns = [
            '그룹코드', '시가총액규모', '지수업종대분류', '지수업종중분류', '지수업종소분류', # line 20
            '벤처기업', '저유동성', 'KRX', 'ETP', 'KRX100',  # line 27
            'KRX자동차', 'KRX반도체', 'KRX바이오', 'KRX은행', 'SPAC',   # line 32
            'KRX에너지화학', 'KRX철강', '단기과열', 'KRX미디어통신', 'KRX건설', # line 38
            '투자주의', 'KRX증권', 'KRX선박', 'KRX섹터_보험', 'KRX섹터_운송',   # line 43
            'KOSDAQ150', '기준가', '매매수량단위', '시간외수량단위', '거래정지',    # line 48
            '정리매매', '관리종목', '시장경고', '경고예고', '불성실공시',   # line 54
            '우회상장', '락구분', '액면변경', '증자구분', '증거금비율',     # line 64
            '신용가능', '신용기간', '전일거래량', '액면가', '상장일자',     # line 69
            '상장주수', '자본금', '결산월', '공모가', '우선주',     # line 75
            '공매도과열', '이상급등', 'KRX300', '매출액', '영업이익',   # line 80
            '경상이익', '당기순이익', 'ROE', '기준년월', '시가총액',    # line 85
            '그룹사코드', '회사신용한도초과', '담보대출가능', '대주가능'
        ]

        df2 = pd.read_fwf(tmp_fil2, widths=field_specs, names=part2_columns)
        df = pd.merge(df1, df2, how='outer', left_index=True, right_index=True)

        # clean temporary file and dataframe
        del (df1)
        del (df2)
        os.remove(tmp_fil1)
        os.remove(tmp_fil2)
        return df

    def fetch_kospi_symbols(self):
        """코스피 종목 코드

        Returns:
            DataFrame:
        """
        base_dir = os.getcwd()
        file_name = "kospi_code.mst.zip"
        url = "https://new.real.download.dws.co.kr/common/master/" + file_name
        self.download_master_file(base_dir, file_name, url)
        df = self.parse_kospi_master(base_dir)
        return df

    def fetch_kosdaq_symbols(self):
        """코스닥 종목 코드

        Returns:
            DataFrame:
        """
        base_dir = os.getcwd()
        file_name = "kosdaq_code.mst.zip"
        url = "https://new.real.download.dws.co.kr/common/master/" + file_name
        self.download_master_file(base_dir, file_name, url)
        df = self.parse_kosdaq_master(base_dir)
        return df

    def check_buy_order(self, symbol: str, price: int, order_type: str):
        """국내주식주문/매수가능조회

        Args:
            symbol (str): symbol
            price (int): 1주당 가격
            order_type (str): "00": 지정가, "01": 시장가, ..., "80": 바스켓
        """
        path = "/uapi/domestic-stock/v1/trading/inquire-psbl-order"
        url = f"{self.base_url}/{path}"
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "VTTC8908R" if self.mock else "TTTC8908R"
        }
        params = {
            'CANO': self.acc_no_prefix,
            'ACNT_PRDT_CD': self.acc_no_postfix,
            'PDNO': symbol,
            'ORD_UNPR': str(price),
            'ORD_DVSN': order_type,
            'CMA_EVLU_AMT_ICLD_YN': '1',
            'OVRS_ICLD_YN': '1'
        }

        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        data['tr_cont'] = res.headers['tr_cont']
        return data

    def fetch_balance(self) -> dict:
        """잔고 조회

        Args:

        Returns:
            dict: response data
        """
        if self.exchange == '서울':
            output = {}

            data = self.fetch_balance_domestic()
            output['output1'] = data['output1']
            output['output2'] = data['output2']

            while data['tr_cont'] == 'M':
                fk100 = data['ctx_area_fk100']
                nk100 = data['ctx_area_nk100']

                data = self.fetch_balance_domestic(fk100, nk100)
                output['output1'].extend(data['output1'])
                output['output2'].extend(data['output2'])

            return output
        else:
            # 해외주식 잔고
            output = {}

            data = self.fetch_balance_oversea()
            output['output1'] = data['output1']
            output['output2'] = data['output2']

            while data['tr_cont'] == 'M':
                fk200 = data['ctx_area_fk200']
                nk200 = data['ctx_area_nk200']

                data = self.fetch_balance_oversea(fk200, nk200)
                output['output1'].extend(data['output1'])
                output['output2'].extend(data['output2'])

            return output

    def fetch_balance_domestic(self, ctx_area_fk100: str = "", ctx_area_nk100: str = "") -> dict:
        """국내주식주문/주식잔고조회
        Args:
            ctx_area_fk100 (str): 연속조회검색조건100
            ctx_areak_nk100 (str): 연속조회키100
        Returns:
            dict: _description_
        """
        path = "uapi/domestic-stock/v1/trading/inquire-balance"
        url = f"{self.base_url}/{path}"
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "VTTC8434R" if self.mock else "TTTC8434R"
        }
        params = {
            'CANO': self.acc_no_prefix,
            'ACNT_PRDT_CD': self.acc_no_postfix,
            'AFHR_FLPR_YN': 'N',
            'OFL_YN': 'N',
            'INQR_DVSN': '01',
            'UNPR_DVSN': '01',
            'FUND_STTL_ICLD_YN': 'N',
            'FNCG_AMT_AUTO_RDPT_YN': 'N',
            'PRCS_DVSN': '01',
            'CTX_AREA_FK100': ctx_area_fk100,
            'CTX_AREA_NK100': ctx_area_nk100
        }

        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        data['tr_cont'] = res.headers['tr_cont']
        return data

    def fetch_present_balance(self, foreign_currency: bool=True) -> dict:
        """해외주식주문/해외주식 체결기준현재잔고
        Args:
            foreign_currency (bool): True: 외화, False: 원화
        Returns:
            dict: _description_
        """
        path = "/uapi/overseas-stock/v1/trading/inquire-present-balance"
        url = f"{self.base_url}/{path}"

        # request header
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "VTRP6504R" if self.mock else "CTRP6504R"
        }

        # query parameter
        nation_code = "000"
        if self.exchange in ["나스닥", "뉴욕", "아멕스"]:
            nation_code = "840"
        elif self.exchange == "홍콩":
            nation_code = "344"
        elif self.exchange in ["상해", "심천"]:
            nation_code = "156"
        elif self.exchange == "도쿄":
            nation_code = "392"
        elif self.exchange in ["하노이", "호치민"]:
            nation_code = "704"
        else:
            nation_code = "000"

        market_code = "00"
        if nation_code == "000":
            market_code = "00"
        elif nation_code == "840":
            if self.exchange == "나스닥":
                market_code = "01"
            elif self.exchange == "뉴욕":
                market_code = "02"
            elif self.exchange == "아멕스":
                market_code = "05"
            else:
                market_code = "00"
        elif nation_code == "156":
            market_code = "00"
        elif nation_code == "392":
            market_code = "01"
        elif nation_code == "704":
            if self.exchange == "하노이":
                market_code = "01"
            else:
                market_code = "02"
        else:
            market_code = "01"

        params = {
            'CANO': self.acc_no_prefix,
            'ACNT_PRDT_CD': self.acc_no_postfix,
            "WCRC_FRCR_DVSN_CD": "02" if foreign_currency else "01",
            "NATN_CD": nation_code,
            "TR_MKET_CD": market_code,
            "INQR_DVSN_CD": "00"
        }
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def fetch_balance_oversea(self, ctx_area_fk200: str = "", ctx_area_nk200: str = "") -> dict:
        """해외주식주문/해외주식 잔고
        Args:
            ctx_area_fk200 (str): 연속조회검색조건200
            ctx_area_nk200 (str): 연속조회키200
        Returns:
            dict: _description_
        """
        path = "/uapi/overseas-stock/v1/trading/inquire-balance"
        url = f"{self.base_url}/{path}"


        # 주야간원장 구분 호출
        resp = self.fetch_oversea_day_night()
        psbl = resp['output']['PSBL_YN']

        if self.mock:
            tr_id = "VTTS3012R" if psbl == 'N' else 'VTTT3012R'
        else:
            tr_id = "TTTS3012R" if psbl == 'N' else 'JTTT3012R'

        # request header
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": tr_id
        }

        # query parameter
        exchange_cd = EXCHANGE_CODE2[self.exchange]
        currency_cd = CURRENCY_CODE[self.exchange]

        params = {
            'CANO': self.acc_no_prefix,
            'ACNT_PRDT_CD': self.acc_no_postfix,
            'OVRS_EXCG_CD': exchange_cd,
            'TR_CRCY_CD': currency_cd,
            'CTX_AREA_FK200': ctx_area_fk200,
            'CTX_AREA_NK200': ctx_area_nk200
        }

        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        data['tr_cont'] = res.headers['tr_cont']
        return data

    def fetch_oversea_day_night(self):
        """해외주식주문/해외주식 주야간원장구분조회
        """
        path = "/uapi/overseas-stock/v1/trading/dayornight"
        url = f"{self.base_url}/{path}"

        # request/header
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "JTTT3010R"
        }

        res = requests.get(url, headers=headers)
        return res.json()

    def create_order(self, side: str, symbol: str, price: int,
                     quantity: int, order_type: str) -> dict:
        """국내주식주문/주식주문(현금)

        Args:
            side (str): _description_
            symbol (str): symbol
            price (int): _description_
            quantity (int): _description_
            order_type (str): _description_

        Returns:
            dict: _description_
        """
        path = "uapi/domestic-stock/v1/trading/order-cash"
        url = f"{self.base_url}/{path}"

        if self.mock:
            tr_id = "VTTC0802U" if side == "buy" else "VTTC0801U"
        else:
            tr_id = "TTTC0802U" if side == "buy" else "TTTC0801U"

        unpr = "0" if order_type == "01" else str(price)

        data = {
            "CANO": self.acc_no_prefix,
            "ACNT_PRDT_CD": self.acc_no_postfix,
            "PDNO": symbol,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": unpr
        }
        hashkey = self.issue_hashkey(data)
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": tr_id,
           "custtype": "P",
           "hashkey": hashkey
        }
        resp = requests.post(url, headers=headers, data=json.dumps(data))
        return resp.json()

    def create_market_buy_order(self, symbol: str, quantity: int) -> dict:
        """시장가 매수

        Args:
            symbol (str): symbol
            quantity (int): quantity

        Returns:
            dict: _description_
        """
        if self.exchange == "서울":
            resp = self.create_order("buy", symbol, 0, quantity, "01")
        else:
            resp = self.create_oversea_order("buy", symbol, "0", quantity, "00")
        return resp

    def create_market_sell_order(self, symbol: str, quantity: int) -> dict:
        """시장가 매도

        Args:
            symbol (str): _description_
            quantity (int): _description_

        Returns:
            dict: _description_
        """
        if self.exchange == "서울":
            resp = self.create_order("sell", symbol, 0, quantity, "01")
        else:
            resp = self.create_oversea_order("sell", symbol, "0", quantity, "00")
        return resp

    def create_limit_buy_order(self, symbol: str, price: int, quantity: int) -> dict:
        """지정가 매수

        Args:
            symbol (str): 종목코드
            price (int): 가격
            quantity (int): 수량

        Returns:
            dict: _description_
        """
        if self.exchange == "서울":
            resp = self.create_order("buy", symbol, price, quantity, "00")
        else:
            resp = self.create_oversea_order("buy", symbol, price, quantity, "00")

        return resp

    def create_limit_sell_order(self, symbol: str, price: int, quantity: int) -> dict:
        """지정가 매도

        Args:
            symbol (str): _description_
            price (int): _description_
            quantity (int): _description_

        Returns:
            dict: _description_
        """
        if self.exchange == "서울":
            resp = self.create_order("sell", symbol, price, quantity, "00")
        else:
            resp = self.create_oversea_order("sell", symbol, price, quantity, "00")
        return resp

    def cancel_order(self, org_no: str, order_no: str, quantity: int, total: bool,
                     order_type: str="00", price: int=100):
        """주문 취소

        Args:
            org_no(str): organization number
            order_no (str): order number
            quantity (int): 수량
            total (bool): True (잔량전부), False (잔량일부)
            order_type (str): 주문구분
            price (int): 가격

        Returns:
            dict :
        """
        return self.update_order(
            org_no, order_no, order_type, price, quantity, False, total
        )

    def modify_order(self, org_no: str, order_no: str, order_type: str,
                     price: int, quantity: int, total: bool):
        """주문정정

        Args:
            org_no(str): organization number
            order_no (str): order number
            order_type (str): 주문구분
            price (int): 가격
            quantity (int): 수량
            total (bool): True (잔량전부), False (잔량일부)

        Returns:
            dict : _description_
        """
        return self.update_order(
            org_no, order_no, order_type, price, quantity, True, total)

    def update_order(self, org_no: str, order_no: str, order_type: str, price: int,
                     quantity: int, is_change: bool = True, total: bool = True):
        """국내주식주문/주식주문(정정취소)

        Args:
            org_no (str): organization code
            order_no (str): order number
            order_type (str): 주문구분
            price (int): 가격
            quantity (int): 수량
            is_change (bool, optional): True: 정정, False: 취소
            total (bool, optional): True (잔량전부), False (잔량일부)

        Returns:
            _type_: _description_
        """
        path = "uapi/domestic-stock/v1/trading/order-rvsecncl"
        url = f"{self.base_url}/{path}"
        param = "01" if is_change else "02"
        data = {
            "CANO": self.acc_no_prefix,
            "ACNT_PRDT_CD": self.acc_no_postfix,
            "KRX_FWDG_ORD_ORGNO": org_no,
            "ORGN_ODNO": order_no,
            "ORD_DVSN": order_type,
            "RVSE_CNCL_DVSN_CD": param,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
            "QTY_ALL_ORD_YN": 'Y' if total else 'N'
        }
        hashkey = self.issue_hashkey(data)
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "VTTC0803U" if self.mock else "TTTC0803U",
           "hashkey": hashkey
        }
        resp = requests.post(url, headers=headers, data=json.dumps(data))
        return resp.json()

    def fetch_open_order(self, param: dict):
        """주식 정정/취소가능 주문 조회
        Args:
            param (dict): 세부 파라미터
        Returns:
            _type_: _description_
        """
        path = "uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
        url = f"{self.base_url}/{path}"

        fk100 = param["CTX_AREA_FK100"]
        nk100 = param["CTX_AREA_NK100"]
        type1 = param["INQR_DVSN_1"]
        type2 = param["INQR_DVSN_2"]

        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "TTTC8036R"
        }

        params = {
            "CANO": self.acc_no_prefix,
            "ACNT_PRDT_CD": self.acc_no_postfix,
            "CTX_AREA_FK100": fk100,
            "CTX_AREA_NK100": nk100,
            "INQR_DVSN_1": type1,
            "INQR_DVSN_2": type2
        }

        resp = requests.get(url, headers=headers, params=params)
        return resp.json()

    def create_oversea_order(self, side: str, symbol: str, price: int,
                             quantity: int, order_type: str) -> dict:
        """해외주식주문/해외주식 주문

        Args:
            side (str): buy: 매수, sell: 매도
            symbol (str): symbol
            price (int): price
            quantity (int): quantity
            order_type (str): "00", "LOO", "LOC", "MOO", "MOC"

        Returns:
            dict: _description_
        """
        path = "uapi/overseas-stock/v1/trading/order"
        url = f"{self.base_url}/{path}"

        tr_id = None
        if self.mock:
            if self.exchange in ["나스닥", "뉴욕", "아멕스"]:
                tr_id = "VTTT1002U" if side == "buy" else "VTTT1002U"
            elif self.exchange == '도쿄':
                tr_id = "VTTS0308U" if side == "buy" else "VTTS0307U"
            elif self.exchange == '상해':
                tr_id = "VTTS0202U" if side == "buy" else "VTTS1005U"
            elif self.exchange == '홍콩':
                tr_id = "VTTS1002U" if side == "buy" else "VTTS1001U"
            elif self.exchange == '심천':
                tr_id = "VTTS0305U" if side == "buy" else "VTTS0304U"
            else:
                tr_id = "VTTS0311U" if side == "buy" else "VTTS0310U"
        else:
            if self.exchange in ["나스닥", "뉴욕", "아멕스"]:
                tr_id = "TTTT1002U" if side == "buy" else "TTTT1006U"
            elif self.exchange == '도쿄':
                tr_id = "TTTS0308U" if side == "buy" else "TTTS0307U"
            elif self.exchange == '상해':
                tr_id = "TTTS0202U" if side == "buy" else "TTTS1005U"
            elif self.exchange == '홍콩':
                tr_id = "TTTS1002U" if side == "buy" else "TTTS1001U"
            elif self.exchange == '심천':
                tr_id = "TTTS0305U" if side == "buy" else "TTTS0304U"
            else:
                tr_id = "TTTS0311U" if side == "buy" else "TTTS0310U"

        exchange_cd = EXCHANGE_CODE3[self.exchange]

        ord_dvsn = "00"
        if tr_id == "TTTT1002U":
            if order_type == "00":
                ord_dvsn = "00"
            elif order_type == "LOO":
                ord_dvsn = "32"
            elif order_type == "LOC":
                ord_dvsn = "34"
        elif tr_id == "TTTT1006U":
            if order_type == "00":
                ord_dvsn = "00"
            elif order_type == "MOO":
                ord_dvsn = "31"
            elif order_type == "LOO":
                ord_dvsn = "32"
            elif order_type == "MOC":
                ord_dvsn = "33"
            elif order_type == "LOC":
                ord_dvsn = "34"
        else:
            ord_dvsn = "00"

        data = {
            "CANO": self.acc_no_prefix,
            "ACNT_PRDT_CD": self.acc_no_postfix,
            "OVRS_EXCG_CD": exchange_cd,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price),
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": ord_dvsn
        }
        hashkey = self.issue_hashkey(data)
        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": tr_id,
           "hashkey": hashkey
        }
        resp = requests.post(url, headers=headers, data=json.dumps(data))
        return resp.json()

    def fetch_ohlcv_domestic(self, symbol: str, timeframe:str='D', start_day:str="",
                             end_day:str="", adj_price:bool=True):
        """국내주식시세/국내주식 기간별 시세(일/주/월/년)

        Args:
            symbol (str): symbol
            timeframe (str, optional): "D": 일, "W": 주, "M": 월, 'Y': 년
            start_day (str, optional): 조회시작일자(YYYYMMDD)
            end_day (str, optional): 조회종료일자(YYYYMMDD)
            adjusted (bool, optional): False: 수정주가 미반영, True: 수정주가 반영
        """
        path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        url = f"{self.base_url}/{path}"

        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "FHKST03010100"
        }

        if end_day == "":
            now = datetime.datetime.now()
            end_day = now.strftime("%Y%m%d")

        if start_day == "":
            start_day = "19800104"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
            "FID_INPUT_DATE_1": start_day,
            "FID_INPUT_DATE_2": end_day,
            "FID_PERIOD_DIV_CODE": timeframe,
            "FID_ORG_ADJ_PRC": 0 if adj_price else 1
        }
        resp = requests.get(url, headers=headers, params=params)
        return resp.json()

    def fetch_minute_bar_overesea(self, symbol: str, exchange: str,
                                  time_period: str = "60",
                                  end_day: str = "",
                                  end_time: str = "",
                                  *,
                                  keyb: str = "",
                                  next_flag: str = "",
                                  pinc: str = "1",
                                  nrec: str = "120",
                                  fill: str = "") -> dict:
        """해외주식 분봉 (HHDFS76950200).

        REQ-WRAPPER-01: 미국주식 분봉(15분/60분 단위) 조회.
        거래소 코드는 인자로 명시(자동 resolve는 상위 레이어 책임).

        Args:
            symbol (str): 종목 코드 (예: "AAPL")
            exchange (str): 거래소 코드 (NAS/NYS/AMS — 인자 그대로 EXCD에 사용)
            time_period (str): 분봉 단위 ("15"/"60" 등). 기본 60.
            end_day (str): 조회 종료일 YYYYMMDD. 기본 ""(최신).
            end_time (str): 조회 종료시각 HHMMSS. 기본 ""(최신).
            keyb (str): 연속조회 키 (페이지네이션). 기본 ""(첫 페이지).
            next_flag (str): NEXT 플래그 (KIS 컨벤션 ""=초기 / "N"=재요청).
            pinc (str): PINC (포함여부). 기본 "1".
            nrec (str): NREC (요청 건수). 기본 "120".
            fill (str): FILL (결측 채우기). 기본 ""(미사용).

        Returns:
            dict: KIS 원시 응답({"output1": {...메타}, "output2": [...분봉 배열]}).

        Raises:
            ExternalAPIError: rt_cd != "0" 인 경우.
        """
        # 지연 import (서비스 레이어 예외 계층)
        from services.exceptions import ExternalAPIError as _ExternalAPIError

        path = "/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice"
        url = f"{self.base_url}{path}"

        headers = {
            "content-type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "HHDFS76950200"
        }

        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol,
            "NMIN": time_period,
            "PINC": pinc,
            "NEXT": next_flag,
            "NREC": nrec,
            "FILL": fill,
            "KEYB": keyb,
        }
        # end_day/end_time 은 KIS가 지원하면 추가, 미지원 환경 호환을 위해 옵션 (요건서 시그니처 보존)
        if end_day:
            params["EDAY"] = end_day
        if end_time:
            params["ETIM"] = end_time

        resp = requests.get(url, headers=headers, params=params)
        try:
            data = resp.json()
        except ValueError as e:
            raise _ExternalAPIError(f"KIS 분봉 응답 파싱 실패: {e}")

        if data.get("rt_cd") != "0":
            raise _ExternalAPIError(
                f"KIS 분봉 조회 실패 (rt_cd={data.get('rt_cd')} msg={data.get('msg1', '')})"
            )
        return data

    def fetch_oversea_asking_price(self, symbol: str, exchange: str) -> dict:
        """해외주식 10단계 호가 조회 (HHDFS76200100, 실전 한정).

        REQ-WRAPPER-01. 거래소 코드는 인자로 명시(NAS/NYS/AMS).

        Args:
            symbol (str): 종목 코드 (예: "AAPL").
            exchange (str): 거래소 코드 (NAS/NYS/AMS — EXCD에 직접 사용).

        Returns:
            dict: KIS 원시 응답 ({"output1": {...메타}, "output2": {...10단계 호가}}).

        Raises:
            ExternalAPIError: rt_cd != "0" 또는 JSON 파싱 실패 시.
        """
        from services.exceptions import ExternalAPIError as _ExternalAPIError

        path = "/uapi/overseas-price/v1/quotations/inquire-asking-price"
        url = f"{self.base_url}{path}"

        headers = {
            "content-type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "HHDFS76200100",
        }
        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol,
        }

        resp = requests.get(url, headers=headers, params=params)
        try:
            data = resp.json()
        except ValueError as e:
            raise _ExternalAPIError(f"KIS 해외 호가 응답 파싱 실패: {e}")

        if data.get("rt_cd") != "0":
            raise _ExternalAPIError(
                f"KIS 해외 호가 조회 실패 (rt_cd={data.get('rt_cd')} msg={data.get('msg1', '')})"
            )
        return data

    def fetch_oversea_price_detail(self, symbol: str, exchange: str) -> dict:
        """해외주식 현재가 상세 조회 (HHDFS76200200).

        REQ-WRAPPER-02. 시/고/저/거래량/52주 고저/전일종가 등 상세 시세.

        Args:
            symbol (str): 종목 코드.
            exchange (str): 거래소 코드 (NAS/NYS/AMS — EXCD에 직접 사용).

        Returns:
            dict: KIS 원시 응답 (output에 가격 상세 필드 포함).

        Raises:
            ExternalAPIError: rt_cd != "0" 또는 JSON 파싱 실패 시.
        """
        from services.exceptions import ExternalAPIError as _ExternalAPIError

        path = "/uapi/overseas-price/v1/quotations/price-detail"
        url = f"{self.base_url}{path}"

        headers = {
            "content-type": "application/json",
            "authorization": self.access_token,
            "appKey": self.api_key,
            "appSecret": self.api_secret,
            "tr_id": "HHDFS76200200",
        }
        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol,
        }

        resp = requests.get(url, headers=headers, params=params)
        try:
            data = resp.json()
        except ValueError as e:
            raise _ExternalAPIError(f"KIS 해외 현재가상세 응답 파싱 실패: {e}")

        if data.get("rt_cd") != "0":
            raise _ExternalAPIError(
                f"KIS 해외 현재가상세 조회 실패 (rt_cd={data.get('rt_cd')} msg={data.get('msg1', '')})"
            )
        return data

    def fetch_ohlcv_overesea(self, symbol: str, timeframe:str='D',
                             end_day:str="", adj_price:bool=True):
        """해외주식현재가/해외주식 기간별시세

        Args:
            symbol (str): symbol
            timeframe (str, optional): "D": 일, "W": 주, "M": 월
            end_day (str, optional): 조회종료일자 (YYYYMMDD)
            adjusted (bool, optional): False: 수정주가 미반영, True: 수정주가 반영
        """
        path = "/uapi/overseas-price/v1/quotations/dailyprice"
        url = f"{self.base_url}/{path}"

        headers = {
           "content-type": "application/json",
           "authorization": self.access_token,
           "appKey": self.api_key,
           "appSecret": self.api_secret,
           "tr_id": "HHDFS76240000"
        }

        timeframe_lookup = {
            'D': "0",
            'W': "1",
            'M': "2"
        }

        if end_day == "":
            now = datetime.datetime.now()
            end_day = now.strftime("%Y%m%d")

        exchange_code = EXCHANGE_CODE4[self.exchange]

        params = {
            "AUTH": "",
            "EXCD": exchange_code,
            "SYMB": symbol,
            "GUBN": timeframe_lookup.get(timeframe, "0"),
            "BYMD": end_day,
            "MODP": 1 if adj_price else 0
        }
        resp = requests.get(url, headers=headers, params=params)
        return resp.json()


# ───────────────────────────────────────────────────────────────────────────
# 투자자별 매매동향 (수급정보) — module-level standalone helpers
# REQ-SUPPLY-API-01 / REQ-SUPPLY-API-02
# 클래스 인스턴스(token.dat) 의존 없이 routers/_kis_auth의 사용자별 토큰 캐시 활용.
# 단위는 백만원(KIS 원본) 유지 — 서비스 레이어에서 ÷100(억원) 변환.
# ───────────────────────────────────────────────────────────────────────────

_VALID_MARKET_CODES = {"U001", "U201"}


def _kis_token():
    """routers/_kis_auth.get_access_token() 위임. 테스트에서는 patch 대상."""
    from routers._kis_auth import get_access_token
    return get_access_token()


def _kis_app_key():
    """KIS appkey/appsecret 반환. 테스트에서는 patch 대상."""
    from routers._kis_auth import get_kis_credentials
    app_key, app_secret, _, _, _ = get_kis_credentials()
    return app_key, app_secret


def _kis_base_url() -> str:
    from routers._kis_auth import BASE_URL
    return BASE_URL


def _to_int(value, default: int = 0) -> int:
    """문자열/숫자를 int로. 빈문자 또는 None은 default."""
    if value is None:
        return default
    try:
        s = str(value).strip()
        if not s:
            return default
        # 부호 + 정수 또는 부호 + 소수 → 정수 반올림
        return int(round(float(s)))
    except (TypeError, ValueError):
        return default


def _to_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        s = str(value).strip()
        if not s:
            return default
        return float(s)
    except (TypeError, ValueError):
        return default


def _format_date_yyyymmdd(s: str) -> str:
    """'20240517' → '2024-05-17'. 형식 불일치 시 원본 반환."""
    if not s or len(s) < 8:
        return s or ""
    s = str(s).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return s


def get_market_investor_daily(market_code: str, days: int = 20) -> list[dict]:
    """시장별 투자자매매동향(일별). KIS TR_ID FHPTJ04040000.

    Args:
        market_code: "U001"(KOSPI) 또는 "U201"(KOSDAQ).
        days: 1~60. 기간 슬라이싱은 KIS가 자동(오늘 기준 역순)으로 반환되므로,
              본 함수는 응답을 그대로 받아 최대 `days`만큼 잘라 반환.

    Returns:
        list[dict]: 표준화 키 — date(YYYY-MM-DD), index_close, prev_diff, prev_pct,
        personal_net_amt, foreign_net_amt, institution_net_amt(각 백만원),
        그리고 기관 11종 분해(securities/inv_trust/private_fund/bank/insurance/
        mrbn/pension/etc_finance/etc_corp/etc_org_net_amt). 단위는 백만원 그대로.
        오름차순(과거→최근)으로 반환.

    Raises:
        ValueError: market_code 또는 days 범위 외.
        ExternalAPIError: KIS HTTP 5xx 또는 rt_cd != "0".
    """
    # ─ 입력 검증 ─
    if market_code not in _VALID_MARKET_CODES:
        raise ValueError(
            f"market_code는 'U001'(KOSPI) 또는 'U201'(KOSDAQ)이어야 합니다: {market_code!r}"
        )
    if not isinstance(days, int) or days < 1 or days > 60:
        raise ValueError(f"days는 1~60 범위여야 합니다: {days!r}")

    # ─ KIS 호출 파라미터 매핑 ─
    # FID_INPUT_ISCD / FID_INPUT_ISCD_2: 업종분류코드(0001=코스피, 1001=코스닥)
    # FID_INPUT_ISCD_1: 소속시장(KSP/KSQ). KIS 명세 FHPTJ04040000.
    iscd_map = {"U001": "0001", "U201": "1001"}
    iscd_short_map = {"U001": "KSP", "U201": "KSQ"}
    today = datetime.datetime.now().strftime("%Y%m%d")

    token = _kis_token()
    app_key, app_secret = _kis_app_key()
    base_url = _kis_base_url()

    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHPTJ04040000",
        "custtype": "P",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "U",
        "FID_INPUT_ISCD": iscd_map[market_code],
        "FID_INPUT_DATE_1": today,
        "FID_INPUT_ISCD_1": iscd_short_map[market_code],
        "FID_INPUT_DATE_2": today,
        "FID_INPUT_ISCD_2": iscd_map[market_code],
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
    except requests.RequestException as exc:
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(f"KIS 시장 수급 API 호출 실패: {exc}")

    if resp.status_code != 200:
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(
            f"KIS 시장 수급 HTTP {resp.status_code}: {getattr(resp, 'text', '')[:200]}"
        )

    data = resp.json() or {}
    if str(data.get("rt_cd", "")) != "0":
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(
            f"KIS 시장 수급 응답 오류: rt_cd={data.get('rt_cd')} msg={data.get('msg1', '')[:200]}"
        )

    raw_rows = data.get("output") or []

    # ─ 표준화 ─
    standardized: list[dict] = []
    for row in raw_rows:
        standardized.append({
            "date": _format_date_yyyymmdd(row.get("stck_bsop_date", "")),
            "index_close": _to_float(row.get("bstp_nmix_prpr")),
            "prev_diff": _to_float(row.get("bstp_nmix_prdy_vrss")),
            "prev_pct": _to_float(row.get("bstp_nmix_prdy_ctrt")),
            # 합계 3종 (백만원)
            "personal_net_amt": _to_int(row.get("prsn_ntby_tr_pbmn")),
            "foreign_net_amt": _to_int(row.get("frgn_ntby_tr_pbmn")),
            "institution_net_amt": _to_int(row.get("orgn_ntby_tr_pbmn")),
            # 기관 11종 분해 (백만원)
            "securities_net_amt": _to_int(row.get("scrt_ntby_tr_pbmn")),
            "inv_trust_net_amt": _to_int(row.get("ivtr_ntby_tr_pbmn")),
            "private_fund_net_amt": _to_int(row.get("pe_fund_ntby_tr_pbmn")),
            "bank_net_amt": _to_int(row.get("bank_ntby_tr_pbmn")),
            "insurance_net_amt": _to_int(row.get("insu_ntby_tr_pbmn")),
            "mrbn_net_amt": _to_int(row.get("mrbn_ntby_tr_pbmn")),
            "pension_net_amt": _to_int(row.get("fund_ntby_tr_pbmn")),
            "etc_finance_net_amt": _to_int(row.get("etc_ntby_tr_pbmn")),
            "etc_corp_net_amt": _to_int(row.get("etc_corp_ntby_tr_pbmn")),
            "etc_org_net_amt": _to_int(row.get("etc_orgt_ntby_tr_pbmn")),
        })

    # KIS는 보통 최신→과거 순. 과거→최신 정렬(차트 자연스러운 방향).
    standardized.sort(key=lambda r: r["date"])

    # days 만큼 슬라이싱 (최근 days개 유지)
    if len(standardized) > days:
        standardized = standardized[-days:]
    return standardized


def get_stock_investor_daily(code: str, days: int = 30) -> list[dict]:
    """종목별 투자자매매동향(일별). KIS TR_ID FHPTJ04160001.

    Args:
        code: 6자리 숫자(국내 종목).
        days: 1~60.

    Returns:
        list[dict]: 표준화 키 — 시장 응답에 매수/매도 분리 + close_price 추가.
        REQ-SUPPLY-API-02 명세. 단위는 백만원(서비스 레이어에서 변환).
        오름차순(과거→최근).

    Raises:
        ValueError: code 형식 또는 days 범위 외.
        ExternalAPIError: KIS 오류.
    """
    # ─ 입력 검증 ─
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        raise ValueError(f"code는 6자리 숫자여야 합니다(국내 종목만 지원): {code!r}")
    if not isinstance(days, int) or days < 1 or days > 60:
        raise ValueError(f"days는 1~60 범위여야 합니다: {days!r}")

    # KIS FHPTJ04160001 명세: "해당일 조회는 장 종료 후 정상 조회 가능"
    # KST 평일 15:40 이전 또는 주말이면 직전 영업일로 후퇴(장중에도 어제까지 데이터 조회 가능).
    _KST = datetime.timezone(datetime.timedelta(hours=9))
    _now_kst = datetime.datetime.now(_KST)
    _cutoff = _now_kst.replace(hour=15, minute=40, second=0, microsecond=0)
    if _now_kst.weekday() >= 5 or _now_kst < _cutoff:
        _d = _now_kst.date() - datetime.timedelta(days=1)
        while _d.weekday() >= 5:
            _d -= datetime.timedelta(days=1)
        today = _d.strftime("%Y%m%d")
    else:
        today = _now_kst.strftime("%Y%m%d")

    token = _kis_token()
    app_key, app_secret = _kis_app_key()
    base_url = _kis_base_url()

    url = f"{base_url}/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHPTJ04160001",
        "custtype": "P",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": code,
        "FID_INPUT_DATE_1": today,
        "FID_ORG_ADJ_PRC": "",
        "FID_ETC_CLS_CODE": "1",
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
    except requests.RequestException as exc:
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(f"KIS 종목 수급 API 호출 실패: {exc}")

    if resp.status_code != 200:
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(
            f"KIS 종목 수급 HTTP {resp.status_code}: {getattr(resp, 'text', '')[:200]}"
        )

    data = resp.json() or {}
    if str(data.get("rt_cd", "")) != "0":
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(
            f"KIS 종목 수급 응답 오류: rt_cd={data.get('rt_cd')} msg={data.get('msg1', '')[:200]}"
        )

    raw_rows = data.get("output2") or []
    standardized: list[dict] = []
    for row in raw_rows:
        standardized.append({
            "date": _format_date_yyyymmdd(row.get("stck_bsop_date", "")),
            "close_price": _to_int(row.get("stck_clpr")),
            # 순매수 합계 3종 (백만원)
            "personal_net_amt": _to_int(row.get("prsn_ntby_tr_pbmn")),
            "foreign_net_amt": _to_int(row.get("frgn_ntby_tr_pbmn")),
            "institution_net_amt": _to_int(row.get("orgn_ntby_tr_pbmn")),
            # 매수/매도 분리 (백만원)
            "personal_buy_amt": _to_int(row.get("prsn_shnu_tr_pbmn")),
            "personal_sell_amt": _to_int(row.get("prsn_seln_tr_pbmn")),
            "foreign_buy_amt": _to_int(row.get("frgn_shnu_tr_pbmn")),
            "foreign_sell_amt": _to_int(row.get("frgn_seln_tr_pbmn")),
            "institution_buy_amt": _to_int(row.get("orgn_shnu_tr_pbmn")),
            "institution_sell_amt": _to_int(row.get("orgn_seln_tr_pbmn")),
            # 기관 11종 분해 (백만원)
            "securities_net_amt": _to_int(row.get("scrt_ntby_tr_pbmn")),
            "inv_trust_net_amt": _to_int(row.get("ivtr_ntby_tr_pbmn")),
            "private_fund_net_amt": _to_int(row.get("pe_fund_ntby_tr_pbmn")),
            "bank_net_amt": _to_int(row.get("bank_ntby_tr_pbmn")),
            "insurance_net_amt": _to_int(row.get("insu_ntby_tr_pbmn")),
            "mrbn_net_amt": _to_int(row.get("mrbn_ntby_tr_pbmn")),
            "pension_net_amt": _to_int(row.get("fund_ntby_tr_pbmn")),
            "etc_finance_net_amt": _to_int(row.get("etc_ntby_tr_pbmn")),
            "etc_corp_net_amt": _to_int(row.get("etc_corp_ntby_tr_pbmn")),
            "etc_org_net_amt": _to_int(row.get("etc_orgt_ntby_tr_pbmn")),
        })
    standardized.sort(key=lambda r: r["date"])
    if len(standardized) > days:
        standardized = standardized[-days:]
    return standardized


def _opt_int(value):
    """문자열/숫자 → int. 빈문자/None → None (예외 X)."""
    if value is None:
        return None
    try:
        s = str(value).strip()
        if not s:
            return None
        return int(round(float(s)))
    except (TypeError, ValueError):
        return None


def _opt_float(value):
    """문자열/숫자 → float. 빈문자/None → None (예외 X)."""
    if value is None:
        return None
    try:
        s = str(value).strip()
        if not s:
            return None
        return float(s)
    except (TypeError, ValueError):
        return None


def get_foreign_holding_snapshot(code: str) -> dict:
    """종목별 외국인 보유 스냅샷. KIS TR_ID FHKST01010100 (주식현재가 시세).

    REQ-FH-API-01.

    Args:
        code: 6자리 숫자(국내 종목).

    Returns:
        dict: 표준화 키 — code, lstn_stcn, frgn_hldn_qty, hts_frgn_ehrt, as_of_date.
            frgn_hldn_qty / hts_frgn_ehrt 빈 문자열 → None.

    Raises:
        ValueError: code 형식 오류 (6자리 숫자 아님).
        ExternalAPIError: KIS HTTP 5xx 또는 rt_cd != "0".
        NotFoundError: output 누락 (종목 미존재 또는 응답 없음).
    """
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        raise ValueError(f"code는 6자리 숫자여야 합니다(국내 종목만 지원): {code!r}")

    token = _kis_token()
    app_key, app_secret = _kis_app_key()
    base_url = _kis_base_url()

    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHKST01010100",
        "custtype": "P",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": code,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
    except requests.RequestException as exc:
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(f"KIS 외국인 스냅샷 API 호출 실패: {exc}")

    if resp.status_code != 200:
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(
            f"KIS 외국인 스냅샷 HTTP {resp.status_code}: {getattr(resp, 'text', '')[:200]}"
        )

    data = resp.json() or {}
    if str(data.get("rt_cd", "")) != "0":
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(
            f"KIS 외국인 스냅샷 응답 오류: rt_cd={data.get('rt_cd')} msg={data.get('msg1', '')[:200]}"
        )

    output = data.get("output") or {}
    if not output:
        from services.exceptions import NotFoundError
        raise NotFoundError(f"종목 {code} 시세 응답 없음")

    _KST = datetime.timezone(datetime.timedelta(hours=9))
    as_of = datetime.datetime.now(_KST).strftime("%Y-%m-%d")

    return {
        "code": code,
        "lstn_stcn": _to_int(output.get("lstn_stcn")),
        "frgn_hldn_qty": _opt_int(output.get("frgn_hldn_qty")),
        "hts_frgn_ehrt": _opt_float(output.get("hts_frgn_ehrt")),
        "as_of_date": as_of,
    }


def get_foreign_holding_daily(code: str, days: int = 30) -> list[dict]:
    """종목별 외국인 보유율 일별 시계열. KIS TR_ID FHKST01010400 (주식현재가 일자별).

    REQ-FH-API-02. KIS 자체 한도 최근 30거래일.

    Args:
        code: 6자리 숫자.
        days: 1~30.

    Returns:
        list[dict]: 표준화 키 — date(YYYY-MM-DD), close, hts_frgn_ehrt(% or None),
            frgn_ntby_qty(int, 빈문자 → 0). 과거→최근 오름차순.

    Raises:
        ValueError: code 또는 days 범위 외.
        ExternalAPIError: KIS 오류.
    """
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        raise ValueError(f"code는 6자리 숫자여야 합니다(국내 종목만 지원): {code!r}")
    if not isinstance(days, int) or days < 1 or days > 30:
        raise ValueError(f"days는 1~30 범위여야 합니다(KIS 자체 한도): {days!r}")

    token = _kis_token()
    app_key, app_secret = _kis_app_key()
    base_url = _kis_base_url()

    url = f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHKST01010400",
        "custtype": "P",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": code,
        "FID_PERIOD_DIV_CODE": "D",
        "FID_ORG_ADJ_PRC": "0000000001",
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
    except requests.RequestException as exc:
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(f"KIS 외국인 일별 API 호출 실패: {exc}")

    if resp.status_code != 200:
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(
            f"KIS 외국인 일별 HTTP {resp.status_code}: {getattr(resp, 'text', '')[:200]}"
        )

    data = resp.json() or {}
    if str(data.get("rt_cd", "")) != "0":
        from services.exceptions import ExternalAPIError
        raise ExternalAPIError(
            f"KIS 외국인 일별 응답 오류: rt_cd={data.get('rt_cd')} msg={data.get('msg1', '')[:200]}"
        )

    raw_rows = data.get("output") or []
    standardized: list[dict] = []
    for row in raw_rows:
        standardized.append({
            "date": _format_date_yyyymmdd(row.get("stck_bsop_date", "")),
            "close": _to_int(row.get("stck_clpr")),
            "hts_frgn_ehrt": _opt_float(row.get("hts_frgn_ehrt")),
            "frgn_ntby_qty": _to_int(row.get("frgn_ntby_qty")),
        })
    standardized.sort(key=lambda r: r["date"])
    if len(standardized) > days:
        standardized = standardized[-days:]
    return standardized


if __name__ == "__main__":
    import pprint

    with open("../koreainvestment.key", encoding='utf-8') as key_file:
        lines = key_file.readlines()

    key = lines[0].strip()
    secret = lines[1].strip()
    acc_no = lines[2].strip()

    broker = KoreaInvestment(
        api_key=key,
        api_secret=secret,
        acc_no=acc_no,
        exchange="나스닥"
    )

    balance = broker.fetch_present_balance()
    print(balance)

    #result = broker.fetch_oversea_day_night()
    #pprint.pprint(result)

    #minute1_ohlcv = broker.fetch_today_1m_ohlcv("005930")
    #pprint.pprint(minute1_ohlcv)

    #broker = KoreaInvestment(key, secret, exchange="나스닥")
    #import pprint
    #resp = broker.fetch_price("005930")
    #pprint.pprint(resp)
    #
    #b = broker.fetch_balance("63398082")
    #pprint.pprint(b)
    #
    # resp = broker.create_market_buy_order("63398082", "005930", 10)
    # pprint.pprint(resp)
    #
    # resp = broker.cancel_order("63398082", "91252", "0000117057", "00", 60000, 5, "Y")
    # print(resp)
    #
    # resp = broker.create_limit_buy_order("63398082", "TQQQ", 35, 1)
    # print(resp)

    # 실시간주식 체결가
    #broker_ws = KoreaInvestmentWS(
    #   key, secret, ["H0STCNT0", "H0STASP0"], ["005930", "000660"], user_id="idjhh82")
    #broker_ws.start()
    #while True:
    #    data_ = broker_ws.get()
    #    if data_[0] == '체결':
    #        print(data_[1])
    #    elif data_[0] == '호가':
    #        print(data_[1])
    #    elif data_[0] == '체잔':
    #        print(data_[1])

    # 실시간주식호가
    # broker_ws = KoreaInvestmentWS(key, secret, "H0STASP0", "005930")
    # broker_ws.start()
    # for i in range(3):
    #    data = broker_ws.get()
    #    print(data)
    #
    # 실시간주식체결통보
    # broker_ws = KoreaInvestmentWS(key, secret, "H0STCNI0", "user_id")
    # broker_ws.start()
    # for i in range(3):
    #    data = broker_ws.get()
    #    print(data)

    #import pprint
    #broker = KoreaInvestment(key, secret, exchange="나스닥")
    #resp_ohlcv = broker.fetch_ohlcv("TSLA", '1d', to="")
    #print(len(resp_ohlcv['output2']))
    #pprint.pprint(resp_ohlcv['output2'][0])
    #pprint.pprint(resp_ohlcv['output2'][-1])
