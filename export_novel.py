from db import init_db
from sim_engine import export_novel_markdown, init_world

if __name__ == "__main__":
    init_db()
    init_world(100)
    path = export_novel_markdown()
    print(f"Exported to {path}")
