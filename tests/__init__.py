import asyncio
import os

import aiohttp


def modular_multiplicative_inverse(b: int, n: int) -> int:
    A = n
    B = b
    U = 0
    V = 1
    while B != 0:
        q = A // B
        A, B = B, A - q * B
        U, V = V, U - q * V
    if U < 0:
        return U + n
    return U


def smallest_square_root_modulo(number, modulus):
    wyn = 0
    for i in range(modulus):
        if (i * i) % modulus == number:
            wyn = i
            break
    return wyn


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


async def send_post(session, url, json_data=None, headers=None):
    """Send a POST request asynchronously."""
    try:
        async with session.post(url, json=json_data, headers=headers) as response:
            message = await response.json()

            if response.status != 200 and response.status != 201:
                print(f"Failed POST request to {url}: {message}")

            return await response.json()
    except Exception as e:
        print(f"Error during POST request to {url}: {e}")


async def send_get(session, url, headers=None, json_data=None):
    """Send a GET request asynchronously."""
    try:
        async with session.get(url, headers=headers, json=json_data) as response:
            message = await response.json()

            if response.status != 200 and response.status != 201:
                print(f"Failed GET request to {url}: {message}")

            return await response.json()
    except Exception as e:
        print(f"Error during GET request to {url}: {e}")
        return {}


async def send_put(session, url, json_data=None, headers=None):
    """Send a PUT request asynchronously."""
    try:
        async with session.put(url, json=json_data, headers=headers) as response:
            message = await response.json()

            if response.status != 201:
                print(f"Failed PUT request to {url}: {message}")

            return await response.json()
    except Exception as e:
        print(f"Error during PUT request to {url}: {e}")


async def add_shares(
    session,
    admin_access_tokens,
    parties,
    first_share_name: str,
    second_share_name: str,
    result_share_name: str,
):
    # Additive share calculation
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-additive-share",
                json_data={
                    "first_share_name": first_share_name,
                    "second_share_name": second_share_name,
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Additive shares calculated for all parties")

    # Set the result share to the additive share
    tasks = []
    for i, party in enumerate(parties):
        # Set the result share to the additive share
        tasks.append(
            send_put(
                session,
                f"{party}/api/set-additive-share/{result_share_name}",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print(f"Result share {result_share_name} set to additive share for all parties")


async def multiply_shares(
    session,
    admin_access_tokens,
    parties,
    first_share_name: str,
    second_share_name: str,
    result_share_name: str,
):
    # Calculate and redistribute q values
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/redistribute-q",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("q values redistributed for all parties")

    # Calculate and redistribute r values
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/redistribute-r",
                json_data={
                    "first_share_name": first_share_name,
                    "second_share_name": second_share_name,
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("r values redistributed for all parties")

    # Calculate the multiplicative share
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-multiplicative-share",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Multiplicative shares calculated for all parties")

    # Set the result share to the multiplicative share
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/set-multiplicative-share/{result_share_name}",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print(
        f"Result share {result_share_name} set to multiplicative share for all parties"
    )


# x XOR y = (x+y) - 2*(x*y)
async def xor_shares(
    session,
    admin_access_tokens,
    parties,
    first_share_name: str,
    second_share_name: str,
    result_share_name: str,
):
    # Additive share calculation
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-additive-share",
                json_data={
                    "first_share_name": first_share_name,
                    "second_share_name": second_share_name,
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Additive shares calculated for all parties")

    # Calculate and redistribute q values
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/redistribute-q",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("q values redistributed for all parties")

    # Calculate and redistribute r values
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/redistribute-r",
                json_data={
                    "first_share_name": first_share_name,
                    "second_share_name": second_share_name,
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("r values redistributed for all parties")

    # Calculate the multiplicative share
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-multiplicative-share",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Multiplicative shares calculated for all parties")

    # Set the result share to the additive share
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-xor-share",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("XOR shares calculated for all parties")

    # Set the result share to the XOR share
    tasks = []
    for i, party in enumerate(parties):
        # Set the result share to the XOR share
        tasks.append(
            send_put(
                session,
                f"{party}/api/set-xor-share/{result_share_name}",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print(f"Result share {result_share_name} set to XOR share for all parties")


async def share_random_u(session, admin_access_tokens, parties):
    # Share random u values
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/redistribute-u",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("u values redistributed for all parties")

    # Calculate the shared u values
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-shared-u",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Shared u values calculated for all parties")


async def share_random_bit(session, admin_access_tokens, parties, p, bit_index):
    opened_v = 0
    while opened_v <= 0:
        await share_random_u(session, admin_access_tokens, parties)

        await multiply_shares(
            session,
            admin_access_tokens,
            parties,
            "u",
            "u",
            "v",
        )

        # Reset calculation for all parties
        tasks = []
        for i, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/reset-calculation",
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                    },
                )
            )
        await asyncio.gather(*tasks)
        print("Calculation reset for all parties")

        tasks = []
        for i, party in enumerate(parties):
            tasks.append(
                send_get(
                    session,
                    f"{party}/api/reconstruct-secret",
                    json_data={"share_to_reconstruct": "v"},
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                    },
                )
            )
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            opened_v = int(result.get("secret"), 16)
            print(f"v reconstructed for party {i + 1} with value {opened_v}")

    w = smallest_square_root_modulo(opened_v, int(p, 16))

    inverse_w = modular_multiplicative_inverse(w, int(p, 16))

    # Set the inverse w shares for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/set-shares",
                json_data={
                    "share_name": "dummy_sharing_of_inverse_w_",
                    "share_value": hex(inverse_w),
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Inverse w shares set for all parties")

    await multiply_shares(
        session,
        admin_access_tokens,
        parties,
        "dummy_sharing_of_inverse_w_",
        "u",
        "inverse_w_times_u",
    )

    # Reset calculation for all parties
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/reset-calculation",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Calculation reset for all parties")

    # Dummy sharing of one for all parties
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/set-shares",
                json_data={
                    "share_name": "dummy_sharing_of_one",
                    "share_value": hex(1),
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Dummy sharing of one set for all parties")

    await add_shares(
        session,
        admin_access_tokens,
        parties,
        "inverse_w_times_u",
        "dummy_sharing_of_one",
        "inverse_w_times_u_plus_one",
    )

    inverse_two = modular_multiplicative_inverse(2, int(p, 16))

    # Dummy sharing of inverse two for all parties
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/set-shares",
                json_data={
                    "share_name": "dummy_sharing_of_inverse_two",
                    "share_value": hex(inverse_two),
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Dummy sharing of inverse two set for all parties")

    await multiply_shares(
        session,
        admin_access_tokens,
        parties,
        "inverse_w_times_u_plus_one",
        "dummy_sharing_of_inverse_two",
        "temporary_random_bit",
    )

    # Reset calculation for all parties
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/reset-calculation",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Calculation reset for all parties")

    # Set the temporary random bit share to the temporary random bit share
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/set-temporary-random-bit-share/{bit_index}",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print(f"Temporary random bit share for bit {bit_index} set for all parties")


async def calculate_z_table_XOR(session, admin_access_tokens, parties, index):
    # Calculate additive shares of z table for all parties
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-additive-share-of-z-table/{index}",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print(f"Additive shares of z table for index {index} calculated for all parties")

    # Calculate and redistribute q value
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/redistribute-q",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print(f"q values redistributed for all parties for index {index}")

    # Calculate and redistribute r values
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-r-of-z-table/{index}",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print(f"r values of z table for index {index} calculated for all parties")

    # Calculate the multiplicative share
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-multiplicative-share",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print(
        f"Multiplicative shares of z table for index {index} calculated for all parties"
    )

    # Calculate the XOR share
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-xor-share",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print(f"XOR shares of z table for index {index} calculated for all parties")

    # Set the z table to XOR share
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/set-z-table-to-xor-share/{index}",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print(f"Z table for index {index} set to XOR share for all parties")


async def calculate_z_tables(session, admin_access_tokens, parties, l):
    for i in range(l - 1, -1, -1):
        await calculate_z_table_XOR(session, admin_access_tokens, parties, i)

        # Reset calculation for all parties
        tasks = []
        for j, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/reset-calculation",
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][j]['access_token']}"
                    },
                )
            )
        await asyncio.gather(*tasks)
        print(f"Calculation reset for all parties after z table {i} calculation")


async def comparison(session, admin_access_tokens, parties, opened_a, l, k):
    # Prepare z tables for all parties
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/prepare-z-tables",
                json_data={
                    "opened_a": hex(opened_a),
                    "l": l,
                    "k": k,
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Z tables prepared for all parties")

    for i in range(l):
        await calculate_z_tables(session, admin_access_tokens, parties, l)

    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/initialize-z-and-Z",
                json_data={"l": l},
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("z and Z initialized for all parties")

    for i in range(l - 1, -1, -1):
        # Prepare for next round of comparison
        tasks = []
        for j, party in enumerate(parties):
            tasks.append(
                send_put(
                    session,
                    f"{party}/api/prepare-for-next-romb/{i}",
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][j]['access_token']}"
                    },
                )
            )
        await asyncio.gather(*tasks)
        print(f"Prepared for next round of comparison for z table {i}")

        # x AND y
        await multiply_shares(
            session,
            admin_access_tokens,
            parties,
            "x",
            "y",
            "z",
        )

        # Reset calculation for all parties
        tasks = []
        for j, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/reset-calculation",
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][j]['access_token']}"
                    },
                )
            )
        await asyncio.gather(*tasks)
        print(f"Calculation reset for all parties after multiplication for z table {i}")

        # X XOR Y
        await xor_shares(session, admin_access_tokens, parties, "X", "Y", "Z")

        # Reset calculation for all parties
        tasks = []
        for j, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/reset-calculation",
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][j]['access_token']}"
                    },
                )
            )
        await asyncio.gather(*tasks)
        print(f"Calculation reset for all parties after XOR for z table {i}")

        # Calculate x AND (X XOR Y)
        await multiply_shares(session, admin_access_tokens, parties, "x", "Z", "Z")

        # Reset calculation for all parties
        tasks = []
        for j, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/reset-calculation",
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][j]['access_token']}"
                    },
                )
            )
        await asyncio.gather(*tasks)
        print(f"Calculation reset for all parties after AND for z table {i}")

        # x AND (X XOR Y) XOR X
        await xor_shares(session, admin_access_tokens, parties, "Z", "X", "Z")

        # Reset calculation for all parties
        tasks = []
        for j, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/reset-calculation",
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][j]['access_token']}"
                    },
                )
            )
        await asyncio.gather(*tasks)
        print(f"Calculation reset for all parties after final XOR for z table {i}")

    # [res] = a_l XOR [r_l] XOR [Z]
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/prepare-shares-for-res-xors/{l}/{l}",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Shares prepared for final XOR for all parties")

    # a_l XOR [r_l] -> przypisz do [res]
    await xor_shares(session, admin_access_tokens, parties, "a_l", "r_l", "res")

    # Reset calculation for all parties
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/reset-calculation",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Calculation reset for all parties after final XOR")

    # [res] XOR [Z] -> przypisz do [res]
    await xor_shares(session, admin_access_tokens, parties, "res", "Z", "res")

    # Reset calculation for all parties
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/reset-calculation",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Calculation reset for all parties after final XOR with Z")


async def main():
    async with aiohttp.ClientSession() as session:
        # Login to user account
        user_access_tokens_1 = await send_post(
            session,
            "http://localhost:5001/api/auth/login",
            json_data={
                "email": "userAutomateTesting@company.com",
                "password": "userAutomateTesting",
            },
        )
        if not user_access_tokens_1:
            print("Failed to login")
            return

        print("User access tokens: ", user_access_tokens_1)

        # Login to user account
        user_access_tokens_2 = await send_post(
            session,
            "http://localhost:5001/api/auth/login",
            json_data={
                "email": "userAutomateTesting_2@company.com",
                "password": "userAutomateTesting_2",
            },
        )
        if not user_access_tokens_2:
            print("Failed to login")
            return

        print("User access tokens: ", user_access_tokens_2)

        # Login to admin account
        admin_access_tokens = await send_post(
            session,
            "http://localhost:5001/api/auth/login",
            json_data={
                "email": "adminAutomateTesting@company.com",
                "password": "adminAutomateTesting",
            },
        )
        if not admin_access_tokens:
            print("Failed to login")
            return

        print("Admin access tokens: ", admin_access_tokens)

    # Create parties and set shares (P_0, ..., P_n-1)
    parties = [item["server"] for item in admin_access_tokens["access_tokens"]]
    print("Parties: ", parties)

    # Shamir's secret sharing
    p = "0x35"
    t = (len(parties) - 1) // 2
    n = len(parties)
    l = 3
    k = 1
    first_bid = 21
    second_bid = 23
    first_bid_shares = Shamir(t, n, first_bid, int(p, 16))  # First client
    second_bid_shares = Shamir(t, n, second_bid, int(p, 16))  # Second client

    print("first_bid_shares = ", first_bid_shares)
    print("second_bid_shares = ", second_bid_shares)
    print("p = ", p)

    async with aiohttp.ClientSession() as session:
        # Factory reset
        tasks = []
        for i, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/factory-reset",
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                    },
                )
            )
        await asyncio.gather(*tasks)
        print("Factory reset for all parties")

        # Set the initial values for each party
        tasks = []
        for i, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/initial-values",
                    json_data={"id": i + 1, "p": p},
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                    },
                )
            )
        await asyncio.gather(*tasks)
        print("Initial values set for all parties")

        # Set the shares for each party
        tasks = []
        for i, party in enumerate(parties):
            for access_token, shares in zip(
                [user_access_tokens_1, user_access_tokens_2],
                [first_bid_shares, second_bid_shares],
            ):
                print(f"Setting share for party {i + 1} with share {shares[i][1]}")

                tasks.append(
                    send_post(
                        session,
                        f"{party}/api/set-client-shares",
                        json_data={"share": hex(shares[i][1])},
                        headers={
                            "Authorization": f"Bearer {access_token['access_tokens'][i]['access_token']}"
                        },
                    )
                )
        await asyncio.gather(*tasks)
        print("Shares set for all parties")

        # Get bidders ids
        bidders = []
        tasks = []
        for i, party in enumerate(parties):
            tasks.append(
                send_get(
                    session,
                    f"{party}/api/get-bidders",
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                    },
                )
            )
        result = await asyncio.gather(*tasks)
        for i, result in enumerate(result):
            bidders = result.get("bidders")
            print(f"Bidders for party {i + 1}: {bidders}")

        # Calculate the A
        tasks = []
        for i, party in enumerate(parties):
            tasks.append(
                send_put(
                    session,
                    f"{party}/api/calculate-A",
                    headers={
                        "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                    },
                )
            )
        await asyncio.gather(*tasks)
        print("A calculated for all parties")

        for _ in range(3):
            for i in range(l + k + 1):
                await share_random_bit(session, admin_access_tokens, parties, p, i)

            tasks = []
            for i, party in enumerate(parties):
                tasks.append(
                    send_put(
                        session,
                        f"{party}/api/calculate-share-of-random-number",
                        headers={
                            "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                        },
                    )
                )
            await asyncio.gather(*tasks)
            print("Share of random number calculated for all parties")

            # Calculate "a" for comparison
            tasks = []
            for i, party in enumerate(parties):
                tasks.append(
                    send_put(
                        session,
                        f"{party}/api/calculate-a-comparison",
                        json_data={
                            "first_client_id": bidders[0],
                            "second_client_id": bidders[1],
                            "l": l,
                            "k": k,
                        },
                        headers={
                            "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                        },
                    )
                )
            await asyncio.gather(*tasks)
            print("'a' for comparison calculated for all parties")

            # Reconstruct "a" for comparison
            opened_a = 0
            tasks = []
            for i, party in enumerate(parties):
                tasks.append(
                    send_get(
                        session,
                        f"{party}/api/reconstruct-secret",
                        json_data={"share_to_reconstruct": "comparison_a"},
                        headers={
                            "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                        },
                    )
                )
            results = await asyncio.gather(*tasks)
            for i, result in enumerate(results):
                opened_a = int(result.get("secret"), 16)
                print(
                    f"Comparison 'a' reconstructed for party {i + 1} with value {opened_a}"
                )

            await comparison(session, admin_access_tokens, parties, opened_a, l, k)

            # Reconstruct final result
            final_result = None
            tasks = []
            for i, party in enumerate(parties):
                tasks.append(
                    send_get(
                        session,
                        f"{party}/api/reconstruct-secret",
                        json_data={"share_to_reconstruct": "res"},
                        headers={
                            "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                        },
                    )
                )
            results = await asyncio.gather(*tasks)
            for i, result in enumerate(results):
                final_result = int(result.get("secret"), 16)
                print(
                    f"Final result reconstructed for party {i + 1} with value {final_result}"
                )

            if first_bid >= second_bid:
                assert final_result == 1
            else:
                assert final_result == 0

            # Reset comparison for all parties
            tasks = []
            for i, party in enumerate(parties):
                tasks.append(
                    send_post(
                        session,
                        f"{party}/api/reset-comparison",
                        headers={
                            "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                        },
                    )
                )
            await asyncio.gather(*tasks)
            print("Comparison reset for all parties")


if __name__ == "__main__":
    asyncio.run(main())
