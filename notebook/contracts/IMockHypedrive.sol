// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.18;

import "./IHyperdrive.sol";

interface IMockHyperdrive is IHyperdrive {
    function shareReserves() external view returns (uint256);
    function bondReserves() external view returns (uint256);
    function longsOutstanding() external view returns (uint256);

    function setFees(
        uint256 _curveFee,
        uint256 _flatFee
    ) external;

    function getSharePrice() external view returns (uint256);

    function setSharePrice(uint256 sharePrice) external;
}