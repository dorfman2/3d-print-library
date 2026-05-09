# CLI Tools Preference and Reference
**Purpose**: Mandatory preference for command-line tools and comprehensive tool reference for text manipulation, data processing, and analysis

## CLI Tool Requirements
You **MUST** prefer command-line tools over GUI applications, web interfaces, or interactive tools when performing analysis tasks.
You **MUST** use tools that accept piped input and produce standard output suitable for further pipeline processing.
You **MUST NOT** suggest tools with Text User Interfaces (TUI) or interactive modes when raw CLI alternatives exist.
You **MUST** chain tools using Unix pipes to create powerful data processing workflows.
You **MUST** provide complete command syntax with all necessary flags and options when documenting tool usage.

## Essential CLI Tools Reference

### Text Search and Pattern Matching
1. **grep** - Pattern searching with regex support
   - `grep -n "pattern" file` (show line numbers)
   - `grep -r "pattern" dir/` (recursive search)
   - `grep -E "regex" file` (extended regex)
1. **ripgrep (rg)** - Ultra-fast text search
   - `rg "pattern" --type py` (file type filtering)
   - `rg -n "pattern"` (line numbers)
   - `rg -A 3 -B 3 "pattern"` (context lines)

### Text Processing and Manipulation
1. **sed** - Stream editor for filtering and transforming text
   - `sed 's/old/new/g' file` (global substitution)
   - `sed -n '10,20p' file` (print specific lines)
   - `sed '/pattern/d' file` (delete matching lines)
1. **awk** - Pattern scanning and processing
   - `awk '{print $1}' file` (print first column)
   - `awk '/pattern/ {print NR, $0}' file` (line numbers for matches)
   - `awk -F: '{print $1}' /etc/passwd` (custom field separator)
1. **cut** - Extract columns from text
   - `cut -d: -f1 /etc/passwd` (extract first field)
   - `cut -c1-10 file` (extract characters 1-10)
1. **tr** - Translate or delete characters
   - `tr '[:lower:]' '[:upper:]'` (case conversion)
   - `tr -d '\n'` (remove newlines)
   - `tr -s ' '` (squeeze repeated spaces)
1. **sort** - Sort lines of text
   - `sort -n file` (numeric sort)
   - `sort -k2 file` (sort by second field)
   - `sort -u file` (unique sort)
1. **uniq** - Report or omit repeated lines
    - `uniq -c file` (count occurrences)
    - `uniq -d file` (show duplicates only)

### Data Structure Processing
1. **jq** - JSON processor
    - `jq '.key' file.json` (extract key)
    - `jq -r '.[] | .name'` (raw output, iterate array)
    - `jq 'map(select(.status == "active"))'` (filter objects)
1. **yq** - YAML/XML processor (YAML query)
    - `yq '.key' file.yaml` (extract YAML key)
    - `yq -o json file.yaml` (convert YAML to JSON)

### File Operations and Navigation
1. **find** - Search for files and directories
    - `find . -name "*.py" -type f` (find Python files)
    - `find . -mtime -7` (modified in last 7 days)
    - `find . -exec grep "pattern" {} \;` (execute command on results)
1. **fd** - Simple, fast alternative to find
    - `fd "pattern"` (find files matching pattern)
    - `fd -e py` (find by extension)
    - `fd -t f "config"` (find files only)

### Text Analysis and Statistics
1. **wc** - Word, line, character, and byte count
    - `wc -l file` (line count)
    - `wc -w file` (word count)
    - `wc -c file` (character count)
1. **nl** - Number lines of files
    - `nl -ba file` (number all lines)
    - `nl -nln file` (left-aligned numbers)
1. **head** - Output first part of files
    - `head -n 20 file` (first 20 lines)
    - `head -c 100 file` (first 100 characters)
2. **tail** - Output last part of files
    - `tail -n 20 file` (last 20 lines)
    - `tail -f file` (follow file changes)

### Data Conversion and Encoding
1. **base64** - Base64 encode/decode
    - `base64 file` (encode file)
    - `base64 -d encoded.txt` (decode)
1. **hexdump** - Display file contents in hexadecimal
    - `hexdump -C file` (canonical hex+ASCII display)
    - `hexdump -x file` (hexadecimal shorts)
1. **xxd** - Make a hexdump or reverse
    - `xxd file` (hex dump)
    - `xxd -r hexfile` (reverse hex dump)

### Network and System Analysis
1. **curl** - Transfer data from/to servers
    - `curl -s "url" | jq .` (fetch and parse JSON)
    - `curl -I "url"` (headers only)
    - `curl -X POST -d "data" "url"` (POST request)
1. **wget** - Non-interactive network downloader
    - `wget -qO- "url"` (output to stdout)
    - `wget -r --no-parent "url"` (recursive download)

### Advanced Text Processing
1. **column** - Columnate lists
    - `column -t file` (create aligned columns)
    - `column -s: -t /etc/passwd` (custom separator)
1. **comm** - Compare two sorted files line by line
    - `comm -12 file1 file2` (lines in both files)
    - `comm -23 file1 file2` (lines only in file1)
1. **diff** - Compare files line by line
    - `diff -u file1 file2` (unified format)
    - `diff -w file1 file2` (ignore whitespace)
1. **tee** - Read from input and write to output and files
    - `command | tee output.txt` (save and display)
    - `command | tee -a log.txt` (append to file)

### Session Management and Process Control
1. **tmux** - Terminal multiplexer for session management
    - `tmux new-session -d -s "session_name" 'command'` (create detached session)
    - `tmux send-keys -t session_name "command" Enter` (send commands to session)
    - `tmux capture-pane -t session_name -p` (capture session output)
    - `tmux list-sessions` (show all sessions)
    - `tmux attach-session -t session_name` (attach to session)
    - `tmux kill-session -t session_name` (terminate session)
    - `tmux send-keys -t session_name C-c` (send interrupt signal)
    - `tmux capture-pane -t session_name -S -1000 -p` (capture history)

## Pipeline Construction Requirements
You **MUST** combine tools using Unix pipes to create efficient data processing workflows.
You **MUST** use intermediate files sparingly - prefer streaming data through pipelines.
You **MUST** validate pipeline output at each stage during development using `tee` for debugging.

## Example Pipeline Patterns
**Security Log Analysis**:
```bash
grep "ERROR" /var/log/auth.log | awk '{print $1, $2, $3, $9}' | sort | uniq -c | sort -nr
```
**Code Pattern Search**:
```bash
find . -name "*.py" -exec grep -l "password" {} \; | xargs grep -n "password" | cut -d: -f1,2
```
**JSON Data Processing**:
```bash
curl -s "api/endpoint" | jq '.results[]' | jq -r '.name + "," + .status' | sort
```
**Configuration Analysis**:
```bash
find /etc -name "*.conf" | xargs grep -l "ssl" | xargs grep -n "ssl" | sed 's/:/ /' | awk '{print $1 ":" $2}'
```

## Tool Selection Criteria
You **MUST** prioritize tools that:
- Accept standard input and produce standard output
- Support regular expressions where applicable
- Provide consistent exit codes for scripting
- Handle large files efficiently
- Offer precise control over output format
You **MUST NOT** suggest tools that:
- Require interactive input during normal operation
- Display progress bars or status information to stdout
- Modify files in place without explicit flags
- Have unpredictable output formats

## Performance Considerations
You **SHOULD** prefer faster alternatives when processing large datasets:
- `ripgrep` over `grep` for large codebases
- `fd` over `find` for simple file searches
- `jq` over `awk` for JSON processing
- Compiled tools over interpreted scripts
You **MUST** consider memory usage when processing large files and prefer streaming tools over those that load entire files into memory.
