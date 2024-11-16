from pprint import pprint

from dynaconf import settings  # type: ignore


def get_settings():
    out = {
        "DEBUG": settings.DEBUG,
        "MONGO_DSN": settings.MONGO_DSN,
        "DATABASE_NAME": settings.DATABASE_NAME,
    }
    if settings.OPENAI_API_KEY:
        out["OPENAI_API_KEY"] = settings.OPENAI_API_KEY[0:12] + "..." + settings.OPENAI_API_KEY[-4:]
    return out


if __name__ == "__main__":
    print("Finding Model Forge configuration:")
    pprint(get_settings())