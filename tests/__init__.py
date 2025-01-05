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


def Shamir(t, n, k0):
    p = 23

    coefficients = [secure_randint(0, p - 1) for _ in range(t)]
    coefficients[0] = k0

    if coefficients[-1] == 0:
        coefficients[-1] = secure_randint(1, p - 1)

    shares = []

    for i in range(1, n + 1):
        shares.append((i, f(i, coefficients, p, t)))

    return shares, p


async def send_post(session, url, json_data=None):
    """Send a POST request asynchronously."""
    try:
        async with session.post(url, json=json_data) as response:
            if response.status != 201:
                print(f"Failed POST request to {url}: {response.status}")
    except Exception as e:
        print(f"Error during POST request to {url}: {e}")


async def send_get(session, url):
    """Send a GET request asynchronously."""
    try:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Failed GET request to {url}: {response.status}")
            return await response.json()
    except Exception as e:
        print(f"Error during GET request to {url}: {e}")
        return {}


async def send_put(session, url, json_data=None):
    """Send a PUT request asynchronously."""
    try:
        async with session.put(url, json=json_data) as response:
            if response.status != 201:
                print(f"Failed PUT request to {url}: {response.status}")
    except Exception as e:
        print(f"Error during PUT request to {url}: {e}")


async def main():
    # Shamir's secret sharing
    t = 2
    n = 5
    first_secret = 7
    second_secret = 2
    third_secret = 8
    first_shares, p = Shamir(t, n, first_secret)  # First client
    second_shares, _ = Shamir(t, n, second_secret)  # Second client
    third_shares, _ = Shamir(t, n, third_secret)  # Third client

    print("shares_1 = ", first_shares)
    print("shares_2 = ", second_shares)
    print("shares_3 = ", third_shares)
    print("p = ", p)

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
            tasks.append(send_post(session, f"{party}/api/factory-reset/"))
        await asyncio.gather(*tasks)
        print("Factory reset for all parties")

        # Set the initial values for each party
        tasks = []
        for i, party in enumerate(parties):
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/initial-values/",
                    json_data={"t": t, "n": n, "id": i + 1, "p": p, "parties": parties},
                )
            )
        await asyncio.gather(*tasks)
        print("Initial values set for all parties")

        # Set the shares for each party
        tasks = []
        for i, party in enumerate(parties):
            for client_id, shares in zip(
                [1, 2, 3], [first_shares, second_shares, third_shares]
            ):
                tasks.append(
                    send_post(
                        session,
                        f"{party}/api/set-shares/",
                        json_data={"client_id": client_id, "share": shares[i][1]},
                    )
                )
        await asyncio.gather(*tasks)
        print("Shares set for all parties")

        # Calculate r for each party
        tasks = []
        for party in parties:
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/calculate-r/",
                    json_data={"first_client_id": 1, "second_client_id": 2},
                )
            )
        await asyncio.gather(*tasks)
        print("r calculated for all parties")

        # Send r to each party
        tasks = []
        for party in parties:
            tasks.append(send_get(session, f"{party}/api/send-r-to-parties/"))
        await asyncio.gather(*tasks)
        print("r sent to all parties")

        # Calculate the multiplicative share for each party
        tasks = []
        for party in parties:
            tasks.append(
                send_put(session, f"{party}/api/calculate-multiplicative-share/")
            )
        await asyncio.gather(*tasks)
        print("Multiplicative shares calculated for all parties")

        # Reconstruct the secret
        tasks = []
        secrets = []
        for party in parties:
            tasks.append(send_get(session, f"{party}/api/reconstruct-secret/"))
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            secret = result.get("secret")
            print(f"Secret reconstructed for party {i + 1} with value {secret}")
            secrets.append(secret)
            assert secret == first_secret * second_secret % p

        # Get status
        tasks = []
        for party in parties:
            tasks.append(send_get(session, f"{party}/api/status/"))
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            print(f"Status for party {i + 1}: {result.get('status')}")

        # Reset the parties
        tasks = []
        for party in parties:
            tasks.append(send_post(session, f"{party}/api/reset/"))
        await asyncio.gather(*tasks)
        print("Reset for all parties")

        # Get status
        tasks = []
        for party in parties:
            tasks.append(send_get(session, f"{party}/api/status/"))
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            print(f"Status for party {i + 1}: {result.get('status')}")

        #
        # New multiplication
        #

        # Calculate r for each party
        tasks = []
        for party in parties:
            tasks.append(
                send_post(
                    session,
                    f"{party}/api/calculate-r/",
                    json_data={"first_client_id": 2, "second_client_id": 3},
                )
            )
        await asyncio.gather(*tasks)
        print("r calculated for all parties")

        # Send r to each party
        tasks = []
        for party in parties:
            tasks.append(send_get(session, f"{party}/api/send-r-to-parties/"))
        await asyncio.gather(*tasks)
        print("r sent to all parties")

        # Calculate the multiplicative share for each party
        tasks = []
        for party in parties:
            tasks.append(
                send_put(session, f"{party}/api/calculate-multiplicative-share/")
            )
        await asyncio.gather(*tasks)
        print("Multiplicative shares calculated for all parties")

        # Reconstruct the secret
        tasks = []
        secrets = []
        for party in parties:
            tasks.append(send_get(session, f"{party}/api/reconstruct-secret/"))
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            secret = result.get("secret")
            print(f"Secret reconstructed for party {i + 1} with value {secret}")
            secrets.append(secret)
            assert secret == second_secret * third_secret % p

        # Factory reset
        tasks = []
        for party in parties:
            tasks.append(send_post(session, f"{party}/api/factory-reset/"))
        await asyncio.gather(*tasks)
        print("Factory reset for all parties")

        # Get status
        tasks = []
        for party in parties:
            tasks.append(send_get(session, f"{party}/api/status/"))
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            print(f"Status for party {i + 1}: {result.get('status')}")


if __name__ == "__main__":
    asyncio.run(main())
