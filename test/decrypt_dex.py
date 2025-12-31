from Crypto.Cipher import AES
import os

key = b"dbcdcfghijklmaop"
cipher = AES.new(key, AES.MODE_ECB)

files_to_decrypt = [r"pgsHZz_unzip\kill-classes.dex", r"pgsHZz_unzip\kill-classes2.dex"]

for enc_file in files_to_decrypt:
    dir_name = os.path.dirname(enc_file)
    base_name = os.path.basename(enc_file)
    dec_file = os.path.join(dir_name, base_name.replace(".dex", "-decrypted.dex"))

    with open(enc_file, "rb") as f:
        encrypted_data = f.read()

    decrypted_data = cipher.decrypt(encrypted_data)

    with open(dec_file, "wb") as f:
        f.write(decrypted_data)
