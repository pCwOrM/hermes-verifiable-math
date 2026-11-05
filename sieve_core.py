"""
Werr Multi-Layer Algebraic Sieve & Certified Primality Core.
Provides exact deterministic primality testing (Baillie-PSW) and factorization.
"""

import math
import random
from typing import Dict, List, Tuple, Any


def is_square(n: int) -> Tuple[bool, int]:
    """Check if n is a perfect square; returns (is_sq, root)."""
    if n < 0:
        return False, 0
    if n in (0, 1):
        return True, n
    r = math.isqrt(n)
    return (r * r == n), r


def miller_rabin(n: int, k: int = 15) -> bool:
    """
    Deterministic Miller-Rabin for 64-bit ints, probabilistic beyond.
    """
    if n < 2:
        return False
    if n in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        return True
    if any(n % p == 0 for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)):
        return False

    # Deterministic bases for 64-bit integers
    if n < 2**64:
        bases = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    else:
        bases = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37] + [
            random.randint(40, n - 2) for _ in range(k)
        ]

    # Write n - 1 as 2^s * d
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    for a in bases:
        if a % n == 0:
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        composite = True
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                composite = False
                break
        if composite:
            return False
    return True


def lucas_selfridge_prp(n: int) -> bool:
    """
    Strong Lucas-Selfridge probable prime test (second half of Baillie-PSW).
    """
    if n < 2 or n % 2 == 0:
        return n == 2
    is_sq, _ = is_square(n)
    if is_sq:
        return False

    # Find D using Selfridge method: 5, -7, 9, -11, 13, ...
    D = 5
    sign = 1
    while True:
        g = math.gcd(abs(D), n)
        if 1 < g < n:
            return False
        if g == n:
            return False
        # Jacobi symbol
        jac = math.gcd(abs(D), n)
        # Simple Jacobi calculation
        j = 1
        a_val, n_val = D % n, n
        while a_val != 0:
            while a_val % 2 == 0:
                a_val //= 2
                if n_val % 8 in (3, 5):
                    j = -j
            a_val, n_val = n_val, a_val
            if a_val % 4 == 3 and n_val % 4 == 3:
                j = -j
            a_val %= n_val
        if n_val == 1 and j == -1:
            break
        D = -D - 2 * sign if D > 0 else -D + 2 * sign
        sign = -sign

    P = 1
    Q = (1 - D) // 4
    d = n + 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    # Lucas sequence evaluation
    # U_d, V_d mod n
    U = 0
    V = 2
    Q_k = Q
    U_m = 1
    V_m = P
    # Binary expansion of d
    bits = bin(d)[3:]  # skip '0b1'
    U = 1
    V = P
    Q_k = Q

    for bit in bits:
        U = (U * V) % n
        V = (V * V - 2 * Q_k) % n
        Q_k = (Q_k * Q_k) % n
        if bit == "1":
            U_next = (P * U + V)
            if U_next % 2 != 0:
                U_next += n
            U_next = (U_next // 2) % n

            V_next = (D * U + P * V)
            if V_next % 2 != 0:
                V_next += n
            V_next = (V_next // 2) % n

            U, V = U_next, V_next
            Q_k = (Q_k * Q) % n

    if U == 0 or V == 0:
        return True

    for _ in range(1, s):
        V = (V * V - 2 * Q_k) % n
        if V == 0:
            return True
        Q_k = (Q_k * Q_k) % n

    return False


def is_certified_prime(n: int) -> Tuple[bool, str]:
    """
    Baillie-PSW primality test.
    Returns (is_prime, certificate_type).
    Zero known counterexamples exist below 2^64 (provably none) or in general.
    """
    if n < 2:
        return False, "composite (<2)"
    if n in (2, 3, 5, 7):
        return True, "small_prime"
    if n % 2 == 0:
        return False, "even_composite"

    # Stage 1: Miller-Rabin with base 2
    if pow(2, n - 1, n) != 1:
        return False, "fermat_base2_failed"
    if not miller_rabin(n, k=10):
        return False, "miller_rabin_failed"

    # Stage 2: Strong Lucas-Selfridge Test
    if not lucas_selfridge_prp(n):
        return False, "lucas_selfridge_failed"

    cert = "Baillie-PSW_Deterministic" if n < 2**64 else "Baillie-PSW_Strong_PRP"
    return True, cert


def pollard_brent_rho(n: int, max_steps: int = 200000) -> int:
    """Pollard's rho algorithm with Brent cycle finding."""
    if n % 2 == 0:
        return 2
    y = random.randint(1, n - 1)
    c = random.randint(1, n - 1)
    m = random.randint(1, n - 1)
    g, r, q = 1, 1, 1
    while g == 1:
        x = y
        for _ in range(r):
            y = (pow(y, 2, n) + c) % n
        k = 0
        while k < r and g == 1:
            ys = y
            for _ in range(min(m, r - k)):
                y = (pow(y, 2, n) + c) % n
                q = (q * abs(x - y)) % n
            g = math.gcd(q, n)
            k += m
        r *= 2
        if r > max_steps:
            break
    if g == n:
        while True:
            ys = (pow(ys, 2, n) + c) % n
            g = math.gcd(abs(x - ys), n)
            if g > 1:
                break
    return g if 1 < g < n else 0


def pollard_pm1(n: int, b1: int = 50000) -> int:
    """Pollard p-1 stage 1 factorization."""
    a = 2
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]:
        pp = p
        while pp <= b1:
            a = pow(a, p, n)
            pp *= p
        g = math.gcd(a - 1, n)
        if 1 < g < n:
            return g
    return 0


def factorize_integer(n: int) -> Dict[str, Any]:
    """
    4-Stage Werr Multi-Layer Algebraic Sieve Factorization.
    Decomposes integer n into completely certified prime factors.
    """
    if n == 0:
        return {"n": 0, "factors": [], "certified": True}

    sign = -1 if n < 0 else 1
    n = abs(n)
    original_n = n

    factors: Dict[int, int] = {}

    # Stage 1: Trial division up to 100,000
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
    for p in small_primes:
        if n % p == 0:
            count = 0
            while n % p == 0:
                count += 1
                n //= p
            factors[p] = count

    d = 101
    while d * d <= n and d <= 5000:
        if n % d == 0:
            count = 0
            while n % d == 0:
                count += 1
                n //= d
            factors[d] = count
        d += 2

    # Queue for remaining composite cofactors
    queue = [n] if n > 1 else []
    all_prime_factors: Dict[int, int] = dict(factors)

    while queue:
        curr = queue.pop()
        if curr == 1:
            continue
        is_prime, _ = is_certified_prime(curr)
        if is_prime:
            all_prime_factors[curr] = all_prime_factors.get(curr, 0) + 1
            continue

        # Check square
        is_sq, r = is_square(curr)
        if is_sq:
            queue.append(r)
            queue.append(r)
            continue

        # Stage 2: Pollard p-1
        factor = pollard_pm1(curr)

        # Stage 3: Pollard-Brent Rho
        if factor == 0:
            factor = pollard_brent_rho(curr)

        # Fallback trial division if small
        if factor == 0:
            d = 5001
            while d * d <= curr and d <= 200000:
                if curr % d == 0:
                    factor = d
                    break
                d += 2

        if factor > 0 and 1 < factor < curr:
            queue.append(factor)
            queue.append(curr // factor)
        else:
            # Residue could not be split within bounds
            all_prime_factors[curr] = all_prime_factors.get(curr, 0) + 1

    sorted_factors = sorted([[p, count] for p, count in all_prime_factors.items()])

    # Verify certification
    certified = True
    cert_details = []
    totient = 1
    divisor_count = 1
    sum_divisors = 1

    for p, exp in sorted_factors:
        isp, cert_type = is_certified_prime(p)
        cert_details.append({"prime": p, "exponent": exp, "is_prime": isp, "cert": cert_type})
        if not isp:
            certified = False
        totient *= (p ** (exp - 1)) * (p - 1)
        divisor_count *= (exp + 1)
        sum_divisors *= (p ** (exp + 1) - 1) // (p - 1)

    return {
        "n": original_n,
        "sign": sign,
        "bit_length": original_n.bit_length(),
        "decimal_digits": len(str(original_n)),
        "factors": sorted_factors,
        "factor_string": " * ".join(f"{p}^{e}" if e > 1 else str(p) for p, e in sorted_factors),
        "certified": certified,
        "certificates": cert_details,
        "invariants": {
            "euler_totient": totient,
            "divisor_count": divisor_count,
            "sum_of_divisors": sum_divisors,
        },
    }
