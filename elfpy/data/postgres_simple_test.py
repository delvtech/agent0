"""Simple Read/Write Test"""

from elfpy.data import postgres
from elfpy.data.pool_info import PoolInfo

if __name__ == "__main__":
    session = postgres.initialize_session()

    pool_info: list[PoolInfo] = [PoolInfo()]

    for i in range(1, 100):
        pool_info[0].blockNumber = i
        pool_info[0].timestamp = i * 1000
        postgres.add_pool_infos(pool_info, session)

    retrieved_infos = session.query(postgres.PoolInfoTable).all()

    for info in retrieved_infos:
        print(info.__dict__)
    postgres.close_session(session)
