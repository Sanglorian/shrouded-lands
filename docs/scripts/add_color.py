import csv
import os
import re

# Folder containing 31.01.md, 00.00.md etc.
WIKI_DIR = "_wiki"          # <-- this matches docs\_wiki
CSV_FILE = "colors.csv"     # CSV with coord,color_label,color_hex

if not os.path.isdir(WIKI_DIR):
    raise RuntimeError(f"Directory not found: {WIKI_DIR}")

# Load CSV into dict { "31.01": "#90B456", ... }
color_map_hex = {}
color_map_label = {}

with open(CSV_FILE, newline='', encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        coord = row["coord"]
        color_map_hex[coord] = row["color_hex"]
        # if you also want label later:
        color_map_label[coord] = row["color_label"]

for filename in os.listdir(WIKI_DIR):
    if not filename.endswith(".md"):
        continue

    coord = filename[:-3]  # strip ".md" -> "31.01"
    if coord not in color_map_hex:
        print(f"⚠ No color for {coord}, skipping {filename}")
        continue

    path = os.path.join(WIKI_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match YAML front matter: ---\n ... \n---\n body
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", content, flags=re.DOTALL)
    if not m:
        print(f"❌ No front matter in {filename}, skipping")
        continue

    yaml, body = m.groups()

    # Lines to add/update
    new_color_hex_line = f'color_hex: "{color_map_hex[coord]}"'
    # If you also want the label, uncomment this:
    # new_color_label_line = f'color_label: "{color_map_label[coord]}"'

    # Update or add color_hex
    if "color_hex:" in yaml:
        yaml = re.sub(r"color_hex:.*", new_color_hex_line, yaml)
    else:
        yaml += "\n" + new_color_hex_line

    # If you also want color_label, do the same:
    # if "color_label:" in yaml:
    #     yaml = re.sub(r"color_label:.*", new_color_label_line, yaml)
    # else:
    #     yaml += "\n" + new_color_label_line

    new_content = f"---\n{yaml}\n---\n{body}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✔ Updated {filename} with color_hex {color_map_hex[coord]}")
