#!/bin/bash

source .env

# Function to display script usage
usage() {
  echo "Usage: $0 --rpc_url=<RPC_URL> --base_token=<BASE_TOKEN> --amount=<AMOUNT>"
  exit 1
}

# Parse command-line options
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --rpc_url=*)
      rpc_url="${key#*=}"
      ;;
    --base_token=*)
      base_token="${key#*=}"
      ;;
    --amount=*)
      amount="${key#*=}"
      ;;
    *)
      echo "Invalid option: $key" >&2
      usage
      ;;
  esac
  shift
done

# Check if all required flags are provided
if [[ -z $rpc_url || -z $base_token || -z $amount ]]; then
  echo "Error: All flags (--rpc_url, --base_token, --amount) must be provided."
  usage
fi

# Check if the Ethereum node is reachable
if curl -s -o /dev/null --connect-timeout 5 "$rpc_url"; then
  echo "Ethereum node is reachable."
else
  echo "Error: Ethereum node is not reachable at the provided RPC URL: $rpc_url"
  exit 1
fi

# Wait until the Ethereum node is ready
while true; do
  if curl -s -X POST --header "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"web3_clientVersion","params":[],"id":1}' "$rpc_url" | grep -q "result"; then
    break
  fi
  echo "Waiting for Ethereum node to be ready..."
  sleep 1
done

echo "--------------------------------"
echo "        MINT TOKENS             "
echo "--------------------------------"

# Use bc for arbitrary precision arithmetic
multiplied_amount=$(echo "$amount * 1000000000000000000" | bc)
echo "multiplied_amount: $multiplied_amount"

# Convert the multiplied amount to a hexadecimal string
amount_hex="0x$(echo "obase=16; $multiplied_amount" | bc)"
echo "amount_hex: $amount_hex"

# mint tokens for account
cast send "$base_token" "mint(uint256)" "$amount_hex" --rpc-url "$rpc_url" --private-key "$USER_KEY"

echo "--------------------------------"
echo " ACCOUNT FUNDED SUCCESSFULLY!! "
echo "--------------------------------"
