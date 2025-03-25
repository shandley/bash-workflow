# ASCII Workflow Visualizer

A Python tool for generating ASCII art visualizations of workflows and pipelines from YAML or JSON definitions.

## Features

- Visualize any workflow or pipeline as ASCII art
- Support for different node types with customizable box styles
- Support for different connection types
- Configure via YAML or JSON files
- Programmatic usage via Python API

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ascii-workflow.git
cd ascii-workflow

# Make the script executable
chmod +x ascii_workflow.py
```

## Usage

### Command Line

```bash
# Using YAML input
./ascii_workflow.py --yaml example.yaml

# Using JSON input
./ascii_workflow.py --json example.json

# Output to a file
./ascii_workflow.py --yaml example.yaml --output workflow.txt
```

### Python API

```python
from ascii_workflow import Workflow, Node, Connection

# Create a workflow
workflow = Workflow("My Workflow")

# Add nodes
workflow.add_node(Node("start", "Start", "start", icon="🚀"))
workflow.add_node(Node("process", "Process Data", "process", icon="🔄"))
workflow.add_node(Node("end", "End", "result", icon="✅"))

# Add connections
workflow.add_connection(Connection("start", "process"))
workflow.add_connection(Connection("process", "end"))

# Render and print
print(workflow.render())
```

## Input Format

### YAML Example

```yaml
title: "My Workflow"
nodes:
  - id: "start"
    label: "Start"
    type: "start"
    icon: "🚀"
    description: "Begin the workflow process"
  
  - id: "process1"
    label: "Process Data"
    type: "process"
    icon: "🔄"
    description: "Process input data"
    
connections:
  - source: "start"
    target: "process1"
    type: "normal"
```

### JSON Example

```json
{
  "title": "My Workflow",
  "nodes": [
    {
      "id": "start",
      "label": "Start",
      "type": "start",
      "icon": "🚀",
      "description": "Begin the workflow process"
    },
    {
      "id": "process1",
      "label": "Process Data",
      "type": "process",
      "icon": "🔄",
      "description": "Process input data"
    }
  ],
  "connections": [
    {
      "source": "start",
      "target": "process1",
      "type": "normal"
    }
  ]
}
```

## Node Types

- `start`: Starting node
- `process`: Generic process node
- `tool`: Tool/execution node
- `decision`: Decision node
- `result`: Result/output node
- `special`: Special node (e.g., environment activation)

## Connection Types

- `normal`: Standard flow
- `thick`: Emphasized flow
- `double`: Double-line flow
- `dashed`: Dashed line flow

## License

MIT