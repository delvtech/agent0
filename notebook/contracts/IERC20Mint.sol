// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.18;

import "./IERC20.sol";

interface IERC20Mint is IERC20 {
    function mint(uint256 amount) external;
}
