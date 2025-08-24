"""Test the service exceptions."""

import pytest

from app.services import AuthorizationError, NotFoundError, ServiceError


class TestServiceExceptions:
    """Test the service layer exceptions."""

    def test_service_error_base_exception(self):
        """Test ServiceError as base exception."""
        # Test instantiation
        error = ServiceError("Test error message")
        assert str(error) == "Test error message"

        # Test inheritance
        assert isinstance(error, Exception)

    def test_not_found_error(self):
        """Test NotFoundError exception."""
        # Test instantiation
        error = NotFoundError("Resource not found")
        assert str(error) == "Resource not found"

        # Test inheritance
        assert isinstance(error, ServiceError)
        assert isinstance(error, Exception)

    def test_authorization_error(self):
        """Test AuthorizationError exception."""
        # Test instantiation
        error = AuthorizationError("Access denied")
        assert str(error) == "Access denied"

        # Test inheritance
        assert isinstance(error, ServiceError)
        assert isinstance(error, Exception)

    def test_exception_hierarchy(self):
        """Test exception inheritance hierarchy."""
        # All service exceptions should inherit from ServiceError
        assert issubclass(NotFoundError, ServiceError)
        assert issubclass(AuthorizationError, ServiceError)

        # ServiceError should inherit from Exception
        assert issubclass(ServiceError, Exception)

    def test_raising_exceptions(self):
        """Test raising and catching service exceptions."""
        # Test raising NotFoundError
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError("Test not found")
        assert str(exc_info.value) == "Test not found"

        # Test raising AuthorizationError
        with pytest.raises(AuthorizationError) as exc_info:
            raise AuthorizationError("Test unauthorized")
        assert str(exc_info.value) == "Test unauthorized"

    def test_catching_base_service_error(self):
        """Test catching service exceptions using base class."""
        # NotFoundError should be catchable as ServiceError
        with pytest.raises(ServiceError):
            raise NotFoundError("Test not found")

        # AuthorizationError should be catchable as ServiceError
        with pytest.raises(ServiceError):
            raise AuthorizationError("Test unauthorized")

    def test_exception_messages_preserved(self):
        """Test that exception messages are properly preserved."""
        test_message = "This is a test error message"

        # Test with each exception type
        service_error = ServiceError(test_message)
        assert str(service_error) == test_message

        not_found_error = NotFoundError(test_message)
        assert str(not_found_error) == test_message

        auth_error = AuthorizationError(test_message)
        assert str(auth_error) == test_message
