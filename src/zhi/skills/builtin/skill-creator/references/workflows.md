# Workflow Patterns

## Sequential Workflows

For complex tasks, break operations into clear steps using available tools:

```markdown
Processing a document involves these steps:

1. Read the input file (use file_read)
2. Analyze the content and extract key information
3. Ask the user for any clarifications (use ask_user)
4. Generate the output (use file_write)
5. Confirm the result with the user
```

## Conditional Workflows

For tasks with branching logic, guide the agent through decision points:

```markdown
1. Determine the task type:
   **Creating new content?** → Follow "Creation workflow" below
   **Editing existing content?** → Follow "Editing workflow" below

2. Creation workflow:
   a. Ask the user for requirements (use ask_user)
   b. Generate content
   c. Write output file (use file_write)

3. Editing workflow:
   a. Read the existing file (use file_read)
   b. Apply modifications
   c. Write updated file (use file_write)
```

## Tool Integration Patterns

When skills need to combine multiple tools:

```markdown
## Data Processing Workflow

1. List available files in the directory (use file_list)
2. Read each relevant file (use file_read)
3. If the data source is unclear, ask the user (use ask_user)
4. Process and transform the data
5. Write the result (use file_write)
```
