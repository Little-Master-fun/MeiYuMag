import asyncio

from app.db.session import AsyncSessionLocal
from app.services.expiration import expiration_service


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await expiration_service.process_yueyuan_pending_signed_files(db)
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
