"""Simple Read/Write Test"""

from datetime import datetime

from elfpy.data import postgres
from elfpy.data.db_schema import PoolInfo

if __name__ == "__main__":
    session = postgres.initialize_session()

    pool_info: list[PoolInfo] = [PoolInfo(blockNumber=0, timestamp=0)]

    for i in range(1, 100):
        pool_info[0].blockNumber = i
        pool_info[0].timestamp = datetime.fromtimestamp(i * 1000)
        postgres.add_pool_infos(pool_info, session)

    retrieved_infos: list[PoolInfo] = session.query(PoolInfo).all()

    if not retrieved_infos:
        postgres.close_session(session)
    else:
        for info in retrieved_infos:
            print(info.__dict__)
        postgres.close_session(session)
