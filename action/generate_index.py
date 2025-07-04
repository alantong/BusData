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
            make_index(fpath)
    with open(os.path.join(directory, "index.html"), "w", encoding="utf-8") as f:
        f.write("<html><style>ul { font-size: 40px; font-family: Helvetica; }</style>")
        if dirs:
            f.write("<ul>\n" + "\n".join(dirs) + "\n")
        if files:    
            f.write("\n".join(files) + "\n</ul>")
        f.write("</html>")
make_index("FGDB")
