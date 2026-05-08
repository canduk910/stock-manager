# 국내선물옵션 기본시세

**카테고리 코드**: `[국내선물옵션] 기본시세`  
**API 수**: 9개

> 출처: 한국투자증권 OpenAPI 전체 문서 (2026-05-08).  
> 자동 변환: `scripts/kis_excel_to_md.py`

---

## 목차

- [선물옵션 시세](#선물옵션-시세) — `GET` `/uapi/domestic-futureoption/v1/quotations/inquire-price` (실전 TR_ID: `FHMIF10000000`)
- [국내선물 기초자산 시세](#국내선물-기초자산-시세) — `GET` `/uapi/domestic-futureoption/v1/quotations/display-board-top` (실전 TR_ID: `FHPIF05030000`)
- [선물옵션 일중예상체결추이](#선물옵션-일중예상체결추이) — `GET` `/uapi/domestic-futureoption/v1/quotations/exp-price-trend` (실전 TR_ID: `FHPIF05110100`)
- [선물옵션기간별시세(일/주/월/년)](#선물옵션기간별시세일주월년) — `GET` `/uapi/domestic-futureoption/v1/quotations/inquire-daily-fuopchartprice` (실전 TR_ID: `FHKIF03020100`)
- [국내옵션전광판_선물](#국내옵션전광판_선물) — `GET` `/uapi/domestic-futureoption/v1/quotations/display-board-futures` (실전 TR_ID: `FHPIF05030200`)
- [선물옵션 분봉조회](#선물옵션-분봉조회) — `GET` `/uapi/domestic-futureoption/v1/quotations/inquire-time-fuopchartprice` (실전 TR_ID: `FHKIF03020200`)
- [국내옵션전광판_옵션월물리스트](#국내옵션전광판_옵션월물리스트) — `GET` `/uapi/domestic-futureoption/v1/quotations/display-board-option-list` (실전 TR_ID: `FHPIO056104C0`)
- [선물옵션 시세호가](#선물옵션-시세호가) — `GET` `/uapi/domestic-futureoption/v1/quotations/inquire-asking-price` (실전 TR_ID: `FHMIF10010000`)
- [국내옵션전광판_콜풋](#국내옵션전광판_콜풋) — `GET` `/uapi/domestic-futureoption/v1/quotations/display-board-callput` (실전 TR_ID: `FHPIF05030100`)

---

## 선물옵션 시세

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [국내선물옵션] 기본시세 |
| API 명 | 선물옵션 시세 |
| API ID | v1_국내선물-006 |
| 실전 TR_ID | FHMIF10000000 |
| 모의 TR_ID | FHMIF10000000 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-futureoption/v1/quotations/inquire-price |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | https://openapivts.koreainvestment.com:29443 |
| 순번 | 205 |

### 개요

선물옵션 시세 API입니다. 

※ 종목코드 마스터파일 파이썬 정제코드는 한국투자증권 Github 참고 부탁드립니다.
   https://github.com/koreainvestment/open-trading-api/tree/main/stocks_info

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | N | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용)<br><br>※ 토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출<br>EX) "Bearer eyJ..........8GA" |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appsecret (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | [실전/모의투자]<br>FHMIF10000000 : 선물 옵션 시세 |
| tr_cont | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| custtype | 고객타입 | string | N | 1 | B : 법인<br>P : 개인 |
| seq_no | 일련번호 | string | N | 2 | [법인 필수] 001 |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Query Parameter**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| FID_COND_MRKT_DIV_CODE | FID 조건 시장 분류 코드 | string | Y | 2 | F: 지수선물, O:지수옵션<br>JF: 주식선물, JO:주식옵션<br>CF: 상품선물(금), 금리선물(국채), 통화선물(달러)<br>CM: 야간선물, EU: 야간옵션 |
| FID_INPUT_ISCD | FID 입력 종목코드 | string | Y | 12 | 종목코드 (예: 101S03) |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| tr_id | 거래ID | string | Y | 13 | 요청한 tr_id |
| tr_cont | 연속 거래 여부 | string | Y | 1 | tr_cont를 이용한 다음조회 불가 API |
| gt_uid | Global UID | string | Y | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| rt_cd | 성공 실패 여부 | string | Y | 1 | 0 : 성공<br>0 이외의 값 : 실패 |
| msg_cd | 응답코드 | string | Y | 8 | 응답코드 |
| msg1 | 응답메세지 | string | Y | 80 | 응답메세지 |
| output1 | 응답상세1 | object | Y |  |  |
| hts_kor_isnm | HTS 한글 종목명 | string | Y | 40 | 종목명 |
| futs_prpr | 선물 현재가 | string | Y | 14 | 선물의 현재가격 |
| futs_prdy_vrss | 선물 전일 대비 | string | Y | 14 | 선물의 전일 종가와 당일 현재가의 차이 (당일 현재가-전일 종가) |
| prdy_vrss_sign | 전일 대비 부호 | string | Y | 1 | 1 : 상한 <br>2 : 상승<br>3 : 보합<br>4 : 하한<br>5 : 하락 |
| futs_prdy_clpr | 선물 전일 종가 | string | Y | 14 | 해당 선물 종목의 전일 종가 |
| futs_prdy_ctrt | 선물 전일 대비율 | string | Y | 11 | 선물 전일 대비 / 당일 현재가 * 100 |
| acml_vol | 누적 거래량 | string | Y | 18 | 당일 조회시점까지 전체 거래량 |
| acml_tr_pbmn | 누적 거래 대금 | string | Y | 18 | 당일 조회시점까지 전체 거래금액 |
| hts_otst_stpl_qty | HTS 미결제 약정 수량 | string | Y | 18 | 현재까지 반대매매로 청산되지 않은 계약수 |
| otst_stpl_qty_icdc | 미결제 약정 수량 증감 | string | Y | 10 | 전일대비 미결제 약정 수량의 증감 |
| futs_oprc | 선물 시가2 | string | Y | 14 | 당일 최초 거래가격 |
| futs_hgpr | 선물 최고가 | string | Y | 14 | 당일 조회 시점까지 가장 높은 거래가격 |
| futs_lwpr | 선물 최저가 | string | Y | 14 | 당일 조회 시점까지 가장 낮은 거래가격 |
| futs_mxpr | 선물 상한가 | string | Y | 14 | 당일 거래 가능한 최고 가격 |
| futs_llam | 선물 하한가 | string | Y | 14 | 당일 거래 가능한 최저 가격 |
| basis | 베이시스 | string | Y | 13 | 이론베이시스<br>선물 이론가격과 현물가격과의 차이 |
| futs_sdpr | 선물 기준가 | string | Y | 14 |  |
| hts_thpr | HTS 이론가 | string | Y | 14 | 해당 월물의 이론적 가치를 계산한 것으로 주가지수 선물 이론가격은 (주가지수 선물 이론가격 = 주가지수 + 기간이자비용 - 기간배당수입) 로 계산 |
| dprt | 괴리율 | string | Y | 11 | 현재의 시장가가 이론가격으로부터 얼마나 벗어나 있는지에 대한 측정 자료<br>괴리도 = (현재가 - 이론가격) |
| crbr_aply_mxpr | 서킷브레이커 적용 상한가 | string | Y | 14 |  |
| crbr_aply_llam | 서킷브레이커 적용 하한가 | string | Y | 14 |  |
| futs_last_tr_date | 선물 최종 거래 일자 | string | Y | 8 | 해당 선물 종목의 마지막 거래일 |
| hts_rmnn_dynu | HTS 잔존 일수 | string | Y | 5 | 최종 거래일까지 남은 일수 |
| futs_lstn_medm_hgpr | 선물 상장 중 최고가 | string | Y | 14 | 해당 선물 종목의 상장일 이후 최고 거래가격 |
| futs_lstn_medm_lwpr | 선물 상장 중 최저가 | string | Y | 14 | 해당 선물 종목의 상장일 이후 최저 거래가격 |
| delta_val | 델타 값 | string | Y | 16 | 옵션 종목의 지표값 |
| gama | 감마 | string | Y | 13 | 옵션 종목의 지표값 |
| theta | 세타 | string | Y | 13 | 옵션 종목의 지표값 |
| vega | 베가 | string | Y | 13 | 옵션 종목의 지표값 |
| rho | 로우 | string | Y | 13 | 옵션 종목의 지표값 |
| hist_vltl | 역사적 변동성 | string | Y | 16 | 옵션 종목의 지표값 |
| hts_ints_vltl | HTS 내재 변동성 | string | Y | 16 | 옵션 종목의 지표값 |
| mrkt_basis | 시장 베이시스 | string | Y | 13 | 시장베이시스<br>현재 시장에서 형성된 선물가격과 현물가격과의 차이 |
| acpr | 행사가 | string | Y | 14 | 옵션의 행사가격 |
| output2 | 응답상세2 | object | Y |  |  |
| bstp_cls_code | 업종 구분 코드 | string | Y | 4 |  |
| hts_kor_isnm | HTS 한글 종목명 | string | Y | 40 | 종목명 |
| bstp_nmix_prpr | 업종 지수 현재가 | string | Y | 14 |  |
| prdy_vrss_sign | 전일 대비 부호 | string | Y | 1 |  |
| bstp_nmix_prdy_vrss | 업종 지수 전일 대비 | string | Y | 14 |  |
| bstp_nmix_prdy_ctrt | 업종 지수 전일 대비율 | string | Y | 11 |  |
| output3 | 응답상세3 | object | Y |  |  |
| bstp_cls_code | 업종 구분 코드 | string | Y | 4 |  |
| hts_kor_isnm | HTS 한글 종목명 | string | Y | 40 |  |
| bstp_nmix_prpr | 업종 지수 현재가 | string | Y | 14 |  |
| prdy_vrss_sign | 전일 대비 부호 | string | Y | 1 |  |
| bstp_nmix_prdy_vrss | 업종 지수 전일 대비 | string | Y | 14 |  |
| bstp_nmix_prdy_ctrt | 업종 지수 전일 대비율 | string | Y | 11 |  |

### Example

**Request Example (Python)**

```
{
"fid_cond_mrkt_div_code": "F",
"fid_input_iscd": "101S03"
}
```

**Response Example**

```
{
  "output1": {
    "hts_kor_isnm": "F 202203",
    "futs_prpr": "395.00",
    "futs_prdy_vrss": "6.70",
    "prdy_vrss_sign": "2",
    "futs_prdy_clpr": "388.30",
    "futs_prdy_ctrt": "1.73",
    "acml_vol": "220924",
    "acml_tr_pbmn": "21741293338",
    "hts_otst_stpl_qty": "247121",
    "otst_stpl_qty_icdc": "-592",
    "futs_oprc": "391.05",
    "futs_hgpr": "395.15",
    "futs_lwpr": "391.00",
    "futs_mxpr": "419.35",
    "futs_llam": "357.25",
    "basis": "0.82",
    "futs_sdpr": "388.30",
    "hts_thpr": "395.48",
    "dprt": "-0.12",
    "crbr_aply_mxpr": "0.00",
    "crbr_aply_llam": "0.00",
    "futs_last_tr_date": "20220310",
    "hts_rmnn_dynu": "58",
    "futs_lstn_medm_hgpr": "434.00",
    "futs_lstn_medm_lwpr": "366.60",
    "delta_val": "1.0000",
    "gama": "0.0000",
    "theta": "0.0000",
    "vega": "0.0000",
    "rho": "0.0000",
    "mrkt_basis": "0.34"
  },
  "output2": {
    "bstp_cls_code": "0001",
    "hts_kor_isnm": "종합",
    "bstp_nmix_prpr": "2972.48",
    "prdy_vrss_sign": "2",
    "bstp_nmix_prdy_vrss": "45.10",
    "bstp_nmix_prdy_ctrt": "1.54"
  },
  "output3": {
    "bstp_cls_code": "2001",
    "hts_kor_isnm": "KOSPI200",
    "bstp_nmix_prpr": "394.66",
    "prdy_vrss_sign": "2",
    "bstp_nmix_prdy_vrss": "5.69",
    "bstp_nmix_prdy_ctrt": "1.46"
  },
  "rt_cd": "0",
  "msg_cd": "MCA00000",
  "msg1": "정상처리 되었습니다!"
}
```

---

## 국내선물 기초자산 시세

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [국내선물옵션] 기본시세 |
| API 명 | 국내선물 기초자산 시세 |
| API ID | 국내선물-021 |
| 실전 TR_ID | FHPIF05030000 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-futureoption/v1/quotations/display-board-top |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 206 |

### 개요

국내선물 기초자산 시세 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0503] 선물옵션 종합시세(Ⅰ) 화면의 "상단 바" 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | FHPIF05030000 |
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
| FID_COND_MRKT_DIV_CODE | 조건 시장 분류 코드 | string | Y | 2 | 시장구분코드 (F: 선물) |
| FID_INPUT_ISCD | 입력 종목코드 | string | Y | 12 | 선물최근월물 ex)(101V06) |
| FID_COND_MRKT_DIV_CODE1 | 조건 시장 분류 코드 | string | Y | 2 | 공백 |
| FID_COND_SCR_DIV_CODE | 조건 화면 분류 코드 | string | Y | 5 | 공백 |
| FID_MTRT_CNT | 만기 수 | string | Y | 11 | 공백 |
| FID_COND_MRKT_CLS_CODE | 조건 시장 구분 코드 | string | Y | 6 | 공백 |

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
| output1 | 응답상세 | object | Y |  |  |
| unas_prpr | 기초자산 현재가 | string | Y | 112 |  |
| unas_prdy_vrss | 기초자산 전일 대비 | string | Y | 112 |  |
| unas_prdy_vrss_sign | 기초자산 전일 대비 부호 | string | Y | 1 |  |
| unas_prdy_ctrt | 기초자산 전일 대비율 | string | Y | 82 |  |
| unas_acml_vol | 기초자산 누적 거래량 | string | Y | 18 |  |
| hts_kor_isnm | HTS 한글 종목명 | string | Y | 40 |  |
| futs_prpr | 선물 현재가 | string | Y | 112 |  |
| futs_prdy_vrss | 선물 전일 대비 | string | Y | 112 |  |
| prdy_vrss_sign | 전일 대비 부호 | string | Y | 1 |  |
| futs_prdy_ctrt | 선물 전일 대비율 | string | Y | 82 |  |
| output2 | 응답상세 | object array | Y |  | array |
| hts_rmnn_dynu | HTS 잔존 일수 | string | Y | 5 |  |

### Example

**Request Example (Python)**

```
fid_cond_mrkt_div_code:F
fid_input_iscd:101V06
fid_cond_mrkt_div_code1:
fid_cond_scr_div_code:
fid_mtrt_cnt:
fid_cond_mrkt_cls_code:
```

**Response Example**

```
{
    "output1": {
        "unas_prpr": "367.25",
        "unas_prdy_vrss": "-3.47",
        "unas_prdy_vrss_sign": "5",
        "unas_prdy_ctrt": "-0.94",
        "unas_acml_vol": "161725000",
        "hts_kor_isnm": "F 202406",
        "futs_prpr": "369.35",
        "futs_prdy_vrss": "-3.45",
        "prdy_vrss_sign": "5",
        "futs_prdy_ctrt": "-0.93"
    },
    "output2": [],
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다."
}
```

---

## 선물옵션 일중예상체결추이

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [국내선물옵션] 기본시세 |
| API 명 | 선물옵션 일중예상체결추이 |
| API ID | 국내선물-018 |
| 실전 TR_ID | FHPIF05110100 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-futureoption/v1/quotations/exp-price-trend |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 207 |

### 개요

선물옵션 일중예상체결추이 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0548] 선물옵션 예상체결추이 화면의 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | FHPIF05110100 |
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
| FID_INPUT_ISCD | 입력 종목코드 | string | Y | 12 | 종목번호 (지수선물:6자리, 지수옵션 9자리) |
| FID_COND_MRKT_DIV_CODE | 조건 시장 분류 코드 | string | Y | 2 | F : 지수선물, O : 지수옵션 |

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
| output1 | 응답상세 | object | Y |  |  |
| hts_kor_isnm | 영업 시간 | string | Y | 40 |  |
| futs_antc_cnpr | 업종 지수 현재가 | string | Y | 112 |  |
| antc_cntg_vrss_sign | 업종 지수 전일 대비 | string | Y | 1 |  |
| futs_antc_cntg_vrss | 전일 대비 부호 | string | Y | 112 |  |
| antc_cntg_prdy_ctrt | 업종 지수 전일 대비율 | string | Y | 82 |  |
| futs_sdpr | 누적 거래 대금 | string | Y | 112 |  |
| output2 | 응답상세 | object array | Y |  | array |
| stck_cntg_hour | 주식체결시간 | string | Y | 6 |  |
| futs_antc_cnpr | 선물예상체결가 | string | Y | 112 |  |
| antc_cntg_vrss_sign | 예상체결대비부호 | string | Y | 1 |  |
| futs_antc_cntg_vrss | 선물예상체결대비 | string | Y | 112 |  |
| antc_cntg_prdy_ctrt | 예상체결전일대비율 | string | Y | 82 |  |

### Example

**Request Example (Python)**

```
FID_COND_MRKT_DIV_CODE:F
FID_INPUT_ISCD:101V06
```

**Response Example**

```
{
    "output1": {
        "hts_kor_isnm": "F 202406",
        "futs_antc_cnpr": "0.000",
        "antc_cntg_vrss_sign": "0",
        "futs_antc_cntg_vrss": "0.000",
        "antc_cntg_prdy_ctrt": "0.00",
        "futs_sdpr": "376.95"
    },
    "output2": [
        {
            "stck_cntg_hour": "084500",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "380.00",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.05",
            "antc_cntg_prdy_ctrt": "0.81"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "380.00",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.05",
            "antc_cntg_prdy_ctrt": "0.81"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "380.00",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.05",
            "antc_cntg_prdy_ctrt": "0.81"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "380.00",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.05",
            "antc_cntg_prdy_ctrt": "0.81"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.95",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "3.00",
            "antc_cntg_prdy_ctrt": "0.80"
        },
        {
            "stck_cntg_hour": "084459",
            "futs_antc_cnpr": "379.90",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.95",
            "antc_cntg_prdy_ctrt": "0.78"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.90",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.95",
            "antc_cntg_prdy_ctrt": "0.78"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.90",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.95",
            "antc_cntg_prdy_ctrt": "0.78"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.90",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.95",
            "antc_cntg_prdy_ctrt": "0.78"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.90",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.95",
            "antc_cntg_prdy_ctrt": "0.78"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.90",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.95",
            "antc_cntg_prdy_ctrt": "0.78"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.90",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.95",
            "antc_cntg_prdy_ctrt": "0.78"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.90",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.95",
            "antc_cntg_prdy_ctrt": "0.78"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.80",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.85",
            "antc_cntg_prdy_ctrt": "0.76"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.80",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.85",
            "antc_cntg_prdy_ctrt": "0.76"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.75",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.80",
            "antc_cntg_prdy_ctrt": "0.74"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.75",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.80",
            "antc_cntg_prdy_ctrt": "0.74"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.75",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.80",
            "antc_cntg_prdy_ctrt": "0.74"
        },
        {
            "stck_cntg_hour": "084458",
            "futs_antc_cnpr": "379.75",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.80",
            "antc_cntg_prdy_ctrt": "0.74"
        },
        {
            "stck_cntg_hour": "084457",
            "futs_antc_cnpr": "379.75",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.80",
            "antc_cntg_prdy_ctrt": "0.74"
        },
        {
            "stck_cntg_hour": "084457",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084457",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084457",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084457",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084457",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084457",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084457",
            "futs_antc_cnpr": "379.75",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.80",
            "antc_cntg_prdy_ctrt": "0.74"
        },
        {
            "stck_cntg_hour": "084457",
            "futs_antc_cnpr": "379.75",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.80",
            "antc_cntg_prdy_ctrt": "0.74"
        },
        {
            "stck_cntg_hour": "084457",
            "futs_antc_cnpr": "379.55",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.60",
            "antc_cntg_prdy_ctrt": "0.69"
        },
        {
            "stck_cntg_hour": "084457",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084456",
            "futs_antc_cnpr": "379.55",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.60",
            "antc_cntg_prdy_ctrt": "0.69"
        },
        {
            "stck_cntg_hour": "084456",
            "futs_antc_cnpr": "379.55",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.60",
            "antc_cntg_prdy_ctrt": "0.69"
        },
        {
            "stck_cntg_hour": "084456",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084456",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084456",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084456",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084456",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084456",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084456",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084455",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084455",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084455",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084455",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084455",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084455",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084455",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084455",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084455",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084455",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084455",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084454",
            "futs_antc_cnpr": "379.70",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.75",
            "antc_cntg_prdy_ctrt": "0.73"
        },
        {
            "stck_cntg_hour": "084454",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084454",
            "futs_antc_cnpr": "379.55",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.60",
            "antc_cntg_prdy_ctrt": "0.69"
        },
        {
            "stck_cntg_hour": "084454",
            "futs_antc_cnpr": "379.55",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.60",
            "antc_cntg_prdy_ctrt": "0.69"
        },
        {
            "stck_cntg_hour": "084454",
            "futs_antc_cnpr": "379.55",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.60",
            "antc_cntg_prdy_ctrt": "0.69"
        },
        {
            "stck_cntg_hour": "084454",
            "futs_antc_cnpr": "379.60",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.65",
            "antc_cntg_prdy_ctrt": "0.70"
        },
        {
            "stck_cntg_hour": "084454",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084454",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084454",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084454",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084454",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084453",
            "futs_antc_cnpr": "379.65",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.70",
            "antc_cntg_prdy_ctrt": "0.72"
        },
        {
            "stck_cntg_hour": "084453",
            "futs_antc_cnpr": "379.60",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.65",
            "antc_cntg_prdy_ctrt": "0.70"
        },
        {
            "stck_cntg_hour": "084453",
            "futs_antc_cnpr": "379.55",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.60",
            "antc_cntg_prdy_ctrt": "0.69"
        },
        {
            "stck_cntg_hour": "084453",
            "futs_antc_cnpr": "379.55",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.60",
            "antc_cntg_prdy_ctrt": "0.69"
        },
        {
            "stck_cntg_hour": "084453",
            "futs_antc_cnpr": "379.55",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.60",
            "antc_cntg_prdy_ctrt": "0.69"
        },
        {
            "stck_cntg_hour": "084453",
            "futs_antc_cnpr": "379.55",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.60",
            "antc_cntg_prdy_ctrt": "0.69"
        },
        {
            "stck_cntg_hour": "084453",
            "futs_antc_cnpr": "379.55",
            "antc_cntg_vrss_sign": "2",
            "futs_antc_cntg_vrss": "2.60",
            "antc_cntg_prdy_ctrt": "0.69"
        }
    ],
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다."
}
```

---

## 선물옵션기간별시세(일/주/월/년)

> ⚠️ 시트를 찾지 못했습니다.

## 국내옵션전광판_선물

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [국내선물옵션] 기본시세 |
| API 명 | 국내옵션전광판_선물 |
| API ID | 국내선물-023 |
| 실전 TR_ID | FHPIF05030200 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-futureoption/v1/quotations/display-board-futures |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 209 |

### 개요

국내옵션전광판_선물 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0503] 선물옵션 종합시세(Ⅰ) 화면의 "하단" 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | FHPIF05030200 |
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
| FID_COND_MRKT_DIV_CODE | 조건 시장 분류 코드 | string | Y | 2 | 시장구분코드 (F: 선물) |
| FID_COND_SCR_DIV_CODE | 조건 화면 분류 코드 | string | Y | 5 | Unique key(20503) |
| FID_COND_MRKT_CLS_CODE | 조건 시장 구분 코드 | string | Y | 6 | 공백: KOSPI200<br>MKI: 미니KOSPI200<br>WKM: KOSPI200위클리(월)<br>WKI: KOSPI200위클리(목)<br>KQI: KOSDAQ150 |

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
| futs_shrn_iscd | 선물 단축 종목코드 | string | Y | 9 |  |
| hts_kor_isnm | HTS 한글 종목명 | string | Y | 40 |  |
| futs_prpr | 선물 현재가 | string | Y | 112 |  |
| futs_prdy_vrss | 선물 전일 대비 | string | Y | 112 |  |
| prdy_vrss_sign | 전일 대비 부호 | string | Y | 1 |  |
| futs_prdy_ctrt | 선물 전일 대비율 | string | Y | 82 |  |
| hts_thpr | HTS 이론가 | string | Y | 112 |  |
| acml_vol | 누적 거래량 | string | Y | 18 |  |
| futs_askp | 선물 매도호가 | string | Y | 112 |  |
| futs_bidp | 선물 매수호가 | string | Y | 112 |  |
| hts_otst_stpl_qty | HTS 미결제 약정 수량 | string | Y | 18 |  |
| futs_hgpr | 선물 최고가 | string | Y | 112 |  |
| futs_lwpr | 선물 최저가 | string | Y | 112 |  |
| hts_rmnn_dynu | HTS 잔존 일수 | string | Y | 5 |  |
| total_askp_rsqn | 총 매도호가 잔량 | string | Y | 12 |  |
| total_bidp_rsqn | 총 매수호가 잔량 | string | Y | 12 |  |
| futs_antc_cnpr | 선물예상체결가 | string | Y | 112 |  |
| futs_antc_cntg_vrss | 선물예상체결대비 | string | Y | 112 |  |
| antc_cntg_vrss_sign | 예상 체결 대비 부호 | string | Y | 1 |  |
| antc_cntg_prdy_ctrt | 예상 체결 전일 대비율 | string | Y | 82 |  |

### Example

**Request Example (Python)**

```
FID_COND_MRKT_DIV_CODE:F
FID_COND_SCR_DIV_CODE:20503
FID_COND_MRKT_CLS_CODE:MKI
```

**Response Example**

```
{
    "output": [
        {
            "futs_shrn_iscd": "105V05",
            "hts_kor_isnm": "미니F 202405",
            "futs_prpr": "368.28",
            "futs_prdy_vrss": "-3.32",
            "prdy_vrss_sign": "5",
            "futs_prdy_ctrt": "-0.89",
            "hts_thpr": "368.26",
            "acml_vol": "91624",
            "futs_askp": "368.28",
            "futs_bidp": "368.26",
            "hts_otst_stpl_qty": "38188",
            "futs_hgpr": "372.86",
            "futs_lwpr": "367.40",
            "hts_rmnn_dynu": "28",
            "total_askp_rsqn": "934",
            "total_bidp_rsqn": "282",
            "futs_antc_cnpr": "0.00",
            "futs_antc_cntg_vrss": "0.00",
            "antc_cntg_vrss_sign": "0",
            "antc_cntg_prdy_ctrt": "0.00"
        },
        {
            "futs_shrn_iscd": "105V06",
            "hts_kor_isnm": "미니F 202406",
            "futs_prpr": "369.48",
            "futs_prdy_vrss": "-3.32",
            "prdy_vrss_sign": "5",
            "futs_prdy_ctrt": "-0.89",
            "hts_thpr": "369.51",
            "acml_vol": "621",
            "futs_askp": "369.54",
            "futs_bidp": "369.48",
            "hts_otst_stpl_qty": "3433",
            "futs_hgpr": "374.16",
            "futs_lwpr": "368.64",
            "hts_rmnn_dynu": "63",
            "total_askp_rsqn": "68",
            "total_bidp_rsqn": "53",
            "futs_antc_cnpr": "0.00",
            "futs_antc_cntg_vrss": "0.00",
            "antc_cntg_vrss_sign": "0",
            "antc_cntg_prdy_ctrt": "0.00"
        },
        {
            "futs_shrn_iscd": "105V07",
            "hts_kor_isnm": "미니F 202407",
            "futs_prpr": "369.00",
            "futs_prdy_vrss": "-3.98",
            "prdy_vrss_sign": "5",
            "futs_prdy_ctrt": "-1.07",
            "hts_thpr": "369.43",
            "acml_vol": "19",
            "futs_askp": "370.24",
            "futs_bidp": "367.52",
            "hts_otst_stpl_qty": "31",
            "futs_hgpr": "372.00",
            "futs_lwpr": "369.00",
            "hts_rmnn_dynu": "91",
            "total_askp_rsqn": "257",
            "total_bidp_rsqn": "13",
            "futs_antc_cnpr": "0.00",
            "futs_antc_cntg_vrss": "0.00",
            "antc_cntg_vrss_sign": "0",
            "antc_cntg_prdy_ctrt": "0.00"
        },
        {
            "futs_shrn_iscd": "105V08",
            "hts_kor_isnm": "미니F 202408",
            "futs_prpr": "373.78",
            "futs_prdy_vrss": "0.00",
            "prdy_vrss_sign": "3",
            "futs_prdy_ctrt": "0.00",
            "hts_thpr": "370.41",
            "acml_vol": "0",
            "futs_askp": "403.58",
            "futs_bidp": "344.00",
            "hts_otst_stpl_qty": "1",
            "futs_hgpr": "0.00",
            "futs_lwpr": "0.00",
            "hts_rmnn_dynu": "119",
            "total_askp_rsqn": "4",
            "total_bidp_rsqn": "5",
            "futs_antc_cnpr": "0.00",
            "futs_antc_cntg_vrss": "0.00",
            "antc_cntg_vrss_sign": "0",
            "antc_cntg_prdy_ctrt": "0.00"
        },
        {
            "futs_shrn_iscd": "105V09",
            "hts_kor_isnm": "미니F 202409",
            "futs_prpr": "374.00",
            "futs_prdy_vrss": "-0.50",
            "prdy_vrss_sign": "5",
            "futs_prdy_ctrt": "-0.13",
            "hts_thpr": "371.67",
            "acml_vol": "3",
            "futs_askp": "404.36",
            "futs_bidp": "369.82",
            "hts_otst_stpl_qty": "10",
            "futs_hgpr": "374.00",
            "futs_lwpr": "371.00",
            "hts_rmnn_dynu": "154",
            "total_askp_rsqn": "4",
            "total_bidp_rsqn": "12",
            "futs_antc_cnpr": "0.00",
            "futs_antc_cntg_vrss": "0.00",
            "antc_cntg_vrss_sign": "0",
            "antc_cntg_prdy_ctrt": "0.00"
        },
        {
            "futs_shrn_iscd": "105V10",
            "hts_kor_isnm": "미니F 202410",
            "futs_prpr": "375.26",
            "futs_prdy_vrss": "0.00",
            "prdy_vrss_sign": "3",
            "futs_prdy_ctrt": "0.00",
            "hts_thpr": "371.72",
            "acml_vol": "0",
            "futs_askp": "405.18",
            "futs_bidp": "345.34",
            "hts_otst_stpl_qty": "0",
            "futs_hgpr": "0.00",
            "futs_lwpr": "0.00",
            "hts_rmnn_dynu": "182",
            "total_askp_rsqn": "4",
            "total_bidp_rsqn": "4",
            "futs_antc_cnpr": "0.00",
            "futs_antc_cntg_vrss": "0.00",
            "antc_cntg_vrss_sign": "0",
            "antc_cntg_prdy_ctrt": "0.00"
        }
    ],
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다."
}
```

---

## 선물옵션 분봉조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [국내선물옵션] 기본시세 |
| API 명 | 선물옵션 분봉조회 |
| API ID | v1_국내선물-012 |
| 실전 TR_ID | FHKIF03020200 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-futureoption/v1/quotations/inquire-time-fuopchartprice |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 210 |

### 개요

선물옵션 분봉조회 API입니다.
실전계좌의 경우, 한 번의 호출에 최대 102건까지 확인 가능하며, 
FID_INPUT_DATE_1(입력날짜), FID_INPUT_HOUR_1(입력시간)을 이용하여 다음조회 가능합니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | FHKIF03020200 |
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
| FID_COND_MRKT_DIV_CODE | FID 조건 시장 분류 코드 | string | Y | 2 | F: 지수선물, O:지수옵션<br>JF: 주식선물, JO:주식옵션,<br>CF: 상품선물(금), 금리선물(국채), 통화선물(달러)<br>CM: 야간선물, EU: 야간옵션 |
| FID_INPUT_ISCD | FID 입력 종목코드 | string | Y | 12 | 종목번호 (지수선물:6자리, 지수옵션 9자리) |
| FID_HOUR_CLS_CODE | FID 시간 구분 코드 | string | Y | 5 | FID 시간 구분 코드(30: 30초, 60: 1분, 3600: 1시간) |
| FID_PW_DATA_INCU_YN | FID 과거 데이터 포함 여부 | string | Y | 2 | Y(과거) / N (당일) |
| FID_FAKE_TICK_INCU_YN | FID 허봉 포함 여부 | string | Y | 2 | N으로 입력 |
| FID_INPUT_DATE_1 | FID 입력 날짜1 | string | Y | 10 | 입력 날짜 기준으로 이전 기간 조회(YYYYMMDD)<br>ex) 20230908 입력 시, 2023년 9월 8일부터 일자 역순으로 조회 |
| FID_INPUT_HOUR_1 | FID 입력 시간1 | string | Y | 10 | 입력 시간 기준으로 이전 시간 조회(HHMMSS)<br>ex) 093000 입력 시, 오전 9시 30분부터 역순으로 분봉 조회<br><br>* CM(야간선물), EU(야간옵션)인 경우, 자정 이후 시간은 +24시간으로 입력<br>ex) 253000 입력 시, 새벽 1시 30분부터 역순으로 분봉 조회 |

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
| Output1 | 응답상세 | object array | Y |  |  |
| futs_prdy_vrss | 선물 전일 대비 | string | Y | 11 |  |
| prdy_vrss_sign | 전일 대비 부호 | string | Y | 1 |  |
| futs_prdy_ctrt | 선물 전일 대비율 | string | Y | 8 |  |
| futs_prdy_clpr | 선물 전일 종가 | string | Y | 11 |  |
| prdy_nmix | 전일 지수 | string | Y | 11 |  |
| acml_vol | 누적 거래량 | string | Y | 18 |  |
| acml_tr_pbmn | 누적 거래 대금 | string | Y | 18 |  |
| hts_kor_isnm | HTS 한글 종목명 | string | Y | 40 |  |
| futs_prpr | 선물 현재가 | string | Y | 11 |  |
| futs_shrn_iscd | 선물 단축 종목코드 | string | Y | 9 |  |
| prdy_vol | 전일 거래량 | string | Y | 18 |  |
| futs_mxpr | 선물 상한가 | string | Y | 11 |  |
| futs_llam | 선물 하한가 | string | Y | 11 |  |
| futs_oprc | 선물 시가2 | string | Y | 11 |  |
| futs_hgpr | 선물 최고가 | string | Y | 11 |  |
| futs_lwpr | 선물 최저가 | string | Y | 11 |  |
| futs_prdy_oprc | 선물 전일 시가 | string | Y | 11 |  |
| futs_prdy_hgpr | 선물 전일 최고가 | string | Y | 11 |  |
| futs_prdy_lwpr | 선물 전일 최저가 | string | Y | 11 |  |
| futs_askp | 선물 매도호가 | string | Y | 11 |  |
| futs_bidp | 선물 매수호가 | string | Y | 11 |  |
| basis | 베이시스 | string | Y | 8 |  |
| kospi200_nmix | KOSPI200 지수 | string | Y | 11 |  |
| kospi200_prdy_vrss | KOSPI200 전일 대비 | string | Y | 18 |  |
| kospi200_prdy_ctrt | KOSPI200 전일 대비율 | string | Y | 8 |  |
| kospi200_prdy_vrss_sign | KOSPI200 전일 대비 부호 | string | Y | 1 |  |
| hts_otst_stpl_qty | HTS 미결제 약정 수량 | string | Y | 18 |  |
| otst_stpl_qty_icdc | 미결제 약정 수량 증감 | string | Y | 10 |  |
| tday_rltv | 당일 체결강도 | string | Y | 11 |  |
| hts_thpr | HTS 이론가 | string | Y | 11 |  |
| dprt | 괴리율 | string | Y | 8 |  |
| Output2 | 응답상세2 | object | Y |  | array |
| stck_bsop_date | 주식 영업 일자 | string | Y | 8 |  |
| stck_cntg_hour | 주식 체결 시간 | string | Y | 6 | CM(야간선물), EU(야간옵션)인 경우, 자정 이후 시간은 +24시간으로 표시<br>ex) "260000"인 경우, 오전 4시를 의미 |
| futs_prpr | 선물 현재가 | string | Y | 11 |  |
| futs_oprc | 선물 시가2 | string | Y | 11 |  |
| futs_hgpr | 선물 최고가 | string | Y | 11 |  |
| futs_lwpr | 선물 최저가 | string | Y | 11 |  |
| cntg_vol | 체결 거래량 | string | Y | 18 |  |
| acml_tr_pbmn | 누적 거래 대금 | string | Y | 18 |  |

### Example

**Request Example (Python)**

```
fid_cond_mrkt_div_code:F
fid_input_iscd:101V09
fid_hour_cls_code:30
fid_pw_data_incu_yn:N
fid_fake_tick_incu_yn:Y
fid_input_date_1:
fid_input_hour_1:
```

**Response Example**

```
{
    "output1": {
        "futs_prdy_vrss": "-0.30",
        "prdy_vrss_sign": "5",
        "futs_prdy_ctrt": "-0.08",
        "futs_prdy_clpr": "359.90",
        "prdy_nmix": "359.90",
        "acml_vol": "349",
        "acml_tr_pbmn": "31394925",
        "hts_kor_isnm": "F 202409",
        "futs_prpr": "359.60",
        "futs_shrn_iscd": "101V09",
        "prdy_vol": "721",
        "futs_mxpr": "388.65",
        "futs_llam": "331.15",
        "futs_oprc": "361.50",
        "futs_hgpr": "362.00",
        "futs_lwpr": "357.20",
        "futs_prdy_oprc": "364.95",
        "futs_prdy_hgpr": "365.30",
        "futs_prdy_lwpr": "358.60",
        "futs_askp": "359.65",
        "futs_bidp": "359.50",
        "basis": "4.06",
        "kospi200_nmix": "356.42",
        "hts_otst_stpl_qty": "11529",
        "otst_stpl_qty_icdc": "0",
        "tday_rltv": "78.97",
        "hts_thpr": "360.48",
        "dprt": "-0.25"
    },
    "output2": [
        {
            "stck_bsop_date": "20240417",
            "stck_cntg_hour": "141500",
            "futs_prpr": "359.60",
            "futs_oprc": "359.60",
            "futs_hgpr": "359.60",
            "futs_lwpr": "359.60",
            "cntg_vol": "0",
            "acml_tr_pbmn": "31394925"
        },
        {
            "stck_bsop_date": "20240417",
            "stck_cntg_hour": "141430",
            "futs_prpr": "359.60",
            "futs_oprc": "359.60",
            "futs_hgpr": "359.60",
            "futs_lwpr": "359.60",
            "cntg_vol": "0",
            "acml_tr_pbmn": "31394925"
        },
        {
            "stck_bsop_date": "20240417",
            "stck_cntg_hour": "141400",
            "futs_prpr": "359.60",
            "futs_oprc": "359.60",
            "futs_hgpr": "359.60",
            "futs_lwpr": "359.60",
            "cntg_vol": "0",
            "acml_tr_pbmn": "31394925"
        },
        {
            "stck_bsop_date": "20240417",
            "stck_cntg_hour": "141330",
            "futs_prpr": "359.60",
            "futs_oprc": "359.60",
            "futs_hgpr": "359.60",
            "futs_lwpr": "359.60",
            "cntg_vol": "0",
            "acml_tr_pbmn": "31394925"
        },...
    ],
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다."
}
```

---

## 국내옵션전광판_옵션월물리스트

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [국내선물옵션] 기본시세 |
| API 명 | 국내옵션전광판_옵션월물리스트 |
| API ID | 국내선물-020 |
| 실전 TR_ID | FHPIO056104C0 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-futureoption/v1/quotations/display-board-option-list |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 211 |

### 개요

국내업종 국내옵션전광판_옵션월물리스트 API입니다. 
한국투자 HTS(eFriend Plus) &gt; [0503] 선물옵션 종합시세(Ⅰ) 화면의 "월물리스트 목록 확인" 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | FHPIO056104C0 |
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
| FID_COND_SCR_DIV_CODE | 조건 화면 분류 코드 | string | Y | 5 | Unique key(509) |
| FID_COND_MRKT_DIV_CODE | 조건 시장 분류 코드 | string | Y | 2 | 공백 |
| FID_COND_MRKT_CLS_CODE | 조건 시장 구분 코드 | string | Y | 6 | 공백 |

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
| mtrt_yymm_code | 만기 년월 코드 | string | Y | 6 |  |
| mtrt_yymm | 만기 년월 | string | Y | 6 |  |

### Example

**Request Example (Python)**

```
fid_cond_scr_div_code:509
fid_cond_mrkt_div_code:
fid_cond_mrkt_cls_code:
```

**Response Example**

```
{
    "output": [
        {
            "mtrt_yymm_code": "0V05",
            "mtrt_yymm": "202405"
        },
        {
            "mtrt_yymm_code": "0V06",
            "mtrt_yymm": "202406"
        },
        {
            "mtrt_yymm_code": "0V07",
            "mtrt_yymm": "202407"
        },
        {
            "mtrt_yymm_code": "0V08",
            "mtrt_yymm": "202408"
        },
        {
            "mtrt_yymm_code": "0V09",
            "mtrt_yymm": "202409"
        },
        {
            "mtrt_yymm_code": "0V10",
            "mtrt_yymm": "202410"
        },
        {
            "mtrt_yymm_code": "0V12",
            "mtrt_yymm": "202412"
        },
        {
            "mtrt_yymm_code": "0W03",
            "mtrt_yymm": "202503"
        },
        {
            "mtrt_yymm_code": "0W06",
            "mtrt_yymm": "202506"
        },
        {
            "mtrt_yymm_code": "0W12",
            "mtrt_yymm": "202512"
        },
        {
            "mtrt_yymm_code": "0612",
            "mtrt_yymm": "202612"
        }
    ],
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다."
}
```

---

## 선물옵션 시세호가

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [국내선물옵션] 기본시세 |
| API 명 | 선물옵션 시세호가 |
| API ID | v1_국내선물-007 |
| 실전 TR_ID | FHMIF10010000 |
| 모의 TR_ID | FHMIF10010000 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-futureoption/v1/quotations/inquire-asking-price |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | https://openapivts.koreainvestment.com:29443 |
| 순번 | 212 |

### 개요

선물옵션 시세호가 API입니다.

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | N | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용)<br><br>※ 토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출<br>EX) "Bearer eyJ..........8GA" |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appsecret (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | [실전/모의투자]<br>FHMIF10010000 : 선물 옵션 시세 호가 |
| tr_cont | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| custtype | 고객타입 | string | N | 1 | B : 법인<br>P : 개인 |
| seq_no | 일련번호 | string | N | 2 | [법인 필수] 001 |
| mac_address | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| phone_number | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 <br>ex) 01011112222 (하이픈 등 구분값 제거) |
| ip_addr | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| gt_uid | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Request Query Parameter**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| FID_COND_MRKT_DIV_CODE | FID 조건 시장 분류 코드 | string | Y | 2 | F: 지수선물, O:지수옵션<br>JF: 주식선물, JO:주식옵션<br>CF: 상품선물(금), 금리선물(국채), 통화선물(달러)<br>CM: 야간선물, EU: 야간옵션 |
| FID_INPUT_ISCD | FID 입력 종목코드 | string | Y | 12 | 종목코드 (예: 101S03) |

**Response Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| tr_id | 거래ID | string | Y | 13 | 요청한 tr_id |
| tr_cont | 연속 거래 여부 | string | Y | 1 | tr_cont를 이용한 다음조회 불가 API |
| gt_uid | Global UID | string | Y | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

**Response Body**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| rt_cd | 성공 실패 여부 | string | Y | 1 | 0 : 성공<br>0 이외의 값 : 실패 |
| msg_cd | 응답코드 | string | Y | 8 | 응답코드 |
| msg1 | 응답메세지 | string | Y | 80 | 응답메세지 |
| output1 | 응답상세1 | object | Y |  |  |
| hts_kor_isnm | HTS 한글 종목명 | string | Y | 40 | 종목명 |
| futs_prpr | 선물 현재가 | string | Y | 14 | 선물의 현재가격 |
| prdy_vrss_sign | 전일 대비 부호 | string | Y | 1 | 1 : 상한 <br>2 : 상승<br>3 : 보합<br>4 : 하한<br>5 : 하락 |
| futs_prdy_vrss | 선물 전일 대비 | string | Y | 14 | 선물의 전일 종가와 당일 현재가의 차이 (당일 현재가-전일 종가) |
| futs_prdy_ctrt | 선물 전일 대비율 | string | Y | 11 | 선물 전일 대비 / 당일 현재가 * 100 |
| acml_vol | 누적 거래량 | string | Y | 18 | 당일 조회시점까지 전체 거래량 |
| futs_prdy_clpr | 선물 전일 종가 | string | Y | 14 | 해당 선물 종목의 전일 종가 |
| futs_shrn_iscd | 선물 단축 종목코드 | string | Y | 9 |  |
| output2 | 응답상세2 | object array | Y |  | Array |
| futs_askp1 | 선물 매도호가1 | string | Y | 14 | 해당 종목의 매도호가 중 1번째 낮은 호가 |
| futs_askp2 | 선물 매도호가2 | string | Y | 14 | 해당 종목의 매도호가 중 2번째 낮은 호가 |
| futs_askp3 | 선물 매도호가3 | string | Y | 14 | 해당 종목의 매도호가 중 3번째 낮은 호가 |
| futs_askp4 | 선물 매도호가4 | string | Y | 14 | 해당 종목의 매도호가 중 4번째 낮은 호가 |
| futs_askp5 | 선물 매도호가5 | string | Y | 14 | 해당 종목의 매도호가 중 5번째 낮은 호가 |
| futs_bidp1 | 선물 매수호가1 | string | Y | 14 | 해당 종목의 매수호가 중 가장 높은 호가 |
| futs_bidp2 | 선물 매수호가1 | string | Y | 14 | 해당 종목의 매수호가 중 2번째 높은 호가 |
| futs_bidp3 | 선물 매수호가3 | string | Y | 14 | 해당 종목의 매수호가 중 3번째 높은 호가 |
| futs_bidp4 | 선물 매수호가4 | string | Y | 14 | 해당 종목의 매수호가 중 4번째 높은 호가 |
| futs_bidp5 | 선물 매수호가5 | string | Y | 14 | 해당 종목의 매수호가 중 5번째 높은 호가 |
| askp_rsqn1 | 매도호가 잔량1 | string | Y | 12 | 매도호가 1의 미체결수량 |
| askp_rsqn2 | 매도호가 잔량2 | string | Y | 12 | 매도호가 2의 미체결수량 |
| askp_rsqn3 | 매도호가 잔량3 | string | Y | 12 | 매도호가 3의 미체결수량 |
| askp_rsqn4 | 매도호가 잔량4 | string | Y | 12 | 매도호가 4의 미체결수량 |
| askp_rsqn5 | 매도호가 잔량5 | string | Y | 12 | 매도호가 5의 미체결수량 |
| bidp_rsqn1 | 매수호가 잔량1 | string | Y | 12 | 매수호가 1의 미체결수량 |
| bidp_rsqn2 | 매수호가 잔량2 | string | Y | 12 | 매수호가 2의 미체결수량 |
| bidp_rsqn3 | 매수호가 잔량3 | string | Y | 12 | 매수호가 3의 미체결수량 |
| bidp_rsqn4 | 매수호가 잔량4 | string | Y | 12 | 매수호가 4의 미체결수량 |
| bidp_rsqn5 | 매수호가 잔량5 | string | Y | 12 | 매수호가 5의 미체결수량 |
| askp_csnu1 | 매도호가 건수1 | string | Y | 10 | 매도호가 1의 미체결 주문 건수 |
| askp_csnu2 | 매도호가 건수2 | string | Y | 10 | 매도호가 2의 미체결 주문 건수 |
| askp_csnu3 | 매도호가 건수3 | string | Y | 10 | 매도호가 3의 미체결 주문 건수 |
| askp_csnu4 | 매도호가 건수4 | string | Y | 10 | 매도호가 4의 미체결 주문 건수 |
| askp_csnu5 | 매도호가 건수5 | string | Y | 10 | 매도호가 5의 미체결 주문 건수 |
| bidp_csnu1 | 매수호가 건수1 | string | Y | 10 | 매수호가 1의 미체결 주문 건수 |
| bidp_csnu2 | 매수호가 건수2 | string | Y | 10 | 매수호가 2의 미체결 주문 건수 |
| bidp_csnu3 | 매수호가 건수3 | string | Y | 10 | 매수호가 3의 미체결 주문 건수 |
| bidp_csnu4 | 매수호가 건수4 | string | Y | 10 | 매수호가 4의 미체결 주문 건수 |
| bidp_csnu5 | 매수호가 건수5 | string | Y | 10 | 매수호가 5의 미체결 주문 건수 |
| total_askp_rsqn | 총 매도호가 잔량 | string | Y | 12 | 매도호가 1~5의 잔량 합계 |
| total_bidp_rsqn | 총 매수호가 잔량 | string | Y | 12 | 매수호가 1~5의 잔량 합계 |
| total_askp_csnu | 총 매도호가 건수 | string | Y | 10 | 매도호가 1~5의 미체결 주문 건수 합계 |
| total_bidp_csnu | 총 매수호가 건수 | string | Y | 10 | 매수호가 1~5의 미체결 주문 건수 합계 |
| aspr_acpt_hour | 호가 접수 시간 | string | Y | 6 | 가장 최근 호가의 접수 시간 |

### Example

**Request Example (Python)**

```
{
"fid_cond_mrkt_div_code" : "F",
"fid_input_iscd" : "101S06"
}
```

**Response Example**

```
{
  "output1": {
    "hts_kor_isnm": "F 202206",
    "futs_prpr": "364.40",
    "prdy_vrss_sign": "2",
    "futs_prdy_vrss": "3.00",
    "futs_prdy_ctrt": "0.83",
    "acml_vol": "193112",
    "futs_prdy_clpr": "361.40",
    "futs_shrn_iscd": "101S06"
  },
  "output2": {
    "futs_askp1": "364.40",
    "futs_askp2": "364.45",
    "futs_askp3": "364.50",
    "futs_askp4": "364.55",
    "futs_askp5": "364.60",
    "futs_bidp1": "364.35",
    "futs_bidp2": "364.30",
    "futs_bidp3": "364.25",
    "futs_bidp4": "364.20",
    "futs_bidp5": "364.15",
    "askp_rsqn1": "35",
    "askp_rsqn2": "47",
    "askp_rsqn3": "32",
    "askp_rsqn4": "56",
    "askp_rsqn5": "88",
    "bidp_rsqn1": "22",
    "bidp_rsqn2": "70",
    "bidp_rsqn3": "68",
    "bidp_rsqn4": "97",
    "bidp_rsqn5": "42",
    "askp_csnu1": "9",
    "askp_csnu2": "19",
    "askp_csnu3": "21",
    "askp_csnu4": "28",
    "askp_csnu5": "20",
    "bidp_csnu1": "9",
    "bidp_csnu2": "45",
    "bidp_csnu3": "26",
    "bidp_csnu4": "31",
    "bidp_csnu5": "22",
    "total_askp_rsqn": "7140",
    "total_bidp_rsqn": "9319",
    "total_askp_csnu": "1091",
    "total_bidp_csnu": "1115",
    "aspr_acpt_hour": "153744"
  },
  "rt_cd": "0",
  "msg_cd": "MCA00000",
  "msg1": "정상처리 되었습니다."
}
```

---

## 국내옵션전광판_콜풋

### 기본 정보

| 항목 | 값 |
| --- | --- |
| API 통신방식 | REST |
| 메뉴 위치 | [국내선물옵션] 기본시세 |
| API 명 | 국내옵션전광판_콜풋 |
| API ID | 국내선물-022 |
| 실전 TR_ID | FHPIF05030100 |
| 모의 TR_ID | 모의투자 미지원 |
| HTTP Method | GET |
| URL 명 | /uapi/domestic-futureoption/v1/quotations/display-board-callput |
| 실전 Domain | https://openapi.koreainvestment.com:9443 |
| 모의 Domain | 모의투자 미지원 |
| 순번 | 213 |

### 개요

국내옵션전광판_콜풋 API입니다.
한국투자 HTS(eFriend Plus) &gt; [0503] 선물옵션 종합시세(Ⅰ) 화면의 "중앙" 기능을 API로 개발한 사항으로, 해당 화면을 참고하시면 기능을 이해하기 쉽습니다.

※ output1, output2 각각 100건까지만 확인이 가능합니다. (FY25년도 서비스 개선 예정)
※ 조회시간이 긴 API인 점 참고 부탁드리며, 잦은 호출을 삼가해주시기 바랍니다. (1초당 최대 1건 권장)

### Layout

**Request Header**

| Element | 한글명 | Type | Required | Length | Description |
| --- | --- | --- | --- | --- | --- |
| content-type | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| authorization | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token <br>일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) <br>법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| appkey | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| appsecret | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| personalseckey | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| tr_id | 거래ID | string | Y | 13 | FHPIF05030100 |
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
| FID_COND_MRKT_DIV_CODE | 조건 시장 분류 코드 | string | Y | 2 | 시장구분코드 (O: 옵션) |
| FID_COND_SCR_DIV_CODE | 조건 화면 분류 코드 | string | Y | 5 | Unique key(20503) |
| FID_MRKT_CLS_CODE | 시장 구분 코드 | string | Y | 2 | 시장구분코드 (CO: 콜옵션) |
| FID_MTRT_CNT | 만기 수 | string | Y | 11 | - FID_COND_MRKT_CLS_CODE : 공백(KOSPI200), MKI(미니KOSPI200), KQI(KOSDAQ150) 인 경우<br>: 만기년월(YYYYMM) 입력 (ex. 202407)<br><br>- FID_COND_MRKT_CLS_CODE : WKM(KOSPI200위클리(월)), WKI(KOSPI200위클리(목)) 인 경우<br>: 만기년월주차(YYMMWW) 입력<br>(ex. 2024년도 7월 3주차인 경우, 240703 입력) |
| FID_COND_MRKT_CLS_CODE | 조건 시장 구분 코드 | string | Y | 6 | 공백: KOSPI200<br>MKI: 미니KOSPI200<br>WKM: KOSPI200위클리(월)<br>WKI: KOSPI200위클리(목)<br>KQI: KOSDAQ150 |
| FID_MRKT_CLS_CODE1 | 시장 구분 코드 | string | Y | 2 | 시장구분코드 (PO: 풋옵션) |

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
| acpr | 행사가 | string | Y | 112 |  |
| unch_prpr | 환산 현재가 | string | Y | 112 |  |
| optn_shrn_iscd | 옵션 단축 종목코드 | string | Y | 9 |  |
| optn_prpr | 옵션 현재가 | string | Y | 112 |  |
| optn_prdy_vrss | 옵션 전일 대비 | string | Y | 112 |  |
| prdy_vrss_sign | 전일 대비 부호 | string | Y | 1 |  |
| optn_prdy_ctrt | 옵션 전일 대비율 | string | Y | 82 |  |
| optn_bidp | 옵션 매수호가 | string | Y | 112 |  |
| optn_askp | 옵션 매도호가 | string | Y | 112 |  |
| tmvl_val | 시간가치 값 | string | Y | 132 |  |
| nmix_sdpr | 지수 기준가 | string | Y | 112 |  |
| acml_vol | 누적 거래량 | string | Y | 18 |  |
| seln_rsqn | 매도 잔량 | string | Y | 12 |  |
| shnu_rsqn | 매수2 잔량 | string | Y | 12 |  |
| acml_tr_pbmn | 누적 거래 대금 | string | Y | 18 |  |
| hts_otst_stpl_qty | HTS 미결제 약정 수량 | string | Y | 18 |  |
| otst_stpl_qty_icdc | 미결제 약정 수량 증감 | string | Y | 10 |  |
| delta_val | 델타 값 | string | Y | 114 |  |
| gama | 감마 | string | Y | 84 |  |
| vega | 베가 | string | Y | 84 |  |
| theta | 세타 | string | Y | 84 |  |
| rho | 로우 | string | Y | 84 |  |
| hts_ints_vltl | HTS 내재 변동성 | string | Y | 114 |  |
| invl_val | 내재가치 값 | string | Y | 132 |  |
| esdg | 괴리도 | string | Y | 114 |  |
| dprt | 괴리율 | string | Y | 82 |  |
| hist_vltl | 역사적 변동성 | string | Y | 114 |  |
| hts_thpr | HTS 이론가 | string | Y | 112 |  |
| optn_oprc | 옵션 시가2 | string | Y | 112 |  |
| optn_hgpr | 옵션 최고가 | string | Y | 112 |  |
| optn_lwpr | 옵션 최저가 | string | Y | 112 |  |
| optn_mxpr | 옵션 상한가 | string | Y | 112 |  |
| optn_llam | 옵션 하한가 | string | Y | 112 |  |
| atm_cls_name | ATM 구분 명 | string | Y | 10 |  |
| rgbf_vrss_icdc | 직전 대비 증감 | string | Y | 10 |  |
| total_askp_rsqn | 총 매도호가 잔량 | string | Y | 12 |  |
| total_bidp_rsqn | 총 매수호가 잔량 | string | Y | 12 |  |
| futs_antc_cnpr | 선물예상체결가 | string | Y | 112 |  |
| futs_antc_cntg_vrss | 선물예상체결대비 | string | Y | 112 |  |
| antc_cntg_vrss_sign | 예상 체결 대비 부호 | string | Y | 1 |  |
| antc_cntg_prdy_ctrt | 예상 체결 전일 대비율 | string | Y | 82 |  |
| output2 | 응답상세 | object array | Y |  | array |
| acpr | 행사가 | string | Y | 112 |  |
| unch_prpr | 환산 현재가 | string | Y | 112 |  |
| optn_shrn_iscd | 옵션 단축 종목코드 | string | Y | 9 |  |
| optn_prpr | 옵션 현재가 | string | Y | 112 |  |
| optn_prdy_vrss | 옵션 전일 대비 | string | Y | 112 |  |
| prdy_vrss_sign | 전일 대비 부호 | string | Y | 1 |  |
| optn_prdy_ctrt | 옵션 전일 대비율 | string | Y | 82 |  |
| optn_bidp | 옵션 매수호가 | string | Y | 112 |  |
| optn_askp | 옵션 매도호가 | string | Y | 112 |  |
| tmvl_val | 시간가치 값 | string | Y | 132 |  |
| nmix_sdpr | 지수 기준가 | string | Y | 112 |  |
| acml_vol | 누적 거래량 | string | Y | 18 |  |
| seln_rsqn | 매도 잔량 | string | Y | 12 |  |
| shnu_rsqn | 매수2 잔량 | string | Y | 12 |  |
| acml_tr_pbmn | 누적 거래 대금 | string | Y | 18 |  |
| hts_otst_stpl_qty | HTS 미결제 약정 수량 | string | Y | 18 |  |
| otst_stpl_qty_icdc | 미결제 약정 수량 증감 | string | Y | 10 |  |
| delta_val | 델타 값 | string | Y | 114 |  |
| gama | 감마 | string | Y | 84 |  |
| vega | 베가 | string | Y | 84 |  |
| theta | 세타 | string | Y | 84 |  |
| rho | 로우 | string | Y | 84 |  |
| hts_ints_vltl | HTS 내재 변동성 | string | Y | 114 |  |
| invl_val | 내재가치 값 | string | Y | 132 |  |
| esdg | 괴리도 | string | Y | 114 |  |
| dprt | 괴리율 | string | Y | 82 |  |
| hist_vltl | 역사적 변동성 | string | Y | 114 |  |
| hts_thpr | HTS 이론가 | string | Y | 112 |  |
| optn_oprc | 옵션 시가2 | string | Y | 112 |  |
| optn_hgpr | 옵션 최고가 | string | Y | 112 |  |
| optn_lwpr | 옵션 최저가 | string | Y | 112 |  |
| optn_mxpr | 옵션 상한가 | string | Y | 112 |  |
| optn_llam | 옵션 하한가 | string | Y | 112 |  |
| atm_cls_name | ATM 구분 명 | string | Y | 10 |  |
| rgbf_vrss_icdc | 직전 대비 증감 | string | Y | 10 |  |
| total_askp_rsqn | 총 매도호가 잔량 | string | Y | 12 |  |
| total_bidp_rsqn | 총 매수호가 잔량 | string | Y | 12 |  |
| futs_antc_cnpr | 선물예상체결가 | string | Y | 112 |  |
| futs_antc_cntg_vrss | 선물예상체결대비 | string | Y | 112 |  |
| antc_cntg_vrss_sign | 예상 체결 대비 부호 | string | Y | 1 |  |
| antc_cntg_prdy_ctrt | 예상 체결 전일 대비율 | string | Y | 82 |  |

### Example

**Request Example (Python)**

```
fid_cond_mrkt_div_code:O
fid_cond_scr_div_code:20503
fid_mrkt_cls_code:CO
fid_mtrt_cnt:202405
fid_cond_mrkt_cls_code:
fid_mrkt_cls_code1:PO
```

**Response Example**

```
{
    "output1": [
        {
            "acpr": "480.00",
            "unch_prpr": "3505.17",
            "optn_shrn_iscd": "201V05480",
            "optn_prpr": "0.01",
            "optn_prdy_vrss": "0.00",
            "prdy_vrss_sign": "3",
            "optn_prdy_ctrt": "0.00",
            "optn_bidp": "0.00",
            "optn_askp": "0.01",
            "tmvl_val": "0.01",
            "nmix_sdpr": "0.01",
            "acml_vol": "34",
            "seln_rsqn": "1710",
            "shnu_rsqn": "0",
            "acml_tr_pbmn": "85",
            "hts_otst_stpl_qty": "642",
            "otst_stpl_qty_icdc": "39",
            "delta_val": "0.0000",
            "gama": "0.0000",
            "vega": "0.0000",
            "theta": "-0.0000",
            "rho": "0.0000",
            "hts_ints_vltl": "31.5614",
            "invl_val": "0.00",
            "esdg": "0.01",
            "dprt": "9999.99",
            "hist_vltl": "16.9285",
            "hts_thpr": "0.00",
            "optn_oprc": "0.01",
            "optn_hgpr": "0.01",
            "optn_lwpr": "0.01",
            "optn_mxpr": "5.20",
            "optn_llam": "0.01",
            "atm_cls_name": "OTM",
            "rgbf_vrss_icdc": "1",
            "total_askp_rsqn": "1710",
            "total_bidp_rsqn": "0",
            "futs_antc_cnpr": "0.00",
            "futs_antc_cntg_vrss": "0.00",
            "antc_cntg_vrss_sign": "0",
            "antc_cntg_prdy_ctrt": "0.00"
        },
		...
    ],
    "output2": [
        {
            "acpr": "480.00",
            "unch_prpr": "3505.17",
            "optn_shrn_iscd": "301V05480",
            "optn_prpr": "108.45",
            "optn_prdy_vrss": "0.00",
            "prdy_vrss_sign": "3",
            "optn_prdy_ctrt": "0.00",
            "optn_bidp": "78.35",
            "optn_askp": "142.60",
            "tmvl_val": "-4.30",
            "nmix_sdpr": "108.45",
            "acml_vol": "0",
            "seln_rsqn": "10",
            "shnu_rsqn": "10",
            "acml_tr_pbmn": "0",
            "hts_otst_stpl_qty": "48",
            "otst_stpl_qty_icdc": "0",
            "delta_val": "-1.0000",
            "gama": "0.0000",
            "vega": "0.0000",
            "theta": "0.0460",
            "rho": "-0.3541",
            "hts_ints_vltl": "0.0000",
            "invl_val": "112.75",
            "esdg": "-3.06",
            "dprt": "-2.74",
            "hist_vltl": "16.9285",
            "hts_thpr": "111.51",
            "optn_oprc": "0.00",
            "optn_hgpr": "0.00",
            "optn_lwpr": "0.00",
            "optn_mxpr": "142.60",
            "optn_llam": "78.35",
            "atm_cls_name": "ITM",
            "rgbf_vrss_icdc": "0",
            "total_askp_rsqn": "10",
            "total_bidp_rsqn": "10",
            "futs_antc_cnpr": "0.00",
            "futs_antc_cntg_vrss": "0.00",
            "antc_cntg_vrss_sign": "0",
            "antc_cntg_prdy_ctrt": "0.00"
        },...
    ],
    "rt_cd": "0",
    "msg_cd": "MCA00000",
    "msg1": "정상처리 되었습니다."
}
```

---
