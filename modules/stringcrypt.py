import os
import Cryptodome
import Cryptodome.Random
import Cryptodome.Cipher

class StringCrypt():
	def __init__(self):
		self.key = None
		self.random = Cryptodome.Random.new()

	# Reads secret key from the given path.
	def readSecretKeyFile(self, path):
		with open(path, 'r') as f:
			hexbytes = f.read()
		key = bytes.fromhex(hexbytes)
		if len(key) != Cryptodome.Cipher.AES.block_size:
			raise Exception(f"Expected key length {Cryptodome.Cipher.AES.block_size}, but got {len(key)}")
		self.key = key

	# Writes a new random secret key to the given path.
	def writeSecretKeyFile(self, path):
		key = self.random.read(Cryptodome.Cipher.AES.block_size)
		# By using os.open() here, we can ensure:
		# 1. We never clobber an existing file
		# 2. The new file, at the moment of creation, is never group- or world-readable
		fd = os.open(path, os.O_CREAT|os.O_WRONLY|os.O_EXCL, 0o600)
		with os.fdopen(fd, 'w') as f:
			f.write(key.hex())
		self.key = key

	# Given a string, returns bytes padded to the cipher's block size.
	# We use RFC5652 padding: https://datatracker.ietf.org/doc/html/rfc5652#section-6.3
	def padString(self, string):
		if Cryptodome.Cipher.AES.block_size > 255:
			raise Exception(f"Cipher block size {Cryptodome.Cipher.AES.block_size} too large for padding method")
		data = string.encode('utf-8')
		blklen = len(data) % Cryptodome.Cipher.AES.block_size
		needed = Cryptodome.Cipher.AES.block_size - blklen
		data += bytes([needed]) * needed
		return data

	# Given bytes, returns a string with the padding removed.
	def unpadString(self, data):
		padlen = data[-1]
		data = data[0:-padlen]
		return data

	# Given a string of the form "key1=val1;key2=val2;...", returns a hash.
	# It is not safe for either keys or values to contain the delimiter characters.
	def unpackFields(self, string):
		fields = {}
		for part in string.split(";"):
			(key, val) = part.split("=", 2)
			fields[key] = val
		return fields

	def encryptString(self, plaintext):
		if self.key == None:
			raise Exception("Attempt to encrypt with no secret key set")
		cipher = f"AES-{Cryptodome.Cipher.AES.block_size * 8}"
		iv = self.random.read(Cryptodome.Cipher.AES.block_size)
		aes = Cryptodome.Cipher.AES.new(self.key, Cryptodome.Cipher.AES.MODE_CBC, iv)
		ciphertext = aes.encrypt(self.padString(plaintext))
		return f"cipher={cipher};iv={iv.hex()};ciphertext={ciphertext.hex()}"

	def decryptString(self, encrypted):
		if self.key == None:
			raise Exception("Attempt to decrypt with no secret key set")
		fields = self.unpackFields(encrypted)
		cipher = f"AES-{Cryptodome.Cipher.AES.block_size * 8}"
		if fields['cipher'] != cipher:
			raise Exception(f"Unexpected cipher {fields['cipher']}")
		iv = bytes.fromhex(fields['iv'])
		ciphertext = bytes.fromhex(fields['ciphertext'])
		aes = Cryptodome.Cipher.AES.new(self.key, Cryptodome.Cipher.AES.MODE_CBC, iv)
		data = aes.decrypt(ciphertext)
		data = self.unpadString(data)
		return data.decode("utf-8")
