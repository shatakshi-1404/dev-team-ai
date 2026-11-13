import { diffStats, parseDiff } from "./diff";
import { buildTree } from "./tree";

const DIFF = `--- /dev/null
+++ b/app.py
@@ -0,0 +1,2 @@
+def a():
+    return 1
`;
const MOD = `--- a/x.py
+++ b/x.py
@@ -1,3 +1,3 @@
 keep
-old
+new
 tail
`;

describe("parseDiff", () => {
  it("numbers added lines", () => {
    const lines = parseDiff(DIFF).filter((l) => l.kind === "add");
    expect(lines.map((l) => [l.newNo, l.text])).toEqual([
      [1, "def a():"],
      [2, "    return 1"],
    ]);
  });
  it("tracks context, deletions and additions in a modification", () => {
    const l = parseDiff(MOD);
    expect(l.find((x) => x.kind === "del")).toMatchObject({ text: "old", oldNo: 2, newNo: null });
    expect(l.find((x) => x.kind === "add")).toMatchObject({ text: "new", newNo: 2 });
    expect(l.filter((x) => x.kind === "ctx").map((x) => x.text)).toEqual(["keep", "tail"]);
    expect(diffStats(MOD)).toEqual({ added: 1, removed: 1 });
  });
  it("returns nothing for an empty diff", () => expect(parseDiff("")).toEqual([]));
});

describe("buildTree", () => {
  it("nests paths and sorts folders before files", () => {
    const t = buildTree(["z.md", "backend/app.py", "backend/tests/test_a.py"]);
    expect(t.map((n) => n.name)).toEqual(["backend", "z.md"]);
    expect(t[0].children.map((n) => n.name)).toEqual(["tests", "app.py"]);
  });
});
