import base64

text = "your-string-here"
encoded = base64.b64encode(text.encode("utf-8"))

print(encoded.decode("utf-8"))

