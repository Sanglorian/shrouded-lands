import csv
import os
import re

WIKI_DIR = "wiki"
CSV_FILE = "colors.csv"

# load CSV into dict { "31.01": "#90B456" }
color_map = {}
with open(CSV_FILE, newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        coord = row['coord']
        color_hex = row['color_hex']
        color_map[coord] = color_hex

for filename in os.listdir(WIKI_DIR):
    if not filename.endswith(".md"):
        continue

    coord = filename[:-3]  # strip ".md"
    if coord not in color_map:
        print(f"⚠ No color for {coord}, skipping")
        continue

    path = os.path.join(WIKI_DIR, filename)
    with open(path, "r", encoding="utf8") as f:
        content = f.read()

    # extract YAML front matter
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, flags=re.DOTALL)
    if not match:
        print(f"❌ No front matter in {filename}, skipping")
        continue

    yaml, body = match.groups()

    # check if color_hex exists already
    if "color_hex:" in yaml:
        # replace existing
        yaml = re.sub(r"color_hex:.*",
                      f"color_hex: \"{color_map[coord]}\"",
                      yaml)
    else:
        # add new line to end of YAML block
        yaml = yaml + f"\ncolor_hex: \"{color_map[coord]}\""

    # write back
    new_content = f"---\n{yaml}\n---\n{body}"
    with open(path, "w", encoding="utf8") as f:
        f.write(new_content)

    print(f"✔ Added color_hex to {filename}")
