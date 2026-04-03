"""서비스 레이어 공통 예외.

서비스 레이어에서 HTTPException 대신 이 예외를 raise하고,
라우터에서 except ServiceError → HTTPException 변환.
"""


class ServiceError(Exception):
    """서비스 레이어 기본 예외."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(ServiceError):
    """리소스 없음 (404)."""

    def __init__(self, message: str = "리소스를 찾을 수 없습니다."):
        super().__init__(message, status_code=404)


class ExternalAPIError(ServiceError):
    """외부 API 호출 실패 (502)."""

    def __init__(self, message: str = "외부 API 호출 실패"):
        super().__init__(message, status_code=502)


class ConfigError(ServiceError):
    """설정 누락 (503)."""

    def __init__(self, message: str = "필수 설정이 누락되었습니다."):
        super().__init__(message, status_code=503)


class ConflictError(ServiceError):
    """리소스 충돌 (409)."""

    def __init__(self, message: str = "리소스가 이미 존재합니다."):
        super().__init__(message, status_code=409)


class PaymentRequiredError(ServiceError):
    """결제/크레딧 부족 (402)."""

    def __init__(self, message: str = "결제 정보를 확인해주세요."):
        super().__init__(message, status_code=402)
