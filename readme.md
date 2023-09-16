### About

`count_lines.py` counts code lines, non-blank lines, statesment, comment lines of selected *.py files recursively under a directory. This repo includes script `count_lines.py`, `count_lines.log` as a demo output file, git submodule python `requests` as a demo project to analyze, and this readme file. Try this out by cloning this repo with `--recurse-submodules` argument, and run:

```
python count_lines.py
```

### How to use
#### Step 0.

Make sure you have Python >= 3.6.

#### Step 1.
Edit the configurations in `count_lines.py: main()`.

* `root_dir` is the project directory including all `*.py` files (including symbolic links) to analyze.
* `output_file` is the output file path.
* `exclude_file_patterns` is a list of regular expressions to exclude certain file paths. The default execludes tests, examples, docs, benchmarks, build files. If there is a path `xxxlib` that you want to exclude, append `".*/xxxlib/.*"` to it.
* `exclude_name_patters` is a list of regular expressions to exclude certain function or class names. The default excludes test functions or classes.

#### Step 2.
Run: `python count_lines.py`

#### Step 3.
Check the result output file.

The first section is a list of included/excluded files, and which RegEx is effective if excluded.

The second section is a list of statistics on each included files, including counts of all lines, non-blank lines, statesments, comment lines.

The last line is the statistics gathered from all included files.

### Explanation

* Lines: lines seperated by "\n" or "\n\r".

* Non-blank lines: lines that exclude blank lines. Blank lines are made of "\t" or space.

* Statements: number of Python statements. Refer the official doc of Python `ast` module. A statement occupying multiple lines are counted as one. If a statement is an expression that does not contain `yield`, `await` or function call, it is not counted. Examples:

```
a = [
	1,
	2,
	3,
]  # counted as 1
1 < 4  # not counted
"abcde"  # not counted
foo()  # counted as 1
foo() < 1 # counted as 1
```

* Commented lines: all lines that contains inline comments and block comments.

### Exceptions

* If the file is corrupted or the code has syntax errors, the file will be excluded.
