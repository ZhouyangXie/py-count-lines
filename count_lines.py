
import os
import io
import re
import ast
import token
import tokenize
import logging
import pathlib
from typing import List


def tranverse_ast_stmt(node, callback):
    """
        tranverse a Python AST into statements only
        (stop at expr or callback return False)
    """
    continue_tranversal = callback(node)
    if not continue_tranversal:
        return

    if isinstance(node, (
            ast.Module, ast.With, ast.AsyncWith, ast.ExceptHandler,
            ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef
            )):
        # visit body
        for stmt in node.body:
            tranverse_ast_stmt(stmt, callback)

    elif isinstance(node, (
        ast.Return, ast.Delete, ast.Assign, ast.AugAssign,
        ast.Raise, ast.Assert, ast.Import, ast.ImportFrom,
        ast.Global, ast.Nonlocal, ast.Pass, ast.Break, ast.Continue,
        ast.Expr
    )):
        # end of tranverse
        pass

    elif isinstance(node, (
        ast.For, ast.AsyncFor, ast.While, ast.If,
    )):
        # visit body and orelse
        for stmt in node.body:
            tranverse_ast_stmt(stmt, callback)
        for stmt in node.orelse:
            tranverse_ast_stmt(stmt, callback)

    elif isinstance(node, (ast.Try, )):
        # visit body, excepthandler, orelse, finalbody
        for stmt in node.body:
            tranverse_ast_stmt(stmt, callback)
        for handler in node.handlers:
            tranverse_ast_stmt(handler, callback)
        for stmt in node.orelse:
            tranverse_ast_stmt(stmt, callback)
        for stmt in node.finalbody:
            tranverse_ast_stmt(stmt, callback)

    # TODO: Match and TryStar statements are newly supported
    # elif isinstance(node, (ast.Match, ast.TryStar)):
        # ...

    else:
        assert isinstance(node, ast.stmt)


def count_statements(source_code: str, exclude_name_patterns=None):
    root_node = ast.parse(source_code)
    count = 0
    if exclude_name_patterns is None:
        exclude_name_patterns = []

    def _node_effective_count(node):
        nonlocal count
        if isinstance(node, ast.Module):
            count += 0
        elif isinstance(node, ast.Expr):
            v = node.value
            if isinstance(v, (
                ast.Await, ast.Yield, ast.YieldFrom, ast.Call
            )):
                count += 1
        else:
            count += 1

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and\
                any([p.match(node.name) is not None for p in exclude_name_patterns]):
            return False
        else:
            return True

    tranverse_ast_stmt(root_node, _node_effective_count)
    return count


def count_lines(source_code: str):
    """
    Returns:
        Tuple[int, int, int]: #line, #nonblank_line, #commented_line
    """
    num_lines = len(io.StringIO(source_code).readlines())
    tokens = tokenize.generate_tokens(io.StringIO(source_code).readline)
    tokens = list(tokens)

    nonblank_lines = set()  # lines consist of \n \r space \t
    inline_comment_lines = set()  # lines with inline or block comments
    block_comment_lines = set()  # block comment lines

    for t in tokens:
        if t.type in (
            token.ENCODING, token.ENDMARKER, token.NEWLINE,
            token.INDENT, token.DEDENT, token.NL,
                ):
            continue
        elif t.type in (token.COMMENT, token.TYPE_COMMENT):
            inline_comment_lines.update(list(range(t.start[0], t.end[0] + 1)))
            nonblank_lines.update(list(range(t.start[0], t.end[0] + 1)))
        elif t.type in (token.STRING, ):
            # possibly block comment
            # skip for now
            continue
        else:
            nonblank_lines.update(list(range(t.start[0], t.end[0] + 1)))

    # add block lines(as token type STRING, )
    for t in tokens:
        if t.type == token.STRING:
            line = t.line.replace("\n", "").replace(" ", "").replace("\t", "").replace("\r", "")
            if (line.startswith("'''") and line.endswith("'''")) or\
                    (line.startswith('"""') and line.endswith('"""')):
                for lineno in range(t.start[0], t.end[0] + 1):
                    if lineno not in nonblank_lines:
                        block_comment_lines.add(lineno)
                        nonblank_lines.add(lineno)

    return num_lines, len(nonblank_lines), len(inline_comment_lines.union(block_comment_lines))


def analyze_file(path, exclude_name_patterns=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        num_statement = count_statements(source_code, exclude_name_patterns)
        num_line, num_nonblank_line, num_commented_line = count_lines(source_code)
    except (FileNotFoundError, OSError):
        logging.info(f'Failed to open: {path}')
        return None
    except (SyntaxError, tokenize.TokenError):
        logging.info(f'File has syntax error: {path}')
        return None

    return num_line, num_nonblank_line, num_statement, num_commented_line


def find_all_py_files(root_dir, exclude_file_patterns):
    if not os.path.exists(root_dir):
        logging.info(f'Root directory {root_dir} does not exist')
        return

    logging.info(f'Scanning .py files under {root_dir}')
    if exclude_file_patterns is None:
        exclude_file_patterns = []

    for path in pathlib.Path(root_dir).glob('**/*.py'):
        if not path.is_file():
            continue
        fn = str(path)
        is_excluded = False
        for p in exclude_file_patterns:
            if p.match(fn) is not None:
                logging.info(f'Exclude {fn} by pattern {p}')
                is_excluded = True
                break
        if is_excluded:
            continue

        logging.info(f'Include {fn}')
        yield fn


def main(
        root_dir: str = ".",
        output_file: str = "count_lines.log",
        exclude_file_patterns: List[str] = None,
        exclude_name_patterns: List[str] = None,
        ):
    logging.basicConfig(
        filename=output_file,
        filemode='w',
        format='%(asctime)s | %(message)s',
        level=logging.INFO
    )
    exclude_file_patterns = [re.compile(p) for p in exclude_file_patterns] if exclude_file_patterns else []
    exclude_name_patterns = [re.compile(p) for p in exclude_name_patterns] if exclude_name_patterns else []
    filenames = list(find_all_py_files(root_dir, exclude_file_patterns))

    num_file, total_num_line, total_num_nonblank_line, total_num_statement, total_num_commented_line = 0, 0, 0, 0, 0
    for fn in filenames:
        result = analyze_file(fn, exclude_name_patterns)
        if result is None:
            continue
        num_file += 1
        num_line, num_nonblank_line, num_statement, num_commented_line = result
        logging.info(
            f"Result of {fn}: #line={num_line} #nonblank-line={num_nonblank_line}"
            f" #statement={num_statement} #commented-line={num_commented_line}"
        )
        total_num_line += num_line
        total_num_nonblank_line += num_nonblank_line
        total_num_statement += num_statement
        total_num_commented_line += num_commented_line

    logging.info(
        f"Overall result: #file={num_file} #line={total_num_line} #nonblank-line={total_num_nonblank_line}"
        f" #statement={total_num_statement} #commented-line={total_num_commented_line}"
    )


if __name__ == "__main__":
    # root directory to scan for *.py files
    root_dir = "."
    # output log file
    output_file = "count_lines.log"
    # exclude file path that match one of the below regex
    exclude_file_patterns = [
        ".*[tT][eE][sS][tT].*",  # exclude test files
        ".*example.*",  # exclude examples
        ".*benchmark.*", ".*bench.*",  # exclude benckmarks
        ".*setup.py",  # exclude setup.py
        ".*/build/.*", ".*/docs?/.*", ".*/examples?/.*"  # exclude build/doc(s)/example(s) directories
    ]
    # exclude file path that match one of the below regex
    exclude_name_patterns = [
        ".*[tT][eE][sS][tT].*",  # exclude test Module/Class/Func
    ]
    main(root_dir, output_file, exclude_file_patterns, exclude_name_patterns)
