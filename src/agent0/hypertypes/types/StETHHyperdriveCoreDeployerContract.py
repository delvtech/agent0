"""A web3.py Contract class for the StETHHyperdriveCoreDeployer contract.

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

from typing import Any, Type, cast

from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress, HexStr
from typing_extensions import Self
from web3 import Web3
from web3.contract.contract import Contract, ContractConstructor, ContractFunction, ContractFunctions
from web3.exceptions import FallbackNotFound
from web3.types import ABI, BlockIdentifier, CallOverride, TxParams

from .IHyperdriveTypes import Fees, PoolConfig
from .utilities import dataclass_to_tuple, rename_returned_types, try_bytecode_hexbytes

structs = {
    "Fees": Fees,
    "PoolConfig": PoolConfig,
}


class StETHHyperdriveCoreDeployerDeployHyperdriveContractFunction(ContractFunction):
    """ContractFunction for the deployHyperdrive method."""

    def __call__(self, name: str, config: PoolConfig, arg3: bytes, target0: str, target1: str, target2: str, target3: str, target4: str, salt: bytes) -> StETHHyperdriveCoreDeployerDeployHyperdriveContractFunction:  # type: ignore
        clone = super().__call__(
            dataclass_to_tuple(name),
            dataclass_to_tuple(config),
            dataclass_to_tuple(arg3),
            dataclass_to_tuple(target0),
            dataclass_to_tuple(target1),
            dataclass_to_tuple(target2),
            dataclass_to_tuple(target3),
            dataclass_to_tuple(target4),
            dataclass_to_tuple(salt),
        )
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


class StETHHyperdriveCoreDeployerContractFunctions(ContractFunctions):
    """ContractFunctions for the StETHHyperdriveCoreDeployer contract."""

    deployHyperdrive: StETHHyperdriveCoreDeployerDeployHyperdriveContractFunction

    def __init__(
        self,
        abi: ABI,
        w3: "Web3",
        address: ChecksumAddress | None = None,
        decode_tuples: bool | None = False,
    ) -> None:
        super().__init__(abi, w3, address, decode_tuples)
        self.deployHyperdrive = StETHHyperdriveCoreDeployerDeployHyperdriveContractFunction.factory(
            "deployHyperdrive",
            w3=w3,
            contract_abi=abi,
            address=address,
            decode_tuples=decode_tuples,
            function_identifier="deployHyperdrive",
        )


stethhyperdrivecoredeployer_abi: ABI = cast(
    ABI,
    [
        {
            "type": "function",
            "name": "deployHyperdrive",
            "inputs": [
                {"name": "__name", "type": "string", "internalType": "string"},
                {
                    "name": "_config",
                    "type": "tuple",
                    "internalType": "struct IHyperdrive.PoolConfig",
                    "components": [
                        {"name": "baseToken", "type": "address", "internalType": "contract IERC20"},
                        {"name": "vaultSharesToken", "type": "address", "internalType": "contract IERC20"},
                        {"name": "linkerFactory", "type": "address", "internalType": "address"},
                        {"name": "linkerCodeHash", "type": "bytes32", "internalType": "bytes32"},
                        {"name": "initialVaultSharePrice", "type": "uint256", "internalType": "uint256"},
                        {"name": "minimumShareReserves", "type": "uint256", "internalType": "uint256"},
                        {"name": "minimumTransactionAmount", "type": "uint256", "internalType": "uint256"},
                        {"name": "circuitBreakerDelta", "type": "uint256", "internalType": "uint256"},
                        {"name": "positionDuration", "type": "uint256", "internalType": "uint256"},
                        {"name": "checkpointDuration", "type": "uint256", "internalType": "uint256"},
                        {"name": "timeStretch", "type": "uint256", "internalType": "uint256"},
                        {"name": "governance", "type": "address", "internalType": "address"},
                        {"name": "feeCollector", "type": "address", "internalType": "address"},
                        {"name": "sweepCollector", "type": "address", "internalType": "address"},
                        {"name": "checkpointRewarder", "type": "address", "internalType": "address"},
                        {
                            "name": "fees",
                            "type": "tuple",
                            "internalType": "struct IHyperdrive.Fees",
                            "components": [
                                {"name": "curve", "type": "uint256", "internalType": "uint256"},
                                {"name": "flat", "type": "uint256", "internalType": "uint256"},
                                {"name": "governanceLP", "type": "uint256", "internalType": "uint256"},
                                {"name": "governanceZombie", "type": "uint256", "internalType": "uint256"},
                            ],
                        },
                    ],
                },
                {"name": "", "type": "bytes", "internalType": "bytes"},
                {"name": "_target0", "type": "address", "internalType": "address"},
                {"name": "_target1", "type": "address", "internalType": "address"},
                {"name": "_target2", "type": "address", "internalType": "address"},
                {"name": "_target3", "type": "address", "internalType": "address"},
                {"name": "_target4", "type": "address", "internalType": "address"},
                {"name": "_salt", "type": "bytes32", "internalType": "bytes32"},
            ],
            "outputs": [{"name": "", "type": "address", "internalType": "address"}],
            "stateMutability": "nonpayable",
        }
    ],
)
# pylint: disable=line-too-long
stethhyperdrivecoredeployer_bytecode = HexStr(
    "0x608060405234801561001057600080fd5b50611e8c806100206000396000f3fe60806040523480156200001157600080fd5b50600436106200002e5760003560e01c8063285fd4011462000033575b600080fd5b6200004a620000443660046200037c565b62000066565b6040516001600160a01b03909116815260200160405180910390f35b60408051336020820152908101829052600090606001604051602081830303815290604052805190602001208a8a8989898989604051620000a790620000e9565b620000b99796959493929190620005a0565b8190604051809103906000f5905080158015620000da573d6000803e3d6000fd5b509a9950505050505050505050565b611813806200064483390190565b634e487b7160e01b600052604160045260246000fd5b604051610200810167ffffffffffffffff81118282101715620001345762000134620000f7565b60405290565b600067ffffffffffffffff80841115620001585762000158620000f7565b604051601f8501601f19908116603f01168101908282118183101715620001835762000183620000f7565b816040528093508581528686860111156200019d57600080fd5b858560208301376000602087830101525050509392505050565b80356001600160a01b0381168114620001cf57600080fd5b919050565b600060808284031215620001e757600080fd5b6040516080810181811067ffffffffffffffff821117156200020d576200020d620000f7565b8060405250809150823581526020830135602082015260408301356040820152606083013560608201525092915050565b600061026082840312156200025257600080fd5b6200025c6200010d565b90506200026982620001b7565b81526200027960208301620001b7565b60208201526200028c60408301620001b7565b6040820152606082013560608201526080820135608082015260a082013560a082015260c082013560c082015260e082013560e0820152610100808301358183015250610120808301358183015250610140808301358183015250610160620002f7818401620001b7565b908201526101806200030b838201620001b7565b908201526101a06200031f838201620001b7565b908201526101c062000333838201620001b7565b908201526101e06200034884848301620001d4565b9082015292915050565b600082601f8301126200036457600080fd5b62000375838335602085016200013a565b9392505050565b60008060008060008060008060006103608a8c0312156200039c57600080fd5b893567ffffffffffffffff80821115620003b557600080fd5b818c0191508c601f830112620003ca57600080fd5b620003db8d8335602085016200013a565b9a50620003ec8d60208e016200023e565b99506102808c01359150808211156200040457600080fd5b50620004138c828d0162000352565b975050620004256102a08b01620001b7565b9550620004366102c08b01620001b7565b9450620004476102e08b01620001b7565b9350620004586103008b01620001b7565b9250620004696103208b01620001b7565b91506103408a013590509295985092959850929598565b80516001600160a01b031682526020810151620004a860208401826001600160a01b03169052565b506040810151620004c460408401826001600160a01b03169052565b50606081015160608301526080810151608083015260a081015160a083015260c081015160c083015260e081015160e08301526101008082015181840152506101208082015181840152506101408082015181840152506101608082015162000537828501826001600160a01b03169052565b5050610180818101516001600160a01b03908116918401919091526101a0808301518216908401526101c080830151909116908301526101e090810151805191830191909152602081015161020083015260408101516102208301526060015161024090910152565b600061032080835289518082850152600091505b80821015620005d8576020828c0101516103408386010152602082019150620005b4565b6103409150600082828601015281601f19601f8301168501019250505062000604602083018962000480565b6001600160a01b039687166102808301529486166102a08201529285166102c08401529084166102e0830152909216610300909201919091529291505056fe6103006040523480156200001257600080fd5b506040516200181338038062001813833981016040819052620000359162000397565b6001600081905586516001600160a01b0390811660809081526020808a0151831660a0908152918a01516101a0908152918a01516101c090815260c0808c01516101e090815260e0808e015161020052610120808f0151909352610100808f0151909152610140808f0151909152908d0180515190925281519093015190925281516040908101516101609081529251606090810151610180908152918d01518616610220528c015161024052918b0151600980549186166001600160a01b0319928316179055918b0151600a8054918616918416919091179055918a0151600b805491851691831691909117905590890151600c805491909316911617905587908790879087908790879087906200014f888262000553565b506001600160a01b0394851661026052928416610280529083166102a05282166102c052166102e052506200061f975050505050505050565b634e487b7160e01b600052604160045260246000fd5b60405161020081016001600160401b0381118282101715620001c457620001c462000188565b60405290565b604051601f8201601f191681016001600160401b0381118282101715620001f557620001f562000188565b604052919050565b80516001600160a01b03811681146200021557600080fd5b919050565b6000608082840312156200022d57600080fd5b604051608081016001600160401b038111828210171562000252576200025262000188565b8060405250809150825181526020830151602082015260408301516040820152606083015160608201525092915050565b600061026082840312156200029757600080fd5b620002a16200019e565b9050620002ae82620001fd565b8152620002be60208301620001fd565b6020820152620002d160408301620001fd565b6040820152606082015160608201526080820151608082015260a082015160a082015260c082015160c082015260e082015160e08201526101008083015181830152506101208083015181830152506101408083015181830152506101606200033c818401620001fd565b9082015261018062000350838201620001fd565b908201526101a062000364838201620001fd565b908201526101c062000378838201620001fd565b908201526101e06200038d848483016200021a565b9082015292915050565b6000806000806000806000610320888a031215620003b457600080fd5b87516001600160401b0380821115620003cc57600080fd5b818a0191508a601f830112620003e157600080fd5b815181811115620003f657620003f662000188565b602091506200040e601f8201601f19168301620001ca565b8181528c838386010111156200042357600080fd5b60005b828110156200044357848101840151828201850152830162000426565b506000838383010152809a5050506200045f8b828c0162000283565b97505050620004726102808901620001fd565b9450620004836102a08901620001fd565b9350620004946102c08901620001fd565b9250620004a56102e08901620001fd565b9150620004b66103008901620001fd565b905092959891949750929550565b600181811c90821680620004d957607f821691505b602082108103620004fa57634e487b7160e01b600052602260045260246000fd5b50919050565b601f8211156200054e57600081815260208120601f850160051c81016020861015620005295750805b601f850160051c820191505b818110156200054a5782815560010162000535565b5050505b505050565b81516001600160401b038111156200056f576200056f62000188565b6200058781620005808454620004c4565b8462000500565b602080601f831160018114620005bf5760008415620005a65750858301515b600019600386901b1c1916600185901b1785556200054a565b600085815260208120601f198616915b82811015620005f057888601518255948401946001909101908401620005cf565b50858210156200060f5787850151600019600388901b60f8161c191681555b5050505050600190811b01905550565b60805160a05160c05160e05161010051610120516101405161016051610180516101a0516101c0516101e05161020051610220516102405161026051610280516102a0516102c0516102e0516110ce620007456000396000818161060f0152818161067b0152610774015260008181610587015281816107a40152610802015260008181610540015261099d0152600081816105db01526107110152600081816101ef015281816103b10152818161064b015281816106ad015281816106df01528181610745015281816107d7015281816108330152818161096b01526109d001526000505060005050600050506000505060005050600050506000505060005050600050506000505060005050600050506000505060005050600050506110ce6000f3fe6080604052600436106101d85760003560e01c80639cd241af11610102578063d899e11211610095578063e4af29d111610064578063e4af29d1146102e8578063eac3e799146105c9578063f3f70707146105fd578063f698da2514610631576101d8565b8063d899e11214610575578063dbbe807014610562578063ded06231146103eb578063e44808bc146105a9576101d8565b8063a6e8a859116100d1578063a6e8a8591461052e578063ab033ea9146102e8578063cba2e58d14610562578063cbc1343414610325576101d8565b80639cd241af1461050e578063a22cb465146104bb578063a42dce80146102e8578063a5107626146102e8576101d8565b806330adf81f1161017a5780634ed2d6ac116101495780634ed2d6ac146104a05780637180c8ca146104bb57806377d05ff4146104db5780639032c726146104ee576101d8565b806330adf81f146104195780633e691db91461044d578063414f826d1461046d5780634c2ac1d91461048d576101d8565b806317fad7fc116101b657806317fad7fc1461035f5780631c0f12b61461037f57806321b57d531461039f57806329b23fc1146103eb576101d8565b806301681a62146102e857806302329a291461030a578063074a6de914610325575b3480156101e457600080fd5b5060003660606000807f00000000000000000000000000000000000000000000000000000000000000006001600160a01b03168585604051610227929190610aa6565b600060405180830381855af49150503d8060008114610262576040519150601f19603f3d011682016040523d82523d6000602084013e610267565b606091505b5091509150811561028b57604051638bb0a34b60e01b815260040160405180910390fd5b600061029682610ab6565b90506001600160e01b03198116636e64089360e11b146102b857815160208301fd5b8151600319810160048401908152926102d991810160200190602401610b27565b80519650602001945050505050f35b3480156102f457600080fd5b50610308610303366004610bec565b610646565b005b34801561031657600080fd5b50610308610303366004610c25565b34801561033157600080fd5b50610345610340366004610c52565b610673565b604080519283526020830191909152015b60405180910390f35b34801561036b57600080fd5b5061030861037a366004610cee565b6106a8565b34801561038b57600080fd5b5061030861039a366004610d83565b6106da565b3480156103ab57600080fd5b506103d37f000000000000000000000000000000000000000000000000000000000000000081565b6040516001600160a01b039091168152602001610356565b3480156103f757600080fd5b5061040b610406366004610dcb565b61070a565b604051908152602001610356565b34801561042557600080fd5b5061040b7f65619c8664d6db8aae8c236ad19598696159942a4245b23b45565cc18e97367381565b34801561045957600080fd5b5061040b610468366004610e25565b61073e565b34801561047957600080fd5b50610308610488366004610e62565b61076f565b61040b61049b366004610e84565b61079d565b3480156104ac57600080fd5b5061030861039a366004610ee8565b3480156104c757600080fd5b506103086104d6366004610f32565b6107d2565b61040b6104e9366004610c52565b6107fb565b3480156104fa57600080fd5b50610308610509366004610f67565b61082e565b34801561051a57600080fd5b50610308610529366004610fe5565b610966565b34801561053a57600080fd5b506103d37f000000000000000000000000000000000000000000000000000000000000000081565b610345610570366004610dcb565b610995565b34801561058157600080fd5b506103d37f000000000000000000000000000000000000000000000000000000000000000081565b3480156105b557600080fd5b506103086105c436600461101d565b6109cb565b3480156105d557600080fd5b506103d37f000000000000000000000000000000000000000000000000000000000000000081565b34801561060957600080fd5b506103d37f000000000000000000000000000000000000000000000000000000000000000081565b34801561063d57600080fd5b5061040b6109fc565b61066f7f0000000000000000000000000000000000000000000000000000000000000000610a8a565b5050565b60008061069f7f0000000000000000000000000000000000000000000000000000000000000000610a8a565b50935093915050565b6106d17f0000000000000000000000000000000000000000000000000000000000000000610a8a565b50505050505050565b6107037f0000000000000000000000000000000000000000000000000000000000000000610a8a565b5050505050565b60006107357f0000000000000000000000000000000000000000000000000000000000000000610a8a565b50949350505050565b60006107697f0000000000000000000000000000000000000000000000000000000000000000610a8a565b50919050565b6107987f0000000000000000000000000000000000000000000000000000000000000000610a8a565b505050565b60006107c87f0000000000000000000000000000000000000000000000000000000000000000610a8a565b5095945050505050565b6107987f0000000000000000000000000000000000000000000000000000000000000000610a8a565b60006108267f0000000000000000000000000000000000000000000000000000000000000000610a8a565b509392505050565b6000807f00000000000000000000000000000000000000000000000000000000000000006001600160a01b03166108636109fc565b60405160248101919091527f65619c8664d6db8aae8c236ad19598696159942a4245b23b45565cc18e97367360448201526001600160a01b03808c1660648301528a16608482015288151560a482015260c4810188905260ff871660e4820152610104810186905261012481018590526101440160408051601f198184030181529181526020820180516001600160e01b03166314e5f07b60e01b1790525161090c919061107c565b600060405180830381855af49150503d8060008114610947576040519150601f19603f3d011682016040523d82523d6000602084013e61094c565b606091505b50915091508161095e57805160208201fd5b805160208201f35b61098f7f0000000000000000000000000000000000000000000000000000000000000000610a8a565b50505050565b6000806109c17f0000000000000000000000000000000000000000000000000000000000000000610a8a565b5094509492505050565b6109f47f0000000000000000000000000000000000000000000000000000000000000000610a8a565b505050505050565b60408051808201825260018152603160f81b60209182015281517f2aef22f9d7df5f9d21c56d14029233f3fdaa91917727e1eb68e504d27072d6cd818301527fc89efdaa54c0f20c7adf612882df0950f5a951637e0307cdcb4c672f298b8bc681840152466060820152306080808301919091528351808303909101815260a0909101909252815191012090565b6060600080836001600160a01b031660003660405161090c9291905b8183823760009101908152919050565b805160208201516001600160e01b03198082169291906004831015610ae55780818460040360031b1b83161693505b505050919050565b634e487b7160e01b600052604160045260246000fd5b60005b83811015610b1e578181015183820152602001610b06565b50506000910152565b600060208284031215610b3957600080fd5b815167ffffffffffffffff80821115610b5157600080fd5b818401915084601f830112610b6557600080fd5b815181811115610b7757610b77610aed565b604051601f8201601f19908116603f01168101908382118183101715610b9f57610b9f610aed565b81604052828152876020848701011115610bb857600080fd5b610bc9836020830160208801610b03565b979650505050505050565b6001600160a01b0381168114610be957600080fd5b50565b600060208284031215610bfe57600080fd5b8135610c0981610bd4565b9392505050565b80358015158114610c2057600080fd5b919050565b600060208284031215610c3757600080fd5b610c0982610c10565b60006060828403121561076957600080fd5b600080600060608486031215610c6757600080fd5b8335925060208401359150604084013567ffffffffffffffff811115610c8c57600080fd5b610c9886828701610c40565b9150509250925092565b60008083601f840112610cb457600080fd5b50813567ffffffffffffffff811115610ccc57600080fd5b6020830191508360208260051b8501011115610ce757600080fd5b9250929050565b60008060008060008060808789031215610d0757600080fd5b8635610d1281610bd4565b95506020870135610d2281610bd4565b9450604087013567ffffffffffffffff80821115610d3f57600080fd5b610d4b8a838b01610ca2565b90965094506060890135915080821115610d6457600080fd5b50610d7189828a01610ca2565b979a9699509497509295939492505050565b60008060008060808587031215610d9957600080fd5b843593506020850135610dab81610bd4565b92506040850135610dbb81610bd4565b9396929550929360600135925050565b60008060008060808587031215610de157600080fd5b843593506020850135925060408501359150606085013567ffffffffffffffff811115610e0d57600080fd5b610e1987828801610c40565b91505092959194509250565b600060208284031215610e3757600080fd5b813567ffffffffffffffff811115610e4e57600080fd5b610e5a84828501610c40565b949350505050565b60008060408385031215610e7557600080fd5b50508035926020909101359150565b600080600080600060a08688031215610e9c57600080fd5b85359450602086013593506040860135925060608601359150608086013567ffffffffffffffff811115610ecf57600080fd5b610edb88828901610c40565b9150509295509295909350565b60008060008060808587031215610efe57600080fd5b843593506020850135610f1081610bd4565b9250604085013591506060850135610f2781610bd4565b939692955090935050565b60008060408385031215610f4557600080fd5b8235610f5081610bd4565b9150610f5e60208401610c10565b90509250929050565b600080600080600080600060e0888a031215610f8257600080fd5b8735610f8d81610bd4565b96506020880135610f9d81610bd4565b9550610fab60408901610c10565b945060608801359350608088013560ff81168114610fc857600080fd5b9699959850939692959460a0840135945060c09093013592915050565b600080600060608486031215610ffa57600080fd5b83359250602084013561100c81610bd4565b929592945050506040919091013590565b600080600080600060a0868803121561103557600080fd5b85359450602086013561104781610bd4565b9350604086013561105781610bd4565b925060608601359150608086013561106e81610bd4565b809150509295509295909350565b6000825161108e818460208701610b03565b919091019291505056fea264697066735822122070bafb43a27860f48c1656f0f49c85644411cb6efdbf25e614a6f83752e5a16164736f6c63430008140033a2646970667358221220c42c6056572190be55d5f9db33de95fb69f6ca2e791c34bf3bebb91ca3ffd0bf64736f6c63430008140033"
)


class StETHHyperdriveCoreDeployerContract(Contract):
    """A web3.py Contract class for the StETHHyperdriveCoreDeployer contract."""

    abi: ABI = stethhyperdrivecoredeployer_abi
    bytecode: bytes | None = try_bytecode_hexbytes(stethhyperdrivecoredeployer_bytecode, "stethhyperdrivecoredeployer")

    def __init__(self, address: ChecksumAddress | None = None) -> None:
        try:
            # Initialize parent Contract class
            super().__init__(address=address)
            self.functions = StETHHyperdriveCoreDeployerContractFunctions(stethhyperdrivecoredeployer_abi, self.w3, address)  # type: ignore

        except FallbackNotFound:
            print("Fallback function not found. Continuing...")

    functions: StETHHyperdriveCoreDeployerContractFunctions

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
        current_nonce = w3.eth.get_transaction_count(account.address, "pending")
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
        contract.functions = StETHHyperdriveCoreDeployerContractFunctions(stethhyperdrivecoredeployer_abi, w3, None)

        return contract
