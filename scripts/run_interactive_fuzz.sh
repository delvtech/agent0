# TODO Run these in the background, assuming these will handle how to notify or log errors

echo "HYPERDRIVE BALANCE"
python lib/agent0/agent0/interactive_fuzz/fuzz_hyperdrive_balance.py;

echo "PATH INDEPENDENCE"
python lib/agent0/agent0/interactive_fuzz/fuzz_path_independence.py;

echo "PROFIT CHECK"
python lib/agent0/agent0/interactive_fuzz/fuzz_profit_check.py;