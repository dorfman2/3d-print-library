# Agent Script Format
**Purpose**: Mandatory standards for creating reusable workflow scripts using `.script.md` files

Agent scripts are reusable workflows that automate complex processes using `.script.md` files.

## File Requirements
You **MUST** use `.script.md` file extension.
You **SHOULD** use kebab-case naming (e.g., `idea-honing.script.md`).

## Script Structure
### Title and Overview
```markdown
# [Script Name]

## Overview
[Concise description of what the script does and when to use it]
```

### Parameters
```markdown
## Parameters
- **required_param**: Description of required parameter
- **optional_param**: Description of optional parameter
- **optional_with_default**: Description of optional parameter, default: "value"
```

**Parameter naming:**
- You **MUST** use snake_case
- You **MUST** be descriptive
- You **MUST** list required parameters first

### Steps
```markdown
## Steps
### 1. Verify Dependencies
Check for required tools and warn the user if any are missing.
**Constraints:**
- You **MUST** verify the following tools are available in your context:
  - tool_name_one
  - tool_name_two
- You **MUST ONLY** check for tool existence and **MUST NOT** attempt to run the tools
- You **MUST** inform the user about any missing tools
- You **MUST** ask if the user wants to proceed anyway despite missing tools
- You **MUST** respect the user's decision to proceed or abort

### 2. [Step Name]
[Natural language description of what happens in this step]
**Constraints:**
- You **MUST** [specific requirement using RFC2119 keyword]
- You **SHOULD** [recommended behavior using RFC2119 keyword]
- You **MAY** [optional behavior using RFC2119 keyword]

### Examples (Optional)
### Example Input/Output
```markdown
[Example input]
```

## RFC2119 Keywords
You **MUST ALWAYS** use RFC2119 keywords in instructions
**Common contexts:**
- Technical limitations
- Security risks
- Data integrity
- User experience
- Compatibility issues

## Tool Dependency Verification
You **MUST** include dependency verification as first step for scripts requiring tools:
- Check tool existence in context (don't run them)
- Warn about missing tools
- Allow user to proceed anyway
- Respect user's decision

## Interactive Scripts
For user interaction:
- You **MUST** indicate when interaction is expected
- You **MUST** specify how to handle responses
- You **MUST** define where to save interaction records

## Best Practices
1. You **MUST** keep steps focused and concise
2. You **MUST** use clear, specific constraints
3. You **SHOULD** include examples for complex outputs
4. You **SHOULD** minimize complex conditional logic
5. You **MUST** specify file paths for artifacts
6. You **MUST** use "You" instead of "The model" in constraints
7. You **SHOULD** test scripts before sharing
