"""A web3.py Contract class for the ERC20ForwarderFactory contract.

DO NOT EDIT.  This file was generated by pypechain.  See documentation at
https://github.com/delvtech/pypechain"""

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

# methods are overriden with specific arguments instead of generic *args, **kwargs
# pylint: disable=arguments-differ

# consumers have too many opinions on line length
# pylint: disable=line-too-long


from __future__ import annotations

from typing import Any, NamedTuple, Type, cast

from eth_abi.codec import ABICodec
from eth_abi.registry import registry as default_registry
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress, HexStr
from hexbytes import HexBytes
from typing_extensions import Self
from web3 import Web3
from web3.contract.contract import Contract, ContractConstructor, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound
from web3.types import ABI, ABIFunction, BlockIdentifier, CallOverride, TxParams

from .utilities import dataclass_to_tuple, get_abi_input_types, rename_returned_types

structs = {}


class ERC20ForwarderFactoryERC20LINK_HASHContractFunction(ContractFunction):
    """ContractFunction for the ERC20LINK_HASH method."""

    def __call__(self) -> ERC20ForwarderFactoryERC20LINK_HASHContractFunction:  # type: ignore
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> bytes:
        """returns bytes."""
        # Define the expected return types from the smart contract call

        return_types = bytes

        # Call the function

        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        return cast(bytes, rename_returned_types(structs, return_types, raw_values))


class ERC20ForwarderFactoryCreateContractFunction(ContractFunction):
    """ContractFunction for the create method."""

    def __call__(self, token: str, tokenId: int) -> ERC20ForwarderFactoryCreateContractFunction:  # type: ignore
        clone = super().__call__(dataclass_to_tuple(token), dataclass_to_tuple(tokenId))
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """returns str."""
        # Define the expected return types from the smart contract call

        return_types = str

        # Call the function

        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        return cast(str, rename_returned_types(structs, return_types, raw_values))


class ERC20ForwarderFactoryGetDeployDetailsContractFunction(ContractFunction):
    """ContractFunction for the getDeployDetails method."""

    class ReturnValues(NamedTuple):
        """The return named tuple for GetDeployDetails."""

        arg1: str
        arg2: int

    def __call__(self) -> ERC20ForwarderFactoryGetDeployDetailsContractFunction:  # type: ignore
        clone = super().__call__()
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> ReturnValues:
        """returns ReturnValues."""
        # Define the expected return types from the smart contract call

        return_types = [str, int]

        # Call the function

        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        return self.ReturnValues(*rename_returned_types(structs, return_types, raw_values))


class ERC20ForwarderFactoryGetForwarderContractFunction(ContractFunction):
    """ContractFunction for the getForwarder method."""

    def __call__(self, token: str, tokenId: int) -> ERC20ForwarderFactoryGetForwarderContractFunction:  # type: ignore
        clone = super().__call__(dataclass_to_tuple(token), dataclass_to_tuple(tokenId))
        self.kwargs = clone.kwargs
        self.args = clone.args
        return self

    def call(
        self,
        transaction: TxParams | None = None,
        block_identifier: BlockIdentifier = "latest",
        state_override: CallOverride | None = None,
        ccip_read_enabled: bool | None = None,
    ) -> str:
        """returns str."""
        # Define the expected return types from the smart contract call

        return_types = str

        # Call the function

        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        return cast(str, rename_returned_types(structs, return_types, raw_values))


class ERC20ForwarderFactoryContractFunctions(ContractFunctions):
    """ContractFunctions for the ERC20ForwarderFactory contract."""

    ERC20LINK_HASH: ERC20ForwarderFactoryERC20LINK_HASHContractFunction

    create: ERC20ForwarderFactoryCreateContractFunction

    getDeployDetails: ERC20ForwarderFactoryGetDeployDetailsContractFunction

    getForwarder: ERC20ForwarderFactoryGetForwarderContractFunction

    def __init__(
        self,
        abi: ABI,
        w3: "Web3",
        address: ChecksumAddress | None = None,
        decode_tuples: bool | None = False,
    ) -> None:
        super().__init__(abi, w3, address, decode_tuples)
        self.ERC20LINK_HASH = ERC20ForwarderFactoryERC20LINK_HASHContractFunction.factory(
            "ERC20LINK_HASH",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="ERC20LINK_HASH",
        )
        self.create = ERC20ForwarderFactoryCreateContractFunction.factory(
            "create",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="create",
        )
        self.getDeployDetails = ERC20ForwarderFactoryGetDeployDetailsContractFunction.factory(
            "getDeployDetails",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="getDeployDetails",
        )
        self.getForwarder = ERC20ForwarderFactoryGetForwarderContractFunction.factory(
            "getForwarder",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="getForwarder",
        )


class ERC20ForwarderFactoryInvalidForwarderAddressContractError:
    """ContractError for InvalidForwarderAddress."""

    # @combomethod destroys return types, so we are redefining functions as both class and instance
    # pylint: disable=function-redefined

    # 4 byte error selector
    selector: str
    # error signature, i.e. CustomError(uint256,bool)
    signature: str

    # pylint: disable=useless-parent-delegation
    def __init__(
        self: "ERC20ForwarderFactoryInvalidForwarderAddressContractError",
    ) -> None:
        self.selector = "0x381dd540"
        self.signature = "InvalidForwarderAddress()"

    def decode_error_data(  # type: ignore
        self: "ERC20ForwarderFactoryInvalidForwarderAddressContractError",
        data: HexBytes,
        # TODO: instead of returning a tuple, return a dataclass with the input names and types just like we do for functions
    ) -> tuple[Any, ...]:
        """Decodes error data returns from a smart contract."""
        error_abi = cast(
            ABIFunction,
            [
                item
                for item in erc20forwarderfactory_abi
                if item.get("name") == "InvalidForwarderAddress" and item.get("type") == "error"
            ][0],
        )
        types = get_abi_input_types(error_abi)
        abi_codec = ABICodec(default_registry)
        decoded = abi_codec.decode(types, data)
        return decoded

    @classmethod
    def decode_error_data(  # type: ignore
        cls: Type["ERC20ForwarderFactoryInvalidForwarderAddressContractError"],
        data: HexBytes,
    ) -> tuple[Any, ...]:
        """Decodes error data returns from a smart contract."""
        error_abi = cast(
            ABIFunction,
            [
                item
                for item in erc20forwarderfactory_abi
                if item.get("name") == "InvalidForwarderAddress" and item.get("type") == "error"
            ][0],
        )
        types = get_abi_input_types(error_abi)
        abi_codec = ABICodec(default_registry)
        decoded = abi_codec.decode(types, data)
        return decoded


class ERC20ForwarderFactoryContractErrors:
    """ContractErrors for the ERC20ForwarderFactory contract."""

    InvalidForwarderAddress: ERC20ForwarderFactoryInvalidForwarderAddressContractError

    def __init__(
        self,
    ) -> None:
        self.InvalidForwarderAddress = ERC20ForwarderFactoryInvalidForwarderAddressContractError()

        self._all = [
            self.InvalidForwarderAddress,
        ]

    def decode_custom_error(self, data: str) -> tuple[Any, ...]:
        """Decodes a custom contract error."""
        selector = data[:10]
        for err in self._all:
            if err.selector == selector:
                return err.decode_error_data(HexBytes(data[10:]))

        raise ValueError(f"ERC20ForwarderFactory does not have a selector matching {selector}")


erc20forwarderfactory_abi: ABI = cast(
    ABI,
    [
        {
            "type": "function",
            "name": "ERC20LINK_HASH",
            "inputs": [],
            "outputs": [{"name": "", "type": "bytes32", "internalType": "bytes32"}],
            "stateMutability": "view",
        },
        {
            "type": "function",
            "name": "create",
            "inputs": [
                {"name": "__token", "type": "address", "internalType": "contract IMultiToken"},
                {"name": "__tokenId", "type": "uint256", "internalType": "uint256"},
            ],
            "outputs": [{"name": "", "type": "address", "internalType": "contract IERC20Forwarder"}],
            "stateMutability": "nonpayable",
        },
        {
            "type": "function",
            "name": "getDeployDetails",
            "inputs": [],
            "outputs": [
                {"name": "", "type": "address", "internalType": "contract IMultiToken"},
                {"name": "", "type": "uint256", "internalType": "uint256"},
            ],
            "stateMutability": "view",
        },
        {
            "type": "function",
            "name": "getForwarder",
            "inputs": [
                {"name": "__token", "type": "address", "internalType": "contract IMultiToken"},
                {"name": "__tokenId", "type": "uint256", "internalType": "uint256"},
            ],
            "outputs": [{"name": "", "type": "address", "internalType": "address"}],
            "stateMutability": "view",
        },
        {"type": "error", "name": "InvalidForwarderAddress", "inputs": []},
    ],
)
# pylint: disable=line-too-long
erc20forwarderfactory_bytecode = HexStr(
    "0x6080604052600080546001600160a01b0319166001908117909155805534801561002857600080fd5b50611441806100386000396000f3fe608060405234801561001057600080fd5b506004361061004c5760003560e01c80630710fd58146100515780630ecaea7314610081578063600eb4ba14610094578063d13053bb146100ca575b600080fd5b61006461005f3660046102cc565b6100e0565b6040516001600160a01b0390911681526020015b60405180910390f35b61006461008f3660046102cc565b6101b5565b6100ab6000546001546001600160a01b0390911691565b604080516001600160a01b039093168352602083019190915201610078565b6100d2610292565b604051908152602001610078565b604080516001600160a01b03841660208201529081018290526000908190606001604051602081830303815290604052805190602001209050600060ff60f81b308360405180602001610132906102bf565b6020820181038252601f19601f820116604052508051906020012060405160200161019494939291906001600160f81b031994909416845260609290921b6bffffffffffffffffffffffff191660018401526015830152603582015260550190565b60408051808303601f19018152919052805160209091012095945050505050565b6001819055600080546001600160a01b0319166001600160a01b038416908117825560408051602081019290925281018390528190606001604051602081830303815290604052805190602001209050600081604051610214906102bf565b8190604051809103906000f5905080158015610234573d6000803e3d6000fd5b50905061024185856100e0565b6001600160a01b0316816001600160a01b0316146102715760405162e0775560e61b815260040160405180910390fd5b600080546001600160a01b0319166001908117909155805591505092915050565b6040516102a1602082016102bf565b6020820181038252601f19601f820116604052508051906020012081565b6111078061030583390190565b600080604083850312156102df57600080fd5b82356001600160a01b03811681146102f657600080fd5b94602093909301359350505056fe60c060405234801561001057600080fd5b50604080516330075a5d60e11b815281513392839263600eb4ba92600480830193928290030181865afa15801561004b573d6000803e3d6000fd5b505050506040513d601f19601f8201168201806040525081019061006f9190610084565b60a0526001600160a01b0316608052506100be565b6000806040838503121561009757600080fd5b82516001600160a01b03811681146100ae57600080fd5b6020939093015192949293505050565b60805160a051610f9f610168600039600081816101400152818161028c015281816103400152818161043e015281816104e9015281816105fb015281816106b00152818161071f015281816109e40152610b8c015260008181610244015281816102b501528181610386015281816104670152818161053701528181610634015281816106d90152818161076f01528181610a2101528181610b020152610bca0152610f9f6000f3fe608060405234801561001057600080fd5b50600436106100f55760003560e01c806370a0823111610097578063d505accf11610066578063d505accf1461020f578063dd62ed3e14610224578063f698da2514610237578063fc0c546a1461023f57600080fd5b806370a08231146101c15780637ecebe00146101d457806395d89b41146101f4578063a9059cbb146101fc57600080fd5b806318160ddd116100d357806318160ddd1461017057806323b872dd1461017857806330adf81f1461018b578063313ce567146101b257600080fd5b806306fdde03146100fa578063095ea7b31461011857806317d70f7c1461013b575b600080fd5b61010261027e565b60405161010f9190610cee565b60405180910390f35b61012b610126366004610d3d565b610331565b604051901515815260200161010f565b6101627f000000000000000000000000000000000000000000000000000000000000000081565b60405190815260200161010f565b61016261042f565b61012b610186366004610d67565b6104da565b6101627f6e71edae12b1b97f4d1f60370fef10105fa2faae0126114a169c64845d6126c981565b6040516012815260200161010f565b6101626101cf366004610da3565b6105ec565b6101626101e2366004610da3565b60006020819052908152604090205481565b6101026106a1565b61012b61020a366004610d3d565b610710565b61022261021d366004610dc5565b61080a565b005b610162610232366004610e38565b610ad8565b610162610c3c565b6102667f000000000000000000000000000000000000000000000000000000000000000081565b6040516001600160a01b03909116815260200161010f565b604051622b600360e21b81527f000000000000000000000000000000000000000000000000000000000000000060048201526060907f00000000000000000000000000000000000000000000000000000000000000006001600160a01b03169062ad800c906024015b600060405180830381865afa158015610304573d6000803e3d6000fd5b505050506040513d6000823e601f3d908101601f1916820160405261032c9190810190610e81565b905090565b6040516313b4b5ab60e21b81527f000000000000000000000000000000000000000000000000000000000000000060048201526001600160a01b038381166024830152604482018390523360648301526000917f000000000000000000000000000000000000000000000000000000000000000090911690634ed2d6ac90608401600060405180830381600087803b1580156103cc57600080fd5b505af11580156103e0573d6000803e3d6000fd5b50506040518481526001600160a01b03861692503391507f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925906020015b60405180910390a35060015b92915050565b60405163bd85b03960e01b81527f000000000000000000000000000000000000000000000000000000000000000060048201526000907f00000000000000000000000000000000000000000000000000000000000000006001600160a01b03169063bd85b03990602401602060405180830381865afa1580156104b6573d6000803e3d6000fd5b505050506040513d601f19601f8201168201806040525081019061032c9190610f2e565b604051633912022f60e21b81527f000000000000000000000000000000000000000000000000000000000000000060048201526001600160a01b0384811660248301528381166044830152606482018390523360848301526000917f00000000000000000000000000000000000000000000000000000000000000009091169063e44808bc9060a401600060405180830381600087803b15801561057d57600080fd5b505af1158015610591573d6000803e3d6000fd5b50505050826001600160a01b0316846001600160a01b03167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef846040516105da91815260200190565b60405180910390a35060019392505050565b604051631b2b776160e11b81527f000000000000000000000000000000000000000000000000000000000000000060048201526001600160a01b0382811660248301526000917f000000000000000000000000000000000000000000000000000000000000000090911690633656eec290604401602060405180830381865afa15801561067d573d6000803e3d6000fd5b505050506040513d601f19601f820116820180604052508101906104299190610f2e565b604051634e41a1fb60e01b81527f000000000000000000000000000000000000000000000000000000000000000060048201526060907f00000000000000000000000000000000000000000000000000000000000000006001600160a01b031690634e41a1fb906024016102e7565b604051633912022f60e21b81527f0000000000000000000000000000000000000000000000000000000000000000600482015233602482018190526001600160a01b0384811660448401526064830184905260848301919091526000917f00000000000000000000000000000000000000000000000000000000000000009091169063e44808bc9060a401600060405180830381600087803b1580156107b557600080fd5b505af11580156107c9573d6000803e3d6000fd5b50506040518481526001600160a01b03861692503391507fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef9060200161041d565b8342111561082b5760405163f87d927160e01b815260040160405180910390fd5b6001600160a01b0387166108525760405163f0dd15fd60e01b815260040160405180910390fd5b6001600160a01b03871660009081526020819052604081205490610874610c3c565b604080517f6e71edae12b1b97f4d1f60370fef10105fa2faae0126114a169c64845d6126c960208201526001600160a01b03808d1692820192909252908a1660608201526080810189905260a0810184905260c0810188905260e0016040516020818303038152906040528051906020012060405160200161090d92919061190160f01b81526002810192909252602282015260420190565b60408051601f198184030181528282528051602091820120600080855291840180845281905260ff89169284019290925260608301879052608083018690529092509060019060a0016020604051602081039080840390855afa158015610978573d6000803e3d6000fd5b505050602060405103519050896001600160a01b0316816001600160a01b0316146109b657604051638baa579f60e01b815260040160405180910390fd5b6001600160a01b03808b1660008181526020819052604090819020600187019055516313b4b5ab60e21b81527f000000000000000000000000000000000000000000000000000000000000000060048201528b83166024820152604481018b905260648101919091527f000000000000000000000000000000000000000000000000000000000000000090911690634ed2d6ac90608401600060405180830381600087803b158015610a6757600080fd5b505af1158015610a7b573d6000803e3d6000fd5b50505050886001600160a01b03168a6001600160a01b03167f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b9258a604051610ac491815260200190565b60405180910390a350505050505050505050565b60405163e985e9c560e01b81526001600160a01b03838116600483015282811660248301526000917f00000000000000000000000000000000000000000000000000000000000000009091169063e985e9c590604401602060405180830381865afa158015610b4b573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610b6f9190610f47565b15610b7d5750600019610429565b6040516321ff32a960e01b81527f000000000000000000000000000000000000000000000000000000000000000060048201526001600160a01b03848116602483015283811660448301527f000000000000000000000000000000000000000000000000000000000000000016906321ff32a990606401602060405180830381865afa158015610c11573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610c359190610f2e565b9050610429565b60408051808201825260018152603160f81b60209182015281517f2aef22f9d7df5f9d21c56d14029233f3fdaa91917727e1eb68e504d27072d6cd818301527fc89efdaa54c0f20c7adf612882df0950f5a951637e0307cdcb4c672f298b8bc681840152466060820152306080808301919091528351808303909101815260a0909101909252815191012090565b60005b83811015610ce5578181015183820152602001610ccd565b50506000910152565b6020815260008251806020840152610d0d816040850160208701610cca565b601f01601f19169190910160400192915050565b80356001600160a01b0381168114610d3857600080fd5b919050565b60008060408385031215610d5057600080fd5b610d5983610d21565b946020939093013593505050565b600080600060608486031215610d7c57600080fd5b610d8584610d21565b9250610d9360208501610d21565b9150604084013590509250925092565b600060208284031215610db557600080fd5b610dbe82610d21565b9392505050565b600080600080600080600060e0888a031215610de057600080fd5b610de988610d21565b9650610df760208901610d21565b95506040880135945060608801359350608088013560ff81168114610e1b57600080fd5b9699959850939692959460a0840135945060c09093013592915050565b60008060408385031215610e4b57600080fd5b610e5483610d21565b9150610e6260208401610d21565b90509250929050565b634e487b7160e01b600052604160045260246000fd5b600060208284031215610e9357600080fd5b815167ffffffffffffffff80821115610eab57600080fd5b818401915084601f830112610ebf57600080fd5b815181811115610ed157610ed1610e6b565b604051601f8201601f19908116603f01168101908382118183101715610ef957610ef9610e6b565b81604052828152876020848701011115610f1257600080fd5b610f23836020830160208801610cca565b979650505050505050565b600060208284031215610f4057600080fd5b5051919050565b600060208284031215610f5957600080fd5b81518015158114610dbe57600080fdfea26469706673582212207258039ff824d28f4da7cc32f9d3373484e3d58ab2672cc25f41326b384ac05c64736f6c63430008140033a2646970667358221220cd312764165d237ba8e4a3b9e656c15ee231868a85df1f0251af4e8df57cdb4d64736f6c63430008140033"
)


class ERC20ForwarderFactoryContract(Contract):
    """A web3.py Contract class for the ERC20ForwarderFactory contract."""

    abi: ABI = erc20forwarderfactory_abi
    bytecode: bytes = HexBytes(erc20forwarderfactory_bytecode)

    def __init__(self, address: ChecksumAddress | None = None) -> None:
        try:
            # Initialize parent Contract class
            super().__init__(address=address)
            self.functions = ERC20ForwarderFactoryContractFunctions(erc20forwarderfactory_abi, self.w3, address)  # type: ignore

            self.errors = ERC20ForwarderFactoryContractErrors()

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    errors: ERC20ForwarderFactoryContractErrors = ERC20ForwarderFactoryContractErrors()

    functions: ERC20ForwarderFactoryContractFunctions

    @classmethod
    def constructor(cls) -> ContractConstructor:  # type: ignore
        """Creates a transaction with the contract's constructor function.

        Parameters
        ----------

        w3 : Web3
            A web3 instance.
        account : LocalAccount
            The account to use to deploy the contract.

        Returns
        -------
        Self
            A deployed instance of the contract.

        """

        return super().constructor()

    @classmethod
    def deploy(cls, w3: Web3, account: LocalAccount | ChecksumAddress) -> Self:
        """Deploys and instance of the contract.

        Parameters
        ----------
        w3 : Web3
            A web3 instance.
        account : LocalAccount
            The account to use to deploy the contract.

        Returns
        -------
        Self
            A deployed instance of the contract.
        """
        deployer = cls.factory(w3=w3)
        constructor_fn = deployer.constructor()

        # if an address is supplied, try to use a web3 default account
        if isinstance(account, str):
            tx_hash = constructor_fn.transact({"from": account})
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            deployed_contract = deployer(address=tx_receipt.contractAddress)  # type: ignore
            return deployed_contract

        # otherwise use the account provided.
        deployment_tx = constructor_fn.build_transaction()
        current_nonce = w3.eth.get_transaction_count(account.address)
        deployment_tx.update({"nonce": current_nonce})

        # Sign the transaction with local account private key
        signed_tx = account.sign_transaction(deployment_tx)

        # Send the signed transaction and wait for receipt
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        deployed_contract = deployer(address=tx_receipt.contractAddress)  # type: ignore
        return deployed_contract

    @classmethod
    def factory(cls, w3: Web3, class_name: str | None = None, **kwargs: Any) -> Type[Self]:
        """Deploys and instance of the contract.

        Parameters
        ----------
        w3 : Web3
            A web3 instance.
        class_name: str | None
            The instance class name.

        Returns
        -------
        Self
            A deployed instance of the contract.
        """
        contract = super().factory(w3, class_name, **kwargs)
        contract.functions = ERC20ForwarderFactoryContractFunctions(erc20forwarderfactory_abi, w3, None)
        contract.errors = ERC20ForwarderFactoryContractErrors()

        return contract
