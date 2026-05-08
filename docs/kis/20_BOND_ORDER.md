# 장내채권 주문/계좌

**카테고리 코드**: `[장내채권] 주문/계좌`  
**API 수**: 7개

> 출처: 한국투자증권 OpenAPI 전체 문서 (2026-05-08).  
> 자동 변환: `scripts/kis_excel_to_md.py`

---

## 목차

- [장내채권 매수주문](#장내채권-매수주문) — `POST` `/uapi/domestic-bond/v1/trading/buy` (실전 TR_ID: `TTTC0952U`)
- [장내채권 매도주문](#장내채권-매도주문) — `POST` `/uapi/domestic-bond/v1/trading/sell` (실전 TR_ID: `TTTC0958U`)
- [장내채권 정정취소주문](#장내채권-정정취소주문) — `POST` `/uapi/domestic-bond/v1/trading/order-rvsecncl` (실전 TR_ID: `TTTC0953U`)
- [채권정정취소가능주문조회](#채권정정취소가능주문조회) — `GET` `/uapi/domestic-bond/v1/trading/inquire-psbl-rvsecncl` (실전 TR_ID: `CTSC8035R`)
- [장내채권 주문체결내역](#장내채권-주문체결내역) — `GET` `/uapi/domestic-bond/v1/trading/inquire-daily-ccld` (실전 TR_ID: `CTSC8013R`)
- [장내채권 잔고조회](#장내채권-잔고조회) — `GET` `/uapi/domestic-bond/v1/trading/inquire-balance` (실전 TR_ID: `CTSC8407R`)
- [장내채권 매수가능조회](#장내채권-매수가능조회) — `GET` `/uapi/domestic-bond/v1/trading/inquire-psbl-order` (실전 TR_ID: `TTTC8910R`)

---

## 장내채권 매수주문

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 주문/계좌 |
| API 명 | 장내채권 매수주문 |
| API ID | 국내주식-124 |
| 실전 TR_ID | TTTC0952U |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | POST |
| URL 명 | /uapi/domestic-bond/v1/trading/buy |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 320 |

### 개요

장내채권 매수주문 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0978] 장내채권주문 '채권매수' 탭의 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | TTTC0952U |
| tr_cont | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 <br>P : 개인 |
| seq_no | 일련번호 | string | N | 2 | [법인 필수] 001 |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| CANO | 종합계좌번호 | string | Y | 8 |  |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 |  |
| PDNO | 상품번호 | string | Y | 12 |  |
| ORD_QTY2 | 주문수량2 | string | Y | 19 | SAMT_MKET_PTCI_YN(소액시장참여여부) : N(일반시장) 입력 시 10단위 입력 |
| BOND_ORD_UNPR | 채권주문단가 | string | Y | 182 |  |
| SAMT_MKET_PTCI_YN | 소액시장참여여부 | string | Y | 1 | N: 일반시장, Y: 소액시장 |
| BOND_RTL_MKET_YN | 채권소매시장여부 | string | Y | 1 | Y, N |
| IDCR_STFNO | 유치자직원번호 | string | Y | 6 | 공백 |
| MGCO_APTM_ODNO | 운용사지정주문번호 | string | Y | 12 | 공백 |
| ORD_SVR_DVSN_CD | 주문서버구분코드 | string | Y | 1 | Unique key(0) |
| CTAC_TLNO | 연락전화번호 | string | Y | 20 |  |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| rt_cd | 성공 실패 여부 | string | Y | 1 |  |
| msg_cd | 응답코드 | string | Y | 8 |  |
| msg1 | 응답메세지 | string | Y | 80 |  |
| output | 응답상세 | object | Y |  |  |
| krx_fwdg_ord_orgno | 한국거래소전송주문조직번호 | string | Y | 5 |  |
| odno | 주문번호 | string | Y | 10 |  |
| ord_tmd | 주문시각 | string | Y | 6 |  |

### Example

**Request Example (Python)**

```
{
    "CANO": "12345678",
    "ACNT_PRDT_CD": "01",
    "PDNO": "KR6095572D81",
    "ORD_QTY2": "1",
    "BOND_ORD_UNPR":"10000",
    "SAMT_MKET_PTCI_YN":"N",
    "BOND_RTL_MKET_YN":"N",
    "IDCR_STFNO":"",
    "MGCO_APTM_ODNO":"",
    "ORD_SVR_DVSN_CD":"0",
    "CTAC_TLNO":""
}
```

**Response Example**

```
{
    "rt_cd": "0",
    "msg_cd": "APBK0013",
    "msg1": "주문 전송 완료 되었습니다.",
    "output": {
        "KRX_FWDG_ORD_ORGNO": "01790",
        "ODNO": "0000015401",
        "ORD_TMD": "104258"
    }
}
```

---

## 장내채권 매도주문

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 주문/계좌 |
| API 명 | 장내채권 매도주문 |
| API ID | 국내주식-123 |
| 실전 TR_ID | TTTC0958U |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | POST |
| URL 명 | /uapi/domestic-bond/v1/trading/sell |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 321 |

### 개요

장내채권 매도주문 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0978] 장내채권주문 '채권매도' 탭의 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | TTTC0958U |
| tr_cont | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 <br>P : 개인 |
| seq_no | 일련번호 | string | N | 2 | [법인 필수] 001 |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| CANO | 종합계좌번호 | string | Y | 8 |  |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 |  |
| ORD_DVSN | 주문구분 | string | Y | 2 | '01: 종목별 (매수일자, 매수순번 공백입력) <br>02: 일자별 (매수순번: 0 입력) <br>03: 체결가별 ' |
| PDNO | 상품번호 | string | Y | 12 |  |
| ORD_QTY2 | 주문수량2 | string | Y | 4 | SAMT_MKET_PTCI_YN(소액시장참여여부) : N(일반시장) 입력 시 10단위 입력 |
| BOND_ORD_UNPR | 주문단가 | string | Y | 8 |  |
| SPRX_YN | 분리과세여부 | string | Y | 1 | N: 종합과세, Y:분리과세 |
| BUY_DT | 매수일자 | string | Y | 8 | (잔고조회 참조) |
| BUY_SEQ | 매수순번 | string | Y | 10 | (잔고조회 참조) |
| SAMT_MKET_PTCI_YN | 소액시장참여여부 | string | Y | 1 | N: 일반시장, Y: 소액시장 |
| SLL_AGCO_OPPS_SLL_YN | 매도대행사반대매도여부 | string | Y | 1 | N |
| BOND_RTL_MKET_YN | 채권소매시장여부 | string | Y | 1 | N |
| MGCO_APTM_ODNO | 운용사지정주문번호 | string | Y | 12 | 공백 |
| ORD_SVR_DVSN_CD | 주문서버구분코드 | string | Y | 1 | Unique key(0) |
| CTAC_TLNO | 연락전화번호 | string | Y | 20 |  |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| rt_cd | 성공 실패 여부 | string | Y | 1 |  |
| msg_cd | 응답코드 | string | Y | 8 |  |
| msg1 | 응답메세지 | string | Y | 80 |  |
| output | 응답상세 | object | Y |  |  |
| krx_fwdg_ord_orgno | 한국거래소전송주문조직번호 | string | Y | 5 |  |
| odno | 주문번호 | string | Y | 10 |  |
| ord_tmd | 주문시각 | string | Y | 6 |  |

### Example

**Request Example (Python)**

```
{
    "CANO": "12345678",
    "ACNT_PRDT_CD": "01",
    "ORD_DVSN":"01",
    "PDNO":"KR6095572D81",
    "ORD_QTY2":"1",
    "BOND_ORD_UNPR":"10450",
    "SPRX_YN":"N",
    "BUY_DT":"",
    "BUY_SEQ":"",
    "SAMT_MKET_PTCI_YN":"N",
    "SLL_AGCO_OPPS_SLL_YN":"N",
    "BOND_RTL_MKET_YN":"N",
    "MGCO_APTM_ODNO":"",
    "ORD_SVR_DVSN_CD":"0",
    "CTAC_TLNO":""
}
```

**Response Example**

```
{
    "rt_cd": "0",
    "msg_cd": "APBK0013",
    "msg1": "주문 전송 완료 되었습니다.",
    "output": {
        "KRX_FWDG_ORD_ORGNO": "01790",
        "ODNO": "0000015402",
        "ORD_TMD": "104347"
    }
}
```

---

## 장내채권 정정취소주문

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 주문/계좌 |
| API 명 | 장내채권 정정취소주문 |
| API ID | 국내주식-125 |
| 실전 TR_ID | TTTC0953U |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | POST |
| URL 명 | /uapi/domestic-bond/v1/trading/order-rvsecncl |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 322 |

### 개요

장내채권 정정취소주문 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0978] 장내채권주문 '채권정정/취소' 탭의 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | TTTC0953U |
| tr_cont | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 <br>P : 개인 |
| seq_no | 일련번호 | string | N | 2 | [법인 필수] 001 |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| CANO | 종합계좌번호 | string | Y | 8 | - |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | - |
| PDNO | 상품번호 | string | Y | 12 | - |
| ORGN_ODNO | 원주문번호 | string | Y | 10 | - |
| ORD_QTY2 | 주문수량2 | string | Y | 19 | 원주문이 일반시장 주문일 시 10단위 입력 |
| BOND_ORD_UNPR | 채권주문단가 | string | Y | 182 | - |
| QTY_ALL_ORD_YN | 잔량전부주문여부 | string | Y | 1 | Y: 잔량전부(주문수량 입력안함), |
| RVSE_CNCL_DVSN_CD | 정정취소구분코드 | string | Y | 2 | 01: 정정, 02: 취소 |
| MGCO_APTM_ODNO | 운용사지정주문번호 | string | Y | 12 | 공백 |
| ORD_SVR_DVSN_CD | 주문서버구분코드 | string | Y | 1 | Unique key(0) |
| CTAC_TLNO | 연락전화번호 | string | Y | 20 | - |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| rt_cd | 성공 실패 여부 | string | Y | 1 |  |
| msg_cd | 응답코드 | string | Y | 8 |  |
| msg1 | 응답메세지 | string | Y | 80 |  |
| output | 응답상세 | object | Y |  |  |
| krx_fwdg_ord_orgno | 한국거래소전송주문조직번호 | string | Y | 5 |  |
| odno | 주문번호 | string | Y | 10 |  |
| ord_tmd | 주문시각 | string | Y | 6 |  |

### Example

**Request Example (Python)**

```
{
    "CANO": "12345678",
    "ACNT_PRDT_CD": "01",
    "PDNO": "KR6095572D81",
    "ORGN_ODNO": "0000015402",
    "ORD_QTY2": "2",
    "BOND_ORD_UNPR": "10460",
    "QTY_ALL_ORD_YN": "Y",
    "RVSE_CNCL_DVSN_CD": "01",
    "MGCO_APTM_ODNO": "",
    "ORD_SVR_DVSN_CD": "0",
    "CTAC_TLNO": ""
}
```

**Response Example**

```
{
    "rt_cd": "0",
    "msg_cd": "APBK0013",
    "msg1": "주문 전송 완료 되었습니다.",
    "output": {
        "KRX_FWDG_ORD_ORGNO": "01790",
        "ODNO": "0000015403",
        "ORD_TMD": "104448"
    }
}
```

---

## 채권정정취소가능주문조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 주문/계좌 |
| API 명 | 채권정정취소가능주문조회 |
| API ID | 국내주식-126 |
| 실전 TR_ID | CTSC8035R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/trading/inquire-psbl-rvsecncl |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 323 |

### 개요

채권정정취소가능주문조회 API입니다. 
정정취소가능한 채권주문 목록을 확인할 수 있습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | CTSC8035R |
| tr_cont | 연속 거래 여부 | string | N | 1 | 공백 : 초기 조회<br>N : 다음 데이터 조회 (output header의 tr_cont가 M일 경우) |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 <br>P : 개인 |
| seq_no | 일련번호 | string | N | 2 | [법인 필수] 001 |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Query Parameter**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| CANO | 종합계좌번호 | string | Y | 8 |  |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 |  |
| ORD_DT | 주문일자 | string | Y | 8 |  |
| ODNO | 주문번호 | string | Y | 10 |  |
| CTX_AREA_FK200 | 연속조회검색조건200 | string | Y | 200 |  |
| CTX_AREA_NK200 | 연속조회키200 | string | Y | 200 |  |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| tr_id | 거래ID | string | Y | 13 | 요청한 tr_id |
| tr_cont | 연속 거래 여부 | string | N | 1 | F or M : 다음 데이터 있음<br>D or E : 마지막 데이터 |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| rt_cd | 성공 실패 여부 | string | Y | 1 |  |
| msg_cd | 응답코드 | string | Y | 8 |  |
| msg1 | 응답메세지 | string | Y | 80 |  |
| output | 응답상세 | object array | Y |  | array |
| odno | 주문번호 | string | Y | 10 |  |
| pdno | 상품번호 | string | Y | 12 |  |
| rvse_cncl_dvsn_name | 정정취소구분명 | string | Y | 60 |  |
| ord_qty | 주문수량 | string | Y | 10 |  |
| bond_ord_unpr | 채권주문단가 | string | Y | 182 |  |
| ord_tmd | 주문시각 | string | Y | 6 |  |
| tot_ccld_qty | 총체결수량 | string | Y | 10 |  |
| tot_ccld_amt | 총체결금액 | string | Y | 19 |  |
| ord_psbl_qty | 주문가능수량 | string | Y | 10 |  |
| orgn_odno | 원주문번호 | string | Y | 10 |  |
| sll_buy_dvsn_cd | 매도매수구분코드 | string | Y | 2 |  |
| ord_dvsn_cd | 주문구분코드 | string | Y | 2 |  |
| mgco_aptm_odno | 운용사지정주문번호 | string | Y | 12 |  |
| samt_mket_ptci_yn | 소액시장참여여부 | string | Y | 1 |  |
| prdt_abrv_name | 상품약어명 | string | Y | 60 |  |

### Example

**Request Example (Python)**

```
CANO:12345678
ACNT_PRDT_CD:01
ORD_DT:
ODNO:
CTX_AREA_FK200:
CTX_AREA_NK200:
```

**Response Example**

```
{
    "ctx_area_fk200": "0!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null                                                                                                                   ",
    "ctx_area_nk200": "                                                                                                                                                                                                        ",
    "output": [
        {
            "odno": "0000015401",
            "pdno": "KR6095572D81",
            "rvse_cncl_dvsn_name": "현금매수",
            "ord_qty": "1",
            "bond_ord_unpr": "10000.00",
            "ord_tmd": "104258",
            "tot_ccld_qty": "0",
            "tot_ccld_amt": "0",
            "ord_psbl_qty": "1",
            "orgn_odno": "",
            "sll_buy_dvsn_cd": "02",
            "ord_dvsn_cd": "01",
            "mgco_aptm_odno": "",
            "samt_mket_ptci_yn": "N",
            "prdt_abrv_name": "AJ네트웍스63-2"
        },
        {
            "odno": "0000015403",
            "pdno": "KR6095572D81",
            "rvse_cncl_dvsn_name": "현금매도",
            "ord_qty": "1",
            "bond_ord_unpr": "10460.00",
            "ord_tmd": "104448",
            "tot_ccld_qty": "0",
            "tot_ccld_amt": "0",
            "ord_psbl_qty": "1",
            "orgn_odno": "0000015402",
            "sll_buy_dvsn_cd": "01",
            "ord_dvsn_cd": "01",
            "mgco_aptm_odno": "",
            "samt_mket_ptci_yn": "N",
            "prdt_abrv_name": "AJ네트웍스63-2"
        }
    ],
    "rt_cd": "0",
    "msg_cd": "KIOK0460",
    "msg1": "조회 되었습니다. (마지막 자료)                                                  "
}
```

---

## 장내채권 주문체결내역

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 주문/계좌 |
| API 명 | 장내채권 주문체결내역 |
| API ID | 국내주식-127 |
| 실전 TR_ID | CTSC8013R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/trading/inquire-daily-ccld |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 324 |

### 개요

장내채권 주문체결내역 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0978] 장내채권주문 '채권주문체결' 탭의 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | CTSC8013R |
| tr_cont | 연속 거래 여부 | string | N | 1 | 공백 : 초기 조회<br>N : 다음 데이터 조회 (output header의 tr_cont가 M일 경우) |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 <br>P : 개인 |
| seq_no | 일련번호 | string | N | 2 | [법인 필수] 001 |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Query Parameter**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| CANO | 종합계좌번호 | string | Y | 8 | 종합계좌번호 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | 계좌상품코드 |
| INQR_STRT_DT | 조회시작일자 | string | Y | 8 | 일자 ~ (1주일 이내) |
| INQR_END_DT | 조회종료일자 | string | Y | 8 | ~ 일자 (조회 당일) |
| SLL_BUY_DVSN_CD | 매도매수구분코드 | string | Y | 2 | %(전체), 01(매도), 02(매수) |
| SORT_SQN_DVSN | 정렬순서구분 | string | Y | 2 | 01(주문순서), 02(주문역순) |
| PDNO | 상품번호 | string | Y | 12 |  |
| NCCS_YN | 미체결여부 | string | Y | 1 | N(전체), C(체결), Y(미체결) |
| CTX_AREA_NK200 | 연속조회키200 | string | Y | 200 |  |
| CTX_AREA_FK200 | 연속조회검색조건200 | string | Y | 200 |  |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| tr_id | 거래ID | string | Y | 13 | 요청한 tr_id |
| tr_cont | 연속 거래 여부 | string | N | 1 | F or M : 다음 데이터 있음<br>D or E : 마지막 데이터 |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| rt_cd | 성공 실패 여부 | string | Y | 1 |  |
| msg_cd | 응답코드 | string | Y | 8 |  |
| msg1 | 응답메세지 | string | Y | 80 |  |
| output1 | 응답상세 | object array | Y |  |  |
| tot_ord_qty | 총주문수량 | string | Y | 10 |  |
| tot_ccld_qty_smtl | 총체결수량합계 | string | Y | 19 |  |
| tot_bond_ccld_avg_unpr | 총채권체결평균단가 | string | Y | 182 |  |
| tot_ccld_amt_smtl | 총체결금액합계 | string | Y | 19 |  |
| output2 | 응답상세 | object | Y |  | array |
| ord_dt | 주문일자 | string | Y | 8 |  |
| odno | 주문번호 | string | Y | 10 |  |
| orgn_odno | 원주문번호 | string | Y | 10 |  |
| ord_dvsn_name | 주문구분명 | string | Y | 60 |  |
| sll_buy_dvsn_cd_name | 매도매수구분코드명 | string | Y | 60 |  |
| shtn_pdno | 단축상품번호 | string | Y | 12 |  |
| prdt_abrv_name | 상품약어명 | string | Y | 60 |  |
| ord_qty | 주문수량 | string | Y | 10 |  |
| bond_ord_unpr | 채권주문단가 | string | Y | 182 |  |
| ord_tmd | 주문시각 | string | Y | 6 |  |
| tot_ccld_qty | 총체결수량 | string | Y | 10 |  |
| bond_avg_unpr | 채권평균단가 | string | Y | 182 |  |
| tot_ccld_amt | 총체결금액 | string | Y | 19 |  |
| loan_dt | 대출일자 | string | Y | 8 |  |
| buy_dt | 매수일자 | string | Y | 8 |  |
| samt_mket_ptci_yn_name | 소액시장참여여부명 | string | Y | 10 |  |
| sprx_psbl_yn_ifom | 분리과세가능여부알림 | string | Y | 60 |  |
| ord_mdia_dvsn_name | 주문매체구분명 | string | Y | 60 |  |
| sll_buy_dvsn_cd | 매도매수구분코드 | string | Y | 2 |  |
| nccs_qty | 미체결수량 | string | Y | 10 |  |
| ord_gno_brno | 주문채번지점번호 | string | Y | 5 |  |

### Example

**Request Example (Python)**

```
CANO:12345678
ACNT_PRDT_CD:01
INQR_STRT_DT:20240401
INQR_END_DT:20240425
SLL_BUY_DVSN_CD:%
SORT_SQN_DVSN:01
PDNO:
NCCS_YN:N
CTX_AREA_FK200:
CTX_AREA_NK200:
```

**Response Example**

```
{
    "ctx_area_nk200": " !^                                                                                                                                                                                                     ",
    "ctx_area_fk200": "null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^null!^%!^null                                                                                     ",
    "output1": [
        {
            "ord_dt": "20240425",
            "odno": "0000015201",
            "orgn_odno": "",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "현금매수",
            "shtn_pdno": "KR6095572D81",
            "prdt_abrv_name": "AJ네트웍스63-2",
            "ord_qty": "1",
            "bond_ord_unpr": "10450.00",
            "ord_tmd": "102033",
            "tot_ccld_qty": "1",
            "bond_avg_unpr": "10250.00",
            "tot_ccld_amt": "1025",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "0",
            "ord_gno_brno": "01790"
        },
        {
            "ord_dt": "20240425",
            "odno": "0000015202",
            "orgn_odno": "",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "현금매수",
            "shtn_pdno": "KR6095572D81",
            "prdt_abrv_name": "AJ네트웍스63-2",
            "ord_qty": "1",
            "bond_ord_unpr": "10450.00",
            "ord_tmd": "135029",
            "tot_ccld_qty": "0",
            "bond_avg_unpr": "0.00",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "0",
            "ord_gno_brno": "01790"
        },
        {
            "ord_dt": "20240425",
            "odno": "0000015203",
            "orgn_odno": "0000015202",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "매수취소*",
            "shtn_pdno": "KR6095572D81",
            "prdt_abrv_name": "AJ네트웍스63-2",
            "ord_qty": "1",
            "bond_ord_unpr": "0.00",
            "ord_tmd": "135108",
            "tot_ccld_qty": "0",
            "bond_avg_unpr": "0.00",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "0",
            "ord_gno_brno": "01790"
        },
        {
            "ord_dt": "20240425",
            "odno": "0000015204",
            "orgn_odno": "",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "현금매수",
            "shtn_pdno": "KR101501D942",
            "prdt_abrv_name": "국민주택1종19-04",
            "ord_qty": "1",
            "bond_ord_unpr": "10929.90",
            "ord_tmd": "163441",
            "tot_ccld_qty": "0",
            "bond_avg_unpr": "0.00",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "1",
            "ord_gno_brno": "01790"
        },
        {
            "ord_dt": "20240425",
            "odno": "0000015205",
            "orgn_odno": "",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "현금매수",
            "shtn_pdno": "KR103502G990",
            "prdt_abrv_name": "국고01125-3909(19-6)",
            "ord_qty": "1",
            "bond_ord_unpr": "7299.00",
            "ord_tmd": "163612",
            "tot_ccld_qty": "0",
            "bond_avg_unpr": "0.00",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "1",
            "ord_gno_brno": "01790"
        },
        {
            "ord_dt": "20240425",
            "odno": "0000015206",
            "orgn_odno": "",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "현금매수",
            "shtn_pdno": "KR103502G990",
            "prdt_abrv_name": "국고01125-3909(19-6)",
            "ord_qty": "1",
            "bond_ord_unpr": "7299.00",
            "ord_tmd": "163618",
            "tot_ccld_qty": "0",
            "bond_avg_unpr": "0.00",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "1",
            "ord_gno_brno": "01790"
        },
        {
            "ord_dt": "20240425",
            "odno": "0000015207",
            "orgn_odno": "",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "현금매수",
            "shtn_pdno": "KR2088012A16",
            "prdt_abrv_name": "경남지역개발20-01",
            "ord_qty": "1",
            "bond_ord_unpr": "10206.60",
            "ord_tmd": "163922",
            "tot_ccld_qty": "0",
            "bond_avg_unpr": "0.00",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "1",
            "ord_gno_brno": "01790"
        },
        {
            "ord_dt": "20240425",
            "odno": "0000015208",
            "orgn_odno": "",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "현금매수",
            "shtn_pdno": "KR2088012A16",
            "prdt_abrv_name": "경남지역개발20-01",
            "ord_qty": "1",
            "bond_ord_unpr": "10206.60",
            "ord_tmd": "164006",
            "tot_ccld_qty": "0",
            "bond_avg_unpr": "0.00",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "1",
            "ord_gno_brno": "01790"
        },
        {
            "ord_dt": "20240425",
            "odno": "0000015209",
            "orgn_odno": "",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "현금매수거부",
            "shtn_pdno": "KR6095572D81",
            "prdt_abrv_name": "AJ네트웍스63-2",
            "ord_qty": "2",
            "bond_ord_unpr": "10450.00",
            "ord_tmd": "170002",
            "tot_ccld_qty": "0",
            "bond_avg_unpr": "0.00",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "0",
            "ord_gno_brno": "01790"
        },
        {
            "ord_dt": "20240425",
            "odno": "0000015210",
            "orgn_odno": "",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "현금매수거부",
            "shtn_pdno": "KR6095572D81",
            "prdt_abrv_name": "AJ네트웍스63-2",
            "ord_qty": "1",
            "bond_ord_unpr": "10400.00",
            "ord_tmd": "170010",
            "tot_ccld_qty": "0",
            "bond_avg_unpr": "0.00",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "0",
            "ord_gno_brno": "01790"
        },
        {
            "ord_dt": "20240425",
            "odno": "0000015211",
            "orgn_odno": "",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "현금매수거부",
            "shtn_pdno": "KR6095572D81",
            "prdt_abrv_name": "AJ네트웍스63-2",
            "ord_qty": "5",
            "bond_ord_unpr": "10400.00",
            "ord_tmd": "170015",
            "tot_ccld_qty": "0",
            "bond_avg_unpr": "0.00",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "0",
            "ord_gno_brno": "01790"
        },
        {
            "ord_dt": "20240425",
            "odno": "0000015212",
            "orgn_odno": "",
            "ord_dvsn_name": "보통",
            "sll_buy_dvsn_cd_name": "현금매수거부",
            "shtn_pdno": "KR6095572D81",
            "prdt_abrv_name": "AJ네트웍스63-2",
            "ord_qty": "5",
            "bond_ord_unpr": "10200.00",
            "ord_tmd": "170019",
            "tot_ccld_qty": "0",
            "bond_avg_unpr": "0.00",
            "tot_ccld_amt": "0",
            "loan_dt": "",
            "buy_dt": "",
            "samt_mket_ptci_yn_name": "일반시장",
            "sprx_psbl_yn_ifom": "종합과세",
            "ord_mdia_dvsn_name": "33",
            "sll_buy_dvsn_cd": "02",
            "nccs_qty": "0",
            "ord_gno_brno": "01790"
        }
    ],
    "output2": {
        "tot_ord_qty": "6",
        "tot_ccld_qty_smtl": "1",
        "tot_bond_ccld_avg_unpr": "10250.00",
        "tot_ccld_amt_smtl": "1025"
    },
    "rt_cd": "0",
    "msg_cd": "KIOK0460",
    "msg1": "조회 되었습니다. (마지막 자료)                                                  "
}
```

---

## 장내채권 잔고조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 주문/계좌 |
| API 명 | 장내채권 잔고조회 |
| API ID | 국내주식-198 |
| 실전 TR_ID | CTSC8407R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/trading/inquire-balance |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 325 |

### 개요

장내채권 잔고조회 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0979] 장내채권종합주문 화면의 "왼쪽 하단 잔고" 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | CTSC8407R |
| tr_cont | 연속 거래 여부 | string | N | 1 | 공백 : 초기 조회<br>N : 다음 데이터 조회 (output header의 tr_cont가 M일 경우) |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 <br>P : 개인 |
| seq_no | 일련번호 | string | N | 2 | [법인 필수] 001 |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Query Parameter**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| CANO | 종합계좌번호 | string | Y | 8 |  |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 |  |
| INQR_CNDT | 조회조건 | string | Y | 2 | 00: 전체, 01: 상품번호단위 |
| PDNO | 상품번호 | string | Y | 12 | 공백 |
| BUY_DT | 매수일자 | string | Y | 8 | 공백 |
| CTX_AREA_FK200 | 연속조회검색조건200 | string | Y | 200 |  |
| CTX_AREA_NK200 | 연속조회키200 | string | Y | 200 |  |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| tr_id | 거래ID | string | Y | 13 | 요청한 tr_id |
| tr_cont | 연속 거래 여부 | string | N | 1 | F or M : 다음 데이터 있음<br>D or E : 마지막 데이터 |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| rt_cd | 성공 실패 여부 | string | Y | 1 |  |
| msg_cd | 응답코드 | string | Y | 8 |  |
| msg1 | 응답메세지 | string | Y | 80 |  |
| output | 응답상세 | object array | Y |  | array |
| pdno | 상품번호 | string | Y | 12 |  |
| prdt_name | 상품명 | string | Y | 60 |  |
| buy_dt | 매수일자 | string | Y | 8 |  |
| buy_sqno | 매수일련번호 | string | Y | 10 |  |
| cblc_qty | 잔고수량 | string | Y | 19 |  |
| agrx_qty | 종합과세수량 | string | Y | 10 |  |
| sprx_qty | 분리과세수량 | string | Y | 10 |  |
| exdt | 만기일 | string | Y | 8 |  |
| buy_erng_rt | 매수수익율 | string | Y | 238 |  |
| buy_unpr | 매수단가 | string | Y | 19 |  |
| buy_amt | 매수금액 | string | Y | 19 |  |
| ord_psbl_qty | 주문가능수량 | string | Y | 10 |  |

### Example

**Request Example (Python)**

```
CANO:12345678
ACNT_PRDT_CD:01
INQR_CNDT:00
PDNO:
BUY_DT:
CTX_AREA_FK200:
CTX_AREA_NK200:
```

**Response Example**

```
{
    "ctx_area_fk200": "!^!^null                                                                                                                                                                                                ",
    "ctx_area_nk200": " !^ !^                                                                                                                                                                                                  ",
    "output": [
        {
            "pdno": "KR101501D942",
            "prdt_name": "국민주택1종19-04",
            "buy_dt": "20240426",
            "buy_sqno": "1",
            "cblc_qty": "4",
            "agrx_qty": "4",
            "sprx_qty": "0",
            "exdt": "20240430",
            "buy_erng_rt": "0.00000000",
            "buy_unpr": "0",
            "buy_amt": "0",
            "ord_psbl_qty": "4"
        },
        {
            "pdno": "KR2088012A16",
            "prdt_name": "경남지역개발20-01",
            "buy_dt": "20240426",
            "buy_sqno": "1",
            "cblc_qty": "6",
            "agrx_qty": "5",
            "sprx_qty": "0",
            "exdt": "20250131",
            "buy_erng_rt": "0.00000000",
            "buy_unpr": "0",
            "buy_amt": "0",
            "ord_psbl_qty": "5"
        },
        {
            "pdno": "KR6003492D41",
            "prdt_name": "대한항공102-2",
            "buy_dt": "20240426",
            "buy_sqno": "1",
            "cblc_qty": "9",
            "agrx_qty": "9",
            "sprx_qty": "0",
            "exdt": "20260424",
            "buy_erng_rt": "0.00000000",
            "buy_unpr": "0",
            "buy_amt": "0",
            "ord_psbl_qty": "9"
        },
        {
            "pdno": "KR6095572D81",
            "prdt_name": "AJ네트웍스63-2",
            "buy_dt": "20240426",
            "buy_sqno": "1",
            "cblc_qty": "23",
            "agrx_qty": "22",
            "sprx_qty": "0",
            "exdt": "20250801",
            "buy_erng_rt": "0.00000000",
            "buy_unpr": "0",
            "buy_amt": "0",
            "ord_psbl_qty": "22"
        }
    ],
    "rt_cd": "0",
    "msg_cd": "KIOK0460",
    "msg1": "조회 되었습니다. (마지막 자료)                                                  "
}
```

---

## 장내채권 매수가능조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 주문/계좌 |
| API 명 | 장내채권 매수가능조회 |
| API ID | 국내주식-199 |
| 실전 TR_ID | TTTC8910R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/trading/inquire-psbl-order |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 326 |

### 개요

장내채권 매수가능조회 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0978] 장내채권주문 화면의 "왼쪽 하단 증거금 사용가능 내역 / 주문가능금액 및 수량" 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다. 

※ (중요) 채권의 경우 주식과 달리, 매수가능수량(buy_psbl_qty) = 매수가능금액(buy_psbl_amt) / 채권주문단가2(bond_ord_unpr2) * 10 인 점 유의하시기 바랍니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | TTTC8910R |
| tr_cont | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 <br>P : 개인 |
| seq_no | 일련번호 | string | N | 2 | [법인 필수] 001 |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Query Parameter**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| CANO | 종합계좌번호 | string | Y | 8 |  |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 |  |
| PDNO | 상품번호 | string | Y | 12 |  |
| BOND_ORD_UNPR | 채권주문단가 | string | Y | 182 |  |
| SAMT_MKET_PTCI_YN | 소액시장참여여부 | string | Y | 1 | Y(소액시장) N (일반시장) |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| tr_id | 거래ID | string | Y | 13 | 요청한 tr_id |
| tr_cont | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| rt_cd | 성공 실패 여부 | string | Y | 1 |  |
| msg_cd | 응답코드 | string | Y | 8 |  |
| msg1 | 응답메세지 | string | Y | 80 |  |
| output | 응답상세 | object array | Y |  | array |
| ord_psbl_cash | 주문가능현금 | string | Y | 19 |  |
| ord_psbl_sbst | 주문가능대용 | string | Y | 19 |  |
| ruse_psbl_amt | 재사용가능금액 | string | Y | 19 |  |
| bond_ord_unpr2 | 채권주문단가2 | string | Y | 182 |  |
| buy_psbl_amt | 매수가능금액 | string | Y | 19 |  |
| buy_psbl_qty | 매수가능수량 | string | Y | 10 | 매수가능수량(buy_psbl_qty) = 매수가능금액(buy_psbl_amt) / 채권주문단가2(bond_ord_unpr2) * 10 |
| cma_evlu_amt | CMA평가금액 | string | Y | 19 |  |

### Example

**Request Example (Python)**

```
CANO:12345678
ACNT_PRDT_CD:01
PDNO:KR6095572D81
BOND_ORD_UNPR:10450.0
```

**Response Example**

```
{
    "output": {
        "ord_psbl_cash": "9285653",
        "ord_psbl_sbst": "117521",
        "ruse_psbl_amt": "0",
        "bond_ord_unpr2": "10450.00",
        "buy_psbl_amt": "9230271",
        "buy_psbl_qty": "8832",
        "cma_evlu_amt": "0"
    },
    "rt_cd": "0",
    "msg_cd": "KIOK0510",
    "msg1": "조회가 완료되었습니다                                                           "
}
```

---
