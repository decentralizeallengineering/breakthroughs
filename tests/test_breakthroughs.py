import importlib.machinery
import importlib.util
import io
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "bin", "breakthroughs")
loader = importlib.machinery.SourceFileLoader("breakthroughs_mod", SCRIPT)
spec = importlib.util.spec_from_loader("breakthroughs_mod", loader)
bt = importlib.util.module_from_spec(spec)
loader.exec_module(bt)


def idea_line(text):
    return json.dumps({"idea": text, "why_it_could_work": "Ann Example says so.",
                       "first_step": "read the readme", "evidence_in_repo": "none"})


class FakeRunner:
    """Records every call. Hot calls answer from a script; the cool call judges all ids."""

    def __init__(self, hot_output):
        self.calls = []
        self.hot_output = hot_output

    def __call__(self, cmd, prompt, cwd, timeout):
        self.calls.append((cmd, prompt, cwd))
        if "You are the reviewer" in prompt:
            ids = [json.loads(x)["id"] for x in prompt.splitlines() if x.startswith('{"id"') and '"agreement"' in x]
            return 0, "\n".join(json.dumps(
                {"id": i, "works": 3, "evidence_checked": "none", "reliability_risk": "x",
                 "cost_hours": 2, "reversibility": "easy", "verdict": "TRY NOW"}) for i in ids), ""
        return self.hot_output(prompt)


class Tests(unittest.TestCase):
    def run_cli(self, argv, runner):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            code = bt.main(argv + ["--out", os.path.join(tmp, "o")], runner=runner, out=out)
            files = sorted(os.listdir(os.path.join(tmp, "o"))) if os.path.isdir(os.path.join(tmp, "o")) else []
            ideas = []
            if "ideas.jsonl" in files:
                with open(os.path.join(tmp, "o", "ideas.jsonl")) as fh:
                    ideas = [json.loads(x) for x in fh]
        return code, out.getvalue(), files, ideas

    def test_clamping(self):
        self.assertEqual(bt.clamp_workers(2), 3)
        self.assertEqual(bt.clamp_workers(15), 10)
        self.assertEqual(bt.clamp_workers(6), 6)
        r = FakeRunner(lambda p: (0, idea_line("alpha beta"), ""))
        self.run_cli(["run", HERE, "--goal", "g", "--workers", "2"], r)
        self.assertEqual(len([c for c in r.calls if "You are the reviewer" not in c[1]]), 3)
        r = FakeRunner(lambda p: (0, idea_line("alpha beta"), ""))
        self.run_cli(["run", HERE, "--goal", "g", "--workers", "15"], r)
        self.assertEqual(len([c for c in r.calls if "You are the reviewer" not in c[1]]), 10)

    def test_distinct_lens_per_worker(self):
        r = FakeRunner(lambda p: (0, idea_line("alpha beta"), ""))
        self.run_cli(["run", HERE, "--goal", "g", "--workers", "10"], r)
        lens_lines = {next(l for l in c[1].splitlines() if l.startswith("LENS:"))
                      for c in r.calls if "You are the reviewer" not in c[1]}
        self.assertEqual(len(lens_lines), 10)
        for c in r.calls:
            self.assertIn("Read,Grep,Glob", c[0])

    def test_dedupe_and_agreement(self):
        lens_a = "Cache the build outputs on a shared disk"
        lens_b = "cache the build outputs on a shared disk please"
        found = [("one", {"idea": lens_a, "why_it_could_work": "w", "first_step": "f", "evidence_in_repo": "e"}),
                 ("two", {"idea": lens_b, "why_it_could_work": "w", "first_step": "f", "evidence_in_repo": "e"}),
                 ("two", {"idea": lens_b, "why_it_could_work": "w", "first_step": "f", "evidence_in_repo": "e"}),
                 ("three", {"idea": "Replace the scheduler with cron", "why_it_could_work": "w",
                            "first_step": "f", "evidence_in_repo": "e"})]
        merged = bt.merge_ideas(found)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["agreement"], 2)
        self.assertEqual(merged[0]["lenses"], ["one", "two"])
        self.assertEqual(merged[1]["agreement"], 1)

    def test_bad_json_recorded_not_guessed(self):
        def hot(prompt):
            if "LENS: Delete half" in prompt:
                return 0, idea_line("good idea number one") + "\n{not json at all\n", ""
            return 0, "this is prose, not json", ""
        r = FakeRunner(hot)
        code, _, files, recs = self.run_cli(["run", HERE, "--goal", "g", "--workers", "3"], r)
        self.assertEqual(code, 0)
        ideas = [x for x in recs if x["type"] == "idea"]
        fails = [x for x in recs if x["type"] == "parse_failure"]
        self.assertEqual([i["idea"] for i in ideas], ["good idea number one"])
        self.assertEqual(len(fails), 3, fails)
        self.assertTrue(any(f["raw"] == "{not json at all" for f in fails))
        self.assertIn("ideas.jsonl", files)

    def test_dry_run_calls_no_model(self):
        def boom(*a, **k):
            raise AssertionError("model called in dry run")
        code, out, files, _ = self.run_cli(["run", HERE, "--goal", "g", "--workers", "4", "--dry-run"], boom)
        self.assertEqual(code, 0)
        self.assertEqual(out.count("HOT lens="), 4)
        self.assertIn("COOL", out)
        self.assertIn("claude -p --model haiku", out)
        self.assertIn("claude -p --model sonnet", out)
        self.assertEqual(files, [])


if __name__ == "__main__":
    unittest.main()
