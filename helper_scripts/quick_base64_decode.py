import base64

encoded = "your-string-here"
decoded = base64.b64decode(encoded).decode("utf-8")

print(decoded)
