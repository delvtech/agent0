#!/bin/bash

source .env

# Function to display script usage
usage() {
  echo "Usage: $0 --rpc_url=<RPC_URL> --base_token=<BASE_TOKEN> --account=<ACCOUNT>"
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
    --account=*)
      account="${key#*=}"
      ;;
    *)
      echo "Invalid option: $key" >&2
      usage
      ;;
  esac
  shift
done

# Check if all required flags are provided
if [[ -z $rpc_url || -z $base_token || -z $account ]]; then
  echo "Error: All flags (--rpc_url, --base_token, --account) must be provided."
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

# get balance for account
result_hex=$(cast call "$base_token" "balanceOf(address)" "$account" --rpc-url "$rpc_url")
result_dec=$(cast to-dec "$result_hex")

# # Divide the result by 10^18 (add a decimal point 18 places from the right)
result_dec_with_decimal=$(echo "scale=18; $result_dec / 1000000000000000000" | bc)

echo "Result in hexadecimal: $result_hex"
echo "Result in decimal: $result_dec"
echo "Result in decimal: $result_dec_with_decimal"