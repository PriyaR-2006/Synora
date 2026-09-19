import os

d = "demo_data/big_test_drive"
os.makedirs(d, exist_ok=True)

with open(f"{d}/notes.txt", "w") as f:
    f.write("Synora test content. " * 5000)

with open(f"{d}/report.txt", "w") as f:
    f.write("Quarterly report data. " * 5000)

with open(f"{d}/copy1.txt", "w") as f:
    f.write("identical content here")

with open(f"{d}/copy2.txt", "w") as f:
    f.write("identical content here")

print("Created files at:", os.path.abspath(d))