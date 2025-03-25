#!/usr/bin/env python3
"""
ASCII Workflow Visualizer

A tool for generating ASCII art visualizations of workflows and pipelines from YAML or JSON definitions.
"""

import argparse
import json
import sys
import yaml
from typing import Dict, List, Optional, Any, Tuple

# Default box styles
BOX_STYLES = {
    "start": {
        "top_left": "┌", "top_right": "┐", "bottom_left": "└", "bottom_right": "┘",
        "horizontal": "─", "vertical": "│", "padding": 1
    },
    "process": {
        "top_left": "┌", "top_right": "┐", "bottom_left": "└", "bottom_right": "┘", 
        "horizontal": "─", "vertical": "│", "padding": 1
    },
    "tool": {
        "top_left": "╔", "top_right": "╗", "bottom_left": "╚", "bottom_right": "╝",
        "horizontal": "═", "vertical": "║", "padding": 1
    },
    "decision": {
        "top_left": "╭", "top_right": "╮", "bottom_left": "╰", "bottom_right": "╯",
        "horizontal": "─", "vertical": "│", "padding": 1
    },
    "result": {
        "top_left": "┏", "top_right": "┓", "bottom_left": "┗", "bottom_right": "┛",
        "horizontal": "━", "vertical": "┃", "padding": 1
    },
    "special": {
        "top_left": "╒", "top_right": "╕", "bottom_left": "╘", "bottom_right": "╛",
        "horizontal": "═", "vertical": "│", "padding": 1
    }
}

# Connection characters
CONNECTIONS = {
    "normal": {"vertical": "│", "horizontal": "─", "down_right": "┌", "down_left": "┐", "up_right": "└", "up_left": "┘", "cross": "┼"},
    "thick": {"vertical": "┃", "horizontal": "━", "down_right": "┏", "down_left": "┓", "up_right": "┗", "up_left": "┛", "cross": "╋"},
    "double": {"vertical": "║", "horizontal": "═", "down_right": "╔", "down_left": "╗", "up_right": "╚", "up_left": "╝", "cross": "╬"},
    "dashed": {"vertical": "┊", "horizontal": "┄", "down_right": "┌", "down_left": "┐", "up_right": "└", "up_left": "┘", "cross": "┼"},
}

# Arrow styles
ARROWS = {
    "normal": "→",
    "bold": "⟶",
    "double": "⇒",
    "success": "✓→",
    "failure": "✗→",
    "conditional": "?→"
}


class Node:
    """Represents a single node in the workflow."""
    
    def __init__(self, node_id: str, label: str, node_type: str = "process", 
                 icon: Optional[str] = None, description: Optional[str] = None, 
                 style: Optional[Dict] = None):
        self.id = node_id
        self.label = label
        self.type = node_type
        self.icon = icon
        self.description = description
        # Use default style for the node type or custom style if provided
        self.style = style or BOX_STYLES.get(node_type, BOX_STYLES["process"])
        # Calculated during layout phase
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        
    def get_display_text(self) -> List[str]:
        """Generate the text to display inside the node box."""
        lines = []
        
        # Add icon if available
        if self.icon:
            display_text = f"{self.icon} {self.label}"
        else:
            display_text = self.label
            
        lines.append(display_text)
        
        # Add description if available
        if self.description:
            # Wrap description text to a reasonable length
            max_line_length = max(len(display_text), 30)
            wrapped_desc = []
            
            words = self.description.split()
            current_line = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + (1 if current_length > 0 else 0) <= max_line_length:
                    if current_length > 0:
                        current_line.append(word)
                        current_length += len(word) + 1  # +1 for the space
                    else:
                        current_line.append(word)
                        current_length += len(word)
                else:
                    wrapped_desc.append(" ".join(current_line))
                    current_line = [word]
                    current_length = len(word)
            
            if current_line:
                wrapped_desc.append(" ".join(current_line))
            
            for line in wrapped_desc:
                lines.append(line)
        
        return lines
    
    def calculate_dimensions(self) -> Tuple[int, int]:
        """Calculate the width and height of the node box."""
        text_lines = self.get_display_text()
        padding = self.style["padding"]
        
        # Width is the length of the longest line plus padding on both sides
        self.width = max(len(line) for line in text_lines) + (padding * 2)
        
        # Height is the number of lines plus padding on top and bottom plus borders
        self.height = len(text_lines) + (padding * 2)
        
        return self.width, self.height


class Connection:
    """Represents a connection between two nodes."""
    
    def __init__(self, source: str, target: str, conn_type: str = "normal", label: Optional[str] = None):
        self.source = source
        self.target = target
        self.type = conn_type
        self.label = label
        # Style based on connection type
        self.style = CONNECTIONS.get(conn_type, CONNECTIONS["normal"])
        self.arrow = ARROWS.get(conn_type, ARROWS["normal"])
        # Path calculated during layout phase
        self.path = []


class Workflow:
    """Manages the workflow definition, layout, and rendering."""
    
    def __init__(self, title: str = "Workflow"):
        self.title = title
        self.nodes: Dict[str, Node] = {}
        self.connections: List[Connection] = []
        self.canvas: List[List[str]] = []
        self.canvas_width = 0
        self.canvas_height = 0
        
    def add_node(self, node: Node) -> None:
        """Add a node to the workflow."""
        self.nodes[node.id] = node
        
    def add_connection(self, connection: Connection) -> None:
        """Add a connection to the workflow."""
        self.connections.append(connection)
        
    def calculate_layout(self) -> None:
        """Calculate the positions of all nodes and connections."""
        if not self.nodes:
            return
            
        # Simple linear layout for now
        current_y = 2  # Start with some margin at the top
        nodes_placement = []
        
        # First pass: determine node dimensions
        for node_id, node in self.nodes.items():
            node.calculate_dimensions()
            
        # Find topological ordering
        ordered_nodes = self._topological_sort()
        
        # Second pass: assign positions
        max_width = max(node.width for node in self.nodes.values()) + 10  # Add some spacing
        
        # Group nodes by "level" based on connections
        node_levels = self._assign_levels(ordered_nodes)
        
        # Assign vertical positions by level
        level_heights = {}
        current_y = 2
        
        for level, level_nodes in sorted(node_levels.items()):
            max_height = max(self.nodes[node_id].height for node_id in level_nodes)
            level_heights[level] = max_height + 2  # Add spacing
            
            # Place nodes within this level
            available_width = max(80, max_width * len(level_nodes))
            spacing = available_width // (len(level_nodes) + 1)
            
            for i, node_id in enumerate(level_nodes):
                node = self.nodes[node_id]
                node.x = (i + 1) * spacing - (node.width // 2)
                node.y = current_y
                
            current_y += level_heights[level]
        
        # Calculate canvas dimensions
        self.canvas_width = max(
            max(node.x + node.width for node in self.nodes.values()) + 5,
            len(self.title) + 4
        )
        self.canvas_height = current_y + 2
        
        # Route connections
        self._route_connections()
        
    def _topological_sort(self) -> List[str]:
        """Sort nodes in topological order."""
        # Build adjacency list
        adjacency = {node_id: [] for node_id in self.nodes}
        
        for conn in self.connections:
            if conn.source in adjacency and conn.target in adjacency:
                adjacency[conn.source].append(conn.target)
        
        # DFS-based topological sort
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(node_id):
            if node_id in temp_visited:
                # Cycle detected, skip
                return
            if node_id in visited:
                return
                
            temp_visited.add(node_id)
            
            for neighbor in adjacency[node_id]:
                visit(neighbor)
                
            temp_visited.remove(node_id)
            visited.add(node_id)
            result.append(node_id)
        
        # Visit all nodes
        for node_id in self.nodes:
            if node_id not in visited:
                visit(node_id)
                
        # Reverse for correct order
        return list(reversed(result))
    
    def _assign_levels(self, ordered_nodes: List[str]) -> Dict[int, List[str]]:
        """Assign nodes to levels based on dependencies."""
        node_levels = {}
        node_to_level = {}
        
        # Build reversed adjacency for checking dependencies
        rev_adjacency = {node_id: [] for node_id in self.nodes}
        
        for conn in self.connections:
            if conn.source in rev_adjacency and conn.target in rev_adjacency:
                rev_adjacency[conn.target].append(conn.source)
        
        # Assign levels
        for node_id in ordered_nodes:
            if not rev_adjacency[node_id]:
                # No dependencies, assign to level 0
                node_to_level[node_id] = 0
            else:
                # Assign to level after all dependencies
                max_dep_level = max(
                    (node_to_level.get(dep, 0) for dep in rev_adjacency[node_id]),
                    default=0
                )
                node_to_level[node_id] = max_dep_level + 1
        
        # Group by level
        for node_id, level in node_to_level.items():
            if level not in node_levels:
                node_levels[level] = []
            node_levels[level].append(node_id)
            
        return node_levels
    
    def _route_connections(self) -> None:
        """Calculate paths for all connections."""
        for conn in self.connections:
            if conn.source not in self.nodes or conn.target not in self.nodes:
                continue
                
            source = self.nodes[conn.source]
            target = self.nodes[conn.target]
            
            # Simple routing: straight line if possible, otherwise L-shaped
            source_x = source.x + source.width // 2
            source_y = source.y + source.height
            target_x = target.x + target.width // 2
            target_y = target.y
            
            # Path consists of points to draw lines between
            conn.path = [(source_x, source_y), (target_x, target_y)]
    
    def render(self) -> str:
        """Render the workflow to ASCII art."""
        if not self.nodes:
            return "Empty workflow"
            
        # Calculate layout if not done already
        if not self.canvas:
            self.calculate_layout()
            
        # Initialize canvas with spaces
        self.canvas = [[' ' for _ in range(self.canvas_width)] for _ in range(self.canvas_height)]
        
        # Draw title
        title_pos = (self.canvas_width - len(self.title)) // 2
        for i, char in enumerate(self.title):
            if 0 <= title_pos + i < self.canvas_width:
                self.canvas[0][title_pos + i] = char
        
        # Draw connections first so nodes can overwrite them
        self._draw_connections()
        
        # Draw nodes
        for node_id, node in self.nodes.items():
            self._draw_node(node)
        
        # Convert canvas to string
        return '\n'.join(''.join(row) for row in self.canvas)
    
    def _draw_node(self, node: Node) -> None:
        """Draw a node on the canvas."""
        style = node.style
        padding = style["padding"]
        
        # Draw the box boundaries
        # Top horizontal line
        for x in range(node.x, node.x + node.width):
            if 0 <= x < self.canvas_width and 0 <= node.y < self.canvas_height:
                if x == node.x:
                    self.canvas[node.y][x] = style["top_left"]
                elif x == node.x + node.width - 1:
                    self.canvas[node.y][x] = style["top_right"]
                else:
                    self.canvas[node.y][x] = style["horizontal"]
        
        # Bottom horizontal line
        for x in range(node.x, node.x + node.width):
            if 0 <= x < self.canvas_width and 0 <= node.y + node.height - 1 < self.canvas_height:
                if x == node.x:
                    self.canvas[node.y + node.height - 1][x] = style["bottom_left"]
                elif x == node.x + node.width - 1:
                    self.canvas[node.y + node.height - 1][x] = style["bottom_right"]
                else:
                    self.canvas[node.y + node.height - 1][x] = style["horizontal"]
        
        # Vertical lines
        for y in range(node.y + 1, node.y + node.height - 1):
            if 0 <= y < self.canvas_height:
                if 0 <= node.x < self.canvas_width:
                    self.canvas[y][node.x] = style["vertical"]
                if 0 <= node.x + node.width - 1 < self.canvas_width:
                    self.canvas[y][node.x + node.width - 1] = style["vertical"]
        
        # Draw node content
        lines = node.get_display_text()
        
        for i, line in enumerate(lines):
            y = node.y + padding + i
            if 0 <= y < self.canvas_height:
                # Center text horizontally
                start_x = node.x + padding
                end_x = min(node.x + node.width - padding, self.canvas_width)
                
                for j, char in enumerate(line):
                    x = start_x + j
                    if start_x <= x < end_x:
                        self.canvas[y][x] = char
    
    def _draw_connections(self) -> None:
        """Draw all connections on the canvas."""
        for conn in self.connections:
            if not conn.path or len(conn.path) < 2:
                continue
                
            style = conn.style
            
            # Draw each segment of the path
            for i in range(len(conn.path) - 1):
                start_x, start_y = conn.path[i]
                end_x, end_y = conn.path[i + 1]
                
                # Draw a straight line
                if start_x == end_x:  # Vertical line
                    for y in range(min(start_y, end_y), max(start_y, end_y) + 1):
                        if 0 <= start_x < self.canvas_width and 0 <= y < self.canvas_height:
                            # Add arrow at the end
                            if y == end_y - 1 and i == len(conn.path) - 2:
                                self.canvas[y][start_x] = 'v'  # Down arrow
                            else:
                                self.canvas[y][start_x] = style["vertical"]
                elif start_y == end_y:  # Horizontal line
                    for x in range(min(start_x, end_x), max(start_x, end_x) + 1):
                        if 0 <= x < self.canvas_width and 0 <= start_y < self.canvas_height:
                            # Add arrow at the end
                            if x == end_x - 1 and i == len(conn.path) - 2:
                                self.canvas[start_y][x] = conn.arrow
                            else:
                                self.canvas[start_y][x] = style["horizontal"]
            
            # Add connection label if exists
            if conn.label:
                # Place label near the middle of the path
                if len(conn.path) >= 2:
                    mid_idx = len(conn.path) // 2
                    x, y = conn.path[mid_idx]
                    
                    # Adjust position slightly to avoid overlapping with the line
                    label_x = x + 1
                    label_y = y
                    
                    if 0 <= label_y < self.canvas_height:
                        for i, char in enumerate(conn.label):
                            if 0 <= label_x + i < self.canvas_width:
                                self.canvas[label_y][label_x + i] = char


def load_workflow_from_yaml(file_path: str) -> Workflow:
    """Load workflow definition from YAML file."""
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
    
    return create_workflow_from_dict(data)


def load_workflow_from_json(file_path: str) -> Workflow:
    """Load workflow definition from JSON file."""
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    return create_workflow_from_dict(data)


def create_workflow_from_dict(data: Dict[str, Any]) -> Workflow:
    """Create a workflow from a dictionary."""
    title = data.get('title', 'Workflow')
    workflow = Workflow(title)
    
    # Create nodes
    for node_data in data.get('nodes', []):
        node = Node(
            node_id=node_data['id'],
            label=node_data['label'],
            node_type=node_data.get('type', 'process'),
            icon=node_data.get('icon'),
            description=node_data.get('description'),
            style=node_data.get('style')
        )
        workflow.add_node(node)
    
    # Create connections
    for conn_data in data.get('connections', []):
        connection = Connection(
            source=conn_data['source'],
            target=conn_data['target'],
            conn_type=conn_data.get('type', 'normal'),
            label=conn_data.get('label')
        )
        workflow.add_connection(connection)
    
    return workflow


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='ASCII Workflow Visualizer')
    
    # Input file options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--yaml', '-y', type=str, help='Path to YAML workflow definition')
    input_group.add_argument('--json', '-j', type=str, help='Path to JSON workflow definition')
    
    # Output options
    parser.add_argument('--output', '-o', type=str, help='Output file path (defaults to stdout)')
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    try:
        if args.yaml:
            workflow = load_workflow_from_yaml(args.yaml)
        elif args.json:
            workflow = load_workflow_from_json(args.json)
        else:
            print("Error: No input file specified")
            sys.exit(1)
        
        # Render the workflow
        output = workflow.render()
        
        # Write output
        if args.output:
            with open(args.output, 'w') as file:
                file.write(output)
        else:
            print(output)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


# Example programmatic usage
def create_sample_workflow():
    """Create a sample workflow programmatically."""
    workflow = Workflow("Sample CI/CD Pipeline")
    
    # Add nodes
    workflow.add_node(Node("start", "Start", "start", icon="🚀"))
    workflow.add_node(Node("checkout", "Git Checkout", "process", icon="📦"))
    workflow.add_node(Node("build", "Build", "tool", icon="🔨"))
    workflow.add_node(Node("test", "Run Tests", "tool", icon="🧪"))
    workflow.add_node(Node("decision", "Tests Passed?", "decision", icon="❓"))
    workflow.add_node(Node("deploy", "Deploy", "process", icon="🚀"))
    workflow.add_node(Node("notify_success", "Success", "result", icon="✅"))
    workflow.add_node(Node("notify_failure", "Failure", "result", icon="❌"))
    
    # Add connections
    workflow.add_connection(Connection("start", "checkout"))
    workflow.add_connection(Connection("checkout", "build"))
    workflow.add_connection(Connection("build", "test"))
    workflow.add_connection(Connection("test", "decision"))
    workflow.add_connection(Connection("decision", "deploy", "normal", "Yes"))
    workflow.add_connection(Connection("decision", "notify_failure", "normal", "No"))
    workflow.add_connection(Connection("deploy", "notify_success"))
    
    return workflow


if __name__ == "__main__":
    # If no arguments are provided, show a sample workflow
    if len(sys.argv) == 1:
        sample = create_sample_workflow()
        print(sample.render())
    else:
        main()