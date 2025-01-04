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


def binary_exponentiation(b, k, n):
    if k < 0:
        k = n - 2

    a = 1
    while k:
        if k & 1:
            a = (a * b) % n
        b = (b * b) % n
        k >>= 1
    return a


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


def computate_coefficients(shares, p):
    coefficients = []

    for i, (x_i, _) in enumerate(shares):
        li = 1
        for j, (x_j, _) in enumerate(shares):
            if i != j:
                li *= x_j * binary_exponentiation(x_j - x_i, -1, p)
                li %= p
        coefficients.append(li)

    return coefficients


def reconstruct_secret(shares, coefficients, p):
    secret = 0

    for i, (_, y_i) in enumerate(shares):
        secret += y_i * coefficients[i]
        secret %= p

    return secret


def main():
    # Shamir's secret sharing
    t = 2
    n = 5
    first_secret = 3
    second_secret = 4
    first_shares, p = Shamir(t, n, first_secret)  # First client
    second_shares, _ = Shamir(t, n, second_secret)  # Second client

    print("shares_1 = ", first_shares)
    print("shares_2 = ", second_shares)
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
            f"{party}/api/set-initial-values/",
            json={"t": t, "n": n, "id": i + 1, "p": p},
        )

        print("Initial values set for party ", i + 1)

    # Set the parties for each party
    for i in range(n):
        party = parties[i]

        requests.post(f"{party}/api/set-parties/", json={"parties": parties})

        print("Parties set for party ", i + 1)

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

        print("Shares set for party ", i + 1)

    # Calulate A for each party
    for i in range(n):
        party = parties[i]

        requests.post(f"{party}/api/calculate-A/")

        print("A calculated for party ", i + 1)

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

        requests.get(f"{party}/api/send-r/")

        print("r sent from party ", i + 1)

    # Calculate the multiplicative share for each party
    for i in range(n):
        party = parties[i]

        requests.put(f"{party}/api/calculate-multiplicative-share/")

        print("Multiplicative share calculated for party ", i + 1)

    # Sum up the multiplicative shares
    multiplicative_shares = [(0, 0)] * n

    for i in range(n):
        party = parties[i]

        multiplicative_share = requests.get(
            f"{party}/api/calculate-multiplicative-share/"
        )

        multiplicative_shares[i] = (
            i + 1,
            multiplicative_share.json()["multiplicative_share"],
        )

    selected_shares = [multiplicative_shares[3], multiplicative_shares[1]]
    print("Selected Shares for Reconstruction: ", selected_shares)

    coefficients = computate_coefficients(selected_shares, p)

    print("coefficients = ", coefficients)

    secret = reconstruct_secret(selected_shares, coefficients, p)

    print("secret = ", secret % p)

    assert (first_secret * second_secret) % p == round(secret % p)

    # Reset the parties
    for i in range(n):
        party = parties[i]

        requests.post(f"{party}/api/reset/")

        print("Reset for party ", i + 1)


if __name__ == "__main__":
    main()
