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

from .utilities import dataclass_to_tuple, get_abi_input_types, rename_returned_types, try_bytecode_hexbytes

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


class ERC20ForwarderFactoryKindContractFunction(ContractFunction):
    """ContractFunction for the kind method."""

    def __call__(self) -> ERC20ForwarderFactoryKindContractFunction:  # type: ignore
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
    ) -> str:
        """returns str."""
        # Define the expected return types from the smart contract call

        return_types = str

        # Call the function

        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        return cast(str, rename_returned_types(structs, return_types, raw_values))


class ERC20ForwarderFactoryNameContractFunction(ContractFunction):
    """ContractFunction for the name method."""

    def __call__(self) -> ERC20ForwarderFactoryNameContractFunction:  # type: ignore
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
    ) -> str:
        """returns str."""
        # Define the expected return types from the smart contract call

        return_types = str

        # Call the function

        raw_values = super().call(transaction, block_identifier, state_override, ccip_read_enabled)
        return cast(str, rename_returned_types(structs, return_types, raw_values))


class ERC20ForwarderFactoryVersionContractFunction(ContractFunction):
    """ContractFunction for the version method."""

    def __call__(self) -> ERC20ForwarderFactoryVersionContractFunction:  # type: ignore
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

    kind: ERC20ForwarderFactoryKindContractFunction

    name: ERC20ForwarderFactoryNameContractFunction

    version: ERC20ForwarderFactoryVersionContractFunction

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
        self.kind = ERC20ForwarderFactoryKindContractFunction.factory(
            "kind",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="kind",
        )
        self.name = ERC20ForwarderFactoryNameContractFunction.factory(
            "name",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="name",
        )
        self.version = ERC20ForwarderFactoryVersionContractFunction.factory(
            "version",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="version",
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
            "type": "constructor",
            "inputs": [{"name": "_name", "type": "string", "internalType": "string"}],
            "stateMutability": "nonpayable",
        },
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
        {
            "type": "function",
            "name": "kind",
            "inputs": [],
            "outputs": [{"name": "", "type": "string", "internalType": "string"}],
            "stateMutability": "view",
        },
        {
            "type": "function",
            "name": "name",
            "inputs": [],
            "outputs": [{"name": "", "type": "string", "internalType": "string"}],
            "stateMutability": "view",
        },
        {
            "type": "function",
            "name": "version",
            "inputs": [],
            "outputs": [{"name": "", "type": "string", "internalType": "string"}],
            "stateMutability": "view",
        },
        {"type": "error", "name": "InvalidForwarderAddress", "inputs": []},
    ],
)
# pylint: disable=line-too-long
erc20forwarderfactory_bytecode = HexStr(
    "0x6080604052600180546001600160a01b0319168117815560025534801561002557600080fd5b506040516118f13803806118f18339810160408190526100449161006d565b600061005082826101bf565b505061027e565b634e487b7160e01b600052604160045260246000fd5b6000602080838503121561008057600080fd5b82516001600160401b038082111561009757600080fd5b818501915085601f8301126100ab57600080fd5b8151818111156100bd576100bd610057565b604051601f8201601f19908116603f011681019083821181831017156100e5576100e5610057565b8160405282815288868487010111156100fd57600080fd5b600093505b8284101561011f5784840186015181850187015292850192610102565b600086848301015280965050505050505092915050565b600181811c9082168061014a57607f821691505b60208210810361016a57634e487b7160e01b600052602260045260246000fd5b50919050565b601f8211156101ba57600081815260208120601f850160051c810160208610156101975750805b601f850160051c820191505b818110156101b6578281556001016101a3565b5050505b505050565b81516001600160401b038111156101d8576101d8610057565b6101ec816101e68454610136565b84610170565b602080601f83116001811461022157600084156102095750858301515b600019600386901b1c1916600185901b1785556101b6565b600085815260208120601f198616915b8281101561025057888601518255948401946001909101908401610231565b508582101561026e5787850151600019600388901b60f8161c191681555b5050505050600190811b01905550565b6116648061028d6000396000f3fe608060405234801561001057600080fd5b506004361061007d5760003560e01c80630ecaea731161005b5780630ecaea73146100ff57806354fd4d5014610112578063600eb4ba14610138578063d13053bb1461016e57600080fd5b806304baa00b1461008257806306fdde03146100cc5780630710fd58146100d4575b600080fd5b6100b6604051806040016040528060158152602001744552433230466f72776172646572466163746f727960581b81525081565b6040516100c391906103fe565b60405180910390f35b6100b6610184565b6100e76100e236600461044c565b610212565b6040516001600160a01b0390911681526020016100c3565b6100e761010d36600461044c565b6102e7565b6100b6604051806040016040528060078152602001663b18971817189b60c91b81525081565b61014f6001546002546001600160a01b0390911691565b604080516001600160a01b0390931683526020830191909152016100c3565b6101766103c4565b6040519081526020016100c3565b6000805461019190610484565b80601f01602080910402602001604051908101604052809291908181526020018280546101bd90610484565b801561020a5780601f106101df5761010080835404028352916020019161020a565b820191906000526020600020905b8154815290600101906020018083116101ed57829003601f168201915b505050505081565b604080516001600160a01b03841660208201529081018290526000908190606001604051602081830303815290604052805190602001209050600060ff60f81b308360405180602001610264906103f1565b6020820181038252601f19601f82011660405250805190602001206040516020016102c694939291906001600160f81b031994909416845260609290921b6bffffffffffffffffffffffff191660018401526015830152603582015260550190565b60408051808303601f19018152919052805160209091012095945050505050565b6002819055600180546001600160a01b0319166001600160a01b0384169081179091556040805160208101929092528101829052600090819060600160405160208183030381529060405280519060200120905060008160405161034a906103f1565b8190604051809103906000f590508015801561036a573d6000803e3d6000fd5b5090506103778585610212565b6001600160a01b0316816001600160a01b0316146103a75760405162e0775560e61b815260040160405180910390fd5b600180546001600160a01b03191681178155600255949350505050565b6040516103d3602082016103f1565b6020820181038252601f19601f820116604052508051906020012081565b611170806104bf83390190565b600060208083528351808285015260005b8181101561042b5785810183015185820160400152820161040f565b506000604082860101526040601f19601f8301168501019250505092915050565b6000806040838503121561045f57600080fd5b82356001600160a01b038116811461047657600080fd5b946020939093013593505050565b600181811c9082168061049857607f821691505b6020821081036104b857634e487b7160e01b600052602260045260246000fd5b5091905056fe60c060405234801561001057600080fd5b50604080516330075a5d60e11b815281513392839263600eb4ba92600480830193928290030181865afa15801561004b573d6000803e3d6000fd5b505050506040513d601f19601f8201168201806040525081019061006f9190610084565b60a0526001600160a01b0316608052506100be565b6000806040838503121561009757600080fd5b82516001600160a01b03811681146100ae57600080fd5b6020939093015192949293505050565b60805160a05161100861016860003960008181610183015281816102f5015281816103a9015281816104a70152818161055201528181610664015281816107190152818161078801528181610a4d0152610bf50152600081816102ad0152818161031e015281816103ef015281816104d0015281816105a00152818161069d01528181610742015281816107d801528181610a8a01528181610b6b0152610c3301526110086000f3fe608060405234801561001057600080fd5b506004361061010b5760003560e01c806354fd4d50116100a2578063a9059cbb11610071578063a9059cbb14610265578063d505accf14610278578063dd62ed3e1461028d578063f698da25146102a0578063fc0c546a146102a857600080fd5b806354fd4d501461020457806370a082311461022a5780637ecebe001461023d57806395d89b411461025d57600080fd5b806318160ddd116100de57806318160ddd146101b357806323b872dd146101bb57806330adf81f146101ce578063313ce567146101f557600080fd5b806304baa00b1461011057806306fdde0314610153578063095ea7b31461015b57806317d70f7c1461017e575b600080fd5b61013d6040518060400160405280600e81526020016d22a92199182337b93bb0b93232b960911b81525081565b60405161014a9190610d57565b60405180910390f35b61013d6102e7565b61016e610169366004610da6565b61039a565b604051901515815260200161014a565b6101a57f000000000000000000000000000000000000000000000000000000000000000081565b60405190815260200161014a565b6101a5610498565b61016e6101c9366004610dd0565b610543565b6101a57f6e71edae12b1b97f4d1f60370fef10105fa2faae0126114a169c64845d6126c981565b6040516012815260200161014a565b61013d604051806040016040528060078152602001663b18971817189b60c91b81525081565b6101a5610238366004610e0c565b610655565b6101a561024b366004610e0c565b60006020819052908152604090205481565b61013d61070a565b61016e610273366004610da6565b610779565b61028b610286366004610e2e565b610873565b005b6101a561029b366004610ea1565b610b41565b6101a5610ca5565b6102cf7f000000000000000000000000000000000000000000000000000000000000000081565b6040516001600160a01b03909116815260200161014a565b604051622b600360e21b81527f000000000000000000000000000000000000000000000000000000000000000060048201526060907f00000000000000000000000000000000000000000000000000000000000000006001600160a01b03169062ad800c906024015b600060405180830381865afa15801561036d573d6000803e3d6000fd5b505050506040513d6000823e601f3d908101601f191682016040526103959190810190610eea565b905090565b6040516313b4b5ab60e21b81527f000000000000000000000000000000000000000000000000000000000000000060048201526001600160a01b038381166024830152604482018390523360648301526000917f000000000000000000000000000000000000000000000000000000000000000090911690634ed2d6ac90608401600060405180830381600087803b15801561043557600080fd5b505af1158015610449573d6000803e3d6000fd5b50506040518481526001600160a01b03861692503391507f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925906020015b60405180910390a35060015b92915050565b60405163bd85b03960e01b81527f000000000000000000000000000000000000000000000000000000000000000060048201526000907f00000000000000000000000000000000000000000000000000000000000000006001600160a01b03169063bd85b03990602401602060405180830381865afa15801561051f573d6000803e3d6000fd5b505050506040513d601f19601f820116820180604052508101906103959190610f97565b604051633912022f60e21b81527f000000000000000000000000000000000000000000000000000000000000000060048201526001600160a01b0384811660248301528381166044830152606482018390523360848301526000917f00000000000000000000000000000000000000000000000000000000000000009091169063e44808bc9060a401600060405180830381600087803b1580156105e657600080fd5b505af11580156105fa573d6000803e3d6000fd5b50505050826001600160a01b0316846001600160a01b03167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef8460405161064391815260200190565b60405180910390a35060019392505050565b604051631b2b776160e11b81527f000000000000000000000000000000000000000000000000000000000000000060048201526001600160a01b0382811660248301526000917f000000000000000000000000000000000000000000000000000000000000000090911690633656eec290604401602060405180830381865afa1580156106e6573d6000803e3d6000fd5b505050506040513d601f19601f820116820180604052508101906104929190610f97565b604051634e41a1fb60e01b81527f000000000000000000000000000000000000000000000000000000000000000060048201526060907f00000000000000000000000000000000000000000000000000000000000000006001600160a01b031690634e41a1fb90602401610350565b604051633912022f60e21b81527f0000000000000000000000000000000000000000000000000000000000000000600482015233602482018190526001600160a01b0384811660448401526064830184905260848301919091526000917f00000000000000000000000000000000000000000000000000000000000000009091169063e44808bc9060a401600060405180830381600087803b15801561081e57600080fd5b505af1158015610832573d6000803e3d6000fd5b50506040518481526001600160a01b03861692503391507fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef90602001610486565b834211156108945760405163f87d927160e01b815260040160405180910390fd5b6001600160a01b0387166108bb5760405163f0dd15fd60e01b815260040160405180910390fd5b6001600160a01b038716600090815260208190526040812054906108dd610ca5565b604080517f6e71edae12b1b97f4d1f60370fef10105fa2faae0126114a169c64845d6126c960208201526001600160a01b03808d1692820192909252908a1660608201526080810189905260a0810184905260c0810188905260e0016040516020818303038152906040528051906020012060405160200161097692919061190160f01b81526002810192909252602282015260420190565b60408051601f198184030181528282528051602091820120600080855291840180845281905260ff89169284019290925260608301879052608083018690529092509060019060a0016020604051602081039080840390855afa1580156109e1573d6000803e3d6000fd5b505050602060405103519050896001600160a01b0316816001600160a01b031614610a1f57604051638baa579f60e01b815260040160405180910390fd5b6001600160a01b03808b1660008181526020819052604090819020600187019055516313b4b5ab60e21b81527f000000000000000000000000000000000000000000000000000000000000000060048201528b83166024820152604481018b905260648101919091527f000000000000000000000000000000000000000000000000000000000000000090911690634ed2d6ac90608401600060405180830381600087803b158015610ad057600080fd5b505af1158015610ae4573d6000803e3d6000fd5b50505050886001600160a01b03168a6001600160a01b03167f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b9258a604051610b2d91815260200190565b60405180910390a350505050505050505050565b60405163e985e9c560e01b81526001600160a01b03838116600483015282811660248301526000917f00000000000000000000000000000000000000000000000000000000000000009091169063e985e9c590604401602060405180830381865afa158015610bb4573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610bd89190610fb0565b15610be65750600019610492565b6040516321ff32a960e01b81527f000000000000000000000000000000000000000000000000000000000000000060048201526001600160a01b03848116602483015283811660448301527f000000000000000000000000000000000000000000000000000000000000000016906321ff32a990606401602060405180830381865afa158015610c7a573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610c9e9190610f97565b9050610492565b60408051808201825260018152603160f81b60209182015281517f2aef22f9d7df5f9d21c56d14029233f3fdaa91917727e1eb68e504d27072d6cd818301527fc89efdaa54c0f20c7adf612882df0950f5a951637e0307cdcb4c672f298b8bc681840152466060820152306080808301919091528351808303909101815260a0909101909252815191012090565b60005b83811015610d4e578181015183820152602001610d36565b50506000910152565b6020815260008251806020840152610d76816040850160208701610d33565b601f01601f19169190910160400192915050565b80356001600160a01b0381168114610da157600080fd5b919050565b60008060408385031215610db957600080fd5b610dc283610d8a565b946020939093013593505050565b600080600060608486031215610de557600080fd5b610dee84610d8a565b9250610dfc60208501610d8a565b9150604084013590509250925092565b600060208284031215610e1e57600080fd5b610e2782610d8a565b9392505050565b600080600080600080600060e0888a031215610e4957600080fd5b610e5288610d8a565b9650610e6060208901610d8a565b95506040880135945060608801359350608088013560ff81168114610e8457600080fd5b9699959850939692959460a0840135945060c09093013592915050565b60008060408385031215610eb457600080fd5b610ebd83610d8a565b9150610ecb60208401610d8a565b90509250929050565b634e487b7160e01b600052604160045260246000fd5b600060208284031215610efc57600080fd5b815167ffffffffffffffff80821115610f1457600080fd5b818401915084601f830112610f2857600080fd5b815181811115610f3a57610f3a610ed4565b604051601f8201601f19908116603f01168101908382118183101715610f6257610f62610ed4565b81604052828152876020848701011115610f7b57600080fd5b610f8c836020830160208801610d33565b979650505050505050565b600060208284031215610fa957600080fd5b5051919050565b600060208284031215610fc257600080fd5b81518015158114610e2757600080fdfea2646970667358221220762ce9710139decaa30c0ed41576747df74c0cd567830cb1e6d61abdb008e54164736f6c63430008140033a2646970667358221220248110d6fabf2dc3078f5aee10ebc7910d668ec3cb8b328a117b8a1d2c111f8764736f6c63430008140033"
)


class ERC20ForwarderFactoryContract(Contract):
    """A web3.py Contract class for the ERC20ForwarderFactory contract."""

    abi: ABI = erc20forwarderfactory_abi
    bytecode: bytes | None = try_bytecode_hexbytes(erc20forwarderfactory_bytecode, "erc20forwarderfactory")

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

    class ConstructorArgs(NamedTuple):
        """Arguments to pass the contract's constructor function."""

        name: str

    @classmethod
    def constructor(cls, name: str) -> ContractConstructor:  # type: ignore
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

        return super().constructor(dataclass_to_tuple(name))

    @classmethod
    def deploy(cls, w3: Web3, account: LocalAccount | ChecksumAddress, constructorArgs: ConstructorArgs) -> Self:
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
        constructor_fn = deployer.constructor(*constructorArgs)

        # if an address is supplied, try to use a web3 default account
        if isinstance(account, str):
            tx_hash = constructor_fn.transact({"from": account})
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            deployed_contract = deployer(address=tx_receipt.contractAddress)  # type: ignore
            return deployed_contract

        # otherwise use the account provided.
        deployment_tx = constructor_fn.build_transaction()
        current_nonce = w3.eth.get_transaction_count(account.address, "pending")
        deployment_tx.update({"nonce": current_nonce})

        # Sign the transaction with local account private key
        signed_tx = account.sign_transaction(deployment_tx)

        # Send the signed transaction and wait for receipt
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
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
