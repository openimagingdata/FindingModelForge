import asyncio
from pathlib import Path
from pprint import pprint

import click
from findingmodelforge.config import (  # type: ignore
    ConfigurationError,
    check_ready_for_openai,
    check_ready_for_perplexity,
    settings,
)
from findingmodelforge.finding_info_tools import describe_finding_name, get_detail_on_finding
from findingmodelforge.finding_model_tools import create_finding_model_from_markdown
from findingmodelforge.models.finding_info import BaseFindingInfo


def get_settings():
    out = {
        "DEBUG": settings.DEBUG,
        "MONGO_DSN": settings.MONGO_DSN,
        "DATABASE_NAME": settings.DATABASE_NAME,
    }

    def format_secret(secret: str) -> str:
        return secret[0:12] + "..." + secret[-4:]

    secrets = ["OPENAI_API_KEY", "PERPLEXITY_API_KEY"]
    for secret in secrets:
        if settings.get(secret, None):
            out[secret] = format_secret(settings.get(secret))
    return out


@click.group()
def cli():
    pass


@cli.command()
def config():
    """Show the currently active configuration."""
    print("Finding Model Forge configuration:")
    pprint(get_settings())


@cli.command()
@click.argument("finding_name", default="Pneumothorax")
def make_info(finding_name):
    """Generate description/synonyms and more details/citations for a finding name."""
    if not check_ready_for_openai():
        described_finding = asyncio.run(describe_finding_name(finding_name))
        pprint(described_finding)
        if check_ready_for_perplexity():
            detailed_response = asyncio.run(get_detail_on_finding(described_finding))
            pprint(detailed_response)


@cli.command()
# Indicate that the argument should be a filename
@click.argument("finding_path", type=click.Path(exists=True))
def markdown_to_fm(finding_path: Path):
    """Convert markdown file to finding model format."""
    finding_path = Path(finding_path)
    print(f"Converting {finding_path} to finding model format.")
    # Get the part of the path that is the finding name (no directory, no extension)
    finding_name = finding_path.stem.replace("_", " ").replace("-", " ")
    if not check_ready_for_openai():
        raise ConfigurationError("OpenAI API key not set (use OPENAI_API_KEY in .env).")
    described_finding = asyncio.run(describe_finding_name(finding_name))
    if not isinstance(described_finding, BaseFindingInfo):
        raise ValueError("Finding info not returned.")
    pprint(described_finding)
    model = asyncio.run(create_finding_model_from_markdown(described_finding, markdown_path=finding_path))
    pprint(model)
