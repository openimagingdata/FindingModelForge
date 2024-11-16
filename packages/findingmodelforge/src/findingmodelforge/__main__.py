from pprint import pprint

from dynaconf import settings  # type: ignore


def get_settings():
    return {
        "DEBUG": settings.DEBUG,
        "MONGO_DSN": settings.MONGO_DSN,
        "DATABASE_NAME": settings.DATABASE_NAME,
    }


if __name__ == "__main__":
    print("Finding Model Forge configuration:")
    pprint(get_settings())
