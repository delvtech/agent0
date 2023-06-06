export BOT_DEVNET=true
export BOT_RPC_URL=http://localhost:8545
export BOT_LOG_FILENAME=testnet_bots
export BOT_LOG_LEVEL=INFO
export BOT_MAX_BYTES=100
export BOT_NUM_LOUIE=0
export BOT_NUM_FRIDA=0
export BOT_NUM_RANDOM=4
export BOT_TRADE_CHANCE=0.1
export BOT_ALCHEMY=false
export BOT_ARTIFACTS_URL=http://localhost:80

python examples/evm_bots.py
