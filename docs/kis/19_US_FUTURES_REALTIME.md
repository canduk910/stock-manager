# 해외선물옵션 실시간시세

**카테고리 코드**: `[해외선물옵션]실시간시세`  
**API 수**: 4개

> 출처: 한국투자증권 OpenAPI 전체 문서 (2026-05-08).  
> 자동 변환: `scripts/kis_excel_to_md.py`

---

## 목차

- [해외선물옵션 실시간체결가](#해외선물옵션-실시간체결가) — `POST` `/tryitout/HDFFF020` (실전 TR_ID: `HDFFF020`)
- [해외선물옵션 실시간호가](#해외선물옵션-실시간호가) — `POST` `/tryitout/HDFFF010` (실전 TR_ID: `HDFFF010`)
- [해외선물옵션 실시간주문내역통보](#해외선물옵션-실시간주문내역통보) — `POST` `/tryitout/HDFFF1C0` (실전 TR_ID: `HDFFF1C0`)
- [해외선물옵션 실시간체결내역통보](#해외선물옵션-실시간체결내역통보) — `POST` `/tryitout/HDFFF2C0` (실전 TR_ID: `HDFFF2C0`)

---

## 해외선물옵션 실시간체결가

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | WEBSOCKET |
| 메뉴 위치 | [해외선물옵션]실시간시세 |
| API 명 | 해외선물옵션 실시간체결가 |
| API ID | 실시간-017 |
| 실전 TR_ID | HDFFF020 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | POST |
| URL 명 | /tryitout/HDFFF020 |
| 실전 Domain | ws://ops.koreainvestment.com:21000 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 316 |

### 개요

※ CME, SGX 실시간시세 유료시세 신청 필수 (포럼 &gt; FAQ &gt; 해외선물옵션 API 유료시세 신청방법(CME, SGX 거래소))
- CME, SGX 거래소 실시간시세는 유료시세 신청 후 이용하시는 모든 계좌에 대해서 접근토큰발급 API 호출하셔야 하며, 
  접근토큰발급 이후 2시간 이내로 신청정보가 동기화되어 유료시세 수신이 가능해집니다.
- CME, SGX 거래소 종목은 유료시세 신청되어 있지 않으면 실시간시세 종목등록이 불가하며, 
  등록 시도 시 "SUBSCRIBE ERROR : mci send failed" 에러가 발생합니다.


(중요) 해외선물옵션시세 출력값을 해석하실 때 ffcode.mst(해외선물종목마스터 파일)에 있는 sCalcDesz(계산 소수점) 값을 활용하셔야 정확한 값을 받아오실 수 있습니다.

- ffcode.mst(해외선물종목마스터 파일) 다운로드 방법 2가지
  1) 한국투자증권 Github의 파이썬 샘플코드를 사용하여 mst 파일 다운로드 및 excel 파일로 정제   
     https://github.com/koreainvestment/open-trading-api/blob/main/stocks_info/overseas_future_code.py
   
  2) 혹은 포럼 - FAQ - 종목정보 다운로드 - 해외선물옵션 클릭하셔서 ffcode.mst(해외선물종목마스터 파일)을 다운로드 후
     Github의 헤더정보(https://github.com/koreainvestment/open-trading-api/blob/main/stocks_info/해외선물옵션정보.h)를 참고하여 해석

- 소수점 계산 시, ffcode.mst(해외선물종목마스터 파일)의 sCalcDesz(계산 소수점) 값 참고
  EX) ffcode.mst 파일의 sCalcDesz(계산 소수점) 값
       품목코드 6A 계산소수점 -4 → 시세 6882.5 수신 시 0.68825 로 해석
       품목코드 GC 계산소수점 -1 → 시세 19225 수신 시 1922.5 로 해석


[참고자료]

실시간시세(웹소켓) 파이썬 샘플코드는 한국투자증권 Github 참고 부탁드립니다.
https://github.com/koreainvestment/open-trading-api/blob/main/websocket/python/ws_domestic_overseas_all.py

실시간시세(웹소켓) API 사용방법에 대한 자세한 설명은 한국투자증권 Wikidocs 참고 부탁드립니다.
https://wikidocs.net/book/7847 (국내주식 업데이트 완료, 추후 해외주식·국내선물옵션 업데이트 예정)

종목코드 마스터파일 파이썬 정제코드는 한국투자증권 Github 참고 부탁드립니다.
https://github.com/koreainvestment/open-trading-api/tree/main/stocks_info

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| approval_key | 웹소켓접속키 | string | Y | 36 | 실시간 (웹소켓) 접속키 발급 API(/oauth2/Approval)를 사용하여 발급받은 웹소켓 접속키 |
| tr_type | 등록/해제 | string | Y | 1 | "1: 등록, 2:해제" |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 / P : 개인 |
| content-type | 컨텐츠타입 | string | Y | 20 | utf-8 |

**Request Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| tr_id | 거래ID | string | Y | 7 | HDFFF020 |
| tr_key | 종목코드 | string | Y | 6 | 종목코드<br><br>※ CME, SGX 실시간시세 유료시세 신청 필수 <br>"포럼 > FAQ > 해외선물옵션 API 유료시세 신청방법(CME, SGX 거래소)" |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| SERIES_CD | 종목코드 | string | Y | 32 | '각 항목사이에는 구분자로 ^ 사용,<br>모든 데이터타입은 String으로 변환되어 push 처리됨' |
| BSNS_DATE | 영업일자 | string | Y | 8 |  |
| MRKT_OPEN_DATE | 장개시일자 | string | Y | 8 |  |
| MRKT_OPEN_TIME | 장개시시각 | string | Y | 6 |  |
| MRKT_CLOSE_DATE | 장종료일자 | string | Y | 8 |  |
| MRKT_CLOSE_TIME | 장종료시각 | string | Y | 6 |  |
| PREV_PRICE | 전일종가 | string | Y | 15 | 전일종가, 체결가격, 전일대비가, 시가, 고가, 저가<br>※ ffcode.mst(해외선물종목마스터 파일)의 sCalcDesz(계산 소수점) 값 참고 |
| RECV_DATE | 수신일자 | string | Y | 8 |  |
| RECV_TIME | 수신시각 | string | Y | 6 | 수신시각(recv_time) = 실제 체결시각 |
| ACTIVE_FLAG | 본장_전산장구분 | string | Y | 1 |  |
| LAST_PRICE | 체결가격 | string | Y | 15 |  |
| LAST_QNTT | 체결수량 | string | Y | 10 |  |
| PREV_DIFF_PRICE | 전일대비가 | string | Y | 15 |  |
| PREV_DIFF_RATE | 등락률 | string | Y | 10 |  |
| OPEN_PRICE | 시가 | string | Y | 15 |  |
| HIGH_PRICE | 고가 | string | Y | 15 |  |
| LOW_PRICE | 저가 | string | Y | 15 |  |
| VOL | 누적거래량 | string | Y | 10 |  |
| PREV_SIGN | 전일대비부호 | string | Y | 1 |  |
| QUOTSIGN | 체결구분 | string | Y | 1 | 2:매수체결 5:매도체결 |
| RECV_TIME2 | 수신시각2 만분의일초 | string | Y | 4 |  |
| PSTTL_PRICE | 전일정산가 | string | Y | 15 |  |
| PSTTL_SIGN | 전일정산가대비 | string | Y | 1 |  |
| PSTTL_DIFF_PRICE | 전일정산가대비가격 | string | Y | 15 |  |
| PSTTL_DIFF_RATE | 전일정산가대비율 | string | Y | 10 |  |

### Example

**Request Example (Python)**

```

```

**Response Example**

```

```

---

## 해외선물옵션 실시간호가

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | WEBSOCKET |
| 메뉴 위치 | [해외선물옵션]실시간시세 |
| API 명 | 해외선물옵션 실시간호가 |
| API ID | 실시간-018 |
| 실전 TR_ID | HDFFF010 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | POST |
| URL 명 | /tryitout/HDFFF010 |
| 실전 Domain | ws://ops.koreainvestment.com:21000 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 317 |

### 개요

※ CME, SGX 실시간시세 유료시세 신청 필수 (포럼 &gt; FAQ &gt; 해외선물옵션 API 유료시세 신청방법(CME, SGX 거래소))
- CME, SGX 거래소 실시간시세는 유료시세 신청 후 이용하시는 모든 계좌에 대해서 접근토큰발급 API 호출하셔야 하며, 
  접근토큰발급 이후 2시간 이내로 신청정보가 동기화되어 유료시세 수신이 가능해집니다.
- CME, SGX 거래소 종목은 유료시세 신청되어 있지 않으면 실시간시세 종목등록이 불가하며, 
  등록 시도 시 "SUBSCRIBE ERROR : mci send failed" 에러가 발생합니다.

(중요) 해외선물옵션시세 출력값을 해석하실 때 ffcode.mst(해외선물종목마스터 파일)에 있는 sCalcDesz(계산 소수점) 값을 활용하셔야 정확한 값을 받아오실 수 있습니다.

- ffcode.mst(해외선물종목마스터 파일) 다운로드 방법 2가지
  1) 한국투자증권 Github의 파이썬 샘플코드를 사용하여 mst 파일 다운로드 및 excel 파일로 정제   
     https://github.com/koreainvestment/open-trading-api/blob/main/stocks_info/overseas_future_code.py
   
  2) 혹은 포럼 - FAQ - 종목정보 다운로드 - 해외선물옵션 클릭하셔서 ffcode.mst(해외선물종목마스터 파일)을 다운로드 후
     Github의 헤더정보(https://github.com/koreainvestment/open-trading-api/blob/main/stocks_info/해외선물옵션정보.h)를 참고하여 해석

- 소수점 계산 시, ffcode.mst(해외선물종목마스터 파일)의 sCalcDesz(계산 소수점) 값 참고
  EX) ffcode.mst 파일의 sCalcDesz(계산 소수점) 값
       품목코드 6A 계산소수점 -4 → 시세 6882.5 수신 시 0.68825 로 해석
       품목코드 GC 계산소수점 -1 → 시세 19225 수신 시 1922.5 로 해석


[참고자료]

실시간시세(웹소켓) 파이썬 샘플코드는 한국투자증권 Github 참고 부탁드립니다.
https://github.com/koreainvestment/open-trading-api/blob/main/websocket/python/ws_domestic_overseas_all.py

실시간시세(웹소켓) API 사용방법에 대한 자세한 설명은 한국투자증권 Wikidocs 참고 부탁드립니다.
https://wikidocs.net/book/7847 (국내주식 업데이트 완료, 추후 해외주식·국내선물옵션 업데이트 예정)

종목코드 마스터파일 파이썬 정제코드는 한국투자증권 Github 참고 부탁드립니다.
https://github.com/koreainvestment/open-trading-api/tree/main/stocks_info

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| approval_key | 웹소켓접속키 | string | Y | 36 | 실시간 (웹소켓) 접속키 발급 API(/oauth2/Approval)를 사용하여 발급받은 웹소켓 접속키 |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 / P : 개인 |
| tr_type | 등록/해제 | string | Y | 1 | "1: 등록, 2:해제" |
| content-type | 컨텐츠타입 | string | Y | 20 | utf-8 |

**Request Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| tr_id | 거래ID | string | Y | 7 | HDFFF010 |
| tr_key | 종목코드 | string | Y | 6 | 종목코드<br><br>※ CME, SGX 실시간시세 유료시세 신청 필수 <br>"포럼 > FAQ > 해외선물옵션 API 유료시세 신청방법(CME, SGX 거래소)" |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| SERIES_CD | 종목코드 | object | Y | 32 | '각 항목사이에는 구분자로 ^ 사용,<br>모든 데이터타입은 String으로 변환되어 push 처리됨' |
| RECV_DATE | 수신일자 | string | Y | 8 |  |
| RECV_TIME | 수신시각 | string | Y | 12 |  |
| PREV_PRICE | 전일종가 | string | Y | 15 | 전일종가, 매수1호가~매도5호가<br>※ ffcode.mst(해외선물종목마스터 파일)의 sCalcDesz(계산 소수점) 값 참고 |
| BID_QNTT_1 | 매수1수량 | string | Y | 10 |  |
| BID_NUM_1 | 매수1번호 | string | Y | 10 |  |
| BID_PRICE_1 | 매수1호가 | string | Y | 15 |  |
| ASK_QNTT_1 | 매도1수량 | string | Y | 10 |  |
| ASK_NUM_1 | 매도1번호 | string | Y | 10 |  |
| ASK_PRICE_1 | 매도1호가 | string | Y | 15 |  |
| BID_QNTT_2 | 매수2수량 | string | Y | 10 |  |
| BID_NUM_2 | 매수2번호 | string | Y | 10 |  |
| BID_PRICE_2 | 매수2호가 | string | Y | 15 |  |
| ASK_QNTT_2 | 매도2수량 | string | Y | 10 |  |
| ASK_NUM_2 | 매도2번호 | string | Y | 10 |  |
| ASK_PRICE_2 | 매도2호가 | string | Y | 15 |  |
| BID_QNTT_3 | 매수3수량 | string | Y | 10 |  |
| BID_NUM_3 | 매수3번호 | string | Y | 10 |  |
| BID_PRICE_3 | 매수3호가 | string | Y | 15 |  |
| ASK_QNTT_3 | 매도3수량 | string | Y | 10 |  |
| ASK_NUM_3 | 매도3번호 | string | Y | 10 |  |
| ASK_PRICE_3 | 매도3호가 | string | Y | 15 |  |
| BID_QNTT_4 | 매수4수량 | string | Y | 10 |  |
| BID_NUM_4 | 매수4번호 | string | Y | 10 |  |
| BID_PRICE_4 | 매수4호가 | string | Y | 15 |  |
| ASK_QNTT_4 | 매도4수량 | string | Y | 10 |  |
| ASK_NUM_4 | 매도4번호 | string | Y | 10 |  |
| ASK_PRICE_4 | 매도4호가 | string | Y | 15 |  |
| BID_QNTT_5 | 매수5수량 | string | Y | 10 |  |
| BID_NUM_5 | 매수5번호 | string | Y | 10 |  |
| BID_PRICE_5 | 매수5호가 | string | Y | 15 |  |
| ASK_QNTT_5 | 매도5수량 | string | Y | 10 |  |
| ASK_NUM_5 | 매도5번호 | string | Y | 10 |  |
| ASK_PRICE_5 | 매도5호가 | string | Y | 15 |  |
| STTL_PRICE | 전일정산가 | string | Y | 15 |  |

### Example

**Request Example (Python)**

```

```

**Response Example**

```

```

---

## 해외선물옵션 실시간주문내역통보

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | WEBSOCKET |
| 메뉴 위치 | [해외선물옵션]실시간시세 |
| API 명 | 해외선물옵션 실시간주문내역통보 |
| API ID | 실시간-019 |
| 실전 TR_ID | HDFFF1C0 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | POST |
| URL 명 | /tryitout/HDFFF1C0 |
| 실전 Domain | ws://ops.koreainvestment.com:21000 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 318 |

### 개요

[참고자료]

실시간시세(웹소켓) 파이썬 샘플코드는 한국투자증권 Github 참고 부탁드립니다.
https://github.com/koreainvestment/open-trading-api/blob/main/websocket/python/ws_domestic_overseas_all.py

실시간시세(웹소켓) API 사용방법에 대한 자세한 설명은 한국투자증권 Wikidocs 참고 부탁드립니다.
https://wikidocs.net/book/7847 (국내주식 업데이트 완료, 추후 해외주식·국내선물옵션 업데이트 예정)

종목코드 마스터파일 파이썬 정제코드는 한국투자증권 Github 참고 부탁드립니다.
https://github.com/koreainvestment/open-trading-api/tree/main/stocks_info

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| approval_key | 웹소켓접속키 | string | Y | 36 | 실시간 (웹소켓) 접속키 발급 API(/oauth2/Approval)를 사용하여 발급받은 웹소켓 접속키 |
| tr_type | 등록/해제 | string | Y | 1 | "1: 등록, 2:해제" |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 / P : 개인 |
| content-type | 컨텐츠타입 | string | Y | 20 | utf-8 |

**Request Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| tr_id | 거래ID | string | Y | 7 | HDFFF1C0 |
| tr_key | HTSID | string | Y | 8 | HTSID |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| USER_ID | 유저ID | object | Y | 8 | '각 항목사이에는 구분자로 ^ 사용,<br>모든 데이터타입은 String으로 변환되어 push 처리됨' |
| ACCT_NO | 계좌번호 | string | Y | 10 |  |
| ORD_DT | 주문일자 | string | Y | 8 |  |
| ODNO | 주문번호 | string | Y | 10 |  |
| ORGN_ORD_DT | 원주문일자 | string | Y | 8 |  |
| ORGN_ODNO | 원주문번호 | string | Y | 10 |  |
| SERIES | 종목명 | string | Y | 32 |  |
| RVSE_CNCL_DVSN_CD | 정정취소구분코드 | string | Y | 2 | 해당없음 : 00 , 정정 : 01 , 취소 : 02 |
| SLL_BUY_DVSN_CD | 매도매수구분코드 | string | Y | 2 | 01 : 매도,  02 : 매수 |
| CPLX_ORD_DVSN_CD | 복합주문구분코드 | string | Y | 1 | 0 (hedge청산만 이용) |
| PRCE_TP | 가격구분코드 | string | Y | 1 | 1:Limit, 2:Market, 3:Stop(Stop가격시 시장가) |
| FM_EXCG_RCIT_DVSN_CD | FM거래소접수구분코드 | string | Y | 2 | 01:접수전, 02:응답, 03:거부 |
| ORD_QTY | 주문수량 | string | Y | 18 |  |
| FM_LMT_PRIC | FMLIMIT가격 | string | Y | 21 |  |
| FM_STOP_ORD_PRIC | FMSTOP주문가격 | string | Y | 21 |  |
| TOT_CCLD_QTY | 총체결수량 | string | Y | 18 |  |
| TOT_CCLD_UV | 총체결단가 | string | Y | 21 |  |
| ORD_REMQ | 잔량 | string | Y | 21 |  |
| FM_ORD_GRP_DT | FM주문그룹일자 | string | Y | 8 | 주문일자(ORD_DT)와 동일 |
| ORD_GRP_STNO | 주문그룹번호 | string | Y | 12 |  |
| ORD_DTL_DTIME | 주문상세일시 | string | Y | 17 |  |
| OPRT_DTL_DTIME | 조작상세일시 | string | Y | 17 |  |
| WORK_EMPL | 주문자 | string | Y | 8 |  |
| CRCY_CD | 통화코드 | string | Y | 3 |  |
| LQD_YN | 청산여부(Y/N) | string | Y | 1 |  |
| LQD_LMT_PRIC | 청산LIMIT가격 | string | Y | 21 |  |
| LQD_STOP_PRIC | 청산STOP가격 | string | Y | 21 |  |
| TRD_COND | 체결조건코드 | string | Y | 1 |  |
| TERM_ORD_VALD_DTIME | 기간주문유효상세일시 | string | Y | 17 |  |
| SPEC_TP | 계좌청산유형구분코드 | string | Y | 1 |  |
| ECIS_RSVN_ORD_YN | 행사예약주문여부 | string | Y | 1 |  |
| FUOP_ITEM_DVSN_CD | 선물옵션종목구분코드 | string | Y | 2 |  |
| AUTO_ORD_DVSN_CD | 자동주문 전략구분 | string | Y | 2 |  |

### Example

**Request Example (Python)**

```

```

**Response Example**

```

```

---

## 해외선물옵션 실시간체결내역통보

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | WEBSOCKET |
| 메뉴 위치 | [해외선물옵션]실시간시세 |
| API 명 | 해외선물옵션 실시간체결내역통보 |
| API ID | 실시간-020 |
| 실전 TR_ID | HDFFF2C0 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | POST |
| URL 명 | /tryitout/HDFFF2C0 |
| 실전 Domain | ws://ops.koreainvestment.com:21000 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 319 |

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| approval_key | 웹소켓 접속키 | string | Y | 36 | 실시간 (웹소켓) 접속키 발급 API(/oauth2/Approval)를 사용하여 발급받은 웹소켓 접속키 |
| tr_type | 등록/해제 | string | Y | 1 | "1: 등록, 2:해제" |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 / P : 개인 |
| content-type | 컨텐츠타입 | string | Y | 20 | utf-8 |

**Request Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| tr_id | 거래ID | string | Y | 7 | HDFFF2C0 |
| tr_key | HTSID | string | Y | 8 | HTSID |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| USER_ID | 유저ID | object | Y | 8 | '각 항목사이에는 구분자로 ^ 사용,<br>모든 데이터타입은 String으로 변환되어 push 처리됨' |
| ACCT_NO | 계좌번호 | string | Y | 10 |  |
| ORD_DT | 주문일자 | string | Y | 8 |  |
| ODNO | 주문번호 | string | Y | 10 |  |
| ORGN_ORD_DT | 원주문일자 | string | Y | 8 |  |
| ORGN_ODNO | 원주문번호 | string | Y | 10 |  |
| SERIES | 종목명 | string | Y | 32 |  |
| RVSE_CNCL_DVSN_CD | 정정취소구분코드 | string | Y | 2 | 해당없음 : 00 , 정정 : 01 , 취소 : 02 |
| SLL_BUY_DVSN_CD | 매도매수구분코드 | string | Y | 2 | 01 : 매도,  02 : 매수 |
| CPLX_ORD_DVSN_CD | 복합주문구분코드 | string | Y | 1 | 0 (hedge청산만 이용) |
| PRCE_TP | 가격구분코드 | string | Y | 1 |  |
| FM_EXCG_RCIT_DVSN_CD | FM거래소접수구분코드 | string | Y | 2 |  |
| ORD_QTY | 주문수량 | string | Y | 18 |  |
| FM_LMT_PRIC | FMLIMIT가격 | string | Y | 21 |  |
| FM_STOP_ORD_PRIC | FMSTOP주문가격 | string | Y | 21 |  |
| TOT_CCLD_QTY | 총체결수량 | string | Y | 18 | 동일한 주문건에 대한 누적된 체결수량 (하나의 주문건에 여러건의 체결내역 발생) |
| TOT_CCLD_UV | 총체결단가 | string | Y | 21 |  |
| ORD_REMQ | 잔량 | string | Y | 21 |  |
| FM_ORD_GRP_DT | FM주문그룹일자 | string | Y | 8 |  |
| ORD_GRP_STNO | 주문그룹번호 | string | Y | 12 |  |
| ORD_DTL_DTIME | 주문상세일시 | string | Y | 17 |  |
| OPRT_DTL_DTIME | 조작상세일시 | string | Y | 17 |  |
| WORK_EMPL | 주문자 | string | Y | 8 |  |
| CCLD_DT | 체결일자 | string | Y | 8 |  |
| CCNO | 체결번호 | string | Y | 11 |  |
| API_CCNO | API 체결번호 | string | Y | 20 |  |
| CCLD_QTY | 체결수량 | string | Y | 18 | 매 체결 단위 체결수량임 (여러건 체결내역 누적 체결수량인 총체결수량과 다름) |
| FM_CCLD_PRIC | FM체결가격 | string | Y | 21 |  |
| CRCY_CD | 통화코드 | string | Y | 3 |  |
| TRST_FEE | 위탁수수료 | string | Y | 21 |  |
| ORD_MDIA_ONLINE_YN | 주문매체온라인여부 | string | Y | 1 |  |
| FM_CCLD_AMT | FM체결금액 | string | Y | 21 |  |
| FUOP_ITEM_DVSN_CD | 선물옵션종목구분코드 | string | Y | 2 |  |

### Example

**Request Example (Python)**

```

```

**Response Example**

```

```

---
