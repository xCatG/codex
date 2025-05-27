# Synchronization Strategy: `codex-py` with `codex-cli`

This document outlines the strategy for maintaining `codex-py` as a Python port of the original TypeScript `codex-cli`, ensuring it tracks the evolution of `codex-cli` within this monorepo.

## 1. Goal

The primary goal is to ensure `codex-py` remains a functional and up-to-date Python equivalent of `codex-cli`. This involves porting new features, bug fixes, and relevant architectural changes from `codex-cli` to `codex-py` in a timely manner.

## 2. Monitoring `codex-cli` Changes

To stay informed about modifications in `codex-cli`, the following methods will be employed:

*   **Git Log:** Regularly review changes specific to the `codex-cli/` directory using commands like:
    ```bash
    git log -p -- codex-cli/
    ```
    This helps identify commits that introduce changes requiring porting.

*   **Pull Requests (PRs):** Monitor and review PRs that affect files within the `codex-cli/` directory. This provides context and discussion around the changes.

*   **Periodic Checks:** Perform scheduled checks of the `codex-cli` codebase, especially when new features or versions of `codex-cli` are announced or released.

## 3. Porting Guidelines

When porting changes from `codex-cli` to `codex-py`, the following guidelines should be followed:

*   **Module and Code Structure:** Strive to maintain an analogous Python module and code structure that mirrors the organization of `codex-cli`. For example, if `codex-cli` has `src/utils/someHelper.ts`, `codex-py` should aim for `src/utils/some_helper.py`.

*   **Feature Parity:** The primary aim is to achieve feature parity. This means if `codex-cli` introduces a new command, option, or behavior, `codex-py` should implement the equivalent.

*   **Idiomatic Python:** While maintaining structural similarity and feature parity, the implementation in `codex-py` should be idiomatic Python. This includes using Python-specific language features, conventions (e.g., PEP 8), and standard library utilities where appropriate.

*   **Dependencies:** When `codex-cli` adds new dependencies (e.g., via `package.json`), identify and add equivalent or suitable alternative Python packages to `codex-py/requirements.txt`.

*   **Commit Messages:** Commit messages in `codex-py` related to porting efforts should clearly reference the original `codex-cli` commit(s) or PR(s) that prompted the changes. This aids in traceability. For example:
    ```
    feat: Port feature X from codex-cli

    This commit ports the functionality related to feature X,
    originally introduced in codex-cli commit `[hash]` / PR `[#PR_number]`.
    ```

## 4. Handling Different Paradigms/Libraries

It's acknowledged that direct one-to-one code translation is not always feasible or desirable due to differences in programming paradigms, standard libraries, and common third-party libraries between TypeScript/Node.js and Python.

*   **TUI Libraries:** `codex-cli` uses `ink` (React-based) for its TUI, while `codex-py` uses `Textual`. The focus should be on porting the TUI's functionality, user experience, and information display, rather than a literal component-by-component translation.
*   **Async/Await:** Both environments support asynchronous programming, but patterns (e.g., event loops, promise handling vs. asyncio) might differ. The core logic of async operations should be ported.
*   **Validation Libraries:** `codex-cli` might use libraries like `zod` for validation, while `codex-py` uses `Pydantic`. The validation rules and error handling behavior should be ported.
*   **Configuration:** `codex-cli` might use JSON or other formats; `codex-py` supports JSON and YAML. The structure and intent of configuration should be preserved.

The key is to understand the *intent* and *functionality* of the `codex-cli` code and reimplement it effectively in Python.

## 5. Testing

Maintaining robust tests is crucial for ensuring the porting process is successful and that `codex-py` functions as expected.

*   **Ported Functionality:** Any feature or bug fix ported from `codex-cli` must have corresponding unit tests in `codex-py`.
*   **Equivalent Tests:** If `codex-cli` adds new tests for a particular piece of logic or functionality that is also present in `codex-py`, consider creating an equivalent test case in `codex-py`'s test suite.

## 6. Tools/Scripts (Future Considerations)

To aid in the synchronization process in the future, we might consider developing or utilizing tools such as:

*   **Structure Diffing:** Scripts that can compare the directory and file structures of `codex-cli/src` and `codex-py/src` to highlight discrepancies.
*   **Dependency Tracking:** Tools to list dependencies from `codex-cli/package.json` and help identify Python equivalents or track which ones have been addressed in `codex-py/requirements.txt`.
*   **Automated Checks:** Potentially, automated checks (e.g., via GitHub Actions) that trigger notifications if significant changes are made to `codex-cli` without corresponding activity in `codex-py` after a certain period.

These are future considerations and would be implemented based on need and available resources.Okay, I have created the `SYNC_STRATEGY.md` file in the `codex-py` directory with the specified content.
The document includes sections for:
1.  Goal
2.  Monitoring `codex-cli` Changes
3.  Porting Guidelines
4.  Handling Different Paradigms/Libraries
5.  Testing
6.  Tools/Scripts (Future Considerations)

All the requested information has been included in the markdown file.
