"""Small, local, evidence-gated memory runtime. Python 3.10+, stdlib only."""
import argparse
import json
import math
import re
import sqlite3
import uuid
from datetime import datetime, timezone


def terms(text):
    return set(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", text.lower()))


class Kernel:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
          id TEXT PRIMARY KEY, project TEXT, trigger TEXT, lesson TEXT,
          evidence TEXT, origin TEXT, state TEXT, utility REAL DEFAULT 0.5);
        CREATE TABLE IF NOT EXISTS feedback (
          memory TEXT, task TEXT, reward REAL, evidence TEXT,
          PRIMARY KEY(memory, task));
        CREATE TABLE IF NOT EXISTS events (
          sequence INTEGER PRIMARY KEY, time TEXT, kind TEXT, payload TEXT);
        """)

    def event(self, kind, payload):
        self.db.execute("INSERT INTO events(time,kind,payload) VALUES(?,?,?)",
                        (datetime.now(timezone.utc).isoformat(), kind,
                         json.dumps(payload, ensure_ascii=False)))

    def add(self, project, trigger, lesson, evidence, origin):
        if not all(isinstance(x, str) and x.strip() for x in
                   (project, trigger, lesson, evidence, origin)):
            raise ValueError("All memory fields require nonempty text")
        mid = uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO memories VALUES(?,?,?,?,?,?,?,?)",
                            (mid, project, trigger, lesson, evidence, origin, "candidate", .5))
            self.event("add", {"id": mid})
        return mid

    def get(self, mid):
        row = self.db.execute("SELECT * FROM memories WHERE id=?", (mid,)).fetchone()
        if row is None:
            raise KeyError(mid)
        return dict(row)

    def feedback(self, mid, task, reward, evidence):
        m = self.get(mid)
        if not task.strip() or not evidence.strip() or not math.isfinite(reward) or not 0 <= reward <= 1:
            raise ValueError("Feedback needs task, evidence and finite reward in [0,1]")
        if task == m["origin"]:
            raise ValueError("Discovery task cannot validate its own lesson")
        with self.db:
            self.db.execute("INSERT INTO feedback VALUES(?,?,?,?)", (mid, task, reward, evidence))
            rewards = [r[0] for r in self.db.execute("SELECT reward FROM feedback WHERE memory=?", (mid,))]
            utility = (1 + sum(rewards)) / (2 + len(rewards))
            # Conservative prototype gate, not a statistical significance claim.
            state = "active" if len(rewards) >= 3 and min(rewards) >= .5 and utility >= .7 else "candidate"
            if m["state"] == "archived":
                state = "archived"
            self.db.execute("UPDATE memories SET utility=?,state=? WHERE id=?", (utility, state, mid))
            self.event("feedback", {"id": mid, "task": task, "reward": reward, "state": state})
        return self.get(mid)

    def archive(self, project):
        if project == "global":
            raise ValueError("Archive a named project, not the global namespace")
        with self.db:
            count = self.db.execute("UPDATE memories SET state='archived' WHERE project=?", (project,)).rowcount
            self.event("archive", {"project": project, "count": count})
        return count

    def recall(self, query, project, budget=2048, include_archived=False):
        """Budget is UTF-8 bytes of the exact returned text, NOT model tokens."""
        if budget < 0:
            raise ValueError("Budget must be nonnegative")
        q = terms(query)
        ranked = []
        for row in self.db.execute("SELECT * FROM memories WHERE project IN (?, 'global')", (project,)):
            m = dict(row)
            if m["state"] != "active" and not (include_archived and m["state"] == "archived"):
                continue
            overlap = len(q & terms(m["trigger"] + " " + m["lesson"])) / max(1, len(q))
            if overlap:
                ranked.append((overlap * m["utility"], m))
        selected = []
        for _, m in sorted(ranked, key=lambda pair: (-pair[0], pair[1]["id"])):
            item = {k: m[k] for k in ("id", "trigger", "lesson", "evidence", "state")}
            line = json.dumps(item, ensure_ascii=False)
            candidate = "\n".join(selected + [line])
            if len(candidate.encode("utf-8")) <= budget:
                selected.append(line)
        return "\n".join(selected)

    def close(self):
        self.db.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default="memory.sqlite3")
    sub = p.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add")
    for field in ("project", "trigger", "lesson", "evidence", "origin"):
        add.add_argument("--" + field, required=True)
    feed = sub.add_parser("feedback")
    for field in ("id", "task", "evidence"):
        feed.add_argument("--" + field, required=True)
    feed.add_argument("--reward", type=float, required=True)
    rec = sub.add_parser("recall")
    rec.add_argument("query")
    rec.add_argument("--project", required=True)
    rec.add_argument("--budget", type=int, default=2048)
    rec.add_argument("--include-archived", action="store_true")
    arc = sub.add_parser("archive")
    arc.add_argument("project")
    args = vars(p.parse_args())
    k = Kernel(args.pop("db"))
    command = args.pop("command")
    if command == "feedback":
        args["mid"] = args.pop("id")
    try:
        result = getattr(k, command)(**args)
        print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False))
    finally:
        k.close()


if __name__ == "__main__":
    main()
