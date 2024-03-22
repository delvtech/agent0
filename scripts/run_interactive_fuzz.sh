# TODO Run these in the background, assuming these will handle how to notify or log errors

echo "HYPERDRIVE BALANCE"
python src/agent0/core/interactive_fuzz/fuzz_hyperdrive_balance.py;

echo "PATH INDEPENDENCE"
python src/agent0/core/interactive_fuzz/fuzz_path_independence.py;

echo "PROFIT CHECK"
python src/agent0/core/interactive_fuzz/fuzz_profit_check.py;