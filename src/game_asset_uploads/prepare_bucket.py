import os

from .infrai_storage import InfraiStorage


def main() -> None:
    bucket = os.environ.get("GAME_ASSET_BUCKET", "player-generated-assets")
    storage = InfraiStorage()
    try:
        storage.create_bucket(bucket)
    finally:
        storage.close()
    print(f"Asset bucket ready: {bucket}")


if __name__ == "__main__":
    main()

