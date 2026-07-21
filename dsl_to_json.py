import json
from dsl_lexer import tokenize
from dsl_parser import Parser, Assignment, BuyStatement, SellStatement, BinaryOp, LogicalOp, Identifier, NumberLiteral, FunctionCall

def node_to_dict(node):
    """Convert one AST node into a plain dict, ready for JSON serialization."""

    if isinstance(node, Assignment):
        return {
            "type": "Assignment",
            "name": node.name,
            "expression": node_to_dict(node.expression)
        }

    if isinstance(node, BuyStatement):
        return {
            "type": "BuyStatement",
            "condition": node_to_dict(node.condition)
        }

    if isinstance(node, SellStatement):
        return {
            "type": "SellStatement",
            "condition": node_to_dict(node.condition)
        }

    if isinstance(node, BinaryOp):
        return {
            "type": "BinaryOp",
            "left": node_to_dict(node.left),
            "operator": node.operator,
            "right": node_to_dict(node.right)
        }

    if isinstance(node, LogicalOp):
        return {
            "type": "LogicalOp",
            "left": node_to_dict(node.left),
            "operator": node.operator,
            "right": node_to_dict(node.right)
        }

    if isinstance(node, Identifier):
        return {
            "type": "Identifier",
            "name": node.name
        }

    if isinstance(node, NumberLiteral):
        return {
            "type": "NumberLiteral",
            "value": node.value
        }

    if isinstance(node, FunctionCall):
        return {
            "type": "FunctionCall",
            "name": node.name,
            "args": [node_to_dict(arg) for arg in node.args]
        }

    raise ValueError(f"Unknown node type: {node}")


def compile_dsl_to_json(source_text, output_path):
    tokens = tokenize(source_text)
    program = Parser(tokens).parse_program()
    program_json = [node_to_dict(stmt) for stmt in program]

    with open(output_path, "w") as f:
        json.dump(program_json, f, indent=2)

    print(f"Wrote {len(program_json)} statements to {output_path}")


if __name__ == "__main__":
    source = """fast_ma = moving_average(close, 5)
slow_ma = moving_average(close, 20)
buy when fast_ma crosses_above slow_ma 
sell when fast_ma crosses_below slow_ma"""

    compile_dsl_to_json(source, "strategy.json")