"""Isolated bill processing; its deadline is enforced by the local queue."""

import asyncio
import logging
import sys


async def run_bill(bill_id: int) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.config import get_settings
    from app.database import create_database_engine
    from app.services.bill_service import process_bill_pipeline

    engine = create_database_engine(get_settings().DATABASE_URL)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await process_bill_pipeline(session, bill_id)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(run_bill(int(sys.argv[1])))
