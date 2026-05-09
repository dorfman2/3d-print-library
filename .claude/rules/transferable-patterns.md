# Transferable Analysis Patterns
**Purpose**: Mandatory standards for identifying and documenting reusable analysis patterns across multiple projects

## Overview

This rule defines how to identify and document search patterns, command-line techniques, and analysis methodologies that are effective across multiple CVE projects and should be preserved in global framework memory for reuse.

## Pattern Recognition

**Constraints:**
- You **MUST** identify patterns that demonstrate broad applicability when you discover effective search/grep/awk/sed/find commands that could work across multiple CVE projects
- You **MUST** recognize transferable methodologies when you develop analysis approaches that aren't specific to the current CVE's technology stack or vulnerability type
- You **MUST** distinguish between project-specific findings and generalizable techniques because only generalizable techniques belong in global memory
- You **MUST** evaluate pattern effectiveness based on whether the technique successfully identifies security-relevant code patterns, configuration issues, or architectural concerns

## Global Memory Documentation

**Constraints:**
- You **MUST** document transferable patterns in `tech-context.md` under appropriate sections because this is the designated location for cross-project technical knowledge
- You **MUST** include the complete command syntax with explanations when documenting command-line patterns because future analysis will need exact reproducible commands
- You **MUST** provide context about when and why to use each pattern since understanding the appropriate use case is critical for effective reuse
- You **MUST** organize patterns by category (search patterns, analysis techniques, tool usage, etc.) because organized knowledge is more accessible and useful

## Pattern Categories

### Search and Grep Patterns
**Constraints:**
- You **MUST** document regex patterns that identify common security anti-patterns across codebases
- You **MUST** include file type filters and directory exclusions that improve search efficiency
- You **MUST** provide examples of successful pattern matches with context about what they reveal

### Analysis Methodologies
**Constraints:**
- You **MUST** document systematic approaches to code review that work across different programming languages
- You **MUST** capture techniques for identifying data flow patterns and potential injection points
- You **MUST** record methods for analyzing configuration files and deployment artifacts

### Tool Usage Patterns
**Constraints:**
- You **MUST** document effective ctags usage patterns for navigating large codebases
- You **MUST** capture sed/awk/grep combinations that extract useful information from complex files
- You **MUST** record find command patterns that efficiently locate security-relevant files

## Documentation Format

**Constraints:**
- You **MUST** use the following format when adding patterns to tech-context.md:

```markdown
### [Pattern Category]

#### [Pattern Name]
- **Command**: `exact command syntax`
- **Purpose**: Brief description of what this finds/accomplishes
- **Use Case**: When to apply this pattern
- **Example**: Sample output or usage scenario
- **Notes**: Any important considerations or variations
```

## Pattern Validation

**Constraints:**
- You **MUST** theoretically walk through several scenarios with patterns on multiple file types or project structures before documenting them because untested patterns may not be truly transferable
- You **MUST** update patterns when you discover improvements or edge cases because maintaining accuracy is critical for framework effectiveness

## Memory Update Triggers

**Constraints:**
- You **MUST** update global memory when you discover a new command-line technique that successfully identifies security patterns across different codebases
- You **MUST** document analysis methodologies when you develop systematic approaches that aren't tied to specific vulnerability types or technologies
- You **MUST** record tool usage patterns when you find efficient ways to navigate, search, or analyze code that would benefit other CVE analysis projects
- You **MUST** update exclusion patterns when you identify file types or directories that consistently contain noise rather than security-relevant information

## Integration with Project Memory

**Constraints:**
- You **MUST** distinguish between project-specific applications of patterns and the patterns themselves because project memory should contain specific findings while global memory contains reusable techniques
- You **MUST** reference global patterns from project memory when applicable since this creates consistency and shows pattern effectiveness
- You **MUST NOT** duplicate pattern documentation between global and project memory because this creates maintenance overhead and potential inconsistencies

## Pattern Evolution

**Constraints:**
- You **MUST** refine patterns based on experience across multiple projects since patterns improve with broader application
- You **MUST** remove or deprecate patterns that prove ineffective or unreliable because maintaining ineffective patterns wastes analysis time
- You **MUST** version or date significant pattern updates so that the evolution of techniques can be tracked and understood
