# KIS OpenAPI 전체 레퍼런스

> 출처: 한국투자증권_오픈API_전체문서_20260418 (338개 API)

## 요약

- **REST API**: 278개
- **WebSocket API**: 60개
- **총**: 338개 API

## 목차

1. [OAuth인증](#oauth인증) (4개)
2. [[국내주식] 주문/계좌](#국내주식-주문계좌) (23개)
3. [[국내주식] 기본시세](#국내주식-기본시세) (21개)
4. [[국내주식] ELW 시세](#국내주식-elw-시세) (22개)
5. [[국내주식] 업종/기타](#국내주식-업종기타) (14개)
6. [[국내주식] 종목정보](#국내주식-종목정보) (26개)
7. [[국내주식] 시세분석](#국내주식-시세분석) (29개)
8. [[국내주식] 순위분석](#국내주식-순위분석) (22개)
9. [[국내주식] 실시간시세](#국내주식-실시간시세) (29개)
10. [[국내선물옵션] 주문/계좌](#국내선물옵션-주문계좌) (15개)
11. [[국내선물옵션] 기본시세](#국내선물옵션-기본시세) (9개)
12. [[국내선물옵션] 실시간시세](#국내선물옵션-실시간시세) (20개)
13. [[해외주식] 주문/계좌](#해외주식-주문계좌) (18개)
14. [[해외주식] 기본시세](#해외주식-기본시세) (14개)
15. [[해외주식] 시세분석](#해외주식-시세분석) (15개)
16. [[해외주식] 실시간시세](#해외주식-실시간시세) (4개)
17. [[해외선물옵션] 주문/계좌](#해외선물옵션-주문계좌) (11개)
18. [[해외선물옵션] 기본시세](#해외선물옵션-기본시세) (20개)
19. [[해외선물옵션]실시간시세](#해외선물옵션실시간시세) (4개)
20. [[장내채권] 주문/계좌](#장내채권-주문계좌) (7개)
21. [[장내채권] 기본시세](#장내채권-기본시세) (8개)
22. [[장내채권] 실시간시세](#장내채권-실시간시세) (3개)

---

## OAuth인증

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 1 | REST | Hashkey | Hashkey | - | - | POST | `/uapi/hashkey` |
| 2 | WEBSOCKET | 실시간 (웹소켓) 접속키 발급 | 실시간-000 | - | - | POST | `/oauth2/Approval` |
| 3 | REST | 접근토큰폐기(P) | 인증-002 | - | - | POST | `/oauth2/revokeP` |
| 4 | REST | 접근토큰발급(P) | 인증-001 | - | - | POST | `/oauth2/tokenP` |

## [국내주식] 주문/계좌

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 5 | REST | 기간별계좌권리현황조회 | 국내주식-211 | CTRGA011R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/period-rights` |
| 6 | REST | 투자계좌자산현황조회 | v1_국내주식-048 | CTRP6548R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/inquire-account-balance` |
| 7 | REST | 퇴직연금 예수금조회 | v1_국내주식-035 | TTTC0506R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/pension/inquire-deposit` |
| 8 | REST | 주식예약주문정정취소 | v1_국내주식-018,019 | (예약취소) CTSC0009U (예약정정) CTSC0013U | 모의투자 미지원 | POST | `/uapi/domestic-stock/v1/trading/order-resv-rvsecncl` |
| 9 | REST | 신용매수가능조회 | v1_국내주식-042 | TTTC8909R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/inquire-credit-psamount` |
| 10 | REST | 주식통합증거금 현황 | 국내주식-191 | TTTC0869R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/intgr-margin` |
| 11 | REST | 퇴직연금 미체결내역 | v1_국내주식-033 | TTTC2201R(기존 KRX만 가능), TTTC2210R (KRX,NXT/SOR) | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/pension/inquire-daily-ccld` |
| 12 | REST | 기간별매매손익현황조회 | v1_국내주식-060 | TTTC8715R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/inquire-period-trade-profit` |
| 13 | REST | 주식주문(정정취소) | v1_국내주식-003 | TTTC0013U | VTTC0013U | POST | `/uapi/domestic-stock/v1/trading/order-rvsecncl` |
| 14 | REST | 주식예약주문조회 | v1_국내주식-020 | CTSC0004R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/order-resv-ccnl` |
| 15 | REST | 퇴직연금 매수가능조회 | v1_국내주식-034 | TTTC0503R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/pension/inquire-psbl-order` |
| 16 | REST | 주식잔고조회 | v1_국내주식-006 | TTTC8434R | VTTC8434R | GET | `/uapi/domestic-stock/v1/trading/inquire-balance` |
| 17 | REST | 퇴직연금 체결기준잔고 | v1_국내주식-032 | TTTC2202R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/pension/inquire-present-balance` |
| 18 | REST | 매수가능조회 | v1_국내주식-007 | TTTC8908R | VTTC8908R | GET | `/uapi/domestic-stock/v1/trading/inquire-psbl-order` |
| 19 | REST | 기간별손익일별합산조회 | v1_국내주식-052 | TTTC8708R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/inquire-period-profit` |
| 20 | REST | 주식주문(현금) | v1_국내주식-001 | (매도) TTTC0011U (매수) TTTC0012U | (매도) VTTC0011U (매수) VTTC0012U | POST | `/uapi/domestic-stock/v1/trading/order-cash` |
| 21 | REST | 매도가능수량조회 | 국내주식-165 | TTTC8408R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/inquire-psbl-sell` |
| 22 | REST | 주식일별주문체결조회 | v1_국내주식-005 | (3개월이내) TTTC0081R (3개월이전) CTSC9215R | (3개월이내) VTTC0081R (3개월이전) VTSC9215R | GET | `/uapi/domestic-stock/v1/trading/inquire-daily-ccld` |
| 23 | REST | 주식정정취소가능주문조회 | v1_국내주식-004 | TTTC0084R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl` |
| 24 | REST | 주식예약주문 | v1_국내주식-017 | CTSC0008U | 모의투자 미지원 | POST | `/uapi/domestic-stock/v1/trading/order-resv` |
| 25 | REST | 주식주문(신용) | v1_국내주식-002 | (매도) TTTC0051U (매수) TTTC0052U | 모의투자 미지원 | POST | `/uapi/domestic-stock/v1/trading/order-credit` |
| 26 | REST | 퇴직연금 잔고조회 | v1_국내주식-036 | TTTC2208R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/pension/inquire-balance` |
| 27 | REST | 주식잔고조회_실현손익 | v1_국내주식-041 | TTTC8494R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/trading/inquire-balance-rlz-pl` |

## [국내주식] 기본시세

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 28 | REST | 주식현재가 일자별 | v1_국내주식-010 | FHKST01010400 | FHKST01010400 | GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-price` |
| 29 | REST | 주식현재가 시세 | v1_국내주식-008 | FHKST01010100 | FHKST01010100 | GET | `/uapi/domestic-stock/v1/quotations/inquire-price` |
| 30 | REST | 국내주식 시간외현재가 | 국내주식-076 | FHPST02300000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-overtime-price` |
| 31 | REST | ETF 구성종목시세 | 국내주식-073 | FHKST121600C0 | 모의투자 미지원 | GET | `/uapi/etfetn/v1/quotations/inquire-component-stock-price` |
| 32 | REST | 주식현재가 시간외시간별체결 | v1_국내주식-025 | FHPST02310000 | FHPST02310000 | GET | `/uapi/domestic-stock/v1/quotations/inquire-time-overtimeconclusion` |
| 33 | REST | NAV 비교추이(종목) | v1_국내주식-069 | FHPST02440000 | 모의투자 미지원 | GET | `/uapi/etfetn/v1/quotations/nav-comparison-trend` |
| 34 | REST | 주식현재가 시간외일자별주가 | v1_국내주식-026 | FHPST02320000 | FHPST02320000 | GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-overtimeprice` |
| 35 | REST | 국내주식 시간외호가 | 국내주식-077 | FHPST02300400 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-overtime-asking-price` |
| 36 | REST | 주식현재가 당일시간대별체결 | v1_국내주식-023 | FHPST01060000 | FHPST01060000 | GET | `/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion` |
| 37 | REST | 주식현재가 시세2 | v1_국내주식-054 | FHPST01010000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-price-2` |
| 38 | REST | 주식일별분봉조회 | 국내주식-213 | FHKST03010230 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice` |
| 39 | REST | 국내주식기간별시세(일/주/월/년) | v1_국내주식-016 | FHKST03010100 | FHKST03010100 | GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice` |
| 40 | REST | NAV 비교추이(일) | v1_국내주식-071 | FHPST02440200 | 모의투자 미지원 | GET | `/uapi/etfetn/v1/quotations/nav-comparison-daily-trend` |
| 41 | REST | 주식현재가 호가/예상체결 | v1_국내주식-011 | FHKST01010200 | FHKST01010200 | GET | `/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn` |
| 42 | REST | 주식현재가 체결 | v1_국내주식-009 | FHKST01010300 | FHKST01010300 | GET | `/uapi/domestic-stock/v1/quotations/inquire-ccnl` |
| 43 | REST | 주식현재가 회원사 | v1_국내주식-013 | FHKST01010600 | FHKST01010600 | GET | `/uapi/domestic-stock/v1/quotations/inquire-member` |
| 44 | REST | NAV 비교추이(분) | v1_국내주식-070 | FHPST02440100 | 모의투자 미지원 | GET | `/uapi/etfetn/v1/quotations/nav-comparison-time-trend` |
| 45 | REST | 주식현재가 투자자 | v1_국내주식-012 | FHKST01010900 | FHKST01010900 | GET | `/uapi/domestic-stock/v1/quotations/inquire-investor` |
| 46 | REST | ETF/ETN 현재가 | v1_국내주식-068 | FHPST02400000 | 모의투자 미지원 | GET | `/uapi/etfetn/v1/quotations/inquire-price` |
| 47 | REST | 국내주식 장마감 예상체결가 | 국내주식-120 | FHKST117300C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/exp-closing-price` |
| 48 | REST | 주식당일분봉조회 | v1_국내주식-022 | FHKST03010200 | FHKST03010200 | GET | `/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice` |

## [국내주식] ELW 시세

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 49 | REST | ELW 현재가 시세 | v1_국내주식-014 | FHKEW15010000 | FHKEW15010000 | GET | `/uapi/domestic-stock/v1/quotations/inquire-elw-price` |
| 50 | REST | ELW 신규상장종목 | 국내주식-181 | FHKEW154800C0 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/newly-listed` |
| 51 | REST | ELW 투자지표추이(일별) | 국내주식-173 | FHPEW02740200 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/indicator-trend-daily` |
| 52 | REST | ELW 민감도 순위 | 국내주식-170 | FHPEW02850000 | 모의투자 미지원 | GET | `/uapi/elw/v1/ranking/sensitivity` |
| 53 | REST | ELW 기초자산별 종목시세 | 국내주식-186 | FHKEW154101C0 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/udrl-asset-price` |
| 54 | REST | ELW 종목검색 | 국내주식-166 | FHKEW15100000 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/cond-search` |
| 55 | REST | ELW 변동성 추이(분별) | 국내주식-179 | FHPEW02840300 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/volatility-trend-minute` |
| 56 | REST | ELW 변동성추이(체결) | 국내주식-177 | FHPEW02840100 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/volatility-trend-ccnl` |
| 57 | REST | ELW 당일급변종목 | 국내주식-171 | FHPEW02870000 | 모의투자 미지원 | GET | `/uapi/elw/v1/ranking/quick-change` |
| 58 | REST | ELW 투자지표추이(분별) | 국내주식-174 | FHPEW02740300 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/indicator-trend-minute` |
| 59 | REST | ELW 기초자산 목록조회 | 국내주식-185 | FHKEW154100C0 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/udrl-asset-list` |
| 60 | REST | ELW 변동성 추이(일별) | 국내주식-178 | FHPEW02840200 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/volatility-trend-daily` |
| 61 | REST | ELW 거래량순위 | 국내주식-168 | FHPEW02780000 | 모의투자 미지원 | GET | `/uapi/elw/v1/ranking/volume-rank` |
| 62 | REST | ELW 지표순위 | 국내주식-169 | FHPEW02790000 | 모의투자 미지원 | GET | `/uapi/elw/v1/ranking/indicator` |
| 63 | REST | ELW 투자지표추이(체결) | 국내주식-172 | FHPEW02740100 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/indicator-trend-ccnl` |
| 64 | REST | ELW 상승률순위 | 국내주식-167 | FHPEW02770000 | 모의투자 미지원 | GET | `/uapi/elw/v1/ranking/updown-rate` |
| 65 | REST | ELW 민감도 추이(일별) | 국내주식-176 | FHPEW02830200 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/sensitivity-trend-daily` |
| 66 | REST | ELW 비교대상종목조회 | 국내주식-183 | FHKEW151701C0 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/compare-stocks` |
| 67 | REST | ELW 만기예정/만기종목 | 국내주식-184 | FHKEW154700C0 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/expiration-stocks` |
| 68 | REST | ELW LP매매추이 | 국내주식-182 | FHPEW03760000 | - | GET | `/uapi/elw/v1/quotations/lp-trade-trend` |
| 69 | REST | ELW 민감도 추이(체결) | 국내주식-175 | FHPEW02830100 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/sensitivity-trend-ccnl` |
| 70 | REST | ELW 변동성 추이(틱) | 국내주식-180 | FHPEW02840400 | 모의투자 미지원 | GET | `/uapi/elw/v1/quotations/volatility-trend-tick` |

## [국내주식] 업종/기타

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 71 | REST | 국내주식 예상체결지수 추이 | 국내주식-121 | FHPST01840000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/exp-index-trend` |
| 72 | REST | 국내주식업종기간별시세(일/주/월/년) | v1_국내주식-021 | FHKUP03500100 | FHKUP03500100 | GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice` |
| 73 | REST | 국내업종 시간별지수(분) | 국내주식-119 | FHPUP02110200 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-index-timeprice` |
| 74 | REST | 국내업종 구분별전체시세 | v1_국내주식-066 | FHPUP02140000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-index-category-price` |
| 75 | REST | 업종 분봉조회 | v1_국내주식-045 | FHKUP03500200 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-time-indexchartprice` |
| 76 | REST | 국내휴장일조회 | 국내주식-040 | CTCA0903R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/chk-holiday` |
| 77 | REST | 국내주식 예상체결 전체지수 | 국내주식-122 | FHKUP11750000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/exp-total-index` |
| 78 | REST | 국내업종 현재지수 | v1_국내주식-063 | FHPUP02100000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-index-price` |
| 79 | REST | 국내선물 영업일조회 | 국내주식-160 | HHMCM000002C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/market-time` |
| 80 | REST | 국내업종 시간별지수(초) | 국내주식-064 | FHPUP02110100 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-index-tickprice` |
| 81 | REST | 국내업종 일자별지수 | v1_국내주식-065 | FHPUP02120000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-index-daily-price` |
| 82 | REST | 금리 종합(국내채권/금리) | 국내주식-155 | FHPST07020000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/comp-interest` |
| 83 | REST | 변동성완화장치(VI) 현황 | v1_국내주식-055 | FHPST01390000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-vi-status` |
| 84 | REST | 종합 시황/공시(제목) | 국내주식-141 | FHKST01011800 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/news-title` |

## [국내주식] 종목정보

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 85 | REST | 상품기본조회 | v1_국내주식-029 | CTPF1604R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/search-info` |
| 86 | REST | 예탁원정보(상장정보일정) | 국내주식-150 | HHKDB669107C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/list-info` |
| 87 | REST | 예탁원정보(공모주청약일정) | 국내주식-151 | HHKDB669108C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/pub-offer` |
| 88 | REST | 국내주식 재무비율 | v1_국내주식-080 | FHKST66430300 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/finance/financial-ratio` |
| 89 | REST | 예탁원정보(자본감소일정) | 국내주식-149 | HHKDB669106C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/cap-dcrs` |
| 90 | REST | 예탁원정보(무상증자일정) | 국내주식-144 | HHKDB669101C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/bonus-issue` |
| 91 | REST | 국내주식 증권사별 투자의견 | 국내주식-189 | FHKST663400C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/invest-opbysec` |
| 92 | REST | 국내주식 당사 신용가능종목 | 국내주식-111 | FHPST04770000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/credit-by-company` |
| 93 | REST | 예탁원정보(주식매수청구일정) | 국내주식-146 | HHKDB669103C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/purreq` |
| 94 | REST | 예탁원정보(액면교체일정) | 국내주식-148 | HHKDB669105C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/rev-split` |
| 95 | REST | 예탁원정보(배당일정) | 국내주식-145 | HHKDB669102C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/dividend` |
| 96 | REST | 국내주식 종목투자의견 | 국내주식-188 | FHKST663300C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/invest-opinion` |
| 97 | REST | 국내주식 안정성비율 | v1_국내주식-083 | FHKST66430600 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/finance/stability-ratio` |
| 98 | REST | 국내주식 수익성비율 | v1_국내주식-081 | FHKST66430400 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/finance/profit-ratio` |
| 99 | REST | 예탁원정보(실권주일정) | 국내주식-152 | HHKDB669109C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/forfeit` |
| 100 | REST | 예탁원정보(의무예치일정) | 국내주식-153 | HHKDB669110C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/mand-deposit` |
| 101 | REST | 국내주식 손익계산서 | v1_국내주식-079 | FHKST66430200 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/finance/income-statement` |
| 102 | REST | 당사 대주가능 종목 | 국내주식-195 | CTSC2702R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/lendable-by-company` |
| 103 | REST | 주식기본조회 | v1_국내주식-067 | CTPF1002R | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/search-stock-info` |
| 104 | REST | 예탁원정보(유상증자일정) | 국내주식-143 | HHKDB669100C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/paidin-capin` |
| 105 | REST | 예탁원정보(주주총회일정) | 국내주식-154 | HHKDB669111C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/sharehld-meet` |
| 106 | REST | 국내주식 성장성비율 | v1_국내주식-085 | FHKST66430800 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/finance/growth-ratio` |
| 107 | REST | 국내주식 대차대조표 | v1_국내주식-078 | FHKST66430100 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/finance/balance-sheet` |
| 108 | REST | 예탁원정보(합병/분할일정) | 국내주식-147 | HHKDB669104C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ksdinfo/merger-split` |
| 109 | REST | 국내주식 종목추정실적 | 국내주식-187 | HHKST668300C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/estimate-perform` |
| 110 | REST | 국내주식 기타주요비율 | v1_국내주식-082 | FHKST66430500 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/finance/other-major-ratios` |

## [국내주식] 시세분석

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 111 | REST | 프로그램매매 종합현황(시간) | 국내주식-114 | FHPPG04600101 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/comp-program-trade-today` |
| 112 | REST | 국내주식 신용잔고 일별추이 | 국내주식-110 | FHPST04760000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/daily-credit-balance` |
| 113 | REST | 시장별 투자자매매동향(일별) | 국내주식-075 | FHPTJ04040000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market` |
| 114 | REST | 국내주식 공매도 일별추이 | 국내주식-134 | FHPST04830000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/daily-short-sale` |
| 115 | REST | 종목별 투자자매매동향(일별) | 종목별 투자자매매동향(일별) | FHPTJ04160001 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily` |
| 116 | REST | 종목조건검색 목록조회 | 국내주식-038 | HHKST03900300 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/psearch-title` |
| 117 | REST | 국내주식 상하한가 포착 | 국내주식-190 | FHKST130000C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/capture-uplowprice` |
| 118 | REST | 프로그램매매 종합현황(일별) | 국내주식-115 | FHPPG04600001 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/comp-program-trade-daily` |
| 119 | REST | 종목별 일별 대차거래추이 | 국내주식-135 | HHPST074500C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/daily-loan-trans` |
| 120 | REST | 종목조건검색조회 | 국내주식-039 | HHKST03900400 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/psearch-result` |
| 121 | REST | 국내주식 매물대/거래비중 | 국내주식-196 | FHPST01130000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/pbar-tratio` |
| 122 | REST | 국내기관_외국인 매매종목가집계 | 국내주식-037 | FHPTJ04400000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/foreign-institution-total` |
| 123 | REST | 관심종목 그룹별 종목조회 | 국내주식-203 | HHKCM113004C6 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/intstock-stocklist-by-group` |
| 124 | REST | 주식현재가 회원사 종목매매동향 | 국내주식-197 | FHPST04540000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-member-daily` |
| 125 | REST | 종목별 프로그램매매추이(일별) | 국내주식-113 | FHPPG04650201 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/program-trade-by-stock-daily` |
| 126 | REST | 관심종목 그룹조회 | 국내주식-204 | HHKCM113004C7 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/intstock-grouplist` |
| 127 | REST | 종목별 외인기관 추정가집계 | v1_국내주식-046 | HHPTJ04160200 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/investor-trend-estimate` |
| 128 | REST | 종목별일별매수매도체결량 | v1_국내주식-056 | FHKST03010800 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-trade-volume` |
| 129 | REST | 국내주식 체결금액별 매매비중 | 국내주식-192 | FHKST111900C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/tradprt-byamt` |
| 130 | REST | 프로그램매매 투자자매매동향(당일) | 국내주식-116 | HHPPG046600C1 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/investor-program-trade-today` |
| 131 | REST | 국내 증시자금 종합 | 국내주식-193 | FHKST649100C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/mktfunds` |
| 132 | REST | 국내주식 예상체결가 추이 | 국내주식-118 | FHPST01810000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/exp-price-trend` |
| 133 | WEBSOCKET | 회원사 실시간 매매동향(틱) | 국내주식-163 | FHPST04320000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/frgnmem-trade-trend` |
| 134 | REST | 시장별 투자자매매동향(시세) | v1_국내주식-074 | FHPTJ04030000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/inquire-investor-time-by-market` |
| 135 | REST | 종목별 프로그램매매추이(체결) | v1_국내주식-044 | FHPPG04650101 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/program-trade-by-stock` |
| 136 | REST | 외국계 매매종목 가집계 | 국내주식-161 | FHKST644100C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/frgnmem-trade-estimate` |
| 137 | REST | 국내주식 시간외예상체결등락률 | 국내주식-140 | FHKST11860000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/overtime-exp-trans-fluct` |
| 138 | REST | 종목별 외국계 순매수추이 | 국내주식-164 | FHKST644400C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/frgnmem-pchs-trend` |
| 139 | REST | 관심종목(멀티종목) 시세조회 | 국내주식-205 | FHKST11300006 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/intstock-multprice` |

## [국내주식] 순위분석

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 140 | REST | 국내주식 예상체결 상승/하락상위 | v1_국내주식-103 | FHPST01820000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/exp-trans-updown` |
| 141 | REST | 국내주식 호가잔량 순위 | 국내주식-089 | FHPST01720000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/quote-balance` |
| 142 | REST | 국내주식 신용잔고 상위 | 국내주식-109 | FHKST17010000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/credit-balance` |
| 143 | REST | 국내주식 시간외거래량순위 | 국내주식-139 | FHPST02350000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/overtime-volume` |
| 144 | REST | 국내주식 배당률 상위 | 국내주식-106 | HHKDB13470100 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/dividend-rate` |
| 145 | REST | 국내주식 시간외잔량 순위 | v1_국내주식-093 | FHPST01760000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/after-hour-balance` |
| 146 | REST | 국내주식 공매도 상위종목 | 국내주식-133 | FHPST04820000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/short-sale` |
| 147 | REST | 국내주식 이격도 순위 | v1_국내주식-095 | FHPST01780000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/disparity` |
| 148 | REST | HTS조회상위20종목 | 국내주식-214 | HHMCM000100C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/hts-top-view` |
| 149 | REST | 거래량순위 | v1_국내주식-047 | FHPST01710000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/quotations/volume-rank` |
| 150 | REST | 국내주식 수익자산지표 순위 | v1_국내주식-090 | FHPST01730000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/profit-asset-index` |
| 151 | REST | 국내주식 신고/신저근접종목 상위 | v1_국내주식-105 | FHPST01870000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/near-new-highlow` |
| 152 | REST | 국내주식 우선주/괴리율 상위 | v1_국내주식-094 | FHPST01770000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/prefer-disparate-ratio` |
| 153 | REST | 국내주식 대량체결건수 상위 | 국내주식-107 | FHKST190900C0 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/bulk-trans-num` |
| 154 | REST | 국내주식 재무비율 순위 | v1_국내주식-092 | FHPST01750000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/finance-ratio` |
| 155 | REST | 국내주식 시가총액 상위 | v1_국내주식-091 | FHPST01740000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/market-cap` |
| 156 | REST | 국내주식 당사매매종목 상위 | v1_국내주식-104 | FHPST01860000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/traded-by-company` |
| 157 | REST | 국내주식 등락률 순위 | v1_국내주식-088 | FHPST01700000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/fluctuation` |
| 158 | REST | 국내주식 시장가치 순위 | v1_국내주식-096 | FHPST01790000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/market-value` |
| 159 | REST | 국내주식 관심종목등록 상위 | v1_국내주식-102 | FHPST01800000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/top-interest-stock` |
| 160 | REST | 국내주식 체결강도 상위 | v1_국내주식-101 | FHPST01680000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/volume-power` |
| 161 | REST | 국내주식 시간외등락율순위 | 국내주식-138 | FHPST02340000 | 모의투자 미지원 | GET | `/uapi/domestic-stock/v1/ranking/overtime-fluctuation` |

## [국내주식] 실시간시세

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 162 | WEBSOCKET | 국내지수 실시간예상체결 | 실시간-027 | H0UPANC0 | 모의투자 미지원 | POST | `/tryitout/H0UPANC0` |
| 163 | REST | 국내주식 장운영정보 (통합) | 국내주식 장운영정보 (통합) | H0UNMKO0 | 모의투자 미지원 | POST | `/tryitout/H0UNMKO0` |
| 164 | WEBSOCKET | 국내주식 실시간회원사 (NXT) | 국내주식 실시간회원사 (NXT) | H0NXMBC0 | 모의투자 미지원 | POST | `/tryitout/H0NXMBC0` |
| 165 | WEBSOCKET | 국내주식 실시간체결통보 | 실시간-005 | H0STCNI0 | H0STCNI9 | POST | `/tryitout/H0STCNI0` |
| 166 | WEBSOCKET | 국내주식 시간외 실시간예상체결 (KRX) | 실시간-024 | H0STOAC0 | 모의투자 미지원 | POST | `/tryitout/H0STOAC0` |
| 167 | WEBSOCKET | 국내주식 시간외 실시간호가 (KRX) | 실시간-025 | H0STOAA0 | 모의투자 미지원 | POST | `/tryitout/H0STOAA0` |
| 168 | WEBSOCKET | 국내주식 실시간프로그램매매 (통합) | 국내주식 실시간프로그램매매 (통합) | H0UNPGM0 | 모의투자 미지원 | POST | `/tryitout/H0UNPGM0` |
| 169 | WEBSOCKET | 국내주식 실시간호가 (통합) | 국내주식 실시간호가 (통합) | H0UNASP0 | 모의투자 미지원 | POST | `/tryitout/H0UNASP0` |
| 170 | WEBSOCKET | 국내주식 실시간프로그램매매 (KRX) | 실시간-048 | H0STPGM0 | 모의투자 미지원 | POST | `/tryitout/H0STPGM0` |
| 171 | WEBSOCKET | 국내주식 장운영정보 (KRX) | 실시간-049 | H0STMKO0 | 모의투자 미지원 | POST | `/tryitout/H0STMKO0` |
| 172 | WEBSOCKET | 국내주식 실시간체결가 (KRX) | 실시간-003 | H0STCNT0 | H0STCNT0 | POST | `/tryitout/H0STCNT0` |
| 173 | WEBSOCKET | 국내지수 실시간프로그램매매 | 실시간-028 | H0UPPGM0 | 모의투자 미지원 | POST | `/tryitout/H0UPPGM0` |
| 174 | WEBSOCKET | 국내주식 실시간회원사 (통합) | 국내주식 실시간회원사 (통합) | H0UNMBC0 | 모의투자 미지원 | POST | `/tryitout/H0UNMBC0` |
| 175 | WEBSOCKET | 국내지수 실시간체결 | 실시간-026 | H0UPCNT0 | 모의투자 미지원 | POST | `/tryitout/H0UPCNT0` |
| 176 | WEBSOCKET | 국내주식 실시간예상체결 (KRX) | 실시간-041 | H0STANC0 | 모의투자 미지원 | POST | `/tryitout/H0STANC0` |
| 177 | WEBSOCKET | ELW 실시간호가 | 실시간-062 | H0EWASP0 | 모의투자 미지원 | POST | `/tryitout/H0EWASP0` |
| 178 | WEBSOCKET | 국내주식 실시간호가 (KRX) | 실시간-004 | H0STASP0 | H0STASP0 | POST | `/tryitout/H0STASP0` |
| 179 | WEBSOCKET | 국내주식 실시간체결가 (통합) | 국내주식 실시간체결가 (통합) | H0UNCNT0 | 모의투자 미지원 | POST | `/tryitout/H0UNCNT0` |
| 180 | WEBSOCKET | 국내주식 실시간호가 (NXT) | 국내주식 실시간호가 (NXT) | H0NXASP0 | 모의투자 미지원 | POST | `/tryitout/H0NXASP0` |
| 181 | WEBSOCKET | 국내주식 실시간프로그램매매 (NXT) | 국내주식 실시간프로그램매매 (NXT) | H0NXPGM0 | 모의투자 미지원 | POST | `/tryitout/H0NXPGM0` |
| 182 | WEBSOCKET | 국내주식 실시간체결가 (NXT) | 국내주식 실시간체결가 (NXT) | H0NXCNT0 | 모의투자 미지원 | POST | `/tryitout/H0NXCNT0` |
| 183 | WEBSOCKET | ELW 실시간체결가 | 실시간-061 | H0EWCNT0 | 모의투자 미지원 | POST | `/tryitout/H0EWCNT0` |
| 184 | WEBSOCKET | ELW 실시간예상체결 | 실시간-063 | H0EWANC0 | 모의투자 미지원 | POST | `/tryitout/H0EWANC0` |
| 185 | WEBSOCKET | 국내주식 실시간예상체결 (NXT) | 국내주식 실시간예상체결 (NXT) | H0NXANC0 | 모의투자 미지원 | POST | `/tryitout/H0NXANC0` |
| 186 | WEBSOCKET | 국내주식 실시간회원사 (KRX) | 실시간-047 | H0STMBC0 | 모의투자 미지원 | POST | `/tryitout/H0STMBC0` |
| 187 | WEBSOCKET | 국내주식 실시간예상체결 (통합) | 국내주식 실시간예상체결 (통합) | H0UNANC0 | 모의투자 미지원 | POST | `/tryitout/H0UNANC0` |
| 188 | REST | 국내주식 장운영정보 (NXT) | 국내주식 장운영정보 (NXT) | H0NXMKO0 | 모의투자 미지원 | POST | `/tryitout/H0NXMKO0` |
| 189 | WEBSOCKET | 국내ETF NAV추이 | 실시간-051 | H0STNAV0 | 모의투자 미지원 | POST | `/tryitout/H0STNAV0` |
| 190 | WEBSOCKET | 국내주식 시간외 실시간체결가 (KRX) | 실시간-042 | H0STOUP0 | 모의투자 미지원 | POST | `/tryitout/H0STOUP0` |

## [국내선물옵션] 주문/계좌

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 191 | REST | (야간)선물옵션 증거금 상세 | 국내선물-024 | (구) JTCE6003R (신) CTFN7107R | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/trading/ngt-margin-detail` |
| 192 | REST | 선물옵션 총자산현황 | v1_국내선물-014 | CTRP6550R | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/trading/inquire-deposit` |
| 193 | REST | 선물옵션기간약정수수료일별 | v1_국내선물-017 | CTFO6119R | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/trading/inquire-daily-amount-fee` |
| 194 | REST | (야간)선물옵션 잔고현황 | 국내선물-010 | (구) JTCE6001R (신) CTFN6118R | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/trading/inquire-ngt-balance` |
| 195 | REST | 선물옵션 잔고현황 | v1_국내선물-004 | CTFO6118R | VTFO6118R | GET | `/uapi/domestic-futureoption/v1/trading/inquire-balance` |
| 196 | REST | 선물옵션 주문 | v1_국내선물-001 | (주간 매수/매도) TTTO1101U (야간 매수/매도) (구) JTCE1001U (신) STTN1101U | (주간 매수/매도) VTTO1101U (야간은 모의투자 미제공) | POST | `/uapi/domestic-futureoption/v1/trading/order` |
| 197 | REST | 선물옵션 잔고평가손익내역 | v1_국내선물-015 | CTFO6159R | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/trading/inquire-balance-valuation-pl` |
| 198 | REST | 선물옵션 증거금률 | 선물옵션 증거금률 | TTTO6032R | 미지원 | GET | `/uapi/domestic-futureoption/v1/quotations/margin-rate` |
| 199 | REST | 선물옵션 정정취소주문 | v1_국내선물-002 | (주간 정정/취소) TTTO1103U (야간 정정/취소) (구) JTCE1002U (신) STTN1103U | (주간 정정/취소) VTTO1103U (야간은 모의투자 미제공) | POST | `/uapi/domestic-futureoption/v1/trading/order-rvsecncl` |
| 200 | REST | 선물옵션 주문체결내역조회 | v1_국내선물-003 | TTTO5201R | VTTO5201R | GET | `/uapi/domestic-futureoption/v1/trading/inquire-ccnl` |
| 201 | REST | (야간)선물옵션 주문체결 내역조회 | 국내선물-009 | (구) JTCE5005R (신) STTN5201R | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/trading/inquire-ngt-ccnl` |
| 202 | REST | (야간)선물옵션 주문가능 조회 | 국내선물-011 | (구) JTCE1004R (신) STTN5105R | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/trading/inquire-psbl-ngt-order` |
| 203 | REST | 선물옵션 잔고정산손익내역 | v1_국내선물-013 | CTFO6117R | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/trading/inquire-balance-settlement-pl` |
| 204 | REST | 선물옵션 주문가능 | v1_국내선물-005 | TTTO5105R | VTTO5105R | GET | `/uapi/domestic-futureoption/v1/trading/inquire-psbl-order` |
| 205 | REST | 선물옵션 기준일체결내역 | v1_국내선물-016 | CTFO5139R | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/trading/inquire-ccnl-bstime` |

## [국내선물옵션] 기본시세

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 206 | REST | 선물옵션 시세 | v1_국내선물-006 | FHMIF10000000 | FHMIF10000000 | GET | `/uapi/domestic-futureoption/v1/quotations/inquire-price` |
| 207 | REST | 국내선물 기초자산 시세 | 국내선물-021 | FHPIF05030000 | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/quotations/display-board-top` |
| 208 | REST | 선물옵션 일중예상체결추이 | 국내선물-018 | FHPIF05110100 | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/quotations/exp-price-trend` |
| 209 | REST | 선물옵션기간별시세(일/주/월/년) | v1_국내선물-008 | FHKIF03020100 | FHKIF03020100 | GET | `/uapi/domestic-futureoption/v1/quotations/inquire-daily-fuopchartprice` |
| 210 | REST | 국내옵션전광판_선물 | 국내선물-023 | FHPIF05030200 | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/quotations/display-board-futures` |
| 211 | REST | 선물옵션 분봉조회 | v1_국내선물-012 | FHKIF03020200 | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/quotations/inquire-time-fuopchartprice` |
| 212 | REST | 국내옵션전광판_옵션월물리스트 | 국내선물-020 | FHPIO056104C0 | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/quotations/display-board-option-list` |
| 213 | REST | 선물옵션 시세호가 | v1_국내선물-007 | FHMIF10010000 | FHMIF10010000 | GET | `/uapi/domestic-futureoption/v1/quotations/inquire-asking-price` |
| 214 | REST | 국내옵션전광판_콜풋 | 국내선물-022 | FHPIF05030100 | 모의투자 미지원 | GET | `/uapi/domestic-futureoption/v1/quotations/display-board-callput` |

## [국내선물옵션] 실시간시세

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 215 | WEBSOCKET | 주식옵션 실시간호가 | 실시간-045 | H0ZOASP0 | 모의투자 미지원 | POST | `/tryitout/H0ZOASP0` |
| 216 | WEBSOCKET | 선물옵션 실시간체결통보 | 실시간-012 | H0IFCNI0 | H0IFCNI9 | POST | `/tryitout/H0IFCNI0` |
| 217 | WEBSOCKET | KRX야간선물 실시간종목체결 | 실시간-064 | H0MFCNT0 | 모의투자 미지원 | POST | `/tryitout/H0MFCNT0` |
| 218 | WEBSOCKET | KRX야간선물 실시간호가 | 실시간-065 | H0MFASP0 | 모의투자 미지원 | POST | `/tryitout/H0MFASP0` |
| 219 | WEBSOCKET | KRX야간옵션 실시간체결가 | 실시간-032 | H0EUCNT0 | 모의투자 미지원 | POST | `/tryitout/H0EUCNT0` |
| 220 | WEBSOCKET | KRX야간옵션실시간예상체결 | 실시간-034 | H0EUANC0 | 모의투자 미지원 | POST | `/tryitout/H0EUANC0` |
| 221 | WEBSOCKET | 지수선물 실시간체결가 | 실시간-010 | H0IFCNT0 | 모의투자 미지원 | POST | `/tryitout/H0IFCNT0` |
| 222 | WEBSOCKET | 주식선물 실시간예상체결 | 실시간-031 | H0ZFANC0 | 모의투자 미지원 | POST | `/tryitout/H0ZFANC0` |
| 223 | WEBSOCKET | KRX야간옵션실시간체결통보 | 실시간-067 | H0MFCNI0 | 모의투자 미지원 | POST | `/tryitout/H0EUCNI0` |
| 224 | WEBSOCKET | KRX야간선물 실시간체결통보 | 실시간-066 | H0MFCNI0 | 모의투자 미지원 | POST | `/tryitout/H0MFCNI0` |
| 225 | WEBSOCKET | 상품선물 실시간체결가 | 실시간-022 | H0CFCNT0 | 모의투자 미지원 | POST | `/tryitout/H0CFCNT0` |
| 226 | WEBSOCKET | 지수선물 실시간호가 | 실시간-011 | H0IFASP0 | 모의투자 미지원 | POST | `/tryitout/H0IFASP0` |
| 227 | WEBSOCKET | 지수옵션  실시간체결가 | 실시간-014 | H0IOCNT0 | 모의투자 미지원 | POST | `/tryitout/H0IOCNT0` |
| 228 | WEBSOCKET | KRX야간옵션 실시간호가 | 실시간-033 | H0EUASP0 | 모의투자 미지원 | POST | `/tryitout/H0EUASP0` |
| 229 | WEBSOCKET | 상품선물 실시간호가 | 실시간-023 | H0CFASP0 | 모의투자 미지원 | POST | `/tryitout/H0CFASP0` |
| 230 | WEBSOCKET | 주식옵션 실시간예상체결 | 실시간-046 | H0ZOANC0 | 모의투자 미지원 | POST | `/tryitout/H0ZOANC0` |
| 231 | WEBSOCKET | 주식선물 실시간호가 | 실시간-030 | H0ZFASP0 | 모의투자 미지원 | POST | `/tryitout/H0ZFASP0` |
| 232 | WEBSOCKET | 주식옵션 실시간체결가 | 실시간-044 | H0ZOCNT0 | 모의투자 미지원 | POST | `/tryitout/H0ZOCNT0` |
| 233 | WEBSOCKET | 지수옵션 실시간호가 | 실시간-015 | H0IOASP0 | 모의투자 미지원 | POST | `/tryitout/H0IOASP0` |
| 234 | WEBSOCKET | 주식선물 실시간체결가 | 실시간-029 | H0ZFCNT0 | 모의투자 미지원 | POST | `/tryitout/H0ZFCNT0` |

## [해외주식] 주문/계좌

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 235 | REST | 해외주식 잔고 | v1_해외주식-006 | TTTS3012R | VTTS3012R | GET | `/uapi/overseas-stock/v1/trading/inquire-balance` |
| 236 | REST | 해외주식 체결기준현재잔고 | v1_해외주식-008 | CTRP6504R | VTRP6504R | GET | `/uapi/overseas-stock/v1/trading/inquire-present-balance` |
| 237 | REST | 해외주식 지정가체결내역조회 | 해외주식-070 | TTTS6059R | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/trading/inquire-algo-ccnl` |
| 238 | REST | 해외주식 기간손익 | v1_해외주식-032 | TTTS3039R | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/trading/inquire-period-profit` |
| 239 | REST | 해외주식 매수가능금액조회 | v1_해외주식-014 | TTTS3007R | VTTS3007R | GET | `/uapi/overseas-stock/v1/trading/inquire-psamount` |
| 240 | REST | 해외주식 정정취소주문 | v1_해외주식-003 | (미국 정정·취소) TTTT1004U (아시아 국가 하단 규격서 참고) | (미국 정정·취소) VTTT1004U (아시아 국가 하단 규격서 참고) | POST | `/uapi/overseas-stock/v1/trading/order-rvsecncl` |
| 241 | REST | 해외주식 예약주문접수 | v1_해외주식-002 | (미국예약매수) TTTT3014U  (미국예약매도) TTTT3016U   (중국/홍콩/일본/베트남 예약주문) TTTS3013U | (미국예약매수) VTTT3014U  (미국예약매도) VTTT3016U   (중국/홍콩/일본/베트남 예약주문) VTTS3013U | POST | `/uapi/overseas-stock/v1/trading/order-resv` |
| 242 | REST | 해외주식 미체결내역 | v1_해외주식-005 | TTTS3018R | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/trading/inquire-nccs` |
| 243 | REST | 해외주식 미국주간정정취소 | v1_해외주식-027 | TTTS6038U | 모의투자 미지원 | POST | `/uapi/overseas-stock/v1/trading/daytime-order-rvsecncl` |
| 244 | REST | 해외주식 주문체결내역 | v1_해외주식-007 | TTTS3035R | VTTS3035R | GET | `/uapi/overseas-stock/v1/trading/inquire-ccnl` |
| 245 | REST | 해외주식 결제기준잔고 | 해외주식-064 | CTRP6010R | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/trading/inquire-paymt-stdr-balance` |
| 246 | REST | 해외주식 일별거래내역 | 해외주식-063 | CTOS4001R | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/trading/inquire-period-trans` |
| 247 | REST | 해외주식 미국주간주문 | v1_해외주식-026 | (주간매수) TTTS6036U (주간매도) TTTS6037U | 모의투자 미지원 | POST | `/uapi/overseas-stock/v1/trading/daytime-order` |
| 248 | REST | 해외주식 예약주문조회 | v1_해외주식-013 | (미국) TTTT3039R (일본/중국/홍콩/베트남) TTTS3014R | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/trading/order-resv-list` |
| 249 | REST | 해외주식 주문 | v1_해외주식-001 | (미국매수) TTTT1002U  (미국매도) TTTT1006U (아시아 국가 하단 규격서 참고) | (미국매수) VTTT1002U  (미국매도) VTTT1001U  (아시아 국가 하단 규격서 참고) | POST | `/uapi/overseas-stock/v1/trading/order` |
| 250 | REST | 해외주식 예약주문접수취소 | v1_해외주식-004 | (미국 예약주문 취소접수) TTTT3017U (아시아국가 미제공) | (미국 예약주문 취소접수) VTTT3017U (아시아국가 미제공) | POST | `/uapi/overseas-stock/v1/trading/order-resv-ccnl` |
| 251 | REST | 해외주식 지정가주문번호조회 | 해외주식-071 | TTTS6058R | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/trading/algo-ordno` |
| 252 | REST | 해외증거금 통화별조회 | 해외주식-035 | TTTC2101R | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/trading/foreign-margin` |

## [해외주식] 기본시세

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 253 | REST | 해외주식 체결추이 | 해외주식-037 | HHDFS76200300 | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/inquire-ccnl` |
| 254 | REST | 해외주식 기간별시세 | v1_해외주식-010 | HHDFS76240000 | HHDFS76240000 | GET | `/uapi/overseas-price/v1/quotations/dailyprice` |
| 255 | REST | 해외결제일자조회 | 해외주식-017 | CTOS5011R | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/quotations/countries-holiday` |
| 256 | REST | 해외주식 현재체결가 | v1_해외주식-009 | HHDFS00000300 | HHDFS00000300 | GET | `/uapi/overseas-price/v1/quotations/price` |
| 257 | REST | 해외주식 복수종목 시세조회 | 해외주식 복수종목 시세조회 | HHDFS76220000 | 미지원 | GET | `/uapi/overseas-price/v1/quotations/multprice` |
| 258 | REST | 해외주식조건검색 | v1_해외주식-015 | HHDFS76410000 | HHDFS76410000 | GET | `/uapi/overseas-price/v1/quotations/inquire-search` |
| 259 | REST | 해외주식 상품기본정보 | v1_해외주식-034 | CTPF1702R | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/search-info` |
| 260 | REST | 해외지수분봉조회 | v1_해외주식-031 | FHKST03030200 | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/inquire-time-indexchartprice` |
| 261 | REST | 해외주식분봉조회 | v1_해외주식-030 | HHDFS76950200 | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice` |
| 262 | REST | 해외주식 현재가상세 | v1_해외주식-029 | HHDFS76200200 | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/price-detail` |
| 263 | REST | 해외주식 업종별코드조회 | 해외주식-049 | HHDFS76370100 | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/industry-price` |
| 264 | REST | 해외주식 종목/지수/환율기간별시세(일/주/월/년) | v1_해외주식-012 | FHKST03030100 | FHKST03030100 | GET | `/uapi/overseas-price/v1/quotations/inquire-daily-chartprice` |
| 265 | REST | 해외주식 업종별시세 | 해외주식-048 | HHDFS76370000 | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/industry-theme` |
| 266 | REST | 해외주식 현재가 호가 | 해외주식-033 | HHDFS76200100 | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/inquire-asking-price` |

## [해외주식] 시세분석

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 267 | REST | 해외주식 거래증가율순위 | 해외주식-045 | HHDFS76330000 | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/ranking/trade-growth` |
| 268 | REST | 해외주식 기간별권리조회 | 해외주식-052 | CTRGT011R | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/period-rights` |
| 269 | REST | 해외주식 가격급등락 | 해외주식-038 | HHDFS76260000 | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/ranking/price-fluct` |
| 270 | REST | 해외주식 거래대금순위 | 해외주식-044 | HHDFS76320010 | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/ranking/trade-pbmn` |
| 271 | REST | 해외주식 거래량급증 | 해외주식-039 | HHDFS76270000 | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/ranking/volume-surge` |
| 272 | REST | 해외주식 신고/신저가 | 해외주식-042 | HHDFS76300000 | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/ranking/new-highlow` |
| 273 | REST | 해외주식 매수체결강도상위 | 해외주식-040 | HHDFS76280000 | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/ranking/volume-power` |
| 274 | REST | 해외주식 거래회전율순위 | 해외주식-046 | HHDFS76340000 | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/ranking/trade-turnover` |
| 275 | REST | 해외뉴스종합(제목) | 해외주식-053 | HHPSTH60100C1 | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/news-title` |
| 276 | REST | 당사 해외주식담보대출 가능 종목 | 해외주식-051 | CTLN4050R | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/colable-by-company` |
| 277 | REST | 해외주식 시가총액순위 | 해외주식-047 | HHDFS76350100 | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/ranking/market-cap` |
| 278 | REST | 해외속보(제목) | 해외주식-055 | FHKST01011801 | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/brknews-title` |
| 279 | REST | 해외주식 상승율/하락율 | 해외주식-041 | HHDFS76290000 | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/ranking/updown-rate` |
| 280 | REST | 해외주식 권리종합 | 해외주식-050 | HHDFS78330900 | 모의투자 미지원 | GET | `/uapi/overseas-price/v1/quotations/rights-by-ice` |
| 281 | REST | 해외주식 거래량순위 | 해외주식-043 | HHDFS76310010 | 모의투자 미지원 | GET | `/uapi/overseas-stock/v1/ranking/trade-vol` |

## [해외주식] 실시간시세

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 282 | WEBSOCKET | 해외주식 실시간호가 | 실시간-021 | HDFSASP0 | 모의투자 미지원 | POST | `/tryitout/HDFSASP0` |
| 283 | WEBSOCKET | 해외주식 지연호가(아시아) | 실시간-008 | HDFSASP1 | 모의투자 미지원 | POST | `/tryitout/HDFSASP1` |
| 284 | WEBSOCKET | 해외주식 실시간지연체결가 | 실시간-007 | HDFSCNT0 | 모의투자 미지원 | POST | `/tryitout/HDFSCNT0` |
| 285 | WEBSOCKET | 해외주식 실시간체결통보 | 실시간-009 | H0GSCNI0 | H0GSCNI9 | POST | `/tryitout/H0GSCNI0` |

## [해외선물옵션] 주문/계좌

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 286 | REST | 해외선물옵션 주문 | v1_해외선물-001 | OTFM3001U | 모의투자 미지원 | POST | `/uapi/overseas-futureoption/v1/trading/order` |
| 287 | REST | 해외선물옵션 정정취소주문 | v1_해외선물-002, 003 | (정정) OTFM3002U (취소) OTFM3003U | 모의투자 미지원 | POST | `/uapi/overseas-futureoption/v1/trading/order-rvsecncl` |
| 288 | REST | 해외선물옵션 당일주문내역조회 | v1_해외선물-004 | OTFM3116R | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/trading/inquire-ccld` |
| 289 | REST | 해외선물옵션 미결제내역조회(잔고) | v1_해외선물-005 | OTFM1412R | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/trading/inquire-unpd` |
| 290 | REST | 해외선물옵션 주문가능조회 | v1_해외선물-006 | OTFM3304R | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/trading/inquire-psamount` |
| 291 | REST | 해외선물옵션 기간계좌손익 일별 | 해외선물-010 | OTFM3118R | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/trading/inquire-period-ccld` |
| 292 | REST | 해외선물옵션 일별 체결내역 | 해외선물-011 | OTFM3122R | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/trading/inquire-daily-ccld` |
| 293 | REST | 해외선물옵션 예수금현황 | 해외선물-012 | OTFM1411R | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/trading/inquire-deposit` |
| 294 | REST | 해외선물옵션 일별 주문내역 | 해외선물-013 | OTFM3120R | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/trading/inquire-daily-order` |
| 295 | REST | 해외선물옵션 기간계좌거래내역 | 해외선물-014 | OTFM3114R | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/trading/inquire-period-trans` |
| 296 | REST | 해외선물옵션 증거금상세 | 해외선물-032 | OTFM3115R | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/trading/margin-detail` |

## [해외선물옵션] 기본시세

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 297 | REST | 해외선물종목현재가 | v1_해외선물-009 | HHDFC55010000 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/inquire-price` |
| 298 | REST | 해외선물종목상세 | v1_해외선물-008 | HHDFC55010100 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/stock-detail` |
| 299 | REST | 해외선물 호가 | 해외선물-031 | HHDFC86000000 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/inquire-asking-price` |
| 300 | REST | 해외선물 분봉조회 | 해외선물-016 | HHDFC55020400 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/inquire-time-futurechartprice` |
| 301 | REST | 해외선물 체결추이(틱) | 해외선물-019 | HHDFC55020200 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/tick-ccnl` |
| 302 | REST | 해외선물 체결추이(주간) | 해외선물-017 | HHDFC55020000 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/weekly-ccnl` |
| 303 | REST | 해외선물 체결추이(일간) | 해외선물-018 | HHDFC55020100 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/daily-ccnl` |
| 304 | REST | 해외선물 체결추이(월간) | 해외선물-020 | HHDFC55020300 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/monthly-ccnl` |
| 305 | REST | 해외선물 상품기본정보 | 해외선물-023 | HHDFC55200000 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/search-contract-detail` |
| 306 | REST | 해외선물 미결제추이 | 해외선물-029 | HHDDB95030000 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/investor-unpd-trend` |
| 307 | REST | 해외옵션종목현재가 | 해외선물-035 | HHDFO55010000 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/opt-price` |
| 308 | REST | 해외옵션종목상세 | 해외선물-034 | HHDFO55010100 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/opt-detail` |
| 309 | REST | 해외옵션 호가 | 해외선물-033 | HHDFO86000000 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/opt-asking-price` |
| 310 | REST | 해외옵션 분봉조회 | 해외선물-040 | HHDFO55020400 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/inquire-time-optchartprice` |
| 311 | REST | 해외옵션 체결추이(틱) | 해외선물-038 | HHDFO55020200 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/opt-tick-ccnl` |
| 312 | REST | 해외옵션 체결추이(일간) | 해외선물-037 | HHDFO55020100 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/opt-daily-ccnl` |
| 313 | REST | 해외옵션 체결추이(주간) | 해외선물-036 | HHDFO55020000 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/opt-weekly-ccnl` |
| 314 | REST | 해외옵션 체결추이(월간) | 해외선물-039 | HHDFO55020300 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/opt-monthly-ccnl` |
| 315 | REST | 해외옵션 상품기본정보 | 해외선물-041 | HHDFO55200000 | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/search-opt-detail` |
| 316 | REST | 해외선물옵션 장운영시간 | 해외선물-030 | OTFM2229R | 모의투자 미지원 | GET | `/uapi/overseas-futureoption/v1/quotations/market-time` |

## [해외선물옵션]실시간시세

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 317 | WEBSOCKET | 해외선물옵션 실시간체결가 | 실시간-017 | HDFFF020 | 모의투자 미지원 | POST | `/tryitout/HDFFF020` |
| 318 | WEBSOCKET | 해외선물옵션 실시간호가 | 실시간-018 | HDFFF010 | 모의투자 미지원 | POST | `/tryitout/HDFFF010` |
| 319 | WEBSOCKET | 해외선물옵션 실시간주문내역통보 | 실시간-019 | HDFFF1C0 | 모의투자 미지원 | POST | `/tryitout/HDFFF1C0` |
| 320 | WEBSOCKET | 해외선물옵션 실시간체결내역통보 | 실시간-020 | HDFFF2C0 | 모의투자 미지원 | POST | `/tryitout/HDFFF2C0` |

## [장내채권] 주문/계좌

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 321 | REST | 장내채권 매수주문 | 국내주식-124 | TTTC0952U | 모의투자 미지원 | POST | `/uapi/domestic-bond/v1/trading/buy` |
| 322 | REST | 장내채권 매도주문 | 국내주식-123 | TTTC0958U | 모의투자 미지원 | POST | `/uapi/domestic-bond/v1/trading/sell` |
| 323 | REST | 장내채권 정정취소주문 | 국내주식-125 | TTTC0953U | 모의투자 미지원 | POST | `/uapi/domestic-bond/v1/trading/order-rvsecncl` |
| 324 | REST | 채권정정취소가능주문조회 | 국내주식-126 | CTSC8035R | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/trading/inquire-psbl-rvsecncl` |
| 325 | REST | 장내채권 주문체결내역 | 국내주식-127 | CTSC8013R | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/trading/inquire-daily-ccld` |
| 326 | REST | 장내채권 잔고조회 | 국내주식-198 | CTSC8407R | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/trading/inquire-balance` |
| 327 | REST | 장내채권 매수가능조회 | 국내주식-199 | TTTC8910R | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/trading/inquire-psbl-order` |

## [장내채권] 기본시세

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 328 | REST | 장내채권현재가(호가) | 국내주식-132 | FHKBJ773401C0 | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/quotations/inquire-asking-price` |
| 329 | REST | 장내채권현재가(시세) | 국내주식-200 | FHKBJ773400C0 | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/quotations/inquire-price` |
| 330 | REST | 장내채권현재가(체결) | 국내주식-201 | FHKBJ773403C0 | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/quotations/inquire-ccnl` |
| 331 | REST | 장내채권현재가(일별) | 국내주식-202 | FHKBJ773404C0 | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/quotations/inquire-daily-price` |
| 332 | REST | 장내채권 기간별시세(일) | 국내주식-159 | FHKBJ773701C0 | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/quotations/inquire-daily-itemchartprice` |
| 333 | REST | 장내채권 평균단가조회 | 국내주식-158 | CTPF2005R | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/quotations/avg-unit` |
| 334 | REST | 장내채권 발행정보 | 국내주식-156 | CTPF1101R | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/quotations/issue-info` |
| 335 | REST | 장내채권 기본조회 | 국내주식-129 | CTPF1114R | 모의투자 미지원 | GET | `/uapi/domestic-bond/v1/quotations/search-bond-info` |

## [장내채권] 실시간시세

| # | 방식 | API 명 | API ID | TR_ID (실전) | TR_ID (모의) | Method | URL |
|---|------|--------|--------|-------------|-------------|--------|-----|
| 336 | WEBSOCKET | 일반채권 실시간체결가 | 실시간-052 | H0BJCNT0 | 모의투자 미지원 | POST | `/tryitout/H0BJCNT0` |
| 337 | WEBSOCKET | 일반채권 실시간호가 | 실시간-053 | H0BJCNT0 | 모의투자 미지원 | POST | `/tryitout/H0BJASP0` |
| 338 | WEBSOCKET | 채권지수 실시간체결가 | 실시간-060 | H0BICNT0 | 모의투자 미지원 | POST | `/tryitout/H0BICNT0` |
