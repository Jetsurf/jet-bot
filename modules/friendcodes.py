import re

class FriendCodes:
	def __init__(self, sqlBroker, stringCrypt):
		self.sqlBroker   = sqlBroker
		self.stringCrypt = stringCrypt

	def formatFriendCode(self, friend_code):
		match = re.match("^(?:SW-)?([0-9]{4})[- ]?([0-9]{4})[- ]?([0-9]{4})$", friend_code)
		if not match:
			return None
		return f"{match[1]}-{match[2]}-{match[3]}"

	async def getFriendCode(self, userid):
		cur = await self.sqlBroker.connect()
		await cur.execute("SELECT encrypted_friend_code FROM friend_codes WHERE (userid = %s)", (userid,))
		row = await cur.fetchone()
		await self.sqlBroker.commit(cur)

		if row is None:
			return None  # No friend code stored

		ciphertext = row[0]
		plaintext = self.stringCrypt.decryptString(ciphertext)
		return plaintext

	async def setFriendCode(self, userid, friend_code):
		friend_code = self.formatFriendCode(friend_code)
		if friend_code is None:
			raise Exception("Malformed friend code")

		ciphertext = self.stringCrypt.encryptString(friend_code)

		cur = await self.sqlBroker.connect()
		await cur.execute("DELETE FROM friend_codes WHERE (userid = %s)", (userid,))
		await cur.execute("INSERT INTO friend_codes (userid, updatetime, encrypted_friend_code) VALUES (%s, NOW(), %s)", (userid, ciphertext))
		await self.sqlBroker.commit(cur)
		return
