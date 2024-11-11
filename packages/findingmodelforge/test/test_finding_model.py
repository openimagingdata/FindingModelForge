import json

from findingmodelforge.models.finding_model import (
    AttributeType,
    ChoiceAttribute,
    ChoiceValue,
    FindingModelBase,
    NumericAttribute,
)


def test_choice_value():
    value = ChoiceValue(name="Severe", description="A severe finding")
    assert value.name == "Severe"
    assert value.description == "A severe finding"


def test_choice_attribute():
    value1 = ChoiceValue(name="Mild")
    value2 = ChoiceValue(name="Severe")
    attribute = ChoiceAttribute(
        name="Severity",
        values=[value1, value2],
        required=True,
    )
    assert attribute.name == "Severity"
    assert attribute.type == AttributeType.CHOICE
    assert len(attribute.values) == 2
    assert attribute.required is True


def test_numeric_attribute():
    attribute = NumericAttribute(
        name="Size",
        minimum=0,
        maximum=10,
        unit="cm",
        required=False,
    )
    assert attribute.name == "Size"
    assert attribute.type == AttributeType.NUMERIC
    assert attribute.minimum == 0
    assert attribute.maximum == 10
    assert attribute.unit == "cm"
    assert attribute.required is False


def test_finding_model_base(tmp_path):
    test_data_dir = tmp_path / "test_data"
    test_data_dir.mkdir()
    choice_values = [ChoiceValue(name="Mild"), ChoiceValue(name="Moderate"), ChoiceValue(name="Severe")]
    choice_attribute = ChoiceAttribute(
        name="Severity",
        values=choice_values,
        required=True,
    )
    numeric_attribute = NumericAttribute(
        name="Size",
        minimum=0,
        maximum=10,
        unit="cm",
        required=False,
    )
    finding_model = FindingModelBase(
        finding_name="ExampleFinding",
        description="An example finding for testing.",
        attributes=[choice_attribute, numeric_attribute],
    )
    json_data = finding_model.model_dump()
    json_file = test_data_dir / "example_finding_model.json"
    with open(json_file, "w") as f:
        json.dump(json_data, f)
    with open(json_file) as f:
        loaded_data = json.load(f)
    loaded_finding_model = FindingModelBase(**loaded_data)
    assert loaded_finding_model.finding_name == finding_model.finding_name
    assert loaded_finding_model.description == finding_model.description
    assert len(loaded_finding_model.attributes) == len(finding_model.attributes)
