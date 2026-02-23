import wrapper
import pprint

from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

APP_KEY = os.getenv("TEST_KIS_APP_KEY")
APP_SECRET = os.getenv("TEST_KIS_APP_SECRET")
ACNT_NO = os.getenv("TEST_KIS_ACNT_NO")  # 계좌번호 앞 8자리
TEST_KIS_ACNT_PRDT_CD = os.getenv("TEST_KIS_ACNT_PRDT_CD")  # 계좌번호 뒤 2자리

broker = wrapper.KoreaInvestment(api_key=APP_KEY, api_secret=APP_SECRET, acc_no=ACNT_NO+"-"+TEST_KIS_ACNT_PRDT_CD)
resp = broker.fetch_price("005930")
pprint.pprint(resp)