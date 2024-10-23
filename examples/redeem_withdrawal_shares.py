from dotenv import load_dotenv

load_dotenv(".env")

import os
import time

from agent0 import Chain, Hyperdrive

RPC_URI = os.getenv("RPC_URI", "")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
# Address of Hyperdrive Sepolia registry
REGISTRY_ADDRESS = "0x03f6554299acf544ac646305800f57db544b837a"

with Chain(RPC_URI) as chain:
    start_block = chain.block_number()

print("Scanning pools & redeeming withdrawal shares when possible...")
print(f"Start block: {start_block}")
while True:
    with Chain(RPC_URI) as chain:
        print(f"block number: {chain.block_number()}")
        registered_pools = Hyperdrive.get_hyperdrive_pools_from_registry(
            chain,
            registry_address=REGISTRY_ADDRESS,
        )
        # Initialize agent with private key for transactions
        agent = chain.init_agent(private_key=PRIVATE_KEY)
        for pool in registered_pools:
            # Withdraw all ready LP shares
            events = pool.get_trade_events()
            # Check if any recent events have occured that free up idle liquidity
            idle_increase_events = not events[
                (events["block_number"] >= start_block)
                & events["event_type"].isin(
                    ["AddLiquidity", "OpenLong", "OpenShort", "CloseLong", "CloseShort", "Checkpoint"]
                )
            ].empty
            if idle_increase_events:
                start_block = chain.block_number()
                withdrawal_shares = agent.get_withdrawal_shares(pool=pool)
                if withdrawal_shares > 0:
                    print(f"Redeem {withdrawal_shares} withdrawal shares on {pool.name}")
                    agent.redeem_withdrawal_shares(withdrawal_shares, pool=pool)
    # sleep for 1 minute
    time.sleep(60)
