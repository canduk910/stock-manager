# 해외선물옵션 주문/계좌

**카테고리 코드**: `[해외선물옵션] 주문/계좌`  
**API 수**: 11개

> 출처: 한국투자증권 OpenAPI 전체 문서 (2026-05-08).  
> 자동 변환: `scripts/kis_excel_to_md.py`

---

## 목차

- [해외선물옵션 주문](#해외선물옵션-주문) — `POST` `/uapi/overseas-futureoption/v1/trading/order` (실전 TR_ID: `OTFM3001U`)
- [해외선물옵션 정정취소주문](#해외선물옵션-정정취소주문) — `POST` `/uapi/overseas-futureoption/v1/trading/order-rvsecncl` (실전 TR_ID: `(정정) OTFM3002U (취소) OTFM3003U`)
- [해외선물옵션 당일주문내역조회](#해외선물옵션-당일주문내역조회) — `GET` `/uapi/overseas-futureoption/v1/trading/inquire-ccld` (실전 TR_ID: `OTFM3116R`)
- [해외선물옵션 미결제내역조회(잔고)](#해외선물옵션-미결제내역조회잔고) — `GET` `/uapi/overseas-futureoption/v1/trading/inquire-unpd` (실전 TR_ID: `OTFM1412R`)
- [해외선물옵션 주문가능조회](#해외선물옵션-주문가능조회) — `GET` `/uapi/overseas-futureoption/v1/trading/inquire-psamount` (실전 TR_ID: `OTFM3304R`)
- [해외선물옵션 기간계좌손익 일별](#해외선물옵션-기간계좌손익-일별) — `GET` `/uapi/overseas-futureoption/v1/trading/inquire-period-ccld` (실전 TR_ID: `OTFM3118R`)
- [해외선물옵션 일별 체결내역](#해외선물옵션-일별-체결내역) — `GET` `/uapi/overseas-futureoption/v1/trading/inquire-daily-ccld` (실전 TR_ID: `OTFM3122R`)
- [해외선물옵션 예수금현황](#해외선물옵션-예수금현황) — `GET` `/uapi/overseas-futureoption/v1/trading/inquire-deposit` (실전 TR_ID: `OTFM1411R`)
- [해외선물옵션 일별 주문내역](#해외선물옵션-일별-주문내역) — `GET` `/uapi/overseas-futureoption/v1/trading/inquire-daily-order` (실전 TR_ID: `OTFM3120R`)
- [해외선물옵션 기간계좌거래내역](#해외선물옵션-기간계좌거래내역) — `GET` `/uapi/overseas-futureoption/v1/trading/inquire-period-trans` (실전 TR_ID: `OTFM3114R`)
- [해외선물옵션 증거금상세](#해외선물옵션-증거금상세) — `GET` `/uapi/overseas-futureoption/v1/trading/margin-detail` (실전 TR_ID: `OTFM3115R`)

---

## 해외선물옵션 주문

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [해외선물옵션] 주문/계좌 |
| API 명 | 해외선물옵션 주문 |
| API ID | v1_해외선물-001 |
| 실전 TR_ID | OTFM3001U |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | POST |
| URL 명 | /uapi/overseas-futureoption/v1/trading/order |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 285 |

### 개요

해외선물옵션 주문 API 입니다.

※ POST API의 경우 BODY값의 key값들을 대문자로 작성하셔야 합니다.
   (EX. "CANO" : "12345678", "ACNT_PRDT_CD": "01",...)

※ 종목코드 마스터파일 파이썬 정제코드는 한국투자증권 Github 참고 부탁드립니다.
   https://github.com/koreainvestment/open-trading-api/tree/main/stocks_info

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용)<br><br>※ 토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출<br>EX) "Bearer eyJ..........8GA" |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | [실전투자]<br>OTFM3001U : ASFM선물옵션주문신규 |
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
| CANO | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| OVRS_FUTR_FX_PDNO | 해외선물FX상품번호 | string | Y | 32 |  |
| SLL_BUY_DVSN_CD | 매도매수구분코드 | string | Y | 2 | 01 : 매도<br>02 : 매수 |
| FM_LQD_USTL_CCLD_DT | FM청산미결제체결일자 | string | N | 8 | 빈칸 (hedge청산만 이용) |
| FM_LQD_USTL_CCNO | FM청산미결제체결번호 | string | N | 10 | 빈칸 (hedge청산만 이용) |
| PRIC_DVSN_CD | 가격구분코드 | string | Y | 1 | 1.지정, 2. 시장, 3. STOP, 4 S/L |
| FM_LIMIT_ORD_PRIC | FMLIMIT주문가격 | string | Y | 20 | 지정가인 경우 가격 입력<br>* 시장가, STOP주문인 경우, 빈칸("") 입력 |
| FM_STOP_ORD_PRIC | FMSTOP주문가격 | string | Y | 20 | STOP 주문 가격 입력<br>* 시장가, 지정가인 경우, 빈칸("") 입력 |
| FM_ORD_QTY | FM주문수량 | string | Y | 10 |  |
| FM_LQD_LMT_ORD_PRIC | FM청산LIMIT주문가격 | string | N | 20 | 빈칸 (hedge청산만 이용) |
| FM_LQD_STOP_ORD_PRIC | FM청산STOP주문가격 | string | N | 20 | 빈칸 (hedge청산만 이용) |
| CCLD_CNDT_CD | 체결조건코드 | string | Y | 1 | 일반적으로 6 (EOD, 지정가) <br>GTD인 경우 5, 시장가인 경우만 2 |
| CPLX_ORD_DVSN_CD | 복합주문구분코드 | string | Y | 1 | 0 (hedge청산만 이용) |
| ECIS_RSVN_ORD_YN | 행사예약주문여부 | string | Y | 1 | N |
| FM_HDGE_ORD_SCRN_YN | FM_HEDGE주문화면여부 | string | Y | 1 | N |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| rt_cd | 성공 실패 여부 | string | Y | 1 | 0 : 성공<br>0 이외의 값 : 실패 |
| msg_cd | 응답코드 | string | Y | 8 |  |
| msg1 | 응답메세지 | string | Y | 80 |  |
| output |  | object | N |  |  |
| ORD_DT | 주문일자 | string | N | 8 |  |
| ODNO | 주문번호 | string | N | 8 | 접수한 주문의 일련번호(ex. 00360686)<br>* 정정/취소시 문자열처럼 "0"을 포함해서 전송 <br>  (ex. ORGN_ODNO : 00360686) |

### Example

**Request Example (Python)**

```
{
    "CANO": "81012345",
    "ACNT_PRDT_CD": "08",
    "OVRS_FUTR_FX_PDNO": "6BZ22",
    "SLL_BUY_DVSN_CD": "02",
    "FM_LQD_USTL_CCLD_DT": "",
    "FM_LQD_USTL_CCNO": "",
    "PRIC_DVSN_CD": "1",
    "FM_LIMIT_ORD_PRIC": "1.17",
    "FM_STOP_ORD_PRIC": "",
    "FM_ORD_QTY": "1",
    "FM_LQD_LMT_ORD_PRIC": "",
    "FM_LQD_STOP_ORD_PRIC": "",
    "CCLD_CNDT_CD": "6",
    "CPLX_ORD_DVSN_CD": "0",
    "ECIS_RSVN_ORD_YN": "N",
    "FM_HDGE_ORD_SCRN_YN": "N"
}
```

**Response Example**

```
{
    "rt_cd": "0",
    "msg_cd": "APBK0013",
    "msg1": "주문 전송 완료 되었습니다.",
    "output": {
        "ORD_DT": "20221214",
        "ODNO": "00298040"
    }
}
```

---

## 해외선물옵션 정정취소주문

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [해외선물옵션] 주문/계좌 |
| API 명 | 해외선물옵션 정정취소주문 |
| API ID | v1_해외선물-002, 003 |
| 실전 TR_ID | (정정) OTFM3002U (취소) OTFM3003U |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | POST |
| URL 명 | /uapi/overseas-futureoption/v1/trading/order-rvsecncl |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 286 |

### 개요

해외선물옵션 정정취소주문 API 입니다.

※ POST API의 경우 BODY값의 key값들을 대문자로 작성하셔야 합니다.
   (EX. "CANO" : "12345678", "ACNT_PRDT_CD": "01",...)

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용)<br><br>※ 토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출<br>EX) "Bearer eyJ..........8GA" |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | [실전투자]<br>OTFM3002U : 해외선물옵션주문정정<br>OTFM3003U : 해외선물옵션주문취소 |
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
| CANO | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| ORGN_ORD_DT | 원주문일자 | string | Y | 8 | 원 주문 시 출력되는 ORD_DT 값을 입력 (현지거래일) |
| ORGN_ODNO | 원주문번호 | string | Y | 8 | 정정/취소시 주문번호(ODNO) 8자리를 문자열처럼 "0"을 포함해서 전송 (원 주문 시 출력된 ODNO 값 활용)<br>(ex. ORGN_ODNO : 00360686) |
| FM_LIMIT_ORD_PRIC | FMLIMIT주문가격 | string | N | 20 | OTFM3002U(해외선물옵션주문정정)만 사용 |
| FM_STOP_ORD_PRIC | FMSTOP주문가격 | string | N | 20 | OTFM3002U(해외선물옵션주문정정)만 사용 |
| FM_LQD_LMT_ORD_PRIC | FM청산LIMIT주문가격 | string | N | 20 | OTFM3002U(해외선물옵션주문정정)만 사용 |
| FM_LQD_STOP_ORD_PRIC | FM청산STOP주문가격 | string | N | 20 | OTFM3002U(해외선물옵션주문정정)만 사용 |
| FM_HDGE_ORD_SCRN_YN | FM_HEDGE주문화면여부 | string | Y | 1 | N |
| FM_MKPR_CVSN_YN | FM시장가전환여부 | string | N | 1 | OTFM3003U(해외선물옵션주문취소)만 사용<br><br>※ FM_MKPR_CVSN_YN 항목에 'Y'로 설정하여 취소주문을 접수할 경우, 주문 취소확인이 들어오면 원장에서 시장가주문을 하나 또 내줌 |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| rt_cd | 성공 실패 여부 | string | Y | 1 | 0 : 성공<br>0 이외의 값 : 실패 |
| msg_cd | 응답코드 | string | Y | 8 |  |
| msg1 | 응답메세지 | string | Y | 80 |  |
| output |  | object | N |  |  |
| ORD_DT | 주문일자 | string | N | 8 | YYYYMMDD(ex. 20230811) |
| ODNO | 주문번호 | string | N | 8 | 접수한 주문의 일련번호(ex. 00360686)<br>* 정정/취소시 문자열처럼 "0"을 포함해서 전송 <br>  (ex. ORGN_ODNO : 00360686) |

### Example

**Request Example (Python)**

```
{
    "CANO": "81012345",
    "ACNT_PRDT_CD": "08",
    "ORGN_ORD_DT": "20221214",
    "ORGN_ODNO": "00298044",
    "FM_MKPR_CVSN_YN": "N",
    "FM_HDGE_ORD_SCRN_YN": "N"
}
```

**Response Example**

```
{
    "rt_cd": "0",
    "msg_cd": "APBK0013",
    "msg1": "주문 전송 완료 되었습니다.",
    "output": {
        "ORD_DT": "20221214",
        "ODNO": "00298045"
    }
}
```

---

## 해외선물옵션 당일주문내역조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [해외선물옵션] 주문/계좌 |
| API 명 | 해외선물옵션 당일주문내역조회 |
| API ID | v1_해외선물-004 |
| 실전 TR_ID | OTFM3116R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/overseas-futureoption/v1/trading/inquire-ccld |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 287 |

### 개요

해외선물옵션 당일주문내역조회 API입니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | OTFM3116R |
| tr_cont | 연속 거래 여부 | string | N | 1 | 공백 : 초기 조회<br>N : 다음 데이터 조회 (output header의 tr_cont가 M일 경우) |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 / P : 개인 |
| seq_no | 일련번호 | string | N | 2 | 법인 : "001" / default   개인: "" |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Query Parameter**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| CANO | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| CCLD_NCCS_DVSN | 체결미체결구분 | string | Y | 2 | 01:전체 / 02:체결 / 03:미체결 |
| SLL_BUY_DVSN_CD | 매도매수구분코드 | string | Y | 2 | %%:전체 / 01:매도 / 02:매수 |
| FUOP_DVSN | 선물옵션구분 | string | Y | 2 | 00:전체 / 01:선물 / 02:옵션 |
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
| output | 응답상세1 | object array | N |  | Array |
| cano | 종합계좌번호 | string | N | 8 |  |
| acnt_prdt_cd | 계좌상품코드 | string | N | 2 |  |
| ord_dt | 주문일자 | string | N | 8 |  |
| odno | 주문번호 | string | N | 8 | 접수한 주문의 일련번호(ex. 00360686)<br>* 정정/취소시 문자열처럼 "0"을 포함해서 전송 <br>  (ex. ORGN_ODNO : 00360686) |
| orgn_ord_dt | 원주문일자 | string | N | 8 |  |
| orgn_odno | 원주문번호 | string | N | 8 | 원주문번호(ex. 00360685) |
| ovrs_futr_fx_pdno | 해외선물FX상품번호 | string | N | 32 |  |
| rcit_dvsn_cd | 접수구분코드 | string | N | 2 | 05	온라인 |
| sll_buy_dvsn_cd | 매도매수구분코드 | string | N | 2 | 01:매도, 02:매수 |
| trad_stgy_dvsn_cd | 매매전략구분코드 | string | N | 2 |  |
| bass_pric_type_cd | 기준가격유형코드 | string | N | 2 | 01	시가평가<br>02	액면가<br>03	기준가격<br>04	대용가 |
| ord_stat_cd | 주문상태코드 | string | N | 2 |  |
| fm_ord_qty | FM주문수량 | string | N | 10 |  |
| fm_ord_pric | FM주문가격 | string | N | 20 |  |
| fm_stop_ord_pric | FMSTOP주문가격 | string | N | 20 |  |
| rsvn_dvsn | 예약구분 | string | N | 2 |  |
| fm_ccld_qty | FM체결수량 | string | N | 10 |  |
| fm_ccld_pric | FM체결가격 | string | N | 20 |  |
| fm_ord_rmn_qty | FM주문잔여수량 | string | N | 10 |  |
| ord_grp_name | 주문그룹명 | string | N | 60 |  |
| erlm_dtl_dtime | 등록상세일시 | string | N | 17 |  |
| ccld_dtl_dtime | 체결상세일시 | string | N | 17 |  |
| ord_stfno | 주문직원번호 | string | N | 6 |  |
| rmks1 | 비고1 | string | N | 100 |  |
| new_lqd_dvsn_cd | 신규청산구분코드 | string | N | 2 | 01	신규<br>02	청산 |
| fm_lqd_lmt_ord_pric | FM청산LIMIT주문가격 | string | N | 20 |  |
| fm_lqd_stop_pric | FM청산STOP가격 | string | N | 20 |  |
| ccld_cndt_cd | 체결조건코드 | string | N | 1 |  |
| noti_vald_dt | 게시유효일자 | string | N | 8 |  |
| acnt_type_cd | 계좌유형코드 | string | N | 2 |  |
| fuop_dvsn | 선물옵션구분 | string | N | 2 | 01:선물, 02: 옵션 |

### Example

**Request Example (Python)**

```
{
	"CANO":"80012345",
	"ACNT_PRDT_CD":"08",
	"CCLD_NCCS_DVSN":"01",
	"SLL_BUY_DVSN_CD":"01",
	"FUOP_DVSN":"00",
	"CTX_AREA_FK100":"",
	"CTX_AREA_NK100":"",
}
```

**Response Example**

```
{
    "ctx_area_fk200": "81012345^08^01^02^00^                                                                                                                                                                                   ",
    "ctx_area_nk200": "                                                                                                                                                                                                        ",
    "output": [
        {
            "cano": "81012345",
            "acnt_prdt_cd": "08",
            "ord_dt": "20221214",
            "odno": "00298048",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "6BZ22",
            "rcit_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "trad_stgy_dvsn_cd": "00",
            "bass_pric_type_cd": "1",
            "ord_stat_cd": "02",
            "fm_ord_qty": "1",
            "fm_ord_pric": "1.1700",
            "fm_stop_ord_pric": "0.0000",
            "rsvn_dvsn": "N",
            "fm_ccld_qty": "0",
            "fm_ccld_pric": "0.0000",
            "fm_ord_rmn_qty": "1",
            "ord_grp_name": "",
            "erlm_dtl_dtime": "20221214134455791",
            "ccld_dtl_dtime": "",
            "ord_stfno": "invent",
            "rmks1": "",
            "new_lqd_dvsn_cd": "1",
            "fm_lqd_lmt_ord_pric": "0.0000",
            "fm_lqd_stop_pric": "0.0000",
            "ccld_cndt_cd": "6",
            "noti_vald_dt": "",
            "acnt_type_cd": "1",
            "fuop_dvsn": "01"
        },
        {
            "cano": "81012345",
            "acnt_prdt_cd": "08",
            "ord_dt": "20221214",
            "odno": "00298045",
            "orgn_ord_dt": "20221214",
            "orgn_odno": "00298044",
            "ovrs_futr_fx_pdno": "6BZ22",
            "rcit_dvsn_cd": "02",
            "sll_buy_dvsn_cd": "02",
            "trad_stgy_dvsn_cd": "00",
            "bass_pric_type_cd": "1",
            "ord_stat_cd": "02",
            "fm_ord_qty": "1",
            "fm_ord_pric": "0.0000",
            "fm_stop_ord_pric": "0.0000",
            "rsvn_dvsn": "N",
            "fm_ccld_qty": "0",
            "fm_ccld_pric": "0.0000",
            "fm_ord_rmn_qty": "0",
            "ord_grp_name": "",
            "erlm_dtl_dtime": "20221214134356649",
            "ccld_dtl_dtime": "",
            "ord_stfno": "invent",
            "rmks1": "",
            "new_lqd_dvsn_cd": "1",
            "fm_lqd_lmt_ord_pric": "0.0000",
            "fm_lqd_stop_pric": "0.0000",
            "ccld_cndt_cd": "6",
            "noti_vald_dt": "",
            "acnt_type_cd": "1",
            "fuop_dvsn": "01"
        },
        {
            "cano": "81012345",
            "acnt_prdt_cd": "08",
            "ord_dt": "20221214",
            "odno": "00298044",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "6BZ22",
            "rcit_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "trad_stgy_dvsn_cd": "00",
            "bass_pric_type_cd": "1",
            "ord_stat_cd": "02",
            "fm_ord_qty": "1",
            "fm_ord_pric": "1.1700",
            "fm_stop_ord_pric": "0.0000",
            "rsvn_dvsn": "N",
            "fm_ccld_qty": "0",
            "fm_ccld_pric": "0.0000",
            "fm_ord_rmn_qty": "0",
            "ord_grp_name": "",
            "erlm_dtl_dtime": "20221214134351411",
            "ccld_dtl_dtime": "",
            "ord_stfno": "invent",
            "rmks1": "",
            "new_lqd_dvsn_cd": "1",
            "fm_lqd_lmt_ord_pric": "0.0000",
            "fm_lqd_stop_pric": "0.0000",
            "ccld_cndt_cd": "6",
            "noti_vald_dt": "",
            "acnt_type_cd": "1",
            "fuop_dvsn": "01"
        },
        {
            "cano": "81012345",
            "acnt_prdt_cd": "08",
            "ord_dt": "20221214",
            "odno": "00298040",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "6BZ22",
            "rcit_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "trad_stgy_dvsn_cd": "00",
            "bass_pric_type_cd": "1",
            "ord_stat_cd": "02",
            "fm_ord_qty": "1",
            "fm_ord_pric": "1.1700",
            "fm_stop_ord_pric": "0.0000",
            "rsvn_dvsn": "N",
            "fm_ccld_qty": "0",
            "fm_ccld_pric": "0.0000",
            "fm_ord_rmn_qty": "1",
            "ord_grp_name": "",
            "erlm_dtl_dtime": "20221214134100992",
            "ccld_dtl_dtime": "",
            "ord_stfno": "invent",
            "rmks1": "",
            "new_lqd_dvsn_cd": "1",
            "fm_lqd_lmt_ord_pric": "0.0000",
            "fm_lqd_stop_pric": "0.0000",
            "ccld_cndt_cd": "6",
            "noti_vald_dt": "",
            "acnt_type_cd": "1",
            "fuop_dvsn": "01"
        }
    ],
    "rt_cd": "0",
    "msg_cd": "KIOK0510",
    "msg1": "조회가 완료되었습니다                                                           "
}
```

---

## 해외선물옵션 미결제내역조회(잔고)

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [해외선물옵션] 주문/계좌 |
| API 명 | 해외선물옵션 미결제내역조회(잔고) |
| API ID | v1_해외선물-005 |
| 실전 TR_ID | OTFM1412R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/overseas-futureoption/v1/trading/inquire-unpd |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 288 |

### 개요

해외선물옵션 미결제내역조회(잔고) API입니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | OTFM1412R |
| tr_cont | 연속 거래 여부 | string | N | 1 | 공백 : 초기 조회<br>N : 다음 데이터 조회 (output header의 tr_cont가 M일 경우) |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 / P : 개인 |
| seq_no | 일련번호 | string | N | 2 | 법인 : "001" / default   개인: "" |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Query Parameter**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| CANO | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| FUOP_DVSN | 선물옵션구분 | string | Y | 2 | 00: 전체 / 01:선물 / 02: 옵션 |
| CTX_AREA_FK100 | 연속조회검색조건100 | string | Y | 100 |  |
| CTX_AREA_NK100 | 연속조회키100 | string | Y | 100 |  |

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
| output | 응답상세1 | object array | N |  | Array |
| cano | 종합계좌번호 | string | N | 8 |  |
| acnt_prdt_cd | 계좌상품코드 | string | N | 2 |  |
| ovrs_futr_fx_pdno | 해외선물FX상품번호 | string | N | 32 |  |
| prdt_type_cd | 상품유형코드 | string | N | 3 |  |
| crcy_cd | 통화코드 | string | N | 3 |  |
| sll_buy_dvsn_cd | 매도매수구분코드 | string | N | 2 |  |
| fm_ustl_qty | FM미결제수량 | string | N | 10 |  |
| fm_ccld_avg_pric | FM체결평균가격 | string | N | 20 |  |
| fm_now_pric | FM현재가격 | string | N | 20 |  |
| fm_evlu_pfls_amt | FM평가손익금액 | string | N | 20 |  |
| fm_opt_evlu_amt | FM옵션평가금액 | string | N | 20 |  |
| fm_otp_evlu_pfls_amt | FM옵션평가손익금액 | string | N | 20 |  |
| fuop_dvsn | 선물옵션구분 | string | N | 2 |  |
| ecis_rsvn_ord_yn | 행사예약주문여부 | string | N | 1 |  |
| fm_lqd_psbl_qty | FM청산가능수량 | string | N | 10 |  |

### Example

**Request Example (Python)**

```
{
	"CANO":"80012345",
	"ACNT_PRDT_CD":"08",
	"FUOP_DVSN":"00",
	"CTX_AREA_FK100":"",
	"CTX_AREA_NK100":"",
}
```

**Response Example**

```
{
    "ctx_area_fk100": "81012345^08^00^                                                                                     ",
    "ctx_area_nk100": "                                                                                                    ",
    "output": [
        {
            "cano": "81012345",
            "acnt_prdt_cd": "08",
            "ovrs_futr_fx_pdno": "6AZ22",
            "prdt_type_cd": "600",
            "crcy_cd": "USD",
            "sll_buy_dvsn_cd": "02",
            "fm_ustl_qty": "2",
            "fm_ccld_avg_pric": "0.62950",
            "fm_now_pric": "0.68320",
            "fm_evlu_pfls_amt": "10740.00",
            "fm_opt_evlu_amt": "",
            "fm_otp_evlu_pfls_amt": "",
            "fuop_dvsn": "01",
            "ecis_rsvn_ord_yn": "",
            "fm_lqd_psbl_qty": "2"
        },
        {
            "cano": "81012345",
            "acnt_prdt_cd": "08",
            "ovrs_futr_fx_pdno": "6BZ22",
            "prdt_type_cd": "600",
            "crcy_cd": "USD",
            "sll_buy_dvsn_cd": "02",
            "fm_ustl_qty": "2",
            "fm_ccld_avg_pric": "1.1898",
            "fm_now_pric": "1.2350",
            "fm_evlu_pfls_amt": "5656.24",
            "fm_opt_evlu_amt": "",
            "fm_otp_evlu_pfls_amt": "",
            "fuop_dvsn": "01",
            "ecis_rsvn_ord_yn": "",
            "fm_lqd_psbl_qty": "2"
        },
        {
            "cano": "81012345",
            "acnt_prdt_cd": "08",
            "ovrs_futr_fx_pdno": "6JZ22",
            "prdt_type_cd": "600",
            "crcy_cd": "USD",
            "sll_buy_dvsn_cd": "02",
            "fm_ustl_qty": "1",
            "fm_ccld_avg_pric": "6925.0",
            "fm_now_pric": "7383.0",
            "fm_evlu_pfls_amt": "5725.00",
            "fm_opt_evlu_amt": "",
            "fm_otp_evlu_pfls_amt": "",
            "fuop_dvsn": "01",
            "ecis_rsvn_ord_yn": "",
            "fm_lqd_psbl_qty": "1"
        },
        {
            "cano": "81012345",
            "acnt_prdt_cd": "08",
            "ovrs_futr_fx_pdno": "ZBZ22",
            "prdt_type_cd": "600",
            "crcy_cd": "USD",
            "sll_buy_dvsn_cd": "01",
            "fm_ustl_qty": "100",
            "fm_ccld_avg_pric": "132.293125",
            "fm_now_pric": "131.218750",
            "fm_evlu_pfls_amt": "107438.00",
            "fm_opt_evlu_amt": "",
            "fm_otp_evlu_pfls_amt": "",
            "fuop_dvsn": "01",
            "ecis_rsvn_ord_yn": "",
            "fm_lqd_psbl_qty": "100"
        }
    ],
    "rt_cd": "0",
    "msg_cd": "KIOK0510",
    "msg1": "조회가 완료되었습니다                                                           "
}
```

---

## 해외선물옵션 주문가능조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [해외선물옵션] 주문/계좌 |
| API 명 | 해외선물옵션 주문가능조회 |
| API ID | v1_해외선물-006 |
| 실전 TR_ID | OTFM3304R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/overseas-futureoption/v1/trading/inquire-psamount |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 289 |

### 개요

해외선물옵션 주문가능조회 API입니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | OTFM3304R |
| tr_cont | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| custtype | 고객 타입 | string | Y | 1 | B : 법인 / P : 개인 |
| seq_no | 일련번호 | string | N | 2 | 법인 : "001" / default   개인: "" |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Query Parameter**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| CANO | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| OVRS_FUTR_FX_PDNO | 해외선물FX상품번호 | string | Y | 32 |  |
| SLL_BUY_DVSN_CD | 매도매수구분코드 | string | Y | 2 | 01 : 매도 / 02 : 매수 |
| FM_ORD_PRIC | FM주문가격 | string | Y | 20 |  |
| ECIS_RSVN_ORD_YN | 행사예약주문여부 | string | Y | 1 | N |

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
| output | 응답상세1 | object | N |  |  |
| cano | 종합계좌번호 | string | N | 8 |  |
| acnt_prdt_cd | 계좌상품코드 | string | N | 2 |  |
| ovrs_futr_fx_pdno | 해외선물FX상품번호 | string | N | 32 |  |
| crcy_cd | 통화코드 | string | N | 3 |  |
| sll_buy_dvsn_cd | 매도매수구분코드 | string | N | 2 |  |
| fm_ustl_qty | FM미결제수량 | string | N | 10 |  |
| fm_lqd_psbl_qty | FM청산가능수량 | string | N | 10 |  |
| fm_new_ord_psbl_qty | FM신규주문가능수량 | string | N | 10 |  |
| fm_tot_ord_psbl_qty | FM총주문가능수량 | string | N | 10 |  |
| fm_mkpr_tot_ord_psbl_qty | FM시장가총주문가능수량 | string | N | 10 |  |

### Example

**Request Example (Python)**

```
{
	"CANO":"80012345",
	"ACNT_PRDT_CD":"08",
	"OVRS_FUTR_FX_PDNO":"6AU22",
	"SLL_BUY_DVSN_CD":"02",
	"FM_ORD_PRIC":"",
	"ECIS_RSVN_ORD_YN":""
}
```

**Response Example**

```
{
    "output": {
        "cano": "80012345",
        "acnt_prdt_cd": "08",
        "ovrs_futr_fx_pdno": "6AU22",
        "crcy_cd": "",
        "sll_buy_dvsn_cd": "02",
        "fm_ustl_qty": "0",
        "fm_lqd_psbl_qty": "0",
        "fm_new_ord_psbl_qty": "3717",
        "fm_tot_ord_psbl_qty": "3717",
        "fm_mkpr_tot_ord_psbl_qty": "3717"
    },
    "rt_cd": "0",
    "msg_cd": "KIOK0510",
    "msg1": "조회가 완료되었습니다                                                           "
}
```

---

## 해외선물옵션 기간계좌손익 일별

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [해외선물옵션] 주문/계좌 |
| API 명 | 해외선물옵션 기간계좌손익 일별 |
| API ID | 해외선물-010 |
| 실전 TR_ID | OTFM3118R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/overseas-futureoption/v1/trading/inquire-period-ccld |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 290 |

### 개요

해외선물옵션 기간계좌손익 일별 API입니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용)<br><br>※ 토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출<br>EX) "Bearer eyJ..........8GA" |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | OTFM3118R |
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
| INQR_TERM_FROM_DT | 조회기간FROM일자 | string | Y | 8 |  |
| INQR_TERM_TO_DT | 조회기간TO일자 | string | Y | 8 |  |
| CANO | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| CRCY_CD | 통화코드 | string | Y | 3 | '%%% : 전체<br>TUS: TOT_USD  / TKR: TOT_KRW<br>KRW: 한국  / USD: 미국<br>EUR: EUR   / HKD: 홍콩<br>CNY: 중국  / JPY: 일본' |
| WHOL_TRSL_YN | 전체환산여부 | string | Y | 1 | N |
| FUOP_DVSN | 선물옵션구분 | string | Y | 2 | 00:전체 / 01:선물 / 02:옵션 |
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
| output1 | 응답상세1 | object array | Y |  | Array |
| cano | 종합계좌번호 | string | Y | 8 |  |
| acnt_prdt_cd | 계좌상품코드 | string | N | 2 |  |
| crcy_cd | 통화코드 | string | Y | 3 |  |
| fm_buy_qty | FM매수수량 | string | Y | 10 |  |
| fm_sll_qty | FM매도수량 | string | Y | 10 |  |
| fm_lqd_pfls_amt | FM청산손익금액 | string | Y | 20 |  |
| fm_fee | FM수수료 | string | Y | 20 |  |
| fm_net_pfls_amt | FM순손익금액 | string | Y | 20 |  |
| fm_ustl_buy_qty | FM미결제매수수량 | string | Y | 10 |  |
| fm_ustl_sll_qty | FM미결제매도수량 | string | Y | 10 |  |
| fm_ustl_evlu_pfls_amt | FM미결제평가손익금액 | string | Y | 20 |  |
| fm_ustl_evlu_pfls_amt2 | FM미결제평가손익금액2 | string | Y | 20 |  |
| fm_ustl_evlu_pfls_icdc_amt | FM미결제평가손익증감금액 | string | Y | 20 |  |
| fm_ustl_agrm_amt | FM미결제약정금액 | string | Y | 20 |  |
| fm_opt_lqd_amt | FM옵션청산금액 | string | Y | 20 |  |
| output2 | 응답상세2 | object array | Y |  | Array |
| cano | 종합계좌번호 | string | Y | 8 |  |
| acnt_prdt_cd | 계좌상품코드 | string | Y | 2 |  |
| ovrs_futr_fx_pdno | 해외선물FX상품번호 | string | Y | 32 |  |
| crcy_cd | 통화코드 | string | Y | 3 |  |
| fm_buy_qty | FM매수수량 | string | Y | 10 |  |
| fm_sll_qty | FM매도수량 | string | Y | 10 |  |
| fm_lqd_pfls_amt | FM청산손익금액 | string | Y | 20 |  |
| fm_fee | FM수수료 | string | Y | 20 |  |
| fm_net_pfls_amt | FM순손익금액 | string | Y | 20 |  |
| fm_ustl_buy_qty | FM미결제매수수량 | string | Y | 10 |  |
| fm_ustl_sll_qty | FM미결제매도수량 | string | Y | 10 |  |
| fm_ustl_evlu_pfls_amt | FM미결제평가손익금액 | string | Y | 20 |  |
| fm_ustl_evlu_pfls_amt2 | FM미결제평가손익금액2 | string | Y | 20 |  |
| fm_ustl_evlu_pfls_icdc_amt | FM미결제평가손익증감금액 | string | Y | 20 |  |
| fm_ccld_avg_pric | FM체결평균가격 | string | Y | 20 |  |
| fm_ustl_agrm_amt | FM미결제약정금액 | string | Y | 20 |  |
| fm_opt_lqd_amt | FM옵션청산금액 | string | Y | 20 |  |

### Example

**Request Example (Python)**

```
{
	"CANO":"80012345",
	"ACNT_PRDT_CD":"08",
	"INQR_TERM_FROM_DT":"20220901",
	"INQR_TERM_TO_DT":"20221117",
	"CRCY_CD":"%%%",
	"WHOL_TRSL_YN":"N",
	"FUOP_DVSN":"00",
	"CTX_AREA_FK100":"",
	"CTX_AREA_NK100":"",
}
```

**Response Example**

```
{
    "ctx_area_fk200": "                                                                                                                                                                                                        ",
    "ctx_area_nk200": "                                                                                                                                                                                                        ",
    "output1": [
        {
            "cano": "80012345",
            "acnt_prdt_cd": "08",
            "crcy_cd": "USD",
            "fm_buy_qty": "",
            "fm_sll_qty": "",
            "fm_lqd_pfls_amt": "0.00",
            "fm_fee": "0.00",
            "fm_net_pfls_amt": "129650.00",
            "fm_ustl_buy_qty": "5",
            "fm_ustl_sll_qty": "100",
            "fm_ustl_evlu_pfls_amt": "129650.00",
            "fm_ustl_evlu_pfls_amt2": "0.00",
            "fm_ustl_evlu_pfls_icdc_amt": "129650.00",
            "fm_ustl_agrm_amt": "13590493.75",
            "fm_opt_lqd_amt": "0.00"
        }
    ],
    "output2": [
        {
            "cano": "80012345",
            "acnt_prdt_cd": "08",
            "ovrs_futr_fx_pdno": "6AZ22",
            "crcy_cd": "USD",
            "fm_buy_qty": "",
            "fm_sll_qty": "",
            "fm_lqd_pfls_amt": "0.00",
            "fm_fee": "0.00",
            "fm_net_pfls_amt": "10850.00",
            "fm_ustl_buy_qty": "2",
            "fm_ustl_sll_qty": "",
            "fm_ustl_evlu_pfls_amt": "10850.00",
            "fm_ustl_evlu_pfls_amt2": "0.00",
            "fm_ustl_evlu_pfls_icdc_amt": "10850.00",
            "fm_ccld_avg_pric": "0.62950",
            "fm_ustl_agrm_amt": "125900.00",
            "fm_opt_lqd_amt": "0.00"
        },
        {
            "cano": "80012345",
            "acnt_prdt_cd": "08",
            "ovrs_futr_fx_pdno": "6BZ22",
            "crcy_cd": "USD",
            "fm_buy_qty": "",
            "fm_sll_qty": "",
            "fm_lqd_pfls_amt": "0.00",
            "fm_fee": "0.00",
            "fm_net_pfls_amt": "5656.25",
            "fm_ustl_buy_qty": "2",
            "fm_ustl_sll_qty": "",
            "fm_ustl_evlu_pfls_amt": "5656.25",
            "fm_ustl_evlu_pfls_amt2": "0.00",
            "fm_ustl_evlu_pfls_icdc_amt": "5656.25",
            "fm_ccld_avg_pric": "1.1898",
            "fm_ustl_agrm_amt": "148718.75",
            "fm_opt_lqd_amt": "0.00"
        },
        {
            "cano": "80012345",
            "acnt_prdt_cd": "08",
            "ovrs_futr_fx_pdno": "6JZ22",
            "crcy_cd": "USD",
            "fm_buy_qty": "",
            "fm_sll_qty": "",
            "fm_lqd_pfls_amt": "0.00",
            "fm_fee": "0.00",
            "fm_net_pfls_amt": "5706.25",
            "fm_ustl_buy_qty": "1",
            "fm_ustl_sll_qty": "",
            "fm_ustl_evlu_pfls_amt": "5706.25",
            "fm_ustl_evlu_pfls_amt2": "0.00",
            "fm_ustl_evlu_pfls_icdc_amt": "5706.25",
            "fm_ccld_avg_pric": "6925.0",
            "fm_ustl_agrm_amt": "86562.50",
            "fm_opt_lqd_amt": "0.00"
        },
        {
            "cano": "80012345",
            "acnt_prdt_cd": "08",
            "ovrs_futr_fx_pdno": "ZBZ22",
            "crcy_cd": "USD",
            "fm_buy_qty": "",
            "fm_sll_qty": "",
            "fm_lqd_pfls_amt": "0.00",
            "fm_fee": "0.00",
            "fm_net_pfls_amt": "107437.50",
            "fm_ustl_buy_qty": "",
            "fm_ustl_sll_qty": "100",
            "fm_ustl_evlu_pfls_amt": "107437.50",
            "fm_ustl_evlu_pfls_amt2": "0.00",
            "fm_ustl_evlu_pfls_icdc_amt": "107437.50",
            "fm_ccld_avg_pric": "132.293125",
            "fm_ustl_agrm_amt": "13229312.50",
            "fm_opt_lqd_amt": "0.00"
        }
    ],
    "rt_cd": "0",
    "msg_cd": "KIOK0510",
    "msg1": "조회가 완료되었습니다                                                           "
}
```

---

## 해외선물옵션 일별 체결내역

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [해외선물옵션] 주문/계좌 |
| API 명 | 해외선물옵션 일별 체결내역 |
| API ID | 해외선물-011 |
| 실전 TR_ID | OTFM3122R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/overseas-futureoption/v1/trading/inquire-daily-ccld |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 291 |

### 개요

해외선물옵션 일별 체결내역 API입니다.
거래소 체결 내역에 따라 , output1에 동일한 주문번호의 데이터들이 수신될 수 있습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용)<br><br>※ 토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출<br>EX) "Bearer eyJ..........8GA" |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | OTFM3122R |
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
| CANO | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| STRT_DT | 시작일자 | string | Y | 8 | 시작일자(YYYYMMDD) |
| END_DT | 종료일자 | string | Y | 8 | 종료일자(YYYYMMDD) |
| FUOP_DVSN_CD | 선물옵션구분코드 | string | Y | 2 | 00:전체 / 01:선물 / 02:옵션 |
| FM_PDGR_CD | FM상품군코드 | string | Y | 10 | 공란(Default) |
| CRCY_CD | 통화코드 | string | Y | 3 | %%% : 전체<br>TUS: TOT_USD  / TKR: TOT_KRW<br>KRW: 한국  / USD: 미국<br>EUR: EUR   / HKD: 홍콩<br>CNY: 중국  / JPY: 일본<br>VND: 베트남 |
| FM_ITEM_FTNG_YN | FM종목합산여부 | string | Y | 1 | "N"(Default) |
| SLL_BUY_DVSN_CD | 매도매수구분코드 | string | Y | 2 | %%: 전체 / 01 : 매도 / 02 : 매수 |
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
| output2 | 응답상세2 | object | Y |  |  |
| fm_tot_ccld_qty | FM총체결수량 | string | Y | 10 |  |
| fm_tot_futr_agrm_amt | FM총선물약정금액 | string | Y | 20 |  |
| fm_tot_opt_agrm_amt | FM총옵션약정금액 | string | Y | 20 |  |
| fm_fee_smtl | FM수수료합계 | string | Y | 20 |  |
| output1 | 응답상세1 | object array | Y |  | Array |
| dt | 일자 | string | Y | 8 |  |
| ccno | 체결번호 | string | Y | 8 |  |
| ovrs_futr_fx_pdno | 해외선물FX상품번호 | string | Y | 32 |  |
| sll_buy_dvsn_cd | 매도매수구분코드 | string | Y | 3 |  |
| fm_ccld_qty | FM체결수량 | string | Y | 10 |  |
| fm_ccld_amt | FM체결금액 | string | Y | 20 |  |
| fm_futr_ccld_amt | FM선물체결금액 | string | Y | 20 |  |
| fm_opt_ccld_amt | FM옵션체결금액 | string | Y | 20 |  |
| crcy_cd | 통화코드 | string | Y | 3 |  |
| fm_fee | FM수수료 | string | Y | 20 |  |
| fm_futr_pure_agrm_amt | FM선물순약정금액 | string | Y | 20 |  |
| fm_opt_pure_agrm_amt | FM옵션순약정금액 | string | Y | 20 |  |
| ccld_dtl_dtime | 체결상세일시 | string | Y | 17 |  |
| ord_dt | 주문일자 | string | Y | 8 |  |
| odno | 주문번호 | string | Y | 8 | 접수한 주문의 일련번호(ex. 00360686) |
| ord_mdia_dvsn_name | 주문매체구분명 | string | Y | 60 |  |

### Example

**Request Example (Python)**

```
{
	"CANO":"80012345",
	"ACNT_PRDT_CD":"08",
	"STRT_DT":"20221010",
	"END_DT":"20221216",
	"FUOP_DVSN":"00",
	"FM_PDGR_CD":"",
	"CRCY_CD":"%%%",
	"FM_ITEM_FTNG_YN":"N",
	"SLL_BUY_DVSN_CD":"%%",
	"CTX_AREA_FK100":"",
	"CTX_AREA_NK100":"",
}
```

**Response Example**

```
{
    "ctx_area_fk200": "80012345^08^20221010^20221216^00^^%%%^N^%%^                                                                                                                                                             ",
    "ctx_area_nk200": "                                                                                                                                                                                                        ",
    "output1": [
        {
            "dt": "20221020",
            "ccno": "00004090",
            "ovrs_futr_fx_pdno": "6AZ22",
            "sll_buy_dvsn_cd": "02",
            "fm_ccld_qty": "1",
            "fm_ccld_amt": ".62955",
            "fm_futr_ccld_amt": "62955",
            "fm_opt_ccld_amt": "0",
            "crcy_cd": "USD",
            "fm_fee": "12.5",
            "fm_futr_pure_agrm_amt": "62967.5",
            "fm_opt_pure_agrm_amt": "0",
            "ccld_dtl_dtime": "20221020132204282",
            "ord_dt": "20221020",
            "odno": "00284471",
            "ord_mdia_dvsn_name": "일반"
        },
        {
            "dt": "20221020",
            "ccno": "00004089",
            "ovrs_futr_fx_pdno": "6AZ22",
            "sll_buy_dvsn_cd": "02",
            "fm_ccld_qty": "1",
            "fm_ccld_amt": ".62945",
            "fm_futr_ccld_amt": "62945",
            "fm_opt_ccld_amt": "0",
            "crcy_cd": "USD",
            "fm_fee": "12.5",
            "fm_futr_pure_agrm_amt": "62957.5",
            "fm_opt_pure_agrm_amt": "0",
            "ccld_dtl_dtime": "20221020125948252",
            "ord_dt": "20221020",
            "odno": "00284466",
            "ord_mdia_dvsn_name": "일반"
        }
    ],
    "output2": {
        "fm_tot_ccld_qty": "2",
        "fm_tot_futr_agrm_amt": "125900",
        "fm_tot_opt_agrm_amt": "0",
        "fm_fee_smtl": "25"
    },
    "rt_cd": "0",
    "msg_cd": "KIOK0510",
    "msg1": "조회가 완료되었습니다                                                           "
}
```

---

## 해외선물옵션 예수금현황

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [해외선물옵션] 주문/계좌 |
| API 명 | 해외선물옵션 예수금현황 |
| API ID | 해외선물-012 |
| 실전 TR_ID | OTFM1411R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/overseas-futureoption/v1/trading/inquire-deposit |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 292 |

### 개요

해외선물옵션 예수금현황 API입니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용)<br><br>※ 토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출<br>EX) "Bearer eyJ..........8GA" |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | OTFM1411R |
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
| CANO | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| CRCY_CD | 통화코드 | string | Y | 3 | TUS: TOT_USD  / TKR: TOT_KRW<br>KRW: 한국  / USD: 미국<br>EUR: EUR   / HKD: 홍콩<br>CNY: 중국  / JPY: 일본<br>VND: 베트남 |
| INQR_DT | 조회일자 | string | Y | 8 |  |

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
| output | 응답상세1 | object | Y |  |  |
| fm_nxdy_dncl_amt | FM익일예수금액 | string | Y | 20 |  |
| fm_tot_asst_evlu_amt | FM총자산평가금액 | string | Y | 20 |  |
| cano | 종합계좌번호 | string | Y | 8 |  |
| acnt_prdt_cd | 계좌상품코드 | string | Y | 2 |  |
| crcy_cd | 통화코드 | string | Y | 3 |  |
| resp_dt | 응답일자 | string | Y | 8 |  |
| fm_dnca_rmnd | FM예수금잔액 | string | Y | 20 |  |
| fm_lqd_pfls_amt | FM청산손익금액 | string | Y | 20 |  |
| fm_fee | FM수수료 | string | Y | 20 |  |
| fm_fuop_evlu_pfls_amt | FM선물옵션평가손익금액 | string | Y | 20 |  |
| fm_rcvb_amt | FM미수금액 | string | Y | 20 |  |
| fm_brkg_mgn_amt | FM위탁증거금액 | string | Y | 20 |  |
| fm_mntn_mgn_amt | FM유지증거금액 | string | Y | 20 |  |
| fm_add_mgn_amt | FM추가증거금액 | string | Y | 20 |  |
| fm_risk_rt | FM위험율 | string | Y | 10 |  |
| fm_ord_psbl_amt | FM주문가능금액 | string | Y | 20 |  |
| fm_drwg_psbl_amt | FM출금가능금액 | string | Y | 20 |  |
| fm_echm_rqrm_amt | FM환전요청금액 | string | Y | 20 |  |
| fm_drwg_prar_amt | FM출금예정금액 | string | Y | 20 |  |
| fm_opt_tr_chgs | FM옵션거래대금 | string | Y | 20 |  |
| fm_opt_icld_asst_evlu_amt | FM옵션포함자산평가금액 | string | Y | 20 |  |
| fm_opt_evlu_amt | FM옵션평가금액 | string | Y | 20 |  |
| fm_crcy_sbst_amt | FM통화대용금액 | string | Y | 20 |  |
| fm_crcy_sbst_use_amt | FM통화대용사용금액 | string | Y | 20 |  |
| fm_crcy_sbst_stup_amt | FM통화대용설정금액 | string | Y | 20 |  |

### Example

**Request Example (Python)**

```
{
	"CANO":"80012345",
	"ACNT_PRDT_CD":"08",
	"CRCY_CD":":"KRW",
	"INQR_DT":"20221214"
}
```

**Response Example**

```
{
    "output": {
        "cano": "81012345",
        "acnt_prdt_cd": "08",
        "crcy_cd": "KRW",
        "resp_dt": "20230104",
        "fm_dnca_rmnd": "9990000012",
        "fm_lqd_pfls_amt": "0",
        "fm_fee": "0",
        "fm_nxdy_dncl_amt": "9990000012",
        "fm_tot_asst_evlu_amt": "9990000012",
        "fm_fuop_evlu_pfls_amt": "0",
        "fm_rcvb_amt": "0",
        "fm_brkg_mgn_amt": "0",
        "fm_mntn_mgn_amt": "0",
        "fm_add_mgn_amt": "0",
        "fm_risk_rt": "0.00",
        "fm_ord_psbl_amt": "9718323936",
        "fm_drwg_psbl_amt": "9704739489",
        "fm_echm_rqrm_amt": "0",
        "fm_drwg_prar_amt": "0",
        "fm_opt_tr_chgs": "0",
        "fm_opt_icld_asst_evlu_amt": "9990000012",
        "fm_opt_evlu_amt": "0",
        "fm_crcy_sbst_amt": "0",
        "fm_crcy_sbst_use_amt": "0",
        "fm_crcy_sbst_stup_amt": "0"
    },
    "rt_cd": "0",
    "msg_cd": "KIOK0510",
    "msg1": "조회가 완료되었습니다                                                           "
}
```

---

## 해외선물옵션 일별 주문내역

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [해외선물옵션] 주문/계좌 |
| API 명 | 해외선물옵션 일별 주문내역 |
| API ID | 해외선물-013 |
| 실전 TR_ID | OTFM3120R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/overseas-futureoption/v1/trading/inquire-daily-order |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 293 |

### 개요

해외선물옵션 일별 주문내역 API입니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용)<br><br>※ 토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출<br>EX) "Bearer eyJ..........8GA" |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | OTFM3120R |
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
| CANO | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| STRT_DT | 시작일자 | string | Y | 8 |  |
| END_DT | 종료일자 | string | Y | 8 |  |
| FM_PDGR_CD | FM상품군코드 | string | Y | 10 |  |
| CCLD_NCCS_DVSN | 체결미체결구분 | string | Y | 2 | 01:전체 / 02:체결 / 03:미체결 |
| SLL_BUY_DVSN_CD | 매도매수구분코드 | string | Y | 2 | %%전체 / 01 : 매도 / 02 : 매수 |
| FUOP_DVSN | 선물옵션구분 | string | Y | 2 | 00:전체 / 01:선물 / 02:옵션 |
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
| output | 응답상세1 | object array | Y |  | Array |
| cano | 종합계좌번호 | string | Y | 8 |  |
| acnt_prdt_cd | 계좌상품코드 | string | Y | 2 |  |
| dt | 일자 | string | Y | 8 |  |
| ord_dt | 주문일자 | string | Y | 8 |  |
| odno | 주문번호 | string | Y | 8 | 접수한 주문의 일련번호(ex. 00360686)<br>* 정정/취소시 문자열처럼 "0"을 포함해서 전송 <br>  (ex. ORGN_ODNO : 00360686)<br>* 정정/취소시 문자열처럼 "0"을 포함해서 전송 <br>  (ex. ORGN_ODNO : 00360686) |
| orgn_ord_dt | 원주문일자 | string | Y | 8 |  |
| orgn_odno | 원주문번호 | string | Y | 8 | 원주문번호(ex. 00360685) |
| ovrs_futr_fx_pdno | 해외선물FX상품번호 | string | Y | 32 |  |
| rvse_cncl_dvsn_cd | 정정취소구분코드 | string | Y | 2 | 청산체결이 없는 신규	00<br>청산체결이 없는 정정	01<br>청산체결이 없는 취소	02<br>청산체결이 있는 취소	02<br>청산체결이 있는 신규	03<br>청산체결이 있는 정정	04<br>행사	05<br>배정	06<br>소멸	07<br>만기	08 |
| sll_buy_dvsn_cd | 매도매수구분코드 | string | Y | 2 |  |
| cplx_ord_dvsn_cd | 복합주문구분코드 | string | Y | 1 |  |
| pric_dvsn_cd | 가격구분코드 | string | Y | 1 |  |
| rcit_dvsn_cd | 접수구분코드 | string | Y | 2 |  |
| fm_ord_qty | FM주문수량 | string | Y | 10 |  |
| fm_ord_pric | FM주문가격 | string | Y | 20 |  |
| fm_stop_ord_pric | FMSTOP주문가격 | string | Y | 20 |  |
| ecis_rsvn_ord_yn | 행사예약주문여부 | string | Y | 1 |  |
| fm_ccld_qty | FM체결수량 | string | Y | 10 |  |
| fm_ccld_pric | FM체결가격 | string | Y | 20 |  |
| fm_ord_rmn_qty | FM주문잔여수량 | string | Y | 10 |  |
| ord_grp_name | 주문그룹명 | string | Y | 60 |  |
| rcit_dtl_dtime | 접수상세일시 | string | Y | 17 |  |
| ccld_dtl_dtime | 체결상세일시 | string | Y | 17 |  |
| ordr_emp_no | 주문자사원번호 | string | Y | 6 |  |
| rjct_rson_name | 거부사유명 | string | Y | 60 |  |
| ccld_cndt_cd | 체결조건코드 | string | Y | 1 |  |
| trad_end_dt | 매매종료일자 | string | Y | 8 |  |

### Example

**Request Example (Python)**

```
{
	"CANO":"12345678",
	"ACNT_PRDT_CD":"08",
	"STRT_DT":"20220101",
	"END_DT":"20221214",
	"FM_PDGR_CD":"",
	"CCLD_NCCS_DVSN":"01",
	"SLL_BUY_DVSN_CD":"%%",
	"FUOP_DVSN":"00",
	"CTX_AREA_FK200":"",
	"CTX_AREA_NK200":"",
}
```

**Response Example**

```
{
    "ctx_area_fk200": "12345678^08^20231206^20231206^^01^%%^00^                                                                                                                                                                ",
    "ctx_area_nk200": "                                                                                                                                                                                                        ",
    "output": [
        {
            "cano": "12345678",
            "acnt_prdt_cd": "08",
            "dt": "20231206",
            "ord_dt": "20231206",
            "odno": "00362398",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "6CZ23",
            "rvse_cncl_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "cplx_ord_dvsn_cd": "0",
            "pric_dvsn_cd": "2",
            "rcit_dvsn_cd": "02",
            "fm_ord_qty": "3",
            "fm_ord_pric": "0.00000",
            "fm_stop_ord_pric": "0.00000",
            "ecis_rsvn_ord_yn": "N",
            "fm_ccld_qty": "3",
            "fm_ccld_pric": "0.73935",
            "fm_ord_rmn_qty": "0",
            "ord_grp_name": "",
            "rcit_dtl_dtime": "20231206092306005",
            "ccld_dtl_dtime": "20231206092306005",
            "ordr_emp_no": "109171",
            "rjct_rson_name": "",
            "ccld_cndt_cd": "2",
            "trad_end_dt": ""
        },
        {
            "cano": "12345678",
            "acnt_prdt_cd": "08",
            "dt": "20231206",
            "ord_dt": "20231206",
            "odno": "00362397",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "6CZ23",
            "rvse_cncl_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "cplx_ord_dvsn_cd": "0",
            "pric_dvsn_cd": "2",
            "rcit_dvsn_cd": "02",
            "fm_ord_qty": "1",
            "fm_ord_pric": "0.00000",
            "fm_stop_ord_pric": "0.00000",
            "ecis_rsvn_ord_yn": "N",
            "fm_ccld_qty": "1",
            "fm_ccld_pric": "0.73925",
            "fm_ord_rmn_qty": "0",
            "ord_grp_name": "",
            "rcit_dtl_dtime": "20231206092247252",
            "ccld_dtl_dtime": "20231206092247252",
            "ordr_emp_no": "109171",
            "rjct_rson_name": "",
            "ccld_cndt_cd": "2",
            "trad_end_dt": ""
        },
        {
            "cano": "12345678",
            "acnt_prdt_cd": "08",
            "dt": "20231206",
            "ord_dt": "20231206",
            "odno": "00362396",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "6CZ23",
            "rvse_cncl_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "cplx_ord_dvsn_cd": "0",
            "pric_dvsn_cd": "2",
            "rcit_dvsn_cd": "02",
            "fm_ord_qty": "1",
            "fm_ord_pric": "0.00000",
            "fm_stop_ord_pric": "0.00000",
            "ecis_rsvn_ord_yn": "N",
            "fm_ccld_qty": "1",
            "fm_ccld_pric": "0.73920",
            "fm_ord_rmn_qty": "0",
            "ord_grp_name": "",
            "rcit_dtl_dtime": "20231206092123893",
            "ccld_dtl_dtime": "20231206092123893",
            "ordr_emp_no": "109171",
            "rjct_rson_name": "",
            "ccld_cndt_cd": "2",
            "trad_end_dt": ""
        },
        {
            "cano": "12345678",
            "acnt_prdt_cd": "08",
            "dt": "20231206",
            "ord_dt": "20231206",
            "odno": "00362395",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "6CZ23",
            "rvse_cncl_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "cplx_ord_dvsn_cd": "0",
            "pric_dvsn_cd": "2",
            "rcit_dvsn_cd": "02",
            "fm_ord_qty": "1",
            "fm_ord_pric": "0.00000",
            "fm_stop_ord_pric": "0.00000",
            "ecis_rsvn_ord_yn": "N",
            "fm_ccld_qty": "1",
            "fm_ccld_pric": "0.73915",
            "fm_ord_rmn_qty": "0",
            "ord_grp_name": "",
            "rcit_dtl_dtime": "20231206092039261",
            "ccld_dtl_dtime": "20231206092039261",
            "ordr_emp_no": "109171",
            "rjct_rson_name": "",
            "ccld_cndt_cd": "2",
            "trad_end_dt": ""
        },
        {
            "cano": "12345678",
            "acnt_prdt_cd": "08",
            "dt": "20231206",
            "ord_dt": "20231206",
            "odno": "00362394",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "10YZ23",
            "rvse_cncl_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "cplx_ord_dvsn_cd": "0",
            "pric_dvsn_cd": "2",
            "rcit_dvsn_cd": "03",
            "fm_ord_qty": "1",
            "fm_ord_pric": "0.000",
            "fm_stop_ord_pric": "0.000",
            "ecis_rsvn_ord_yn": "N",
            "fm_ccld_qty": "0",
            "fm_ccld_pric": "0.000",
            "fm_ord_rmn_qty": "0",
            "ord_grp_name": "",
            "rcit_dtl_dtime": "",
            "ccld_dtl_dtime": "",
            "ordr_emp_no": "109171",
            "rjct_rson_name": "[정상적인거부]Text[Order price is outside bands 'Bid of 4269",
            "ccld_cndt_cd": "2",
            "trad_end_dt": ""
        },
        {
            "cano": "12345678",
            "acnt_prdt_cd": "08",
            "dt": "20231206",
            "ord_dt": "20231206",
            "odno": "00362393",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "6AZ23",
            "rvse_cncl_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "cplx_ord_dvsn_cd": "0",
            "pric_dvsn_cd": "1",
            "rcit_dvsn_cd": "02",
            "fm_ord_qty": "2",
            "fm_ord_pric": "0.65000",
            "fm_stop_ord_pric": "0.00000",
            "ecis_rsvn_ord_yn": "N",
            "fm_ccld_qty": "0",
            "fm_ccld_pric": "0.00000",
            "fm_ord_rmn_qty": "0",
            "ord_grp_name": "",
            "rcit_dtl_dtime": "20231206091838237",
            "ccld_dtl_dtime": "",
            "ordr_emp_no": "45TesT",
            "rjct_rson_name": "FCM 거부됨",
            "ccld_cndt_cd": "6",
            "trad_end_dt": ""
        },
        {
            "cano": "12345678",
            "acnt_prdt_cd": "08",
            "dt": "20231206",
            "ord_dt": "20231206",
            "odno": "00362392",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "6AZ23",
            "rvse_cncl_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "cplx_ord_dvsn_cd": "0",
            "pric_dvsn_cd": "1",
            "rcit_dvsn_cd": "02",
            "fm_ord_qty": "2",
            "fm_ord_pric": "0.65000",
            "fm_stop_ord_pric": "0.00000",
            "ecis_rsvn_ord_yn": "N",
            "fm_ccld_qty": "0",
            "fm_ccld_pric": "0.00000",
            "fm_ord_rmn_qty": "0",
            "ord_grp_name": "",
            "rcit_dtl_dtime": "20231206091835180",
            "ccld_dtl_dtime": "",
            "ordr_emp_no": "45TesT",
            "rjct_rson_name": "FCM 거부됨",
            "ccld_cndt_cd": "6",
            "trad_end_dt": ""
        },
        {
            "cano": "12345678",
            "acnt_prdt_cd": "08",
            "dt": "20231206",
            "ord_dt": "20231206",
            "odno": "00362391",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "6AZ23",
            "rvse_cncl_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "cplx_ord_dvsn_cd": "0",
            "pric_dvsn_cd": "1",
            "rcit_dvsn_cd": "02",
            "fm_ord_qty": "2",
            "fm_ord_pric": "0.65000",
            "fm_stop_ord_pric": "0.00000",
            "ecis_rsvn_ord_yn": "N",
            "fm_ccld_qty": "0",
            "fm_ccld_pric": "0.00000",
            "fm_ord_rmn_qty": "0",
            "ord_grp_name": "",
            "rcit_dtl_dtime": "20231206083023955",
            "ccld_dtl_dtime": "",
            "ordr_emp_no": "45TesT",
            "rjct_rson_name": "FCM 거부됨",
            "ccld_cndt_cd": "6",
            "trad_end_dt": ""
        },
        {
            "cano": "12345678",
            "acnt_prdt_cd": "08",
            "dt": "20231206",
            "ord_dt": "20231206",
            "odno": "00362390",
            "orgn_ord_dt": "",
            "orgn_odno": "",
            "ovrs_futr_fx_pdno": "6AZ23",
            "rvse_cncl_dvsn_cd": "00",
            "sll_buy_dvsn_cd": "02",
            "cplx_ord_dvsn_cd": "0",
            "pric_dvsn_cd": "1",
            "rcit_dvsn_cd": "02",
            "fm_ord_qty": "2",
            "fm_ord_pric": "0.65000",
            "fm_stop_ord_pric": "0.00000",
            "ecis_rsvn_ord_yn": "N",
            "fm_ccld_qty": "0",
            "fm_ccld_pric": "0.00000",
            "fm_ord_rmn_qty": "0",
            "ord_grp_name": "",
            "rcit_dtl_dtime": "20231206082401404",
            "ccld_dtl_dtime": "",
            "ordr_emp_no": "45TesT",
            "rjct_rson_name": "FCM 거부됨",
            "ccld_cndt_cd": "6",
            "trad_end_dt": ""
        }
    ],
    "rt_cd": "0",
    "msg_cd": "KIOK0510",
```

---

## 해외선물옵션 기간계좌거래내역

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [해외선물옵션] 주문/계좌 |
| API 명 | 해외선물옵션 기간계좌거래내역 |
| API ID | 해외선물-014 |
| 실전 TR_ID | OTFM3114R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/overseas-futureoption/v1/trading/inquire-period-trans |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 294 |

### 개요

해외선물옵션 기간계좌거래내역 API입니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용)<br><br>※ 토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출<br>EX) "Bearer eyJ..........8GA" |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | OTFM3114R |
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
| INQR_TERM_FROM_DT | 조회기간FROM일자 | string | Y | 8 |  |
| INQR_TERM_TO_DT | 조회기간TO일자 | string | Y | 8 |  |
| CANO | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| ACNT_PRDT_CD | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| ACNT_TR_TYPE_CD | 계좌거래유형코드 | string | Y | 2 | 1: 전체, 2:입출금 , 3: 결제 |
| CRCY_CD | 통화코드 | string | Y | 3 | '%%% : 전체<br>TUS: TOT_USD  / TKR: TOT_KRW<br>KRW: 한국  / USD: 미국<br>EUR: EUR   / HKD: 홍콩<br>CNY: 중국  / JPY: 일본<br>VND: 베트남  ' |
| CTX_AREA_FK100 | 연속조회검색조건100 | string | Y | 100 | 공란 : 최초 조회시<br>이전 조회 Output CTX_AREA_FK100값 : 다음페이지 조회시(2번째부터) |
| CTX_AREA_NK100 | 연속조회키100 | string | Y | 100 | 공란 : 최초 조회시<br>이전 조회 Output CTX_AREA_NK100값 : 다음페이지 조회시(2번째부터) |
| PWD_CHK_YN | 비밀번호체크여부 | string | Y | 1 | 공란(Default) |

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
| output | 응답상세1 | object array | Y |  | Array |
| bass_dt | 기준일자 | string | Y | 8 |  |
| cano | 종합계좌번호 | string | Y | 8 |  |
| acnt_prdt_cd | 계좌상품코드 | string | Y | 2 |  |
| fm_ldgr_inog_seq | FM원장출납순번 | string | Y | 10 |  |
| acnt_tr_type_name | 계좌거래유형명 | string | Y | 60 |  |
| crcy_cd | 통화코드 | string | Y | 3 |  |
| tr_itm_name | 거래항목명 | string | Y | 60 |  |
| fm_iofw_amt | FM입출금액 | string | Y | 20 |  |
| fm_fee | FM수수료 | string | Y | 20 |  |
| fm_tax_amt | FM세금금액 | string | Y | 20 |  |
| fm_sttl_amt | FM결제금액 | string | Y | 20 |  |
| fm_bf_dncl_amt | FM이전예수금액 | string | Y | 20 |  |
| fm_dncl_amt | FM예수금액 | string | Y | 20 |  |
| fm_rcvb_occr_amt | FM미수발생금액 | string | Y | 20 |  |
| fm_rcvb_pybk_amt | FM미수변제금액 | string | Y | 20 |  |
| ovdu_int_pybk_amt | 연체이자변제금액 | string | Y | 20 |  |
| rmks_text | 비고내용 | string | Y | 500 |  |

### Example

**Request Example (Python)**

```
{
	"INQR_TERM_FROM_DT":"20220101",
	"INQR_TERM_TO_DT":"20221214",
	"CANO":"80012345",
	"ACNT_PRDT_CD":"08",
	"ACNT_TR_TYPE_CD":"%%",
	"CRCY_CD":"%%%",
	"CTX_AREA_FK100":"",
	"CTX_AREA_NK100":"",
	"PWD_CHK_YN":""
}
```

**Response Example**

```
{
    "ctx_area_fk100": "20220101^20221214^81012345^08^%%^%%%^                                                               ",
    "ctx_area_nk100": "                                                                                                    ",
    "output": [],
    "rt_cd": "0",
    "msg_cd": "KIOK0560",
    "msg1": "조회할 내용이 없습니다                                                          "
}
```

---

## 해외선물옵션 증거금상세

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [해외선물옵션] 주문/계좌 |
| API 명 | 해외선물옵션 증거금상세 |
| API ID | 해외선물-032 |
| 실전 TR_ID | OTFM3115R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/overseas-futureoption/v1/trading/margin-detail |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 미지원 |
| 순번 | 295 |

### 개요

해외선물옵션 증거금상세 API입니다.
한국투자 HTS(eFriend Plus) &gt; [2711] 해외선물옵션 증거금상세 화면 의 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

[증거금 상세설명]
- SPAN, EUREX 증거금
1. 가격변동증거금 : 보유하고 있는 미결제를 Product Class 별로 구간[SPAN-16구간, EUREX-29구간)손익 합계액 산출하며 최대손실구간의 금액을 해당 Class의 증거금으로 산정
2. 스프레드증거금 : 보유하고 있는 미결제를 Product Class 별로 스프레드 산정하며 스프레드 증거금 적용
** 스프레드 산정방법 : SPAN은 선물+옵션의 Delta Spread로 계산, EUREX는 선물의 Spread만 산정 보유중인 옵선가치를 평가하며 청산가치가 양수(고객미 수취할 금액이 있는 경우)에 해당하는 금액을 증거금에서 할인
3. 옵션가격증거금 : 보유중인 옵션가치를 평가하여 청산가치가 양수(고객이 수취할 금액이 있는 경우)에 해당하는 금액을 증거금에서 할인
**계산식 : MAXID, 온선평가대금 Class별 합계액) ** 산출된 값을 음수처리함 옵션 미결제약정에 대해 최소로 징구하는 증거금
4. 옵선최소증거금 증거금 : 옵션 미결제약정에 대해 최소로 징구하는 증거금
﻿** SPAN : 매도옵선회소증거금(행사가별로 상미)과 매수옵선최소증거금(계약당 1Tick에 해당하는 금액)
** EUREX : 매수옵선최소증거금(계약당 1Tick에 해당하는 금액)(EUREX는 매도옵션최소증거금이 가격변동증거금에 포함되어 있음)
5. 일방해소증거금 : (기본개념)보유중인 포트폴리오 중에서 머느 일방향을 전량 청산했을 경우 잔존하는 미결제 약정의 최대손실가능액을 사전에 징구함
가격상승포지션과 가격하락포지션에 대해 최불리증거금을 각각 산정하며 큰 금액을 증거금으로 장구
﻿* 가격장승포지션 : 선물매수포지션, 풋옵션매도포지션
﻿* 가격하락포지션 : 선물매도포지션, 콜옵션매도포지선

- 일반 증거금
1. 선물미결제증거금 : 선물미결제약정에 대해 계약당증거금율 적용
2. 매도옵션미결제증거금 : 매도옵션미결제약정에 대해 옵선계약당 증거금을 적용
** 옵션계약당증거금 : 각 종목별 최불리증거금액으로 해외 거래소에서 계산하며 제공되는 데이터임
3. 매수옵션미결제증거금 : 매수옵션최소증거금으로 1Tick에 해당하는 금액을 적용

- 주문 증거금
1. 선물 주문증거금 : 선물 미체결주문에 대해 계약당 증거금을 적용(신규주문에 한해 징수)
2. 매도옵션 주문증거금 : 옵션매도 미체결주문에 대해 계약당증거금을 적용(신규주문에 한해 징수)
3. 매수옵션 주문증거금 : 옵션매수 미체결주문에 대해 최소증거금(Tick Value와 10 중에서 큰 금액)과 만기행사예약한 미체결주문에 대한 행사예약증거금을 징수
4. 매수옵션 주문대금 : 옵션매수 미체결주문의 매수대금(주문가격을 기준으로 대금 산정, 시장가주문시 현재가 +50틱으로 매수대금 산정)
5. 매수옵선행사예약증거금 : 옵선매수 미결제약정 중에서 행사예약한 수량에 대해 기초자산선물의 계약당 증거금을 징수

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | OTFM3115R |
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
| CRCY_CD | 통화코드 | string | Y | 3 | 'TKR(TOT_KRW), TUS(TOT_USD), <br>USD(미국달러), HKD(홍콩달러),<br>CNY(중국위안화), JPY )일본엔화), VND(베트남동)' |
| INQR_DT | 조회일자 | string | Y | 8 |  |

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
| output | 응답상세 | object | Y |  |  |
| cano | 종합계좌번호 | string | Y | 8 |  |
| acnt_prdt_cd | 계좌상품코드 | string | Y | 2 |  |
| crcy_cd | 통화코드 | string | Y | 3 |  |
| resp_dt | 응답일자 | string | Y | 8 |  |
| acnt_net_risk_mgna_aply_yn | 계좌순위험증거금적용여부 | string | Y | 1 |  |
| fm_ord_psbl_amt | FM주문가능금액 | string | Y | 20 |  |
| fm_add_mgn_amt | FM추가증거금액 | string | Y | 20 |  |
| fm_brkg_mgn_amt | FM위탁증거금액 | string | Y | 20 |  |
| fm_excc_brkg_mgn_amt | FM정산위탁증거금액 | string | Y | 20 |  |
| fm_ustl_mgn_amt | FM미결제증거금액 | string | Y | 20 |  |
| fm_mntn_mgn_amt | FM유지증거금액 | string | Y | 20 |  |
| fm_ord_mgn_amt | FM주문증거금액 | string | Y | 20 |  |
| fm_futr_ord_mgn_amt | FM선물주문증거금액 | string | Y | 20 |  |
| fm_opt_buy_ord_amt | FM옵션매수주문금액 | string | Y | 20 |  |
| fm_opt_sll_ord_mgn_amt | FM옵션매도주문증거금액 | string | Y | 20 |  |
| fm_opt_buy_ord_mgn_amt | FM옵션매수주문증거금액 | string | Y | 20 |  |
| fm_ecis_rsvn_mgn_amt | FM행사예약증거금액 | string | Y | 20 |  |
| fm_span_brkg_mgn_amt | FMSPAN위탁증거금액 | string | Y | 20 |  |
| fm_span_pric_altr_mgn_amt | FMSPAN가격변동증거금액 | string | Y | 20 |  |
| fm_span_term_sprd_mgn_amt | FMSPAN기간스프레드증거금액 | string | Y | 20 |  |
| fm_span_buy_opt_min_mgn_amt | FMSPAN옵션가격증거금액 | string | Y | 20 |  |
| fm_span_opt_min_mgn_amt | FMSPAN옵션최소증거금액 | string | Y | 20 |  |
| fm_span_tot_risk_mgn_amt | FMSPAN총위험증거금액 | string | Y | 20 |  |
| fm_span_mntn_mgn_amt | FMSPAN유지증거금액 | string | Y | 20 |  |
| fm_span_mntn_pric_altr_mgn_amt | FMSPAN유지가격변동증거금액 | string | Y | 20 |  |
| fm_span_mntn_term_sprd_mgn_amt | FMSPAN유지기간스프레드증거금액 | string | Y | 20 |  |
| fm_span_mntn_opt_pric_mgn_amt | FMSPAN유지옵션가격증거금액 | string | Y | 20 |  |
| fm_span_mntn_opt_min_mgn_amt | FMSPAN유지옵션최소증거금액 | string | Y | 20 |  |
| fm_span_mntn_tot_risk_mgn_amt | FMSPAN유지총위험증거금액 | string | Y | 20 |  |
| fm_eurx_brkg_mgn_amt | FMEUREX위탁증거금액 | string | Y | 20 |  |
| fm_eurx_pric_altr_mgn_amt | FMEUREX가격변동증거금액 | string | Y | 20 |  |
| fm_eurx_term_sprd_mgn_amt | FMEUREX기간스프레드증거금액 | string | Y | 20 |  |
| fm_eurx_opt_pric_mgn_amt | FMEUREX옵션가격증거금액 | string | Y | 20 |  |
| fm_eurx_buy_opt_min_mgn_amt | FMEUREX매수옵션최소증거금액 | string | Y | 20 |  |
| fm_eurx_tot_risk_mgn_amt | FMEUREX총위험증거금액 | string | Y | 20 |  |
| fm_eurx_mntn_mgn_amt | FMEUREX유지증거금액 | string | Y | 20 |  |
| fm_eurx_mntn_pric_altr_mgn_amt | FMEUREX유지가격변동증거금액 | string | Y | 20 |  |
| fm_eurx_mntn_term_sprd_mgn_amt | FMEUREX기간스프레드증거금액 | string | Y | 20 |  |
| fm_eurx_mntn_opt_pric_mgn_amt | FMEUREX유지옵션가격증거금액 | string | Y | 20 |  |
| fm_eurx_mntn_tot_risk_mgn_amt | FMEUREX유지총위험증거금액 | string | Y | 20 |  |
| fm_gnrl_brkg_mgn_amt | FM일반위탁증거금액 | string | Y | 20 |  |
| fm_futr_ustl_mgn_amt | FM선물미결제증거금액 | string | Y | 20 |  |
| fm_sll_opt_ustl_mgn_amt | FM매도옵션미결제증거금액 | string | Y | 20 |  |
| fm_buy_opt_ustl_mgn_amt | FM매수옵션미결제증거금액 | string | Y | 20 |  |
| fm_sprd_ustl_mgn_amt | FM스프레드미결제증거금액 | string | Y | 20 |  |
| fm_avg_dsct_mgn_amt | FMAVG할인증거금액 | string | Y | 20 |  |
| fm_gnrl_mntn_mgn_amt | FM일반유지증거금액 | string | Y | 20 |  |
| fm_futr_mntn_mgn_amt | FM선물유지증거금액 | string | Y | 20 |  |
| fm_opt_mntn_mgn_amt | FM옵션유지증거금액 | string | Y | 20 |  |

### Example

**Request Example (Python)**

```
CANO:12345678
ACNT_PRDT_CD:08
CRCY_CD:TKR
INQR_DT:20240522
```

**Response Example**

```
{
    "output": {
        "cano": "12345678",
        "acnt_prdt_cd": "08",
        "crcy_cd": "TKR",
        "resp_dt": "20240522",
        "acnt_net_risk_mgna_aply_yn": "Y",
        "fm_ord_psbl_amt": "86128052",
        "fm_add_mgn_amt": "0",
        "fm_brkg_mgn_amt": "49082990",
        "fm_excc_brkg_mgn_amt": "49082990",
        "fm_ustl_mgn_amt": "49082990",
        "fm_mntn_mgn_amt": "44620900",
        "fm_ord_mgn_amt": "0",
        "fm_futr_ord_mgn_amt": "0",
        "fm_opt_buy_ord_amt": "0",
        "fm_opt_sll_ord_mgn_amt": "0",
        "fm_opt_buy_ord_mgn_amt": "0",
        "fm_ecis_rsvn_mgn_amt": "0",
        "fm_span_brkg_mgn_amt": "49082990",
        "fm_span_pric_altr_mgn_amt": "49082990",
        "fm_span_term_sprd_mgn_amt": "0",
        "fm_span_buy_opt_min_mgn_amt": "0",
        "fm_span_opt_min_mgn_amt": "0",
        "fm_span_tot_risk_mgn_amt": "49082990",
        "fm_span_mntn_mgn_amt": "44620900",
        "fm_span_mntn_pric_altr_mgn_amt": "44620900",
        "fm_span_mntn_term_sprd_mgn_amt": "0",
        "fm_span_mntn_opt_pric_mgn_amt": "0",
        "fm_span_mntn_opt_min_mgn_amt": "0",
        "fm_span_mntn_tot_risk_mgn_amt": "44620900",
        "fm_eurx_brkg_mgn_amt": "0",
        "fm_eurx_pric_altr_mgn_amt": "0",
        "fm_eurx_term_sprd_mgn_amt": "0",
        "fm_eurx_opt_pric_mgn_amt": "0",
        "fm_eurx_buy_opt_min_mgn_amt": "0",
        "fm_eurx_tot_risk_mgn_amt": "0",
        "fm_eurx_mntn_mgn_amt": "0",
        "fm_eurx_mntn_pric_altr_mgn_amt": "0",
        "fm_eurx_mntn_term_sprd_mgn_amt": "0",
        "fm_eurx_mntn_opt_pric_mgn_amt": "0",
        "fm_eurx_mntn_tot_risk_mgn_amt": "0",
        "fm_gnrl_brkg_mgn_amt": "0",
        "fm_futr_ustl_mgn_amt": "0",
        "fm_sll_opt_ustl_mgn_amt": "0",
        "fm_buy_opt_ustl_mgn_amt": "0",
        "fm_sprd_ustl_mgn_amt": "0",
        "fm_avg_dsct_mgn_amt": "0",
        "fm_gnrl_mntn_mgn_amt": "0",
        "fm_futr_mntn_mgn_amt": "0",
        "fm_opt_mntn_mgn_amt": "0"
    },
    "rt_cd": "0",
    "msg_cd": "KIOK0510",
    "msg1": "조회가 완료되었습니다                                                           "
}
```

---
