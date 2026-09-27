# Guided Contribution Mode

AtlasCode features a **Guided Contribution Mode** that acts as an interactive mentor, helping you contribute to any open source repository without requiring you to know the codebase inside out.

Instead of trying to automatically write the code (which often fails on complex issues), AtlasCode analyzes the problem and provides you with a step-by-step checklist, telling you exactly where to look, what files to modify, and where to place your tests.

## How it works

1. **Select an Issue**: Go to the "Contribute" tab for an analyzed project and select an issue.
2. **Review the Plan**: AtlasCode generates a contribution plan. It analyzes the issue and suggests the relevant files to edit and the command to run tests.
3. **Approve & Begin**: Click "Create Branch & Begin". This creates a new Git branch and switches the UI into Guided Mode.
4. **Implement**:
   - Open your favorite IDE in the repository directory (the path is provided in the UI).
   - Follow the interactive checklist.
   - Use the "Refresh" button in AtlasCode to see the files you've changed.
5. **Test**: Click "Run Tests". AtlasCode will run the project's test suite and show you the results directly in the UI. If tests fail, you can fix them in your IDE and run them again.
6. **Commit & PR**: Once tests pass, you can select which modified files to include, write a commit message, and commit the changes. AtlasCode provides a generated Pull Request draft and instructions to push the branch to GitHub.

## Manual Execution vs Automatic
Initially, AtlasCode attempted to automatically implement the plan and fix tests. This is no longer the case. You have full control over the implementation and the test execution, making it a much better learning tool and a safer way to contribute.
