# KIS OpenAPI 전체 인덱스

> 출처: `한국투자증권_오픈API_전체문서_20260508_030000.xlsx` (2026-05-08 기준).  
> 자동 변환: `scripts/kis_excel_to_md.py`. 본 디렉토리는 코드/리뷰용 참조 자료이며, 1:1 사본이 아님(표 형식 정리됨).

## 카테고리 목차

| 파일 | 카테고리 | API 수 |
| --- | --- | --- |
| [01_OAUTH.md](./01_OAUTH.md) | OAuth 인증 (`OAuth인증`) | 3 |
| [02_KR_STOCK_ORDER.md](./02_KR_STOCK_ORDER.md) | 국내주식 주문/계좌 (`[국내주식] 주문/계좌`) | 23 |
| [03_KR_STOCK_QUOTE.md](./03_KR_STOCK_QUOTE.md) | 국내주식 기본시세 (`[국내주식] 기본시세`) | 21 |
| [04_KR_ELW.md](./04_KR_ELW.md) | 국내주식 ELW 시세 (`[국내주식] ELW 시세`) | 22 |
| [05_KR_SECTOR_ETC.md](./05_KR_SECTOR_ETC.md) | 국내주식 업종/기타 (`[국내주식] 업종/기타`) | 14 |
| [06_KR_STOCK_INFO.md](./06_KR_STOCK_INFO.md) | 국내주식 종목정보 (`[국내주식] 종목정보`) | 26 |
| [07_KR_MARKET_ANALYSIS.md](./07_KR_MARKET_ANALYSIS.md) | 국내주식 시세분석 (`[국내주식] 시세분석`) | 29 |
| [08_KR_RANK.md](./08_KR_RANK.md) | 국내주식 순위분석 (`[국내주식] 순위분석`) | 22 |
| [09_KR_REALTIME.md](./09_KR_REALTIME.md) | 국내주식 실시간시세 (`[국내주식] 실시간시세`) | 29 |
| [10_KR_FUTURES_ORDER.md](./10_KR_FUTURES_ORDER.md) | 국내선물옵션 주문/계좌 (`[국내선물옵션] 주문/계좌`) | 15 |
| [11_KR_FUTURES_QUOTE.md](./11_KR_FUTURES_QUOTE.md) | 국내선물옵션 기본시세 (`[국내선물옵션] 기본시세`) | 9 |
| [12_KR_FUTURES_REALTIME.md](./12_KR_FUTURES_REALTIME.md) | 국내선물옵션 실시간시세 (`[국내선물옵션] 실시간시세`) | 20 |
| [13_US_STOCK_ORDER.md](./13_US_STOCK_ORDER.md) | 해외주식 주문/계좌 (`[해외주식] 주문/계좌`) | 18 |
| [14_US_STOCK_QUOTE.md](./14_US_STOCK_QUOTE.md) | 해외주식 기본시세 (`[해외주식] 기본시세`) | 14 |
| [15_US_STOCK_ANALYSIS.md](./15_US_STOCK_ANALYSIS.md) | 해외주식 시세분석 (`[해외주식] 시세분석`) | 15 |
| [16_US_STOCK_REALTIME.md](./16_US_STOCK_REALTIME.md) | 해외주식 실시간시세 (`[해외주식] 실시간시세`) | 4 |
| [17_US_FUTURES_ORDER.md](./17_US_FUTURES_ORDER.md) | 해외선물옵션 주문/계좌 (`[해외선물옵션] 주문/계좌`) | 11 |
| [18_US_FUTURES_QUOTE.md](./18_US_FUTURES_QUOTE.md) | 해외선물옵션 기본시세 (`[해외선물옵션] 기본시세`) | 20 |
| [19_US_FUTURES_REALTIME.md](./19_US_FUTURES_REALTIME.md) | 해외선물옵션 실시간시세 (`[해외선물옵션]실시간시세`) | 4 |
| [20_BOND_ORDER.md](./20_BOND_ORDER.md) | 장내채권 주문/계좌 (`[장내채권] 주문/계좌`) | 7 |
| [21_BOND_QUOTE.md](./21_BOND_QUOTE.md) | 장내채권 기본시세 (`[장내채권] 기본시세`) | 8 |
| [22_BOND_REALTIME.md](./22_BOND_REALTIME.md) | 장내채권 실시간시세 (`[장내채권] 실시간시세`) | 3 |

**총 API 수**: 337개  

---

## 전체 API 표 (메뉴 위치별 정렬)

| # | 카테고리 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | OAuth인증 | 실시간 (웹소켓) 접속키 발급 | 실시간-000 |  |  | WEBSOCKET POST | `/oauth2/Approval` |
| 2 | OAuth인증 | 접근토큰폐기(P) | 인증-002 |  |  | REST POST | `/oauth2/revokeP` |
| 3 | OAuth인증 | 접근토큰발급(P) | 인증-001 |  |  | REST POST | `/oauth2/tokenP` |
| 4 | [국내주식] 주문/계좌 | 기간별계좌권리현황조회 | 국내주식-211 | CTRGA011R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/period-rights` |
| 5 | [국내주식] 주문/계좌 | 투자계좌자산현황조회 | v1_국내주식-048 | CTRP6548R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/inquire-account-balance` |
| 6 | [국내주식] 주문/계좌 | 퇴직연금 예수금조회 | v1_국내주식-035 | TTTC0506R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/pension/inquire-deposit` |
| 7 | [국내주식] 주문/계좌 | 주식예약주문정정취소 | v1_국내주식-018,019 | (예약취소) CTSC0009U (예약정정) CTSC0013U | 모의투자 미지원 | REST POST | `/uapi/domestic-stock/v1/trading/order-resv-rvsecncl` |
| 8 | [국내주식] 주문/계좌 | 신용매수가능조회 | v1_국내주식-042 | TTTC8909R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/inquire-credit-psamount` |
| 9 | [국내주식] 주문/계좌 | 주식통합증거금 현황 | 국내주식-191 | TTTC0869R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/intgr-margin` |
| 10 | [국내주식] 주문/계좌 | 퇴직연금 미체결내역 | v1_국내주식-033 | TTTC2201R(기존 KRX만 가능), TTTC2210R (KRX,NXT/SOR) | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/pension/inquire-daily-ccld` |
| 11 | [국내주식] 주문/계좌 | 기간별매매손익현황조회 | v1_국내주식-060 | TTTC8715R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/inquire-period-trade-profit` |
| 12 | [국내주식] 주문/계좌 | 주식주문(정정취소) | v1_국내주식-003 | TTTC0013U | VTTC0013U | REST POST | `/uapi/domestic-stock/v1/trading/order-rvsecncl` |
| 13 | [국내주식] 주문/계좌 | 주식예약주문조회 | v1_국내주식-020 | CTSC0004R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/order-resv-ccnl` |
| 14 | [국내주식] 주문/계좌 | 퇴직연금 매수가능조회 | v1_국내주식-034 | TTTC0503R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/pension/inquire-psbl-order` |
| 15 | [국내주식] 주문/계좌 | 주식잔고조회 | v1_국내주식-006 | TTTC8434R | VTTC8434R | REST GET | `/uapi/domestic-stock/v1/trading/inquire-balance` |
| 16 | [국내주식] 주문/계좌 | 퇴직연금 체결기준잔고 | v1_국내주식-032 | TTTC2202R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/pension/inquire-present-balance` |
| 17 | [국내주식] 주문/계좌 | 매수가능조회 | v1_국내주식-007 | TTTC8908R | VTTC8908R | REST GET | `/uapi/domestic-stock/v1/trading/inquire-psbl-order` |
| 18 | [국내주식] 주문/계좌 | 기간별손익일별합산조회 | v1_국내주식-052 | TTTC8708R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/inquire-period-profit` |
| 19 | [국내주식] 주문/계좌 | 주식주문(현금) | v1_국내주식-001 | (매도) TTTC0011U (매수) TTTC0012U | (매도) VTTC0011U (매수) VTTC0012U | REST POST | `/uapi/domestic-stock/v1/trading/order-cash` |
| 20 | [국내주식] 주문/계좌 | 매도가능수량조회 | 국내주식-165 | TTTC8408R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/inquire-psbl-sell` |
| 21 | [국내주식] 주문/계좌 | 주식일별주문체결조회 | v1_국내주식-005 | (3개월이내) TTTC0081R (3개월이전) CTSC9215R | (3개월이내) VTTC0081R (3개월이전) VTSC9215R | REST GET | `/uapi/domestic-stock/v1/trading/inquire-daily-ccld` |
| 22 | [국내주식] 주문/계좌 | 주식정정취소가능주문조회 | v1_국내주식-004 | TTTC0084R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl` |
| 23 | [국내주식] 주문/계좌 | 주식예약주문 | v1_국내주식-017 | CTSC0008U | 모의투자 미지원 | REST POST | `/uapi/domestic-stock/v1/trading/order-resv` |
| 24 | [국내주식] 주문/계좌 | 주식주문(신용) | v1_국내주식-002 | (매도) TTTC0051U (매수) TTTC0052U | 모의투자 미지원 | REST POST | `/uapi/domestic-stock/v1/trading/order-credit` |
| 25 | [국내주식] 주문/계좌 | 퇴직연금 잔고조회 | v1_국내주식-036 | TTTC2208R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/pension/inquire-balance` |
| 26 | [국내주식] 주문/계좌 | 주식잔고조회_실현손익 | v1_국내주식-041 | TTTC8494R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/trading/inquire-balance-rlz-pl` |
| 27 | [국내주식] 기본시세 | 주식현재가 일자별 | v1_국내주식-010 | FHKST01010400 | FHKST01010400 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-price` |
| 28 | [국내주식] 기본시세 | 주식현재가 시세 | v1_국내주식-008 | FHKST01010100 | FHKST01010100 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-price` |
| 29 | [국내주식] 기본시세 | 국내주식 시간외현재가 | 국내주식-076 | FHPST02300000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-overtime-price` |
| 30 | [국내주식] 기본시세 | ETF 구성종목시세 | 국내주식-073 | FHKST121600C0 | 모의투자 미지원 | REST GET | `/uapi/etfetn/v1/quotations/inquire-component-stock-price` |
| 31 | [국내주식] 기본시세 | 주식현재가 시간외시간별체결 | v1_국내주식-025 | FHPST02310000 | FHPST02310000 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-time-overtimeconclusion` |
| 32 | [국내주식] 기본시세 | NAV 비교추이(종목) | v1_국내주식-069 | FHPST02440000 | 모의투자 미지원 | REST GET | `/uapi/etfetn/v1/quotations/nav-comparison-trend` |
| 33 | [국내주식] 기본시세 | 주식현재가 시간외일자별주가 | v1_국내주식-026 | FHPST02320000 | FHPST02320000 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-overtimeprice` |
| 34 | [국내주식] 기본시세 | 국내주식 시간외호가 | 국내주식-077 | FHPST02300400 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-overtime-asking-price` |
| 35 | [국내주식] 기본시세 | 주식현재가 당일시간대별체결 | v1_국내주식-023 | FHPST01060000 | FHPST01060000 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion` |
| 36 | [국내주식] 기본시세 | 주식현재가 시세2 | v1_국내주식-054 | FHPST01010000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-price-2` |
| 37 | [국내주식] 기본시세 | 주식일별분봉조회 | 국내주식-213 | FHKST03010230 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice` |
| 38 | [국내주식] 기본시세 | 국내주식기간별시세(일/주/월/년) | v1_국내주식-016 | FHKST03010100 | FHKST03010100 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice` |
| 39 | [국내주식] 기본시세 | NAV 비교추이(일) | v1_국내주식-071 | FHPST02440200 | 모의투자 미지원 | REST GET | `/uapi/etfetn/v1/quotations/nav-comparison-daily-trend` |
| 40 | [국내주식] 기본시세 | 주식현재가 호가/예상체결 | v1_국내주식-011 | FHKST01010200 | FHKST01010200 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn` |
| 41 | [국내주식] 기본시세 | 주식현재가 체결 | v1_국내주식-009 | FHKST01010300 | FHKST01010300 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-ccnl` |
| 42 | [국내주식] 기본시세 | 주식현재가 회원사 | v1_국내주식-013 | FHKST01010600 | FHKST01010600 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-member` |
| 43 | [국내주식] 기본시세 | NAV 비교추이(분) | v1_국내주식-070 | FHPST02440100 | 모의투자 미지원 | REST GET | `/uapi/etfetn/v1/quotations/nav-comparison-time-trend` |
| 44 | [국내주식] 기본시세 | 주식현재가 투자자 | v1_국내주식-012 | FHKST01010900 | FHKST01010900 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-investor` |
| 45 | [국내주식] 기본시세 | ETF/ETN 현재가 | v1_국내주식-068 | FHPST02400000 | 모의투자 미지원 | REST GET | `/uapi/etfetn/v1/quotations/inquire-price` |
| 46 | [국내주식] 기본시세 | 국내주식 장마감 예상체결가 | 국내주식-120 | FHKST117300C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/exp-closing-price` |
| 47 | [국내주식] 기본시세 | 주식당일분봉조회 | v1_국내주식-022 | FHKST03010200 | FHKST03010200 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice` |
| 48 | [국내주식] ELW 시세 | ELW 현재가 시세 | v1_국내주식-014 | FHKEW15010000 | FHKEW15010000 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-elw-price` |
| 49 | [국내주식] ELW 시세 | ELW 신규상장종목 | 국내주식-181 | FHKEW154800C0 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/newly-listed` |
| 50 | [국내주식] ELW 시세 | ELW 투자지표추이(일별) | 국내주식-173 | FHPEW02740200 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/indicator-trend-daily` |
| 51 | [국내주식] ELW 시세 | ELW 민감도 순위 | 국내주식-170 | FHPEW02850000 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/ranking/sensitivity` |
| 52 | [국내주식] ELW 시세 | ELW 기초자산별 종목시세 | 국내주식-186 | FHKEW154101C0 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/udrl-asset-price` |
| 53 | [국내주식] ELW 시세 | ELW 종목검색 | 국내주식-166 | FHKEW15100000 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/cond-search` |
| 54 | [국내주식] ELW 시세 | ELW 변동성 추이(분별) | 국내주식-179 | FHPEW02840300 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/volatility-trend-minute` |
| 55 | [국내주식] ELW 시세 | ELW 변동성추이(체결) | 국내주식-177 | FHPEW02840100 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/volatility-trend-ccnl` |
| 56 | [국내주식] ELW 시세 | ELW 당일급변종목 | 국내주식-171 | FHPEW02870000 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/ranking/quick-change` |
| 57 | [국내주식] ELW 시세 | ELW 투자지표추이(분별) | 국내주식-174 | FHPEW02740300 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/indicator-trend-minute` |
| 58 | [국내주식] ELW 시세 | ELW 기초자산 목록조회 | 국내주식-185 | FHKEW154100C0 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/udrl-asset-list` |
| 59 | [국내주식] ELW 시세 | ELW 변동성 추이(일별) | 국내주식-178 | FHPEW02840200 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/volatility-trend-daily` |
| 60 | [국내주식] ELW 시세 | ELW 거래량순위 | 국내주식-168 | FHPEW02780000 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/ranking/volume-rank` |
| 61 | [국내주식] ELW 시세 | ELW 지표순위 | 국내주식-169 | FHPEW02790000 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/ranking/indicator` |
| 62 | [국내주식] ELW 시세 | ELW 투자지표추이(체결) | 국내주식-172 | FHPEW02740100 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/indicator-trend-ccnl` |
| 63 | [국내주식] ELW 시세 | ELW 상승률순위 | 국내주식-167 | FHPEW02770000 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/ranking/updown-rate` |
| 64 | [국내주식] ELW 시세 | ELW 민감도 추이(일별) | 국내주식-176 | FHPEW02830200 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/sensitivity-trend-daily` |
| 65 | [국내주식] ELW 시세 | ELW 비교대상종목조회 | 국내주식-183 | FHKEW151701C0 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/compare-stocks` |
| 66 | [국내주식] ELW 시세 | ELW 만기예정/만기종목 | 국내주식-184 | FHKEW154700C0 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/expiration-stocks` |
| 67 | [국내주식] ELW 시세 | ELW LP매매추이 | 국내주식-182 | FHPEW03760000 |  | REST GET | `/uapi/elw/v1/quotations/lp-trade-trend` |
| 68 | [국내주식] ELW 시세 | ELW 민감도 추이(체결) | 국내주식-175 | FHPEW02830100 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/sensitivity-trend-ccnl` |
| 69 | [국내주식] ELW 시세 | ELW 변동성 추이(틱) | 국내주식-180 | FHPEW02840400 | 모의투자 미지원 | REST GET | `/uapi/elw/v1/quotations/volatility-trend-tick` |
| 70 | [국내주식] 업종/기타 | 국내주식 예상체결지수 추이 | 국내주식-121 | FHPST01840000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/exp-index-trend` |
| 71 | [국내주식] 업종/기타 | 국내주식업종기간별시세(일/주/월/년) | v1_국내주식-021 | FHKUP03500100 | FHKUP03500100 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice` |
| 72 | [국내주식] 업종/기타 | 국내업종 시간별지수(분) | 국내주식-119 | FHPUP02110200 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-index-timeprice` |
| 73 | [국내주식] 업종/기타 | 국내업종 구분별전체시세 | v1_국내주식-066 | FHPUP02140000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-index-category-price` |
| 74 | [국내주식] 업종/기타 | 업종 분봉조회 | v1_국내주식-045 | FHKUP03500200 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-time-indexchartprice` |
| 75 | [국내주식] 업종/기타 | 국내휴장일조회 | 국내주식-040 | CTCA0903R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/chk-holiday` |
| 76 | [국내주식] 업종/기타 | 국내주식 예상체결 전체지수 | 국내주식-122 | FHKUP11750000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/exp-total-index` |
| 77 | [국내주식] 업종/기타 | 국내업종 현재지수 | v1_국내주식-063 | FHPUP02100000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-index-price` |
| 78 | [국내주식] 업종/기타 | 국내선물 영업일조회 | 국내주식-160 | HHMCM000002C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/market-time` |
| 79 | [국내주식] 업종/기타 | 국내업종 시간별지수(초) | 국내주식-064 | FHPUP02110100 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-index-tickprice` |
| 80 | [국내주식] 업종/기타 | 국내업종 일자별지수 | v1_국내주식-065 | FHPUP02120000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-index-daily-price` |
| 81 | [국내주식] 업종/기타 | 금리 종합(국내채권/금리) | 국내주식-155 | FHPST07020000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/comp-interest` |
| 82 | [국내주식] 업종/기타 | 변동성완화장치(VI) 현황 | v1_국내주식-055 | FHPST01390000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-vi-status` |
| 83 | [국내주식] 업종/기타 | 종합 시황/공시(제목) | 국내주식-141 | FHKST01011800 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/news-title` |
| 84 | [국내주식] 종목정보 | 상품기본조회 | v1_국내주식-029 | CTPF1604R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/search-info` |
| 85 | [국내주식] 종목정보 | 예탁원정보(상장정보일정) | 국내주식-150 | HHKDB669107C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/list-info` |
| 86 | [국내주식] 종목정보 | 예탁원정보(공모주청약일정) | 국내주식-151 | HHKDB669108C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/pub-offer` |
| 87 | [국내주식] 종목정보 | 국내주식 재무비율 | v1_국내주식-080 | FHKST66430300 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/finance/financial-ratio` |
| 88 | [국내주식] 종목정보 | 예탁원정보(자본감소일정) | 국내주식-149 | HHKDB669106C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/cap-dcrs` |
| 89 | [국내주식] 종목정보 | 예탁원정보(무상증자일정) | 국내주식-144 | HHKDB669101C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/bonus-issue` |
| 90 | [국내주식] 종목정보 | 국내주식 증권사별 투자의견 | 국내주식-189 | FHKST663400C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/invest-opbysec` |
| 91 | [국내주식] 종목정보 | 국내주식 당사 신용가능종목 | 국내주식-111 | FHPST04770000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/credit-by-company` |
| 92 | [국내주식] 종목정보 | 예탁원정보(주식매수청구일정) | 국내주식-146 | HHKDB669103C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/purreq` |
| 93 | [국내주식] 종목정보 | 예탁원정보(액면교체일정) | 국내주식-148 | HHKDB669105C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/rev-split` |
| 94 | [국내주식] 종목정보 | 예탁원정보(배당일정) | 국내주식-145 | HHKDB669102C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/dividend` |
| 95 | [국내주식] 종목정보 | 국내주식 종목투자의견 | 국내주식-188 | FHKST663300C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/invest-opinion` |
| 96 | [국내주식] 종목정보 | 국내주식 안정성비율 | v1_국내주식-083 | FHKST66430600 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/finance/stability-ratio` |
| 97 | [국내주식] 종목정보 | 국내주식 수익성비율 | v1_국내주식-081 | FHKST66430400 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/finance/profit-ratio` |
| 98 | [국내주식] 종목정보 | 예탁원정보(실권주일정) | 국내주식-152 | HHKDB669109C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/forfeit` |
| 99 | [국내주식] 종목정보 | 예탁원정보(의무예치일정) | 국내주식-153 | HHKDB669110C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/mand-deposit` |
| 100 | [국내주식] 종목정보 | 국내주식 손익계산서 | v1_국내주식-079 | FHKST66430200 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/finance/income-statement` |
| 101 | [국내주식] 종목정보 | 당사 대주가능 종목 | 국내주식-195 | CTSC2702R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/lendable-by-company` |
| 102 | [국내주식] 종목정보 | 주식기본조회 | v1_국내주식-067 | CTPF1002R | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/search-stock-info` |
| 103 | [국내주식] 종목정보 | 예탁원정보(유상증자일정) | 국내주식-143 | HHKDB669100C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/paidin-capin` |
| 104 | [국내주식] 종목정보 | 예탁원정보(주주총회일정) | 국내주식-154 | HHKDB669111C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/sharehld-meet` |
| 105 | [국내주식] 종목정보 | 국내주식 성장성비율 | v1_국내주식-085 | FHKST66430800 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/finance/growth-ratio` |
| 106 | [국내주식] 종목정보 | 국내주식 대차대조표 | v1_국내주식-078 | FHKST66430100 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/finance/balance-sheet` |
| 107 | [국내주식] 종목정보 | 예탁원정보(합병/분할일정) | 국내주식-147 | HHKDB669104C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ksdinfo/merger-split` |
| 108 | [국내주식] 종목정보 | 국내주식 종목추정실적 | 국내주식-187 | HHKST668300C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/estimate-perform` |
| 109 | [국내주식] 종목정보 | 국내주식 기타주요비율 | v1_국내주식-082 | FHKST66430500 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/finance/other-major-ratios` |
| 110 | [국내주식] 시세분석 | 프로그램매매 종합현황(시간) | 국내주식-114 | FHPPG04600101 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/comp-program-trade-today` |
| 111 | [국내주식] 시세분석 | 국내주식 신용잔고 일별추이 | 국내주식-110 | FHPST04760000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/daily-credit-balance` |
| 112 | [국내주식] 시세분석 | 시장별 투자자매매동향(일별) | 국내주식-075 | FHPTJ04040000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market` |
| 113 | [국내주식] 시세분석 | 국내주식 공매도 일별추이 | 국내주식-134 | FHPST04830000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/daily-short-sale` |
| 114 | [국내주식] 시세분석 | 종목별 투자자매매동향(일별) | 종목별 투자자매매동향(일별) | FHPTJ04160001 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily` |
| 115 | [국내주식] 시세분석 | 종목조건검색 목록조회 | 국내주식-038 | HHKST03900300 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/psearch-title` |
| 116 | [국내주식] 시세분석 | 국내주식 상하한가 포착 | 국내주식-190 | FHKST130000C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/capture-uplowprice` |
| 117 | [국내주식] 시세분석 | 프로그램매매 종합현황(일별) | 국내주식-115 | FHPPG04600001 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/comp-program-trade-daily` |
| 118 | [국내주식] 시세분석 | 종목별 일별 대차거래추이 | 국내주식-135 | HHPST074500C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/daily-loan-trans` |
| 119 | [국내주식] 시세분석 | 종목조건검색조회 | 국내주식-039 | HHKST03900400 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/psearch-result` |
| 120 | [국내주식] 시세분석 | 국내주식 매물대/거래비중 | 국내주식-196 | FHPST01130000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/pbar-tratio` |
| 121 | [국내주식] 시세분석 | 국내기관_외국인 매매종목가집계 | 국내주식-037 | FHPTJ04400000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/foreign-institution-total` |
| 122 | [국내주식] 시세분석 | 관심종목 그룹별 종목조회 | 국내주식-203 | HHKCM113004C6 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/intstock-stocklist-by-group` |
| 123 | [국내주식] 시세분석 | 주식현재가 회원사 종목매매동향 | 국내주식-197 | FHPST04540000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-member-daily` |
| 124 | [국내주식] 시세분석 | 종목별 프로그램매매추이(일별) | 국내주식-113 | FHPPG04650201 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/program-trade-by-stock-daily` |
| 125 | [국내주식] 시세분석 | 관심종목 그룹조회 | 국내주식-204 | HHKCM113004C7 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/intstock-grouplist` |
| 126 | [국내주식] 시세분석 | 종목별 외인기관 추정가집계 | v1_국내주식-046 | HHPTJ04160200 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/investor-trend-estimate` |
| 127 | [국내주식] 시세분석 | 종목별일별매수매도체결량 | v1_국내주식-056 | FHKST03010800 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-trade-volume` |
| 128 | [국내주식] 시세분석 | 국내주식 체결금액별 매매비중 | 국내주식-192 | FHKST111900C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/tradprt-byamt` |
| 129 | [국내주식] 시세분석 | 프로그램매매 투자자매매동향(당일) | 국내주식-116 | HHPPG046600C1 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/investor-program-trade-today` |
| 130 | [국내주식] 시세분석 | 국내 증시자금 종합 | 국내주식-193 | FHKST649100C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/mktfunds` |
| 131 | [국내주식] 시세분석 | 국내주식 예상체결가 추이 | 국내주식-118 | FHPST01810000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/exp-price-trend` |
| 132 | [국내주식] 시세분석 | 회원사 실시간 매매동향(틱) | 국내주식-163 | FHPST04320000 | 모의투자 미지원 | WEBSOCKET GET | `/uapi/domestic-stock/v1/quotations/frgnmem-trade-trend` |
| 133 | [국내주식] 시세분석 | 시장별 투자자매매동향(시세) | v1_국내주식-074 | FHPTJ04030000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/inquire-investor-time-by-market` |
| 134 | [국내주식] 시세분석 | 종목별 프로그램매매추이(체결) | v1_국내주식-044 | FHPPG04650101 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/program-trade-by-stock` |
| 135 | [국내주식] 시세분석 | 외국계 매매종목 가집계 | 국내주식-161 | FHKST644100C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/frgnmem-trade-estimate` |
| 136 | [국내주식] 시세분석 | 국내주식 시간외예상체결등락률 | 국내주식-140 | FHKST11860000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/overtime-exp-trans-fluct` |
| 137 | [국내주식] 시세분석 | 종목별 외국계 순매수추이 | 국내주식-164 | FHKST644400C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/frgnmem-pchs-trend` |
| 138 | [국내주식] 시세분석 | 관심종목(멀티종목) 시세조회 | 국내주식-205 | FHKST11300006 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/intstock-multprice` |
| 139 | [국내주식] 순위분석 | 국내주식 예상체결 상승/하락상위 | v1_국내주식-103 | FHPST01820000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/exp-trans-updown` |
| 140 | [국내주식] 순위분석 | 국내주식 호가잔량 순위 | 국내주식-089 | FHPST01720000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/quote-balance` |
| 141 | [국내주식] 순위분석 | 국내주식 신용잔고 상위 | 국내주식-109 | FHKST17010000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/credit-balance` |
| 142 | [국내주식] 순위분석 | 국내주식 시간외거래량순위 | 국내주식-139 | FHPST02350000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/overtime-volume` |
| 143 | [국내주식] 순위분석 | 국내주식 배당률 상위 | 국내주식-106 | HHKDB13470100 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/dividend-rate` |
| 144 | [국내주식] 순위분석 | 국내주식 시간외잔량 순위 | v1_국내주식-093 | FHPST01760000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/after-hour-balance` |
| 145 | [국내주식] 순위분석 | 국내주식 공매도 상위종목 | 국내주식-133 | FHPST04820000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/short-sale` |
| 146 | [국내주식] 순위분석 | 국내주식 이격도 순위 | v1_국내주식-095 | FHPST01780000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/disparity` |
| 147 | [국내주식] 순위분석 | HTS조회상위20종목 | 국내주식-214 | HHMCM000100C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/hts-top-view` |
| 148 | [국내주식] 순위분석 | 거래량순위 | v1_국내주식-047 | FHPST01710000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/quotations/volume-rank` |
| 149 | [국내주식] 순위분석 | 국내주식 수익자산지표 순위 | v1_국내주식-090 | FHPST01730000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/profit-asset-index` |
| 150 | [국내주식] 순위분석 | 국내주식 신고/신저근접종목 상위 | v1_국내주식-105 | FHPST01870000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/near-new-highlow` |
| 151 | [국내주식] 순위분석 | 국내주식 우선주/괴리율 상위 | v1_국내주식-094 | FHPST01770000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/prefer-disparate-ratio` |
| 152 | [국내주식] 순위분석 | 국내주식 대량체결건수 상위 | 국내주식-107 | FHKST190900C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/bulk-trans-num` |
| 153 | [국내주식] 순위분석 | 국내주식 재무비율 순위 | v1_국내주식-092 | FHPST01750000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/finance-ratio` |
| 154 | [국내주식] 순위분석 | 국내주식 시가총액 상위 | v1_국내주식-091 | FHPST01740000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/market-cap` |
| 155 | [국내주식] 순위분석 | 국내주식 당사매매종목 상위 | v1_국내주식-104 | FHPST01860000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/traded-by-company` |
| 156 | [국내주식] 순위분석 | 국내주식 등락률 순위 | v1_국내주식-088 | FHPST01700000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/fluctuation` |
| 157 | [국내주식] 순위분석 | 국내주식 시장가치 순위 | v1_국내주식-096 | FHPST01790000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/market-value` |
| 158 | [국내주식] 순위분석 | 국내주식 관심종목등록 상위 | v1_국내주식-102 | FHPST01800000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/top-interest-stock` |
| 159 | [국내주식] 순위분석 | 국내주식 체결강도 상위 | v1_국내주식-101 | FHPST01680000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/volume-power` |
| 160 | [국내주식] 순위분석 | 국내주식 시간외등락율순위 | 국내주식-138 | FHPST02340000 | 모의투자 미지원 | REST GET | `/uapi/domestic-stock/v1/ranking/overtime-fluctuation` |
| 161 | [국내주식] 실시간시세 | 국내지수 실시간예상체결 | 실시간-027 | H0UPANC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0UPANC0` |
| 162 | [국내주식] 실시간시세 | 국내주식 장운영정보 (통합) | 국내주식 장운영정보 (통합) | H0UNMKO0 | 모의투자 미지원 | REST POST | `/tryitout/H0UNMKO0` |
| 163 | [국내주식] 실시간시세 | 국내주식 실시간회원사 (NXT) | 국내주식 실시간회원사 (NXT) | H0NXMBC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0NXMBC0` |
| 164 | [국내주식] 실시간시세 | 국내주식 실시간체결통보 | 실시간-005 | H0STCNI0 | H0STCNI9 | WEBSOCKET POST | `/tryitout/H0STCNI0` |
| 165 | [국내주식] 실시간시세 | 국내주식 시간외 실시간예상체결 (KRX) | 실시간-024 | H0STOAC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0STOAC0` |
| 166 | [국내주식] 실시간시세 | 국내주식 시간외 실시간호가 (KRX) | 실시간-025 | H0STOAA0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0STOAA0` |
| 167 | [국내주식] 실시간시세 | 국내주식 실시간프로그램매매 (통합) | 국내주식 실시간프로그램매매 (통합) | H0UNPGM0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0UNPGM0` |
| 168 | [국내주식] 실시간시세 | 국내주식 실시간호가 (통합) | 국내주식 실시간호가 (통합) | H0UNASP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0UNASP0` |
| 169 | [국내주식] 실시간시세 | 국내주식 실시간프로그램매매 (KRX) | 실시간-048 | H0STPGM0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0STPGM0` |
| 170 | [국내주식] 실시간시세 | 국내주식 장운영정보 (KRX) | 실시간-049 | H0STMKO0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0STMKO0` |
| 171 | [국내주식] 실시간시세 | 국내주식 실시간체결가 (KRX) | 실시간-003 | H0STCNT0 | H0STCNT0 | WEBSOCKET POST | `/tryitout/H0STCNT0` |
| 172 | [국내주식] 실시간시세 | 국내지수 실시간프로그램매매 | 실시간-028 | H0UPPGM0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0UPPGM0` |
| 173 | [국내주식] 실시간시세 | 국내주식 실시간회원사 (통합) | 국내주식 실시간회원사 (통합) | H0UNMBC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0UNMBC0` |
| 174 | [국내주식] 실시간시세 | 국내지수 실시간체결 | 실시간-026 | H0UPCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0UPCNT0` |
| 175 | [국내주식] 실시간시세 | 국내주식 실시간예상체결 (KRX) | 실시간-041 | H0STANC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0STANC0` |
| 176 | [국내주식] 실시간시세 | ELW 실시간호가 | 실시간-062 | H0EWASP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0EWASP0` |
| 177 | [국내주식] 실시간시세 | 국내주식 실시간호가 (KRX) | 실시간-004 | H0STASP0 | H0STASP0 | WEBSOCKET POST | `/tryitout/H0STASP0` |
| 178 | [국내주식] 실시간시세 | 국내주식 실시간체결가 (통합) | 국내주식 실시간체결가 (통합) | H0UNCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0UNCNT0` |
| 179 | [국내주식] 실시간시세 | 국내주식 실시간호가 (NXT) | 국내주식 실시간호가 (NXT) | H0NXASP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0NXASP0` |
| 180 | [국내주식] 실시간시세 | 국내주식 실시간프로그램매매 (NXT) | 국내주식 실시간프로그램매매 (NXT) | H0NXPGM0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0NXPGM0` |
| 181 | [국내주식] 실시간시세 | 국내주식 실시간체결가 (NXT) | 국내주식 실시간체결가 (NXT) | H0NXCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0NXCNT0` |
| 182 | [국내주식] 실시간시세 | ELW 실시간체결가 | 실시간-061 | H0EWCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0EWCNT0` |
| 183 | [국내주식] 실시간시세 | ELW 실시간예상체결 | 실시간-063 | H0EWANC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0EWANC0` |
| 184 | [국내주식] 실시간시세 | 국내주식 실시간예상체결 (NXT) | 국내주식 실시간예상체결 (NXT) | H0NXANC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0NXANC0` |
| 185 | [국내주식] 실시간시세 | 국내주식 실시간회원사 (KRX) | 실시간-047 | H0STMBC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0STMBC0` |
| 186 | [국내주식] 실시간시세 | 국내주식 실시간예상체결 (통합) | 국내주식 실시간예상체결 (통합) | H0UNANC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0UNANC0` |
| 187 | [국내주식] 실시간시세 | 국내주식 장운영정보 (NXT) | 국내주식 장운영정보 (NXT) | H0NXMKO0 | 모의투자 미지원 | REST POST | `/tryitout/H0NXMKO0` |
| 188 | [국내주식] 실시간시세 | 국내ETF NAV추이 | 실시간-051 | H0STNAV0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0STNAV0` |
| 189 | [국내주식] 실시간시세 | 국내주식 시간외 실시간체결가 (KRX) | 실시간-042 | H0STOUP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0STOUP0` |
| 190 | [국내선물옵션] 주문/계좌 | (야간)선물옵션 증거금 상세 | 국내선물-024 | (구) JTCE6003R (신) CTFN7107R | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/trading/ngt-margin-detail` |
| 191 | [국내선물옵션] 주문/계좌 | 선물옵션 총자산현황 | v1_국내선물-014 | CTRP6550R | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/trading/inquire-deposit` |
| 192 | [국내선물옵션] 주문/계좌 | 선물옵션기간약정수수료일별 | v1_국내선물-017 | CTFO6119R | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/trading/inquire-daily-amount-fee` |
| 193 | [국내선물옵션] 주문/계좌 | (야간)선물옵션 잔고현황 | 국내선물-010 | (구) JTCE6001R (신) CTFN6118R | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/trading/inquire-ngt-balance` |
| 194 | [국내선물옵션] 주문/계좌 | 선물옵션 잔고현황 | v1_국내선물-004 | CTFO6118R | VTFO6118R | REST GET | `/uapi/domestic-futureoption/v1/trading/inquire-balance` |
| 195 | [국내선물옵션] 주문/계좌 | 선물옵션 주문 | v1_국내선물-001 | (주간 매수/매도) TTTO1101U (야간 매수/매도) (구) JTCE1001U (신) STTN1101U | (주간 매수/매도) VTTO1101U (야간은 모의투자 미제공) | REST POST | `/uapi/domestic-futureoption/v1/trading/order` |
| 196 | [국내선물옵션] 주문/계좌 | 선물옵션 잔고평가손익내역 | v1_국내선물-015 | CTFO6159R | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/trading/inquire-balance-valuation-pl` |
| 197 | [국내선물옵션] 주문/계좌 | 선물옵션 증거금률 | 선물옵션 증거금률 | TTTO6032R | 미지원 | REST GET | `/uapi/domestic-futureoption/v1/quotations/margin-rate` |
| 198 | [국내선물옵션] 주문/계좌 | 선물옵션 정정취소주문 | v1_국내선물-002 | (주간 정정/취소) TTTO1103U (야간 정정/취소) (구) JTCE1002U (신) STTN1103U | (주간 정정/취소) VTTO1103U (야간은 모의투자 미제공) | REST POST | `/uapi/domestic-futureoption/v1/trading/order-rvsecncl` |
| 199 | [국내선물옵션] 주문/계좌 | 선물옵션 주문체결내역조회 | v1_국내선물-003 | TTTO5201R | VTTO5201R | REST GET | `/uapi/domestic-futureoption/v1/trading/inquire-ccnl` |
| 200 | [국내선물옵션] 주문/계좌 | (야간)선물옵션 주문체결 내역조회 | 국내선물-009 | (구) JTCE5005R (신) STTN5201R | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/trading/inquire-ngt-ccnl` |
| 201 | [국내선물옵션] 주문/계좌 | (야간)선물옵션 주문가능 조회 | 국내선물-011 | (구) JTCE1004R (신) STTN5105R | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/trading/inquire-psbl-ngt-order` |
| 202 | [국내선물옵션] 주문/계좌 | 선물옵션 잔고정산손익내역 | v1_국내선물-013 | CTFO6117R | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/trading/inquire-balance-settlement-pl` |
| 203 | [국내선물옵션] 주문/계좌 | 선물옵션 주문가능 | v1_국내선물-005 | TTTO5105R | VTTO5105R | REST GET | `/uapi/domestic-futureoption/v1/trading/inquire-psbl-order` |
| 204 | [국내선물옵션] 주문/계좌 | 선물옵션 기준일체결내역 | v1_국내선물-016 | CTFO5139R | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/trading/inquire-ccnl-bstime` |
| 205 | [국내선물옵션] 기본시세 | 선물옵션 시세 | v1_국내선물-006 | FHMIF10000000 | FHMIF10000000 | REST GET | `/uapi/domestic-futureoption/v1/quotations/inquire-price` |
| 206 | [국내선물옵션] 기본시세 | 국내선물 기초자산 시세 | 국내선물-021 | FHPIF05030000 | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/quotations/display-board-top` |
| 207 | [국내선물옵션] 기본시세 | 선물옵션 일중예상체결추이 | 국내선물-018 | FHPIF05110100 | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/quotations/exp-price-trend` |
| 208 | [국내선물옵션] 기본시세 | 선물옵션기간별시세(일/주/월/년) | v1_국내선물-008 | FHKIF03020100 | FHKIF03020100 | REST GET | `/uapi/domestic-futureoption/v1/quotations/inquire-daily-fuopchartprice` |
| 209 | [국내선물옵션] 기본시세 | 국내옵션전광판_선물 | 국내선물-023 | FHPIF05030200 | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/quotations/display-board-futures` |
| 210 | [국내선물옵션] 기본시세 | 선물옵션 분봉조회 | v1_국내선물-012 | FHKIF03020200 | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/quotations/inquire-time-fuopchartprice` |
| 211 | [국내선물옵션] 기본시세 | 국내옵션전광판_옵션월물리스트 | 국내선물-020 | FHPIO056104C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/quotations/display-board-option-list` |
| 212 | [국내선물옵션] 기본시세 | 선물옵션 시세호가 | v1_국내선물-007 | FHMIF10010000 | FHMIF10010000 | REST GET | `/uapi/domestic-futureoption/v1/quotations/inquire-asking-price` |
| 213 | [국내선물옵션] 기본시세 | 국내옵션전광판_콜풋 | 국내선물-022 | FHPIF05030100 | 모의투자 미지원 | REST GET | `/uapi/domestic-futureoption/v1/quotations/display-board-callput` |
| 214 | [국내선물옵션] 실시간시세 | 주식옵션 실시간호가 | 실시간-045 | H0ZOASP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0ZOASP0` |
| 215 | [국내선물옵션] 실시간시세 | 선물옵션 실시간체결통보 | 실시간-012 | H0IFCNI0 | H0IFCNI9 | WEBSOCKET POST | `/tryitout/H0IFCNI0` |
| 216 | [국내선물옵션] 실시간시세 | KRX야간선물 실시간종목체결 | 실시간-064 | H0MFCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0MFCNT0` |
| 217 | [국내선물옵션] 실시간시세 | KRX야간선물 실시간호가 | 실시간-065 | H0MFASP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0MFASP0` |
| 218 | [국내선물옵션] 실시간시세 | KRX야간옵션 실시간체결가 | 실시간-032 | H0EUCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0EUCNT0` |
| 219 | [국내선물옵션] 실시간시세 | KRX야간옵션실시간예상체결 | 실시간-034 | H0EUANC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0EUANC0` |
| 220 | [국내선물옵션] 실시간시세 | 지수선물 실시간체결가 | 실시간-010 | H0IFCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0IFCNT0` |
| 221 | [국내선물옵션] 실시간시세 | 주식선물 실시간예상체결 | 실시간-031 | H0ZFANC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0ZFANC0` |
| 222 | [국내선물옵션] 실시간시세 | KRX야간옵션실시간체결통보 | 실시간-067 | H0MFCNI0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0EUCNI0` |
| 223 | [국내선물옵션] 실시간시세 | KRX야간선물 실시간체결통보 | 실시간-066 | H0MFCNI0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0MFCNI0` |
| 224 | [국내선물옵션] 실시간시세 | 상품선물 실시간체결가 | 실시간-022 | H0CFCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0CFCNT0` |
| 225 | [국내선물옵션] 실시간시세 | 지수선물 실시간호가 | 실시간-011 | H0IFASP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0IFASP0` |
| 226 | [국내선물옵션] 실시간시세 | 지수옵션  실시간체결가 | 실시간-014 | H0IOCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0IOCNT0` |
| 227 | [국내선물옵션] 실시간시세 | KRX야간옵션 실시간호가 | 실시간-033 | H0EUASP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0EUASP0` |
| 228 | [국내선물옵션] 실시간시세 | 상품선물 실시간호가 | 실시간-023 | H0CFASP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0CFASP0` |
| 229 | [국내선물옵션] 실시간시세 | 주식옵션 실시간예상체결 | 실시간-046 | H0ZOANC0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0ZOANC0` |
| 230 | [국내선물옵션] 실시간시세 | 주식선물 실시간호가 | 실시간-030 | H0ZFASP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0ZFASP0` |
| 231 | [국내선물옵션] 실시간시세 | 주식옵션 실시간체결가 | 실시간-044 | H0ZOCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0ZOCNT0` |
| 232 | [국내선물옵션] 실시간시세 | 지수옵션 실시간호가 | 실시간-015 | H0IOASP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0IOASP0` |
| 233 | [국내선물옵션] 실시간시세 | 주식선물 실시간체결가 | 실시간-029 | H0ZFCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0ZFCNT0` |
| 234 | [해외주식] 주문/계좌 | 해외주식 잔고 | v1_해외주식-006 | TTTS3012R | VTTS3012R | REST GET | `/uapi/overseas-stock/v1/trading/inquire-balance` |
| 235 | [해외주식] 주문/계좌 | 해외주식 체결기준현재잔고 | v1_해외주식-008 | CTRP6504R | VTRP6504R | REST GET | `/uapi/overseas-stock/v1/trading/inquire-present-balance` |
| 236 | [해외주식] 주문/계좌 | 해외주식 지정가체결내역조회 | 해외주식-070 | TTTS6059R | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/trading/inquire-algo-ccnl` |
| 237 | [해외주식] 주문/계좌 | 해외주식 기간손익 | v1_해외주식-032 | TTTS3039R | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/trading/inquire-period-profit` |
| 238 | [해외주식] 주문/계좌 | 해외주식 매수가능금액조회 | v1_해외주식-014 | TTTS3007R | VTTS3007R | REST GET | `/uapi/overseas-stock/v1/trading/inquire-psamount` |
| 239 | [해외주식] 주문/계좌 | 해외주식 정정취소주문 | v1_해외주식-003 | (미국 정정·취소) TTTT1004U (아시아 국가 하단 규격서 참고) | (미국 정정·취소) VTTT1004U (아시아 국가 하단 규격서 참고) | REST POST | `/uapi/overseas-stock/v1/trading/order-rvsecncl` |
| 240 | [해외주식] 주문/계좌 | 해외주식 예약주문접수 | v1_해외주식-002 | (미국예약매수) TTTT3014U  (미국예약매도) TTTT3016U   (중국/홍콩/일본/베트남 예약주문) TTTS3013U | (미국예약매수) VTTT3014U  (미국예약매도) VTTT3016U   (중국/홍콩/일본/베트남 예약주문) VTTS3013U | REST POST | `/uapi/overseas-stock/v1/trading/order-resv` |
| 241 | [해외주식] 주문/계좌 | 해외주식 미체결내역 | v1_해외주식-005 | TTTS3018R | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/trading/inquire-nccs` |
| 242 | [해외주식] 주문/계좌 | 해외주식 미국주간정정취소 | v1_해외주식-027 | TTTS6038U | 모의투자 미지원 | REST POST | `/uapi/overseas-stock/v1/trading/daytime-order-rvsecncl` |
| 243 | [해외주식] 주문/계좌 | 해외주식 주문체결내역 | v1_해외주식-007 | TTTS3035R | VTTS3035R | REST GET | `/uapi/overseas-stock/v1/trading/inquire-ccnl` |
| 244 | [해외주식] 주문/계좌 | 해외주식 결제기준잔고 | 해외주식-064 | CTRP6010R | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/trading/inquire-paymt-stdr-balance` |
| 245 | [해외주식] 주문/계좌 | 해외주식 일별거래내역 | 해외주식-063 | CTOS4001R | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/trading/inquire-period-trans` |
| 246 | [해외주식] 주문/계좌 | 해외주식 미국주간주문 | v1_해외주식-026 | (주간매수) TTTS6036U (주간매도) TTTS6037U | 모의투자 미지원 | REST POST | `/uapi/overseas-stock/v1/trading/daytime-order` |
| 247 | [해외주식] 주문/계좌 | 해외주식 예약주문조회 | v1_해외주식-013 | (미국) TTTT3039R (일본/중국/홍콩/베트남) TTTS3014R | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/trading/order-resv-list` |
| 248 | [해외주식] 주문/계좌 | 해외주식 주문 | v1_해외주식-001 | (미국매수) TTTT1002U  (미국매도) TTTT1006U (아시아 국가 하단 규격서 참고) | (미국매수) VTTT1002U  (미국매도) VTTT1001U  (아시아 국가 하단 규격서 참고) | REST POST | `/uapi/overseas-stock/v1/trading/order` |
| 249 | [해외주식] 주문/계좌 | 해외주식 예약주문접수취소 | v1_해외주식-004 | (미국 예약주문 취소접수) TTTT3017U (아시아국가 미제공) | (미국 예약주문 취소접수) VTTT3017U (아시아국가 미제공) | REST POST | `/uapi/overseas-stock/v1/trading/order-resv-ccnl` |
| 250 | [해외주식] 주문/계좌 | 해외주식 지정가주문번호조회 | 해외주식-071 | TTTS6058R | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/trading/algo-ordno` |
| 251 | [해외주식] 주문/계좌 | 해외증거금 통화별조회 | 해외주식-035 | TTTC2101R | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/trading/foreign-margin` |
| 252 | [해외주식] 기본시세 | 해외주식 체결추이 | 해외주식-037 | HHDFS76200300 | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/inquire-ccnl` |
| 253 | [해외주식] 기본시세 | 해외주식 기간별시세 | v1_해외주식-010 | HHDFS76240000 | HHDFS76240000 | REST GET | `/uapi/overseas-price/v1/quotations/dailyprice` |
| 254 | [해외주식] 기본시세 | 해외결제일자조회 | 해외주식-017 | CTOS5011R | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/quotations/countries-holiday` |
| 255 | [해외주식] 기본시세 | 해외주식 현재체결가 | v1_해외주식-009 | HHDFS00000300 | HHDFS00000300 | REST GET | `/uapi/overseas-price/v1/quotations/price` |
| 256 | [해외주식] 기본시세 | 해외주식 복수종목 시세조회 | 해외주식 복수종목 시세조회 | HHDFS76220000 | 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/multprice` |
| 257 | [해외주식] 기본시세 | 해외주식조건검색 | v1_해외주식-015 | HHDFS76410000 | HHDFS76410000 | REST GET | `/uapi/overseas-price/v1/quotations/inquire-search` |
| 258 | [해외주식] 기본시세 | 해외주식 상품기본정보 | v1_해외주식-034 | CTPF1702R | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/search-info` |
| 259 | [해외주식] 기본시세 | 해외지수분봉조회 | v1_해외주식-031 | FHKST03030200 | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/inquire-time-indexchartprice` |
| 260 | [해외주식] 기본시세 | 해외주식분봉조회 | v1_해외주식-030 | HHDFS76950200 | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice` |
| 261 | [해외주식] 기본시세 | 해외주식 현재가상세 | v1_해외주식-029 | HHDFS76200200 | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/price-detail` |
| 262 | [해외주식] 기본시세 | 해외주식 업종별코드조회 | 해외주식-049 | HHDFS76370100 | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/industry-price` |
| 263 | [해외주식] 기본시세 | 해외주식 종목/지수/환율기간별시세(일/주/월/년) | v1_해외주식-012 | FHKST03030100 | FHKST03030100 | REST GET | `/uapi/overseas-price/v1/quotations/inquire-daily-chartprice` |
| 264 | [해외주식] 기본시세 | 해외주식 업종별시세 | 해외주식-048 | HHDFS76370000 | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/industry-theme` |
| 265 | [해외주식] 기본시세 | 해외주식 현재가 호가 | 해외주식-033 | HHDFS76200100 | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/inquire-asking-price` |
| 266 | [해외주식] 시세분석 | 해외주식 거래증가율순위 | 해외주식-045 | HHDFS76330000 | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/ranking/trade-growth` |
| 267 | [해외주식] 시세분석 | 해외주식 기간별권리조회 | 해외주식-052 | CTRGT011R | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/period-rights` |
| 268 | [해외주식] 시세분석 | 해외주식 가격급등락 | 해외주식-038 | HHDFS76260000 | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/ranking/price-fluct` |
| 269 | [해외주식] 시세분석 | 해외주식 거래대금순위 | 해외주식-044 | HHDFS76320010 | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/ranking/trade-pbmn` |
| 270 | [해외주식] 시세분석 | 해외주식 거래량급증 | 해외주식-039 | HHDFS76270000 | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/ranking/volume-surge` |
| 271 | [해외주식] 시세분석 | 해외주식 신고/신저가 | 해외주식-042 | HHDFS76300000 | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/ranking/new-highlow` |
| 272 | [해외주식] 시세분석 | 해외주식 매수체결강도상위 | 해외주식-040 | HHDFS76280000 | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/ranking/volume-power` |
| 273 | [해외주식] 시세분석 | 해외주식 거래회전율순위 | 해외주식-046 | HHDFS76340000 | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/ranking/trade-turnover` |
| 274 | [해외주식] 시세분석 | 해외뉴스종합(제목) | 해외주식-053 | HHPSTH60100C1 | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/news-title` |
| 275 | [해외주식] 시세분석 | 당사 해외주식담보대출 가능 종목 | 해외주식-051 | CTLN4050R | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/colable-by-company` |
| 276 | [해외주식] 시세분석 | 해외주식 시가총액순위 | 해외주식-047 | HHDFS76350100 | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/ranking/market-cap` |
| 277 | [해외주식] 시세분석 | 해외속보(제목) | 해외주식-055 | FHKST01011801 | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/brknews-title` |
| 278 | [해외주식] 시세분석 | 해외주식 상승율/하락율 | 해외주식-041 | HHDFS76290000 | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/ranking/updown-rate` |
| 279 | [해외주식] 시세분석 | 해외주식 권리종합 | 해외주식-050 | HHDFS78330900 | 모의투자 미지원 | REST GET | `/uapi/overseas-price/v1/quotations/rights-by-ice` |
| 280 | [해외주식] 시세분석 | 해외주식 거래량순위 | 해외주식-043 | HHDFS76310010 | 모의투자 미지원 | REST GET | `/uapi/overseas-stock/v1/ranking/trade-vol` |
| 281 | [해외주식] 실시간시세 | 해외주식 실시간호가 | 실시간-021 | HDFSASP0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/HDFSASP0` |
| 282 | [해외주식] 실시간시세 | 해외주식 지연호가(아시아) | 실시간-008 | HDFSASP1 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/HDFSASP1` |
| 283 | [해외주식] 실시간시세 | 해외주식 실시간지연체결가 | 실시간-007 | HDFSCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/HDFSCNT0` |
| 284 | [해외주식] 실시간시세 | 해외주식 실시간체결통보 | 실시간-009 | H0GSCNI0 | H0GSCNI9 | WEBSOCKET POST | `/tryitout/H0GSCNI0` |
| 285 | [해외선물옵션] 주문/계좌 | 해외선물옵션 주문 | v1_해외선물-001 | OTFM3001U | 모의투자 미지원 | REST POST | `/uapi/overseas-futureoption/v1/trading/order` |
| 286 | [해외선물옵션] 주문/계좌 | 해외선물옵션 정정취소주문 | v1_해외선물-002, 003 | (정정) OTFM3002U (취소) OTFM3003U | 모의투자 미지원 | REST POST | `/uapi/overseas-futureoption/v1/trading/order-rvsecncl` |
| 287 | [해외선물옵션] 주문/계좌 | 해외선물옵션 당일주문내역조회 | v1_해외선물-004 | OTFM3116R | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/trading/inquire-ccld` |
| 288 | [해외선물옵션] 주문/계좌 | 해외선물옵션 미결제내역조회(잔고) | v1_해외선물-005 | OTFM1412R | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/trading/inquire-unpd` |
| 289 | [해외선물옵션] 주문/계좌 | 해외선물옵션 주문가능조회 | v1_해외선물-006 | OTFM3304R | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/trading/inquire-psamount` |
| 290 | [해외선물옵션] 주문/계좌 | 해외선물옵션 기간계좌손익 일별 | 해외선물-010 | OTFM3118R | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/trading/inquire-period-ccld` |
| 291 | [해외선물옵션] 주문/계좌 | 해외선물옵션 일별 체결내역 | 해외선물-011 | OTFM3122R | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/trading/inquire-daily-ccld` |
| 292 | [해외선물옵션] 주문/계좌 | 해외선물옵션 예수금현황 | 해외선물-012 | OTFM1411R | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/trading/inquire-deposit` |
| 293 | [해외선물옵션] 주문/계좌 | 해외선물옵션 일별 주문내역 | 해외선물-013 | OTFM3120R | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/trading/inquire-daily-order` |
| 294 | [해외선물옵션] 주문/계좌 | 해외선물옵션 기간계좌거래내역 | 해외선물-014 | OTFM3114R | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/trading/inquire-period-trans` |
| 295 | [해외선물옵션] 주문/계좌 | 해외선물옵션 증거금상세 | 해외선물-032 | OTFM3115R | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/trading/margin-detail` |
| 296 | [해외선물옵션] 기본시세 | 해외선물종목현재가 | v1_해외선물-009 | HHDFC55010000 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/inquire-price` |
| 297 | [해외선물옵션] 기본시세 | 해외선물종목상세 | v1_해외선물-008 | HHDFC55010100 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/stock-detail` |
| 298 | [해외선물옵션] 기본시세 | 해외선물 호가 | 해외선물-031 | HHDFC86000000 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/inquire-asking-price` |
| 299 | [해외선물옵션] 기본시세 | 해외선물 분봉조회 | 해외선물-016 | HHDFC55020400 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/inquire-time-futurechartprice` |
| 300 | [해외선물옵션] 기본시세 | 해외선물 체결추이(틱) | 해외선물-019 | HHDFC55020200 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/tick-ccnl` |
| 301 | [해외선물옵션] 기본시세 | 해외선물 체결추이(주간) | 해외선물-017 | HHDFC55020000 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/weekly-ccnl` |
| 302 | [해외선물옵션] 기본시세 | 해외선물 체결추이(일간) | 해외선물-018 | HHDFC55020100 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/daily-ccnl` |
| 303 | [해외선물옵션] 기본시세 | 해외선물 체결추이(월간) | 해외선물-020 | HHDFC55020300 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/monthly-ccnl` |
| 304 | [해외선물옵션] 기본시세 | 해외선물 상품기본정보 | 해외선물-023 | HHDFC55200000 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/search-contract-detail` |
| 305 | [해외선물옵션] 기본시세 | 해외선물 미결제추이 | 해외선물-029 | HHDDB95030000 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/investor-unpd-trend` |
| 306 | [해외선물옵션] 기본시세 | 해외옵션종목현재가 | 해외선물-035 | HHDFO55010000 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/opt-price` |
| 307 | [해외선물옵션] 기본시세 | 해외옵션종목상세 | 해외선물-034 | HHDFO55010100 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/opt-detail` |
| 308 | [해외선물옵션] 기본시세 | 해외옵션 호가 | 해외선물-033 | HHDFO86000000 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/opt-asking-price` |
| 309 | [해외선물옵션] 기본시세 | 해외옵션 분봉조회 | 해외선물-040 | HHDFO55020400 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/inquire-time-optchartprice` |
| 310 | [해외선물옵션] 기본시세 | 해외옵션 체결추이(틱) | 해외선물-038 | HHDFO55020200 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/opt-tick-ccnl` |
| 311 | [해외선물옵션] 기본시세 | 해외옵션 체결추이(일간) | 해외선물-037 | HHDFO55020100 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/opt-daily-ccnl` |
| 312 | [해외선물옵션] 기본시세 | 해외옵션 체결추이(주간) | 해외선물-036 | HHDFO55020000 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/opt-weekly-ccnl` |
| 313 | [해외선물옵션] 기본시세 | 해외옵션 체결추이(월간) | 해외선물-039 | HHDFO55020300 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/opt-monthly-ccnl` |
| 314 | [해외선물옵션] 기본시세 | 해외옵션 상품기본정보 | 해외선물-041 | HHDFO55200000 | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/search-opt-detail` |
| 315 | [해외선물옵션] 기본시세 | 해외선물옵션 장운영시간 | 해외선물-030 | OTFM2229R | 모의투자 미지원 | REST GET | `/uapi/overseas-futureoption/v1/quotations/market-time` |
| 316 | [해외선물옵션]실시간시세 | 해외선물옵션 실시간체결가 | 실시간-017 | HDFFF020 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/HDFFF020` |
| 317 | [해외선물옵션]실시간시세 | 해외선물옵션 실시간호가 | 실시간-018 | HDFFF010 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/HDFFF010` |
| 318 | [해외선물옵션]실시간시세 | 해외선물옵션 실시간주문내역통보 | 실시간-019 | HDFFF1C0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/HDFFF1C0` |
| 319 | [해외선물옵션]실시간시세 | 해외선물옵션 실시간체결내역통보 | 실시간-020 | HDFFF2C0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/HDFFF2C0` |
| 320 | [장내채권] 주문/계좌 | 장내채권 매수주문 | 국내주식-124 | TTTC0952U | 모의투자 미지원 | REST POST | `/uapi/domestic-bond/v1/trading/buy` |
| 321 | [장내채권] 주문/계좌 | 장내채권 매도주문 | 국내주식-123 | TTTC0958U | 모의투자 미지원 | REST POST | `/uapi/domestic-bond/v1/trading/sell` |
| 322 | [장내채권] 주문/계좌 | 장내채권 정정취소주문 | 국내주식-125 | TTTC0953U | 모의투자 미지원 | REST POST | `/uapi/domestic-bond/v1/trading/order-rvsecncl` |
| 323 | [장내채권] 주문/계좌 | 채권정정취소가능주문조회 | 국내주식-126 | CTSC8035R | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/trading/inquire-psbl-rvsecncl` |
| 324 | [장내채권] 주문/계좌 | 장내채권 주문체결내역 | 국내주식-127 | CTSC8013R | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/trading/inquire-daily-ccld` |
| 325 | [장내채권] 주문/계좌 | 장내채권 잔고조회 | 국내주식-198 | CTSC8407R | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/trading/inquire-balance` |
| 326 | [장내채권] 주문/계좌 | 장내채권 매수가능조회 | 국내주식-199 | TTTC8910R | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/trading/inquire-psbl-order` |
| 327 | [장내채권] 기본시세 | 장내채권현재가(호가) | 국내주식-132 | FHKBJ773401C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/quotations/inquire-asking-price` |
| 328 | [장내채권] 기본시세 | 장내채권현재가(시세) | 국내주식-200 | FHKBJ773400C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/quotations/inquire-price` |
| 329 | [장내채권] 기본시세 | 장내채권현재가(체결) | 국내주식-201 | FHKBJ773403C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/quotations/inquire-ccnl` |
| 330 | [장내채권] 기본시세 | 장내채권현재가(일별) | 국내주식-202 | FHKBJ773404C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/quotations/inquire-daily-price` |
| 331 | [장내채권] 기본시세 | 장내채권 기간별시세(일) | 국내주식-159 | FHKBJ773701C0 | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/quotations/inquire-daily-itemchartprice` |
| 332 | [장내채권] 기본시세 | 장내채권 평균단가조회 | 국내주식-158 | CTPF2005R | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/quotations/avg-unit` |
| 333 | [장내채권] 기본시세 | 장내채권 발행정보 | 국내주식-156 | CTPF1101R | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/quotations/issue-info` |
| 334 | [장내채권] 기본시세 | 장내채권 기본조회 | 국내주식-129 | CTPF1114R | 모의투자 미지원 | REST GET | `/uapi/domestic-bond/v1/quotations/search-bond-info` |
| 335 | [장내채권] 실시간시세 | 일반채권 실시간체결가 | 실시간-052 | H0BJCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0BJCNT0` |
| 336 | [장내채권] 실시간시세 | 일반채권 실시간호가 | 실시간-053 | H0BJCNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0BJASP0` |
| 337 | [장내채권] 실시간시세 | 채권지수 실시간체결가 | 실시간-060 | H0BICNT0 | 모의투자 미지원 | WEBSOCKET POST | `/tryitout/H0BICNT0` |

---

## 도메인

| 환경 | URL |
| --- | --- |
| 실전 | `https://openapi.koreainvestment.com:9443` |
| 모의 | `https://openapivts.koreainvestment.com:29443` |

> 모의투자 미지원 API는 카테고리별 문서의 `모의 TR_ID` 필드에 명시됨.
