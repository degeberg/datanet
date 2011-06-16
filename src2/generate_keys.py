#!/usr/bin/python2

from Crypto.PublicKey import RSA
from Crypto import Random

rng = Random.new().read

private_key = RSA.generate(1024, rng)

with open('id_rsa', 'w') as f:
    f.write(private_key.exportKey())
