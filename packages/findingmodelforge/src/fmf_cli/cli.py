import asyncio
from pathlib import Path

import click
from findingmodelforge.config import settings
from findingmodelforge.finding_info_tools import describe_finding_name, get_detail_on_finding
from findingmodelforge.finding_model_tools import (
    create_finding_model_from_markdown,
    create_finding_model_stub_from_finding_info,
)
from findingmodelforge.models.finding_info import BaseFindingInfo
from rich.console import Console


@click.group()
def cli():
    pass


@cli.command()
def config():
    """Show the currently active configuration."""
    console = Console()
    console.print("[yellow bold]Finding Model Forge configuration:")
    console.print_json(settings.model_dump_json())


@cli.command()
@click.argument("finding_name", default="Pneumothorax")
def make_info(finding_name):
    """Generate description/synonyms and more details/citations for a finding name."""
    console = Console()
    console.print(f"[gray] Getting information on [yellow bold]{finding_name}")
    with console.status("[bold green]Getting description and synonyms..."):
        described_finding = asyncio.run(describe_finding_name(finding_name))
    with console.status("Getting detailed information... "):
        detailed_response = asyncio.run(get_detail_on_finding(described_finding))
    console.print(detailed_response)


@cli.command()
@click.argument("finding_name", default="Pneumothorax")
def make_stub_model(finding_name):
    console = Console()
    console.print(f"[gray] Getting stub model for [yellow bold]{finding_name}")
    with console.status("[bold green]Getting description and synonyms..."):
        described_finding = asyncio.run(describe_finding_name(finding_name))
    stub = create_finding_model_stub_from_finding_info(described_finding)
    console.print_json(stub.model_dump_json())


@cli.command()
# Indicate that the argument should be a filename
@click.argument("finding_path", type=click.Path(exists=True, path_type=Path))
def markdown_to_fm(finding_path: Path):
    """Convert markdown file to finding model format."""

    console = Console()
    finding_name = finding_path.stem.replace("_", " ").replace("-", " ")
    console.print(f"[gray] Getting model for [yellow bold]{finding_name}")
    click.echo(f"Converting {finding_path} to finding model format.")
    with console.status("[bold green]Getting description..."):
        described_finding = asyncio.run(describe_finding_name(finding_name))
        console.print(described_finding)
    if not isinstance(described_finding, BaseFindingInfo):
        raise ValueError("Finding info not returned.")
    with console.status("Creating model from Markdown description..."):
        model = asyncio.run(create_finding_model_from_markdown(described_finding, markdown_path=finding_path))
    console.print(model)
