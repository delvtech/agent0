"""A web3.py Contract class for the IERC4626Hyperdrive contract."""

# contracts have PascalCase names
# pylint: disable=invalid-name

# contracts control how many attributes and arguments we have in generated code
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments

# we don't need else statement if the other conditionals all have return,
# but it's easier to generate
# pylint: disable=no-else-return

# This file is bound to get very long depending on contract sizes.
# pylint: disable=too-many-lines

from __future__ import annotations

from typing import cast

from eth_typing import ChecksumAddress, HexStr
from hexbytes import HexBytes
from web3.contract.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound
from web3.types import ABI, BlockIdentifier, CallOverride, TxParams

from .IERC4626HyperdriveTypes import Checkpoint, MarketState, Options, PoolConfig, PoolInfo, WithdrawPool


class IERC4626HyperdriveDOMAIN_SEPARATORContractFunction(ContractFunction):
    """ContractFunction for the DOMAIN_SEPARATOR method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveDOMAIN_SEPARATORContractFunction":
        super().__call__()
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> bytes:
        """returns bytes"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdrivePERMIT_TYPEHASHContractFunction(ContractFunction):
    """ContractFunction for the PERMIT_TYPEHASH method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdrivePERMIT_TYPEHASHContractFunction":
        super().__call__()
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> bytes:
        """returns bytes"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveAddLiquidityContractFunction(ContractFunction):
    """ContractFunction for the addLiquidity method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _contribution: int, _minApr: int, _maxApr: int, _options: Options
    ) -> "IERC4626HyperdriveAddLiquidityContractFunction":
        super().__call__(_contribution, _minApr, _maxApr, _options)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """returns int"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveBalanceOfContractFunction(ContractFunction):
    """ContractFunction for the balanceOf method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int, owner: str) -> "IERC4626HyperdriveBalanceOfContractFunction":
        super().__call__(tokenId, owner)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """returns int"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveBaseTokenContractFunction(ContractFunction):
    """ContractFunction for the baseToken method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveBaseTokenContractFunction":
        super().__call__()
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """returns str"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveBatchTransferFromContractFunction(ContractFunction):
    """ContractFunction for the batchTransferFrom method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _from: str, to: str, ids: list[int], values: list[int]
    ) -> "IERC4626HyperdriveBatchTransferFromContractFunction":
        super().__call__(_from, to, ids, values)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveCheckpointContractFunction(ContractFunction):
    """ContractFunction for the checkpoint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _checkpointTime: int) -> "IERC4626HyperdriveCheckpointContractFunction":
        super().__call__(_checkpointTime)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveCloseLongContractFunction(ContractFunction):
    """ContractFunction for the closeLong method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _maturityTime: int,
        _bondAmount: int,
        _minOutput: int,
        _options: Options,
    ) -> "IERC4626HyperdriveCloseLongContractFunction":
        super().__call__(_maturityTime, _bondAmount, _minOutput, _options)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """returns int"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveCloseShortContractFunction(ContractFunction):
    """ContractFunction for the closeShort method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _maturityTime: int,
        _bondAmount: int,
        _minOutput: int,
        _options: Options,
    ) -> "IERC4626HyperdriveCloseShortContractFunction":
        super().__call__(_maturityTime, _bondAmount, _minOutput, _options)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """returns int"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveCollectGovernanceFeeContractFunction(ContractFunction):
    """ContractFunction for the collectGovernanceFee method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _options: Options) -> "IERC4626HyperdriveCollectGovernanceFeeContractFunction":
        super().__call__(_options)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """returns int"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveGetCheckpointContractFunction(ContractFunction):
    """ContractFunction for the getCheckpoint method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _checkpointId: int) -> "IERC4626HyperdriveGetCheckpointContractFunction":
        super().__call__(_checkpointId)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> Checkpoint:
        """returns Checkpoint"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveGetMarketStateContractFunction(ContractFunction):
    """ContractFunction for the getMarketState method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveGetMarketStateContractFunction":
        super().__call__()
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> MarketState:
        """returns MarketState"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveGetPoolConfigContractFunction(ContractFunction):
    """ContractFunction for the getPoolConfig method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveGetPoolConfigContractFunction":
        super().__call__()
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> PoolConfig:
        """returns PoolConfig"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveGetPoolInfoContractFunction(ContractFunction):
    """ContractFunction for the getPoolInfo method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveGetPoolInfoContractFunction":
        super().__call__()
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> PoolInfo:
        """returns PoolInfo"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveGetUncollectedGovernanceFeesContractFunction(ContractFunction):
    """ContractFunction for the getUncollectedGovernanceFees method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
    ) -> "IERC4626HyperdriveGetUncollectedGovernanceFeesContractFunction":
        super().__call__()
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """returns int"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveGetWithdrawPoolContractFunction(ContractFunction):
    """ContractFunction for the getWithdrawPool method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveGetWithdrawPoolContractFunction":
        super().__call__()
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> WithdrawPool:
        """returns WithdrawPool"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveInitializeContractFunction(ContractFunction):
    """ContractFunction for the initialize method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _contribution: int, _apr: int, _options: Options
    ) -> "IERC4626HyperdriveInitializeContractFunction":
        super().__call__(_contribution, _apr, _options)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """returns int"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveIsApprovedForAllContractFunction(ContractFunction):
    """ContractFunction for the isApprovedForAll method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, owner: str, spender: str) -> "IERC4626HyperdriveIsApprovedForAllContractFunction":
        super().__call__(owner, spender)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> bool:
        """returns bool"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveIsSweepableContractFunction(ContractFunction):
    """ContractFunction for the isSweepable method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _target: str) -> "IERC4626HyperdriveIsSweepableContractFunction":
        super().__call__(_target)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> bool:
        """returns bool"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveLoadContractFunction(ContractFunction):
    """ContractFunction for the load method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _slots: list[int]) -> "IERC4626HyperdriveLoadContractFunction":
        super().__call__(_slots)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> list[bytes]:
        """returns list[bytes]"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveNameContractFunction(ContractFunction):
    """ContractFunction for the name method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _id: int) -> "IERC4626HyperdriveNameContractFunction":
        super().__call__(_id)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """returns str"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveNoncesContractFunction(ContractFunction):
    """ContractFunction for the nonces method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, owner: str) -> "IERC4626HyperdriveNoncesContractFunction":
        super().__call__(owner)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """returns int"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveOpenLongContractFunction(ContractFunction):
    """ContractFunction for the openLong method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _baseAmount: int,
        _minOutput: int,
        _minSharePrice: int,
        _options: Options,
    ) -> "IERC4626HyperdriveOpenLongContractFunction":
        super().__call__(_baseAmount, _minOutput, _minSharePrice, _options)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> tuple[int, int]:
        """returns (int, int)"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveOpenShortContractFunction(ContractFunction):
    """ContractFunction for the openShort method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        _bondAmount: int,
        _maxDeposit: int,
        _minSharePrice: int,
        _options: Options,
    ) -> "IERC4626HyperdriveOpenShortContractFunction":
        super().__call__(_bondAmount, _maxDeposit, _minSharePrice, _options)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> tuple[int, int]:
        """returns (int, int)"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdrivePauseContractFunction(ContractFunction):
    """ContractFunction for the pause method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _status: bool) -> "IERC4626HyperdrivePauseContractFunction":
        super().__call__(_status)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdrivePerTokenApprovalsContractFunction(ContractFunction):
    """ContractFunction for the perTokenApprovals method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenId: int, owner: str, spender: str) -> "IERC4626HyperdrivePerTokenApprovalsContractFunction":
        super().__call__(tokenId, owner, spender)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """returns int"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdrivePermitForAllContractFunction(ContractFunction):
    """ContractFunction for the permitForAll method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self,
        owner: str,
        spender: str,
        _approved: bool,
        deadline: int,
        v: int,
        r: bytes,
        s: bytes,
    ) -> "IERC4626HyperdrivePermitForAllContractFunction":
        super().__call__(owner, spender, _approved, deadline, v, r, s)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdrivePoolContractFunction(ContractFunction):
    """ContractFunction for the pool method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdrivePoolContractFunction":
        super().__call__()
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """returns str"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveRedeemWithdrawalSharesContractFunction(ContractFunction):
    """ContractFunction for the redeemWithdrawalShares method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _shares: int, _minOutput: int, _options: Options
    ) -> "IERC4626HyperdriveRedeemWithdrawalSharesContractFunction":
        super().__call__(_shares, _minOutput, _options)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> tuple[int, int]:
        """returns (int, int)"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveRemoveLiquidityContractFunction(ContractFunction):
    """ContractFunction for the removeLiquidity method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, _shares: int, _minOutput: int, _options: Options
    ) -> "IERC4626HyperdriveRemoveLiquidityContractFunction":
        super().__call__(_shares, _minOutput, _options)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> tuple[int, int]:
        """returns (int, int)"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveSetApprovalContractFunction(ContractFunction):
    """ContractFunction for the setApproval method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, tokenID: int, operator: str, amount: int) -> "IERC4626HyperdriveSetApprovalContractFunction":
        super().__call__(tokenID, operator, amount)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveSetApprovalBridgeContractFunction(ContractFunction):
    """ContractFunction for the setApprovalBridge method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenID: int, operator: str, amount: int, caller: str
    ) -> "IERC4626HyperdriveSetApprovalBridgeContractFunction":
        super().__call__(tokenID, operator, amount, caller)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveSetApprovalForAllContractFunction(ContractFunction):
    """ContractFunction for the setApprovalForAll method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, operator: str, approved: bool) -> "IERC4626HyperdriveSetApprovalForAllContractFunction":
        super().__call__(operator, approved)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveSetGovernanceContractFunction(ContractFunction):
    """ContractFunction for the setGovernance method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _who: str) -> "IERC4626HyperdriveSetGovernanceContractFunction":
        super().__call__(_who)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveSetPauserContractFunction(ContractFunction):
    """ContractFunction for the setPauser method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, who: str, status: bool) -> "IERC4626HyperdriveSetPauserContractFunction":
        super().__call__(who, status)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveSweepContractFunction(ContractFunction):
    """ContractFunction for the sweep method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _target: str) -> "IERC4626HyperdriveSweepContractFunction":
        super().__call__(_target)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveSymbolContractFunction(ContractFunction):
    """ContractFunction for the symbol method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _id: int) -> "IERC4626HyperdriveSymbolContractFunction":
        super().__call__(_id)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """returns str"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveTarget0ContractFunction(ContractFunction):
    """ContractFunction for the target0 method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveTarget0ContractFunction":
        super().__call__()
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """returns str"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveTarget1ContractFunction(ContractFunction):
    """ContractFunction for the target1 method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self) -> "IERC4626HyperdriveTarget1ContractFunction":
        super().__call__()
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """returns str"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveTotalSupplyContractFunction(ContractFunction):
    """ContractFunction for the totalSupply method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(self, _id: int) -> "IERC4626HyperdriveTotalSupplyContractFunction":
        super().__call__(_id)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> int:
        """returns int"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveTransferFromContractFunction(ContractFunction):
    """ContractFunction for the transferFrom method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenID: int, _from: str, to: str, amount: int
    ) -> "IERC4626HyperdriveTransferFromContractFunction":
        super().__call__(tokenID, _from, to, amount)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveTransferFromBridgeContractFunction(ContractFunction):
    """ContractFunction for the transferFromBridge method."""

    # super() call methods are generic, while our version adds values & types
    # pylint: disable=arguments-differ

    def __call__(
        self, tokenID: int, _from: str, to: str, amount: int, caller: str
    ) -> "IERC4626HyperdriveTransferFromBridgeContractFunction":
        super().__call__(tokenID, _from, to, amount, caller)
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ):
        """No return value"""
        return super().call(transaction, block_identifier, state_override, ccip_read_enabled)


class IERC4626HyperdriveContractFunctions(ContractFunctions):
    """ContractFunctions for the IERC4626Hyperdrive contract."""

    DOMAIN_SEPARATOR: IERC4626HyperdriveDOMAIN_SEPARATORContractFunction

    PERMIT_TYPEHASH: IERC4626HyperdrivePERMIT_TYPEHASHContractFunction

    addLiquidity: IERC4626HyperdriveAddLiquidityContractFunction

    balanceOf: IERC4626HyperdriveBalanceOfContractFunction

    baseToken: IERC4626HyperdriveBaseTokenContractFunction

    batchTransferFrom: IERC4626HyperdriveBatchTransferFromContractFunction

    checkpoint: IERC4626HyperdriveCheckpointContractFunction

    closeLong: IERC4626HyperdriveCloseLongContractFunction

    closeShort: IERC4626HyperdriveCloseShortContractFunction

    collectGovernanceFee: IERC4626HyperdriveCollectGovernanceFeeContractFunction

    getCheckpoint: IERC4626HyperdriveGetCheckpointContractFunction

    getMarketState: IERC4626HyperdriveGetMarketStateContractFunction

    getPoolConfig: IERC4626HyperdriveGetPoolConfigContractFunction

    getPoolInfo: IERC4626HyperdriveGetPoolInfoContractFunction

    getUncollectedGovernanceFees: IERC4626HyperdriveGetUncollectedGovernanceFeesContractFunction

    getWithdrawPool: IERC4626HyperdriveGetWithdrawPoolContractFunction

    initialize: IERC4626HyperdriveInitializeContractFunction

    isApprovedForAll: IERC4626HyperdriveIsApprovedForAllContractFunction

    isSweepable: IERC4626HyperdriveIsSweepableContractFunction

    load: IERC4626HyperdriveLoadContractFunction

    name: IERC4626HyperdriveNameContractFunction

    nonces: IERC4626HyperdriveNoncesContractFunction

    openLong: IERC4626HyperdriveOpenLongContractFunction

    openShort: IERC4626HyperdriveOpenShortContractFunction

    pause: IERC4626HyperdrivePauseContractFunction

    perTokenApprovals: IERC4626HyperdrivePerTokenApprovalsContractFunction

    permitForAll: IERC4626HyperdrivePermitForAllContractFunction

    pool: IERC4626HyperdrivePoolContractFunction

    redeemWithdrawalShares: IERC4626HyperdriveRedeemWithdrawalSharesContractFunction

    removeLiquidity: IERC4626HyperdriveRemoveLiquidityContractFunction

    setApproval: IERC4626HyperdriveSetApprovalContractFunction

    setApprovalBridge: IERC4626HyperdriveSetApprovalBridgeContractFunction

    setApprovalForAll: IERC4626HyperdriveSetApprovalForAllContractFunction

    setGovernance: IERC4626HyperdriveSetGovernanceContractFunction

    setPauser: IERC4626HyperdriveSetPauserContractFunction

    sweep: IERC4626HyperdriveSweepContractFunction

    symbol: IERC4626HyperdriveSymbolContractFunction

    target0: IERC4626HyperdriveTarget0ContractFunction

    target1: IERC4626HyperdriveTarget1ContractFunction

    totalSupply: IERC4626HyperdriveTotalSupplyContractFunction

    transferFrom: IERC4626HyperdriveTransferFromContractFunction

    transferFromBridge: IERC4626HyperdriveTransferFromBridgeContractFunction


ierc4626hyperdrive_abi: ABI = cast(
    ABI,
    [
        {"inputs": [], "name": "AlreadyClosed", "type": "error"},
        {"inputs": [], "name": "ApprovalFailed", "type": "error"},
        {
            "inputs": [],
            "name": "BaseBufferExceedsShareReserves",
            "type": "error",
        },
        {"inputs": [], "name": "BatchInputLengthMismatch", "type": "error"},
        {"inputs": [], "name": "BelowMinimumContribution", "type": "error"},
        {"inputs": [], "name": "BelowMinimumShareReserves", "type": "error"},
        {"inputs": [], "name": "BondMatured", "type": "error"},
        {"inputs": [], "name": "BondNotMatured", "type": "error"},
        {
            "inputs": [
                {
                    "internalType": "bytes4",
                    "name": "underlyingError",
                    "type": "bytes4",
                }
            ],
            "name": "CallFailed",
            "type": "error",
        },
        {"inputs": [], "name": "EndIndexTooLarge", "type": "error"},
        {"inputs": [], "name": "ExpiredDeadline", "type": "error"},
        {"inputs": [], "name": "FeeTooHigh", "type": "error"},
        {
            "inputs": [],
            "name": "FixedPointMath_InvalidExponent",
            "type": "error",
        },
        {"inputs": [], "name": "FixedPointMath_InvalidInput", "type": "error"},
        {"inputs": [], "name": "FixedPointMath_NegativeInput", "type": "error"},
        {
            "inputs": [],
            "name": "FixedPointMath_NegativeOrZeroInput",
            "type": "error",
        },
        {"inputs": [], "name": "InputLengthMismatch", "type": "error"},
        {"inputs": [], "name": "InsufficientPrice", "type": "error"},
        {"inputs": [], "name": "InvalidApr", "type": "error"},
        {"inputs": [], "name": "InvalidBaseToken", "type": "error"},
        {"inputs": [], "name": "InvalidCheckpointDuration", "type": "error"},
        {"inputs": [], "name": "InvalidCheckpointTime", "type": "error"},
        {"inputs": [], "name": "InvalidContribution", "type": "error"},
        {"inputs": [], "name": "InvalidERC20Bridge", "type": "error"},
        {"inputs": [], "name": "InvalidFeeAmounts", "type": "error"},
        {"inputs": [], "name": "InvalidFeeDestination", "type": "error"},
        {"inputs": [], "name": "InvalidForwarderAddress", "type": "error"},
        {"inputs": [], "name": "InvalidIndexes", "type": "error"},
        {"inputs": [], "name": "InvalidInitialSharePrice", "type": "error"},
        {"inputs": [], "name": "InvalidMaturityTime", "type": "error"},
        {"inputs": [], "name": "InvalidMinimumShareReserves", "type": "error"},
        {"inputs": [], "name": "InvalidPositionDuration", "type": "error"},
        {"inputs": [], "name": "InvalidShareReserves", "type": "error"},
        {"inputs": [], "name": "InvalidSignature", "type": "error"},
        {"inputs": [], "name": "InvalidTimestamp", "type": "error"},
        {"inputs": [], "name": "InvalidToken", "type": "error"},
        {"inputs": [], "name": "InvalidTradeSize", "type": "error"},
        {"inputs": [], "name": "MaxFeeTooHigh", "type": "error"},
        {"inputs": [], "name": "MinimumSharePrice", "type": "error"},
        {"inputs": [], "name": "MinimumTransactionAmount", "type": "error"},
        {"inputs": [], "name": "MintPercentTooHigh", "type": "error"},
        {"inputs": [], "name": "NegativeInterest", "type": "error"},
        {"inputs": [], "name": "NegativePresentValue", "type": "error"},
        {"inputs": [], "name": "NoAssetsToWithdraw", "type": "error"},
        {"inputs": [], "name": "NonPayableInitialization", "type": "error"},
        {"inputs": [], "name": "NotPayable", "type": "error"},
        {"inputs": [], "name": "OutputLimit", "type": "error"},
        {"inputs": [], "name": "Paused", "type": "error"},
        {"inputs": [], "name": "PoolAlreadyInitialized", "type": "error"},
        {"inputs": [], "name": "QueryOutOfRange", "type": "error"},
        {"inputs": [], "name": "RestrictedZeroAddress", "type": "error"},
        {
            "inputs": [{"internalType": "bytes", "name": "data", "type": "bytes"}],
            "name": "ReturnData",
            "type": "error",
        },
        {
            "inputs": [],
            "name": "ShareReservesDeltaExceedsBondReservesDelta",
            "type": "error",
        },
        {"inputs": [], "name": "TransferFailed", "type": "error"},
        {"inputs": [], "name": "Unauthorized", "type": "error"},
        {"inputs": [], "name": "UnexpectedAssetId", "type": "error"},
        {"inputs": [], "name": "UnexpectedSender", "type": "error"},
        {"inputs": [], "name": "UnexpectedSuccess", "type": "error"},
        {"inputs": [], "name": "UnsafeCastToInt128", "type": "error"},
        {"inputs": [], "name": "UnsafeCastToUint128", "type": "error"},
        {"inputs": [], "name": "UnsupportedToken", "type": "error"},
        {"inputs": [], "name": "ZeroLpTotalSupply", "type": "error"},
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "provider",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpSharePrice",
                    "type": "uint256",
                },
            ],
            "name": "AddLiquidity",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "owner",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "spender",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "value",
                    "type": "uint256",
                },
            ],
            "name": "Approval",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "account",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "operator",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "bool",
                    "name": "approved",
                    "type": "bool",
                },
            ],
            "name": "ApprovalForAll",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "trader",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "assetId",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "bondAmount",
                    "type": "uint256",
                },
            ],
            "name": "CloseLong",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "trader",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "assetId",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "bondAmount",
                    "type": "uint256",
                },
            ],
            "name": "CloseShort",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "collector",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseFees",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
            ],
            "name": "CollectGovernanceFee",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "checkpointTime",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturedShorts",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturedLongs",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpSharePrice",
                    "type": "uint256",
                },
            ],
            "name": "CreateCheckpoint",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "provider",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "apr",
                    "type": "uint256",
                },
            ],
            "name": "Initialize",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "trader",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "assetId",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "bondAmount",
                    "type": "uint256",
                },
            ],
            "name": "OpenLong",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "trader",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "uint256",
                    "name": "assetId",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "bondAmount",
                    "type": "uint256",
                },
            ],
            "name": "OpenShort",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "provider",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "withdrawalShareAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
            ],
            "name": "RedeemWithdrawalShares",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "provider",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "baseAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "sharePrice",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "withdrawalShareAmount",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "lpSharePrice",
                    "type": "uint256",
                },
            ],
            "name": "RemoveLiquidity",
            "type": "event",
        },
        {
            "anonymous": False,
            "inputs": [
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "operator",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "from",
                    "type": "address",
                },
                {
                    "indexed": True,
                    "internalType": "address",
                    "name": "to",
                    "type": "address",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "id",
                    "type": "uint256",
                },
                {
                    "indexed": False,
                    "internalType": "uint256",
                    "name": "value",
                    "type": "uint256",
                },
            ],
            "name": "TransferSingle",
            "type": "event",
        },
        {
            "inputs": [],
            "name": "DOMAIN_SEPARATOR",
            "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "PERMIT_TYPEHASH",
            "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_contribution",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minApr",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_maxApr",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "addLiquidity",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "lpShares",
                    "type": "uint256",
                }
            ],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenId",
                    "type": "uint256",
                },
                {"internalType": "address", "name": "owner", "type": "address"},
            ],
            "name": "balanceOf",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "baseToken",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "from", "type": "address"},
                {"internalType": "address", "name": "to", "type": "address"},
                {
                    "internalType": "uint256[]",
                    "name": "ids",
                    "type": "uint256[]",
                },
                {
                    "internalType": "uint256[]",
                    "name": "values",
                    "type": "uint256[]",
                },
            ],
            "name": "batchTransferFrom",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_checkpointTime",
                    "type": "uint256",
                }
            ],
            "name": "checkpoint",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_maturityTime",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_bondAmount",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minOutput",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "closeLong",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_maturityTime",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_bondAmount",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minOutput",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "closeShort",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                }
            ],
            "name": "collectGovernanceFee",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "proceeds",
                    "type": "uint256",
                }
            ],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_checkpointId",
                    "type": "uint256",
                }
            ],
            "name": "getCheckpoint",
            "outputs": [
                {
                    "components": [
                        {
                            "internalType": "uint128",
                            "name": "sharePrice",
                            "type": "uint128",
                        },
                        {
                            "internalType": "int128",
                            "name": "exposure",
                            "type": "int128",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Checkpoint",
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getMarketState",
            "outputs": [
                {
                    "components": [
                        {
                            "internalType": "uint128",
                            "name": "shareReserves",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "bondReserves",
                            "type": "uint128",
                        },
                        {
                            "internalType": "int128",
                            "name": "shareAdjustment",
                            "type": "int128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "longExposure",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "longsOutstanding",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "shortsOutstanding",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "longAverageMaturityTime",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "shortAverageMaturityTime",
                            "type": "uint128",
                        },
                        {
                            "internalType": "bool",
                            "name": "isInitialized",
                            "type": "bool",
                        },
                        {
                            "internalType": "bool",
                            "name": "isPaused",
                            "type": "bool",
                        },
                    ],
                    "internalType": "struct IHyperdrive.MarketState",
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getPoolConfig",
            "outputs": [
                {
                    "components": [
                        {
                            "internalType": "contract IERC20",
                            "name": "baseToken",
                            "type": "address",
                        },
                        {
                            "internalType": "address",
                            "name": "linkerFactory",
                            "type": "address",
                        },
                        {
                            "internalType": "bytes32",
                            "name": "linkerCodeHash",
                            "type": "bytes32",
                        },
                        {
                            "internalType": "uint256",
                            "name": "initialSharePrice",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "minimumShareReserves",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "minimumTransactionAmount",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "precisionThreshold",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "positionDuration",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "checkpointDuration",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "timeStretch",
                            "type": "uint256",
                        },
                        {
                            "internalType": "address",
                            "name": "governance",
                            "type": "address",
                        },
                        {
                            "internalType": "address",
                            "name": "feeCollector",
                            "type": "address",
                        },
                        {
                            "components": [
                                {
                                    "internalType": "uint256",
                                    "name": "curve",
                                    "type": "uint256",
                                },
                                {
                                    "internalType": "uint256",
                                    "name": "flat",
                                    "type": "uint256",
                                },
                                {
                                    "internalType": "uint256",
                                    "name": "governance",
                                    "type": "uint256",
                                },
                            ],
                            "internalType": "struct IHyperdrive.Fees",
                            "name": "fees",
                            "type": "tuple",
                        },
                    ],
                    "internalType": "struct IHyperdrive.PoolConfig",
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getPoolInfo",
            "outputs": [
                {
                    "components": [
                        {
                            "internalType": "uint256",
                            "name": "shareReserves",
                            "type": "uint256",
                        },
                        {
                            "internalType": "int256",
                            "name": "shareAdjustment",
                            "type": "int256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "bondReserves",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "lpTotalSupply",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "sharePrice",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "longsOutstanding",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "longAverageMaturityTime",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "shortsOutstanding",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "shortAverageMaturityTime",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "withdrawalSharesReadyToWithdraw",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "withdrawalSharesProceeds",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "lpSharePrice",
                            "type": "uint256",
                        },
                        {
                            "internalType": "uint256",
                            "name": "longExposure",
                            "type": "uint256",
                        },
                    ],
                    "internalType": "struct IHyperdrive.PoolInfo",
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getUncollectedGovernanceFees",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "getWithdrawPool",
            "outputs": [
                {
                    "components": [
                        {
                            "internalType": "uint128",
                            "name": "readyToWithdraw",
                            "type": "uint128",
                        },
                        {
                            "internalType": "uint128",
                            "name": "proceeds",
                            "type": "uint128",
                        },
                    ],
                    "internalType": "struct IHyperdrive.WithdrawPool",
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_contribution",
                    "type": "uint256",
                },
                {"internalType": "uint256", "name": "_apr", "type": "uint256"},
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "initialize",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "lpShares",
                    "type": "uint256",
                }
            ],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "owner", "type": "address"},
                {
                    "internalType": "address",
                    "name": "spender",
                    "type": "address",
                },
            ],
            "name": "isApprovedForAll",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "_target",
                    "type": "address",
                }
            ],
            "name": "isSweepable",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256[]",
                    "name": "_slots",
                    "type": "uint256[]",
                }
            ],
            "name": "load",
            "outputs": [{"internalType": "bytes32[]", "name": "", "type": "bytes32[]"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
            "name": "name",
            "outputs": [{"internalType": "string", "name": "", "type": "string"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
            "name": "nonces",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_baseAmount",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minOutput",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minSharePrice",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "openLong",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "bondProceeds",
                    "type": "uint256",
                },
            ],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_bondAmount",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_maxDeposit",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minSharePrice",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "openShort",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "maturityTime",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "traderDeposit",
                    "type": "uint256",
                },
            ],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "bool", "name": "_status", "type": "bool"}],
            "name": "pause",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenId",
                    "type": "uint256",
                },
                {"internalType": "address", "name": "owner", "type": "address"},
                {
                    "internalType": "address",
                    "name": "spender",
                    "type": "address",
                },
            ],
            "name": "perTokenApprovals",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "owner", "type": "address"},
                {
                    "internalType": "address",
                    "name": "spender",
                    "type": "address",
                },
                {"internalType": "bool", "name": "_approved", "type": "bool"},
                {
                    "internalType": "uint256",
                    "name": "deadline",
                    "type": "uint256",
                },
                {"internalType": "uint8", "name": "v", "type": "uint8"},
                {"internalType": "bytes32", "name": "r", "type": "bytes32"},
                {"internalType": "bytes32", "name": "s", "type": "bytes32"},
            ],
            "name": "permitForAll",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "pool",
            "outputs": [
                {
                    "internalType": "contract IERC4626",
                    "name": "",
                    "type": "address",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_shares",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minOutput",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "redeemWithdrawalShares",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "proceeds",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "sharesRedeemed",
                    "type": "uint256",
                },
            ],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "_shares",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "_minOutput",
                    "type": "uint256",
                },
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "destination",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "asBase",
                            "type": "bool",
                        },
                        {
                            "internalType": "bytes",
                            "name": "extraData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct IHyperdrive.Options",
                    "name": "_options",
                    "type": "tuple",
                },
            ],
            "name": "removeLiquidity",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "baseProceeds",
                    "type": "uint256",
                },
                {
                    "internalType": "uint256",
                    "name": "withdrawalShares",
                    "type": "uint256",
                },
            ],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenID",
                    "type": "uint256",
                },
                {
                    "internalType": "address",
                    "name": "operator",
                    "type": "address",
                },
                {
                    "internalType": "uint256",
                    "name": "amount",
                    "type": "uint256",
                },
            ],
            "name": "setApproval",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenID",
                    "type": "uint256",
                },
                {
                    "internalType": "address",
                    "name": "operator",
                    "type": "address",
                },
                {
                    "internalType": "uint256",
                    "name": "amount",
                    "type": "uint256",
                },
                {
                    "internalType": "address",
                    "name": "caller",
                    "type": "address",
                },
            ],
            "name": "setApprovalBridge",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "operator",
                    "type": "address",
                },
                {"internalType": "bool", "name": "approved", "type": "bool"},
            ],
            "name": "setApprovalForAll",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "address", "name": "_who", "type": "address"}],
            "name": "setGovernance",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "who", "type": "address"},
                {"internalType": "bool", "name": "status", "type": "bool"},
            ],
            "name": "setPauser",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "contract IERC20",
                    "name": "_target",
                    "type": "address",
                }
            ],
            "name": "sweep",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
            "name": "symbol",
            "outputs": [{"internalType": "string", "name": "", "type": "string"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "target0",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "target1",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
            "name": "totalSupply",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenID",
                    "type": "uint256",
                },
                {"internalType": "address", "name": "from", "type": "address"},
                {"internalType": "address", "name": "to", "type": "address"},
                {
                    "internalType": "uint256",
                    "name": "amount",
                    "type": "uint256",
                },
            ],
            "name": "transferFrom",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {
                    "internalType": "uint256",
                    "name": "tokenID",
                    "type": "uint256",
                },
                {"internalType": "address", "name": "from", "type": "address"},
                {"internalType": "address", "name": "to", "type": "address"},
                {
                    "internalType": "uint256",
                    "name": "amount",
                    "type": "uint256",
                },
                {
                    "internalType": "address",
                    "name": "caller",
                    "type": "address",
                },
            ],
            "name": "transferFromBridge",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ],
)
# pylint: disable=line-too-long
ierc4626hyperdrive_bytecode = HexStr("0x")


class IERC4626HyperdriveContract(Contract):
    """A web3.py Contract class for the IERC4626Hyperdrive contract."""

    abi: ABI = ierc4626hyperdrive_abi
    bytecode: bytes = HexBytes(ierc4626hyperdrive_bytecode)

    def __init__(self, address: ChecksumAddress | None = None) -> None:
        try:
            # Initialize parent Contract class
            super().__init__(address=address)

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    # TODO: add events
    # events: ERC20ContractEvents

    functions: IERC4626HyperdriveContractFunctions
