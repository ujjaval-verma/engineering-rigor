import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
H = ROOT / "harness"
MARKER = "TO" + "DO"
# Built, not spelled: a literal here would exempt this line from our own scanners.
SECRET_ESCAPE = "rigor:" + " ignore-secret"
MODEL_ESCAPE = "rigor:" + " ignore-model"
# Never inline: `just init` rewrites this literal in every tracked file.
PLACEHOLDER = "example" + "_app"
TABLE_HEAD = "| # | invariant | enforced by |\n|---|---|---|\n"


def sh(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), capture_output=True, text=True, check=False, cwd=cwd)


def git_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    sh("git", "init", "-q", "-b", "main", str(tmp_path))
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    sh("git", "-C", str(tmp_path), "add", "-A")
    cfg = ["-c", "user.email=t@t", "-c", "user.name=t"]
    sh("git", "-C", str(tmp_path), *cfg, "commit", "-qm", "fixture")
    return tmp_path


@pytest.mark.parametrize(
    "msg,ok",
    [
        ("feat(P1): add thing", True),
        ("fix: narrow case", True),
        ("refactor(core)!: rename", True),
        ("docs: words", True),
        ("feat(api.v2): dotted scope", True),
        ("Merge branch 'x'", True),
        ('Revert "feat: x"', True),
        ("fixup! feat: x", True),
        ("added stuff", False),
        ("feature: wrong type", False),
        ("feat:no space", False),
        ("feat: " + "x" * 73, False),
    ],
)
def test_commit_msg(tmp_path, msg, ok):
    f = tmp_path / "MSG"
    f.write_text(msg + "\n\nbody\n")
    r = sh("python3", str(H / "check-commit-msg.py"), str(f))
    assert (r.returncode == 0) is ok, r.stderr


def test_no_todo_clean(tmp_path):
    repo = git_repo(tmp_path, {"a.py": "x = 1\n", "docs/FOLLOWUPS.md": f"- [ ] {MARKER} later\n"})
    assert sh("sh", str(H / "check-no-todo.sh"), str(repo)).returncode == 0


def test_no_todo_dirty(tmp_path):
    repo = git_repo(tmp_path, {"a.py": f"# {MARKER}: fix\n"})
    r = sh("sh", str(H / "check-no-todo.sh"), str(repo))
    assert r.returncode == 1 and "a.py" in r.stdout + r.stderr


def test_stray_md(tmp_path):
    ok = git_repo(tmp_path / "ok", {"README.md": "", "CLAUDE.md": "", "docs/x.md": ""})
    assert sh("sh", str(H / "check-stray-md.sh"), str(ok)).returncode == 0
    bad = git_repo(tmp_path / "bad", {"README.md": "", "NOTES.md": ""})
    r = sh("sh", str(H / "check-stray-md.sh"), str(bad))
    assert r.returncode == 1 and "NOTES.md" in r.stdout + r.stderr


@pytest.mark.parametrize("script", ["check-commit-msg.py", "check-no-todo.sh", "check-stray-md.sh"])
def test_help(script):
    runner = "python3" if script.endswith(".py") else "sh"
    r = sh(runner, str(H / script), "--help")
    assert r.returncode == 0 and "Usage" in r.stdout


def test_links(tmp_path):
    ok = git_repo(
        tmp_path / "ok",
        {
            "README.md": "[a](docs/a.md) [b](https://x.y) [c](#top)",
            "docs/a.md": "[up](../README.md)",
        },
    )
    assert sh("python3", str(H / "check-links.py"), str(ok)).returncode == 0
    bad = git_repo(tmp_path / "bad", {"README.md": "[gone](docs/missing.md)"})
    r = sh("python3", str(H / "check-links.py"), str(bad))
    assert r.returncode == 1 and "docs/missing.md" in r.stdout + r.stderr


def test_secrets(tmp_path):
    key = "sk-ant-api03-" + "Ab9xQ2mZ7pL4kR8sT1vW3yU6nH0jF5dG" * 2
    bad = git_repo(tmp_path / "bad", {"cfg.py": f'API_KEY = "{key}"\n'})
    r = sh("python3", str(H / "check-secrets.py"), str(bad))
    assert r.returncode == 1 and "cfg.py" in r.stdout + r.stderr
    ok = git_repo(
        tmp_path / "ok",
        {
            "cfg.py": f'API_KEY = "{key}"  # {SECRET_ESCAPE}\n',
            "low.py": 'TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n',
            ".env.example": "ANTHROPIC_API_KEY=\n",
        },
    )
    assert sh("python3", str(H / "check-secrets.py"), str(ok)).returncode == 0


@pytest.mark.parametrize("script", ["check-links.py", "check-secrets.py"])
def test_help_py(script):
    r = sh("python3", str(H / script), "--help")
    assert r.returncode == 0 and "Usage" in r.stdout


@pytest.mark.parametrize(
    "msg,ok",
    [
        ("amend! feat: x", True),
        ("chore(deps/npm): bump x", True),
    ],
)
def test_commit_msg_workflows(tmp_path, msg, ok):
    f = tmp_path / "MSG"
    f.write_text(msg + "\n")
    assert (sh("python3", str(H / "check-commit-msg.py"), str(f)).returncode == 0) is ok


def test_no_todo_case_insensitive(tmp_path):
    repo = git_repo(tmp_path, {"a.py": f"# {MARKER.lower()}: fix\n"})
    r = sh("sh", str(H / "check-no-todo.sh"), str(repo))
    assert r.returncode == 1 and "a.py" in r.stdout + r.stderr


def test_no_todo_word_boundary(tmp_path):
    repo = git_repo(tmp_path, {"a.py": f"{MARKER.lower()}s_done = 1  # hackathon\n"})
    assert sh("sh", str(H / "check-no-todo.sh"), str(repo)).returncode == 0


def test_no_todo_outside_git(tmp_path):
    (tmp_path / "loose").mkdir()
    r = sh("sh", str(H / "check-no-todo.sh"), str(tmp_path / "loose"))
    assert r.returncode == 2 and "git" in r.stdout + r.stderr


def test_links_skips_fenced_and_absolute(tmp_path):
    repo = git_repo(
        tmp_path,
        {
            "README.md": (
                "```\n[x](docs/nope.md)\n```\n"
                "[a](/docs/abs.md) [b](//x.y/z.md) [c](tel:+15550100) [d](<docs/a.md>)\n"
                "[e](docs/my%20file.md)\n"
            ),
            "docs/a.md": "",
            "docs/my file.md": "",
        },
    )
    r = sh("python3", str(H / "check-links.py"), str(repo))
    assert r.returncode == 0, r.stdout + r.stderr


def test_links_titled_and_reference(tmp_path):
    repo = git_repo(tmp_path, {"README.md": '[a](docs/missing.md "Title")\n[id]: docs/gone.md\n'})
    r = sh("python3", str(H / "check-links.py"), str(repo))
    out = r.stdout + r.stderr
    assert r.returncode == 1 and "docs/missing.md" in out and "docs/gone.md" in out


def test_links_wrong_case(tmp_path):
    repo = git_repo(tmp_path, {"README.md": "[a](docs/guide.md)", "docs/Guide.md": ""})
    r = sh("python3", str(H / "check-links.py"), str(repo))
    assert r.returncode == 1 and "docs/guide.md" in r.stdout + r.stderr


def test_links_directory_target(tmp_path):
    repo = git_repo(tmp_path, {"README.md": "[a](docs)", "docs/a.md": ""})
    assert sh("python3", str(H / "check-links.py"), str(repo)).returncode == 0


def test_secrets_vendor_prefixes(tmp_path):
    keys = {
        "gh.txt": "gho_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6q7r8",
        "pat.txt": "github_pat_" + "11ABCDEFG0aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789",
        "openai.txt": "sk-proj-" + "T3BlbkFJ0aBcDeFgHiJkLmNoPqRsTuVwXyZ123456",
        "google.txt": "AIza" + "SyD0aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567",
        "stripe.txt": "sk_live_" + "51H0aBcDeFgHiJkLmNoPqRsTu",
        "aws.txt": "ASIA" + "IOSFODNN7EXAMPLE",
        # Deliberate fixture credential; the escape keeps our own scanner off this line.
        "jwt.txt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig",  # rigor: ignore-secret
    }
    for name, value in keys.items():
        repo = git_repo(tmp_path / name, {name: value + "\n"})
        r = sh("python3", str(H / "check-secrets.py"), str(repo))
        assert r.returncode == 1 and name in r.stdout + r.stderr, name


def test_secrets_unquoted_env_assignment(tmp_path):
    repo = git_repo(tmp_path, {".env": "DB_PASSWORD=p4ssw0rd-With-Sym#2-abcdefghij\n"})
    r = sh("python3", str(H / "check-secrets.py"), str(repo))
    assert r.returncode == 1 and ".env" in r.stdout + r.stderr


def test_secrets_json_token(tmp_path):
    body = '{"token": "aB3/dE6+gH9.jK2=mN5pQ8rS1tU4vW7xY0z"}\n'  # rigor: ignore-secret
    repo = git_repo(tmp_path, {"c.json": body})
    assert sh("python3", str(H / "check-secrets.py"), str(repo)).returncode == 1


def test_secrets_placeholders_and_locks(tmp_path):
    repo = git_repo(
        tmp_path,
        {
            ".env.example": "API_KEY=REPLACE_ME_WITH_YOUR_KEY\nTOKEN=changeme-0123456789abcd\n",
            "README.md": 'API_KEY = "your-api-key-goes-here-1234"\n',
            "prose.py": 'SECRET = "the quick brown fox jumped over"\n',
        },
    )
    r = sh("python3", str(H / "check-secrets.py"), str(repo))
    assert r.returncode == 0, r.stdout + r.stderr


def test_secrets_skips_lock_files(tmp_path):
    body = (
        'token = "aB3dE6gH9jK2mN5pQ8rS1tU4vW7xY0z1"\n'  # rigor: ignore-secret  # deliberate fixture
    )
    assert (
        sh(
            "python3", str(H / "check-secrets.py"), str(git_repo(tmp_path / "a", {"a.py": body}))
        ).returncode
        == 1
    )
    ok = git_repo(tmp_path / "b", {"uv.lock": body, "deps.lock": body})
    assert sh("python3", str(H / "check-secrets.py"), str(ok)).returncode == 0


def test_no_todo_ignores_hyphenated_names(tmp_path):
    """The marker inside a hyphenated filename is a reference, not deferred work."""
    body = f"check-no-{MARKER.lower()}.sh runs in the gate\n"
    repo = git_repo(tmp_path, {"justfile": body})
    assert sh("sh", str(H / "check-no-todo.sh"), str(repo)).returncode == 0


def test_links_ignores_footnote_definitions(tmp_path):
    repo = git_repo(
        tmp_path,
        {
            "README.md": "[^1]: See the docs.\n[^n]: docs/nope.md\n[ok]: docs/a.md\n",
            "docs/a.md": "",
        },
    )
    assert sh("python3", str(H / "check-links.py"), str(repo)).returncode == 0


def test_links_reference_definition_still_checked(tmp_path):
    repo = git_repo(tmp_path, {"README.md": '[r]: docs/gone.md "Title"\n'})
    r = sh("python3", str(H / "check-links.py"), str(repo))
    assert r.returncode == 1 and "docs/gone.md" in r.stdout + r.stderr


def test_secrets_url_and_suffixed_names_not_flagged(tmp_path):
    repo = git_repo(
        tmp_path,
        {
            "cfg.py": (
                'TOKEN_URL = "https://auth.acme.dev/oauth2/v2/authorize9182"\n'
                'API_KEY_HEADER = "X-Api-Key-V2-Auth1"\n'
            ),
            "cfg.yml": "TOKEN_ENDPOINT: https://auth.acme.dev/oauth2/v2/authorize9182\n",
            "notes.md": "Ticket task-abcdefghij1234567890 tracks the rollout.\n",
        },
    )
    r = sh("python3", str(H / "check-secrets.py"), str(repo))
    assert r.returncode == 0, r.stdout + r.stderr


def test_secrets_bare_name_still_flagged(tmp_path):
    body = "API_TOKEN=latest-aB3dE6gH9jK2mN5pQ8rS1tU4\n"
    repo = git_repo(tmp_path, {".env": body})
    r = sh("python3", str(H / "check-secrets.py"), str(repo))
    assert r.returncode == 1 and ".env" in r.stdout + r.stderr


def test_secrets_ignore_file(tmp_path):
    body = 'token = "aB3dE6gH9jK2mN5pQ8rS1tU4vW7xY0z1"\n'  # rigor: ignore-secret  # fixture
    files = {"tests/fixtures/a.json": body, "tests/fixtures/b.json": body}
    assert (
        sh("python3", str(H / "check-secrets.py"), str(git_repo(tmp_path / "a", files))).returncode
        == 1
    )
    ok = git_repo(
        tmp_path / "b",
        {**files, ".secret-scan-ignore": "# recorded API fixtures\ntests/fixtures/*.json\n"},
    )
    assert sh("python3", str(H / "check-secrets.py"), str(ok)).returncode == 0


REAL = "aB3dE6gH9jK2mN5pQ8rS1tU4vW7xY0z1"  # plausible 32-char credential value


@pytest.mark.parametrize(
    "name,body,flagged",
    [
        ("bare_suffixed", f"API_KEY_PROD={REAL}\n", True),
        ("bare_numbered", f"DB_PASSWORD_2={REAL}\n", True),
        ("json_suffixed", f'{{"API_KEY_PROD": "{REAL}"}}\n', True),
        ("header_name", 'API_KEY_HEADER = "X-Api-Key-V2-Auth1-abcdef"\n', False),
        ("url_name", "TOKEN_URL=https://auth.acme.dev/oauth2/v2/authorize9182\n", False),
        ("testing_value", "TOKEN=integration-testing-token-0001\n", False),
    ],
)
def test_secrets_name_suffixes(tmp_path, name, body, flagged):
    repo = git_repo(tmp_path / name, {"cfg.txt": body})
    r = sh("python3", str(H / "check-secrets.py"), str(repo))
    assert (r.returncode == 1) is flagged, r.stdout + r.stderr


AGENTS_OK = """# Agents
| model | policy | use | verified | confidence |
|---|---|---|---|---|
| `claude-opus-5` | allowed | subagents | 2026-08-24 | high |
| `claude-haiku-4-5-20251001` | banned | never | 2026-08-24 | high |
"""


def test_models(tmp_path):
    agents = tmp_path / "agents.md"
    agents.write_text(AGENTS_OK)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text('MODEL = "claude-opus-5"\n')
    args = ["python3", str(H / "check-models.py"), "--src", str(src), "--agents", str(agents)]
    assert sh(*args).returncode == 0
    (src / "b.py").write_text('M = "claude-haiku-4-5-20251001"\n')
    r = sh(*args)
    assert r.returncode == 1 and "claude-haiku-4-5-20251001" in r.stdout + r.stderr
    (src / "b.py").write_text('M = "claude-unknown-9"\n')
    assert sh(*args).returncode == 1


def test_models_table_needs_date(tmp_path):
    agents = tmp_path / "agents.md"
    src = tmp_path / "src"
    src.mkdir()
    agents.write_text(
        AGENTS_OK.replace("2026-08-24 | high |\n| `claude-haiku", "soon | high |\n| `claude-haiku")
    )
    r = sh("python3", str(H / "check-models.py"), "--src", str(src), "--agents", str(agents))
    assert r.returncode == 1


def test_invariants(tmp_path):
    (tmp_path / "harness").mkdir()
    (tmp_path / "harness" / "x.sh").write_text("")
    claude = tmp_path / "CLAUDE.md"
    claude.write_text(TABLE_HEAD + "| 1 | a | `harness/x.sh` |\n| 2 | b | prose |\n")
    inv = str(H / "check-invariants.py")
    args = ["python3", inv, "--claude", str(claude), "--root", str(tmp_path)]
    assert sh(*args).returncode == 0
    claude.write_text(TABLE_HEAD + "| 1 | a | `harness/nope.sh` |\n")
    r = sh(*args)
    assert r.returncode == 1 and "nope.sh" in r.stdout + r.stderr
    claude.write_text(TABLE_HEAD + "| 1 | a | |\n")
    assert sh(*args).returncode == 1


def drift(repo: Path) -> int:
    return sh("sh", str(H / "check-drift.sh"), "--no-lock", str(repo)).returncode


def test_drift_clean_and_dirty(tmp_path):
    repo = git_repo(tmp_path, {"pkg/_generated/a.py": "x=1\n"})
    assert drift(repo) == 0
    (repo / "pkg/_generated/a.py").write_text("x=2\n")
    assert drift(repo) == 1
    # Staged-but-uncommitted must also fail: the check compares against HEAD, not the index.
    sh("git", "-C", str(repo), "add", "-A")
    assert drift(repo) == 1
    sh("git", "-C", str(repo), "checkout", "HEAD", "--", ".")
    sh("git", "-C", str(repo), "reset", "-q")
    assert drift(repo) == 0
    (repo / "pkg/_generated/new.py").write_text("")
    assert drift(repo) == 1
    (repo / "pkg/_generated/new.py").unlink()
    (repo / "_generated").mkdir()
    (repo / "_generated" / "root.py").write_text("")
    assert drift(repo) == 1, "a root-level _generated/ must be caught too"


def init_repo(at: Path) -> Path:
    """A scratch project to rename. init.py walks `git ls-files`, so it must be a real repo."""
    return git_repo(
        at,
        {
            f"src/{PLACEHOLDER}/__init__.py": f'"""{PLACEHOLDER}."""\n',
            "pyproject.toml": f'name = "{PLACEHOLDER}"\n',
        },
    )


def init(proj: Path, name: str) -> subprocess.CompletedProcess[str]:
    return sh("python3", str(H / "init.py"), "--root", str(proj), name)


def test_init_renames(tmp_path):
    proj = init_repo(tmp_path / "p")
    assert init(proj, "acme_billing").returncode == 0
    assert (proj / "src" / "acme_billing" / "__init__.py").read_text() == '"""acme_billing."""\n'
    assert "acme_billing" in (proj / "pyproject.toml").read_text()
    assert init(proj, "again").returncode == 1
    assert init(proj, "Bad-Name").returncode == 1


def test_init_leaves_its_own_test_suite_runnable(tmp_path):
    """This file must not carry the placeholder as a literal, or `just init` would
    rewrite its own fixture and leave `just check` red on the first command a new
    user runs. Guards the concatenation above against a well-meaning inliner."""
    assert PLACEHOLDER not in Path(__file__).read_text(encoding="utf-8")


def test_init_leaves_no_nonsense_prose(tmp_path):
    """Substitution is blind, so prose that *names* the placeholder becomes a lie in
    every adopted repo. Genuine path references (src/, pyproject) must still rename;
    sentences about "the placeholder" must not mention it by name. Checked on a real
    copy of the tracked tree, because the damage only shows up there.
    """
    if not (ROOT / "src" / PLACEHOLDER).is_dir():
        pytest.skip("already initialised — there is no placeholder left to rename")
    proj = tmp_path / "adopted"
    for rel in sh("git", "-C", str(ROOT), "ls-files").stdout.split():
        if not (ROOT / rel).is_file():
            continue  # a rename staged but not committed
        dst = proj / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    sh("git", "init", "-q", "-b", "main", str(proj))
    _git(proj, "add", "-A")
    _git(proj, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "fixture")

    r = init(proj, "acme")
    assert r.returncode == 0, r.stdout + r.stderr
    hits = _git(proj, "grep", "-l", PLACEHOLDER).stdout.split()
    assert hits == ["harness/init.py"], f"placeholder survives outside init.py: {hits}"

    menu = sh("just", "--list", "--unsorted", cwd=proj)
    assert menu.returncode == 0, menu.stdout + menu.stderr
    assert "acme placeholder" not in menu.stdout, menu.stdout
    assert "placeholder package" in menu.stdout, menu.stdout
    assert "acme" not in (proj / "CLAUDE.md").read_text(encoding="utf-8")
    assert 'name = "acme"' in (proj / "pyproject.toml").read_text(encoding="utf-8")
    assert 'strict = ["src/acme/core"]' in (proj / "pyproject.toml").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "name", ["import", "class", "src", "tests", "harness", "docs", PLACEHOLDER]
)
def test_init_rejects_unusable_names(tmp_path, name):
    proj = init_repo(tmp_path / name.replace("_", "-"))
    r = init(proj, name)
    assert r.returncode == 1, r.stdout + r.stderr
    assert (proj / "src" / PLACEHOLDER).is_dir(), "a rejected name must not have renamed anything"


def test_init_refuses_existing_destination(tmp_path):
    proj = init_repo(tmp_path / "p")
    (proj / "src" / "taken").mkdir()
    r = init(proj, "taken")
    assert r.returncode == 1 and "already exists" in r.stdout + r.stderr
    assert (proj / "src" / PLACEHOLDER).is_dir()


@pytest.mark.parametrize("where", ["nowhere", "."])
def test_drift_cannot_look(tmp_path, where):
    """Reporting "clean" because git could not be asked is worse than erroring. A path
    that does not exist and a directory that is not a work tree both say so and exit 2."""
    r = sh("sh", str(H / "check-drift.sh"), "--no-lock", str(tmp_path / where))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "drift:" in r.stdout + r.stderr


@pytest.mark.parametrize(
    "script",
    [
        "check-drift.sh",
        "status.sh",
        "doctor.sh",
        "gate.sh",
        "check-models.py",
        "check-invariants.py",
        "init.py",
    ],
)
def test_help_all(script):
    runner = "python3" if script.endswith(".py") else "sh"
    r = sh(runner, str(H / script), "--help")
    assert r.returncode == 0 and "Usage" in r.stdout


def test_status_runs():
    r = sh("sh", str(H / "status.sh"), cwd=ROOT)
    assert r.returncode == 0 and "branch:" in r.stdout


def test_doctor_runs():
    r = sh("sh", str(H / "doctor.sh"), cwd=ROOT)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    # A version check that resolves to nothing must not report as a soft warning:
    # `xargs -I{} {} --version` is a no-op on BSD, and printed `WARN python  != …`.
    assert "WARN python" not in out, out
    assert re.search(r"^ok   python \d+\.\d+", out, re.M), out


def test_doctor_fails_on_python_version_mismatch(tmp_path):
    """`.python-version` is a hard requirement, not advice: a wrong interpreter is
    the failure `just doctor` exists to name, so it exits non-zero."""
    (tmp_path / ".python-version").write_text("3.4\n")
    r = sh("sh", str(H / "doctor.sh"), cwd=tmp_path)
    out = r.stdout + r.stderr
    assert r.returncode != 0, out
    assert "FAIL python" in out and "3.4" in out, out


def test_models_scans_non_python_config(tmp_path):
    agents = tmp_path / "agents.md"
    agents.write_text(AGENTS_OK)
    src = tmp_path / "src"
    src.mkdir()
    (src / "cfg.yaml").write_text("model: claude-haiku-4-5-20251001\n")
    r = sh("python3", str(H / "check-models.py"), "--src", str(src), "--agents", str(agents))
    assert r.returncode == 1 and "cfg.yaml" in r.stdout + r.stderr


@pytest.mark.parametrize(
    "body",
    [
        "# see https://docs.anthropic.com/en/docs/claude-code\n",
        'URL = "https://claude.com/claude-code"\n',
        'X = "xclaude-opus-5-turbo"\n',
        # Sentence punctuation is not part of the id: this is the allowed model.
        "# We default to claude-opus-5.\n",
    ],
)
def test_models_ignores_non_ids(tmp_path, body):
    agents = tmp_path / "agents.md"
    agents.write_text(AGENTS_OK)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text(body)
    r = sh("python3", str(H / "check-models.py"), "--src", str(src), "--agents", str(agents))
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize(
    "legacy",
    ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-2.1"],
)
def test_models_catches_legacy_ids(tmp_path, legacy):
    """A digit-leading family is still a model id; leaving it unmatched would let a
    legacy id sit in src/ unreviewed, which is the one thing this check exists to stop."""
    agents = tmp_path / "agents.md"
    agents.write_text(AGENTS_OK)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text(f'M = "{legacy}"\n')
    r = sh("python3", str(H / "check-models.py"), "--src", str(src), "--agents", str(agents))
    out = r.stdout + r.stderr
    assert r.returncode == 1 and legacy in out and "not in AGENTS.md model table" in out


@pytest.mark.parametrize("escaped", [True, False])
def test_models_escape_comment(tmp_path, escaped):
    """The id match is deliberately broad, so it needs an opt-out the author types
    on the line it excuses — not a config file that silently widens over time."""
    agents = tmp_path / "agents.md"
    agents.write_text(AGENTS_OK)
    src = tmp_path / "src"
    src.mkdir()
    escape = f"  # {MODEL_ESCAPE}" if escaped else ""
    (src / "a.py").write_text(f'x = "claude-2024-report"{escape}\n')
    r = sh("python3", str(H / "check-models.py"), "--src", str(src), "--agents", str(agents))
    assert (r.returncode == 0) is escaped, r.stdout + r.stderr


# --- task 8: git hooks and Claude Code settings ----------------------------------------

HOOK_LIMITS = {"pre-commit": 10, "commit-msg": 6, "pre-push": 62}
HOOK_DELEGATES = {
    "pre-commit": "just check",
    "commit-msg": "harness/check-commit-msg.py",
    "pre-push": "just verify",
}
# A pre-push `just verify` runs this very suite inside a temp worktree. Without this flag
# the slow tests below would recurse into another push, and another.
NESTED = "ENGINEERING_RIGOR_NESTED"
not_nested = pytest.mark.skipif(
    bool(os.environ.get(NESTED)), reason="nested inside a pre-push `just verify`"
)


def test_hooks_are_thin_and_executable():
    """Hooks are dispatchers. Anything they do beyond `exec`ing `just` or a harness script
    is logic living where neither `just check` nor a reviewer will look for it."""
    for name, limit in HOOK_LIMITS.items():
        hook = ROOT / ".githooks" / name
        assert hook.exists() and hook.stat().st_mode & 0o111, name
        body = hook.read_text()
        n = len(body.splitlines())
        assert n <= limit, f"{name}: {n} lines, limit {limit} — move logic into harness/"
        assert HOOK_DELEGATES[name] in body, f"{name} must delegate to {HOOK_DELEGATES[name]}"
        for line in body.splitlines():
            if not line.strip().startswith("exec "):
                continue
            target = line.strip()[len("exec ") :]
            assert target.startswith(("just ", "python3 harness/", "sh harness/")), (
                f"{name} may only exec just/harness, got: {target}"
            )


def test_claude_settings_shape():
    s = json.loads((ROOT / ".claude" / "settings.json").read_text())
    perms = s["permissions"]
    deny = " ".join(perms["deny"])
    for needle in ("--no-verify", "--force", "core.hooksPath", "pip install"):
        assert needle in deny, f"deny list does not mention {needle}"
    for rule in perms["deny"] + perms["allow"]:
        # Claude Code checks path rules against Edit and Read only. A Write/Glob/
        # NotebookEdit path rule is accepted, never consulted, and warns at startup.
        assert not rule.startswith(("Write(", "NotebookEdit(", "Glob(", "MultiEdit(")), (
            f"path rule on a tool that never consults it: {rule}"
        )
        # A leading slash anchors the path to this settings file; without one the rule
        # anchors to the session cwd and stops matching <root>/harness from a subdirectory.
        if rule.startswith(("Edit(", "Read(")):
            assert rule.split("(", 1)[1].startswith("/"), f"cwd-anchored path rule: {rule}"
    hooks = s["hooks"]
    wired = {
        "PreToolUse": "harness/guard-gate.sh",
        "Stop": "harness/gate.sh",
        "SubagentStop": "harness/gate.sh",
        "SessionStart": "harness/status.sh",
    }
    for event, script in wired.items():
        assert event in hooks, f"no {event} hook"
        cmds = [h["command"] for entry in hooks[event] for h in entry["hooks"]]
        assert any(script in c and "$CLAUDE_PROJECT_DIR" in c for c in cmds), (
            f"{event} does not run {script} via $CLAUDE_PROJECT_DIR: {cmds}"
        )
    assert any(e.get("matcher") == "Bash" for e in hooks["PreToolUse"])


def test_commit_msg_hook_rejects(tmp_path):
    # The hook calls `harness/check-commit-msg.py` by relative path; git always runs hooks
    # from the worktree root, so the test must too — otherwise it "passes" on python's
    # exit 2 (file not found) rather than the check's exit 1.
    f = tmp_path / "MSG"
    f.write_text("bad message\n")
    r = sh("sh", str(ROOT / ".githooks" / "commit-msg"), str(f), cwd=ROOT)
    assert r.returncode == 1, r.stdout + r.stderr


# --- the hooks, driven by real git -----------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return sh("git", "-C", str(repo), *args)


def _worktrees(repo: Path) -> int:
    return len(_git(repo, "worktree", "list").stdout.strip().splitlines())


@pytest.fixture(scope="module")
def hook_repo(tmp_path_factory):
    """A throwaway repo holding the tracked tree, with the real hooks installed.

    `git archive HEAD`, so these tests drive *committed* hooks: commit a hook change
    before expecting it here. `uv sync` once — the hooks shell out to `just`, which is
    `uv run --locked` all the way down.
    """
    repo = tmp_path_factory.mktemp("hooks") / "repo"
    repo.mkdir()
    r = sh("sh", "-c", f'git -C "{ROOT}" archive HEAD | tar -x -C "{repo}"')
    assert r.returncode == 0, r.stdout + r.stderr
    sh("git", "init", "-q", "-b", "main", str(repo))
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("commit.gpgsign", "false")):
        _git(repo, "config", k, v)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "chore: fixture")
    _git(repo, "config", "core.hooksPath", ".githooks")
    r = sh("uv", "sync", "--locked", cwd=repo)
    assert r.returncode == 0, r.stdout + r.stderr
    return repo


@pytest.fixture
def hooked(hook_repo):
    """Module-scoped repo, per-test rollback: each test commits and edits freely."""
    base = _git(hook_repo, "rev-parse", "HEAD").stdout.strip()
    yield hook_repo
    _git(hook_repo, "reset", "-q", "--hard", base)
    _git(hook_repo, "clean", "-qfd")


@pytest.mark.slow
@not_nested
@pytest.mark.parametrize("msg,ok", [("bad message", False), ("feat: real commit", True)])
def test_commit_msg_hook_on_a_real_commit(hooked, msg, ok):
    (hooked / "note.txt").write_text("x\n")
    _git(hooked, "add", "note.txt")
    r = _git(hooked, "commit", "-m", msg)
    out = r.stdout + r.stderr
    assert (r.returncode == 0) is ok, out
    if not ok:
        assert "commit-msg:" in out, out
    subject = _git(hooked, "log", "-1", "--format=%s").stdout.strip()
    assert (subject == msg) is ok, subject


@pytest.mark.slow
@not_nested
@pytest.mark.parametrize(
    "body,ok", [("import os\n", False), ("VALUE: int = 1\n", True)], ids=["dirty", "clean"]
)
def test_pre_commit_runs_just_check(hooked, body, ok):
    """An unused import fails `just lint`, so the commit must not land."""
    # Derived, never spelled: `just init NAME` renames the package under src/.
    pkg = next(d for d in sorted((hooked / "src").iterdir()) if (d / "__init__.py").exists())
    (pkg / "probe.py").write_text(body)
    _git(hooked, "add", "-A")
    r = _git(hooked, "commit", "-m", "feat: probe")
    out = r.stdout + r.stderr
    assert (r.returncode == 0) is ok, out
    landed = _git(hooked, "log", "--oneline", "-1").stdout
    assert ("feat: probe" in landed) is ok, landed


@pytest.mark.slow
@not_nested
def test_pre_push_tamper_check_and_worktree_cleanup(hooked, tmp_path):
    """Uncommitted edit to a gate file blocks the push and never reaches a worktree;
    a clean tree runs `just verify` in a temp worktree and tears it down."""
    bare = tmp_path / "remote.git"
    sh("git", "init", "--bare", "-q", str(bare))
    _git(hooked, "remote", "add", "probe", str(bare))
    env = {**os.environ, NESTED: "1"}
    push = ["git", "-C", str(hooked), "push", "probe", "main"]
    try:
        hook = hooked / ".githooks" / "pre-commit"
        keep = hook.read_text()
        hook.write_text("#!/bin/sh\nexit 0\n")
        r = subprocess.run(push, capture_output=True, text=True, check=False, env=env)
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert ".githooks/pre-commit differs from HEAD" in out, out
        assert _worktrees(hooked) == 1, "tamper check must bail before adding a worktree"

        hook.write_text(keep)
        r = subprocess.run(push, capture_output=True, text=True, check=False, env=env)
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "pre-push: just verify @" in out, out
        assert _worktrees(hooked) == 1, "temp worktree was not removed"
    finally:
        _git(hooked, "remote", "remove", "probe")


def test_just_menu_describes_every_recipe():
    """`just` is the only discovery surface this repo ships, so a recipe with no
    description is a recipe a cold reader cannot use. `just --list` shows the comment
    line immediately above the recipe — a note parked there silently shadows it."""
    bare = sh("just", cwd=ROOT)
    assert bare.returncode == 0 and "Available recipes:" in bare.stdout, bare.stderr
    listed = sh("just", "--list", "--unsorted", cwd=ROOT).stdout
    assert listed.splitlines()[1:] == bare.stdout.splitlines()[1:], "`just` must be `--list`"
    undescribed = []
    for line in listed.splitlines()[1:]:
        name, _, desc = line.strip().partition("#")
        if not desc.strip():
            undescribed.append(name.strip())
    assert not undescribed, f"recipes with no `just --list` description: {undescribed}"


def test_ci_only_calls_just():
    """CI is a thin caller: every step is a `just` recipe, so CI and pre-push cannot drift."""
    body = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    runs = [line.split("run:", 1)[1].strip() for line in body.splitlines() if "run:" in line]
    assert runs, "ci.yml has no run steps"
    allowed = ("just ", "time just ", "uv tool install")
    for r in runs:
        assert r.startswith(allowed), f"CI must only call just: {r!r}"
    # Setting it would silently skip the slow real-hook tests CI exists to run.
    assert NESTED not in body, f"ci.yml must not set {NESTED}"
