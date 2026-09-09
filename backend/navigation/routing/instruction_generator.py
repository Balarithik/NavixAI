"""
Instruction Generator for NavixAI.
Converts path nodes and edges into clean, human-readable navigation directions.
"""

def generate_instructions(path_nodes, path_edges):
    """
    Generates step-by-step directions from node and edge sequence.
    """
    if not path_nodes:
        return []

    if len(path_nodes) == 1:
        return [f"You are already at {path_nodes[0].name}"]

    instructions = []
    start_node = path_nodes[0]
    instructions.append(f"Start at {start_node.name} (Floor {start_node.floor.floor_number})")

    for i in range(len(path_edges)):
        edge = path_edges[i]
        curr_node = path_nodes[i]
        next_node = path_nodes[i + 1]

        # Check for vertical floor transition
        if curr_node.floor.floor_number != next_node.floor.floor_number:
            direction = "up" if next_node.floor.floor_number > curr_node.floor.floor_number else "down"
            if edge.movement_type == 'lift':
                instructions.append(f"Take {curr_node.name} {direction} to Floor {next_node.floor.floor_number}")
            elif edge.movement_type == 'stairs':
                instructions.append(f"Take the stairs {direction} to Floor {next_node.floor.floor_number}")
            else:
                instructions.append(f"Proceed {direction} to Floor {next_node.floor.floor_number}")
            continue

        # Normal walking on same floor
        if next_node == path_nodes[-1]:
            instructions.append(f"Arrive at destination: {next_node.name}")
        elif next_node.type == 'junction':
            instructions.append(f"Continue straight through {next_node.name}")
        elif next_node.type in ('stair', 'lift'):
            instructions.append(f"Walk towards {next_node.name}")
        else:
            instructions.append(f"Continue past {next_node.name}")

    # Deduplicate consecutive identical instructions if any
    cleaned_instructions = []
    for inst in instructions:
        if not cleaned_instructions or cleaned_instructions[-1] != inst:
            cleaned_instructions.append(inst)

    return cleaned_instructions
