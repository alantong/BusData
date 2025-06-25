import os

def make_index(directory, rel_path=""):
    files = []
    dirs = []
    for fname in sorted(os.listdir(directory)):
        fpath = os.path.join(directory, fname)
        if os.path.isfile(fpath):
            files.append(f'<li><a href="{rel_path}{fname}">{fname}</a></li>')
        elif os.path.isdir(fpath):
            dirs.append(f'<li><a href="{rel_path}{fname}/index.html">{fname}/</a></li>')
            make_index(fpath, rel_path + fname + "/")
    with open(os.path.join(directory, "index.html"), "w", encoding="utf-8") as f:
        if dirs:
            f.write("<ul>\n" + "\n".join(dirs) + "\n")
        if files:    
            f.write("\n".join(files) + "\n</ul>")

make_index("FGDB")
make_index("FGDB/BUS")
make_index("FGDB/BUS/Map")
make_index("FGDB/GMB")
make_index("FGDB/GMB/Map")