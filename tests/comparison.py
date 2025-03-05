import asyncio
import os

import aiohttp


def secure_randint(start, end):
    """Generate a secure random integer between start and end (inclusive) using os.urandom."""
    if start > end:
        raise ValueError("start must be less than or equal to end")

    range_size = end - start + 1
    num_bytes = (range_size - 1).bit_length() // 8 + 1
    mask = (1 << (num_bytes * 8)) - 1

    while True:
        random_int = int.from_bytes(os.urandom(num_bytes), "big") & mask
        if random_int < range_size:
            return start + random_int


def f(x, coefficients, p, t):
    return sum([coefficients[i] * x**i for i in range(t)]) % p


def Shamir(t, n, k0, p):
    coefficients = [secure_randint(0, p - 1) for _ in range(t)]
    coefficients[0] = k0

    if coefficients[-1] == 0:
        coefficients[-1] = secure_randint(1, p - 1)

    shares = []

    for i in range(1, n + 1):
        shares.append((i, f(i, coefficients, p, t)))

    return shares


async def send_post(session, url, json_data=None):
    """Send a POST request asynchronously."""
    try:
        async with session.post(url, json=json_data) as response:
            message = await response.json()

            if response.status != 201:
                print(f"Failed POST request to {url}: {message}")
    except Exception as e:
        print(f"Error during POST request to {url}: {e}")


async def send_get(session, url):
    """Send a GET request asynchronously."""
    try:
        async with session.get(url) as response:
            message = await response.json()

            if response.status != 200:
                print(f"Failed POST request to {url}: {message}")
            return await response.json()
    except Exception as e:
        print(f"Error during GET request to {url}: {e}")
        return {}


async def send_put(session, url, json_data=None):
    """Send a PUT request asynchronously."""
    try:
        async with session.put(url, json=json_data) as response:
            message = await response.json()

            if response.status != 201:
                print(f"Failed POST request to {url}: {message}")
    except Exception as e:
        print(f"Error during PUT request to {url}: {e}")


async def main():
    # Shamir's secret sharing
    p = "0xD"
    t = 2
    n = 5
    l = 3
    k = 1
    first_bid = 3
    second_bid = 7
    first_bid_shares = Shamir(t, n, first_bid, int(p, 16))  # First client
    second_bid_shares = Shamir(t, n, second_bid, int(p, 16))  # Second client

    print("first_bid_shares = ", first_bid_shares)
    print("second_bid_shares = ", second_bid_shares)
    print("p = ", p)

    bits_of_r = []
    shares_of_bits_of_r = []
    for i in range(l + k + 2):
        new_r_bit = int.from_bytes(os.urandom(1)) % 2
        bits_of_r.append(new_r_bit)
        shares_new_r_bit = Shamir(t, n, new_r_bit, int(p, 16))
        shares_of_bits_of_r.append(shares_new_r_bit)

    print("bits of r: ", bits_of_r)
    print(
        "l-th bit of r: ",
        bits_of_r[l],
        "shares of l-th bit of r: ",
        shares_of_bits_of_r[l],
    )

    # Create parties and set shares (P_0, ..., P_n-1)
    parties = [
        "http://localhost:5000",
        "http://localhost:5001",
        "http://localhost:5002",
        "http://localhost:5003",
        "http://localhost:5004",
    ]

    async with aiohttp.ClientSession() as session:
        # Factory reset
        tasks = []
        for party in parties:
            tasks.append(send_post(session, f"{party}/api/factory-reset"))
        await asyncio.gather(*tasks)
        print("Factory reset for all parties")

        # Set the initial values for each party
        tasks = []
        for i, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/initial-values",
                    json_data={"t": t, "n": n, "id": i + 1, "p": p, "parties": parties},
                )
            )
        await asyncio.gather(*tasks)
        print("Initial values set for all parties")

        # Set the shares for each party
        tasks = []
        for i, party in enumerate(parties):
            for client_id, shares in zip([1, 2], [first_bid_shares, second_bid_shares]):
                tasks.append(
                    send_post(
                        session,
                        f"{party}/api/set-shares",
                        json_data={"client_id": client_id, "share": str(shares[i][1])},
                    )
                )
        await asyncio.gather(*tasks)
        print("Shares set for all parties")

        shares_for_clients = [[] for _ in range(n)]

        for bit in shares_of_bits_of_r:
            for i, share_of_bit in enumerate(bit):
                shares_for_clients[i].append(share_of_bit[1])

        # Set the random number bit shares for each party
        tasks = []
        for i, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/set-random-number-bit-shares",
                    json_data={"shares": shares_for_clients[i]},
                )
            )
        await asyncio.gather(*tasks)
        print("Random number bit shares set for all parties")

        # Calculate the 'A' for the comparison
        tasks = []
        for i, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/calculate-a-comparison",
                    json_data={
                        "l": l,
                        "k": k,
                        "first_client_id": 1,
                        "second_client_id": 2,
                    },
                )
            )
        await asyncio.gather(*tasks)
        print("A calculated for all parties")

        # Reconstruct the secret
        tasks = []
        opened_a = 0
        for party in parties:
            tasks.append(send_get(session, f"{party}/api/reconstruct-secret"))
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            opened_a = result.get("secret")
            print(f"A reconstructed for party {i + 1} with value {opened_a}")

        # Calculate "z" for the comparison
        tasks = []
        for i, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/calculate-z-comparison",
                    json_data={"opened_a": opened_a, "l": l, "k": k},
                )
            )
        await asyncio.gather(*tasks)
        print("Z calculated for all parties")


if __name__ == "__main__":
    asyncio.run(main())
