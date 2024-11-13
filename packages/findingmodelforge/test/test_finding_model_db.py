import pytest
from findingmodelforge.models.finding_model import NumericAttribute
from findingmodelforge.models.finding_model_db import FindingModelDb


@pytest.mark.asyncio
async def test_create_and_get_finding_model(db_init):
    # Create an object
    attributes = [NumericAttribute(name="Size", minimum=0, maximum=10, unit="cm", required=False)]
    finding_model = FindingModelDb(finding_name="Test Model", description="This is a test model", attributes=attributes)
    result = await finding_model.save()
    assert result is not None and result.id is not None

    # Retrieve the object
    count = await FindingModelDb.count()
    assert count == 1
    retrieved_model = await FindingModelDb.find_one(FindingModelDb.finding_name == "Test Model")
    assert retrieved_model is not None
    assert retrieved_model.finding_name == "Test Model"
    assert retrieved_model.description == "This is a test model"


@pytest.mark.asyncio
async def get_count(db_init):
    count = await FindingModelDb.count()
    assert count == 1
