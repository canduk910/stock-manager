# 장내채권 기본시세

**카테고리 코드**: `[장내채권] 기본시세`  
**API 수**: 8개

> 출처: 한국투자증권 OpenAPI 전체 문서 (2026-05-08).  
> 자동 변환: `scripts/kis_excel_to_md.py`

---

## 목차

- [장내채권현재가(호가)](#장내채권현재가호가) — `GET` `/uapi/domestic-bond/v1/quotations/inquire-asking-price` (실전 TR_ID: `FHKBJ773401C0`)
- [장내채권현재가(시세)](#장내채권현재가시세) — `GET` `/uapi/domestic-bond/v1/quotations/inquire-price` (실전 TR_ID: `FHKBJ773400C0`)
- [장내채권현재가(체결)](#장내채권현재가체결) — `GET` `/uapi/domestic-bond/v1/quotations/inquire-ccnl` (실전 TR_ID: `FHKBJ773403C0`)
- [장내채권현재가(일별)](#장내채권현재가일별) — `GET` `/uapi/domestic-bond/v1/quotations/inquire-daily-price` (실전 TR_ID: `FHKBJ773404C0`)
- [장내채권 기간별시세(일)](#장내채권-기간별시세일) — `GET` `/uapi/domestic-bond/v1/quotations/inquire-daily-itemchartprice` (실전 TR_ID: `FHKBJ773701C0`)
- [장내채권 평균단가조회](#장내채권-평균단가조회) — `GET` `/uapi/domestic-bond/v1/quotations/avg-unit` (실전 TR_ID: `CTPF2005R`)
- [장내채권 발행정보](#장내채권-발행정보) — `GET` `/uapi/domestic-bond/v1/quotations/issue-info` (실전 TR_ID: `CTPF1101R`)
- [장내채권 기본조회](#장내채권-기본조회) — `GET` `/uapi/domestic-bond/v1/quotations/search-bond-info` (실전 TR_ID: `CTPF1114R`)

---

## 장내채권현재가(호가)

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 기본시세 |
| API 명 | 장내채권현재가(호가) |
| API ID | 국내주식-132 |
| 실전 TR_ID | FHKBJ773401C0 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/quotations/inquire-asking-price |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 327 |

### 개요

장내채권현재가(호가) API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0978] 장내채권주문 "우측 호가창" 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | FHKBJ773401C0 |
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
| FID_COND_MRKT_DIV_CODE | 조건 시장 분류 코드 | string | Y | 2 | B: 장내 |
| FID_INPUT_ISCD | 입력 종목코드 | string | Y | 12 | 채권종목코드<br>ex. KR2088012A16 |

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
| output | 응답상세 | object | Y |  |  |
| aspr_acpt_hour | 호가 접수 시간 | string | Y | 6 |  |
| bond_askp1 | 채권 매도호가1 | string | Y | 112 |  |
| bond_askp2 | 채권 매도호가2 | string | Y | 112 |  |
| bond_askp3 | 채권 매도호가3 | string | Y | 112 |  |
| bond_askp4 | 채권 매도호가4 | string | Y | 112 |  |
| bond_askp5 | 채권 매도호가5 | string | Y | 112 |  |
| bond_bidp1 | 채권 매수호가1 | string | Y | 112 |  |
| bond_bidp2 | 채권 매수호가2 | string | Y | 112 |  |
| bond_bidp3 | 채권 매수호가3 | string | Y | 112 |  |
| bond_bidp4 | 채권 매수호가4 | string | Y | 112 |  |
| bond_bidp5 | 채권 매수호가5 | string | Y | 112 |  |
| askp_rsqn1 | 매도호가 잔량1 | string | Y | 12 |  |
| askp_rsqn2 | 매도호가 잔량2 | string | Y | 12 |  |
| askp_rsqn3 | 매도호가 잔량3 | string | Y | 12 |  |
| askp_rsqn4 | 매도호가 잔량4 | string | Y | 12 |  |
| askp_rsqn5 | 매도호가 잔량5 | string | Y | 12 |  |
| bidp_rsqn1 | 매수호가 잔량1 | string | Y | 12 |  |
| bidp_rsqn2 | 매수호가 잔량2 | string | Y | 12 |  |
| bidp_rsqn3 | 매수호가 잔량3 | string | Y | 12 |  |
| bidp_rsqn4 | 매수호가 잔량4 | string | Y | 12 |  |
| bidp_rsqn5 | 매수호가 잔량5 | string | Y | 12 |  |
| total_askp_rsqn | 총 매도호가 잔량 | string | Y | 12 |  |
| total_bidp_rsqn | 총 매수호가 잔량 | string | Y | 12 |  |
| ntby_aspr_rsqn | 순매수 호가 잔량 | string | Y | 12 |  |
| seln_ernn_rate1 | 매도 수익 비율1 | string | Y | 84 |  |
| seln_ernn_rate2 | 매도 수익 비율2 | string | Y | 84 |  |
| seln_ernn_rate3 | 매도 수익 비율3 | string | Y | 84 |  |
| seln_ernn_rate4 | 매도 수익 비율4 | string | Y | 84 |  |
| seln_ernn_rate5 | 매도 수익 비율5 | string | Y | 84 |  |
| shnu_ernn_rate1 | 매수2 수익 비율1 | string | Y | 84 |  |
| shnu_ernn_rate2 | 매수2 수익 비율2 | string | Y | 84 |  |
| shnu_ernn_rate3 | 매수2 수익 비율3 | string | Y | 84 |  |
| shnu_ernn_rate4 | 매수2 수익 비율4 | string | Y | 84 |  |
| shnu_ernn_rate5 | 매수2 수익 비율5 | string | Y | 84 |  |

### Example

**Request Example (Python)**

```
FID_COND_MRKT_DIV_CODE:B
FID_INPUT_ISCD:KR2088012A16
```

**Response Example**

```
{
    "output": {
        "aspr_acpt_hour": "094618",
        "bond_askp1": "0.00",
        "bond_askp2": "0.00",
        "bond_askp3": "0.00",
        "bond_askp4": "0.00",
        "bond_askp5": "0.00",
        "bond_bidp1": "10190.20",
        "bond_bidp2": "10189.70",
        "bond_bidp3": "10189.40",
        "bond_bidp4": "10188.90",
        "bond_bidp5": "10188.60",
        "askp_rsqn1": "0",
        "askp_rsqn2": "0",
        "askp_rsqn3": "0",
        "askp_rsqn4": "0",
        "askp_rsqn5": "0",
        "bidp_rsqn1": "320138",
        "bidp_rsqn2": "53685",
        "bidp_rsqn3": "9081",
        "bidp_rsqn4": "8232",
        "bidp_rsqn5": "4020",
        "total_askp_rsqn": "0",
        "total_bidp_rsqn": "425156",
        "ntby_aspr_rsqn": "425156",
        "seln_ernn_rate1": "0.000",
        "seln_ernn_rate2": "0.000",
        "seln_ernn_rate3": "0.000",
        "seln_ernn_rate4": "0.000",
        "seln_ernn_rate5": "0.000",
        "shnu_ernn_rate1": "4.549",
        "shnu_ernn_rate2": "4.556",
        "shnu_ernn_rate3": "4.560",
        "shnu_ernn_rate4": "4.567",
        "shnu_ernn_rate5": "4.571"
    },
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다."
}
```

---

## 장내채권현재가(시세)

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 기본시세 |
| API 명 | 장내채권현재가(시세) |
| API ID | 국내주식-200 |
| 실전 TR_ID | FHKBJ773400C0 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/quotations/inquire-price |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 328 |

### 개요

장내채권현재가(시세) API입니다.
장내채권의 기본시세(시가,고가,저가,종가)를 확인할 수 있습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | FHKBJ773400C0 |
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
| FID_COND_MRKT_DIV_CODE | 조건시장분류코드 | string | Y | 2 | B (업종코드) |
| FID_INPUT_ISCD | 입력종목코드 | string | Y | 12 | 채권종목코드(ex KR2033022D33) |

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
| output | 응답상세 | object | Y |  |  |
| stnd_iscd | 표준종목코드 | string | Y | 12 |  |
| hts_kor_isnm | HTS한글종목명 | string | Y | 40 |  |
| bond_prpr | 채권현재가 | string | Y | 112 |  |
| prdy_vrss_sign | 전일대비부호 | string | Y | 1 |  |
| bond_prdy_vrss | 채권전일대비 | string | Y | 112 |  |
| prdy_ctrt | 전일대비율 | string | Y | 82 |  |
| acml_vol | 누적거래량 | string | Y | 18 |  |
| bond_prdy_clpr | 채권전일종가 | string | Y | 112 |  |
| bond_oprc | 채권시가2 | string | Y | 112 |  |
| bond_hgpr | 채권고가 | string | Y | 112 |  |
| bond_lwpr | 채권저가 | string | Y | 112 |  |
| ernn_rate | 수익비율 | string | Y | 84 |  |
| oprc_ert | 시가2수익률 | string | Y | 72 |  |
| hgpr_ert | 최고가수익률 | string | Y | 72 |  |
| lwpr_ert | 최저가수익률 | string | Y | 72 |  |
| bond_mxpr | 채권상한가 | string | Y | 112 |  |
| bond_llam | 채권하한가 | string | Y | 112 |  |

### Example

**Request Example (Python)**

```
FID_COND_MRKT_DIV_CODE:B
FID_INPUT_ISCD:KR6095572D81
```

**Response Example**

```
{
    "output": {
        "stnd_iscd": "KR6095572D81",
        "hts_kor_isnm": "AJ네트웍스63-2",
        "bond_prpr": "10265.00",
        "prdy_vrss_sign": "5",
        "bond_prdy_vrss": "-15.00",
        "prdy_ctrt": "-0.15",
        "acml_vol": "110000",
        "bond_prdy_clpr": "10280.00",
        "bond_oprc": "10265.00",
        "bond_hgpr": "10265.00",
        "bond_lwpr": "10265.00",
        "ernn_rate": "4.478",
        "oprc_ert": "4.478",
        "hgpr_ert": "4.478",
        "lwpr_ert": "4.478",
        "bond_mxpr": "13364.00",
        "bond_llam": "7196.00"
    },
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다."
}
```

---

## 장내채권현재가(체결)

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 기본시세 |
| API 명 | 장내채권현재가(체결) |
| API ID | 국내주식-201 |
| 실전 TR_ID | FHKBJ773403C0 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/quotations/inquire-ccnl |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 329 |

### 개요

장내채권현재가(체결) API입니다
장내채권의 체결데이터를 확인할 수 있습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | FHKBJ773403C0 |
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
| FID_COND_MRKT_DIV_CODE | 조건시장분류코드 | string | Y | 2 | B (업종코드) |
| FID_INPUT_ISCD | 입력종목코드 | string | Y | 12 | 채권종목코드(ex KR2033022D33) |

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
| output | 응답상세 | object | Y |  |  |
| stck_cntg_hour | 주식 체결 시간 | string | Y | 6 |  |
| bond_prpr | 채권 현재가 | string | Y | 112 |  |
| bond_prdy_vrss | 채권 전일 대비 | string | Y | 112 |  |
| prdy_vrss_sign | 전일 대비 부호 | string | Y | 1 |  |
| prdy_ctrt | 전일 대비율 | string | Y | 82 |  |
| cntg_vol | 체결 거래량 | string | Y | 18 |  |
| acml_vol | 누적 거래량 | string | Y | 18 |  |

### Example

**Request Example (Python)**

```
FID_COND_MRKT_DIV_CODE:B
FID_INPUT_ISCD:KR6095572D81
```

**Response Example**

```
{
    "output": [
        {
            "stck_cntg_hour": "091632",
            "bond_prpr": "10265.00",
            "bond_prdy_vrss": "-15.00",
            "prdy_vrss_sign": "5",
            "prdy_ctrt": "-0.15",
            "cntg_vol": "110000",
            "acml_vol": "110000"
        }
    ],
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다."
}
```

---

## 장내채권현재가(일별)

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 기본시세 |
| API 명 | 장내채권현재가(일별) |
| API ID | 국내주식-202 |
| 실전 TR_ID | FHKBJ773404C0 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/quotations/inquire-daily-price |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 330 |

### 개요

장내채권현재가(일별) API입니다. 
장내채권의 일별 시세데이터를 최근 100건까지 확인할 수 있습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | FHKBJ773404C0 |
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
| FID_COND_MRKT_DIV_CODE | 조건시장분류코드 | string | Y | 2 | B (업종코드) |
| FID_INPUT_ISCD | 입력종목코드 | string | Y | 12 | 채권종목코드(ex KR2033022D33) |

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
| output | 응답상세 | object | Y |  |  |
| stck_bsop_date | 주식영업일자 | string | Y | 8 |  |
| bond_prpr | 채권현재가 | string | Y | 112 |  |
| bond_prdy_vrss | 채권전일대비 | string | Y | 112 |  |
| prdy_vrss_sign | 전일대비부호 | string | Y | 1 |  |
| prdy_ctrt | 전일대비율 | string | Y | 82 |  |
| acml_vol | 누적거래량 | string | Y | 18 |  |
| bond_oprc | 채권시가2 | string | Y | 112 |  |
| bond_hgpr | 채권고가 | string | Y | 112 |  |
| bond_lwpr | 채권저가 | string | Y | 112 |  |

### Example

**Request Example (Python)**

```
FID_COND_MRKT_DIV_CODE:B
FID_INPUT_ISCD:KR6095572D81
```

**Response Example**

```
{
    "output": [
        {
            "stck_bsop_date": "20240503",
            "bond_prpr": "10265.00",
            "bond_prdy_vrss": "-15.00",
            "prdy_vrss_sign": "5",
            "prdy_ctrt": "-0.15",
            "acml_vol": "110000",
            "bond_oprc": "10265.00",
            "bond_hgpr": "10265.00",
            "bond_lwpr": "10265.00"
        },
        {
            "stck_bsop_date": "20240502",
            "bond_prpr": "10280.00",
            "bond_prdy_vrss": "-145.00",
            "prdy_vrss_sign": "5",
            "prdy_ctrt": "-1.39",
            "acml_vol": "61278",
            "bond_oprc": "10280.00",
            "bond_hgpr": "10280.00",
            "bond_lwpr": "10280.00"
        },
        {
            "stck_bsop_date": "20240430",
            "bond_prpr": "10425.00",
            "bond_prdy_vrss": "5.00",
            "prdy_vrss_sign": "2",
            "prdy_ctrt": "0.05",
            "acml_vol": "5012",
            "bond_oprc": "10425.00",
            "bond_hgpr": "10425.00",
            "bond_lwpr": "10425.00"
        },
        {
            "stck_bsop_date": "20240429",
            "bond_prpr": "10420.00",
            "bond_prdy_vrss": "-30.00",
            "prdy_vrss_sign": "5",
            "prdy_ctrt": "-0.29",
            "acml_vol": "9999",
            "bond_oprc": "10420.00",
            "bond_hgpr": "10420.00",
            "bond_lwpr": "10420.00"
        },
        {
            "stck_bsop_date": "20240426",
            "bond_prpr": "10450.00",
            "bond_prdy_vrss": "10.30",
            "prdy_vrss_sign": "2",
            "prdy_ctrt": "0.10",
            "acml_vol": "102001",
            "bond_oprc": "10430.00",
            "bond_hgpr": "10450.00",
            "bond_lwpr": "10430.00"
        },
        {
            "stck_bsop_date": "20240425",
            "bond_prpr": "10439.70",
            "bond_prdy_vrss": "39.70",
            "prdy_vrss_sign": "2",
            "prdy_ctrt": "0.38",
            "acml_vol": "5718",
            "bond_oprc": "10290.00",
            "bond_hgpr": "10439.70",
            "bond_lwpr": "10290.00"
        },
        {
            "stck_bsop_date": "20240424",
            "bond_prpr": "10400.00",
            "bond_prdy_vrss": "-100.00",
            "prdy_vrss_sign": "5",
            "prdy_ctrt": "-0.95",
            "acml_vol": "3000",
            "bond_oprc": "10400.00",
            "bond_hgpr": "10400.00",
            "bond_lwpr": "10400.00"
        },
        {
            "stck_bsop_date": "20240423",
            "bond_prpr": "10500.00",
            "bond_prdy_vrss": "50.00",
            "prdy_vrss_sign": "2",
            "prdy_ctrt": "0.48",
            "acml_vol": "10023",
            "bond_oprc": "10400.00",
            "bond_hgpr": "10500.00",
            "bond_lwpr": "10400.00"
        },
        {
            "stck_bsop_date": "20240422",
            "bond_prpr": "10450.00",
            "bond_prdy_vrss": "50.00",
            "prdy_vrss_sign": "2",
            "prdy_ctrt": "0.48",
            "acml_vol": "185887",
            "bond_oprc": "10450.00",
            "bond_hgpr": "10500.00",
            "bond_lwpr": "10449.90"
        },
        {
            "stck_bsop_date": "20240416",
            "bond_prpr": "10400.00",
            "bond_prdy_vrss": "41.00",
            "prdy_vrss_sign": "2",
            "prdy_ctrt": "0.40",
            "acml_vol": "16204",
            "bond_oprc": "10270.10",
            "bond_hgpr": "10400.00",
            "bond_lwpr": "10270.10"
        },
        {
            "stck_bsop_date": "20240409",
            "bond_prpr": "10359.00",
            "bond_prdy_vrss": "0.00",
            "prdy_vrss_sign": "3",
            "prdy_ctrt": "0.00",
            "acml_vol": "25500",
            "bond_oprc": "10270.00",
            "bond_hgpr": "10359.00",
            "bond_lwpr": "10270.00"
        },
        {
            "stck_bsop_date": "20240408",
            "bond_prpr": "10359.00",
            "bond_prdy_vrss": "98.90",
            "prdy_vrss_sign": "2",
            "prdy_ctrt": "0.96",
            "acml_vol": "3908",
            "bond_oprc": "10270.00",
            "bond_hgpr": "10359.00",
            "bond_lwpr": "10201.40"
        },
        {
            "stck_bsop_date": "20240405",
            "bond_prpr": "10260.10",
            "bond_prdy_vrss": "10.10",
            "prdy_vrss_sign": "2",
            "prdy_ctrt": "0.10",
            "acml_vol": "86102",
            "bond_oprc": "10260.00",
            "bond_hgpr": "10369.70",
            "bond_lwpr": "10260.00"
        },
        {
            "stck_bsop_date": "20240404",
            "bond_prpr": "10250.00",
            "bond_prdy_vrss": "0.00",
            "prdy_vrss_sign": "3",
            "prdy_ctrt": "0.00",
            "acml_vol": "160002",
            "bond_oprc": "10370.00",
            "bond_hgpr": "10370.00",
            "bond_lwpr": "10250.00"
        },
        {
            "stck_bsop_date": "20240403",
            "bond_prpr": "10250.00",
            "bond_prdy_vrss": "-10.00",
            "prdy_vrss_sign": "5",
            "prdy_ctrt": "-0.10",
            "acml_vol": "15003",
            "bond_oprc": "10200.00",
            "bond_hgpr": "10250.00",
            "bond_lwpr": "10200.00"
        },
        {
            "stck_bsop_date": "20240402",
            "bond_prpr": "10260.00",
            "bond_prdy_vrss": "120.00",
            "prdy_vrss_sign": "2",
            "prdy_ctrt": "1.18",
            "acml_vol": "50000",
            "bond_oprc": "10260.00",
            "bond_hgpr": "10260.00",
            "bond_lwpr": "10260.00"
        },
		...
    ],
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다."
}
```

---

## 장내채권 기간별시세(일)

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 기본시세 |
| API 명 | 장내채권 기간별시세(일) |
| API ID | 국내주식-159 |
| 실전 TR_ID | FHKBJ773701C0 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/quotations/inquire-daily-itemchartprice |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 331 |

### 개요

장내채권 기간별시세(일) API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0979] 장내채권종합주문 화면 가운데 "일별" 클릭 시 시세 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다. 

최근 30건까지 데이터 확인이 가능합니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | FHKBJ773701C0 |
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
| FID_COND_MRKT_DIV_CODE | 조건 시장 구분 코드 | string | Y | 6 | Unique key(B) |
| FID_INPUT_ISCD | 입력 종목코드 | string | Y | 12 | 종목코드 |

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
| stck_bsop_date | 주식영업일자 | string | Y | 8 |  |
| bond_oprc | 채권시가2 | string | Y | 112 |  |
| bond_hgpr | 채권고가 | string | Y | 112 |  |
| bond_lwpr | 채권저가 | string | Y | 112 |  |
| bond_prpr | 채권현재가 | string | Y | 112 |  |
| acml_vol | 누적거래량 | string | Y | 18 |  |

### Example

**Request Example (Python)**

```
FID_COND_MRKT_DIV_CODE:B
FID_INPUT_ISCD:KR101501D967
```

**Response Example**

```
{
    "output": [
        {
            "stck_bsop_date": "20240610",
            "bond_oprc": "0.00",
            "bond_hgpr": "0.00",
            "bond_lwpr": "0.00",
            "bond_prpr": "10997.10",
            "acml_vol": "0"
        },
        {
            "stck_bsop_date": "20240607",
            "bond_oprc": "10997.10",
            "bond_hgpr": "10997.10",
            "bond_lwpr": "10997.10",
            "bond_prpr": "10997.10",
            "acml_vol": "119"
        },
        {
            "stck_bsop_date": "20240605",
            "bond_oprc": "10997.50",
            "bond_hgpr": "10997.50",
            "bond_lwpr": "10997.50",
            "bond_prpr": "10997.50",
            "acml_vol": "97"
        },
        {
            "stck_bsop_date": "20240530",
            "bond_oprc": "10860.00",
            "bond_hgpr": "10860.00",
            "bond_lwpr": "10860.00",
            "bond_prpr": "10860.00",
            "acml_vol": "46"
        },
        {
            "stck_bsop_date": "20240529",
            "bond_oprc": "10873.00",
            "bond_hgpr": "10873.00",
            "bond_lwpr": "10873.00",
            "bond_prpr": "10873.00",
            "acml_vol": "3"
        },
        {
            "stck_bsop_date": "20240528",
            "bond_oprc": "8540.00",
            "bond_hgpr": "10700.00",
            "bond_lwpr": "8540.00",
            "bond_prpr": "10700.00",
            "acml_vol": "49"
        },
        {
            "stck_bsop_date": "20240520",
            "bond_oprc": "10867.70",
            "bond_hgpr": "10867.70",
            "bond_lwpr": "10867.70",
            "bond_prpr": "10867.70",
            "acml_vol": "14"
        },
        {
            "stck_bsop_date": "20240517",
            "bond_oprc": "10850.40",
            "bond_hgpr": "10850.40",
            "bond_lwpr": "10850.40",
            "bond_prpr": "10850.40",
            "acml_vol": "1015"
        },
        {
            "stck_bsop_date": "20240514",
            "bond_oprc": "10861.80",
            "bond_hgpr": "10863.50",
            "bond_lwpr": "10861.80",
            "bond_prpr": "10863.50",
            "acml_vol": "17549"
        },
        {
            "stck_bsop_date": "20240513",
            "bond_oprc": "10844.30",
            "bond_hgpr": "10861.10",
            "bond_lwpr": "10844.30",
            "bond_prpr": "10861.10",
            "acml_vol": "1963"
        },
        {
            "stck_bsop_date": "20240510",
            "bond_oprc": "10858.00",
            "bond_hgpr": "10858.00",
            "bond_lwpr": "10858.00",
            "bond_prpr": "10858.00",
            "acml_vol": "12"
        },
        {
            "stck_bsop_date": "20240509",
            "bond_oprc": "10857.00",
            "bond_hgpr": "10857.00",
            "bond_lwpr": "10857.00",
            "bond_prpr": "10857.00",
            "acml_vol": "2"
        },
        {
            "stck_bsop_date": "20240508",
            "bond_oprc": "10856.20",
            "bond_hgpr": "10856.20",
            "bond_lwpr": "10856.20",
            "bond_prpr": "10856.20",
            "acml_vol": "11"
        },
        {
            "stck_bsop_date": "20240424",
            "bond_oprc": "10820.70",
            "bond_hgpr": "10820.70",
            "bond_lwpr": "10820.70",
            "bond_prpr": "10820.70",
            "acml_vol": "931"
        },
        {
            "stck_bsop_date": "20240423",
            "bond_oprc": "10818.60",
            "bond_hgpr": "10819.00",
            "bond_lwpr": "10818.60",
            "bond_prpr": "10819.00",
            "acml_vol": "3708"
        },
        {
            "stck_bsop_date": "20240422",
            "bond_oprc": "10817.60",
            "bond_hgpr": "10823.00",
            "bond_lwpr": "10817.60",
            "bond_prpr": "10823.00",
            "acml_vol": "13959"
        },
        {
            "stck_bsop_date": "20240308",
            "bond_oprc": "10756.00",
            "bond_hgpr": "10788.00",
            "bond_lwpr": "10756.00",
            "bond_prpr": "10788.00",
            "acml_vol": "20"
        },
        {
            "stck_bsop_date": "20231108",
            "bond_oprc": "10600.00",
            "bond_hgpr": "10600.00",
            "bond_lwpr": "10600.00",
            "bond_prpr": "10600.00",
            "acml_vol": "949"
        },
        {
            "stck_bsop_date": "20231018",
            "bond_oprc": "10570.00",
            "bond_hgpr": "10620.00",
            "bond_lwpr": "10570.00",
            "bond_prpr": "10620.00",
            "acml_vol": "1890"
        },
        {
            "stck_bsop_date": "20231013",
            "bond_oprc": "10592.00",
            "bond_hgpr": "10630.00",
            "bond_lwpr": "10592.00",
            "bond_prpr": "10630.00",
            "acml_vol": "10714"
        },
        {
            "stck_bsop_date": "20231012",
            "bond_oprc": "10541.00",
            "bond_hgpr": "10592.00",
            "bond_lwpr": "10541.00",
            "bond_prpr": "10592.00",
            "acml_vol": "5691"
        },
        {
            "stck_bsop_date": "20230926",
            "bond_oprc": "10615.70",
            "bond_hgpr": "10615.70",
            "bond_lwpr": "10615.70",
            "bond_prpr": "10615.70",
            "acml_vol": "4731"
        },
        {
            "stck_bsop_date": "20230914",
            "bond_oprc": "10579.00",
            "bond_hgpr": "10579.00",
            "bond_lwpr": "10579.00",
            "bond_prpr": "10579.00",
            "acml_vol": "10"
        },
        {
            "stck_bsop_date": "20230913",
            "bond_oprc": "10501.00",
            "bond_hgpr": "10501.00",
            "bond_lwpr": "10501.00",
            "bond_prpr": "10501.00",
            "acml_vol": "9"
        },
        {
            "stck_bsop_date": "20230912",
            "bond_oprc": "10499.10",
            "bond_hgpr": "10540.00",
            "bond_lwpr": "10499.10",
            "bond_prpr": "10499.10",
            "acml_vol": "30"
        },
        {
            "stck_bsop_date": "20230829",
            "bond_oprc": "10389.00",
            "bond_hgpr": "10389.00",
            "bond_lwpr": "10389.00",
            "bond_prpr": "10389.00",
            "acml_vol": "4761"
        },
        {
            "stck_bsop_date": "20230825",
            "bond_oprc": "10550.00",
            "bond_hgpr": "10550.00",
            "bond_lwpr": "10550.00",
            "bond_prpr": "10550.00",
            "acml_vol": "12555"
        },
        {
            "stck_bsop_date": "20230818",
            "bond_oprc": "10299.20",
            "bond_hgpr": "10299.20",
            "bond_lwpr": "10299.20",
            "bond_prpr": "10299.20",
            "acml_vol": "2838"
        },
        {
            "stck_bsop_date": "20230814",
            "bond_oprc": "10350.00",
            "bond_hgpr": "10450.00",
            "bond_lwpr": "10350.00",
            "bond_prpr": "10450.00",
            "acml_vol": "2838"
        },
        {
            "stck_bsop_date": "20230720",
            "bond_oprc": "10527.00",
            "bond_hgpr": "10527.00",
            "bond_lwpr": "10527.00",
            "bond_prpr": "10527.00",
            "acml_vol": "18"
        }
    ],
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다."
}
```

---

## 장내채권 평균단가조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 기본시세 |
| API 명 | 장내채권 평균단가조회 |
| API ID | 국내주식-158 |
| 실전 TR_ID | CTPF2005R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/quotations/avg-unit |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 332 |

### 개요

장내채권 평균단가조회 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [7216] 채권 발행정보 화면의 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | CTPF2005R |
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
| INQR_STRT_DT | 조회시작일자 | string | Y | 8 | 일자 ~ |
| INQR_END_DT | 조회종료일자 | string | Y | 8 | ~ 일자 |
| PDNO | 상품번호 | string | Y | 12 | 공백: 전체,  특정종목 조회시 : 종목코드 |
| PRDT_TYPE_CD | 상품유형코드 | string | Y | 3 | Unique key(302) |
| VRFC_KIND_CD | 검증종류코드 | string | Y | 2 | Unique key(00) |
| CTX_AREA_NK30 | 연속조회키30 | string | Y | 30 | 공백 |
| CTX_AREA_FK100 | 연속조회검색조건100 | string | Y | 100 | 공백 |

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
| output1 | 응답상세 | object array | Y |  | array |
| evlu_dt | 평가일자 | string | Y | 245 |  |
| pdno | 상품번호 | string | Y | 202 |  |
| prdt_type_cd | 상품유형코드 | string | Y | 238 |  |
| prdt_name | 상품명 | string | Y | 1 |  |
| kis_unpr | 한국신용평가단가 | string | Y | 8 |  |
| kbp_unpr | 한국채권평가단가 | string | Y | 500 |  |
| nice_evlu_unpr | 한국신용정보평가단가 | string | Y | 238 |  |
| fnp_unpr | 에프앤자산평가단가 | string | Y | 202 |  |
| avg_evlu_unpr | 평균평가단가 | string | Y | 500 |  |
| kis_crdt_grad_text | 한국신용평가신용등급내용 | string | Y | 238 |  |
| kbp_crdt_grad_text | 한국채권평가신용등급내용 | string | Y | 202 |  |
| nice_crdt_grad_text | 한국신용정보신용등급내용 | string | Y | 238 |  |
| fnp_crdt_grad_text | 에프앤자산평가신용등급내용 | string | Y | 500 |  |
| chng_yn | 변경여부 | string | Y | 238 |  |
| kis_erng_rt | 한국신용평가수익율 | string | Y | 202 |  |
| kbp_erng_rt | 한국채권평가수익율 | string | Y | 238 |  |
| nice_evlu_erng_rt | 한국신용정보평가수익율 | string | Y | 500 |  |
| fnp_erng_rt | 에프앤자산평가수익율 | string | Y | 179 |  |
| avg_evlu_erng_rt | 평균평가수익율 | string | Y | 202 |  |
| kis_rf_unpr | 한국신용평가RF단가 | string | Y | 238 |  |
| kbp_rf_unpr | 한국채권평가RF단가 | string | Y | 12 |  |
| nice_evlu_rf_unpr | 한국신용정보평가RF단가 | string | Y | 60 |  |
| avg_evlu_rf_unpr | 평균평가RF단가 | string | Y | 3 |  |
| output2 | 응답상세 | object array | Y |  | array |
| evlu_dt | 평가일자 | string | Y | 19 |  |
| pdno | 상품번호 | string | Y | 1 |  |
| prdt_type_cd | 상품유형코드 | string | Y | 8 |  |
| prdt_name | 상품명 | string | Y | 19 |  |
| kis_evlu_amt | 한국신용평가평가금액 | string | Y | 19 |  |
| kbp_evlu_amt | 한국채권평가평가금액 | string | Y | 19 |  |
| nice_evlu_amt | 한국신용정보평가금액 | string | Y | 19 |  |
| fnp_evlu_amt | 에프앤자산평가평가금액 | string | Y | 12 |  |
| avg_evlu_amt | 평균평가금액 | string | Y | 60 |  |
| chng_yn | 변경여부 | string | Y | 3 |  |
| output3 | 응답상세 | object array | Y |  | array |
| evlu_dt | 평가일자 | string | Y | 236 |  |
| pdno | 상품번호 | string | Y | 19 |  |
| prdt_type_cd | 상품유형코드 | string | Y | 1 |  |
| prdt_name | 상품명 | string | Y | 8 |  |
| kis_crcy_cd | 한국신용평가통화코드 | string | Y | 3 |  |
| kis_evlu_unit_pric | 한국신용평가평가단위가격 | string | Y | 236 |  |
| kis_evlu_pric | 한국신용평가평가가격 | string | Y | 19 |  |
| kbp_crcy_cd | 한국채권평가통화코드 | string | Y | 3 |  |
| kbp_evlu_unit_pric | 한국채권평가평가단위가격 | string | Y | 236 |  |
| kbp_evlu_pric | 한국채권평가평가가격 | string | Y | 19 |  |
| nice_crcy_cd | 한국신용정보통화코드 | string | Y | 3 |  |
| nice_evlu_unit_pric | 한국신용정보평가단위가격 | string | Y | 236 |  |
| nice_evlu_pric | 한국신용정보평가가격 | string | Y | 19 |  |
| avg_evlu_unit_pric | 평균평가단위가격 | string | Y | 12 |  |
| avg_evlu_pric | 평균평가가격 | string | Y | 60 |  |
| chng_yn | 변경여부 | string | Y | 3 |  |

### Example

**Request Example (Python)**

```
INQR_STRT_DT:20240101
INQR_END_DT:20240425
PDNO:KR2033022D33
PRDT_TYPE_CD:302
VRFC_KIND_CD:00
CTX_AREA_NK30:
CTX_AREA_FK100:
```

**Response Example**

```
{
    "ctx_area_nk30": "20240406!^KR2033022D33!^302   ",
    "ctx_area_fk100": "20240101!^20240425!^KR2033022D33!^302!^00                                                           ",
    "output1": [
        {
            "evlu_dt": "20240425",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9745.69000000",
            "kbp_unpr": "9760.39000000",
            "nice_evlu_unpr": "9767.78000000",
            "fnp_unpr": "9760.76",
            "avg_evlu_unpr": "9758.65000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.87000000",
            "kbp_erng_rt": "3.83000000",
            "nice_evlu_erng_rt": "3.810000000",
            "fnp_erng_rt": "3.82900000",
            "avg_evlu_erng_rt": "3.83480",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240424",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9757.62000000",
            "kbp_unpr": "9771.98000000",
            "nice_evlu_unpr": "9780.14000000",
            "fnp_unpr": "9773.46",
            "avg_evlu_unpr": "9770.80000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.83500000",
            "kbp_erng_rt": "3.79600000",
            "nice_evlu_erng_rt": "3.774000000",
            "fnp_erng_rt": "3.79200000",
            "avg_evlu_erng_rt": "3.79930",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240423",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9764.04000000",
            "kbp_unpr": "9778.42000000",
            "nice_evlu_unpr": "9785.84000000",
            "fnp_unpr": "9779.90",
            "avg_evlu_unpr": "9777.05000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.81500000",
            "kbp_erng_rt": "3.77600000",
            "nice_evlu_erng_rt": "3.756000000",
            "fnp_erng_rt": "3.77200000",
            "avg_evlu_erng_rt": "3.77980",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240422",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9753.79000000",
            "kbp_unpr": "9768.17000000",
            "nice_evlu_unpr": "9777.44000000",
            "fnp_unpr": "9769.65",
            "avg_evlu_unpr": "9767.26000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.84000000",
            "kbp_erng_rt": "3.80100000",
            "nice_evlu_erng_rt": "3.776000000",
            "fnp_erng_rt": "3.79700000",
            "avg_evlu_erng_rt": "3.80350",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240421",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9765.77000000",
            "kbp_unpr": "9780.18000000",
            "nice_evlu_unpr": "9789.47000000",
            "fnp_unpr": "9781.66",
            "avg_evlu_unpr": "9779.27000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.80500000",
            "kbp_erng_rt": "3.76600000",
            "nice_evlu_erng_rt": "3.741000000",
            "fnp_erng_rt": "3.76200000",
            "avg_evlu_erng_rt": "3.76850",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240420",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9764.79000000",
            "kbp_unpr": "9779.20000000",
            "nice_evlu_unpr": "9788.50000000",
            "fnp_unpr": "9780.69",
            "avg_evlu_unpr": "9778.29000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.80500000",
            "kbp_erng_rt": "3.76600000",
            "nice_evlu_erng_rt": "3.741000000",
            "fnp_erng_rt": "3.76200000",
            "avg_evlu_erng_rt": "3.76850",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240419",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9763.81000000",
            "kbp_unpr": "9778.23000000",
            "nice_evlu_unpr": "9787.53000000",
            "fnp_unpr": "9779.72",
            "avg_evlu_unpr": "9777.32000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.80500000",
            "kbp_erng_rt": "3.76600000",
            "nice_evlu_erng_rt": "3.741000000",
            "fnp_erng_rt": "3.76200000",
            "avg_evlu_erng_rt": "3.76850",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240418",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9782.54000000",
            "kbp_unpr": "9793.65000000",
            "nice_evlu_unpr": "9805.22000000",
            "fnp_unpr": "9798.50",
            "avg_evlu_unpr": "9794.97000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.75200000",
            "kbp_erng_rt": "3.72200000",
            "nice_evlu_erng_rt": "3.691000000",
            "fnp_erng_rt": "3.70900000",
            "avg_evlu_erng_rt": "3.71850",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240417",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9770.02000000",
            "kbp_unpr": "9777.77000000",
            "nice_evlu_unpr": "9791.94000000",
            "fnp_unpr": "9784.10",
            "avg_evlu_unpr": "9780.95000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.78300000",
            "kbp_erng_rt": "3.76200000",
            "nice_evlu_erng_rt": "3.724000000",
            "fnp_erng_rt": "3.74500000",
            "avg_evlu_erng_rt": "3.75350",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240416",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9767.18000000",
            "kbp_unpr": "9774.93000000",
            "nice_evlu_unpr": "9788.73000000",
            "fnp_unpr": "9782.02",
            "avg_evlu_unpr": "9778.21000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.78800000",
            "kbp_erng_rt": "3.76700000",
            "nice_evlu_erng_rt": "3.730000000",
            "fnp_erng_rt": "3.74800000",
            "avg_evlu_erng_rt": "3.75830",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240415",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9778.13000000",
            "kbp_unpr": "9787.02000000",
            "nice_evlu_unpr": "9798.98000000",
            "fnp_unpr": "9794.12",
            "avg_evlu_unpr": "9789.56000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.75600000",
            "kbp_erng_rt": "3.73200000",
            "nice_evlu_erng_rt": "3.700000000",
            "fnp_erng_rt": "3.71300000",
            "avg_evlu_erng_rt": "3.72530",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240414",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9795.10000000",
            "kbp_unpr": "9802.13000000",
            "nice_evlu_unpr": "9812.25000000",
            "fnp_unpr": "9808.13",
            "avg_evlu_unpr": "9804.40000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.70800000",
            "kbp_erng_rt": "3.68900000",
            "nice_evlu_erng_rt": "3.662000000",
            "fnp_erng_rt": "3.67300000",
            "avg_evlu_erng_rt": "3.68300",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240413",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9794.13000000",
            "kbp_unpr": "9801.18000000",
            "nice_evlu_unpr": "9811.30000000",
            "fnp_unpr": "9807.17",
            "avg_evlu_unpr": "9803.44000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.70800000",
            "kbp_erng_rt": "3.68900000",
            "nice_evlu_erng_rt": "3.662000000",
            "fnp_erng_rt": "3.67300000",
            "avg_evlu_erng_rt": "3.68300",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240412",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9793.17000000",
            "kbp_unpr": "9800.22000000",
            "nice_evlu_unpr": "9810.35000000",
            "fnp_unpr": "9806.22",
            "avg_evlu_unpr": "9802.49000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.70800000",
            "kbp_erng_rt": "3.68900000",
            "nice_evlu_erng_rt": "3.662000000",
            "fnp_erng_rt": "3.67300000",
            "avg_evlu_erng_rt": "3.68300",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240411",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9764.91000000",
            "kbp_unpr": "9773.80000000",
            "nice_evlu_unpr": "9783.16000000",
            "fnp_unpr": "9778.67",
            "avg_evlu_unpr": "9775.13000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.78100000",
            "kbp_erng_rt": "3.75700000",
            "nice_evlu_erng_rt": "3.732000000",
            "fnp_erng_rt": "3.74400000",
            "avg_evlu_erng_rt": "3.75350",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240410",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9793.13000000",
            "kbp_unpr": "9799.81000000",
            "nice_evlu_unpr": "9809.20000000",
            "fnp_unpr": "9804.69",
            "avg_evlu_unpr": "9801.70000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.70300000",
            "kbp_erng_rt": "3.68500000",
            "nice_evlu_erng_rt": "3.660000000",
            "fnp_erng_rt": "3.67200000",
            "avg_evlu_erng_rt": "3.68000",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240409",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9792.17000000",
            "kbp_unpr": "9798.85000000",
            "nice_evlu_unpr": "9808.25000000",
            "fnp_unpr": "9803.74",
            "avg_evlu_unpr": "9800.75000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.70300000",
            "kbp_erng_rt": "3.68500000",
            "nice_evlu_erng_rt": "3.660000000",
            "fnp_erng_rt": "3.67200000",
            "avg_evlu_erng_rt": "3.68000",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240408",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9796.84000000",
            "kbp_unpr": "9802.41000000",
            "nice_evlu_unpr": "9812.94000000",
            "fnp_unpr": "9806.92",
            "avg_evlu_unpr": "9804.77000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.68800000",
            "kbp_erng_rt": "3.67300000",
            "nice_evlu_erng_rt": "3.645000000",
            "fnp_erng_rt": "3.66100000",
            "avg_evlu_erng_rt": "3.66680",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240407",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9814.71000000",
            "kbp_unpr": "9818.40000000",
            "nice_evlu_unpr": "9830.10000000",
            "fnp_unpr": "9822.93",
            "avg_evlu_unpr": "9821.53000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.63800000",
            "kbp_erng_rt": "3.62800000",
            "nice_evlu_erng_rt": "3.597000000",
            "fnp_erng_rt": "3.61600000",
            "avg_evlu_erng_rt": "3.61980",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        },
        {
            "evlu_dt": "20240406",
            "pdno": "KR2033022D33",
            "prdt_type_cd": "302",
            "prdt_name": "충북지역개발채권23-03",
            "kis_unpr": "9813.76000000",
            "kbp_unpr": "9817.46000000",
            "nice_evlu_unpr": "9829.16000000",
            "fnp_unpr": "9821.99",
            "avg_evlu_unpr": "9820.59000000",
            "kis_crdt_grad_text": "",
            "kbp_crdt_grad_text": "",
            "nice_crdt_grad_text": "",
            "fnp_crdt_grad_text": "",
            "chng_yn": "N",
            "kis_erng_rt": "3.63800000",
            "kbp_erng_rt": "3.62800000",
            "nice_evlu_erng_rt": "3.597000000",
            "fnp_erng_rt": "3.61600000",
            "avg_evlu_erng_rt": "3.61980",
            "kis_rf_unpr": "0.00",
            "kbp_rf_unpr": "0.00",
            "nice_evlu_rf_unpr": "0.00",
            "avg_evlu_rf_unpr": "0.00"
        }
    ],
    "output2": [],
    "output3": [],
    "rt_cd": "0",
    "msg_cd": "KIOK0500",
    "msg1": "조회가 계속됩니다..다음버튼을 Click 하십시오.                                   "
}
```

---

## 장내채권 발행정보

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 기본시세 |
| API 명 | 장내채권 발행정보 |
| API ID | 국내주식-156 |
| 실전 TR_ID | CTPF1101R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/quotations/issue-info |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 333 |

### 개요

장내채권 발행정보 API입니다.
한국투자 HTS(eFriend Plus) &gt; [7216] 채권 발행정보 화면의 상단 채권정보 데이터를 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | CTPF1101R |
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
| PDNO | 사용자권한정보 | string | Y | 12 | 채권 종목번호(ex. KR6449111CB8) |
| PRDT_TYPE_CD | 거래소코드 | string | Y | 3 | Unique key(302) |

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
| output | 응답상세 | object | Y |  |  |
| pdno | 상품번호 | string | Y | 12 |  |
| prdt_type_cd | 상품유형코드 | string | Y | 3 |  |
| prdt_name | 상품명 | string | Y | 60 |  |
| prdt_eng_name | 상품영문명 | string | Y | 60 |  |
| ivst_heed_prdt_yn | 투자유의상품여부 | string | Y | 1 |  |
| exts_yn | 연장여부 | string | Y | 1 |  |
| bond_clsf_cd | 채권분류코드 | string | Y | 6 |  |
| bond_clsf_kor_name | 채권분류한글명 | string | Y | 60 |  |
| papr | 액면가 | string | Y | 19 |  |
| int_mned_dvsn_cd | 이자월말구분코드 | string | Y | 1 |  |
| rvnu_shap_cd | 매출형태코드 | string | Y | 1 |  |
| issu_amt | 발행금액 | string | Y | 19 |  |
| lstg_rmnd | 상장잔액 | string | Y | 19 |  |
| int_dfrm_mcnt | 이자지급개월수 | string | Y | 6 |  |
| bond_int_dfrm_mthd_cd | 채권이자지급방법코드 | string | Y | 2 |  |
| splt_rdpt_rcnt | 분할상환횟수 | string | Y | 6 |  |
| prca_dfmt_term_mcnt | 원금거치기간개월수 | string | Y | 6 |  |
| int_anap_dvsn_cd | 이자선후급구분코드 | string | Y | 1 |  |
| bond_rght_dvsn_cd | 채권권리구분코드 | string | Y | 2 |  |
| prdt_pclc_text | 상품특성내용 | string | Y | 500 |  |
| prdt_abrv_name | 상품약어명 | string | Y | 60 |  |
| prdt_eng_abrv_name | 상품영문약어명 | string | Y | 60 |  |
| sprx_psbl_yn | 분리과세가능여부 | string | Y | 1 |  |
| pbff_pplc_ofrg_mthd_cd | 공모사모모집방법코드 | string | Y | 2 |  |
| cmco_cd | 주간사코드 | string | Y | 4 |  |
| issu_istt_cd | 발행기관코드 | string | Y | 5 |  |
| issu_istt_name | 발행기관명 | string | Y | 60 |  |
| pnia_dfrm_agcy_istt_cd | 원리금지급대행기관코드 | string | Y | 4 |  |
| dsct_ec_rt | 할인할증율 | string | Y | 238 |  |
| srfc_inrt | 표면이율 | string | Y | 238 |  |
| expd_rdpt_rt | 만기상환율 | string | Y | 238 |  |
| expd_asrc_erng_rt | 만기보장수익율 | string | Y | 238 |  |
| bond_grte_istt_name | 채권보증기관명 | string | Y | 60 |  |
| int_dfrm_day_type_cd | 이자지급일유형코드 | string | Y | 2 |  |
| ksd_int_calc_unit_cd | 증권예탁결제원이자계산단위코드 | string | Y | 1 |  |
| int_wunt_uder_prcs_dvsn_cd | 이자원화단위미만처리구분코드 | string | Y | 1 |  |
| rvnu_dt | 매출일자 | string | Y | 8 |  |
| issu_dt | 발행일자 | string | Y | 8 |  |
| lstg_dt | 상장일자 | string | Y | 8 |  |
| expd_dt | 만기일자 | string | Y | 8 |  |
| rdpt_dt | 상환일자 | string | Y | 8 |  |
| sbst_pric | 대용가격 | string | Y | 19 |  |
| rgbf_int_dfrm_dt | 직전이자지급일자 | string | Y | 8 |  |
| nxtm_int_dfrm_dt | 차기이자지급일자 | string | Y | 8 |  |
| frst_int_dfrm_dt | 최초이자지급일자 | string | Y | 8 |  |
| ecis_pric | 행사가격 | string | Y | 19 |  |
| rght_stck_std_pdno | 권리주식표준상품번호 | string | Y | 12 |  |
| ecis_opng_dt | 행사개시일자 | string | Y | 8 |  |
| ecis_end_dt | 행사종료일자 | string | Y | 8 |  |
| bond_rvnu_mthd_cd | 채권매출방법코드 | string | Y | 2 |  |
| oprt_stfno | 조작직원번호 | string | Y | 6 |  |
| oprt_stff_name | 조작직원명 | string | Y | 60 |  |
| rgbf_int_dfrm_wday | 직전이자지급요일 | string | Y | 2 |  |
| nxtm_int_dfrm_wday | 차기이자지급요일 | string | Y | 2 |  |
| kis_crdt_grad_text | 한국신용평가신용등급내용 | string | Y | 500 |  |
| kbp_crdt_grad_text | 한국채권평가신용등급내용 | string | Y | 500 |  |
| nice_crdt_grad_text | 한국신용정보신용등급내용 | string | Y | 500 |  |
| fnp_crdt_grad_text | 에프앤자산평가신용등급내용 | string | Y | 500 |  |
| dpsi_psbl_yn | 예탁가능여부 | string | Y | 1 |  |
| pnia_int_calc_unpr | 원리금이자계산단가 | string | Y | 234 |  |
| prcm_idx_bond_yn | 물가지수채권여부 | string | Y | 1 |  |
| expd_exts_srdp_rcnt | 만기연장분할상환횟수 | string | Y | 10 |  |
| expd_exts_srdp_rt | 만기연장분할상환율 | string | Y | 2212 |  |
| loan_psbl_yn | 대출가능여부 | string | Y | 1 |  |
| grte_dvsn_cd | 보증구분코드 | string | Y | 1 |  |
| fnrr_rank_dvsn_cd | 선후순위구분코드 | string | Y | 1 |  |
| krx_lstg_abol_dvsn_cd | 한국거래소상장폐지구분코드 | string | Y | 1 |  |
| asst_rqdi_dvsn_cd | 자산유동화구분코드 | string | Y | 2 |  |
| opcb_dvsn_cd | 옵션부사채구분코드 | string | Y | 1 |  |
| crfd_item_yn | 크라우드펀딩종목여부 | string | Y | 1 |  |
| crfd_item_rstc_cclc_dt | 크라우드펀딩종목제한해지일자 | string | Y | 8 |  |
| bond_nmpr_unit_pric | 채권호가단위가격 | string | Y | 202 |  |
| ivst_heed_bond_dvsn_name | 투자유의채권구분명 | string | Y | 60 |  |
| add_erng_rt | 추가수익율 | string | Y | 238 |  |
| add_erng_rt_aply_dt | 추가수익율적용일자 | string | Y | 8 |  |
| bond_tr_stop_dvsn_cd | 채권거래정지구분코드 | string | Y | 1 |  |
| ivst_heed_bond_dvsn_cd | 투자유의채권구분코드 | string | Y | 1 |  |
| pclr_cndt_text | 특이조건내용 | string | Y | 500 |  |
| hbbd_yn | 하이브리드채권여부 | string | Y | 1 |  |
| cdtl_cptl_scty_type_cd | 조건부자본증권유형코드 | string | Y | 1 |  |
| elec_scty_yn | 전자증권여부 | string | Y | 1 |  |
| sq1_clop_ecis_opng_dt | 1차콜옵션행사개시일자 | string | Y | 8 |  |
| frst_erlm_stfno | 최초등록직원번호 | string | Y | 6 |  |
| frst_erlm_dt | 최초등록일자 | string | Y | 8 |  |
| frst_erlm_tmd | 최초등록시각 | string | Y | 6 |  |
| tlg_rcvg_dtl_dtime | 전문수신상세일시 | string | Y | 17 |  |

### Example

**Request Example (Python)**

```
PDNO:KR6449111CB8
PRDT_TYPE_CD:302
```

**Response Example**

```
{
    "output": {
        "pdno": "KR6449111CB8",
        "prdt_type_cd": "302",
        "prdt_name": "2022기보제일차유동화전문1-1(사)",
        "prdt_eng_name": "2022 KIBO 1st Securitization Specialty1-1(S)",
        "ivst_heed_prdt_yn": "N",
        "exts_yn": "N",
        "bond_clsf_cd": "116100",
        "bond_clsf_kor_name": "일반사채",
        "papr": "10000",
        "int_mned_dvsn_cd": "1",
        "rvnu_shap_cd": "2",
        "issu_amt": "77839700000",
        "lstg_rmnd": "77839700000",
        "int_dfrm_mcnt": "3",
        "bond_int_dfrm_mthd_cd": "03",
        "splt_rdpt_rcnt": "0",
        "prca_dfmt_term_mcnt": "0",
        "int_anap_dvsn_cd": "2",
        "bond_rght_dvsn_cd": "",
        "prdt_pclc_text": "",
        "prdt_abrv_name": "2022기보제일차유1-1(사)",
        "prdt_eng_abrv_name": "2022 KIBO 1st SEC1-1(S)",
        "sprx_psbl_yn": "N",
        "pbff_pplc_ofrg_mthd_cd": "01",
        "cmco_cd": "2117",
        "issu_istt_cd": "44911",
        "issu_istt_name": "2022기보제일차유동화전문 유한회사",
        "pnia_dfrm_agcy_istt_cd": "1105",
        "dsct_ec_rt": "0.000000",
        "srfc_inrt": "5.931000",
        "expd_rdpt_rt": "0.000000",
        "expd_asrc_erng_rt": "0.000000",
        "bond_grte_istt_name": "2022기보제일차유동화전문 유한회사",
        "int_dfrm_day_type_cd": "01",
        "ksd_int_calc_unit_cd": "1",
        "int_wunt_uder_prcs_dvsn_cd": "1",
        "rvnu_dt": "",
        "issu_dt": "20221116",
        "lstg_dt": "20221116",
        "expd_dt": "20241116",
        "rdpt_dt": "20241116",
        "sbst_pric": "8900",
        "rgbf_int_dfrm_dt": "20240516",
        "nxtm_int_dfrm_dt": "20240816",
        "frst_int_dfrm_dt": "",
        "ecis_pric": "0",
        "rght_stck_std_pdno": "",
        "ecis_opng_dt": "",
        "ecis_end_dt": "",
        "bond_rvnu_mthd_cd": "",
        "oprt_stfno": "BATCH",
        "oprt_stff_name": "",
        "rgbf_int_dfrm_wday": "05",
        "nxtm_int_dfrm_wday": "06",
        "kis_crdt_grad_text": "AAA",
        "kbp_crdt_grad_text": "AAA",
        "nice_crdt_grad_text": "AAA",
        "fnp_crdt_grad_text": "AAA",
        "dpsi_psbl_yn": "Y",
        "pnia_int_calc_unpr": "0",
        "prcm_idx_bond_yn": "N",
        "expd_exts_srdp_rcnt": "0",
        "expd_exts_srdp_rt": "0",
        "loan_psbl_yn": "N",
        "grte_dvsn_cd": "4",
        "fnrr_rank_dvsn_cd": "1",
        "krx_lstg_abol_dvsn_cd": "Y",
        "asst_rqdi_dvsn_cd": "11",
        "opcb_dvsn_cd": "",
        "crfd_item_yn": "N",
        "crfd_item_rstc_cclc_dt": "",
        "bond_nmpr_unit_pric": "0.100000",
        "ivst_heed_bond_dvsn_name": "",
        "add_erng_rt": "0.000000",
        "add_erng_rt_aply_dt": "",
        "bond_tr_stop_dvsn_cd": "N",
        "ivst_heed_bond_dvsn_cd": "0",
        "pclr_cndt_text": "",
        "hbbd_yn": "N",
        "cdtl_cptl_scty_type_cd": "",
        "elec_scty_yn": "Y",
        "sq1_clop_ecis_opng_dt": "",
        "frst_erlm_stfno": "",
        "frst_erlm_dt": "",
        "frst_erlm_tmd": ""
    },
    "rt_cd": "0",
    "msg_cd": "KIOK0530",
    "msg1": "조회되었습니다                                                                  "
}
```

---

## 장내채권 기본조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [장내채권] 기본시세 |
| API 명 | 장내채권 기본조회 |
| API ID | 국내주식-129 |
| 실전 TR_ID | CTPF1114R |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-bond/v1/quotations/search-bond-info |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 334 |

### 개요

장내채권 기본조회 API입니다. 
장내채권의 상품정보를 확인 가능합니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | CTPF1114R |
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
| PDNO | 상품번호 | string | Y | 12 | 상품번호 |
| PRDT_TYPE_CD | 상품유형코드 | string | Y | 3 | Unique key(302) |

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
| output | 응답상세 | object | Y |  |  |
| pdno | 상품번호 | string | Y | 12 |  |
| prdt_type_cd | 상품유형코드 | string | Y | 3 |  |
| ksd_bond_item_name | 증권예탁결제원채권종목명 | string | Y | 100 |  |
| ksd_bond_item_eng_name | 증권예탁결제원채권종목영문명 | string | Y | 100 |  |
| ksd_bond_lstg_type_cd | 증권예탁결제원채권상장유형코드 | string | Y | 2 |  |
| ksd_ofrg_dvsn_cd | 증권예탁결제원모집구분코드 | string | Y | 2 |  |
| ksd_bond_int_dfrm_dvsn_cd | 증권예탁결제원채권이자지급구분 | string | Y | 1 |  |
| issu_dt | 발행일자 | string | Y | 8 |  |
| rdpt_dt | 상환일자 | string | Y | 8 |  |
| rvnu_dt | 매출일자 | string | Y | 8 |  |
| iso_crcy_cd | 통화코드 | string | Y | 3 |  |
| mdwy_rdpt_dt | 중도상환일자 | string | Y | 8 |  |
| ksd_rcvg_bond_dsct_rt | 증권예탁결제원수신채권할인율 | string | Y | 2212 |  |
| ksd_rcvg_bond_srfc_inrt | 증권예탁결제원수신채권표면이율 | string | Y | 2012 |  |
| bond_expd_rdpt_rt | 채권만기상환율 | string | Y | 2212 |  |
| ksd_prca_rdpt_mthd_cd | 증권예탁결제원원금상환방법코드 | string | Y | 2 |  |
| int_caltm_mcnt | 이자계산기간개월수 | string | Y | 10 |  |
| ksd_int_calc_unit_cd | 증권예탁결제원이자계산단위코드 | string | Y | 1 | 1.발행금액<br>2.만원<br>3.십만원<br>4.백만원 |
| uval_cut_dvsn_cd | 절상절사구분코드 | string | Y | 1 |  |
| uval_cut_dcpt_dgit | 절상절사소수점자릿수 | string | Y | 10 |  |
| ksd_dydv_caltm_aply_dvsn_cd | 증권예탁결제원일할계산기간적용 | string | Y | 1 |  |
| dydv_calc_dcnt | 일할계산일수 | string | Y | 5 |  |
| bond_expd_asrc_erng_rt | 채권만기보장수익율 | string | Y | 2212 |  |
| padf_plac_hdof_name | 원리금지급장소본점명 | string | Y | 60 |  |
| lstg_dt | 상장일자 | string | Y | 8 |  |
| lstg_abol_dt | 상장폐지일자 | string | Y | 8 |  |
| ksd_bond_issu_mthd_cd | 증권예탁결제원채권발행방법코드 | string | Y | 1 |  |
| laps_indf_yn | 경과이자지급여부 | string | Y | 1 |  |
| ksd_lhdy_pnia_dfrm_mthd_cd | 증권예탁결제원공휴일원리금지급 | string | Y | 1 |  |
| frst_int_dfrm_dt | 최초이자지급일자 | string | Y | 8 |  |
| ksd_prcm_lnkg_gvbd_yn | 증권예탁결제원물가연동국고채여 | string | Y | 1 |  |
| dpsi_end_dt | 예탁종료일자 | string | Y | 8 |  |
| dpsi_strt_dt | 예탁시작일자 | string | Y | 8 |  |
| dpsi_psbl_yn | 예탁가능여부 | string | Y | 1 |  |
| atyp_rdpt_bond_erlm_yn | 비정형상환채권등록여부 | string | Y | 1 |  |
| dshn_occr_yn | 부도발생여부 | string | Y | 1 |  |
| expd_exts_yn | 만기연장여부 | string | Y | 1 |  |
| pclr_ptcr_text | 특이사항내용 | string | Y | 500 |  |
| dpsi_psbl_excp_stat_cd | 예탁가능예외상태코드 | string | Y | 2 |  |
| expd_exts_srdp_rcnt | 만기연장분할상환횟수 | string | Y | 10 |  |
| expd_exts_srdp_rt | 만기연장분할상환율 | string | Y | 2212 |  |
| expd_rdpt_rt | 만기상환율 | string | Y | 238 |  |
| expd_asrc_erng_rt | 만기보장수익율 | string | Y | 238 |  |
| bond_int_dfrm_mthd_cd | 채권이자지급방법코드 | string | Y | 2 | 01.할인채<br>02.복리채<br>03.이표채.확정금리<br>04.이표채.금리연동<br>05.이표채.변동금리<br>06.단리채<br>07.분할채<br>09.복5단2<br>19.기타.고정금리<br>29.기타.변동금리 |
| int_dfrm_day_type_cd | 이자지급일유형코드 | string | Y | 2 | 01.발행일<br>02.만기일<br>03.특정일 |
| prca_dfmt_term_mcnt | 원금거치기간개월수 | string | Y | 6 |  |
| splt_rdpt_rcnt | 분할상환횟수 | string | Y | 6 |  |
| rgbf_int_dfrm_dt | 직전이자지급일자 | string | Y | 8 |  |
| nxtm_int_dfrm_dt | 차기이자지급일자 | string | Y | 8 |  |
| sprx_psbl_yn | 분리과세가능여부 | string | Y | 1 |  |
| ictx_rt_dvsn_cd | 소득세율구분코드 | string | Y | 2 |  |
| bond_clsf_cd | 채권분류코드 | string | Y | 6 |  |
| bond_clsf_kor_name | 채권분류한글명 | string | Y | 60 |  |
| int_mned_dvsn_cd | 이자월말구분코드 | string | Y | 1 | 1.일자기준<br>2.말일기준 |
| pnia_int_calc_unpr | 원리금이자계산단가 | string | Y | 234 |  |
| frn_intr | FRN금리 | string | Y | 1512 |  |
| aply_day_prcm_idx_lnkg_cefc | 적용일물가지수연동계수 | string | Y | 151 |  |
| ksd_expd_dydv_calc_bass_cd | 증권예탁결제원만기일할계산기준 | string | Y | 1 |  |
| expd_dydv_calc_dcnt | 만기일할계산일수 | string | Y | 7 |  |
| ksd_cbbw_dvsn_cd | 증권예탁결제원신종사채구분코드 | string | Y | 1 |  |
| crfd_item_yn | 크라우드펀딩종목여부 | string | Y | 1 |  |
| pnia_bank_ofdy_dfrm_mthd_cd | 원리금은행휴무일지급방법코드 | string | Y | 1 |  |
| qib_yn | QIB여부 | string | Y | 1 |  |
| qib_cclc_dt | QIB해지일자 | string | Y | 8 |  |
| csbd_yn | 영구채여부 | string | Y | 1 |  |
| csbd_cclc_dt | 영구채해지일자 | string | Y | 8 |  |
| ksd_opcb_yn | 증권예탁결제원옵션부사채여부 | string | Y | 1 |  |
| ksd_sodn_yn | 증권예탁결제원후순위채권여부 | string | Y | 1 |  |
| ksd_rqdi_scty_yn | 증권예탁결제원유동화증권여부 | string | Y | 1 |  |
| elec_scty_yn | 전자증권여부 | string | Y | 1 |  |
| rght_ecis_mbdy_dvsn_cd | 권리행사주체구분코드 | string | Y | 1 |  |
| int_rkng_mthd_dvsn_cd | 이자산정방법구분코드 | string | Y | 1 |  |
| ofrg_dvsn_cd | 모집구분코드 | string | Y | 2 |  |
| ksd_tot_issu_amt | 증권예탁결제원총발행금액 | string | Y | 202 |  |
| next_indf_chk_ecls_yn | 다음이자지급체크제외여부 | string | Y | 1 |  |
| ksd_bond_intr_dvsn_cd | 증권예탁결제원채권금리구분코드 | string | Y | 1 |  |
| ksd_inrt_aply_dvsn_cd | 증권예탁결제원이율적용구분코드 | string | Y | 1 |  |
| krx_issu_istt_cd | KRX발행기관코드 | string | Y | 5 |  |
| ksd_indf_frqc_uder_calc_cd | 증권예탁결제원이자지급주기미만 | string | Y | 1 |  |
| ksd_indf_frqc_uder_calc_dcnt | 증권예탁결제원이자지급주기미만 | string | Y | 4 |  |
| tlg_rcvg_dtl_dtime | 전문수신상세일시 | string | Y | 17 |  |

### Example

**Request Example (Python)**

```
PDNO:KR2033022D33
PRDT_TYPE_CD:302
```

**Response Example**

```
{
    "output": {
        "pdno": "KR2033022D33",
        "prdt_type_cd": "302",
        "ksd_bond_item_name": "충북지역개발채권 23-03",
        "ksd_bond_item_eng_name": "CHUNGBUK PROVINCIAL DEVELOPMENT 23-03",
        "ksd_bond_lstg_type_cd": "11",
        "ksd_ofrg_dvsn_cd": "11",
        "ksd_bond_int_dfrm_dvsn_cd": "3",
        "issu_dt": "20230331",
        "rdpt_dt": "20280331",
        "rvnu_dt": "20230302",
        "iso_crcy_cd": "KRW",
        "mdwy_rdpt_dt": "00000000",
        "ksd_rcvg_bond_dsct_rt": "0.000000000000",
        "ksd_rcvg_bond_srfc_inrt": "2.500000000000",
        "bond_expd_rdpt_rt": "100.000000000000",
        "ksd_prca_rdpt_mthd_cd": "11",
        "int_caltm_mcnt": "12",
        "ksd_int_calc_unit_cd": "1",
        "uval_cut_dvsn_cd": "2",
        "uval_cut_dcpt_dgit": "0",
        "ksd_dydv_caltm_aply_dvsn_cd": "1",
        "dydv_calc_dcnt": "0",
        "bond_expd_asrc_erng_rt": "0.000000000000",
        "padf_plac_hdof_name": "농협은행",
        "lstg_dt": "20230302",
        "lstg_abol_dt": "20280401",
        "ksd_bond_issu_mthd_cd": "2",
        "laps_indf_yn": "Y",
        "ksd_lhdy_pnia_dfrm_mthd_cd": "2",
        "frst_int_dfrm_dt": "00000000",
        "ksd_prcm_lnkg_gvbd_yn": "N",
        "dpsi_end_dt": "20280401",
        "dpsi_strt_dt": "20230302",
        "dpsi_psbl_yn": "Y",
        "atyp_rdpt_bond_erlm_yn": "N",
        "dshn_occr_yn": "N",
        "expd_exts_yn": "N",
        "pclr_ptcr_text": "",
        "dpsi_psbl_excp_stat_cd": "",
        "expd_exts_srdp_rcnt": "0",
        "expd_exts_srdp_rt": "0.000000000000",
        "expd_rdpt_rt": "0.00000000",
        "expd_asrc_erng_rt": "0.00000000",
        "bond_int_dfrm_mthd_cd": "02",
        "int_dfrm_day_type_cd": "02",
        "prca_dfmt_term_mcnt": "0",
        "splt_rdpt_rcnt": "0",
        "rgbf_int_dfrm_dt": "",
        "nxtm_int_dfrm_dt": "20280331",
        "sprx_psbl_yn": "N",
        "ictx_rt_dvsn_cd": "",
        "bond_clsf_cd": "112555",
        "bond_clsf_kor_name": "충북지역개발채권",
        "int_mned_dvsn_cd": "2",
        "pnia_int_calc_unpr": "0.0000",
        "frn_intr": "0.000000000000",
        "aply_day_prcm_idx_lnkg_cefc": "0.0000000000",
        "ksd_expd_dydv_calc_bass_cd": "",
        "expd_dydv_calc_dcnt": "0",
        "ksd_cbbw_dvsn_cd": "9",
        "crfd_item_yn": "N",
        "pnia_bank_ofdy_dfrm_mthd_cd": "1",
        "qib_yn": "N",
        "qib_cclc_dt": "00000000",
        "csbd_yn": "N",
        "csbd_cclc_dt": "00000000",
        "ksd_opcb_yn": "N",
        "ksd_sodn_yn": "N",
        "ksd_rqdi_scty_yn": "N",
        "elec_scty_yn": "Y",
        "rght_ecis_mbdy_dvsn_cd": "1",
        "int_rkng_mthd_dvsn_cd": "1",
        "ofrg_dvsn_cd": "",
        "ksd_tot_issu_amt": "17303560000.00",
        "next_indf_chk_ecls_yn": "N",
        "ksd_bond_intr_dvsn_cd": "1",
        "ksd_inrt_aply_dvsn_cd": "1",
        "krx_issu_istt_cd": "MB033",
        "ksd_indf_frqc_uder_calc_cd": "1",
        "ksd_indf_frqc_uder_calc_dcnt": "0",
        "tlg_rcvg_dtl_dtime": "20240625060514023"
    },
    "rt_cd": "0",
    "msg_cd": "KIOK0530",
    "msg1": "조회되었습니다                                                                  "
}
```

---
