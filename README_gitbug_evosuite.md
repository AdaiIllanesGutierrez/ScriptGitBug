# GitBug-Java + EvoSuite Experiment Runner

This project contains a small automation pipeline for running EvoSuite experiments on GitBug-Java bugs.

The main idea is simple: generate tests from the **fixed** version of a bug, then run the exact same generated tests on both the fixed and buggy versions. If the tests pass on fixed and fail on buggy, then the generated test suite revealed the bug.

```text
fixed = PASS
buggy = FAIL
```

That is the strongest result.

---

## 1. Important note about paths

The scripts use local paths from the machine where the experiment is being run. Before running anything, check the path constants near the top of the scripts.

In `run_screened_bugs.py`, check values like:

```python
RUNNER = ".../gitbug_evosuite_runner.py"
GITBUG_REPO = ".../gitbug-java"
EVOSUITE_JAR = ".../evosuite-1.2.0.jar"
JUNIT_JAR = ".../junit-4.13.2.jar"
HAMCREST_JAR = ".../hamcrest-core-1.3.jar"
BASE_WORK_ROOT = Path(".../gitbug-batch")
DEFAULT_BUGS_CSV = Path(".../bugs.csv")
```

These should point to your own files and folders.

For example, on my machine they may look like:

```text
GitBug-Java repo:   /home/atsum/Documents/gitbug-java
Scripts folder:     /home/atsum/Documents/investigation
EvoSuite jar:       /home/atsum/Desktop/evosuite-1.2.0.jar
Batch output:       /home/atsum/Documents/gitbug-batch
Input bugs CSV:     /home/atsum/Documents/investigation/bugs.csv
```

But if your folders are different, update the constants in the scripts before running.

A good way to check a path is:

```bash
ls /path/to/file-or-folder
```

For example:

```bash
ls /path/to/gitbug-java
ls /path/to/evosuite-1.2.0.jar
ls /path/to/bugs.csv
```

---

## 2. Files in the workflow

### `gitbug_evosuite_runner.py`

This is the **one-bug worker**.

It runs the full EvoSuite workflow for one bug/class pair:

1. Checkout the buggy version.
2. Checkout the fixed version.
3. Compile the fixed version.
4. Generate EvoSuite tests on the fixed version.
5. Compile the generated tests.
6. Run the tests on the fixed version.
7. Compile the buggy version.
8. Run the same fixed-generated tests on the buggy version.
9. Print a result summary.

Most of the time, this file is called automatically by `run_screened_bugs.py`.

---

### `run_screened_bugs.py`

This is the **batch runner**.

It reads bug/class pairs from a CSV file, calls `gitbug_evosuite_runner.py` for each row, and stores results in a CSV file.

It supports:

```text
--limit             run only the first N rows
--force             rerun even if previous results exist
--timeout           maximum time per bug, in seconds
--heap              Java heap size for EvoSuite
--cleanup-targets   delete Maven target/ folders after each bug to save disk
```

This is the script normally used for experiments.

---

### `bugs.csv`

This is the input list of bug/class pairs.

Format:

```csv
bug_id,class_under_test
semver4j-semver4j-10102b374298,org.semver4j.RangesList
klausbrunner-solarpositioning-4d35aecb4840,net.e175.klaus.solarpositioning.DeltaT
```

Each row means:

```text
Run EvoSuite for this bug, targeting this Java class.
```

A bug can appear more than once if multiple classes changed:

```csv
klausbrunner-solarpositioning-79c0044373b4,net.e175.klaus.solarpositioning.Grena3
klausbrunner-solarpositioning-79c0044373b4,net.e175.klaus.solarpositioning.SPA
```

In that case, each row is a separate bug-class experiment.

---

### `screen_gitbug_candidates.py`

This optional helper script finds possible candidates.

It does not run EvoSuite. It only screens GitBug-Java bugs by checking:

1. Can the buggy version be checked out?
2. Can the fixed version be checked out?
3. Which `.java` files changed?
4. Can the fixed version compile with Maven?

It writes candidate rows into:

```text
screened_candidates.csv
```

Only rows with `compile_pass` are good candidates for `bugs.csv`.

---

## 3. Environment setup

Run the scripts from the GitBug-Java Poetry environment.

The general pattern is:

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py
```

For example, if the repository is in `/home/atsum/Documents/gitbug-java` and the scripts are in `/home/atsum/Documents/investigation`:

```bash
cd /home/atsum/Documents/gitbug-java
poetry run python /home/atsum/Documents/investigation/run_screened_bugs.py
```

Do not run the script with plain `python` from another folder if GitBug-Java depends on Poetry. That can cause errors such as:

```text
ModuleNotFoundError: No module named 'gitbugactions'
```

If Java needs to be set manually, use the correct Java path for your machine. Example for Java 11 on Ubuntu:

```bash
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH="$JAVA_HOME/bin:$PATH"
```

The batch script can also set Java 11 automatically if the path exists on the machine.

---

## 4. Running the batch script

Replace the paths below with your real paths.

### Run the first 5 bugs

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py --limit 5 --force
```

Example:

```bash
cd /home/atsum/Documents/gitbug-java
poetry run python /home/atsum/Documents/investigation/run_screened_bugs.py --limit 5 --force
```

### Run the first 10 bugs

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py --limit 10 --force
```

### Run all bugs in `bugs.csv`

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py --force
```

### Run with a 2-minute timeout per bug

Timeout is in seconds, so 2 minutes is `120`:

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py --timeout 120 --force
```

### Run with more EvoSuite heap

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py --heap 6g --force
```

### Clean Maven `target/` folders after each run

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py --cleanup-targets --force
```

This is useful if disk space becomes a problem.

---

## 5. Output structure

The batch script writes a summary CSV to:

```text
<BASE_WORK_ROOT>/results.csv
```

Example:

```text
/home/atsum/Documents/gitbug-batch/results.csv
```

Check it with:

```bash
cat <BASE_WORK_ROOT>/results.csv
```

Example:

```bash
cat /home/atsum/Documents/gitbug-batch/results.csv
```

Count result types:

```bash
cut -d, -f6 <BASE_WORK_ROOT>/results.csv | sort | uniq -c
```

Each bug/class run gets its own folder:

```text
<BASE_WORK_ROOT>/<bug-id>__<class-name>/
```

Inside that folder:

```text
buggy/
fixed/
logs/
```

Useful log files:

```text
logs/evosuite_fixed.log
logs/compile_generated_tests.log
logs/run_fixed.log
logs/run_buggy.log
logs/batch_driver_stdout_stderr.log
```

---

## 6. Result meanings

### `BUG-REVEALING`

```text
fixed = PASS
buggy = FAIL
```

Best case. EvoSuite generated a valid test suite that exposes the bug.

### `NO DIFFERENCE FOUND`

```text
fixed = PASS
buggy = PASS
```

The generated tests are valid, but they do not reveal the bug.

### `UNSTABLE/UNHELPFUL`

```text
fixed = FAIL
buggy = FAIL
```

The tests fail even on the fixed version, so they are not reliable for bug detection.

This can happen with flaky or overfitted EvoSuite assertions, especially in numerical or floating-point-heavy code.

### `MIXED RESULT`

```text
fixed = FAIL
buggy = PASS
```

Unusual. Inspect the logs carefully.

### `EVOSUITE NO TESTS`

EvoSuite did not create any `*_ESTest.java` files.

Usually check:

```bash
cat <BUG_WORK_ROOT>/logs/evosuite_fixed.log
```

Common causes include EvoSuite crashes, RMI/class-loading problems, or export failures.

### `TIMEOUT`

The run exceeded the timeout set by `--timeout`.

The log should contain something like:

```text
[TIMEOUT] Killed after 120 seconds.
```

### `COMPILE FAILED`

The project did not compile with Maven.

### `TEST COMPILE FAILED`

EvoSuite generated tests, but `javac` could not compile them.

---

## 7. Checking one result manually

For a specific bug-class folder:

```bash
cd <BUG_WORK_ROOT>
```

Example:

```bash
cd /home/atsum/Documents/gitbug-batch/semver4j-semver4j-10102b374298__org_semver4j_RangesList
```

Check generated test source files:

```bash
find fixed/evosuite-tests -name "*.java"
```

Check compiled test files:

```bash
find fixed/evosuite-tests -name "*.class"
```

Check JUnit results:

```bash
cat logs/run_fixed.log
cat logs/run_buggy.log
```

A strong bug-revealing case should have:

```text
run_fixed.log -> OK (...)
run_buggy.log -> FAILURES!!!
```

---

## 8. Running one bug manually

Most runs should go through `run_screened_bugs.py`, but the worker can be called directly.

Template:

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/gitbug_evosuite_runner.py \
  --gitbug-repo <GITBUG_REPO> \
  --bug-id <BUG_ID> \
  --class-under-test <FULLY_QUALIFIED_CLASS> \
  --evosuite-jar <EVOSUITE_JAR> \
  --junit-jar <JUNIT_JAR> \
  --hamcrest-jar <HAMCREST_JAR> \
  --work-root <WORK_ROOT> \
  --heap 4g
```

Example:

```bash
cd /home/atsum/Documents/gitbug-java
poetry run python /home/atsum/Documents/investigation/gitbug_evosuite_runner.py \
  --gitbug-repo /home/atsum/Documents/gitbug-java \
  --bug-id semver4j-semver4j-10102b374298 \
  --class-under-test org.semver4j.RangesList \
  --evosuite-jar /home/atsum/Desktop/evosuite-1.2.0.jar \
  --junit-jar /home/atsum/.m2/repository/junit/junit/4.13.2/junit-4.13.2.jar \
  --hamcrest-jar /home/atsum/.m2/repository/org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar \
  --work-root /home/atsum/Documents/gitbug-batch/manual-semver \
  --heap 4g
```

---

## 9. Finding more candidate bugs

Run the candidate screening script from the GitBug-Java Poetry environment:

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/screen_gitbug_candidates.py
```

It creates:

```text
screened_candidates.csv
```

Only rows with:

```text
compile_pass
```

should be copied into `bugs.csv`.

To create `bugs.csv` from all compile-pass rows:

```bash
python3 - <<'PY'
import csv

src = "<SCRIPTS_DIR>/screened_candidates.csv"
dst = "<SCRIPTS_DIR>/bugs.csv"

seen = set()
rows = []

with open(src, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["status"] != "compile_pass":
            continue

        bug_id = row["bug_id"].strip()
        cls = row["class_under_test"].strip()

        if not bug_id or not cls:
            continue

        key = (bug_id, cls)
        if key in seen:
            continue

        seen.add(key)
        rows.append({"bug_id": bug_id, "class_under_test": cls})

with open(dst, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["bug_id", "class_under_test"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} bug-class entries to {dst}")
PY
```

Important: replace `<SCRIPTS_DIR>` with your actual scripts folder before running that block.

---

## 10. Java version notes

The screening script checks compilation with the Java version active in the environment.

So if the current environment uses Java 11, then:

```text
compile_pass
```

means:

```text
This bug/class compiled with Java 11 on this machine.
```

It does not automatically test both Java 8 and Java 11.

If needed, switch `JAVA_HOME` and rerun the screening script to test another Java version.

---

## 11. Common issues

### Poetry cannot find `pyproject.toml`

Run from the GitBug-Java repo:

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py
```

or use:

```bash
poetry -C <GITBUG_REPO> run python <SCRIPTS_DIR>/run_screened_bugs.py
```

### `ModuleNotFoundError: gitbugactions`

This usually means the script was run with system Python instead of Poetry.

Use:

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py
```

### EvoSuite generated no tests

Check:

```bash
cat <BUG_WORK_ROOT>/logs/evosuite_fixed.log
```

This may be an EvoSuite limitation, not necessarily a script bug.

### Tests fail on both fixed and buggy

This is usually classified as:

```text
UNSTABLE/UNHELPFUL
```

It often means the generated tests are brittle or overfitted.

### Running all bugs takes too long

Use:

```bash
--limit 10
--timeout 120
```

Example:

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py --limit 10 --timeout 120 --force
```

---

## 12. Quick command reference

Run first 5:

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py --limit 5 --force
```

Run all:

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py --force
```

Run with 2-minute timeout:

```bash
cd <GITBUG_REPO>
poetry run python <SCRIPTS_DIR>/run_screened_bugs.py --timeout 120 --force
```

Check results:

```bash
cat <BASE_WORK_ROOT>/results.csv
```

Count result types:

```bash
cut -d, -f6 <BASE_WORK_ROOT>/results.csv | sort | uniq -c
```
