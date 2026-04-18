"""services/exceptions.py 예외 계층 단위 테스트."""

from services.exceptions import (
    ServiceError,
    NotFoundError,
    ExternalAPIError,
    ConfigError,
    ConflictError,
    PaymentRequiredError,
)


class TestServiceError:
    def test_default_status_code(self):
        err = ServiceError("에러 발생")
        assert err.status_code == 400
        assert err.message == "에러 발생"

    def test_custom_status_code(self):
        err = ServiceError("커스텀", status_code=500)
        assert err.status_code == 500


class TestNotFoundError:
    def test_status_code(self):
        err = NotFoundError()
        assert err.status_code == 404

    def test_default_message(self):
        err = NotFoundError()
        assert "찾을 수 없습니다" in err.message

    def test_custom_message(self):
        err = NotFoundError("없음")
        assert err.message == "없음"

    def test_inherits_service_error(self):
        err = NotFoundError()
        assert isinstance(err, ServiceError)


class TestExternalAPIError:
    def test_status_code(self):
        assert ExternalAPIError().status_code == 502


class TestConfigError:
    def test_status_code(self):
        assert ConfigError().status_code == 503


class TestConflictError:
    def test_status_code(self):
        assert ConflictError().status_code == 409


class TestPaymentRequiredError:
    def test_status_code(self):
        assert PaymentRequiredError().status_code == 402


class TestInheritance:
    def test_all_inherit_service_error(self):
        for cls in [NotFoundError, ExternalAPIError, ConfigError, ConflictError, PaymentRequiredError]:
            assert issubclass(cls, ServiceError)

    def test_exception_is_catchable(self):
        with __import__("pytest").raises(ServiceError):
            raise NotFoundError("test")
