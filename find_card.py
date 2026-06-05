import re
with open(r"D:\fgo ai\chat_system\index.html", "r", encoding="utf-8") as f:
    c = f.read()
m = re.search(r"onclick=.openChat", c)
if m:
    print(c[max(0, m.start()-400):m.start()+300])
else:
    print("not found")
