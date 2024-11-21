import asyncio
from pprint import pprint

import click
from findingmodelforge import settings  # type: ignore
from findingmodelforge.finding_info_tools import describe_finding_name, get_detail_on_finding


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
    if settings.get("OPENAI_API_KEY", None):
        described_finding = asyncio.run(describe_finding_name(finding_name))
        pprint(described_finding)
        if settings.get("PERPLEXITY_API_KEY", None) and settings.get("PERPLEXITY_BASE_URL", None):
            detailed_response = asyncio.run(get_detail_on_finding(described_finding))
            pprint(detailed_response)
