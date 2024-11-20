import pytest
from findingmodelforge.prompt_template import create_prompt_messages, load_prompt_template
from jinja2 import Template


def test_generate_messages_from_markdown_simple():
    markdown_prompt = """
# SYSTEM

You are a super-intelligent AI that loves to be helpful.

# USER

What is the capital of {{country}}?

# ASSISTANT

The capital of {{country}} is {{capital}}.

# USER

Tell me a joke about a radiologist, a penguin, and a showgirl.
"""
    expected_messages = [
        {"role": "system", "content": "You are a super-intelligent AI that loves to be helpful."},
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "Tell me a joke about a radiologist, a penguin, and a showgirl."},
    ]

    template = Template(markdown_prompt)
    result = create_prompt_messages(template, country="France", capital="Paris")
    assert result == expected_messages


def test_generate_messages_from_markdown_invalid_role():
    markdown_prompt = """
# SYSTEM

This is a system message.

# UNKNOWN

This role is not recognized.
"""
    template = Template(markdown_prompt)
    with pytest.raises(NotImplementedError):
        create_prompt_messages(template)


def test_generate_messages_from_markdown_incomplete_sections():
    markdown_prompt = """
# USER

Incomplete message without content.

# ASSISTANT
"""
    expected_messages = [
        {"role": "user", "content": "Incomplete message without content."},
        {"role": "assistant", "content": ""},
    ]

    template = Template(markdown_prompt)
    result = create_prompt_messages(template)
    assert result == expected_messages


def test_generate_messages_from_loaded_template():
    template = load_prompt_template("get_finding_description")
    EXPECTED_RESULT = [
        {
            "role": "system",
            "content": "You are a radiology informatics assistant helping a radiologist write a textbook.\nYou are very good at understanding the properties of radiology findings and can \nhelp the radiologist flesh out information about the findings.",
        },
        {
            "role": "user",
            "content": "Create a one-to-two sentence definition/description for the finding. \nIf applicable, include synonyms as might be used by radiologists and other health \ncare professionals, including acronyms.\n\nThe description should be concise and use medical terminology; it's intended to be \nread by health care professionsals rather than laypersons.\n\nFinding to describe: pneumothorax",
        },
    ]
    result = create_prompt_messages(template, finding_name="pneumothorax")
    assert result == EXPECTED_RESULT
