from math import ceil

def checksum(data: str, num_blocks: int) -> tuple[str, str]:
    length = len(data)
    if num_blocks < 1:
        raise ValueError("num_blocks must be at least 1")
    if num_blocks > length:
        # Option A: treat each bit as a block
        block_size = 1
        num_blocks = length
    else:
        block_size = ceil(length / num_blocks)

    blocks = []
    for i in range(0, length, block_size):
        block = data[i:i + block_size]
        # pad with zeros to full block_size
        if len(block) < block_size:
            block += '0' * (block_size - len(block))
        print("block:", block)
        blocks.append(block)

    total = 0
    for block in blocks:
        total += int(block, 2)

    # binary representation of the sum (no ‘0b’ prefix)
    sum_bits = bin(total)[2:]
    print("sum:", sum_bits)

    # one's-complement checksum, masked to block_size bits
    mask = (1 << block_size) - 1
    chk = (~total & mask)
    checksum_bits = bin(chk)[2:].zfill(block_size)

    # concatenate data blocks and checksum for transmission
    tx_data = ''.join(blocks) + checksum_bits
    return tx_data, checksum_bits


if __name__ == "__main__":
    data = input("Enter binary data: ").strip()
    num_blocks = int(input("Enter number of blocks: "))
    tx_data, chk = checksum(data, num_blocks)
    print('-' * 28)
    print("checksum:", chk)
    print("Transmitted Data (Data + Checksum):", tx_data)
