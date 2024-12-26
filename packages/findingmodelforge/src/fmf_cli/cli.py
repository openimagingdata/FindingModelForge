import asyncio
from pathlib import Path

import click
from findingmodelforge.config import settings
from findingmodelforge.finding_info_tools import describe_finding_name, get_detail_on_finding
from findingmodelforge.finding_model_tools import (
    create_finding_model_from_markdown,
    create_finding_model_stub_from_finding_info,
)
from findingmodelforge.models.finding_info import BaseFindingInfo, DetailedFindingInfo
from findingmodelforge.models.finding_info_db import FindingInfoDb
from findingmodelforge.models.finding_model_db import FindingModelDb
from rich.console import Console

INITIALIZED_DB = False


async def init_db() -> None:
    from beanie import init_beanie
    from motor.motor_asyncio import AsyncIOMotorClient

    global INITIALIZED_DB
    if not INITIALIZED_DB:
        client: AsyncIOMotorClient = AsyncIOMotorClient(str(settings.mongo_dsn.get_secret_value()))
        database = client.get_database(settings.database_name)
        await init_beanie(database, document_models=[FindingModelDb, FindingInfoDb])
        INITIALIZED_DB = True


@click.group()
def cli():
    pass


@cli.command()
def config():
    """Show the currently active configuration."""
    console = Console()
    console.print("[yellow bold]Finding Model Forge configuration:")
    console.print_json(settings.model_dump_json())


def print_info_truncate_detail(console: Console, finding_info: BaseFindingInfo) -> None:
    out = finding_info.model_dump()
    if out.get("detail") and len(out["detail"]) > 100:
        out["detail"] = out["detail"][0:100] + "..."
    console.print(out)


@cli.command()
@click.argument("finding_name", default="Pneumothorax")
@click.option("--detailed", "-d", is_flag=True, help="Get detailed information on the finding.")
def make_info(finding_name: str, detailed: bool):
    """Generate description/synonyms and more details/citations for a finding name."""

    console = Console()

    async def _do_got_info_from_db(finding_info: FindingInfoDb, detailed: bool) -> None:
        console.print("Already in database.")
        print_info_truncate_detail(console, finding_info)
        if not detailed:
            return
        with console.status("Getting detailed information..."):
            detailed_response = await get_detail_on_finding(finding_info)
        if not isinstance(detailed_response, DetailedFindingInfo):
            raise ValueError("Detailed finding info not returned.")
        finding_info.detail = detailed_response.detail
        finding_info.citations = detailed_response.citations
        result = await finding_info.save()
        if result is None or result.id is None:
            raise RuntimeError("Error saving to database.")
        console.print(f"Saved to database: [yellow]: {result.id}")

    async def _do_make_info(finding_name: str, detailed: bool) -> None:
        await init_db()
        console.print(f"[gray] Getting information on [yellow bold]{finding_name}")
        result = await FindingInfoDb.find_one(FindingInfoDb.name == finding_name)
        if result is not None:
            return await _do_got_info_from_db(result, detailed)
        with console.status("[bold green]Getting description and synonyms..."):
            described_finding = await describe_finding_name(finding_name)
        if not isinstance(described_finding, BaseFindingInfo):
            raise ValueError("Finding info not returned.")
        if detailed:
            with console.status("Getting detailed information... "):
                detailed_response = await get_detail_on_finding(described_finding)
            if not isinstance(detailed_response, DetailedFindingInfo):
                raise ValueError("Detailed finding info not returned.")
            described_finding = detailed_response
        print_info_truncate_detail(console, described_finding)
        with console.status("Saving to database..."):
            db_finding = FindingInfoDb(**described_finding.model_dump())
            result = await db_finding.save()
        if result is None or result.id is None:
            raise RuntimeError("Error saving to database.")
        console.print(f"Saved to database as [yellow]{result.id}")

    asyncio.run(_do_make_info(finding_name, detailed))


@cli.command()
@click.argument("finding_name", default="Pneumothorax")
@click.option("--tags", "-t", multiple=True, help="Tags to add to the model.")
def make_stub_model(finding_name: str, tags: list[str]):
    """Generate a simple finding model object (presence and change elements only) from a finding name."""

    console = Console()

    async def _do_make_stub_model(finding_name: str, tags: list[str]) -> None:
        with console.status("[bold green] Initializing database..."):
            await init_db()
        with console.status(f"[bold green] Checking for {finding_name}..."):
            model_result = await FindingModelDb.find_one(FindingModelDb.name == finding_name)
        if model_result is not None:
            console.print(f"Found [bold]{model_result.name}[/] in model database: [yellow]{model_result.id}")
            return
        console.print(f"[gray] Getting stub model for [yellow bold]{finding_name}")
        # Get it from the database if it's already there
        result = await FindingInfoDb.find_one(FindingInfoDb.name == finding_name)
        if result is not None:
            console.print(f"Found [bold]{result.name}[/] in info database: [yellow]{result.id}")
            described_finding: BaseFindingInfo = result
        else:
            with console.status("[bold green]Getting description and synonyms..."):
                described_finding = await describe_finding_name(finding_name)
        assert isinstance(described_finding, BaseFindingInfo)
        stub = create_finding_model_stub_from_finding_info(described_finding, tags)
        console.print("Saving to database...")
        stub_db = FindingModelDb(**stub.model_dump())
        result = await stub_db.save()
        console.print_json(stub_db.model_dump_json())

    asyncio.run(_do_make_stub_model(finding_name, tags))


@cli.command()
# Indicate that the argument should be a filename
@click.argument("finding_path", type=click.Path(exists=True, path_type=Path))
def markdown_to_fm(finding_path: Path):
    """Convert markdown file to finding model format."""

    console = Console()

    async def _do_markdown_to_fm(finding_path: Path) -> None:
        with console.status("[bold green] Initializing database..."):
            await init_db()
        finding_name = finding_path.stem.replace("_", " ").replace("-", " ")
        console.print(f"[gray] Getting model for [yellow bold]{finding_name}")
        click.echo(f"Converting {finding_path} to finding model format.")
        with console.status("[bold green]Checking for existing info..."):
            result = await FindingInfoDb.find_one(FindingInfoDb.name == finding_name)
        if result is not None:
            console.print(f"Found [bold]{result.name}[/] in info database: [yellow]{result.id}")
            described_finding: BaseFindingInfo = result
        else:
            with console.status("[bold green]Getting description..."):
                described_finding = await describe_finding_name(finding_name)
        print_info_truncate_detail(console, described_finding)
        assert isinstance(described_finding, BaseFindingInfo), "Finding info not returned."

        with console.status("Creating model from Markdown description..."):
            model = await create_finding_model_from_markdown(described_finding, markdown_path=finding_path)
        console.print(model.model_dump())

    asyncio.run(_do_markdown_to_fm(finding_path))


if __name__ == "__main__":
    cli()
