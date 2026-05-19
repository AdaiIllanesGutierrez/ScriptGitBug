# GitBug-Java + EvoSuite Experiment

Generates tests with EvoSuite on the **fixed** version of a bug, then runs those same tests on both the fixed and buggy versions. If tests pass on fixed and fail on buggy → the bug is revealed.

---

## Files

| File | What it does |
|---|---|
| `run_screened_bugs.py` | **Main script.** Batch runner — loops bugs × seeds × java versions, calls the worker, writes `results.csv` |
| `gitbug_evosuite_runner.py` | **Worker.** Runs the full EvoSuite pipeline for one (bug, class, seed, java) combination. Called automatically by the batch runner |
| `bugs.csv` | Input bug list: `bug_id, class_under_test`. No java version — runs with whatever `--java-versions` you pass |
| `bugs_java_assigned.csv` | Input bug list with `java_version` per row. Each bug uses only its assigned version (Java 8 or 11) |
| `assign_java_versions.py` | Generates `bugs_java_assigned.csv` from a baseline `results.csv`. Bugs that worked → Java 11, failed → Java 8 |
| `analyze_evosuite_failures.py` | Post-run. Reads logs and classifies why EvoSuite failed (classpath error, RMI crash, CFG error, etc.) |
| `extract_evosuite_metrics.py` | Post-run. Extracts coverage metrics from EvoSuite logs and adds them to results |
| `docker/java8.Dockerfile` | Docker image with Java 8 + Maven |
| `docker/java11.Dockerfile` | Docker image with Java 11 + Maven |
| `docker/build.sh` | Builds both Docker images (run once before experiments) |

---

## Prerequisites

Before running anything, make sure you have:

- **Python 3.10+**
- **Poetry** — used to run scripts inside the GitBug-Java environment
- **Docker** — used to run Maven and EvoSuite in the correct Java version
- **GitBug-Java** repo cloned — [https://github.com/gitbugactions/gitbug-java](https://github.com/gitbugactions/gitbug-java)
- **EvoSuite 1.2.0 jar** — download from [https://github.com/EvoSuite/evosuite/releases/tag/v1.2.0](https://github.com/EvoSuite/evosuite/releases/tag/v1.2.0)
- **JUnit 4.13.2 jar** and **Hamcrest 1.3 jar** — these are pulled automatically by Maven into `~/.m2/` when you first build any Maven project, or you can download them manually

---

## Step 1 — Clone and install GitBug-Java

```bash
git clone https://github.com/gitbugactions/gitbug-java.git
cd gitbug-java
poetry install
```

---

## Step 2 — Update paths in `run_screened_bugs.py`

Open `run_screened_bugs.py` and update the constants at the top of the file to match your machine:

```python
RUNNER        = "/path/to/gitbug_evosuite_runner.py"
GITBUG_REPO   = "/path/to/gitbug-java"
EVOSUITE_JAR  = "/path/to/evosuite-1.2.0.jar"
JUNIT_JAR     = "/path/to/.m2/repository/junit/junit/4.13.2/junit-4.13.2.jar"
HAMCREST_JAR  = "/path/to/.m2/repository/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar"
BASE_WORK_ROOT = Path("/path/to/output/gitbug-batch")
DEFAULT_BUGS_CSV = Path("/path/to/bugs.csv")
```

**What each path is:**

| Constant | What to put here |
|---|---|
| `RUNNER` | Full path to `gitbug_evosuite_runner.py` (this repo) |
| `GITBUG_REPO` | Where you cloned GitBug-Java |
| `EVOSUITE_JAR` | Where you saved `evosuite-1.2.0.jar` |
| `JUNIT_JAR` | Usually `~/.m2/repository/junit/junit/4.13.2/junit-4.13.2.jar` |
| `HAMCREST_JAR` | Usually `~/.m2/repository/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar` |
| `BASE_WORK_ROOT` | Any folder where output files and run folders will be written |
| `DEFAULT_BUGS_CSV` | Full path to `bugs.csv` in this repo |

> **Tip:** If you are not sure where your `.m2` folder is, run `find ~ -name "junit-4.13.2.jar" 2>/dev/null` to locate it.

---

## Step 3 — Build Docker images (once)

```bash
bash /path/to/docker/build.sh
```

This creates two Docker images: `gitbug-java8` and `gitbug-java11`. Only needed once per machine. After building, verify with:

```bash
docker images | grep gitbug
```

You should see both `gitbug-java8` and `gitbug-java11`.

---

## Step 4 — Test with a small run first

Always test with a few bugs before running everything. Run from the GitBug-Java repo directory:

```bash
cd /path/to/gitbug-java

poetry run python /path/to/investigation/run_screened_bugs.py \
  --bugs-csv /path/to/investigation/bugs_java_assigned.csv \
  --seeds 3147383999447 \
  --limit 5
```

You can also hange the number from 5 to others

Expected output:
```
Loaded 5 bug(s) x 1 seed(s) = 5 total runs.
Java versions: per-bug (from CSV)
...
[1/5] some-bug :: some.Class :: seed=3147383999447 :: java=8
  fixed=PASS | buggy=FAIL | result=BUG-REVEALING
```

If you see `RUNNER ERROR` on every run, check your paths in Step 2.

---

## Running the full experiment

### Option A — All bugs, one seed, per-bug java version (90 runs, recommended)

```bash
cd /path/to/gitbug-java

poetry run python /path/to/investigation/run_screened_bugs.py \
  --bugs-csv /path/to/investigation/bugs_java_assigned.csv \
  --seeds 3147383999447
```

### Option B — All bugs, both java versions, one seed (180 runs)

Useful if you want to compare Java 8 vs Java 11 for every bug:

```bash
cd /path/to/gitbug-java

poetry run python /path/to/investigation/run_screened_bugs.py \
  --bugs-csv /path/to/investigation/bugs.csv \
  --seeds 3147383999447 \
  --java-versions 8 11
```

### Option C — All bugs, all 30 seeds, per-bug java version (2700 runs)

Full statistical experiment:

```bash
cd /path/to/gitbug-java

poetry run python /path/to/investigation/run_screened_bugs.py \
  --bugs-csv /path/to/investigation/bugs_java_assigned.csv \
  --seeds 3147383999447 9617663486099 5379124608314 4823761945872 9865472301598 \
          4098156729301 4378296150428 8912357690412 4082159706387 5017574018895 \
          3157718788187 8462097531802 8394051763254 7861948975955 5785033018534 \
          4687593021847 1369827450193 8912045678210 4195939566797 5919993929691 \
          8492013567021 4629875132408 7245638910523 4823167590241 7237611861410 \
          4872395016821 4967023185649 6048152937021 9516437924806 8609571234567
```

> Add `--force` to any command to re-run bugs that already have results. IMportant

---

## Key flags

| Flag | Default | Meaning |
|---|---|---|
| `--bugs-csv` | `bugs.csv` | Which bug list to use |
| `--seeds` | first 5 seeds | EvoSuite random seeds |
| `--java-versions` | `8 11` | Java versions to test (ignored if CSV has `java_version` column) |
| `--limit N` | no limit | Run only the first N bugs |
| `--timeout N` | 1800 | Seconds allowed per run |
| `--heap` | `4g` | Java heap for EvoSuite |
| `--force` | off | Re-run even if results already exist |
| `--cleanup-targets` | off | Delete Maven `target/` after each run (saves disk space) |

---

## Output

Results are written to `<BASE_WORK_ROOT>/results.csv`.

Each run also gets its own folder:
```
<BASE_WORK_ROOT>/<bug_id>__<class>__seed_<N>__java<V>/
  buggy/        ← buggy checkout
  fixed/        ← fixed checkout + generated tests
  logs/
    evosuite_fixed.log               ← EvoSuite output
    batch_driver_stdout_stderr.log   ← full run log
```

### Result meanings

| Result | fixed | buggy | Meaning |
|---|---|---|---|
| `BUG-REVEALING` | PASS | FAIL | Best case — bug is detected |
| `NO DIFFERENCE FOUND` | PASS | PASS | Tests valid but don't expose the bug |
| `UNSTABLE/UNHELPFUL` | FAIL | FAIL | Tests fail on both — not reliable |
| `EVOSUITE NO TESTS` | — | — | EvoSuite crashed or produced no tests |
| `RUNNER ERROR` | — | — | Script-level error (compile failed, permission, etc.) |
| `TIMEOUT` | — | — | Run exceeded `--timeout` |

---

## Post-run analysis

### Classify why EvoSuite failed

```bash
python3 /path/to/analyze_evosuite_failures.py
```

Reads logs, classifies failures by category, writes `evosuite_failures_analysis.csv`.

### Re-assign java versions from a new baseline

Run a baseline first, then:

```bash
python3 /path/to/investigation/assign_java_versions.py \
  --results-csv /path/to/gitbug-batch/results.csv \
  --out /path/to/investigation/bugs_java_assigned.csv
```

Bugs with `BUG-REVEALING` or `NO DIFFERENCE FOUND` → `java_version=11`. Everything else → `java_version=8`.

---

## Why Docker

EvoSuite 1.2.0 was designed for Java 8. On Java 11, some projects fail with:
```
Unsupported class file major version 55
```

Docker lets each bug run inside the correct Java environment without installing multiple Java versions on the host. Python runs on the host; Maven and EvoSuite run inside the container. All paths are mounted at the same absolute location inside the container so classpath resolution works correctly.

---

## Common errors

### `ModuleNotFoundError: No module named 'gitbugactions'`
Run the script with `poetry run` from inside the GitBug-Java repo, not with system Python.

### `RUNNER ERROR` on every bug
Check the paths in `run_screened_bugs.py` — one of the jars or folders likely doesn't exist at the path specified.

### `EVOSUITE NO TESTS` for many bugs
Check `logs/evosuite_fixed.log` inside the bug's folder. Common causes: RMI crash, classpath error, or an EvoSuite internal bug with that class.

### Docker permission errors
Make sure Docker is running and your user is in the `docker` group:
```bash
sudo usermod -aG docker $USER
# then log out and back in
```
