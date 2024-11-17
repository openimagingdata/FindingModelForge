import asyncio
import sys
from pprint import pprint

from dynaconf import settings  # type: ignore

from findingmodelforge.finding_model_generator import describe_finding_name, get_detail_on_finding


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


if __name__ == "__main__":
    print("Finding Model Forge configuration:")
    pprint(get_settings())

    finding_name = sys.argv[1] if len(sys.argv) > 1 else "Pneumothorax"
    described_finding = asyncio.run(describe_finding_name(finding_name))
    pprint(described_finding)
    detailed_response = asyncio.run(get_detail_on_finding(described_finding))
    pprint(detailed_response)
