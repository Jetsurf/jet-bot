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
		async with self.sqlBroker.context() as sql:
			row = await sql.query_first("SELECT encrypted_friend_code FROM friend_codes WHERE (userid = %s)", (userid,))

		if row is None:
			return None  # No friend code stored

		ciphertext = row['encrypted_friend_code']
		plaintext = self.stringCrypt.decryptString(ciphertext)
		return plaintext

	async def setFriendCode(self, userid, friend_code):
		friend_code = self.formatFriendCode(friend_code)
		if friend_code is None:
			raise Exception("Malformed friend code")

		existing = await self.getFriendCode(userid)
		if (existing is not None) and (friend_code == existing):
			return  # No change

		ciphertext = self.stringCrypt.encryptString(friend_code)

		async with self.sqlBroker.context() as sql:
			await sql.query("DELETE FROM friend_codes WHERE (userid = %s)", (userid,))
			await sql.query("INSERT INTO friend_codes (userid, updatetime, encrypted_friend_code) VALUES (%s, NOW(), %s)", (userid, ciphertext))

		return
