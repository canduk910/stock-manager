"""KIS 인증 공통 모듈 — services/kis_auth.py로 이동 (2026-07-04 refactor F-1).

하위 호환 별칭 shim: `routers._kis_auth`와 `services.kis_auth`는 **동일 모듈 객체**다.
`from routers._kis_auth import X`, `patch("routers._kis_auth....")`, `_token_cache`
등 private 가변 상태 접근까지 기존 경로 그대로 동작한다.
신규 코드는 `services.kis_auth`를 직접 import할 것.
"""

import sys

from services import kis_auth as _impl

sys.modules[__name__] = _impl
