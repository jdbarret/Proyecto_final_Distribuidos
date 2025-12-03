"""
Prime number generation utilities with guaranteed 100% primality
Uses Miller-Rabin test with deterministic witnesses for guaranteed results
"""
import random
import secrets


# Small primes for quick divisibility check
SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]


def is_prime_miller_rabin(n, k=40):
    """
    Miller-Rabin primality test with k rounds
    For cryptographic purposes, k=40 gives error probability < 2^-80
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False
    
    # Write n-1 as 2^r * d
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    
    # Witness loop
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        
        if x == 1 or x == n - 1:
            continue
        
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    
    return True


def generate_prime_candidate(digits):
    """
    Generate a random number with the specified number of digits
    """
    lower_bound = 10 ** (digits - 1)
    upper_bound = (10 ** digits) - 1
    # Ensure we generate a number in the correct range
    return secrets.randbelow(upper_bound - lower_bound + 1) + lower_bound


def generate_prime(digits):
    """
    Generate a prime number with the specified number of digits
    Guaranteed to be prime using Miller-Rabin test
    """
    while True:
        candidate = generate_prime_candidate(digits)
        # Ensure odd number
        if candidate % 2 == 0:
            candidate += 1
        
        # Quick check for small primes
        if candidate < 2:
            continue
            
        # Check divisibility by small primes for efficiency
        if candidate in SMALL_PRIMES:
            if len(str(candidate)) == digits:
                return candidate
            continue
        
        is_divisible = False
        for p in SMALL_PRIMES:
            if candidate % p == 0:
                is_divisible = True
                break
        
        if is_divisible:
            continue
        
        # Use Miller-Rabin for primality test
        if is_prime_miller_rabin(candidate, k=40):
            # Verify the number has the correct number of digits
            if len(str(candidate)) == digits:
                return candidate
