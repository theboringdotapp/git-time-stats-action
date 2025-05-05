# Git Time Stats GitHub Action

A GitHub Action that calculates and reports time spent on a repository based on git commit history. This action can automatically update your README with statistics about how much time has been spent working on the project.

## Features

- Calculates total time spent based on git commit history
- Groups commits into coding sessions based on time proximity
- Filters out bot commits (e.g., from GitHub Actions)
- Can automatically update your README with the latest stats
- Customizable session parameters
- Option to commit changes directly back to the repository

## Usage

### Basic Usage

Add the following to your GitHub workflow:

```yaml
- name: Calculate Git Time Stats
  uses: theboringdotapp/git-time-stats-action@1.1
  with:
    readme-path: 'README.md'  # Default is README.md
    commit-changes: 'true'    # Auto-commit the changes back to the repository
```

Make sure your README.md contains these markers where the stats should be inserted:

```md
<!-- START_GIT_TIME_STATS -->
<!-- END_GIT_TIME_STATS -->
```

### Complete Example

```yaml
name: Update README Stats

on:
  push:
    branches:
      - main

jobs:
  update-stats:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Needed to push the updated README

    steps:
      - name: Checkout Full History
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need full history for accurate stats

      - name: Calculate Git Time Stats
        id: git-time-stats
        uses: theboringdotapp/git-time-stats-action@v1
        with:
          session-gap: 30      # Minutes gap between sessions
          min-session: 5       # Minimum session duration in minutes
          max-session: 8       # Maximum session duration in hours
          readme-path: 'README.md'
          commit-changes: 'true'
          commit-message: 'docs: Update time stats [skip ci]'
```

## Inputs

| Input           | Description                                        | Required | Default                                |
|-----------------|----------------------------------------------------|----------|----------------------------------------|
| session-gap     | Time gap in minutes between sessions               | No       | 30                                     |
| min-session     | Minimum session duration in minutes                | No       | 5                                      |
| max-session     | Maximum session duration in hours                  | No       | 8                                      |
| readme-path     | Path to the README file to update                  | No       | README.md                              |
| update-readme   | Whether to update the README with the stats        | No       | true                                   |
| commit-changes  | Whether to commit changes back to the repository   | No       | false                                  |
| commit-message  | Commit message to use when committing changes      | No       | docs: Update time stats in README [skip ci] |

## Outputs

| Output  | Description                                       |
|---------|---------------------------------------------------|
| stats   | Generated statistics in markdown format           |
| changed | Whether the README was updated (true/false)       |

## Example Stats Output

```
- Total time spent: 42h 30m (2550.0 minutes)
- Number of sessions: 15
- Total commits: 87
- Average session length: 2h 50m
- Average time per commit: 29m

#### Time by Author:
- alice: 25h 15m (59.4%)
- bob: 17h 15m (40.6%)
```

## License

MIT 