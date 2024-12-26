import pytest
from findingmodelforge.models.finding_info_db import FindingInfoDb


@pytest.mark.asyncio
@pytest.mark.needs_db
async def test_create_and_get_finding_info(db_init):
    # Create an object
    info = FindingInfoDb(
        name="Test Finding",
        description="This is a test finding",
    )

    result = await info.save()
    assert result is not None and result.id is not None

    # Retrieve the object
    count = await FindingInfoDb.count()
    assert count == 1
    retrieved_model = await FindingInfoDb.find_one(FindingInfoDb.name == "Test Finding")
    assert retrieved_model is not None
    assert retrieved_model.name == "Test Finding"
    assert retrieved_model.description == "This is a test finding"


@pytest.mark.asyncio
@pytest.mark.needs_db
async def get_count(db_init):
    count = await FindingInfoDb.count()
    assert count == 1
