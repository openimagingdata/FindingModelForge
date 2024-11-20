import re
from pathlib import Path

from jinja2 import Template
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

PROMPT_TEMPLATE_DIR = Path(__file__).parent / "prompt_templates"


def load_prompt_template(template_file_name: str) -> Template:
    template_file_name = (
        template_file_name if template_file_name.endswith(".md.jinja") else f"{template_file_name}.md.jinja"
    )
    template_file = PROMPT_TEMPLATE_DIR / template_file_name
    if not template_file.exists():
        raise FileNotFoundError(f"Prompt template {template_file_name} not found")
    template_text = template_file.read_text()
    return Template(template_text)


def create_prompt_messages(template: Template, **kwargs) -> list[ChatCompletionMessageParam]:
    rendered_prompt = template.render(**kwargs)

    # Split the markdown text into sections based on '# [ROLE]' headers
    sections = re.split(r"(^|\n)# ([A-Z]+)", rendered_prompt)

    # Remove any leading/trailing whitespace and empty strings
    sections = [s.strip() for s in sections if s.strip()]

    # Build the list of messages
    prompt_messages: list[ChatCompletionMessageParam] = []
    for i in range(0, len(sections), 2):
        role = sections[i].lower()
        # If there is no content for the role, use an empty string
        content = "" if i + 1 >= len(sections) else sections[i + 1]
        message: ChatCompletionMessageParam
        if role == "system":
            message = ChatCompletionSystemMessageParam(role="system", content=content)
        elif role == "user":
            message = ChatCompletionUserMessageParam(role="user", content=content)
        elif role == "assistant":
            message = ChatCompletionAssistantMessageParam(role="assistant", content=content)
        else:
            raise NotImplementedError(f"Role {role} not implemented")

        prompt_messages.append(message)

    return prompt_messages
