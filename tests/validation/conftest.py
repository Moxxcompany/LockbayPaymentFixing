import pytest


@pytest.fixture
def results(request):
    """
    Dynamic fixture that returns the appropriate validation results object
    based on which test module is calling it.
    """
    module_name = request.module.__name__
    
    if 'test_financial_operations' in module_name:
        from tests.validation.test_financial_operations import FinancialValidationResults
        return FinancialValidationResults()
    elif 'test_session_management' in module_name:
        from tests.validation.test_session_management import SessionValidationResults
        return SessionValidationResults()
    elif 'test_infrastructure_validation' in module_name:
        from tests.validation.test_infrastructure_validation import InfrastructureValidationResults
        return InfrastructureValidationResults()
    elif 'test_state_machines' in module_name:
        from tests.validation.test_state_machines import StateMachineValidationResults
        return StateMachineValidationResults()
    else:
        raise ValueError(f"Unknown test module: {module_name}")
