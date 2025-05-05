#!/usr/bin/env python3
import subprocess
import datetime
import argparse
from collections import defaultdict
import sys
import os

def check_git_repo():
    """Check if the current directory is a git repository."""
    try:
        # Try to get the git root directory to ensure we're in a valid repo
        result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], 
                      check=True, capture_output=True, text=True)
        # If successful, print the root directory to stderr for debugging
        if os.environ.get('GITHUB_ACTIONS'):
            print(f"Git repository found at: {result.stdout.strip()}", file=sys.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e.stderr}", file=sys.stderr)
        return False

def get_git_log():
    """Get git commit history with timestamps."""
    cmd = ['git', 'log', '--format=%at %H %an']
    
    # In GitHub Actions, let's print more verbose output for debugging
    if os.environ.get('GITHUB_ACTIONS'):
        print(f"Running git command: {' '.join(cmd)}", file=sys.stderr)
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    commits = []
    
    lines = result.stdout.strip().split('\n')
    if not lines or not lines[0]:
        print("Warning: No commit history found", file=sys.stderr)
        return []
        
    for line in lines:
        if not line.strip():
            continue
        parts = line.split(' ', 2)
        if len(parts) >= 2:
            timestamp, commit_hash = int(parts[0]), parts[1]
            author_name = parts[2] if len(parts) > 2 else ""
            commits.append({
                'timestamp': timestamp,
                'datetime': datetime.datetime.fromtimestamp(timestamp),
                'hash': commit_hash,
                'author': author_name
            })

    # Filter out bot commits
    filtered_commits = [c for c in commits if not c['author'].endswith('[bot]')]
    
    # Print some debug info in GitHub Actions
    if os.environ.get('GITHUB_ACTIONS'):
        print(f"Found {len(commits)} total commits, {len(filtered_commits)} after filtering", file=sys.stderr)
    
    return sorted(filtered_commits, key=lambda x: x['timestamp'])

def group_commits_into_sessions(commits, session_threshold_mins=30):
    """Group commits into coding sessions based on time proximity."""
    if not commits:
        return []
    
    sessions = []
    current_session = [commits[0]]
    
    for i in range(1, len(commits)):
        current_commit = commits[i]
        last_commit = current_session[-1]
        
        time_diff = current_commit['timestamp'] - last_commit['timestamp']
        minutes_diff = time_diff / 60
        
        if minutes_diff <= session_threshold_mins:
            current_session.append(current_commit)
        else:
            sessions.append(current_session)
            current_session = [current_commit]
    
    if current_session:
        sessions.append(current_session)
    
    return sessions

def calculate_session_durations(sessions, min_session_mins=5, max_session_hours=8):
    """Calculate the duration of each coding session with reasonable limits."""
    durations = []
    
    for session in sessions:
        if len(session) == 1:
            # For single-commit sessions, assume minimum duration
            duration_mins = min_session_mins * 2  # Double the minimum time to account for work before commit
        else:
            # For multi-commit sessions:
            # 1. Time between first and last commit
            # 2. Buffer for work before first commit
            # 3. Buffer for work after last commit
            start_time = session[0]['timestamp']
            end_time = session[-1]['timestamp']
            duration_mins = (end_time - start_time) / 60 + (min_session_mins * 2)
        
        # Cap excessively long sessions
        max_mins = max_session_hours * 60
        duration_mins = min(duration_mins, max_mins)
        
        durations.append({
            'start': session[0]['datetime'],
            'end': session[-1]['datetime'],
            'commits': len(session),
            'duration_mins': duration_mins,
            'authors': set(commit['author'] for commit in session)
        })
    
    return durations

def format_time(minutes):
    """Format minutes as hours and minutes."""
    hours, mins = divmod(int(minutes), 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    else:
        return f"{mins}m"

def main():
    parser = argparse.ArgumentParser(description='Generate git time statistics for README.')
    parser.add_argument('--session-gap', type=int, default=30,
                        help='Time gap in minutes to consider between sessions (default: 30)')
    parser.add_argument('--min-session', type=int, default=5,
                        help='Minimum session duration in minutes (default: 5)')
    parser.add_argument('--max-session', type=int, default=8,
                        help='Maximum session duration in hours (default: 8)')
    parser.add_argument('--output-file', help='Optional: File to write markdown stats to.')
    parser.add_argument('--debug', action='store_true', help='Print debug information')

    args = parser.parse_args()
    
    # Print parameters in debug mode or in GitHub Actions
    if args.debug or os.environ.get('GITHUB_ACTIONS'):
        print(f"Running with parameters:", file=sys.stderr)
        print(f"  Session gap: {args.session_gap} minutes", file=sys.stderr)
        print(f"  Min session: {args.min_session} minutes", file=sys.stderr)
        print(f"  Max session: {args.max_session} hours", file=sys.stderr)
        print(f"  Current directory: {os.getcwd()}", file=sys.stderr)
    
    if not check_git_repo():
        print("Error: Not a git repository", file=sys.stderr)
        # In GitHub Actions, output something to avoid breaking the workflow
        if os.environ.get('GITHUB_ACTIONS'):
            print("- Error: Not a git repository\n- Please check the action setup")
        sys.exit(1)
    
    try:
        commits = get_git_log()
        
        if not commits:
            stats_output = "- No commit history found to generate statistics.\n- Please ensure the repository has commits and history is fetched."
        else:
            sessions = group_commits_into_sessions(commits, args.session_gap)
            durations = calculate_session_durations(sessions, args.min_session, args.max_session)
            
            # Calculate statistics
            total_mins = sum(d['duration_mins'] for d in durations)
            total_commits = sum(d['commits'] for d in durations)
            
            # Prepare author stats
            author_times = defaultdict(float)
            for session in durations:
                for author in session['authors']:
                    author_times[author] += session['duration_mins'] / len(session['authors'])
            
            # Build the Markdown output string
            stats_lines = []
            stats_lines.append(f"- Total time spent: {format_time(total_mins)} ({total_mins:.1f} minutes)")
            stats_lines.append(f"- Number of sessions: {len(durations)}")
            stats_lines.append(f"- Total commits: {total_commits}")
            
            if len(durations) > 0:
                avg_session = total_mins / len(durations)
                stats_lines.append(f"- Average session length: {format_time(avg_session)}")
            
            if total_commits > 0:
                avg_time_per_commit = total_mins / total_commits
                stats_lines.append(f"- Average time per commit: {format_time(avg_time_per_commit)}")
            
            # Add author breakdown if multiple authors
            if len(author_times) > 1:
                stats_lines.append(f"\n#### Time by Author:")
                for author, mins in sorted(author_times.items(), key=lambda x: x[1], reverse=True):
                    percentage = (mins / total_mins) * 100 if total_mins else 0
                    stats_lines.append(f"- {author}: {format_time(mins)} ({percentage:.1f}%)")
            
            stats_output = "\n".join(line for line in stats_lines if line is not None)
        
        # Output the result
        if args.output_file:
            try:
                with open(args.output_file, 'w') as f:
                    f.write(stats_output)
                print(f"Stats written to {args.output_file}", file=sys.stderr)
            except IOError as e:
                print(f"Error writing to output file {args.output_file}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # Print directly to stdout without adding an extra newline
            sys.stdout.write(stats_output)

    except Exception as e:
        print(f"Error generating stats: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        # In GitHub Actions, output something to avoid breaking the workflow completely
        if os.environ.get('GITHUB_ACTIONS'):
            print(f"- Error: Failed to generate git stats\n- Reason: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 