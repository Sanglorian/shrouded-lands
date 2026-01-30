import os
import re
import shutil

MEDIA_DIR = "media"
WIKI_DIR = "_wiki"   # adjust if yours is named differently

def normalize_name(name):
    # Normalize spaces to underscores
    new = name.replace(" ", "_")
    # Optional: collapse double underscores
    new = re.sub(r"_+", "_", new)
    return new

def rename_media_files():
    for filename in os.listdir(MEDIA_DIR):
        old_path = os.path.join(MEDIA_DIR, filename)
        if not os.path.isfile(old_path):
            continue

        new_filename = normalize_name(filename)
        new_path = os.path.join(MEDIA_DIR, new_filename)

        if new_filename != filename:
            print(f"Renaming '{filename}' → '{new_filename}'")
            shutil.move(old_path, new_path)

def update_wiki_references():
    file_map = {}
    # Build map of original->normalized for replacement
    for filename in os.listdir(MEDIA_DIR):
        normalized = normalize_name(filename)
        file_map[filename] = normalized
        file_map[filename.replace("_", " ")] = normalized  # catch SL 15.png case

    # Update references inside _wiki pages
    for root, _, files in os.walk(WIKI_DIR):
        for f in files:
            if not f.endswith(".md"):
                continue

            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()

            original = text
            for variant, normalized in file_map.items():
                text = text.replace(variant, normalized)

            if text != original:
                print(f"Updating references in {path}")
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)

if __name__ == "__main__":
    rename_media_files()
    update_wiki_references()
