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


async def send_get(session, url, headers=None):
    """Send a GET request asynchronously."""
    try:
        async with session.get(url, headers=headers) as response:
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
    except Exception as e:
        print(f"Error during PUT request to {url}: {e}")


async def xor(
    parties,
    session,
    admin_access_tokens,
    take_value_from_temporary_zZ,
    zZ_first_multiplication_factor,
    zZ_second_multiplication_factor,
):
    # Calculate and share q for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/redistribute-q",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("q calculated and shared for all parties")

    # Calculate and share r for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/redistribute-r",
                json_data={
                    "take_value_from_temporary_zZ": take_value_from_temporary_zZ,
                    "zZ_first_multiplication_factor": zZ_first_multiplication_factor,
                    "zZ_second_multiplication_factor": zZ_second_multiplication_factor,
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("r calculated and shared for all parties")

    # Calculate the multiplicative share for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-multiplicative-share",
                json_data={
                    "calculate_for_xor": True,
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Multiplicative shares calculated for all parties")

    # xor for all parties
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/xor",
                json_data={
                    "take_value_from_temporary_zZ": take_value_from_temporary_zZ,
                    "zZ_first_multiplication_factor": zZ_first_multiplication_factor,
                    "zZ_second_multiplication_factor": zZ_second_multiplication_factor,
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("xor calculated for all parties")

    # Reset the calculation for parties
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
    print("Reset for all parties")


async def romb(parties, session, admin_access_tokens):
    """
    Helper fuction for comparison
    (x, X) ◇ (y, Y) = (x^y , x^(X⊕Y)⊕X)
    x - zZ[0][0]  X - zZ[0][1]
    y - zZ[0][0]  Y - zZ[0][1]
    """
    # Reset the calculation for parties
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
    print("Reset for all parties")

    # First AND: x ^ y
    # Calculate and share q for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/redistribute-q",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("q calculated and shared for all parties")

    # Calculate and share r for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/redistribute-r",
                json_data={
                    "take_value_from_temporary_zZ": False,
                    "zZ_first_multiplication_factor": [0, 0],
                    "zZ_second_multiplication_factor": [1, 0],
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("r calculated and shared for all parties")

    # Calculate the multiplicative share for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-multiplicative-share",
                json_data={"set_in_temporary_zZ_index": 0, "calculate_for_xor": False},
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Multiplicative shares calculated for all parties")

    # Reset the calculation for parties
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
    print("Reset for all parties")

    # Second XOR: (X XOR Y)
    # xor the shares

    await xor(parties, session, admin_access_tokens, False, [0, 1], [1, 1])

    # SECOND AND: x ^ (X XOR Y)
    # Calculate and share q for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/redistribute-q",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("q calculated and shared for all parties")

    # Calculate and share r for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/redistribute-r",
                json_data={
                    "take_value_from_temporary_zZ": True,
                    "zZ_first_multiplication_factor": [0, 0],
                    "zZ_second_multiplication_factor": [1],
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("r calculated and shared for all parties")

    # Calculate the multiplicative share for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-multiplicative-share",
                json_data={"set_in_temporary_zZ_index": 1, "calculate_for_xor": False},
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Multiplicative shares calculated for all parties")

    # Reset the calculation for parties
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
    print("Reset for all parties")

    # SECOND XOR: x ^ (X XOR Y) XOR X
    # Calculate and share q for each party
    await xor(parties, session, admin_access_tokens, True, [0, 1], [1])


# Calculate the final comparison result
async def calculate_final_comparison_result(
    parties,
    session,
    admin_access_tokens,
    opened_a,
    l,
    k,
):
    # Reset the calculation for parties
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
    print("Reset for all parties")

    # Calculate and share q for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/redistribute-q",
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("q calculated and shared for all parties")

    # Calculate and share r for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/redistribute-r",
                json_data={
                    "calculate_final_comparison_result": True,
                    "opened_a": opened_a,
                    "l": l,
                    "k": k,
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("r calculated and shared for all parties")

    # Calculate the multiplicative share for each party
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_put(
                session,
                f"{party}/api/calculate-multiplicative-share",
                json_data={
                    "calculate_for_xor": True,
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Multiplicative shares calculated for all parties")

    # xor for all parties
    tasks = []
    for i, party in enumerate(parties):
        tasks.append(
            send_post(
                session,
                f"{party}/api/calculate-comparison-result",
                json_data={
                    "opened_a": opened_a,
                    "l": l,
                    "k": k,
                },
                headers={
                    "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                },
            )
        )
    await asyncio.gather(*tasks)
    print("Comparison result calculated for all parties")


async def main():
    async with aiohttp.ClientSession() as session:
        # Login to user account
        user_access_tokens_1 = await send_post(
            session,
            "http://localhost:5001/api/auth/login",
            json_data={
                "email": "userAutomateTesting",
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
                "email": "userAutomateTesting_2",
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
                "email": "adminAutomateTesting",
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
    p = "0x1EEF"
    t = (len(parties) - 1) // 2
    n = len(parties)
    l = 12
    k = 1
    first_bid = 5
    second_bid = 3
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
                        f"{party}/api/set-shares",
                        json_data={"share": hex(shares[i][1])},
                        headers={
                            "Authorization": f"Bearer {access_token['access_tokens'][i]['access_token']}"
                        },
                    )
                )
        await asyncio.gather(*tasks)
        print("Shares set for all parties")

        # Get bidders ids
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

        while True:
            # Calculate the 'A' for the comparison
            tasks = []
            for i, party in enumerate(parties):
                tasks.append(
                    send_post(
                        session,
                        f"{party}/api/calculate-a-comparison",
                        json_data={
                            "first_client_id": 23,
                            "second_client_id": 25,
                        },
                        headers={
                            "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                        },
                    )
                )
            await asyncio.gather(*tasks)
            print("A calculated for all parties")

            # Reconstruct the secret
            tasks = []
            opened_a = 0
            for i, party in enumerate(parties):
                tasks.append(
                    send_get(
                        session,
                        f"{party}/api/reconstruct-secret",
                        headers={
                            "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                        },
                    )
                )
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
                        headers={
                            "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                        },
                    )
                )
            await asyncio.gather(*tasks)
            print("Z calculated for all parties")

            for _ in range(l):
                await romb(parties, session, admin_access_tokens)

                # Pop the first element from the list
                tasks = []
                for i, party in enumerate(parties):
                    tasks.append(
                        send_post(
                            session,
                            f"{party}/api/pop-zZ",
                            headers={
                                "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                            },
                        )
                    )
                await asyncio.gather(*tasks)
                print("Popped zZ for all parties")

            # Calculate the final comparison result
            await calculate_final_comparison_result(
                parties, session, admin_access_tokens, opened_a, l, k
            )

            # Reconstruct the secret
            tasks = []
            for i, party in enumerate(parties):
                tasks.append(
                    send_get(
                        session,
                        f"{party}/api/reconstruct-secret",
                        headers={
                            "Authorization": f"Bearer {admin_access_tokens['access_tokens'][i]['access_token']}"
                        },
                    )
                )
            results = await asyncio.gather(*tasks)
            for i, result in enumerate(results):
                secret = int(result.get("secret"), 16)
                print(f"Secret reconstructed for party {i + 1} with value {secret}")

                assert secret == 0

            # Reset comparison
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
