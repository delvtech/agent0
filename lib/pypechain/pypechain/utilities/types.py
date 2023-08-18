def solidity_to_python_type(solidity_type: str) -> str:
    """Returns the stringfied python type for the gien solidity type."""
    # Basic types
    if solidity_type in [
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "uint128",
        "uint256",
        "int8",
        "int16",
        "int32",
        "int64",
        "int128",
        "int256",
    ]:
        return "int"
    elif solidity_type == "address":
        return "str"
    elif solidity_type == "bool":
        return "bool"
    elif solidity_type == "bytes":
        return "bytes"
        # TODO this should actually be a BytesLike string or something.
    elif solidity_type.startswith("bytes"):  # for bytes1, bytes2,...,bytes32
        return "bytes"
    elif solidity_type == "string":
        return "str"
    # Fixed-size arrays of uints and ints
    elif any(solidity_type.startswith(x) for x in ["uint", "int"]) and solidity_type.endswith("]"):
        # TODO: use a package like 'array' or 'numpy' to provide fixed arrays.
        # Extract the size of the array, e.g., "uint8[3]" -> 3
        # size = int(solidity_type.split("[")[-1].split("]")[0])
        # Return a list of 'int' of the given size
        return "list[int]"
    else:
        # If the Solidity type isn't recognized, raise an exception or return some default value
        raise ValueError(f"Unknown Solidity type: {solidity_type}")
