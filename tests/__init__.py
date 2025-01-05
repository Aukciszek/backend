import os

import requests


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


def main():
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

    # Set the initial values for each party
    for i in range(n):
        party = parties[i]

        requests.post(
            f"{party}/api/initial-values/",
            json={"t": t, "n": n, "id": i + 1, "p": p, "parties": parties},
        )

        print("Initial values set for party ", i + 1)

    # Set the shares for each party
    for i in range(n):
        party = parties[i]

        requests.post(
            f"{party}/api/set-shares/",
            json={"client_id": 1, "share": first_shares[i][1]},
        )
        requests.post(
            f"{party}/api/set-shares/",
            json={"client_id": 2, "share": second_shares[i][1]},
        )
        requests.post(
            f"{party}/api/set-shares/",
            json={"client_id": 3, "share": third_shares[i][1]},
        )

        print("Shares set for party ", i + 1)

    # Calulate r for each party
    for i in range(n):
        party = parties[i]

        requests.post(
            f"{party}/api/calculate-r/",
            json={"first_client_id": 1, "second_client_id": 2},
        )

        print("r calculated for party ", i + 1)

    # Send r to each party
    for i in range(n):
        party = parties[i]

        requests.get(f"{party}/api/send-r-to-parties/")

        print("r sent from party ", i + 1)

    # Calculate the multiplicative share for each party
    for i in range(n):
        party = parties[i]

        requests.put(f"{party}/api/calculate-multiplicative-share/")

        print("Multiplicative share calculated for party ", i + 1)

    # Resonstruct the secret
    for i in range(n):
        party = parties[i]

        response = requests.get(f"{party}/api/reconstruct-secret/")

        print(
            f"Secret reconstructed for party {i + 1} with value {response.json()['secret']}"
        )

        assert response.json()["secret"] == first_secret * second_secret % p

    # Get status
    for i in range(n):
        party = parties[i]

        response = requests.get(f"{party}/api/status/")

        print(f"Status for party {i + 1}: {response.json()['status']}")

    # Reset the parties
    for i in range(n):
        party = parties[i]

        requests.post(f"{party}/api/reset/")

        print("Reset for party ", i + 1)

    # Get status
    for i in range(n):
        party = parties[i]

        response = requests.get(f"{party}/api/status/")

        print(f"Status for party {i + 1}: {response.json()['status']}")

    #
    # New multiplication
    #

    # Calulate r for each party
    for i in range(n):
        party = parties[i]

        requests.post(
            f"{party}/api/calculate-r/",
            json={"first_client_id": 2, "second_client_id": 3},
        )

        print("r calculated for party ", i + 1)

    # Send r to each party
    for i in range(n):
        party = parties[i]

        requests.get(f"{party}/api/send-r-to-parties/")

        print("r sent from party ", i + 1)

    # Calculate the multiplicative share for each party
    for i in range(n):
        party = parties[i]

        requests.put(f"{party}/api/calculate-multiplicative-share/")

        print("Multiplicative share calculated for party ", i + 1)

    # Resonstruct the secret
    for i in range(n):
        party = parties[i]

        response = requests.get(f"{party}/api/reconstruct-secret/")

        print(
            f"Secret reconstructed for party {i + 1} with value {response.json()['secret']}"
        )

        assert response.json()["secret"] == second_secret * third_secret % p

    # Facotory reset
    for i in range(n):
        party = parties[i]

        requests.post(f"{party}/api/factory-reset/")

        print("Factory reset for party ", i + 1)


if __name__ == "__main__":
    main()
