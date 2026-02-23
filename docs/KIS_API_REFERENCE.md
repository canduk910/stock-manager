[필수 전제사항 - 모든 작업에 공통 적용]

1. 프로젝트 루트에 첨부된 wrapper.py 파일이 존재한다.
   이 파일은 한국투자증권 OpenAPI Python wrapper로, KoreaInvestment 클래스를 포함한다.

2. ❗ wrapper.py 수정 정책: 자유롭게 변경 가능
   - 필요한 새 API 메서드 추가, 기존 메서드 개선, 버그 수정 등 자유롭게 변경한다.
   - wrapper.py에 없는 KIS API 기능(재무비율, 순위분석, 조건검색 등)이 필요하면
     wrapper.py에 직접 새 메서드를 추가하는 것을 우선으로 고려한다.
   - wrapper.py에 넣기 애매한 보조 로직(재무지표 계산 등)은 services/ 하위 파일로 분리한다.

3. KIS API 공식문서 참조:
   프로젝트 루트에 첨부된 「한국투자증권_오픈API_전체문서.xlsx」(337개 시트) 파일을
   반드시 참조하여 API 호출 코드를 작성한다.
   - 각 시트는 하나의 API 레이아웃을 담고 있음
   - 필수 확인사항: Element(항목명), Type(데이터 타입), Length(길이),
     Required(필수 여부), Description(설명)
   - 특히 POST API의 Body key값은 반드시 대문자 ("CANO", "ACNT_PRDT_CD" 등)
   - 금액/수량 등 수치데이터가 String으로 정의된 경우 타입 엄격 준수

4. wrapper.py의 KoreaInvestment 클래스 기존 메서드:
   - fetch_symbols() → KOSPI+KOSDAQ 전체 종목 DataFrame
     · 활용 컬럼: 단축코드, 한글명, 그룹코드, 시장, 매출액, 영업이익,
       당기순이익, ROE, 시가총액, 상장일자, 기준년월
   - fetch_kospi_symbols() → 코스피 종목 마스터 DataFrame (시가총액규모, 업종분류 포함)
   - fetch_kosdaq_symbols() → 코스닥 종목 마스터 DataFrame
   - fetch_price(symbol) → 현재가 시세 dict
     · 주요 필드: stck_prpr, prdy_vrss, prdy_ctrt, hts_avls, per, pbr,
       stck_dryy_hgpr, stck_dryy_lwpr, lstn_stcn
   - fetch_ohlcv(symbol, timeframe, start, end) → 기간별 시세 (최대 100건/회)
   - fetch_ohlcv_domestic(symbol, timeframe, start, end) → 국내 일/주/월/년 OHLCV
   - fetch_today_1m_ohlcv(symbol) → 당일 1분봉

5. wrapper.py에 추가해야 할 KIS API 메서드:
   아래 API들은 wrapper.py에 아직 구현되지 않았으나 프로젝트에 필요하다.
   KIS API 문서의 해당 시트를 참조하여 wrapper.py에 새 메서드로 추가할 것:

   [재무제표 계열] - 실전전용, 모의투자 미지원
   - 국내주식 손익계산서: GET /uapi/domestic-stock/v1/finance/income-statement
     TR_ID: FHKST66430200 | 시트: 「국내주식 손익계산서」
   - 국내주식 대차대조표: GET /uapi/domestic-stock/v1/finance/balance-sheet
     TR_ID: FHKST66430100 | 시트: 「국내주식 대차대조표」
   - 국내주식 재무비율: GET /uapi/domestic-stock/v1/finance/financial-ratio
     TR_ID: FHKST66430300 | 시트: 「국내주식 재무비율」
   - 국내주식 수익성비율: GET /uapi/domestic-stock/v1/finance/profit-ratio
     TR_ID: FHKST66430400 | 시트: 「국내주식 수익성비율」
   - 국내주식 성장성비율: GET /uapi/domestic-stock/v1/finance/growth-ratio
     TR_ID: FHKST66430800 | 시트: 「국내주식 성장성비율」
   - 국내주식 안정성비율: GET /uapi/domestic-stock/v1/finance/stability-ratio
     TR_ID: FHKST66430600 | 시트: 「국내주식 안정성비율」
   - 국내주식 기타주요비율: GET /uapi/domestic-stock/v1/finance/other-major-ratios
     TR_ID: FHKST66430500 | 시트: 「국내주식 기타주요비율」
   - 국내주식 종목추정실적: GET /uapi/domestic-stock/v1/quotations/estimate-perform
     TR_ID: HHKST668300C0 | 시트: 「국내주식 종목추정실적」

   [순위분석 계열]
   - 거래량순위: GET /uapi/domestic-stock/v1/quotations/volume-rank
     TR_ID: FHPST01710000 | 시트: 「거래량순위」 | 최대 30건
   - 국내주식 시가총액 상위: GET /uapi/domestic-stock/v1/ranking/market-cap
     TR_ID: FHPST01740000 | 시트: 「국내주식 시가총액 상위」
   - 국내주식 등락률 순위: GET /uapi/domestic-stock/v1/ranking/fluctuation
     TR_ID: FHPST01700000 | 시트: 「국내주식 등락률 순위」
   - 국내주식 시장가치 순위: GET /uapi/domestic-stock/v1/ranking/market-value
     TR_ID: FHPST01790000 | 시트: 「국내주식 시장가치 순위」

   [종목정보/검색 계열]
   - 주식기본조회: GET /uapi/domestic-stock/v1/quotations/search-stock-info
     TR_ID: CTPF1002R | 시트: 「주식기본조회」
   - 종목조건검색 목록조회: GET /uapi/domestic-stock/v1/quotations/psearch-title
     TR_ID: HHKST03900300 | 시트: 「종목조건검색 목록조회」
   - 종목조건검색조회: GET /uapi/domestic-stock/v1/quotations/psearch-result
     TR_ID: HHKST03900400 | 시트: 「종목조건검색조회」

   [관심종목 계열] - HTS에서 등록한 관심종목 연동
   - 관심종목 그룹조회: GET .../intstock-grouplist
     TR_ID: HHKCM113004C7
   - 관심종목 그룹별 종목조회: GET .../intstock-stocklist-by-group
     TR_ID: HHKCM113004C6
   - 관심종목(멀티종목) 시세조회: GET .../intstock-multprice
     TR_ID: FHKST11300006 | 한 번에 최대 30종목

6. 한국투자증권 API 인증 정보는 환경변수에서 읽어온다:
   - KIS_API_KEY, KIS_API_SECRET, KIS_ACC_NO
   - OPENDART_API_KEY (OpenDart 공시 조회용)

7. KoreaInvestment 인스턴스 생성 패턴:
   from wrapper import KoreaInvestment
   broker = KoreaInvestment(
       api_key=os.environ['KIS_API_KEY'],
       api_secret=os.environ['KIS_API_SECRET'],
       acc_no=os.environ['KIS_ACC_NO'],
       exchange='서울'
   )

8. wrapper.py에 새 메서드 추가 시 규칙:
   - 기존 메서드 네이밍 컨벤션(fetch_xxx)을 따를 것
   - KIS API 문서 엑셀의 해당 시트를 열어 Element/Type/Required/Length를
     확인한 후 코드 작성 (특히 Query Parameter와 Response Body 필드)
   - 실전용 TR_ID와 모의투자용 TR_ID를 모두 지원
   - 응답의 rt_cd != '0'이면 실패 처리, msg1/msg_cd 로깅

9. 기술 스택 (웹 기반):
   - 백엔드: Python 3.10+ / FastAPI + Uvicorn
   - 프론트엔드: React 19 + Vite + Tailwind CSS v4
   - 라우팅: react-router-dom
   - 차트: Recharts (React 네이티브 차트 라이브러리)
   - HTTP: 네이티브 fetch (프론트엔드), requests (백엔드/wrapper.py)
   - 개발: Vite dev server → FastAPI 프록시 (/api → localhost:8000)